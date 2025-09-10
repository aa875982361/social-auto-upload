import asyncio
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity
from myUtils.auth import check_cookie
from myUtils.auth_service import AuthService, require_auth, require_admin, require_user
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from conf import BASE_DIR
from myUtils.login import get_tencent_cookie, douyin_cookie_gen, get_ks_cookie, xiaohongshu_cookie_gen
from myUtils.postVideo import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs

active_queues = {}
app = Flask(__name__)

#允许所有来源跨域访问
CORS(app)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# 初始化认证服务
auth_service = AuthService(app)

# ==================== 数据隔离工具函数 ====================

def get_user_data_dir(user_id):
    """获取用户专属数据目录"""
    user_dir = Path(BASE_DIR / "data" / "users" / str(user_id))
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def get_user_video_dir(user_id):
    """获取用户专属视频目录"""
    video_dir = get_user_data_dir(user_id) / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    return video_dir

def get_user_account_dir(user_id):
    """获取用户专属账号目录"""
    account_dir = get_user_data_dir(user_id) / "accounts"
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir

def verify_file_ownership(file_path, user_id):
    """验证文件是否属于指定用户"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM file_records WHERE file_path = ? AND created_by = ?",
                (file_path, user_id)
            )
            return cursor.fetchone()[0] > 0
    except Exception as e:
        print(f"验证文件所有权失败: {e}")
        return False

def verify_account_ownership(account_id, user_id):
    """验证账号是否属于指定用户"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM user_info WHERE id = ? AND created_by = ?",
                (account_id, user_id)
            )
            return cursor.fetchone()[0] > 0
    except Exception as e:
        print(f"验证账号所有权失败: {e}")
        return False

# 获取当前目录（假设 index.html 和 assets 在这里）
current_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), 'favicon.ico')

# （未来打包用）
@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')

# ==================== 用户认证API ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({
            'code': 400,
            'msg': '用户名、邮箱和密码都是必填项',
            'data': None
        }), 400
    
    result = auth_service.register_user(username, email, password)
    
    if result['success']:
        return jsonify({
            'code': 200,
            'msg': result['message'],
            'data': {'user_id': result['user_id']}
        }), 200
    else:
        return jsonify({
            'code': 400,
            'msg': result['message'],
            'data': None
        }), 400

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    """用户登录"""
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({
            'code': 400,
            'msg': '用户名和密码都是必填项',
            'data': None
        }), 400
    
    result = auth_service.authenticate_user(username, password)
    
    if result['success']:
        return jsonify({
            'code': 200,
            'msg': result['message'],
            'data': result['data']
        }), 200
    else:
        return jsonify({
            'code': 401,
            'msg': result['message'],
            'data': None
        }), 401

