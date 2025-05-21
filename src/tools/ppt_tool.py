from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json
from src.utils.logger import get_logger

# Get logger
logger = get_logger('ppt')

class PPTToolInput(BaseModel):
    command: str = Field(..., description="Natural language command describing the PPT operation")

class PPTTool(BaseTool):
    name: str = "ppt_tool"
    description: str = """Tool for creating and editing PowerPoint presentations from natural language commands."""
    args_schema: type[BaseModel] = PPTToolInput

    def _run(self, input_data: PPTToolInput) -> str:
        """Process the command using a large model to interpret and convert to structured PPT operations."""
        try:
            # Assuming the availability of a large language model to interpret commands
            from src.models.llm_models import INTENT_MODEL
            from langchain.schema import SystemMessage, HumanMessage

            system_prompt = """You are a PPT assistant converting natural language commands to structured JSON.
                Operations: create, open, add_slide, add_text, add_image, add_shape, save.
                Respond with JSON format:
                {"operation": "operation_name", "parameters": { ... }}"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=input_data.command)
            ]

            response = INTENT_MODEL.invoke(messages)
            operation_json = json.loads(response.content)

            # Here you could call your existing PPT functions
            operation = operation_json.get("operation")
            parameters = operation_json.get("parameters", {})

            logger.info(f"Executing operation: {operation} with parameters: {parameters}")
            # Mock response for simplicity
            return json.dumps({"success": True, "operation": operation, "parameters": parameters})

        except Exception as e:
            logger.error(f"Error in PPT tool: {str(e)}")
            return json.dumps({"success": False, "message": f"Error: {str(e)}"})

    async def _arun(self, input_data: PPTToolInput) -> str:
        return self._run(input_data)
