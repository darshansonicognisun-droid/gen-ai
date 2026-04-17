import os
import time
from groq import Groq, RateLimitError, APIError
from dotenv import load_dotenv
import tiktoken

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client with API key and rate limiter
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables.")

client = Groq(api_key=api_key)
max_context_tokens = 6000

# System prompt for the chatbot
SYSTEM_PROMPT = """You are RakshakAI, an AI assistant specialized in Indian laws and legal information.
Your goal is to educate Indian citizens about their legal rights and laws in simple language.

Guidelines:
1. Language Rules (STRICT):
   - If user asks in English → reply ONLY in English
   - If user asks in Hindi → reply ONLY in Hindi
   - Use Hinglish ONLY if user mixes both languages
   - Do NOT translate unless user explicitly asks
2. Cite specific articles/sections when relevant
3. If unsure, say so and suggest consulting a lawyer
4. Focus on: Constitution, IPC, CrPC, Civil laws, Consumer rights
5. When asked to draft documents, use information from previous conversation
6. Maintain conversation context and refer back to earlier questions
"""

# 🆕 CONVERSATION HISTORY - This is the key!
conversation_history = []

# API call function with retry logic for rate limits and API errors


def chat(user_message, max_retries=3):
    """
    Send message to Groq API with full conversation history
    """
    # Add user message to history
    conversation_history.append({"role": "user", "content": user_message})

    # Build complete message list with system prompt + max 6 conversation history
    MAX_HISTORY = 6
    # 🔥 Trim history to fit within token limits before sending
    trim_history()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *conversation_history[-MAX_HISTORY:],  # 🔥 Include ONLY recent messages!
    ]

    for attempt in range(max_retries):
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
                temperature=0.0,
                max_tokens=300,
            )

            # Get assistant's response
            print("RakshakAI: ", end="", flush=True)
            full_response = ""

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
                    full_response += content
            print("\n")

            # Add assistant's response to history
            conversation_history.append({"role": "assistant", "content": full_response})

            get_response_stats(messages, full_response)  # Get stats about the response

            return full_response

        except RateLimitError as e:
            print(f"Rate limit hit. Retrying in {e.retry_after} seconds...")
            time.sleep(10)
        except APIError as e:
            print(f"API error: {e}. Retrying...")
            time.sleep(10)
        print("failed to get response after retries.")


# Utility function to reset conversation history
def reset_conversation():
    """Clear conversation history"""
    global conversation_history
    conversation_history = []
    print("✅ Conversation history cleared!")


# Utility function to count tokens in a text using tiktoken
def count_tokens(messages, model="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model)
    # 🔥 Convert messages list → single string
    text = ""
    for msg in messages:
        text += msg["content"] + " "

    tokens = encoding.encode(text)
    return len(tokens)


# Utility function to trim conversation history to fit within token limits
def trim_history():
    """Keep only recent messages within token limit"""
    while count_tokens(conversation_history) > max_context_tokens:
        # Remove oldest user-assistant pair
        if len(conversation_history) >= 2:
            conversation_history.pop(0)
            conversation_history.pop(0)
        else:
            break


# Utility function to get response statistics
def get_response_stats(messages, response_text, model="llama-3.3-70b-versatile"):
    prompt_tokens = count_tokens(messages)
    completion_tokens = count_tokens([{"content": response_text}])

    stats = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "model": model,
    }

    print(f"📊 Stats: {stats}")
    return stats


if __name__ == "__main__":
    print("=" * 70)
    print("🇮🇳 RakshakAI - Indian Law Chatbot")
    print("=" * 70)
    print("\nCommands:")
    print("  'exit' or 'quit' - End conversation")
    print("  'reset' - Clear conversation history")
    print("  'history' - Show conversation history")
    print("=" * 70)
    print()

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("\n👋 Thank you for using RakshakAI! See you soon!")
            break

        if user_input.lower() == "reset":
            reset_conversation()
            continue

        if user_input.lower() == "trim":
            trim_history()
            continue

        if user_input.lower() == "history":
            print("\n📜 Conversation History:")
            print("=" * 70)
            for i, msg in enumerate(conversation_history, 1):
                role = msg["role"].upper()
                content = (
                    msg["content"][:100] + "..."
                    if len(msg["content"]) > 100
                    else msg["content"]
                )
                print(f"{i}. {role}: {content}")
            print("=" * 70)
            continue

        answer = chat(user_input)
