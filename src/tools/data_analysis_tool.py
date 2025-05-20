from langchain.tools import BaseTool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from src.models.llm_models import SUMMARY_MODEL
from pydantic import Field

class DataAnalysisTool(BaseTool):
    name: str = "data_analysis_tool"
    description: str = "Tool for data analysis and information retrieval"
    search: DuckDuckGoSearchAPIWrapper = Field(default_factory=DuckDuckGoSearchAPIWrapper)
    
    def _run(self, query: str) -> str:
        try:
            print("Searching for relevant information...")
            # Use DuckDuckGo search
            search_results = self.search.results(query, max_results=5)
            
            if not search_results:
                return "No relevant information found"
            
            # Format search results
            formatted_results = "\n\n".join([
                f"Title: {result.get('title', '')}\n"
                f"Summary: {result.get('snippet', '')}\n"
                f"Link: {result.get('link', '')}"
                for result in search_results
            ])
            
            # Use LLM to summarize search results
            summary_prompt = PromptTemplate(
                input_variables=["search_results", "query"],
                template="""Based on the following search results, provide a comprehensive analysis and summary of "{query}":
                
Search results:
{search_results}

Please provide a structured analysis and summary, including key facts, data points, and most relevant insights.
"""
            )
            
            summary_chain = LLMChain(
                llm=SUMMARY_MODEL,
                prompt=summary_prompt
            )
            
            summary = summary_chain.run(search_results=formatted_results, query=query)
            return summary
            
        except Exception as e:
            return f"Data analysis failed: {str(e)}"
        
    async def _arun(self, query: str) -> str:
        return self._run(query) 