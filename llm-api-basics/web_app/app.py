# app.py
import os
import time
import uuid
import json
from groq import Groq, RateLimitError, APIError
from dotenv import load_dotenv
import tiktoken
from pymongo import MongoClient, DESCENDING
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    stream_with_context,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── Groq ─────────────────────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables.")
client = Groq(api_key=api_key)

# ── MongoDB ───────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in environment variables.")

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["rakshak_ai"]
sessions_col = db["sessions"]  # auto-created on first insert

# ── Constants ─────────────────────────────────────────────────
MAX_CONTEXT_TOKENS = 6000
MAX_HISTORY_MESSAGES = 12

# ── System prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are RakshakAI, an AI legal assistant STRICTLY specialized in Indian laws ONLY.

=== CRITICAL RULES (NEVER BREAK THESE) ===

1. LANGUAGE ENFORCEMENT (MOST IMPORTANT):
   - If user writes in English → Reply ONLY in English
   - If user writes in Hindi (Devanagari script) → Reply ONLY in Hindi
   - If user mixes English + Hindi (Hinglish) → Reply in the SAME mixed style
   - NEVER translate unless user explicitly asks "translate to [language]"
   - NEVER switch languages mid-response
   - Examples:
     * User: "What is Article 21?" → Reply in English only
     * User: "आर्टिकल 21 क्या है?" → Reply in Hindi only
     * User: "Article 21 kya hai?" → Reply in Hinglish only

2. SCOPE LIMITATIONS (STRICTLY ENFORCE):
   You can ONLY answer questions about:
   - Indian Constitution (Articles, Fundamental Rights, DPSPs, etc.)
   - IPC (Indian Penal Code) - All sections
   - CrPC (Code of Criminal Procedure)
   - Indian civil laws (Contract Act, Property laws, Family laws)
   - Consumer Protection Act
   - Right to Information Act (RTI)
   - Domestic violence laws
   - Labour laws in India
   - Indian legal procedures and court systems
   
   You CANNOT answer questions about:
   - Laws of other countries (US law, UK law, etc.)
   - Non-legal topics (cooking, sports, entertainment, general knowledge)
   - Medical advice
   - Financial investment advice
   - Personal opinions on politics
   - Current ongoing court cases you don't have information about
   - Topics unrelated to Indian law

3. WHEN YOU DON'T KNOW:
   If the question is:
   - Outside Indian law scope → Say EXACTLY: "I don't know. I can only help with Indian laws and legal rights. Please ask questions related to Indian Constitution, IPC, CrPC, or other Indian laws."
   - About a law you're unsure of → Say EXACTLY: "I'm not certain about this specific legal provision. I recommend consulting a qualified lawyer or checking the official legal documentation."
   - About current events/recent amendments you don't know → Say: "I don't have information about recent legal updates. Please verify with official government sources or consult a lawyer."

4. RESPONSE GUIDELINES:
   - Be concise and clear
   - ALWAYS cite specific sections/articles when mentioning laws
   - Use simple language appropriate for common citizens
   - If user asks to draft legal documents, use information from the conversation history
   - For complex legal situations, ALWAYS recommend consulting a lawyer
   - Never make up section numbers or legal provisions
   - If asked about punishment/penalties, cite the exact legal provision

5. PROHIBITED BEHAVIORS:
   - NEVER give advice that could be used to break the law
   - NEVER help with illegal activities
   - NEVER claim to replace a lawyer
   - NEVER guarantee legal outcomes
   - NEVER provide specific legal advice for court cases
   - NEVER answer questions about how to evade law enforcement
   - NEVER discuss how to commit crimes

