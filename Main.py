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

# Хранилище авторов постов
post_authors = {}

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
        keyboard = [
            # Первая кнопка - большая (занимает всю ширину)
            [InlineKeyboardButton("📋 ВЗЯТЬ ЗАДАНИЕ", callback_data=f"take_task_{author.id if author else 'unknown'}")],
            # Вторая строка - две маленькие кнопки
            [
                InlineKeyboardButton("💳 ВЫПЛАТЫ", url="https://t.me/milkywaypayments"),
                InlineKeyboardButton("📚 ОБУЧЕНИЕ", url="https://t.me/MilkywayObuchenie")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение в канал
        if message.text:
            sent_message = await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=message_text,
                reply_markup=reply_markup
            )
        elif message.photo:
            sent_message = await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=message_text if message_text else None,
                reply_markup=reply_markup
            )
        elif message.document:
            sent_message = await context.bot.send_document(
                chat_id=TARGET_CHANNEL_ID,
                document=message.document.file_id,
                caption=message_text if message_text else None,
                reply_markup=reply_markup
            )
        elif message.video:
            sent_message = await context.bot.send_video(
                chat_id=TARGET_CHANNEL_ID,
                video=message.video.file_id,
                caption=message_text if message_text else None,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID,
                text="❌ Неподдерживаемый тип сообщения."
            )
            return
        
        # Сохраняем информацию об авторе
        if author:
            post_authors[sent_message.message_id] = {
                'user_id': author.id,
                'username': author.username,
                'full_name': author.full_name
            }
        
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
    """Обработка нажатия на кнопку 'ВЗЯТЬ ЗАДАНИЕ'"""
    query = update.callback_query
    user = query.from_user
    message = query.message
    
    try:
        data = query.data
        
        if data.startswith('take_task_'):
            await query.answer("⏳ Отправка...")
            
            # Получаем ID автора
            parts = data.split('_')
            if len(parts) < 3 or parts[2] == 'unknown':
                await query.answer("❌ Не удалось определить автора", show_alert=True)
                return
            
            author_id = int(parts[2])
            
            # Текст для автора
            user_message = (
                f"✅ НОВЫЙ ОТКЛИК!\n\n"
                f"📝 Задание: {message.text or message.caption or 'Медиафайл'}\n\n"
                f"👤 Откликнулся: {user.full_name}"
            )
            if user.username:
                user_message += f" (@{user.username})"
            user_message += f"\n🆔 ID: {user.id}"
            
            # Отправляем автору
            try:
                await context.bot.send_message(
                    chat_id=author_id,
                    text=user_message
                )
                await query.answer("✅ Отклик отправлен автору!", show_alert=True)
                logger.info(f"Отклик от {user.id} -> автору {author_id}")
            except Exception as e:
                await query.answer("❌ Автор запретил сообщения", show_alert=True)
                
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await query.answer("❌ Ошибка", show_alert=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 БОТ ЗАПУЩЕН\n\n"
        "Все сообщения из группы автоматически пересылаются в канал с кнопками:\n"
        "• ВЗЯТЬ ЗАДАНИЕ - отклик автору\n"
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
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print(f"🚀 БОТ ЗАПУЩЕН")
    print(f"📁 Группа: {SOURCE_GROUP_ID}")
    print(f"📢 Канал: {TARGET_CHANNEL_ID}")
    print(f"💬 Все сообщения автоматически пересылаются в канал")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
