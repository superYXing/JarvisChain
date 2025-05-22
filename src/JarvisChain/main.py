import asyncio
import json
import warnings
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.tools.ppt_add_tool import PPTAddTool
from src.JarvisChain.tools.ppt_remove_tool import PPTRemoveTool
from src.JarvisChain.tools.ppt_update_tool import PPTUpdateTool
from src.JarvisChain.tools.data_analysis_tool import DataAnalysisTool
from src.JarvisChain.tools.ppt_outline_tool import PPTOutlineTool
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
from src.JarvisChain.tools.response_analysis_tool import ResponseAnalysisTool
from src.JarvisChain.tools.image_search_tool import ImageSearchTool
from src.JarvisChain.utils.user_profile import UserProfileManager
from src.JarvisChain.utils.memory_manager import MemoryManager
from src.JarvisChain.utils.logger import get_logger
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools.render import format_tool_to_openai_function
from typing import List, Dict, Any

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Get logger
logger = get_logger('main')

class PPTCreationAgent:
    def __init__(self):
        self.tools = [
            PPTOutlineTool(),
            UserInteractionTool(),
            PPTAddTool(),
            ImageSearchTool()
        ]
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.current_ppt_filename = None
        self.outline = None
        self.images = []
        
        # Initialize PPT Creation Agent
        self.agent = self._create_ppt_agent()
        
    def _create_ppt_agent(self) -> AgentExecutor:
        """创建PPT创建专用的Agent"""
        system_message = """你是一个专业的PPT创建助手。你的任务是按照以下流程创建PPT：
        1. 使用PPT大纲工具生成大纲
        2. 向用户确认大纲方案
        3. 创建PPT并添加内容
        4. 搜索并添加相关图片
        5. 每完成一个步骤都要向用户报告进度
        
        请严格按照这个流程执行，确保每个步骤都得到用户的确认。"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 将工具转换为OpenAI函数格式
        functions = [format_tool_to_openai_function(t) for t in self.tools]
        
        # 创建Agent
        agent = (
            {
                "input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_to_openai_function_messages(x["intermediate_steps"]),
                "chat_history": lambda x: x["chat_history"],
            }
            | prompt
            | INTENT_MODEL.bind(functions=functions)
            | OpenAIFunctionsAgentOutputParser()
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True
        )
    
    async def create_ppt(self, topic: str) -> Dict[str, Any]:
        """执行PPT创建流程"""
        try:
            # 1. Generate outline
            outline_result = await self.agent.ainvoke({
                "input": f"Please generate a PPT outline for topic '{topic}'"
            })
            self.outline = outline_result.get("output")
            
            # 2. User confirmation
            confirmation = await self.agent.ainvoke({
                "input": f"I have prepared a PPT plan for {topic}. Details: {self.outline}. Do you agree with this plan?"
            })
            
            if "不同意" in confirmation.get("output", "").lower():
                return {"success": False, "message": "用户不同意当前方案"}
            
            # 3. Create PPT
            ppt_result = await self.agent.ainvoke({
                "input": f"创建关于{topic}的演示文稿，使用以下大纲：{self.outline}"
            })
            
            # 4. Search and add images
            for section in self.outline.get("sections", []):
                image_result = await self.agent.ainvoke({
                    "input": f"搜索与'{section['title']}'相关的图片"
                })
                if image_result.get("success"):
                    self.images.extend(image_result.get("images", []))
            
            return {
                "success": True,
                "message": "PPT创建完成",
                "outline": self.outline,
                "images": self.images
            }
            
        except Exception as e:
            logger.error(f"PPT创建过程出错: {str(e)}")
            return {"success": False, "message": f"错误: {str(e)}"}

async def main():
    # Initialize tools
    tools = [
        PPTAddTool(),
        PPTRemoveTool(),
        PPTUpdateTool(),
        DataAnalysisTool(),
        PPTOutlineTool(),
        UserInteractionTool(),
        ResponseAnalysisTool(),
        ImageSearchTool()
    ]
    
    logger.info("Tools initialized")
    
    # Initialize memory manager for long-term knowledge
    memory_manager = MemoryManager()
    logger.info("Long-term memory manager initialized")
    
    # Initialize conversation memory for short-term context
    conversation_memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    logger.info("Conversation memory initialized")
    
    # Initialize user profile manager
    userProfileManager = UserProfileManager()
    logger.info("User profile manager initialized")
    
    # Initialize PPT creation agent
    ppt_agent = PPTCreationAgent()
    logger.info("PPT creation agent initialized")
    
    # Initialize planning agent with memory
    systemMessage = """You are a smart assistant that helps users complete various tasks. You can create presentations, analyze data, and have daily conversations. You can access conversation history to provide more context and personalized responses.
As a planner, you need to:
1. Analyze user needs and create execution plan
2. Determine each step's operation
3. Decide when to require user input
4. Determine next step based on execution result
5. Wait for user interaction in the first conversation

