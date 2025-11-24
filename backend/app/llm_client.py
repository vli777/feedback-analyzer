import os
# from openai import OpenAI
#
# client = OpenAI(
#     api_key=os.getenv("NVIDIA_API_KEY"),
#     base_url="https://integrate.api.nvidia.com/v1"
# )

from langchain_nvidia_ai_endpoints import ChatNVIDIA

client = ChatNVIDIA(
    model="meta/llama-3.2-3b-instruct",
    api_key=os.getenv("NVIDIA_API_KEY"),
    temperature=0.2,
    top_p=0.7,
    max_tokens=1024,
)
