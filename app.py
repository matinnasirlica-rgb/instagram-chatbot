import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = "mytoken123"
APP_ID = "1627023788534334"
APP_SECRET = "2ef1f9302bab0cabbfa489ed08968f9b"
GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = "Sen Instagram-da bir chatbot-san. İstifadəçilərlə təbii, mehriban şəkildə söhbət edirsən. Qısa cavablar ver. Azərbaycan dilində cavab ver."

conversation_history = {}


def get_token():
    """Render Environment-dən token al"""
    return os.environ.get("PAGE_ACCESS_TOKEN", "")


def get_ai_response(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    conversation_history[user_id].append({
        "role": "user",
        "content": user_message
    })

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": conversation_history[user_id][-10:],
                "max_tokens": 500
            },
            timeout=30
        )
        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]

        conversation_history[user_id].append({
            "role": "assistant",
            "content": ai_reply
        })

        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = [conversation_history[user_id][0]] + conversation_history[user_id][-19:]

        return ai_reply

    except Exception as e:
        print(f"❌ Groq xətası: {e}")
        return "Bağışla, cavab verə bilmirəm. Bir az sonra yaz! 🙏"


def send_instagram_message(recipient_id: str, message: str):
    token = get_token()
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    result = response.json()
    print(f"📤 Göndərildi: {result}")

    if "error" in result:
        code = result["error"].get("code")
        print(f"❌ TOKEN XƏTASI (kod {code}) — Render-də PAGE_ACCESS_TOKEN yenilə!")

    return result


@app.route("/", methods=["GET"])
def health_check():
    return "OK", 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook doğrulandı!")
        return challenge, 200
    return "Xəta", 403


@app.route("/webhook", methods=["POST"])
def handle_message():
    data = request.get_json()
    print(f"📥 Gələn data: {data}")
    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging["sender"]["id"]
                if "message" in messaging and "text" in messaging["message"]:
                    user_message = messaging["message"]["text"]
                    print(f"📩 ({sender_id}): {user_message}")
                    ai_reply = get_ai_response(sender_id, user_message)
                    print(f"🤖 AI: {ai_reply}")
                    send_instagram_message(sender_id, ai_reply)
    except Exception as e:
        print(f"❌ Xəta: {e}")
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
