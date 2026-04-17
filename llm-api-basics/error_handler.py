import time
from groq import APIError, RateLimitError, Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def safe_api_call(message, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message}],
                temperature=1.5,
                max_tokens=100,
                top_p=0.9,
            )
            return response
        except RateLimitError as e:
            print(f"Rate limit hit: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except APIError as e:
            print(f"API error: {e}, retrying in 5 seconds...")
            time.sleep(5)
    print("Max retries reached. API call failed.")


message = "What is the capital of France? why?"
response = safe_api_call(message)
if response:
    print(f"Response: {response.choices[0].message.content}")
