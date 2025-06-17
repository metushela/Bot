
import json
import os
from flask import Flask, request
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "7980302462:AAFS3EBrr1qaeWVwsY63W_fusboMlNKETE8"
bot = telegram.Bot(token=TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"
conversations = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({"questions": []}, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route(f"/{TOKEN}", methods=["POST"])
def receive_update():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text

    if chat_id in conversations:
        step = conversations[chat_id]["step"]

        if step == "waiting_message":
            conversations[chat_id]["message"] = text
            conversations[chat_id]["step"] = "waiting_button_count"
            bot.send_message(chat_id, "Combien de boutons veux-tu ajouter ?")
        elif step == "waiting_button_count":
            if not text.isdigit():
                bot.send_message(chat_id, "Donne un nombre valide.")
                return "ok"
            conversations[chat_id]["button_count"] = int(text)
            conversations[chat_id]["buttons"] = []
            conversations[chat_id]["step"] = "waiting_button_title"
            conversations[chat_id]["current_button"] = 1
            bot.send_message(chat_id, f"Titre du bouton 1 :")
        elif step == "waiting_button_title":
            conversations[chat_id]["buttons"].append({"text": text})
            conversations[chat_id]["step"] = "waiting_button_url"
            bot.send_message(chat_id, f"Lien du bouton {conversations[chat_id]['current_button']} :")
        elif step == "waiting_button_url":
            conversations[chat_id]["buttons"][-1]["url"] = text
            if conversations[chat_id]["current_button"] < conversations[chat_id]["button_count"]:
                conversations[chat_id]["current_button"] += 1
                conversations[chat_id]["step"] = "waiting_button_title"
                bot.send_message(chat_id, f"Titre du bouton {conversations[chat_id]['current_button']} :")
            else:
                msg = conversations[chat_id]["message"]
                buttons = conversations[chat_id]["buttons"]
                keyboard = [[InlineKeyboardButton(b["text"], url=b["url"])] for b in buttons]
                markup = InlineKeyboardMarkup(keyboard)
                bot.send_message(chat_id, "Voici l'aperçu :", reply_markup=markup)
                bot.send_message(chat_id, "Dans quel groupe ou chaîne veux-tu publier ?
Envoie l'@nomdugroupe ou l'ID.")
                conversations[chat_id]["step"] = "waiting_destination"
        elif step == "waiting_destination":
            try:
                msg = conversations[chat_id]["message"]
                buttons = conversations[chat_id]["buttons"]
                keyboard = [[InlineKeyboardButton(b["text"], url=b["url"])] for b in buttons]
                markup = InlineKeyboardMarkup(keyboard)
                bot.send_message(text, msg, reply_markup=markup)
                bot.send_message(chat_id, "✅ Message publié avec succès.")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Erreur : {e}")
            conversations.pop(chat_id)
        return "ok"

    if text.startswith("/ajouter"):
        try:
            parts = text.split(" | ")
            _, question, reponse, image = parts
        except ValueError:
            bot.send_message(chat_id, "❌ Format invalide.
Utilise :
/ajouter | question | réponse | image_url (facultatif)")
            return "ok"
        data = load_data()
        data["questions"].append({
            "question": question.strip(),
            "reponse": reponse.strip(),
            "image": image.strip()
        })
        save_data(data)
        bot.send_message(chat_id, "✅ Question enregistrée !")

    elif text == "/liste":
        data = load_data()
        if not data["questions"]:
            bot.send_message(chat_id, "📭 Aucune question enregistrée.")
        else:
            msg = "\n".join([f"{i+1}. {q['question']}" for i, q in enumerate(data["questions"])])
            bot.send_message(chat_id, f"📚 Liste des questions :\n{msg}")

    elif text.startswith("/qcm"):
        data = load_data()
        if not data["questions"]:
            bot.send_message(chat_id, "❌ Aucune question pour faire un QCM.")
            return 'ok'
        import random
        q = random.choice(data["questions"])
        keyboard = [[InlineKeyboardButton("Voir la réponse", callback_data=f"reponse:{q['reponse']}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, f"❓ {q['question']}", reply_markup=reply_markup)

    elif text == "/publier":
        conversations[chat_id] = {"step": "waiting_message"}
        bot.send_message(chat_id, "Quel est le message à publier ?")

    elif text.startswith("/boutons"):
        keyboard = [
            [InlineKeyboardButton("Bouton 1", callback_data='btn1')],
            [InlineKeyboardButton("Bouton 2", callback_data='btn2')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, "Voici tes boutons :", reply_markup=reply_markup)

    else:
        bot.send_message(chat_id, "Commande inconnue. Essaie /ajouter, /liste, /qcm, /publier ou /boutons")

    return "ok"

@app.route("/")
def index():
    return "Bot Telegram Actif."

@app.before_first_request
def set_webhook():
    url = os.environ.get("RENDER_EXTERNAL_URL") or "https://TON-NOM.onrender.com"
    bot.set_webhook(f"{url}/{TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
