import os
import asyncio
from typing import Annotated, TypedDict, Union
from dotenv import load_dotenv

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# Load environment variables
load_dotenv()

# --- 1. Define Tools ---
@tool
def get_weather(location: str):
    """Get the current weather for a specific location."""
    return f"The weather in {location} is currently sunny and 25°C."

@tool
def get_current_time() -> str:
    """Get the exact current local date and time."""
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

tools = [get_weather, get_current_time]
tool_node = ToolNode(tools)

# --- 2. Define State ---
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# --- 3. Define the Agent ---
async def call_model(state: State):
    api_key = os.getenv("NVEDIAKIMIK2_API_KEY")
    model_name = "moonshotai/kimi-k2-thinking" 
    
    # Simulate System Prompt Injection (like main app)
    from datetime import datetime
    current_time_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    system_instruction = f"""
    You are a helpful assistant.
    Current Date & Time: {current_time_str}
    
    Use the get_current_time tool only if you need to double check.
    """
    
    # Prepend system message if not present
    input_messages = state["messages"]
    if not isinstance(input_messages[0], BaseMessage) or input_messages[0].type != "system":
        from langchain_core.messages import SystemMessage
        input_messages = [SystemMessage(content=system_instruction)] + input_messages

    # Initialize the NVIDIA model
    llm = ChatNVIDIA(
        model=model_name,
        nvidia_api_key=api_key,
        temperature=0.7,
        max_completion_tokens=4096
    ).bind_tools(tools)
    
    response = await llm.ainvoke(input_messages)
    return {"messages": [response]}

# --- 4. Build the Graph ---
workflow = StateGraph(State)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

app = workflow.compile()

# --- 5. Run the Test ---
async def run_test():
    print("=" * 70)
    print("NVIDIA NIM + LANGGRAPH INTEGRATION TEST")
    print(f"Model: moonshotai/kimi-k2-thinking")
    print("=" * 70)

    # Question that triggers both reasoning and a tool call
    inputs = {
        "messages": [
            HumanMessage(content="What is the weather in India right now and waht is the current date? Please think through your response step-by-step.")
        ]
    }

    print("🔄 Streaming Graph Execution...\n")
    
    async for event in app.astream(inputs, stream_mode="values"):
        last_message = event["messages"][-1]
        
        if isinstance(last_message, AIMessage):
            print(f"\n--- [AI MESSAGE] ---")
            # NVIDIA reasoning models often include thoughts in the content
            # or in a separate field depending on the specific NIM implementation.
            # Most standard LangChain implementations put the whole response in .content
            print(f"Content:\n{last_message.content}")
            
            if last_message.tool_calls:
                print(f"Tool Calls: {last_message.tool_calls}")
        
        elif isinstance(last_message, HumanMessage):
            print(f"--- [USER MESSAGE] ---\n{last_message.content}")
            
    print("\n" + "=" * 70)
    print("✅ Integration test completed!")

if __name__ == "__main__":
    asyncio.run(run_test())
