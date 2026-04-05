import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# =============================================
# KONFIQURASIYA
# =============================================
VERIFY_TOKEN = "mytoken123"
PAGE_ACCESS_TOKEN = "IGAAN0h2810oRBZAFlBQ0RPa1VwTVE1YUxYVGxJbWJFZA3oxZAldDWURtOEJLRXlJYnAtcEZA4TG9ROHNSZADdfX0RnemxhQ1lVVWpvZAWFBUlBtM0VxUWtubWtDMWlfNThsaEg1UlBRaUZATaFMzOWl3bkduQmFIMmN5dTV5Y0tCdUQtcwZDZD"
GEMINI_API_KEY = "AIzaSyASp89UDVrgAC3Yg7UW6HnmRqiz1QdMAJ0"
# =============================================

# Gemini quraşdırması
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""
Sen Instagram-da bir chatbot-san. İstifadəçilərlə təbii, mehriban və maraqlı şəkildə söhbət edirsən.
- Qısa və aydın cavablar ver
- Emoji istifadə et (az-az)
- Azərbaycan dilində cavab ver
- Mehriban və kömək edən ol
"""
)

# Hər istifadəçinin söhbət tarixçəsini saxla
conversation_history = {}


def get_ai_response(user_id: str, user_message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = model.start_chat(history=[])
    chat = conversation_history[user_id]
    try:
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"❌ Gemini xətası: {e}")
        return "Bağışla, hal-hazırda cavab verə bilmirəm. Bir az sonra yenidən yaz! 🙏"


def send_instagram_message(recipient_id: str, message: str):
    url = "https://graph.facebook.com/v18.0/me/messages"
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


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook doğrulandı!")
        return challenge, 200
    return "Xəta: Token uyğun deyil", 403


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
                    print(f"📩 Gələn mesaj ({sender_id}): {user_message}")
                    ai_reply = get_ai_response(sender_id, user_message)
                    print(f"🤖 Gemini cavabı: {ai_reply}")
                    send_instagram_message(sender_id, ai_reply)
    except Exception as e:
        print(f"❌ Xəta: {e}")
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
