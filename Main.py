import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

BOT_TOKEN = '8556771866:AAFXI0DCV1QcIK0Rva0U3DczhYb2v1yzR9k'
SOURCE_GROUP_ID = -1003968893490
TARGET_CHANNEL_ID = -1003819262906

logging.basicConfig(level=logging.INFO)

def extract_info(text):
    """Извлекает платформу и оплату"""
    platform = ""
    payment = ""
    
    platform_match = re.search(r'➤ Платформа:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if platform_match:
        platform = platform_match.group(1).strip()
    
    payment_match = re.search(r'➤ Оплата:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if payment_match:
        payment = payment_match.group(1).strip()
    
    return platform, payment

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(SOURCE_GROUP_ID):
        return
    
    if update.effective_user and update.effective_user.id == context.bot.id:
        return
    
    msg = update.effective_message
    author = update.effective_user
    message_text = msg.text or msg.caption or ""
    
    # Извлекаем платформу и оплату
    platform, payment = extract_info(message_text)
    
    # Формируем текст для ЛС
    prefill_text = f"Здравствуйте, я из канала MilkyWay, я за заданием {platform} за {payment}₽"
    prefill = quote(prefill_text)
    
    # Ссылка на ЛС автора
    if author and author.username:
        respond_url = f"https://t.me/{author.username}?text={prefill}"
    else:
        respond_url = f"https://t.me/{BOT_TOKEN.split(':')[0]}?text={prefill}"
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton("📋 ВЗЯТЬ ЗАДАНИЕ", url=respond_url)],
        [
            InlineKeyboardButton("💳 ВЫПЛАТЫ", url="https://t.me/milkywaypayments"),
            InlineKeyboardButton("📚 ОБУЧЕНИЕ", url="https://t.me/MilkywayObuchenie")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем в канал
    if msg.text:
        await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=message_text, reply_markup=reply_markup)
    elif msg.photo:
        await context.bot.send_photo(chat_id=TARGET_CHANNEL_ID, photo=msg.photo[-1].file_id, caption=message_text, reply_markup=reply_markup)
    elif msg.video:
        await context.bot.send_video(chat_id=TARGET_CHANNEL_ID, video=msg.video.file_id, caption=message_text, reply_markup=reply_markup)
    
    await context.bot.send_message(chat_id=SOURCE_GROUP_ID, text="✅ Отправлено в канал")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущен")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Chat(SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO), 
        forward_to_channel
    ))
    
    print("🚀 Бот запущен")
    app.run_polling()

if __name__ == '__main__':
    main()
