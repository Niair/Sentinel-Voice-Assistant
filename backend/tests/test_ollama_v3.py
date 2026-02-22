from typing import TypedDict
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph

# 1️⃣ Define proper state schema
class State(TypedDict):
    input: str
    output: str

# 2️⃣ Load model
llm = OllamaLLM(model="qwen3-coder:480b-cloud")

# 3️⃣ Node function
def chatbot(state: State):
    response = llm.invoke(state["input"])
    return {"output": response}

# 4️⃣ Build graph
graph = StateGraph(State)

graph.add_node("chatbot", chatbot)
graph.set_entry_point("chatbot")
graph.set_finish_point("chatbot")

app = graph.compile()

# 5️⃣ Run
result = app.invoke({"input": "Explain RAG in 3 lines"})
print(result)