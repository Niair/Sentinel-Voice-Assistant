from langchain_ollama import OllamaLLM

llm = OllamaLLM(
    model="qwen3-coder:480b-cloud"
)

response = llm.invoke("What is dynamic programming?")

print(response)