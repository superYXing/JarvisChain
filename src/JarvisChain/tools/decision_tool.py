from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from src.JarvisChain.models.llm_models import DECISION_MODEL
from src.JarvisChain.utils.logger import get_logger

# 获取日志记录器
logger = get_logger('decision')

class DecisionTool(BaseTool):
    """用于确定执行状态和下一步操作的工具"""
    name: str = "decision_tool"
    description: str = """用于确定当前执行状态并决定下一步操作的工具。
    分析当前执行结果和上下文，以确定是否需要：
    1. 继续下一步
    2. 请求用户输入
    3. 完成任务
    4. 处理错误
    
    输入格式：
    {
        "response": "执行结果",
        "context": "上下文信息"
    }
    """
    
    def _run(self, input_str: str) -> dict:
        """同步确定执行状态"""
        try:
            # 解析输入
            import json
            input_data = json.loads(input_str)
            response = input_data.get("response", "")
            context = input_data.get("context", "")
            
            # 构建决策提示
            decision_prompt = PromptTemplate(
                input_variables=["response", "context"],
                template="""分析以下执行结果和上下文以确定下一步操作。

上下文信息：
{context}

执行结果：
{response}

请分析并返回一个包含以下字段的JSON格式决策：
{
    "action": "CONTINUE|USER_INPUT|COMPLETE|ERROR",
    "reason": "决策原因",
    "next_step": "具体的下一步建议"
}

其中：
- CONTINUE: 继续下一步
- USER_INPUT: 需要用户输入
- COMPLETE: 任务完成
- ERROR: 需要处理错误

只返回JSON格式的决策，不要包含其他输出。
"""
            )
            
            # 创建决策链
            decision_chain = LLMChain(
                llm=DECISION_MODEL,
                prompt=decision_prompt
            )
            
            # 执行决策
            result = decision_chain.run(
                response=response,
                context=context
            )
            
            # 解析JSON结果
            decision = json.loads(result)
            return decision
            
        except Exception as e:
            logger.error(f"决策失败: {str(e)}")
            return {
                "action": "ERROR",
                "reason": f"决策过程中出错: {str(e)}",
                "next_step": "请求用户重新输入"
            }
    
    async def _arun(self, input_str: str) -> dict:
        """异步确定执行状态"""
        try:
            # 解析输入
            import json
            input_data = json.loads(input_str)
            response = input_data.get("response", "")
            context = input_data.get("context", "")
            
            # 构建决策提示
            decision_prompt = PromptTemplate(
                input_variables=["response", "context"],
                template="""分析以下执行结果和上下文以确定下一步操作。

上下文信息：
{context}

执行结果：
{response}

请分析并返回一个包含以下字段的JSON格式决策：
{
    "action": "CONTINUE|USER_INPUT|COMPLETE|ERROR",
    "reason": "决策原因",
    "next_step": "具体的下一步建议"
}

其中：
- CONTINUE: 继续下一步
- USER_INPUT: 需要用户输入
- COMPLETE: 任务完成
- ERROR: 需要处理错误

只返回JSON格式的决策，不要包含其他输出。
"""
            )
            
            # 创建决策链
            decision_chain = LLMChain(
                llm=DECISION_MODEL,
                prompt=decision_prompt
            )
            
            # 执行决策
            result = await decision_chain.arun(
                response=response,
                context=context
            )
            
            # 解析JSON结果
            decision = json.loads(result)
            return decision
            
        except Exception as e:
            logger.error(f"决策失败: {str(e)}")
            return {
                "action": "ERROR",
                "reason": f"决策过程中出错: {str(e)}",
                "next_step": "请求用户重新输入"
            } 