import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = "mytoken123"
PAGE_ACCESS_TOKEN = "IGAAN0h2810oRBZAGFWcHc4RzJMQW93ajM3dFRmdG9LbGVxdEdyT3VYSkhXMjZArMjdrRExOR291c2hPMXVQcWlOTzFnZA1Jvb1hnVld2blNvVWEwRl9NTnhJS3R1ZATVRZAjJhMjdpbFVGbW5JSmtuRXlsa29wR25JTmRyTXQ2M0xpbwZDZD"
GEMINI_API_KEY = "AIzaSyASp89UDVrgAC3Yg7UW6HnmRqiz1QdMAJ0"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

SYSTEM_PROMPT = "Sen Instagram-da bir chatbot-san. İstifadəçilərlə təbii, mehriban şəkildə söhbət edirsən. Qısa cavablar ver. Azərbaycan dilində cavab ver."

conversation_history = {}


def get_ai_response(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": conversation_history[user_id][-10:]
    }

    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=30)
        result = response.json()
        print(f"🔍 Gemini raw: {result}")

        if "candidates" in result:
            ai_reply = result["candidates"][0]["content"]["parts"][0]["text"]
            conversation_history[user_id].append({
                "role": "model",
                "parts": [{"text": ai_reply}]
            })
            if len(conversation_history[user_id]) > 20:
                conversation_history[user_id] = conversation_history[user_id][-20:]
            return ai_reply
        else:
            print(f"❌ Gemini xətası: {result}")
            return "Bağışla, cavab verə bilmirəm. Bir az sonra yaz! 🙏"
    except Exception as e:
        print(f"❌ Xəta: {e}")
        return "Bağışla, cavab verə bilmirəm. Bir az sonra yaz! 🙏"


def send_instagram_message(recipient_id: str, message: str):
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    headers = {
        "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(f"📤 Göndərildi: {response.json()}")
    return response.json()


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
