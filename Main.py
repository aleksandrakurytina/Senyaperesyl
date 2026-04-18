import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

BOT_TOKEN = '8556771866:AAFXI0DCV1QcIK0Rva0U3DczhYb2v1yzR9k'
SOURCE_GROUP_ID = -1003968893490
TARGET_CHANNEL_ID = -1003819262906

logging.basicConfig(level=logging.INFO)

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(SOURCE_GROUP_ID):
        return
    
    if update.effective_user and update.effective_user.id == context.bot.id:
        return
    
    msg = update.effective_message
    author = update.effective_user
    message_text = msg.text or msg.caption or ""
    
    # Текст который подставится в поле ввода
    prefill = quote(f"Здравствуйте, я из канала MilkyWay за заданием")
    
    # Ссылка на ЛС автора с готовым текстом
    if author.username:
        respond_url = f"https://t.me/{author.username}?text={prefill}"
    else:
        respond_url = f"https://t.me/{BOT_TOKEN.split(':')[0]}?text={prefill}"
    
    # Кнопки
    keyboard = [
        [InlineKeyboardButton("📋 Взять задание", url=respond_url)],  # Большая кнопка
        [
            InlineKeyboardButton("💳 Выплаты", url="https://t.me/milkywaypayments"),
            InlineKeyboardButton("📚 Обучение", url="https://t.me/MilkywayObuchenie")
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
    elif msg.document:
        await context.bot.send_document(chat_id=TARGET_CHANNEL_ID, document=msg.document.file_id, caption=message_text, reply_markup=reply_markup)
    
    await context.bot.send_message(chat_id=SOURCE_GROUP_ID, text="✅ Отправлено в канал")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот запущен!\n\nВсе сообщения из группы будут пересылаться в канал с кнопками:\n• Взять задание (с готовым текстом)\n• Выплаты\n• Обучение")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Chat(SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL), 
        forward_to_channel
    ))
    
    print("🚀 Бот запущен")
    app.run_polling()

if __name__ == '__main__':
    main()