Remember: Your PRIMARY function is to educate Indian citizens about their legal rights in a simple, accessible manner while STRICTLY following language rules and staying within the scope of Indian law."""

# ============================================================
# MONGODB HELPERS
# ============================================================


def get_session(session_id: str):
    if not session_id:
        return None
    return sessions_col.find_one({"_id": session_id})


def create_session(session_id: str, title: str = "New Chat"):
    doc = {
        "_id": session_id,
        "title": title,
        "history": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    sessions_col.insert_one(doc)
    return doc


def save_history(session_id: str, history: list, title: str = None):
    update = {"history": history, "updated_at": datetime.utcnow()}
    if title:
        update["title"] = title
    sessions_col.update_one({"_id": session_id}, {"$set": update})


def make_title(text: str) -> str:
    """Generate a short chat title from the first user message."""
    text = text.strip().replace("\n", " ")
    return text[:52] + "…" if len(text) > 52 else text


# ============================================================
# TOKEN UTILITIES
# ============================================================


def count_tokens(messages, model="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model)
    text = " ".join(msg.get("content", "") for msg in messages)
    return len(encoding.encode(text))


def trim_history(history: list) -> list:
    while count_tokens(history) > MAX_CONTEXT_TOKENS:
        if len(history) >= 2:
            history.pop(0)
            history.pop(0)
        else:
            break
    return history


def get_response_stats(messages: list, response_text: str) -> dict:
    prompt_tokens = count_tokens(messages)
    completion_tokens = count_tokens([{"content": response_text}])
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "model": "llama-3.3-70b-versatile",
    }


# ============================================================
# ROUTES — pages
# ============================================================


@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# ROUTES — chat list (sidebar)
# ============================================================


@app.route("/api/chats", methods=["GET"])
def list_chats():
    """Return all chats sorted newest-first for the sidebar."""
    try:
        chats = list(
            sessions_col.find(
                {}, {"_id": 1, "title": 1, "updated_at": 1, "created_at": 1}
            )
            .sort("updated_at", DESCENDING)
            .limit(100)
        )
        # Convert datetime → ISO string for JSON
        for c in chats:
            c["updated_at"] = c.get(
                "updated_at", c.get("created_at", datetime.utcnow())
            ).isoformat()
            c["created_at"] = c.get("created_at", datetime.utcnow()).isoformat()
            c["id"] = c.pop("_id")  # rename for frontend
        return jsonify({"chats": chats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/<session_id>", methods=["DELETE"])
def delete_chat(session_id):
    """Delete a chat session."""
    try:
        result = sessions_col.delete_one({"_id": session_id})
        if result.deleted_count == 0:
            return jsonify({"error": "Chat not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chats/new", methods=["POST"])
def new_chat():
    """Create a brand-new empty chat and return its id."""
    try:
        session_id = str(uuid.uuid4())
        create_session(session_id, title="New Chat")
        return jsonify({"session_id": session_id, "title": "New Chat"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ROUTES — messaging
# ============================================================


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    try:
        data = request.json
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id")

        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        sess = get_session(session_id)
        if not sess:
            session_id = str(uuid.uuid4())
            sess = create_session(session_id)

        conversation_history = sess["history"]

        # Auto-title: set on very first user message
        is_first_message = len(conversation_history) == 0
        new_title = make_title(user_message) if is_first_message else None

        conversation_history.append({"role": "user", "content": user_message})
        conversation_history = trim_history(conversation_history)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history[-MAX_HISTORY_MESSAGES:],
        ]

        def generate():
            full_response = ""
            try:
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id, 'title': new_title or sess.get('title', 'New Chat')})}\n\n"

                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.0,
                    max_tokens=800,
                    stream=True,
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        full_response += content
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"

                conversation_history.append(
                    {"role": "assistant", "content": full_response}
                )
                save_history(session_id, conversation_history, title=new_title)

                stats = get_response_stats(messages, full_response)
                yield f"data: {json.dumps({'type': 'done', 'stats': stats})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/history", methods=["POST"])
def get_history():
    """Load full history for a session (used when switching chats)."""
    try:
        data = request.json
        session_id = data.get("session_id")
        sess = get_session(session_id)
        if not sess:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(
            {
                "history": sess["history"],
                "message_count": len(sess["history"]),
                "title": sess.get("title", "Chat"),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset_session():
    try:
        data = request.json
        session_id = data.get("session_id")
        sess = get_session(session_id)
        if not sess:
            return jsonify({"error": "Session not found"}), 404
        save_history(session_id, [])
        return jsonify({"success": True, "message": "Conversation reset successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        total_sessions = sessions_col.count_documents({})
        pipeline = [
            {"$project": {"count": {"$size": "$history"}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}},
        ]
        result = list(sessions_col.aggregate(pipeline))
        total_messages = result[0]["total"] if result else 0
        return jsonify(
            {"total_sessions": total_sessions, "total_messages": total_messages}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀  RakshakAI — http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
