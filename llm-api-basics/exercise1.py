from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def estimate_tokens(text):
    # Approx: 1 token ≈ 4 characters (simple rule)
    return len(text) // 4


def make_api_call(
    model, temperature, message, max_tokens, top_p, frequency_penalty, presence_penalty
):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
    except Exception as e:
        print(f"Error during API call: {e}")
        return

    print(f"{'=' * 60}")
    print(f"RESPONSE:\n{response.choices[0].message.content}\n")

    estimated_prompt_tokens = estimate_tokens(message)
    print(f"Estimated Prompt Tokens: {estimated_prompt_tokens}")

    actual_prompt_tokens = response.usage.prompt_tokens

    print(f"Actual Prompt Tokens: {actual_prompt_tokens}")
    print(f"Difference: {actual_prompt_tokens - estimated_prompt_tokens}\n\n")


message = "what is 2+4?"

make_api_call(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    message=message,
    max_tokens=1024,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
)

make_api_call(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    message=message,
    max_tokens=1024,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
)

make_api_call(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    message=message,
    max_tokens=1024,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
)
