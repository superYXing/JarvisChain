from langchain.tools import BaseTool
from tavily import TavilyClient
import os
import requests
from src.JarvisChain.utils.logger import get_logger
from dotenv import load_dotenv
from pydantic import Field
import json

# 加载环境变量
load_dotenv()

# Get logger
logger = get_logger('image_search')

class ImageSearchTool(BaseTool):
    """图片搜索工具"""
    name: str = "image_search_tool"
    description: str = "搜索图片并保存到本地。输入应该是搜索关键词。"
    client: TavilyClient = Field(
        default_factory=lambda: TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    )
    img_dir: str = Field(
        default_factory=lambda: os.path.join(os.getcwd(), "img")
    )
    counter_file: str = Field(
        default_factory=lambda: os.path.join(os.getcwd(), "img", "counter.json")
    )
    _counter: int = 0
    _ppts_dir: str = "ppts"
    
    def __init__(self, **data):
        super().__init__(**data)
        # 确保img目录存在
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
        # 初始化或加载计数器
        self._init_counter()
    
    def _init_counter(self):
        """初始化或加载计数器"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    self._counter = json.load(f).get('counter', 0)
            else:
                os.makedirs(os.path.dirname(self.counter_file), exist_ok=True)
                self._save_counter()
        except Exception as e:
            logger.error(f"初始化计数器失败: {str(e)}")
            self._counter = 0
    
    def _save_counter(self):
        """保存计数器"""
        try:
            with open(self.counter_file, 'w') as f:
                json.dump({'counter': self._counter}, f)
        except Exception as e:
            logger.error(f"保存计数器失败: {str(e)}")
    
    def _get_next_filename(self, prefix=None) -> str:
        """获取下一个文件名"""
        self._counter += 1
        self._save_counter()
        if prefix:
            return f"{prefix}_{self._counter}.jpg"
        return f"image_{self._counter}.jpg"
    
    def _run(self, query: str) -> str:
        """同步执行图片搜索"""
        try:
            # 解析查询参数
            params = self._parse_query(query)
            search_query = params.get("query", query)
            max_images = params.get("max_images", 3)
            image_prefix = params.get("prefix", None)
            
            # 使用Tavily搜索图片
            search_result = self.client.search(
                query=search_query,
                search_depth="advanced",
                include_images=True,
                max_results=5  # 获取更多结果，因为并非所有结果都有图片
            )
            
            # 获取图片URL
            image_urls = []
            if 'images' in search_result:
                image_urls = search_result['images'][:max_images]  # 限制图片数量
            
            if not image_urls:
                return "未找到相关图片"
            
            # 下载并保存图片
            saved_images = []
            absolute_paths = []
            for url in image_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        # 生成文件名
                        file_name = self._get_next_filename(image_prefix)
                        file_path = os.path.join(self.img_dir, file_name)
                        
                        # 保存图片
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        saved_images.append(file_name)
                        absolute_paths.append(file_path)
                        logger.info(f"成功保存图片: {file_name}")
                except Exception as e:
                    logger.error(f"下载图片时发生错误: {str(e)}")
            
            if saved_images:
                # 返回带有相对路径和绝对路径的JSON结果
                result = {
                    "success": True,
                    "message": f"成功保存了 {len(saved_images)} 张图片",
                    "images": [
                        {
                            "filename": img, 
                            "relative_path": f"img/{img}", 
                            "absolute_path": os.path.join(self.img_dir, img)
                        }
                        for img in saved_images
                    ]
                }
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({"success": False, "message": "图片下载失败"})
                
        except Exception as e:
            logger.error(f"搜索图片时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({"success": False, "message": f"搜索图片时发生错误: {str(e)}"})
    
    def _parse_query(self, query: str) -> dict:
        """解析查询字符串，提取参数"""
        try:
            # 尝试将查询解析为JSON
            if query.strip().startswith("{"):
                try:
                    return json.loads(query)
                except json.JSONDecodeError:
                    pass
            
            # 检查是否包含特殊参数标记
            params = {"query": query}
            
            # 提取max_images参数
            if "max_images:" in query:
                parts = query.split("max_images:")
                if len(parts) > 1:
                    try:
                        max_images = int(parts[1].split()[0])
                        params["max_images"] = max_images
                        # 移除参数标记
                        params["query"] = query.replace(f"max_images:{max_images}", "").strip()
                    except ValueError:
                        pass
            
            # 提取prefix参数
            if "prefix:" in query:
                parts = query.split("prefix:")
                if len(parts) > 1:
                    prefix = parts[1].split()[0]
                    params["prefix"] = prefix
                    # 移除参数标记
                    params["query"] = query.replace(f"prefix:{prefix}", "").strip()
            
            return params
        except Exception as e:
            logger.error(f"解析查询时发生错误: {str(e)}")
            return {"query": query}
    
    async def _arun(self, query: str) -> str:
        """异步执行图片搜索"""
        return self._run(query) 