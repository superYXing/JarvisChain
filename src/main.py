import asyncio
import json
import warnings
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage, HumanMessage
from src.models.llm_models import INTENT_MODEL
from tools.ppt_tool import PPTTool
from src.tools.data_analysis_tool import DataAnalysisTool
from src.tools.chat_tool import ChatTool
from src.tools.user_interaction_tool import UserInteractionTool
from src.tools.response_analysis_tool import ResponseAnalysisTool
from src.utils.user_profile import UserProfileManager
from src.utils.logger import get_logger
from src.database.vector_store import VectorStore

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Get logger
logger = get_logger('main')

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
1. Analyze user requirements and create execution plans, may be more than onoe tools needed to be used
2. Determine what operations to perform at each step
3. Judge whether user input is needed, 
If it's just a simple greeting like "hello" or "hi", there's no need to call any tools.
4. Decide next steps based on execution results
5.Please wait user's interaction at the first chat.
Available tools:
- ppt_tool: For creating and editing, optimizing PPTs
- data_analysis_tool: For data analysis and visualization
- chat_tool: For daily conversations
- user_interaction: Use when user input is needed, Only complex tasks like creating PowerPoint presentations or gathering research materials require confirming details with users.
- response_analysis_tool: Analyze conversations and decide next steps, Only complex tasks like creating PowerPoint presentations or gathering research materials require confirming details with users.

Execution rules:
1. After each execution, analyze results and decide next steps
2. First, check for the availability of Chroma and UserProfileManager
. If both are found, invoke UserProfileManager; otherwise, utilize the UserInteraction tool.
3. If task is complete, return final results
4. If problems occur, try alternative solutions or request user help
5. For simple greetings like 'hello', 'hi', or casual phrases, do not invoke any tools or generate detailed responses.
   Just return a brief polite acknowledgment using natural language.

6. Maintain a professional and friendly tone.
7. If you discover user profile information, save it for future reference.

PPT Creation Guidelines:
1. When creating a presentation:
   - First, gather all necessary information using data_analysis_tool
   - Create an outline of the presentation structure
   - Confirm the outline with the user using user_interaction_tool
   - Create slides one by one using ppt_tool
   - After each major section, confirm with the user

2. For each slide:
   - Use appropriate layouts (title, content, image, etc.)
   - Add text with proper formatting (size, color, alignment)
   - Include relevant images when needed
   - Use shapes for visual elements
   - Maintain consistent styling

3. PPT Creation Process:
   a. Initial Planning:
      - Analyze user requirements
      - Research topic using data_analysis_tool
      - Create presentation outline
      - Get user confirmation

   b. Content Creation:
      - Create title slide
      - Add content slides
      - Insert images and shapes
      - Format text and elements
      - Save progress regularly

   c. Review and Refinement:
      - Show progress to user
      - Get feedback
      - Make necessary adjustments
      - Finalize presentation

4. Best Practices:
   - Keep slides clean and uncluttered
   - Use consistent fonts and colors
   - Include relevant images and graphics
   - Maintain proper spacing and alignment
   - Save work frequently
   - Get user feedback at key points

Priorities:
1. UserInteractionTool()
2. ResponseAnalysisTool()
3. DataAnalysisTool()
4. PPTTool()
Note: Numbers represent priority levels (1 = highest, 5 = lowest).
"""
    
    agent = initialize_agent(
        tools,
        INTENT_MODEL,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        system_message=system_message
    )
    
    print("Welcome to the J-A-R-V-I-S intelligent assistant! Type 'exit' to end the conversation.")
    
    # Initial greeting
    initial_response = await agent.ainvoke("Greet the user and ask what you can help them with today.Then wait the user's interaction.")
    print(f"J-A-R-V-I-S: {initial_response['output']}")
    
    # Get initial user input
    user_input = await tools[3]._arun("How can I help you today?")
    
    while True:
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("J-A-R-V-I-S: Thank you for using the intelligent assistant, goodbye!")
            break
        
        # Retrieve relevant historical information
        relevant_memories = vector_store.search(user_input, k=3)
        memory_context = "\n".join([doc.page_content for doc in relevant_memories]) if relevant_memories else ""
        
        # todo: 判断用户画像改为一个tool
        # Check user profile information
        if await user_profile_manager.is_user_profile_info(user_input):
            success = await user_profile_manager.save_user_profile(user_input)
            if success:
                print("------------User profile information saved---------------")
        
        try:
            # Build input with historical context
            enhanced_input = f"{memory_context}\n\nCurrent user input: {user_input}" if memory_context else user_input
            
            # Let AI plan and execute tasks
            response = await agent.ainvoke(enhanced_input)
            #调试查看最终的input
            print(f"*******最终的input：*********{enhanced_input}")
            print(f"J-A-R-V-I-S: {response['output']}")
            
            # Save conversation to vector database
            conversation = f"User: {user_input}\nAssistant: {response['output']}"
            vector_store.add_document(conversation)
            
            # Analyze response and decide next steps
            analysis_input = json.dumps({
                "response": response['output'],
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
                user_input = await tools[3]._arun("This task has been completed. Is there anything else I can help you with?")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            print("J-A-R-V-I-S: Sorry, I encountered some problems. Could you please describe your needs again?")
            user_input = await tools[3]._arun("Please describe your needs again:")

if __name__ == "__main__":
    asyncio.run(main()) 