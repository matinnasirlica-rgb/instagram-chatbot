import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== KONFIQURASIYA ==========
VERIFY_TOKEN = "mytoken123"
INSTAGRAM_TOKEN = "IGAAN0h2810oRBZAGJmdUpQOVdtdWdURkFtVTBFckl2QlpuRFBzWE53YXBvaDRqY0pPVnhxOWNQMzJ2QXlJSHNfendQbWNoRHpSY2d5dldOdkxoWkFiOWZA2V0hpQ1BDWTNFWGhHeEdweTFzNUxrcVBkNV9xM2g3Yms5ZAXhIWFRSZAwZDZD"
PAGE_ACCESS_TOKEN = "EAAXHxP706j4BRGno6HALEXcW6xlZCfS4AwDZBNJtUXoI7gsZAtcqskV4oop0OkvdMZAjKBLPdeiEPTKnjj0q61YhHd6g7Cvf1aZCMmHOZCLVt27gGkdidUi0hR7tJKrUE8uxdqWqUCpBilWs03UNZAMjBQ5ElllPnZB2ZABX9BTKPByr2CqaNbrjw4Wkrs5GdECMY"
FACEBOOK_PAGE_ID = "113851988486996"
INSTAGRAM_ACCOUNT_ID = "17841442893592153"
GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# ===================================

SYSTEM_PROMPT = "Sen Instagram-da bir chatbot-san. İstifadəçilərlə təbii, mehriban şəkildə söhbət edirsən. Qısa cavablar ver. Azərbaycan dilində cavab ver."

conversation_history = {}


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
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }

    # 1. IGAAN token + Instagram Account ID
    url1 = f"https://graph.facebook.com/v21.0/{INSTAGRAM_ACCOUNT_ID}/messages"
    r1 = requests.post(url1, json=payload, headers={"Authorization": f"Bearer {INSTAGRAM_TOKEN}", "Content-Type": "application/json"})
    result1 = r1.json()
    print(f"📤 Cəhd 1 (IGAAN+IG_ID): {result1}")
    if "error" not in result1:
        return result1

    # 2. Page token + Instagram Account ID
    r2 = requests.post(url1, json=payload, headers={"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}", "Content-Type": "application/json"})
    result2 = r2.json()
    print(f"📤 Cəhd 2 (PAGE+IG_ID): {result2}")
    if "error" not in result2:
        return result2

    # 3. Page token + Facebook Page ID
    url3 = f"https://graph.facebook.com/v21.0/{FACEBOOK_PAGE_ID}/messages"
    r3 = requests.post(url3, json=payload, headers={"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}", "Content-Type": "application/json"})
    result3 = r3.json()
    print(f"📤 Cəhd 3 (PAGE+FB_ID): {result3}")
    return result3


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
