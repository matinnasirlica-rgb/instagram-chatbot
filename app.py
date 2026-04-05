import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# =============================================
# BURAYA ÖZ MƏLUMATLARINI DAXİL ET
# =============================================
VERIFY_TOKEN = "istediyin_bir_söz"         # Meta Webhook verify token (özün seç)
PAGE_ACCESS_TOKEN = "BURAYA_META_TOKEN"    # Meta App-dan alacaqsan
GEMINI_API_KEY = "BURAYA_GEMINI_KEY"       # aistudio.google.com-dan alacaqsan
# =============================================

# Gemini quraşdırması
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",  # Pulsuz və sürətli model
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
    """Gemini AI-dan cavab al"""

    # İstifadəçinin chat session-ını yüklə
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
    """Instagram-a cavab göndər"""
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
    return response.json()


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook doğrulama"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook doğrulandı!")
        return challenge, 200
    else:
        return "Xəta: Token uyğun deyil", 403


@app.route("/webhook", methods=["POST"])
def handle_message():
    """Gələn mesajları emal et"""
    data = request.get_json()

    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging["sender"]["id"]

                # Yalnız mətn mesajlarını emal et
                if "message" in messaging and "text" in messaging["message"]:
                    user_message = messaging["message"]["text"]
                    print(f"📩 Gələn mesaj ({sender_id}): {user_message}")

                    # AI cavabı al
                    ai_reply = get_ai_response(sender_id, user_message)
                    print(f"🤖 Gemini cavabı: {ai_reply}")

                    # Cavabı göndər
                    send_instagram_message(sender_id, ai_reply)

    except Exception as e:
        print(f"❌ Xəta: {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
