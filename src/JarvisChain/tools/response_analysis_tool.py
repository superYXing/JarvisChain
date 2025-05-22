from langchain.tools import BaseTool
from langchain.schema import SystemMessage, HumanMessage
from src.JarvisChain.models.llm_models import DECISION_MODEL
from src.JarvisChain.utils.logger import get_logger
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
            # Ensure input is valid JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"Invalid input JSON format: {input_text}")
                    # Try to extract useful information from string
                    if "Action Input:" in input_text:
                        # May be direct input from agent
                        logger.info("Attempting to extract information from agent input")
                        data = {
                            "response": "",
                            "user_input": input_text
                        }
                    else:
                        return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            # Log input content for debugging
            logger.info(f"Analyzing input - Response: {response[:100]}... | User input: {user_input[:100]}...")
            
            # Check if content is PPT-related
            is_ppt_related = self._check_if_ppt_related(user_input, response)
            
            system_prompt = """You are a dialogue analysis expert. Your task is to analyze the dialogue and return a JSON format response.
Important: You must only return a valid JSON object, do not include any other text or explanation.

Analyze the AI's response and user input to determine the next action.
Return a JSON object with the following structure:
{
    "needs_continuation": boolean,  // Whether to continue execution
    "needs_user_input": boolean,    // Whether user input is needed
    "is_task_complete": boolean,    // Whether the task is complete
    "next_prompt": string          // If user input is needed, provide an appropriate prompt
}

Rules:
1. Only complex tasks (such as creating PPTs or collecting research materials) require user confirmation of details.
2. If it's a simple greeting (like "hello" or "hi"), set needs_user_input to false.
3. Only return a JSON object, do not include any other text.
4. Ensure the JSON format is correct, use true/false for booleans, and quotes for strings.
5. For PPT creation process:
   a. In the initial stage of PPT creation (collecting information, determining topic), set needs_user_input to true
   b. During PPT creation (adding slides, content, and images), set needs_continuation to true, needs_user_input to false
   c. Only when AI explicitly indicates need for user confirmation or encounters a decision point, user input is needed
   d. Identify completion indicators like "PPT completed" or "presentation saved", set is_task_complete to true
6. If the user explicitly asks questions or requests modifications, always set needs_user_input to true
7. In daily conversations unrelated to PPT, follow normal confirmation process

Strictly return JSON format, do not add any other text."""

            # If it's PPT-related content, add more context
            if is_ppt_related:
                system_prompt += """
PPT Creation Special Guidelines:
1. File creation and initial planning stage require user confirmation - set needs_user_input to true
2. When AI indicates "creating slides" or "processing", set needs_continuation to true, needs_user_input to false
3. When AI output contains "successfully created" or "presentation saved", it indicates the main task is complete, set is_task_complete to true
4. If the user inputs new PPT instructions (modify layout, add content), continue processing - needs_continuation to true
5. For AI discussing content it is building, no user confirmation is needed - needs_continuation to true, needs_user_input to false
"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User input: {user_input}\nAI response: {response}")
            ]
            
            result = DECISION_MODEL.invoke(messages)
            logger.info(f"DECISION_MODEL original response: {result.content}")
            
            # Ensure the return is valid JSON
            try:
                # Try to directly parse the returned content
                try:
                    parsed_result = json.loads(result.content)
                except json.JSONDecodeError:
                    # Try to extract JSON part
                    content = result.content
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_content = content[start_idx:end_idx]
                        logger.info(f"Extracted JSON content: {json_content}")
                        parsed_result = json.loads(json_content)
                    else:
                        raise ValueError("Unable to extract valid JSON from response")
                
                # Verify necessary fields exist
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                missing_fields = [field for field in required_fields if field not in parsed_result]
                
                if missing_fields:
                    logger.error(f"Missing fields in response: {missing_fields}")
                    # Provide default values for missing fields
                    for field in missing_fields:
                        if field == "next_prompt":
                            parsed_result[field] = "Do you need other help?"
                        elif field == "is_task_complete":
                            parsed_result[field] = True
                        else:
                            parsed_result[field] = False
                
                # Perform additional PPT-related logic processing
                if is_ppt_related:
                    parsed_result = self._adjust_for_ppt_workflow(parsed_result, response, user_input)
                
                return json.dumps(parsed_result)
            except Exception as e:
                logger.error(f"Error processing DECISION_MODEL response: {str(e)}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_default_response()
    
    def _check_if_ppt_related(self, user_input, response):
        """Check if content is PPT-related"""
        ppt_keywords = ["ppt", "演示文稿", "幻灯片", "presentation", "slide"]
        
        # Check if user input or AI response contains PPT keywords
        for keyword in ppt_keywords:
            if (keyword.lower() in user_input.lower() or keyword.lower() in response.lower()):
                return True
                
        # Check if it contains PPT filename format
        if "presentation_" in response and ".pptx" in response:
            return True
            
        return False
    
    def _adjust_for_ppt_workflow(self, result, response, user_input):
        """Adjust analysis results for PPT workflow"""
        # Automated processing during PPT creation
        if ("正在创建" in response or "处理中" in response or 
            "添加幻灯片" in response or "adding slide" in response or 
            "添加内容" in response):
            result["needs_continuation"] = True
            result["needs_user_input"] = False
        
        # PPT creation completion indicators
        if ("成功创建" in response or "已完成" in response or 
            "已保存" in response or "成功执行" in response or
            "演示文稿已" in response):
            result["is_task_complete"] = True
            # If there's a clear follow-up question, still need user input
            if "您需要" in response or "是否需要" in response:
                result["needs_user_input"] = True
            
        # If user explicitly confirms or rejects, need user input
        if any(keyword in user_input.lower() for keyword in ["确认", "同意", "可以", "不要", "取消", "修改"]):
            result["needs_user_input"] = True
            
        # Check if it's a short user input followed by detailed response (usually no need for confirmation)
        if len(user_input) < 15 and len(response) > 100 and "ppt" in response.lower():
            result["needs_continuation"] = True
            result["needs_user_input"] = False
            
        return result
    
    async def _arun(self, input_text: str) -> str:
        """Run analysis tool asynchronously"""
        try:
            # Ensure input is valid JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"Invalid input JSON format: {input_text}")
                    # Try to extract useful information from string
                    if "Action Input:" in input_text:
                        # May be direct input from agent
                        logger.info("Attempting to extract information from agent input")
                        data = {
                            "response": "",
                            "user_input": input_text
                        }
                    else:
                        return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            # Log input content for debugging
            logger.info(f"Analyzing input - Response: {response[:100]}... | User input: {user_input[:100]}...")
            
            # Check if content is PPT-related
            is_ppt_related = self._check_if_ppt_related(user_input, response)
            
            system_prompt = """You are a dialogue analysis expert. Your task is to analyze the dialogue and return a JSON format response.