Execution rules:
1. Report result after each tool call, wait for user confirmation before proceeding to the next step
2. Request user help if there's a problem, maintain a professional and friendly tone

===== PPT Creation Process =====
1. Generate outline: Use the PPT outline tool to generate a PPT outline
2. User confirmation: Use the user interaction tool to confirm with the user, format: user_interaction_tool ("I have prepared a PPT plan for [topic], [number of chapters] chapters and corresponding images. Details: [plan details]. Do you agree with this plan?")
3. Create PPT: Format: ppt_add_tool ("Create a presentation about [topic]"), report progress after each completed slide
"""
    
    # Initialize agent with updated OpenAI model
    agent = initialize_agent(
        tools,
        INTENT_MODEL,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        system_message=systemMessage,
        memory=conversation_memory,
        handle_parsing_errors=True
    )
    logger.info("Planning agent initialized")
    
    print("Welcome to J-A-R-V-I-S AI Assistant! Type 'exit' to end the conversation.")
    
    # Get initial user input
    logger.info("Waiting for initial user input")
    userInput = await tools[5]._arun("What can I help you with today?")
    
    while True:
        if userInput.lower() in ['exit', 'quit', 'bye']:
            logger.info("User requested exit")
            print("J-A-R-V-I-S: Thank you for using the AI Assistant, goodbye!")
            break
        
        # First check if user input contains personal information
        logger.info("Checking if user input contains personal information")
        if await userProfileManager.is_user_profile_info(userInput):
            success = await userProfileManager.save_user_profile(userInput)
            if success:
                logger.info("Successfully saved user profile information")
                print("------------User information saved---------------")
                userInput = await tools[5]._arun("Information saved. Do you need anything else?")
                continue
        
        # Check if the request is PPT-related
        if "ppt" in userInput.lower() or "presentation" in userInput.lower() or "slide" in userInput.lower():
            # Extract topic from user input
            topic = userInput.replace("create", "").replace("ppt", "").replace("presentation", "").strip()
            if not topic:
                userInput = await tools[5]._arun("Please tell me what topic you want to create a PPT about?")
                continue
                
            # Use PPT creation agent
            result = await ppt_agent.create_ppt(topic)
            if result["success"]:
                userInput = await tools[5]._arun("PPT creation completed! Do you need any other help?")
            else:
                userInput = await tools[5]._arun(f"Sorry, there was a problem during PPT creation: {result['message']}. Please tell me how you would like to proceed?")
            continue
        
        # Check for relevant information in long-term memory system
        logger.info(f"Searching relevant long-term memories, user input: {userInput}")
        relevantMemories = await memory_manager.get_relevant_memories(userInput)
        memoryContext = "\n".join([doc.page_content for doc in relevantMemories]) if relevantMemories else ""
        logger.info(f"Found {len(relevantMemories)} relevant long-term memories")
        
        try:
            # Build enhanced input
            context = []
            if memoryContext:
                context.append(f"Historical information: {memoryContext}")
            if chat_history := conversation_memory.chat_memory.messages:
                context.append(f"Conversation history: {chat_history[-1].content}")
            
            enhancedInput = f"{' | '.join(context)} | Current input: {userInput}" if context else userInput
            logger.info(f"Enhanced input content: {enhancedInput}")
            
            # Use agent to process request
            response = await agent.ainvoke(enhancedInput)
            logger.info(f"Agent response: {response['output']}")
            print(f"J-A-R-V-I-S: {response['output']}")
            
            # Analyze response and decide next steps
            analysisInput = json.dumps({
                "response": response['output'],
                "user_input": userInput
            })
            
            logger.info(f"Input sent to ResponseAnalysisTool: {analysisInput}")
            
            try:
                analysisResult = await tools[6]._arun(analysisInput)
                logger.info(f"ResponseAnalysisTool raw output: {analysisResult}")
                
                try:
                    analysis = json.loads(analysisResult)
                    logger.info(f"Analysis result: {analysis}")
                    
                    if analysis.get("needs_continuation", False):
                        logger.info("Need to continue execution")
                        continue
                    elif analysis.get("needs_user_input", False):
                        logger.info(f"Need user input, prompt: {analysis.get('next_prompt', '')}")
                        userInput = await tools[5]._arun(analysis.get("next_prompt", "Please provide more information:"))
                    else:
                        logger.info("Task completed, waiting for new user input")
                        userInput = await tools[5]._arun("Task completed. Do you need anything else?")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON error when parsing ResponseAnalysisTool output: {str(e)}")
                    userInput = await tools[5]._arun("I seem to have encountered some technical issues. Could you please describe your needs again?")
            except Exception as e:
                logger.error(f"Error analyzing response: {str(e)}")
                userInput = await tools[5]._arun("Sorry, I encountered some issues during processing. Please describe your needs again:")
        except Exception as e:
            logger.error(f"Error during execution: {str(e)}")
            userInput = await tools[5]._arun("Sorry, I encountered some issues during processing. Please describe your needs again:")

if __name__ == "__main__":
    asyncio.run(main()) 