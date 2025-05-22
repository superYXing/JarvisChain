from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json
from src.JarvisChain.utils.logger import get_logger
from src.JarvisChain.models.llm_models import INTENT_MODEL
from langchain.schema import SystemMessage, HumanMessage

# Get logger
logger = get_logger('ppt_outline')

class PPTOutlineTool(BaseTool):
    name: str = "ppt_outline_tool"
    description: str = """用于根据搜索结果生成PPT大纲的工具。"""
    
    def _run(self, input_data: str) -> str:
        """处理生成PPT大纲的命令"""

        system_prompt = """你是一个专业的PPT大纲生成专家。你的任务是根据提供的信息生成PPT大纲。你是一位专业的演示文稿设计师，擅长根据给定主题，自动生成结构清晰、逻辑严谨、内容丰富的PPT大纲。

你生成的大纲应当包括：
1. **封面页**：包含演示主题标题。
2. **目录页（可选）**：列出各章节的标题（如适用）。
3. **3-5个主体章节**：每章包含标题和2-4点内容，每点不超过两句话，尽量简洁明确。
4. **结论页**：总结主题要点，或给出展望/建议。
5. **可选附录页**：用于拓展阅读、参考资料、致谢等内容。

输出格式如下：
---
【封面】
主题：XXX

【章节1】
标题：XXX
- 内容1
- 内容2
- 内容3

【章节2】
标题：XXX
- 内容1
- 内容2
...

【结论】
- 总结点1
- 总结点2

---

编写要求：
- 内容要符合逻辑顺序，避免内容重复。
- 每章节内容要围绕主题展开，逐层深入。
- 使用简洁有力的中文表达。
- 如遇科普型主题，适当加入举例说明。
"""
            
        messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=input_data)
            ]
            
        response = INTENT_MODEL.invoke(messages)

        print(f"大纲结果：{response}")
    
    async def _arun(self, input_data: str) -> str:
        """异步处理生成PPT大纲的命令"""
        return self._run(input_data) 