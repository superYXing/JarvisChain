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
            # Parse input text
            data = json.loads(input_text)
            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            system_prompt = """You are a conversation analysis expert. Analyze the AI's response and user input to determine the next action.
Please return the analysis result in JSON format as follows:
{
    "needs_continuation": true/false,  // Whether execution needs to continue
    "needs_user_input": true/false,    // Whether user input is needed
    "is_task_complete": true/false,    // Whether the task is complete
    "next_prompt": "Next prompt"       // If user input is needed, provide appropriate prompt

    notice:Only complex tasks like creating PowerPoint presentations or gathering research materials require confirming details with users.
      If it's just a simple greeting like "hello" or "hi", there's no need to call any tools.
}"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User input: {user_input}\nAI response: {response}")
            ]
            
            result = DECISION_MODEL.invoke(messages)
            return result.content  # Return JSON string directly
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            # Return default values if parsing fails
            return json.dumps({
                "needs_continuation": False,
                "needs_user_input": True,
                "is_task_complete": True,
                "next_prompt": "Can not handle right now. Is there anything else I can help you with?"
            })
    
    async def _arun(self, input_text: str) -> str:
        """Run analysis tool asynchronously"""
        try:
            # Parse input text
            data = json.loads(input_text)
            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            system_prompt = """You are a conversation analysis expert. If it's just a simple greeting like "hello" or "hi", there's no need to call any tools.Analyze the AI's response and user input to determine the next action.
Please return the analysis result in JSON format as follows:
{
    "needs_continuation": true/false,  // Whether execution needs to continue
    "needs_user_input": true/false,    // Whether user input is needed
    "is_task_complete": true/false,    // Whether the task is complete
    "next_prompt": "Next prompt"       // If user input is needed, provide appropriate prompt

    Notice：
    notice:Only complex tasks like creating PowerPoint presentations or gathering research materials require confirming details with users.
     If it's just a simple greeting like "hello" or "hi", there's no need to call any tools.
}"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User input: {user_input}")
            ]
            
            result = await DECISION_MODEL.ainvoke(messages)
            return result.content  # Return JSON string directly
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            # Return default values if parsing fails
            return json.dumps({
                "needs_continuation": False,
                "needs_user_input": True,
                "is_task_complete": True,
                "next_prompt": "Can not handle right now. Is there anything else I can help you with?"
            }) 