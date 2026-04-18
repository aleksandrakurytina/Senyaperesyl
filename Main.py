import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Настройки
BOT_TOKEN = '8556771866:AAFXI0DCV1QcIK0Rva0U3DczhYb2v1yzR9k'
SOURCE_GROUP_ID = -1003968893490
TARGET_CHANNEL_ID = -1003819262906

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка всех сообщений из группы в канал с 3 кнопками"""
    
    try:
        # Проверяем, что сообщение из нужной группы
        if str(update.effective_chat.id) != str(SOURCE_GROUP_ID):
            return

        author = update.effective_user
        message = update.effective_message

        # Пропускаем сообщения от самого бота
        if author and author.id == context.bot.id:
            return
        
        # Берем текст сообщения
        message_text = message.text or message.caption or ""
        
        if not message_text and not message.photo and not message.document and not message.video:
            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID,
                text="❌ Отправьте текст, фото, видео или документ."
            )
            return
        
        # Создаем клавиатуру с 3 кнопками
        keyboard = []
        
        # Первая кнопка - ссылка на ЛС автора (если есть username)
        if author and author.username:
            keyboard.append([InlineKeyboardButton("📋 ВЗЯТЬ ЗАДАНИЕ", url=f"https://t.me/{author.username}")])
        else:
            # Если нет username - показываем ID
            keyboard.append([InlineKeyboardButton("📋 ВЗЯТЬ ЗАДАНИЕ", callback_data="no_username")])
        
        # Вторая строка - две маленькие кнопки
        keyboard.append([
            InlineKeyboardButton("💳 ВЫПЛАТЫ", url="https://t.me/milkywaypayments"),
            InlineKeyboardButton("📚 ОБУЧЕНИЕ", url="https://t.me/MilkywayObuchenie")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Добавляем в сообщение username автора для удобства
        author_text = f"\n\n👤 Автор: @{author.username}" if author and author.username else f"\n\n👤 Автор: {author.full_name} (нет username)"
        
        # Отправляем сообщение в канал
        if message.text:
            await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=message_text + author_text,
                reply_markup=reply_markup
            )
        elif message.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=(message_text if message_text else "") + author_text,
                reply_markup=reply_markup
            )
        elif message.document:
            await context.bot.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=message.document.file_id,
                caption=(message_text if message_text else "") + author_text,
                reply_markup=reply_markup
            )
        elif message.video:
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=message.video.file_id,
                caption=(message_text if message_text else "") + author_text,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID,
                text="❌ Неподдерживаемый тип сообщения."
            )
            return
        
        # Отправляем подтверждение в группу
        await context.bot.send_message(
            chat_id=SOURCE_GROUP_ID,
            text="✅ Сообщение отправлено в канал!"
        )
        
        logger.info(f"Сообщение переслано. Автор: {author.full_name if author else 'Unknown'}")
                
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await context.bot.send_message(
            chat_id=SOURCE_GROUP_ID,
            text=f"❌ Ошибка: {str(e)}"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия, если нет username"""
    query = update.callback_query
    await query.answer("❌ У автора нет username, напишите ему в ЛС по ID", show_alert=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 БОТ ЗАПУЩЕН\n\n"
        "Все сообщения из группы автоматически пересылаются в канал с кнопками:\n"
        "• ВЗЯТЬ ЗАДАНИЕ - открывает ЛС с автором\n"
        "• ВЫПЛАТЫ - канал @milkywaypayments\n"
        "• ОБУЧЕНИЕ - канал @MilkywayObuchenie"
    )

def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    
    # Пересылка всех сообщений
    application.add_handler(
        MessageHandler(
            filters.Chat(SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL), 
            forward_to_channel
        )
    )
    
    # Обработчик для случая, если нет username
    application.add_handler(CallbackQueryHandler(button_callback, pattern="no_username"))
    
    print(f"🚀 БОТ ЗАПУЩЕН")
    print(f"📁 Группа: {SOURCE_GROUP_ID}")
    print(f"📢 Канал: {TARGET_CHANNEL_ID}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
