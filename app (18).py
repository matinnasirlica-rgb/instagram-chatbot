import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = "mytoken123"
INSTAGRAM_TOKEN = "IGAAN0h2810oRBZAGJmdUpQOVdtdWdURkFtVTBFckl2QlpuRFBzWE53YXBvaDRqY0pPVnhxOWNQMzJ2QXlJSHNfendQbWNoRHpSY2d5dldOdkxoWkFiOWZA2V0hpQ1BDWTNFWGhHeEdweTFzNUxrcVBkNV9xM2g3Yms1ZAXhIWFRSZAwZDZD"
INSTAGRAM_ACCOUNT_ID = "17841442893592153"
INSTAGRAM_APP_ID = "972549965337220"
INSTAGRAM_APP_SECRET = "e2af211a3332ca0bb6c0a99bbd1202eb"
GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = "Sen Instagram-da bir chatbot-san. İstifadəçilərlə təbii, mehriban şəkildə söhbət edirsən. Qısa cavablar ver. Azərbaycan dilində cavab ver."

conversation_history = {}
current_token = {"value": INSTAGRAM_TOKEN}


def refresh_instagram_token():
    """Instagram tokenini avtomatik yenilə"""
    try:
        url = "https://graph.instagram.com/refresh_access_token"
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": current_token["value"]
        }
        response = requests.get(url, params=params)
        result = response.json()
        print(f"🔄 Token yeniləndi: {result}")
        if "access_token" in result:
            current_token["value"] = result["access_token"]
            print("✅ Yeni token alındı!")
        else:
            print(f"❌ Token yenilənmədi: {result}")
    except Exception as e:
        print(f"❌ Token yeniləmə xətası: {e}")


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
    url = f"https://graph.instagram.com/v21.0/{INSTAGRAM_ACCOUNT_ID}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }
    headers = {
        "Authorization": f"Bearer {current_token['value']}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    result = response.json()
    print(f"📤 Göndərildi: {result}")

    # Token bitibsə yenilə
    if "error" in result and result["error"].get("code") == 190:
        print("🔄 Token bitib, yenilənir...")
        refresh_instagram_token()
        headers["Authorization"] = f"Bearer {current_token['value']}"
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Yenidən göndərildi: {response.json()}")

    return result


@app.route("/", methods=["GET"])
def health_check():
    return "OK", 200


@app.route("/refresh", methods=["GET"])
def manual_refresh():
    refresh_instagram_token()
    return jsonify({"status": "ok"}), 200


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
