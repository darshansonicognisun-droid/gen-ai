from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def make_api_call(temperature, message):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": message}],
        temperature=temperature,
    )

    print(f"RESPONSE:\n{response.choices[0].message.content}\n")
    print(f"{'=' * 60}\n")


make_api_call(0.0, "My name is darshan, what is my name?")
make_api_call(1.5, "My name is darshan, what is my name?")
