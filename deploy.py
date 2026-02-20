import os
import telebot
from flask import Flask
import threading

# 🔐 Token environment dan olinadi
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Environment variable qo‘shing.")

bot = telebot.TeleBot(TOKEN)

# ====== Oddiy buyruqlar ======

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom 👋 Bot ishlayapti 🔥")

@bot.message_handler(commands=['id'])
def user_id(message):
    bot.reply_to(message, f"Sening ID: {message.from_user.id}")

# ====== Flask server (Render sleep bo‘lmasligi uchun) ======

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 🚀"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Flask thread
threading.Thread(target=run_flask).start()

# Bot polling
bot.infinity_polling()
