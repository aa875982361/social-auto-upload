import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from myUtils.auth import check_cookie
from myUtils.jwt_auth import jwt_auth, token_required, optional_token
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from conf import BASE_DIR
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs
from utils.download_manager import download_manager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

active_queues = {}
# 正在发布的任务集合，用于防止重复提交
publishing_tasks = set()
app = Flask(__name__)

def generate_task_id(title, file_list, account_list, type):
    """生成任务唯一标识，基于标题、文件列表、账号列表和平台类型"""
    # 将列表转换为排序后的字符串，确保相同内容生成相同ID
    file_str = '|'.join(sorted(file_list))
    account_str = '|'.join(sorted(account_list))
    
    # 组合所有关键信息
    task_data = f"{title}|{file_str}|{account_str}|{type}"
    
    # 生成MD5哈希作为任务ID
    return hashlib.md5(task_data.encode('utf-8')).hexdigest()

def get_platform_name(platform_type):
    """根据平台类型获取平台名称"""
    platform_map = {
        1: '小红书',
        2: '视频号', 
        3: '抖音',
        4: '快手'
    }
    return platform_map.get(platform_type, '未知平台')

def save_publish_history(task_id, platform_type, platform_name, account_name, account_file_path, 
                        title, tags, file_list, status='pending', error_message=None,
                        enable_timer=0, videos_per_day=1, daily_times=None, start_days=0, category=0):
    """保存发布历史记录"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 将列表转换为JSON字符串
            tags_json = json.dumps(tags) if tags else None
            file_list_json = json.dumps(file_list)
            daily_times_json = json.dumps(daily_times) if daily_times else None
            
            cursor.execute('''
                INSERT INTO publish_history (
                    task_id, platform_type, platform_name, account_name, account_file_path,
                    title, tags, file_list, status, error_message,
                    enable_timer, videos_per_day, daily_times, start_days, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, platform_type, platform_name, account_name, account_file_path,
                title, tags_json, file_list_json, status, error_message,
                enable_timer, videos_per_day, daily_times_json, start_days, category
            ))
            conn.commit()
            print(f"✅ 发布历史记录已保存: {task_id}")
    except Exception as e:
        print(f"❌ 保存发布历史记录失败: {e}")

def update_publish_history_status(task_id, status, error_message=None):
    """更新发布历史记录状态"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE publish_history 
                SET status = ?, error_message = ?, publish_time = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (status, error_message, task_id))
            conn.commit()
            print(f"✅ 发布历史状态已更新: {task_id} -> {status}")
    except Exception as e:
        print(f"❌ 更新发布历史状态失败: {e}")