@app.route('/api/auth/logout', methods=['POST'])
@require_user()
def logout_api():
    """用户登出"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    result = auth_service.logout_user(token)
    
    return jsonify({
        'code': 200,
        'msg': result['message'],
        'data': None
    }), 200

@app.route('/api/auth/profile', methods=['GET'])
@require_user()
def get_profile():
    """获取当前用户信息"""
    user = request.current_user
    
    return jsonify({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'created_at': user['created_at']
        }
    }), 200

@app.route('/api/auth/users', methods=['GET'])
@require_admin()
def get_all_users():
    """获取所有用户（仅管理员）"""
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at
                FROM auth_users
                ORDER BY created_at DESC
            ''')
            
            users = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'code': 200,
                'msg': '获取成功',
                'data': users
            }), 200
            
    except Exception as e:
        return jsonify({
            'code': 500,
            'msg': f'获取用户列表失败: {str(e)}',
            'data': None
        }), 500

@app.route('/upload', methods=['POST'])
@require_user()
def upload_file():
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
    try:
        # 获取当前用户ID
        current_user_id = int(get_jwt_identity())
        
        # 保存文件到用户专属目录
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        final_filename = f"{uuid_v1}_{file.filename}"
        user_video_dir = get_user_video_dir(current_user_id)
        filepath = user_video_dir / final_filename
        file.save(filepath)
        
        # 记录文件信息到数据库
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO file_records (filename, filesize, file_path, created_by)
                VALUES (?, ?, ?, ?)
            ''', (file.filename, round(float(os.path.getsize(filepath)) / (1024 * 1024), 2), final_filename, current_user_id))
            conn.commit()
            print(f"\u2705 用户{current_user_id}上传文件已记录")
        
        return jsonify({"code": 200, "msg": "File uploaded successfully", "data": final_filename}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e), "data": None}), 500

@app.route('/getFile', methods=['GET'])
@require_user()
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())

    if not filename:
        return jsonify({"code": 400, "msg": "filename is required", "data": None}), 400

    # 防止路径穿越攻击
    if '..' in filename or filename.startswith('/'):
        return jsonify({"code": 400, "msg": "Invalid filename", "data": None}), 400

    try:
        # 验证文件所有权
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 检查文件是否属于当前用户
            cursor.execute("SELECT COUNT(*) FROM file_records WHERE file_path = ? AND created_by = ?", (filename, current_user_id))
            count = cursor.fetchone()[0]
            
            if count == 0:
                return jsonify({
                    "code": 403,
                    "msg": "Access denied: file not found or not owned by current user",
                    "data": None
                }), 403
    
        # 拼接用户专属文件路径
        user_video_dir = get_user_video_dir(current_user_id)
        full_file_path = user_video_dir / filename
        file_path = str(user_video_dir)
        
        # 检查文件是否存在
        if not full_file_path.exists():
            return jsonify({"code": 404, "msg": "File not found", "data": None}), 404

        # 返回文件
        return send_from_directory(file_path, filename)
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"File access failed: {str(e)}",
            "data": None
        }), 500


@app.route('/uploadSave', methods=['POST'])
@require_user()
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
        # 获取当前用户ID
        current_user_id = int(get_jwt_identity())
        
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        user_video_dir = get_user_video_dir(current_user_id)
        filepath = user_video_dir / final_filename

        # 保存文件
        file.save(filepath)
        
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path, created_by)
            VALUES (?, ?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename, current_user_id))
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

@app.route('/getFiles', methods=['GET'])
@require_user()
def get_all_files():
    try:
        # 获取当前用户ID
        current_user_id = int(get_jwt_identity())
        
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            cursor = conn.cursor()

            # 只查询当前用户的文件记录
            cursor.execute("SELECT * FROM file_records WHERE created_by = ? ORDER BY upload_time DESC", (current_user_id,))
            rows = cursor.fetchall()

            # 将结果转为字典列表
            data = [dict(row) for row in rows]
            
            print(f"\n📋 用户{current_user_id}的文件数据，共{len(rows)}条")

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


@app.route("/getValidAccounts",methods=['GET'])
@require_user()
def getValidAccounts():
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())
    
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        # 只查询当前用户创建的账号
        print(f"\n🔍 用户{current_user_id}正在查询账号，类型: {type(current_user_id)}")
        cursor.execute('''
        SELECT * FROM user_info WHERE created_by = ?''', (current_user_id,))
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        print(f"\n📋 用户{current_user_id}的账号数据，共{len(rows)}条")
        # 注释掉cookie验证，避免在测试时因为没有真实cookie文件导致账号被过滤
        # for row in rows_list:
        #     # 使用 asyncio.run 来运行异步函数
        #     flag = asyncio.run(check_cookie(row[1],row[2]))
        #     if not flag:
        #         row[4] = 0
        #         cursor.execute('''
        #         UPDATE user_info 
        #         SET status = ? 
        #         WHERE id = ? AND created_by = ?
        #         ''', (0, row[0], current_user_id))
        #         conn.commit()
        #         print("✅ 用户状态已更新")
        
        return jsonify(
                        {
                            "code": 200,
                            "msg": None,
                            "data": rows_list
                        }),200

@app.route('/deleteFile', methods=['GET'])
@require_user()
def delete_file():
    file_id = request.args.get('id')
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录，确保文件属于当前用户
            cursor.execute("SELECT * FROM file_records WHERE id = ? AND created_by = ?", (file_id, current_user_id))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found or access denied",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ? AND created_by = ?", (file_id, current_user_id))
            conn.commit()
            
            # 同时删除物理文件
            try:
                user_video_dir = get_user_video_dir(current_user_id)
                file_path = user_video_dir / record['file_path']
                if file_path.exists():
                    file_path.unlink()
                    print(f"\u2705 已删除物理文件: {record['file_path']}")
            except Exception as delete_error:
                print(f"\u26a0\ufe0f 删除物理文件失败: {delete_error}")

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

@app.route('/deleteAccount', methods=['GET'])
@require_user()
def delete_account():
    account_id = int(request.args.get('id'))
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())

    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录，确保账号属于当前用户
            cursor.execute("SELECT * FROM user_info WHERE id = ? AND created_by = ?", (account_id, current_user_id))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found or access denied",
                    "data": None
                }), 404

            record = dict(record)

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ? AND created_by = ?", (account_id, current_user_id))
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


# SSE 登录接口
@app.route('/login')
@require_user()
def login():
    # 1 小红书 2 视频号 3 抖音 4 快手
    type = request.args.get('type')
    # 账号名
    id = request.args.get('id')
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())

    # 模拟一个用于异步通信的队列
    status_queue = Queue()
    active_queues[id] = status_queue

    def on_close():
        print(f"清理队列: {id}")
        del active_queues[id]
    # 启动异步任务线程，传递当前用户ID
    thread = threading.Thread(target=run_async_function, args=(type,id,status_queue,current_user_id), daemon=True)
    thread.start()
    response = Response(sse_stream(status_queue,), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 关键：禁用 Nginx 缓冲
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/postVideo', methods=['POST'])
@require_user()
def postVideo():
    # 获取JSON数据
    data = request.get_json()

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
    
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())
    
    # 验证账号权限：确保所有账号都属于当前用户
    try:
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            cursor = conn.cursor()
            
            # 验证每个账号文件是否属于当前用户
            for account_file in account_list:
                cursor.execute('''
                    SELECT COUNT(*) FROM user_info 
                    WHERE filePath = ? AND created_by = ?
                ''', (account_file, current_user_id))
                
                count = cursor.fetchone()[0]
                if count == 0:
                    return jsonify({
                        "code": 403,
                        "msg": f"无权限使用账号: {account_file}",
                        "data": None
                    }), 403
    
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"验证账号权限失败: {str(e)}",
            "data": None
        }), 500
    
    # 打印获取到的数据（仅作为示例）
    print("File List:", file_list)
    print("Account List:", account_list)
    print(f"User {current_user_id} 正在发布视频")
    
    match type:
        case 1:
            post_video_xhs(title, file_list, tags, account_list, category, enableTimer, videos_per_day, daily_times,
                               start_days)
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


@app.route('/updateUserinfo', methods=['POST'])
@require_user()
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())
    
    try:
        # 获取数据库连接
        with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 先检查账号是否属于当前用户
            cursor.execute("SELECT * FROM user_info WHERE id = ? AND created_by = ?", (user_id, current_user_id))
            record = cursor.fetchone()
            
            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found or access denied",
                    "data": None
                }), 404

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ? AND created_by = ?;
                           ''', (type, userName, user_id, current_user_id))
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

@app.route('/postVideoBatch', methods=['POST'])
@require_user()
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    
    # 获取当前用户ID
    current_user_id = int(get_jwt_identity())
    
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
        
        # 验证账号权限：确保所有账号都属于当前用户
        try:
            with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
                cursor = conn.cursor()
                
                # 验证每个账号文件是否属于当前用户
                for account_file in account_list:
                    cursor.execute('''
                        SELECT COUNT(*) FROM user_info 
                        WHERE filePath = ? AND created_by = ?
                    ''', (account_file, current_user_id))
                    
                    count = cursor.fetchone()[0]
                    if count == 0:
                        return jsonify({
                            "code": 403,
                            "msg": f"无权限使用账号: {account_file}",
                            "data": None
                        }), 403
        
        except Exception as e:
            return jsonify({
                "code": 500,
                "msg": f"验证账号权限失败: {str(e)}",
                "data": None
            }), 500
        
        # 打印获取到的数据（仅作为示例）
        print("File List:", file_list)
        print("Account List:", account_list)
        print(f"User {current_user_id} 正在批量发布视频")
        
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
def run_async_function(type,id,status_queue,current_user_id):
    match type:
        case '1':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(xiaohongshu_cookie_gen(id, status_queue, current_user_id))
            loop.close()
        case '2':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_tencent_cookie(id,status_queue, current_user_id))
            loop.close()
        case '3':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(douyin_cookie_gen(id,status_queue, current_user_id))
            loop.close()
        case '4':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_ks_cookie(id,status_queue, current_user_id))
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

if __name__ == '__main__':
    app.run(host='0.0.0.0' ,port=5409)
