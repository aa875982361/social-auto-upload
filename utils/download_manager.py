import os
import hashlib
import json
import requests
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Optional
import logging

from conf import BASE_DIR

logger = logging.getLogger(__name__)

class DownloadManager:
    """管理线上资源下载和本地文件映射的类"""
    
    def __init__(self):
        self.download_dir = BASE_DIR / "videoFile"
        self.mapping_file = BASE_DIR / "url_mapping.json"
        self.url_to_file_map = self._load_mapping()
        
        # 确保下载目录存在
        self.download_dir.mkdir(exist_ok=True)
    
    def _load_mapping(self) -> Dict[str, str]:
        """加载URL到本地文件的映射关系"""
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"无法加载映射文件 {self.mapping_file}")
        return {}
    
    def _save_mapping(self):
        """保存URL到本地文件的映射关系"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.url_to_file_map, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存映射文件失败: {e}")
    
    def _generate_filename(self, url: str) -> str:
        """根据URL生成唯一的本地文件名"""
        # 使用URL的MD5哈希作为文件名前缀
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
        
        # 尝试从URL中提取文件扩展名
        parsed_url = urlparse(url)
        path = parsed_url.path
        if path and '.' in path:
            # 获取最后一个点后面的内容作为扩展名
            ext = path.split('.')[-1].lower()
            # 验证扩展名是否是常见的视频格式
            if ext in ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'm4v', 'webm']:
                return f"{url_hash}.{ext}"
        
        # 如果无法确定扩展名，默认使用mp4
        return f"{url_hash}.mp4"
    
    def _download_file(self, url: str, local_path: Path) -> bool:
        """下载文件到本地路径"""
        try:
            logger.info(f"开始下载文件: {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('video/') and 'application/octet-stream' not in content_type:
                logger.warning(f"URL返回的内容类型可能不是视频文件: {content_type}")
            
            # 下载文件
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 验证文件大小
            if local_path.stat().st_size == 0:
                local_path.unlink()  # 删除空文件
                logger.error(f"下载的文件为空: {url}")
                return False
            
            logger.info(f"文件下载成功: {local_path}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"下载文件失败 {url}: {e}")
            if local_path.exists():
                local_path.unlink()  # 清理部分下载的文件
            return False
        except Exception as e:
            logger.error(f"下载过程中发生未知错误 {url}: {e}")
            if local_path.exists():
                local_path.unlink()
            return False
    
    def is_url(self, file_path: str) -> bool:
        """判断字符串是否为URL"""
        return file_path.startswith(('http://', 'https://'))
    
    def get_local_file(self, file_path: str) -> Optional[str]:
        """
        获取本地文件路径。如果是URL，则下载到本地；如果是本地文件，直接返回。
        
        Args:
            file_path: 文件路径或URL
            
        Returns:
            本地文件的相对路径（相对于videoFile目录）或None（如果处理失败）
        """
        # 如果不是URL，直接返回原路径
        if not self.is_url(file_path):
            return file_path
        
        # 检查是否已经下载过
        if file_path in self.url_to_file_map:
            local_filename = self.url_to_file_map[file_path]
            local_path = self.download_dir / local_filename
            
            # 验证文件是否还存在
            if local_path.exists():
                logger.info(f"使用已缓存的文件: {local_filename}")
                return local_filename
            else:
                # 文件不存在，从映射中删除
                logger.warning(f"缓存的文件不存在，重新下载: {local_filename}")
                del self.url_to_file_map[file_path]
        
        # 生成本地文件名
        local_filename = self._generate_filename(file_path)
        local_path = self.download_dir / local_filename
        
        # 确保文件名唯一
        counter = 1
        original_filename = local_filename
        while local_path.exists():
            name, ext = os.path.splitext(original_filename)
            local_filename = f"{name}_{counter}{ext}"
            local_path = self.download_dir / local_filename
            counter += 1
        
        # 下载文件
        if self._download_file(file_path, local_path):
            # 保存映射关系
            self.url_to_file_map[file_path] = local_filename
            self._save_mapping()
            return local_filename
        else:
            logger.error(f"下载文件失败: {file_path}")
            return None
    
    def process_file_list(self, file_list: list) -> list:
        """
        处理文件列表，将URL下载为本地文件
        
        Args:
            file_list: 包含文件路径和URL的列表
            
        Returns:
            处理后的本地文件路径列表
        """
        processed_files = []
        
        for file_path in file_list:
            if not file_path:
                continue
                
            local_file = self.get_local_file(file_path)
            if local_file:
                processed_files.append(local_file)
            else:
                logger.error(f"无法处理文件: {file_path}")
        
        return processed_files
    
    def cleanup_unused_files(self):
        """清理未使用的下载文件（可选功能）"""
        try:
            mapped_files = set(self.url_to_file_map.values())
            
            for file_path in self.download_dir.iterdir():
                if file_path.is_file() and file_path.name not in mapped_files:
                    # 这个文件不在映射中，可能是孤儿文件
                    logger.info(f"发现未映射的文件: {file_path.name}")
                    # 注意：这里只是记录，不删除，因为可能是用户手动上传的文件
        except Exception as e:
            logger.error(f"清理文件时发生错误: {e}")

# 创建全局下载管理器实例
download_manager = DownloadManager()
