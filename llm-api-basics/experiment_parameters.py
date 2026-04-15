# experiment_parameters.py
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def make_api_call(model, temperature, max_tokens, message):
    """Make an API call with specific parameters"""

    print(f"\n{'=' * 60}")
    print(f"MODEL: {model}")
    print(f"TEMPERATURE: {temperature}")
    print(f"MAX_TOKENS: {max_tokens}")
    print(f"{'=' * 60}\n")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": message}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    print(f"RESPONSE:\n{response.choices[0].message.content}\n")
    print(f"TOKENS USED: {response.usage.total_tokens}")
    print(f"{'=' * 60}\n")


# Test different parameters
question = "Explain Article 21 in simple terms"

# Experiment 1: Different models
print("\n🧪 EXPERIMENT 1: Different Models\n")
make_api_call("llama-3.3-70b-versatile", 0.7, 150, question)
make_api_call("llama-3.1-8b-instant", 0.7, 150, question)

# Experiment 2: Different temperatures
print("\n🧪 EXPERIMENT 2: Different Temperatures\n")
make_api_call("llama-3.3-70b-versatile", 0.0, 150, question)  # Very focused
make_api_call("llama-3.3-70b-versatile", 1.0, 150, question)  # More creative
make_api_call("llama-3.3-70b-versatile", 2.0, 150, question)  # Very random

# Experiment 3: Different max_tokens
print("\n🧪 EXPERIMENT 3: Different Max Tokens\n")
make_api_call("llama-3.3-70b-versatile", 0.7, 50, question)  # Short answer
make_api_call("llama-3.3-70b-versatile", 0.7, 300, question)  # Long answer
