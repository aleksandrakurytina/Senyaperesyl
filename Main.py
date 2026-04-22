import logging
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

BOT_TOKEN = '8556771866:AAFXI0DCV1QcIK0Rva0U3DczhYb2v1yzR9k'
SOURCE_GROUP_ID = -1003968893490
TARGET_CHANNEL_ID = -1003819262906

# Время жизни поста в секундах (1 час = 3600 секунд)
POST_LIFETIME_SECONDS = 3600

logging.basicConfig(level=logging.INFO)

# Хранилище задач на закрытие
scheduled_tasks = {}

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

async def close_post_after_hour(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, original_text: str = None):
    """Закрывает пост через час"""
    try:
        # Кнопки для закрытого поста
        closed_keyboard = [
            [
                InlineKeyboardButton("💳 Выплаты", url="https://t.me/milkywaypayments"),
                InlineKeyboardButton("📚 Обучение", url="https://t.me/MilkywayObuchenie")
            ]
        ]
        
        closed_markup = InlineKeyboardMarkup(closed_keyboard)
        
        # Текст закрытого поста
        closed_text = "🔒 Набор закрыт, ожидайте следующие задания ❗️"
        
        # Редактируем сообщение
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=closed_text,
            reply_markup=closed_markup
        )
        
        logging.info(f"Пост {message_id} закрыт через час")
        
    except Exception as e:
        logging.error(f"Ошибка при закрытии поста {message_id}: {e}")

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
    prefill_text = f"Здравствуйте, я из канала MilkyWay, за заданием {platform} за {payment}₽"
    prefill = quote(prefill_text)
    
    # Ссылка на ЛС автора
    if author and author.username:
        respond_url = f"https://t.me/{author.username}?text={prefill}"
    else:
        respond_url = f"https://t.me/{BOT_TOKEN.split(':')[0]}?text={prefill}"
    
    # Кнопки для активного поста
    keyboard = [
        [InlineKeyboardButton("📋 Взять задание", url=respond_url)],
        [
            InlineKeyboardButton("💳 Выплаты", url="https://t.me/milkywaypayments"),
            InlineKeyboardButton("📚 Обучение", url="https://t.me/MilkywayObuchenie")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем в канал
    sent_message = None
    if msg.text:
        sent_message = await context.bot.send_message(chat_id=TARGET_CHANNEL_ID, text=message_text, reply_markup=reply_markup)
    elif msg.photo:
        sent_message = await context.bot.send_photo(chat_id=TARGET_CHANNEL_ID, photo=msg.photo[-1].file_id, caption=message_text, reply_markup=reply_markup)
    elif msg.video:
        sent_message = await context.bot.send_video(chat_id=TARGET_CHANNEL_ID, video=msg.video.file_id, caption=message_text, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=SOURCE_GROUP_ID, text="❌ Неподдерживаемый тип файла")
        return
    
    if sent_message:
        # Планируем закрытие поста через час
        job = context.job_queue.run_once(
            lambda ctx: close_post_after_hour(
                ctx, 
                TARGET_CHANNEL_ID, 
                sent_message.message_id,
                message_text
            ),
            when=POST_LIFETIME_SECONDS
        )
        
        # Сохраняем информацию о задаче
        scheduled_tasks[sent_message.message_id] = job
        
        await context.bot.send_message(chat_id=SOURCE_GROUP_ID, text="✅ Отправлено в канал\n⏰ Пост автоматически закроется через 1 час")
        logging.info(f"Пост {sent_message.message_id} отправлен, закроется через час")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот запущен\n\n"
        "Все посты автоматически закрываются через 1 час после публикации."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем job_queue для планирования задач
    app.job_queue = app.job_queue
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Chat(SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO), 
        forward_to_channel
    ))
    
    print("🚀 Бот запущен")
    print("⏰ Посты будут автоматически закрываться через 1 час")
    app.run_polling()

if __name__ == '__main__':
    main()
