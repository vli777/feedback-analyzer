import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Base LLM client for NVIDIA API
base_client = ChatNVIDIA(
    model="meta/llama-3.2-3b-instruct",
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=0.2,
    top_p=0.7,
    max_tokens=1024,
)

# Legacy client for backwards compatibility
client = base_client
