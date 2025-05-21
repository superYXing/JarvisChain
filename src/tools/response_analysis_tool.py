from langchain.tools import BaseTool
from langchain.schema import SystemMessage, HumanMessage
from src.models.llm_models import DECISION_MODEL
from src.utils.logger import get_logger
import json

# Get logger
logger = get_logger('response_analysis')

class ResponseAnalysisTool(BaseTool):
    """Tool for analyzing AI responses and user inputs"""
    name: str = "response_analysis_tool"
    description: str = "Analyze AI responses and user inputs to determine next steps"
    
    def _run(self, input_text: str) -> str:
        """Run analysis tool synchronously"""
        try:
            # 确保输入是有效的JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"Invalid input JSON: {input_text}")
                    return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            system_prompt = """你是一个对话分析专家。你的任务是分析对话并返回JSON格式的响应。
重要：你必须只返回一个有效的JSON对象，不要包含其他文本或解释。

分析AI的响应和用户输入以确定下一步行动。
返回一个具有以下结构的JSON对象：
{
    "needs_continuation": boolean,  // 是否需要继续执行
    "needs_user_input": boolean,    // 是否需要用户输入
    "is_task_complete": boolean,    // 任务是否完成
    "next_prompt": string          // 如果需要用户输入，提供适当的提示
}

规则：
1. 只有复杂的任务（如创建PPT或收集研究材料）才需要向用户确认细节。
2. 如果是简单的问候（如"hello"或"hi"），将needs_user_input设置为false。
3. 只返回JSON对象，不要包含其他文本。
4. 确保JSON格式正确，布尔值使用true/false，字符串使用引号。"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户输入: {user_input}\nAI响应: {response}")
            ]
            
            result = DECISION_MODEL.invoke(messages)
            
            # 确保返回的是有效的JSON
            try:
                # 尝试解析返回的内容
                parsed_result = json.loads(result.content)
                # 验证必要的字段是否存在
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                if all(field in parsed_result for field in required_fields):
                    return result.content
                else:
                    logger.error(f"Missing required fields in response: {result.content}")
                    return self._get_default_response()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from model: {result.content}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            return self._get_default_response()
    
    async def _arun(self, input_text: str) -> str:
        """Run analysis tool asynchronously"""
        try:
            # 确保输入是有效的JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"Invalid input JSON: {input_text}")
                    return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            system_prompt = """你是一个对话分析专家。你的任务是分析对话并返回JSON格式的响应。
重要：你必须只返回一个有效的JSON对象，不要包含其他文本或解释。

分析AI的响应和用户输入以确定下一步行动。
返回一个具有以下结构的JSON对象：
{
    "needs_continuation": boolean,  // 是否需要继续执行
    "needs_user_input": boolean,    // 是否需要用户输入
    "is_task_complete": boolean,    // 任务是否完成
    "next_prompt": string          // 如果需要用户输入，提供适当的提示
}

规则：
1. 只有复杂的任务（如创建PPT或收集研究材料）才需要向用户确认细节。
2. 如果是简单的问候（如"hello"或"hi"），将needs_user_input设置为false。
3. 只返回JSON对象，不要包含其他文本。
4. 确保JSON格式正确，布尔值使用true/false，字符串使用引号。"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户输入: {user_input}\nAI响应: {response}")
            ]
            
            result = await DECISION_MODEL.ainvoke(messages)
            
            # 确保返回的是有效的JSON
            try:
                # 尝试解析返回的内容
                parsed_result = json.loads(result.content)
                # 验证必要的字段是否存在
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                if all(field in parsed_result for field in required_fields):
                    return result.content
                else:
                    logger.error(f"Missing required fields in response: {result.content}")
                    return self._get_default_response()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from model: {result.content}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            return self._get_default_response()
    
    def _get_default_response(self) -> str:
        """返回默认的响应JSON"""
        return json.dumps({
            "needs_continuation": False,
            "needs_user_input": True,
            "is_task_complete": True,
            "next_prompt": "抱歉，我现在无法处理这个请求。您还有其他需要帮助的吗？"
        }) 