def init_database():
    """初始化数据库，确保所有必需的表都存在"""
    db_path = Path(BASE_DIR / "data" / "db" / "database.db")
    
    # 确保目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查数据库是否存在或为空
    db_exists = db_path.exists() and db_path.stat().st_size > 0
    
    if not db_exists:
        print("🔄 初始化数据库...")
    else:
        print("🔄 检查并创建数据库表...")
        print("🔄 备份数据库表...")
        # 备份现有数据库文件
        backup_filename = f"{db_path.stem}_backup_{time.strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = db_path.parent / backup_filename
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ 数据库备份成功: {backup_filename}")
        except Exception as e:
            print(f"❌ 数据库备份失败: {e}")

    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 创建账号记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type INTEGER NOT NULL,
            filePath TEXT NOT NULL,
            userName TEXT NOT NULL,
            status INTEGER DEFAULT 0
        )
        ''')
        
        # 创建文件记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filesize REAL,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT
        )
        ''')
        
        # 创建发布历史记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS publish_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            platform_type INTEGER NOT NULL,
            platform_name TEXT NOT NULL,
            account_name TEXT NOT NULL,
            account_file_path TEXT NOT NULL,
            title TEXT NOT NULL,
            tags TEXT,
            file_list TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            publish_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            enable_timer INTEGER DEFAULT 0,
            videos_per_day INTEGER DEFAULT 1,
            daily_times TEXT,
            start_days INTEGER DEFAULT 0,
            category INTEGER DEFAULT 0
        )
        ''')
        
        conn.commit()
        print("✅ 数据库表检查/创建完成")

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# 获取当前目录和前端构建目录
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dist_dir = os.path.join(current_dir, 'sau_frontend', 'dist')

# 处理所有静态资源请求（指向前端构建目录）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(frontend_dist_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（指向前端构建目录）
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(frontend_dist_dir, 'favicon.ico')

# 处理根路径，返回前端构建的 index.html
@app.route('/')
def hello_world():
    return send_from_directory(frontend_dist_dir, 'index.html')

# 登录接口
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'msg': '请求数据不能为空',
                'data': None
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'code': 400,
                'msg': '用户名和密码不能为空',
                'data': None
            }), 400
        
        # 验证用户名和密码
        if jwt_auth.verify_credentials(username, password):
            # 生成token
            token = jwt_auth.generate_token(username)
            return jsonify({
                'code': 200,
                'msg': '登录成功',
                'data': {
                    'token': token,
                    'username': username,
                    'expire_hours': jwt_auth.token_expire_hours
                }
            }), 200
        else:
            return jsonify({
                'code': 401,
                'msg': '用户名或密码错误',
                'data': None
            }), 401
            
    except Exception as e:
        return jsonify({
            'code': 500,
            'msg': f'登录失败: {str(e)}',
            'data': None
        }), 500

# 验证token接口
@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token():
    """验证token是否有效"""
    return jsonify({
        'code': 200,
        'msg': 'Token有效',
        'data': {
            'username': request.current_user
        }
    }), 200

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # 保存文件到指定位置
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{file.filename}")
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{file.filename}"}), 200
    except Exception as e:
        return jsonify({"code":200,"msg": str(e),"data":None}), 500

@app.route('/api/getFile', methods=['GET'])
@token_required
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')

    if not filename:
        return {"error": "filename is required"}, 400

    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return {"error": "Invalid filename"}, 400

    # 拼接完整路径
    file_path = str(Path(BASE_DIR / "videoFile"))

    # 返回文件
    return send_from_directory(file_path,filename)


@app.route('/api/uploadSave', methods=['POST'])
@token_required
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # 获取表单中的自定义文件名（可选）
    custom_filename = request.form.get('filename', None)
    if custom_filename:
        filename = custom_filename + "." + file.filename.split('.')[-1]
    else:
        filename = file.filename

    try:
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(BASE_DIR / "videoFile" / f"{uuid_v1}_{filename}")

        # 保存文件
        file.save(filepath)

        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ 上传文件已记录")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("upload failed!"),
            "data": None
        }), 500

@app.route('/api/getFiles', methods=['GET'])
@token_required
def get_all_files():
    try:
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # 将结果转为字典列表
            data = [dict(row) for row in rows]

        return jsonify({
            "code": 200,
            "msg": "success",
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


@app.route("/api/getValidAccounts",methods=['GET'])
@token_required
def getValidAccounts():
    # 获取搜索关键词参数
    search_keyword = request.args.get('search', '').strip()
    
    with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        
        # 根据是否有搜索关键词执行不同的查询
        if search_keyword:
            cursor.execute('''
            SELECT * FROM user_info 
            WHERE userName LIKE ?''', (f'%{search_keyword}%',))
        else:
            cursor.execute('''
            SELECT * FROM user_info''')
        
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print("\n📋 当前数据表内容：")
        for row in rows:
            print(row)
        
        # 创建新的事件循环来处理异步cookie检查
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for row in rows_list:
                flag = loop.run_until_complete(check_cookie(row[1],row[2]))
                if not flag:
                    row[4] = 0
                    cursor.execute('''
                    UPDATE user_info 
                    SET status = ? 
                    WHERE id = ?
                    ''', (0,row[0]))
                    conn.commit()
                    print("✅ 用户状态已更新")
        finally:
            loop.close()
            
        for row in rows:
            print(row)
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

@app.route('/api/deleteFile', methods=['GET'])
@token_required
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/api/deleteAccount', methods=['GET'])
@token_required
def delete_account():
    account_id = int(request.args.get('id'))

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500


# SSE 登录接口 (与账号登录不同，这是社交媒体账号登录)
@app.route('/api/account/login')
def account_login():
    token = request.args.get('token')
    # 如果URL中包含token参数，验证token
    if not token:
        return jsonify({
            'code': 401,
            'msg': '缺少认证token',
            'data': None
        }), 401
    if token:
        from myUtils.jwt_auth import jwt_auth
        is_valid, payload = jwt_auth.verify_token(token)
        if not is_valid:
            return jsonify({
                'code': 401,
                'msg': payload.get('error', 'Token无效或已过期'),
                'data': None
            }), 401
    # 1 小红书 2 视频号 3 抖音 4 快手
    type = request.args.get('type')
    # 账号名
    id = request.args.get('id')

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"清理队列: {id}")
        del active_queues[id]
    # 启动异步任务线程
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/api/postVideo', methods=['POST'])
@token_required
def postVideo():
    try:
        # 获取JSON数据
        data = request.get_json()
        
        # 参数验证
        if not data:
            return jsonify({
                "code": 400,
                "msg": "请求数据不能为空",
                "data": None
            }), 400

        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        
        # 基本参数验证
        if not file_list:
            return jsonify({
                "code": 400,
                "msg": "文件列表不能为空",
                "data": None
            }), 400
            
        if not account_list:
            return jsonify({
                "code": 400,
                "msg": "账号列表不能为空", 
                "data": None
            }), 400
            
        if not type or type not in [1, 2, 3, 4]:
            return jsonify({
                "code": 400,
                "msg": "平台类型无效",
                "data": None
            }), 400
        
        if category == 0:
            category = None

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        
        # 打印获取到的数据（包含URL支持信息）
        print("Original File List:", file_list)
        print("Account List:", account_list)
        online_count = len([f for f in file_list if f.startswith(('http://', 'https://'))])
        local_count = len([f for f in file_list if not f.startswith(('http://', 'https://'))])
        print(f"包含线上资源数量: {online_count}")
        print(f"包含本地文件数量: {local_count}")
        
        # 提前处理文件下载，将所有线上资源下载到本地
        print("开始处理文件下载...")
        processed_file_list = download_manager.process_file_list(file_list)
        
        if not processed_file_list:
            return jsonify({
                "code": 400,
                "msg": "没有有效的文件可以上传，所有文件处理失败",
                "data": None
            }), 400
        
        if len(processed_file_list) != len(file_list):
            print(f"警告: 部分文件处理失败，原始文件数: {len(file_list)}, 处理成功: {len(processed_file_list)}")
        
        print(f"文件处理完成，最终文件列表: {processed_file_list}")
        
        # 生成任务唯一标识
        task_id = generate_task_id(title, file_list, account_list, type)
        print(f"生成任务ID: {task_id}")
        
        # 检查是否有重复任务正在进行
        if task_id in publishing_tasks:
            return jsonify({
                "code": 409,
                "msg": "相同的发布任务正在进行中，请勿重复提交",
                "data": {"task_id": task_id}
            }), 409
        
        # 将任务ID添加到正在发布的任务集合中
        publishing_tasks.add(task_id)
        print(f"任务 {task_id} 已添加到发布队列")
        
        # 获取平台名称
        platform_name = get_platform_name(type)
        
        # 为每个账号记录发布历史
        for account_file_path in account_list:
            # 从账号文件路径中提取账号名称（去掉路径和扩展名）
            account_name = Path(account_file_path).stem
            
            # 保存发布历史记录
            save_publish_history(
                task_id=task_id,
                platform_type=type,
                platform_name=platform_name,
                account_name=account_name,
                account_file_path=account_file_path,
                title=title,
                tags=tags,
                file_list=processed_file_list,
                status='pending',
                enable_timer=1 if enableTimer else 0,
                videos_per_day=videos_per_day or 1,
                daily_times=daily_times,
                start_days=start_days or 0,
                category=category or 0
            )
        
    except Exception as e:
        print(f"参数解析或文件处理错误: {e}")
        return jsonify({
            "code": 500,
            "msg": f"参数解析或文件处理错误: {str(e)}",
            "data": None
        }), 500
    
    try:
        # 执行视频上传，现在使用已处理的本地文件列表
        match type:
            case 1:
                post_video_xhs(title, processed_file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 2:
                post_video_tencent(title, processed_file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 3:
                post_video_DouYin(title, processed_file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case 4:
                post_video_ks(title, processed_file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
        
        # 发布成功，更新历史记录状态
        update_publish_history_status(task_id, 'success')
                          
        # 返回成功响应
        return jsonify({
            "code": 200,
            "msg": "视频上传任务已启动，线上资源已下载完成",
            "data": {
                "original_files": len(file_list),
                "processed_files": len(processed_file_list),
                "online_resources_downloaded": online_count,
                "local_files": local_count,
                "download_success_rate": f"{len(processed_file_list)}/{len(file_list)}",
                "task_id": task_id
            }
        }), 200
        
    except Exception as e:
        print(f"视频上传处理错误: {e}")
        # 发布失败，更新历史记录状态
        if 'task_id' in locals():
            update_publish_history_status(task_id, 'failed', str(e))
        return jsonify({
            "code": 500,
            "msg": f"视频上传处理失败: {str(e)}",
            "data": None
        }), 500
    finally:
        # 无论成功还是失败，都要从发布队列中移除任务ID
        try:
            if 'task_id' in locals():
                publishing_tasks.discard(task_id)
                print(f"任务 {task_id} 已从发布队列中移除")
        except Exception as cleanup_error:
            print(f"清理任务ID时出错: {cleanup_error}")


@app.route('/api/updateUserinfo', methods=['POST'])
@token_required
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/api/postVideoBatch', methods=['POST'])
@token_required
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)
        match type:
            case 1:
                return
            case 2:
                post_video_tencent(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 3:
                post_video_DouYin(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
            case 4:
                post_video_ks(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                          start_days)
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# 包装函数：在线程中运行异步函数
def run_async_function(type,id,status_queue):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id,status_queue))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id,status_queue))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id,status_queue))
            loop.close()

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # 避免 CPU 占满
            time.sleep(0.1)

@app.route('/api/publishHistory', methods=['GET'])
@token_required
def get_publish_history():
    """获取发布历史记录"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        platform_type = request.args.get('platformType')
        status = request.args.get('status')
        account_name = request.args.get('accountName')
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 构建查询条件
            where_conditions = []
            params = []
            
            if platform_type:
                where_conditions.append("platform_type = ?")
                params.append(platform_type)
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
                
            if account_name:
                where_conditions.append("account_name LIKE ?")
                params.append(f"%{account_name}%")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM publish_history {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 查询数据
            data_sql = f"""
                SELECT * FROM publish_history 
                {where_clause}
                ORDER BY created_time DESC 
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, params + [page_size, offset])
            records = cursor.fetchall()
            
            # 转换记录为字典列表
            history_list = []
            for record in records:
                history_item = {
                    'id': record['id'],
                    'task_id': record['task_id'],
                    'platform_type': record['platform_type'],
                    'platform_name': record['platform_name'],
                    'account_name': record['account_name'],
                    'account_file_path': record['account_file_path'],
                    'title': record['title'],
                    'tags': json.loads(record['tags']) if record['tags'] else [],
                    'file_list': json.loads(record['file_list']),
                    'status': record['status'],
                    'error_message': record['error_message'],
                    'publish_time': record['publish_time'],
                    'created_time': record['created_time'],
                    'enable_timer': record['enable_timer'],
                    'videos_per_day': record['videos_per_day'],
                    'daily_times': json.loads(record['daily_times']) if record['daily_times'] else [],
                    'start_days': record['start_days'],
                    'category': record['category']
                }
                history_list.append(history_item)
            
            return jsonify({
                "code": 200,
                "msg": "获取发布历史成功",
                "data": {
                    "list": history_list,
                    "total": total,
                    "page": page,
                    "pageSize": page_size,
                    "totalPages": (total + page_size - 1) // page_size
                }
            }), 200
            
    except Exception as e:
        print(f"获取发布历史失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"获取发布历史失败: {str(e)}",
            "data": None
        }), 500

@app.route('/api/publishStatus/<task_id>', methods=['GET'])
@token_required
def get_publish_status(task_id):
    """获取特定任务的发布状态"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM publish_history 
                WHERE task_id = ? 
                ORDER BY created_time DESC
            """, (task_id,))
            records = cursor.fetchall()
            
            if not records:
                return jsonify({
                    "code": 404,
                    "msg": "未找到该任务",
                    "data": None
                }), 404
            
            # 转换记录为字典列表
            status_list = []
            for record in records:
                status_item = {
                    'id': record['id'],
                    'task_id': record['task_id'],
                    'platform_type': record['platform_type'],
                    'platform_name': record['platform_name'],
                    'account_name': record['account_name'],
                    'title': record['title'],
                    'status': record['status'],
                    'error_message': record['error_message'],
                    'publish_time': record['publish_time'],
                    'created_time': record['created_time']
                }
                status_list.append(status_item)
            
            return jsonify({
                "code": 200,
                "msg": "获取任务状态成功",
                "data": status_list
            }), 200
            
    except Exception as e:
        print(f"获取任务状态失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"获取任务状态失败: {str(e)}",
            "data": None
        }), 500

@app.route('/api/deletePublishHistory/<int:history_id>', methods=['DELETE'])
@token_required
def delete_publish_history(history_id):
    """删除发布历史记录"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "data" / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM publish_history WHERE id = ?", (history_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({
                    "code": 200,
                    "msg": "删除成功",
                    "data": None
                }), 200
            else:
                return jsonify({
                    "code": 404,
                    "msg": "记录不存在",
                    "data": None
                }), 404
                
    except Exception as e:
        print(f"删除发布历史失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"删除发布历史失败: {str(e)}",
            "data": None
        }), 500

if __name__ == '__main__':
    # 初始化数据库
    init_database()
    app.run(host='0.0.0.0' ,port=5409)
