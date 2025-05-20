from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from src.models.llm_models import DECISION_MODEL
from src.utils.logger import get_logger

# Get logger
logger = get_logger('decision')

class DecisionTool(BaseTool):
    """Tool for determining execution status and next steps"""
    name: str = "decision_tool"
    description: str = """Tool for determining current execution status and deciding next steps.
    Analyzes current execution results and context to determine if we need to:
    1. Continue with next step
    2. Request user input
    3. Complete the task
    4. Handle errors
    
    Input format:
    {
        "response": "Execution result",
        "context": "Context information"
    }
    """
    
    def _run(self, input_str: str) -> dict:
        """Synchronously determine execution status"""
        try:
            # Parse input
            import json
            input_data = json.loads(input_str)
            response = input_data.get("response", "")
            context = input_data.get("context", "")
            
            # Build decision prompt
            decision_prompt = PromptTemplate(
                input_variables=["response", "context"],
                template="""Analyze the following execution result and context to determine next steps.

Context information:
{context}

Execution result:
{response}

Please analyze and return a JSON format decision containing the following fields:
{
    "action": "CONTINUE|USER_INPUT|COMPLETE|ERROR",
    "reason": "Decision reason",
    "next_step": "Specific next step suggestion"
}

Where:
- CONTINUE: Continue with next step
- USER_INPUT: Need user input
- COMPLETE: Task complete
- ERROR: Need to handle error

Return only the JSON format decision, no other output.
"""
            )
            
            # Create decision chain
            decision_chain = LLMChain(
                llm=DECISION_MODEL,
                prompt=decision_prompt
            )
            
            # Execute decision
            result = decision_chain.run(
                response=response,
                context=context
            )
            
            # Parse JSON result
            decision = json.loads(result)
            return decision
            
        except Exception as e:
            logger.error(f"Decision failed: {str(e)}")
            return {
                "action": "ERROR",
                "reason": f"Error in decision process: {str(e)}",
                "next_step": "Request user to re-enter input"
            }
    
    async def _arun(self, input_str: str) -> dict:
        """Asynchronously determine execution status"""
        try:
            # Parse input
            import json
            input_data = json.loads(input_str)
            response = input_data.get("response", "")
            context = input_data.get("context", "")
            
            # Build decision prompt
            decision_prompt = PromptTemplate(
                input_variables=["response", "context"],
                template="""Analyze the following execution result and context to determine next steps.

Context information:
{context}

Execution result:
{response}

Please analyze and return a JSON format decision containing the following fields:
{
    "action": "CONTINUE|USER_INPUT|COMPLETE|ERROR",
    "reason": "Decision reason",
    "next_step": "Specific next step suggestion"
}

Where:
- CONTINUE: Continue with next step
- USER_INPUT: Need user input
- COMPLETE: Task complete
- ERROR: Need to handle error

Return only the JSON format decision, no other output.
"""
            )
            
            # Create decision chain
            decision_chain = LLMChain(
                llm=DECISION_MODEL,
                prompt=decision_prompt
            )
            
            # Execute decision
            result = await decision_chain.arun(
                response=response,
                context=context
            )
            
            # Parse JSON result
            decision = json.loads(result)
            return decision
            
        except Exception as e:
            logger.error(f"Decision failed: {str(e)}")
            return {
                "action": "ERROR",
                "reason": f"Error in decision process: {str(e)}",
                "next_step": "Request user to re-enter input"
            } 