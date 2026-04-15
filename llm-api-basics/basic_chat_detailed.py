# basic_chat_detailed.py
from groq import Groq
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "What is Article 21 of Indian Constitution?"}
    ],
)

# Print the ENTIRE response object
print("=" * 60)
print("FULL RESPONSE OBJECT")
print("=" * 60)
print(response)
print("\n")

# Print specific parts
print("=" * 60)
print("RESPONSE ID")
print("=" * 60)
print(response.id)
print("\n")

print("=" * 60)
print("MODEL USED")
print("=" * 60)
print(response.model)
print("\n")

print("=" * 60)
print("MESSAGE CONTENT (The AI's answer)")
print("=" * 60)
print(response.choices[0].message.content)
print("\n")

print("=" * 60)
print("TOKEN USAGE")
print("=" * 60)
print(f"Tokens in your question: {response.usage.prompt_tokens}")
print(f"Tokens in AI's answer: {response.usage.completion_tokens}")
print(f"Total tokens used: {response.usage.total_tokens}")
print("\n")

print("=" * 60)
print("FINISH REASON")
print("=" * 60)
print(response.choices[0].finish_reason)
print("(stop = completed naturally, length = hit max tokens)")
