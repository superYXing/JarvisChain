from langchain.tools import BaseTool
from langchain.tools.tavily_search import TavilySearchResults
import os
from src.utils.logger import get_logger
from dotenv import load_dotenv
from pydantic import Field

# 加载环境变量
load_dotenv()

# Get logger
logger = get_logger('data_analysis')

class DataAnalysisTool(BaseTool):
    """数据分析工具"""
    name: str = "data_analysis_tool"
    description: str = "搜索和分析数据。输入应该是搜索关键词。"
    search_tool: TavilySearchResults = Field(
        default_factory=lambda: TavilySearchResults(
            api_key=os.getenv("TAVILY_API_KEY"),
            max_results=5,
            include_images=False
        )
    )
    
    def _run(self, query: str) -> str:
        """同步执行数据搜索"""
        try:
            # 使用Tavily搜索数据
            search_result = self.search_tool.run(query)
            
            # 解析搜索结果
            if isinstance(search_result, str):
                search_result = eval(search_result)  # 将字符串转换为字典
            
            # 提取文本内容
            results = []
            for result in search_result:
                if 'content' in result:
                    results.append(result['content'])
                elif 'title' in result:
                    results.append(result['title'])
            
            if not results:
                return "未找到相关信息"
            
            # 格式化输出
            formatted_results = "\n\n".join([
                f"结果 {i+1}:\n{content}"
                for i, content in enumerate(results)
            ])
            
            return f"找到以下相关信息：\n\n{formatted_results}"
                
        except Exception as e:
            logger.error(f"搜索数据时发生错误: {str(e)}")
            return f"搜索数据时发生错误: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """异步执行数据搜索"""
        return self._run(query) 