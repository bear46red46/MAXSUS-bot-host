import telebot
import os
import subprocess
import json
from datetime import datetime
import threading
import time

# ================== SOZLAMALAR ==================
TOKEN = "8266159930:AAE6SlQFuMp3x9ZkTJ1wjghvEoT8XNUz4iQ"
BASE_DIR = "users"
ANALYTICS_FILE = "analytics.json"
STATUS_FILE = "status.json"

bot = telebot.TeleBot(TOKEN)
os.makedirs(BASE_DIR, exist_ok=True)

# ================== YORDAMCHI FUNKSIYALAR ==================

def user_dir(user_id):
    path = f"{BASE_DIR}/{user_id}"
    os.makedirs(path, exist_ok=True)
    return path

def status_path(user_id):
    return f"{user_dir(user_id)}/{STATUS_FILE}"

def set_status(user_id, state: bool):
    with open(status_path(user_id), "w") as f:
        json.dump({"running": state}, f)

def get_status(user_id):
    path = status_path(user_id)
    if not os.path.exists(path):
        set_status(user_id, False)
        return False
    with open(path, "r") as f:
        return json.load(f)["running"]

def save_analysis(user_id, data):
    with open(f"{user_dir(user_id)}/{ANALYTICS_FILE}", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ================== KOD TAHLIL QILUVCHI ==================

def analyze_code(file_path):
    analysis = {
        "lines": 0,
        "functions": 0,
        "imports": 0,
        "risk_words": [],
        "file": os.path.basename(file_path),
        "created_at": str(datetime.now())
    }

    risk_list = ["os.system", "subprocess", "rm -rf", "eval", "exec", "shutil.rmtree"]

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    analysis["lines"] = len(lines)

    for line in lines:
        line_strip = line.strip()

        if line_strip.startswith("def "):
            analysis["functions"] += 1

        if line_strip.startswith("import ") or line_strip.startswith("from "):
            analysis["imports"] += 1

        for risk in risk_list:
            if risk in line and risk not in analysis["risk_words"]:
                analysis["risk_words"].append(risk)

    return analysis

# ================== BOT QISMI ==================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Bot-hosting tizimi.\n\n"
        "📁 Istalgan `.py` + `requirements.txt` yuboring.\n"
        "🚀 /deploy — ishga tushirish\n"
        "🛑 /off — to‘xtatish\n"
        "▶️ /on — qayta yoqish\n"
        "📊 /analysis — kodni ochib tahlil qilish\n"
        "ℹ️ /status — holatni ko‘rish"
    )

# ====== FAYLLARNI QABUL QILISH (HAR QANDAY .py) ======
@bot.message_handler(content_types=["document"])
def save_file(message):
    user_id = message.from_user.id
    path = user_dir(user_id)

    file_name = message.document.file_name

    if not (file_name.endswith(".py") or file_name == "requirements.txt"):
        bot.reply_to(message, "❌ Faqat `.py` yoki `requirements.txt` qabul qilinadi!")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open(f"{path}/{file_name}", "wb") as f:
        f.write(downloaded)

    bot.reply_to(message, f"📁 `{file_name}` saqlandi!")

# ====== USER BOTNI ISHGA TUSHIRISH ======
def run_user_bot(user_id, filename):
    path = user_dir(user_id)

    req_path = f"{path}/requirements.txt"
    if os.path.exists(req_path):
        subprocess.run(["pip", "install", "-r", req_path])

    set_status(user_id, True)

    process = subprocess.Popen(["python", f"{path}/{filename}"])

    while True:
        time.sleep(2)
        if not get_status(user_id):
            process.terminate()
            break

# ====== DEPLOY ======
@bot.message_handler(commands=["deploy"])
def deploy(message):
    user_id = message.from_user.id
    path = user_dir(user_id)

    # Oxirgi yuborilgan .py faylni topamiz
    py_files = [f for f in os.listdir(path) if f.endswith(".py")]

    if not py_files:
        bot.send_message(message.chat.id, "❌ Avval biror `.py` fayl yuboring!")
        return

    main_file = py_files[-1]  # oxirgi yuborilganini olamiz

    # Pauza
    set_status(user_id, False)

    # Tahlil
    analysis = analyze_code(f"{path}/{main_file}")
    save_analysis(user_id, analysis)

    # Ishga tushirish
    threading.Thread(
        target=run_user_bot, args=(user_id, main_file), daemon=True
    ).start()

    bot.send_message(
        message.chat.id,
        f"🚀 `{main_file}` deployed!\n📊 /analysis bilan ko‘ring."
    )

# ====== ON / OFF ======
@bot.message_handler(commands=["off"])
def turn_off(message):
    set_status(message.from_user.id, False)
    bot.send_message(message.chat.id, "🛑 Botingiz to‘xtatildi.")

@bot.message_handler(commands=["on"])
def turn_on(message):
    user_id = message.from_user.id
    path = user_dir(user_id)

    py_files = [f for f in os.listdir(path) if f.endswith(".py")]
    if not py_files:
        bot.send_message(message.chat.id, "❌ Hech qanday `.py` topilmadi!")
        return

    main_file = py_files[-1]
    threading.Thread(
        target=run_user_bot, args=(user_id, main_file), daemon=True
    ).start()

    bot.send_message(message.chat.id, f"▶️ `{main_file}` qayta yoqildi.")

@bot.message_handler(commands=["status"])
def status(message):
    state = "🟢 ON" if get_status(message.from_user.id) else "🔴 OFF"
    bot.send_message(message.chat.id, f"📌 Holat: {state}")

# ====== ANALYSIS (HAR QANDAY .py) ======
@bot.message_handler(commands=["analysis"])
def show_analysis(message):
    user_id = message.from_user.id
    path = user_dir(user_id)

    py_files = [f for f in os.listdir(path) if f.endswith(".py")]
    if not py_files:
        bot.send_message(message.chat.id, "❌ Hech qanday `.py` fayl yo‘q!")
        return

    target_file = py_files[-1]

    # Pauza
    set_status(user_id, False)

    analysis = analyze_code(f"{path}/{target_file}")
    save_analysis(user_id, analysis)

    text = (
        "📊 **KOD TAHLILI**\n\n"
        f"📁 Fayl: {analysis['file']}\n"
        f"📄 Qatorlar: {analysis['lines']}\n"
        f"🔧 Funksiyalar: {analysis['functions']}\n"
        f"📦 Importlar: {analysis['imports']}\n"
        f"⚠️ Riskli kodlar: {', '.join(analysis['risk_words']) or 'Yo‘q'}\n"
        f"🕒 Tahlil vaqti: {analysis['created_at']}\n\n"
        "📄 Kod fayli quyida yuborildi 👇"
    )

    bot.send_message(message.chat.id, text)
    bot.send_document(message.chat.id, open(f"{path}/{target_file}", "rb"))

# ================== BOTNI ISHGA TUSHIRISH ==================
print("Hosting bot running...")
bot.polling()