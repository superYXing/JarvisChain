from langchain.tools import BaseTool

class PPTTool(BaseTool):
    name: str = "ppt_creation_tool"
    description: str = "Tool for creating PPT presentations, handling all PPT-related requests"
    
    def _run(self, query: str) -> str:
        # This is just an example, should call actual PPT generation API or service
        return f"PPT created: {query}"
        
    async def _arun(self, query: str) -> str:
        return self._run(query) 