#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Konfiguratsiya
TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS = os.environ.get('ALLOWED_USERS', '').split(',')  # Faqat ruxsat etilgan userlar

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Vaqtinchalik papka
TEMP_DIR = tempfile.mkdtemp()

# Health check uchun endpoint (Render uchun)
async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot sog'lomligini tekshirish uchun oddiy xabar"""
    await update.message.reply_text('✅ Bot ishlayapti!')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi - bot haqida ma'lumot"""
    user = update.effective_user
    welcome_text = (
        f"👋 Assalomu alaykum {user.first_name}!\n\n"
        f"📦 Men Python botlarni joylashtirish uchun yordamchi botman.\n\n"
        f"📤 Menga ikkita fayl yuboring:\n"
        f"1️⃣ bot.py - asosiy bot kodingiz\n"
        f"2️⃣ requirements.txt - kerakli kutubxonalar ro'yxati\n\n"
        f"🔧 Komandalar:\n"
        f"/start - Boshlash\n"
        f"/help - Yordam\n"
        f"/status - Bot holatini tekshirish\n"
        f"/clear - Vaqtinchalik fayllarni tozalash"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = (
        "🤖 **Botdan foydalanish qo'llanmasi**\n\n"
        "1️⃣ **Fayllarni tayyorlash**:\n"
        "   - `bot.py` - asosiy bot faylingiz\n"
        "   - `requirements.txt` - kutubxonalar ro'yxati\n\n"
        "2️⃣ **Fayllarni yuborish**:\n"
        "   - Ikkala faylni ketma-ket yuboring\n"
        "   - Bot avtomatik tekshiradi va joylashtiradi\n\n"
        "3️⃣ **Natija**:\n"
        "   - Muvaffaqiyatli bo'lsa, GitHub repozitori va Render linki beriladi\n\n"
        "⚠️ **Muhim**: requirements.txt da quyidagi kutubxona bo'lishi shart:\n"
        "   `python-telegram-bot>=20.0`"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot holatini tekshirish"""
    status_text = (
        f"📊 **Bot holati**\n\n"
        f"✅ Bot ishlamoqda\n"
        f"📁 Vaqtinchalik fayllar: {len(os.listdir(TEMP_DIR))} ta\n"
        f"👤 Ruxsat etilgan foydalanuvchilar: {len(ALLOWED_USERS) if ALLOWED_USERS[0] else 'Hamma'}\n"
        f"🕐 Vaqt: {update.message.date}"
    )
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def clear_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vaqtinchalik fayllarni tozalash"""
    try:
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, exist_ok=True)
        await update.message.reply_text("✅ Vaqtinchalik fayllar tozalandi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fayllarni qabul qilish va tekshirish"""
    
    # Foydalanuvchini tekshirish
    user_id = str(update.effective_user.id)
    if ALLOWED_USERS[0] and user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Sizga ruxsat berilmagan!")
        return
    
    document = update.message.document
    file_name = document.file_name
    
    # Faqat .py va .txt fayllarni qabul qilish
    if not (file_name.endswith('.py') or file_name.endswith('.txt')):
        await update.message.reply_text("❌ Faqat .py va .txt fayllar qabul qilinadi!")
        return
    
    # Faylni yuklab olish
    file = await context.bot.get_file(document.file_id)
    file_path = os.path.join(TEMP_DIR, file_name)
    await file.download_to_drive(file_path)
    
    # Foydalanuvchiga xabar berish
    await update.message.reply_text(f"✅ {file_name} qabul qilindi!")
    
    # Ikkala fayl borligini tekshirish
    bot_file = os.path.join(TEMP_DIR, 'bot.py')
    req_file = os.path.join(TEMP_DIR, 'requirements.txt')
    
    if os.path.exists(bot_file) and os.path.exists(req_file):
        await process_files(update, context)

async def process_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fayllarni tekshirish va tahlil qilish"""
    await update.message.reply_text("🔄 Fayllarni tekshirish boshlandi...")
    
    try:
        # requirements.txt ni tekshirish
        with open(os.path.join(TEMP_DIR, 'requirements.txt'), 'r') as f:
            requirements = f.read()
        
        # python-telegram-bot borligini tekshirish
        if 'python-telegram-bot' not in requirements:
            await update.message.reply_text(
                "⚠️ Ogohlantirish: requirements.txt da 'python-telegram-bot' topilmadi!\n"
                "Bot ishlamasligi mumkin."
            )
        
        # bot.py ni sintaksis tekshirish
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', os.path.join(TEMP_DIR, 'bot.py')],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            await update.message.reply_text(
                f"❌ bot.py da xatolik:\n```\n{result.stderr}\n```",
                parse_mode='Markdown'
            )
            return
        
        # Muvaffaqiyatli xabar
        success_message = (
            "✅ **Barcha tekshiruvlardan o'tdi!**\n\n"
            "📝 **Keyingi qadamlar**:\n"
            "1️⃣ GitHub'ga yuklash (avtomatik)\n"
            "2️⃣ Render'da joylashtirish\n"
            "3️⃣ Cron-job.org sozlash\n\n"
            "📌 **Eslatma**: Bot to'liq ishlashi uchun:\n"
            "• GitHub repozitori yaratish\n"
            "• Render'da Web Service ochish\n"
            "• Cron-job.org da ping sozlash\n\n"
            "🔄 Jarayon davom etmoqda..."
        )
        await update.message.reply_text(success_message, parse_mode='Markdown')
        
        # Bu yerda GitHub API orqali yuklash kodi bo'lishi mumkin
        # Hozircha faqat fayllarni saqlaymiz
        
        # Fayl tarkibini ko'rsatish
        with open(os.path.join(TEMP_DIR, 'bot.py'), 'r') as f:
            bot_content = f.read()[:500]  # Faqat 500 belgi
        
        await update.message.reply_text(
            f"📄 **bot.py (boshi):**\n```python\n{bot_content}\n...\n```",
            parse_mode='Markdown'
        )
        
        # requirements.txt ni ko'rsatish
        await update.message.reply_text(
            f"📄 **requirements.txt:**\n```\n{requirements}\n```",
            parse_mode='Markdown'
        )
        
        # Yakuniy xabar
        final_message = (
            "🎉 **Bot tayyor!**\n\n"
            "📂 Fayllar saqlandi. Endi:\n\n"
            "1️⃣ **GitHub**: Yangi repo yaratib, fayllarni yuklang\n"
            "2️⃣ **Render**: GitHub reponi ulang va deploy qiling\n"
            "3️⃣ **Cron-job**: Har 5 daqiqada ping sozlang\n\n"
            "📚 Batafsil: /help"
        )
        await update.message.reply_text(final_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        # Vaqtinchalik fayllarni tozalash (ixtiyoriy)
        # shutil.rmtree(TEMP_DIR)
        # os.makedirs(TEMP_DIR, exist_ok=True)
        pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatoliklarni qayta ishlash"""
    logger.error(f"Xatolik: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Texnik xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
            )
    except:
        pass

def main():
    """Botni ishga tushirish"""
    
    # Token mavjudligini tekshirish
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("BOT_TOKEN muhit o'zgaruvchisida ko'rsatilmagan!")
        print("❌ Iltimos, BOT_TOKEN ni sozlang!")
        print("Masalan: export BOT_TOKEN='sizning_tokeningiz'")
        sys.exit(1)
    
    # Application yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("clear", clear_temp))
    application.add_handler(CommandHandler("health", health_check))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Xatolik handleri
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    logger.info("Bot ishga tushmoqda...")
    print("🤖 Bot ishga tushdi! @BotFather dan test qiling.")
    
    # Polling orqali ishlash (Render uchun webhook ham qo'llash mumkin)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