Important: You must only return a valid JSON object, do not include any other text or explanation.

Analyze the AI's response and user input to determine the next action.
Return a JSON object with the following structure:
{
    "needs_continuation": boolean,  // Whether to continue execution
    "needs_user_input": boolean,    // Whether user input is needed
    "is_task_complete": boolean,    // Whether the task is complete
    "next_prompt": string          // If user input is needed, provide an appropriate prompt
}

Rules:
1. Only complex tasks (such as creating PPTs or collecting research materials) require user confirmation of details.
2. If it's a simple greeting (like "hello" or "hi"), set needs_user_input to false.
3. Only return a JSON object, do not include any other text.
4. Ensure the JSON format is correct, use true/false for booleans, and quotes for strings.
5. For PPT creation process:
   a. In the initial stage of PPT creation (collecting information, determining topic), set needs_user_input to true
   b. During PPT creation (adding slides, content, and images), set needs_continuation to true, needs_user_input to false
   c. Only when AI explicitly indicates need for user confirmation or encounters a decision point, user input is needed
   d. Identify completion indicators like "PPT completed" or "presentation saved", set is_task_complete to true
6. If the user explicitly asks questions or requests modifications, always set needs_user_input to true
7. In daily conversations unrelated to PPT, follow normal confirmation process

Strictly return JSON format, do not add any other text."""

            # If it's PPT-related content, add more context
            if is_ppt_related:
                system_prompt += """
PPT Creation Special Guidelines:
1. File creation and initial planning stage require user confirmation - set needs_user_input to true
2. When AI indicates "creating slides" or "processing", set needs_continuation to true, needs_user_input to false
3. When AI output contains "successfully created" or "presentation saved", it indicates the main task is complete, set is_task_complete to true
4. If the user inputs new PPT instructions (modify layout, add content), continue processing - needs_continuation to true
5. For AI discussing content it is building, no user confirmation is needed - needs_continuation to true, needs_user_input to false
"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User input: {user_input}\nAI response: {response}")
            ]
            
            result = await DECISION_MODEL.ainvoke(messages)
            logger.info(f"DECISION_MODEL original response: {result.content}")
            
            # Ensure the return is valid JSON
            try:
                # Try to directly parse the returned content
                try:
                    parsed_result = json.loads(result.content)
                except json.JSONDecodeError:
                    # Try to extract JSON part
                    content = result.content
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_content = content[start_idx:end_idx]
                        logger.info(f"Extracted JSON content: {json_content}")
                        parsed_result = json.loads(json_content)
                    else:
                        raise ValueError("Unable to extract valid JSON from response")
                
                # Verify necessary fields exist
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                missing_fields = [field for field in required_fields if field not in parsed_result]
                
                if missing_fields:
                    logger.error(f"Missing fields in response: {missing_fields}")
                    # Provide default values for missing fields
                    for field in missing_fields:
                        if field == "next_prompt":
                            parsed_result[field] = "Do you need other help?"
                        elif field == "is_task_complete":
                            parsed_result[field] = True
                        else:
                            parsed_result[field] = False
                
                # Perform additional PPT-related logic processing
                if is_ppt_related:
                    parsed_result = self._adjust_for_ppt_workflow(parsed_result, response, user_input)
                
                return json.dumps(parsed_result)
            except Exception as e:
                logger.error(f"Error processing DECISION_MODEL response: {str(e)}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"Error analyzing response: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_default_response()
    
    def _get_default_response(self) -> str:
        """Return default response JSON"""
        return json.dumps({
            "needs_continuation": False,
            "needs_user_input": True,
            "is_task_complete": True,
            "next_prompt": "Sorry, I cannot process this request now. Do you need other help?"
        }) 