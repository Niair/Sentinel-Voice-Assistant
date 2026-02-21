import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama           # preferred per warning
from langchain_core.messages import HumanMessage

load_dotenv()

llm = ChatOllama(
    model="qwen3.5:cloud",
    base_url="https://api.ollama.ai",
    headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"}
)

resp = llm.invoke([HumanMessage(content="Hello!")])
print(resp.content)