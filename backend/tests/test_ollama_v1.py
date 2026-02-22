import requests

url = "http://localhost:11434/api/generate"

data = {
    "model": "qwen3-coder:480b-cloud",
    "prompt": "Explain recursion in simple words.",
    "stream": False
}

response = requests.post(url, json=data)

print(response.json())