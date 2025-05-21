from langchain.tools import BaseTool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.tools.tavily_search import TavilySearchResults
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from src.models.llm_models import SUMMARY_MODEL
from pydantic import Field
import os
from dotenv import load_dotenv
import requests
from PIL import Image
from io import BytesIO
import time
import json

# 加载环境变量
load_dotenv()

class DataAnalysisTool(BaseTool):
    name: str = "data_analysis_tool"
    description: str = "Tool for data analysis and information retrieval using both DuckDuckGo and Tavily search"
    search_ddg: DuckDuckGoSearchAPIWrapper = Field(default_factory=DuckDuckGoSearchAPIWrapper)
    search_tavily: TavilySearchResults = Field(default_factory=lambda: TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY")))
    
    def _download_and_save_image(self, image_url: str, save_path: str) -> bool:
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                img.save(save_path)
                return True
            return False
        except Exception as e:
            print(f"下载图片失败: {str(e)}")
            return False

    def _search_and_save_images(self, query: str) -> list:
        try:
            # 确保img目录存在
            img_dir = os.path.join(os.getcwd(), "img")
            os.makedirs(img_dir, exist_ok=True)
            
            # 使用Tavily搜索图片
            tavily_results = self.search_tavily.invoke(
                query,
                search_depth="advanced",
                include_images=True
            )
            
            saved_images = []
            image_count = 0
            
            # 处理Tavily搜索结果
            for result in tavily_results:
                if image_count >= 3:  # 只保存前3张图片
                    break
                    
                # 检查结果中是否包含图片
                if 'images' in result:
                    for image_url in result['images']:
                        if image_count >= 3:
                            break
                            
                        timestamp = int(time.time())
                        save_path = os.path.join(img_dir, f"image_{timestamp}_{image_count}.jpg")
                        if self._download_and_save_image(image_url, save_path):
                            saved_images.append(save_path)
                            image_count += 1
            
            return saved_images
        except Exception as e:
            print(f"图片搜索失败: {str(e)}")
            return []

    def _run(self, query: str) -> str:
        try:
            print("搜索相关信息...")
            
            # 搜索并保存图片
            saved_images = self._search_and_save_images(query)
            image_info = "\n".join([f"已保存图片: {img}" for img in saved_images]) if saved_images else "未找到相关图片"
            
            # 使用 Tavily 搜索
            tavily_results = self.search_tavily.invoke(
                query,
                search_depth="advanced",
                include_images=True
            )
            
            # 处理 Tavily 结果
            all_results = []
            for result in tavily_results:
                all_results.append({
                    "source": "Tavily",
                    "title": result.get('title', ''),
                    "summary": result.get('content', ''),
                    "link": result.get('url', ''),
                    "images": result.get('images', [])
                })
            
            if not all_results:
                return "未找到相关信息"
            
            # 格式化搜索结果
            formatted_results = "\n\n".join([
                f"来源: {result['source']}\n"
                f"标题: {result['title']}\n"
                f"摘要: {result['summary']}\n"
                f"链接: {result['link']}\n"
                f"相关图片数量: {len(result['images'])}"
                for result in all_results
            ])
            
            # 使用 LLM 总结搜索结果
            summary_prompt = PromptTemplate(
                input_variables=["search_results", "query", "image_info"],
                template="""基于以下搜索结果，提供关于"{query}"的综合分析和总结：

搜索结果：
{search_results}

图片信息：
{image_info}

请提供结构化的分析和总结，包括关键事实、数据点和最相关的见解。
请用中文回答。
"""
            )
            
            summary_chain = LLMChain(
                llm=SUMMARY_MODEL,
                prompt=summary_prompt
            )
            
            summary = summary_chain.run(
                search_results=formatted_results,
                query=query,
                image_info=image_info
            )
            return summary
            
        except Exception as e:
            return f"数据分析失败: {str(e)}"
        
    async def _arun(self, query: str) -> str:
        return self._run(query) 