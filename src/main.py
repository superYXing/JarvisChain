import asyncio
import json
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage, HumanMessage
from src.models.llm_models import INTENT_MODEL
from src.tools.ppt_tool import PPTTool
from src.tools.data_analysis_tool import DataAnalysisTool
from src.tools.chat_tool import ChatTool
from src.tools.user_interaction_tool import UserInteractionTool
from src.tools.response_analysis_tool import ResponseAnalysisTool
from src.utils.user_profile import UserProfileManager
from src.utils.logger import get_logger
from src.database.vector_store import VectorStore

# Get logger
logger = get_logger('main')

async def classify_intent(user_input: str) -> int:
    """Classify user intent and return tool ID: 1(PPT) or 2(Data Analysis)"""
    system_prompt = """You are a user intent classifier. Analyze the user input and determine which category it belongs to:
1: PPT Creation - All requests related to creating, designing, or modifying presentations
2: Data Analysis - All requests related to data processing, analysis, visualization, or information search
3: Other - All requests that don't fall into the above categories
Return only the number 1, 2, or 3, with no other output."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    response = await INTENT_MODEL.ainvoke(messages)
    
    try:
        intent_id = int(response.content.strip())
        return intent_id if intent_id in [1, 2, 3] else 3
    except:
        return 3

async def main():
    # Initialize tools
    tools = [
        PPTTool(),
        DataAnalysisTool(),
        ChatTool(),
        UserInteractionTool(),
        ResponseAnalysisTool()
    ]
    
    # Initialize user profile manager
    user_profile_manager = UserProfileManager()
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Initialize planning agent
    system_message = """You are an intelligent assistant that can help users complete various tasks.
You can create presentations, analyze data, and engage in daily conversations.

As a planner, you need to:
1. Analyze user requirements and create execution plans
2. Determine what operations to perform at each step
3. Judge whether user input is needed
4. Decide next steps based on execution results

Available tools:
- ppt_tool: For creating and editing PPTs
- data_analysis_tool: For data analysis and visualization
- chat_tool: For daily conversations
- user_interaction: Use when user input is needed
- response_analysis_tool: Analyze conversations and decide next steps

Execution rules:
1. After each execution, analyze results and decide next steps
2. If user input is needed, use the user_interaction tool
3. If task is complete, return final results
4. If problems occur, try alternative solutions or request user help

Maintain a professional and friendly tone.
If you discover user profile information, save it for future reference."""
    
    agent = initialize_agent(
        tools,
        INTENT_MODEL,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        system_message=system_message
    )
    
    logger.info("Welcome to the intelligent assistant! Type 'exit' to end the conversation.")
    
    # Initial greeting
    initial_response = await agent.arun("Greet the user and ask what you can help them with today.")
    logger.info(f"Assistant's response: {initial_response}")
    
    # Get initial user input
    user_input = await tools[3]._arun("How can I help you today?")
    
    while True:
        if user_input.lower() in ['exit', 'quit', 'bye']:
            logger.info("Assistant: Thank you for using the intelligent assistant, goodbye!")
            break
        
        # Retrieve relevant historical information
        relevant_memories = vector_store.search(user_input, k=3)
        memory_context = "\n".join([doc.page_content for doc in relevant_memories]) if relevant_memories else ""
        
        # Check user profile information
        if await user_profile_manager.is_user_profile_info(user_input):
            success = await user_profile_manager.save_user_profile(user_input)
            if success:
                logger.info("User profile information saved")
        
        try:
            # Build input with historical context
            enhanced_input = f"{memory_context}\n\nCurrent user input: {user_input}" if memory_context else user_input
            
            # Let AI plan and execute tasks
            response = await agent.arun(enhanced_input)
            logger.info(f"Assistant's response: {response}")
            
            # Save conversation to vector database
            conversation = f"User: {user_input}\nAssistant: {response}"
            vector_store.add_document(conversation)
            
            # Analyze response and decide next steps
            analysis_input = json.dumps({
                "response": response,
                "user_input": user_input
            })
            analysis_result = await tools[4]._arun(analysis_input)
            analysis = json.loads(analysis_result)
            
            if analysis["needs_continuation"]:
                # Continue execution without user input
                continue
            elif analysis["needs_user_input"]:
                # Need user input
                user_input = await tools[3]._arun(analysis["next_prompt"])
            else:
                # Task complete, wait for new user input
                user_input = await tools[3]._arun("Is there anything else I can help you with?")
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            logger.info("Assistant: Sorry, I encountered some problems. Could you please describe your needs again?")
            user_input = await tools[3]._arun("Please describe your needs again:")

if __name__ == "__main__":
    asyncio.run(main()) 