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

# 获取日志记录器
logger = get_logger('image_search_tool')

class ImageSearchTool(BaseTool):
    """图片搜索工具"""
    name: str = "ImageSearchTool"
    description: str = (
        "搜索图片并保存到本地。输入为JSON格式。字段："
        "'query'（搜索关键词）、"
        "'max_results'（可选，最大结果数量，默认：5）。"
    )
    client: TavilyClient = None
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
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
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
    
    def _download_image(self, url: str, filename: str) -> bool:
        """下载图片到本地"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            filepath = os.path.join(self.img_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"成功保存图片: {filename}")
            return True
        except Exception as e:
            logger.error(f"下载图片失败 {url}: {str(e)}")
            return False
    
    def _run(self, input_data: str) -> str:
        try:
            # 解析输入参数
            if isinstance(input_data, str):
                try:
                    data = json.loads(input_data)
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试解析为简单的查询字符串
                    data = {"query": input_data.strip()}
            else:
                data = input_data
            
            query = data.get("query")
            max_results = data.get("max_results", 5)

            if not query:
                return json.dumps({
                    "success": False,
                    "message": "需要提供搜索关键词"
                })

            logger.info(f"开始搜索图片: {query}")
            
            # 使用Tavily搜索，包含图片
            search_results = self.client.search(
                query=query,
                search_depth="basic",
                include_images=True,
                max_results=max_results
            )
            
            # 提取图片URL
            images = search_results.get("images", [])
            if not images:
                return json.dumps({
                    "success": False,
                    "message": "未找到相关图片"
                })
            
            # 下载并保存图片
            saved_images = []
            for i, image_url in enumerate(images[:max_results]):
                filename = self._get_next_filename()
                if self._download_image(image_url, filename):
                    saved_images.append({
                        "filename": filename,
                        "path": os.path.join(self.img_dir, filename),
                        "url": image_url
                    })
            
            if not saved_images:
                return json.dumps({
                    "success": False,
                    "message": "所有图片下载失败"
                })
            
            return json.dumps({
                "success": True,
                "message": f"成功搜索并保存了 {len(saved_images)} 张图片",
                "images": saved_images,
                "query": query
            })

        except Exception as e:
            logger.error(f"搜索图片失败: {str(e)}")
            return json.dumps({
                "success": False,
                "message": str(e)
            })
    
    async def _arun(self, input_data: str) -> str:
        return self._run(input_data) 