import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio

# Настройки
BOT_TOKEN = '8724423809:AAEeLx9F4Xku8AAHqrRYCl-UWqrsc4TTRME'  # Ваш токен
SOURCE_GROUP_ID = -1003321868745  # ID группы откуда пересылаем
TARGET_CHANNEL_ID = -1003079468911  # ID канала куда пересылаем

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Словарь для хранения связи сообщений с автором
post_authors = {}

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка всех сообщений из группы в канал с одной кнопкой"""
    
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
        
        if not message_text and not message.media:
            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID,
                text="❌ Сообщение пустое. Пересылка отменена."
            )
            return
        
        # Создаем одну кнопку "Взять задание"
        keyboard = []
        
        if author and author.username:
            # Если есть username - кнопка с переходом в ЛС
            keyboard.append([InlineKeyboardButton("📋 Взять задание", url=f"https://t.me/{author.username}")])
        elif author:
            # Если нет username - callback кнопка
            keyboard.append([InlineKeyboardButton("📋 Взять задание", callback_data=f"take_task_{author.id}")])
        else:
            keyboard.append([InlineKeyboardButton("📋 Взять задание", callback_data="take_task_unknown")])
        
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
                text="❌ Неподдерживаемый тип сообщения. Пересылка отменена."
            )
            return
        
        # Сохраняем информацию об авторе поста
        if author:
            post_authors[sent_message.message_id] = {
                'user_id': author.id,
                'username': author.username,
                'full_name': author.full_name
            }
            logger.info(f"Сохранен автор поста {sent_message.message_id}: {author.full_name}")
        
        # Отправляем подтверждение в группу
        await context.bot.send_message(
            chat_id=SOURCE_GROUP_ID,
            text="✅ Сообщение успешно переслано в канал!"
        )
        
        logger.info(f"Сообщение переслано в канал. Автор: {author.full_name if author else 'Неизвестный'}")
                
    except Exception as e:
        logger.error(f"Ошибка при пересылке: {e}")
        await context.bot.send_message(
            chat_id=SOURCE_GROUP_ID,
            text=f"❌ Ошибка при пересылке сообщения: {str(e)}"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Взять задание'"""
    query = update.callback_query
    user = query.from_user
    message = query.message
    
    try:
        data = query.data
        logger.info(f"Нажата кнопка: {data} от пользователя {user.full_name} (ID: {user.id})")
        
        if data.startswith('take_task_'):
            # Получаем ID автора
            if data == 'take_task_unknown':
                await query.answer(
                    text="❌ Не удалось определить автора задания",
                    show_alert=True
                )
                return
            
            author_id = int(data.split('_')[2])
            
            # Получаем информацию об авторе поста
            author_info = post_authors.get(message.message_id)
            
            if not author_info:
                try:
                    author_chat = await context.bot.get_chat(author_id)
                    author_info = {
                        'user_id': author_id,
                        'username': author_chat.username,
                        'full_name': author_chat.full_name
                    }
                except:
                    await query.answer(
                        text="❌ Не удалось найти автора задания",
                        show_alert=True
                    )
                    return
            
            # Отправляем сообщение автору
            try:
                # Текст сообщения для автора
                user_message = f"Здравствуйте, я из канала MilkyWay, я за заданием * за *₽\n\n" \
                              f"👤 Откликнулся: {user.full_name}"
                if user.username:
                    user_message += f" (@{user.username})"
                user_message += f"\n🆔 ID: {user.id}"
                
                await context.bot.send_message(
                    chat_id=author_id,
                    text=user_message
                )
                
                # Показываем уведомление нажавшему
                await query.answer(
                    text="✅ Ваш отклик отправлен автору! Он свяжется с вами в ближайшее время.",
                    show_alert=True
                )
                
                logger.info(f"Отклик от пользователя {user.id} отправлен автору {author_id}")
                
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение автору {author_id}: {e}")
                await query.answer(
                    text="❌ Не удалось отправить отклик. Возможно, автор запретил сообщения.",
                    show_alert=True
                )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки: {e}")
        await query.answer(
            text="❌ Произошла ошибка",
            show_alert=True
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 Бот запущен!\n\n"
        "Все сообщения из группы автоматически пересылаются в канал с кнопкой 'Взять задание'.\n"
        "При нажатии на кнопку откликнувшемуся будет отправлено сообщение автору."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 Инструкция:\n\n"
        "1. Отправьте любое сообщение в группу\n"
        "2. Бот автоматически перешлет его в канал\n"
        "3. В канале появится кнопка 'Взять задание'\n"
        "4. При нажатии на кнопку автору задания придет уведомление с контактами откликнувшегося\n\n"
        "Автор задания получит сообщение: 'Здравствуйте, я из канала MilkyWay, я за заданием * за *₽'"
    )

def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик для всех типов сообщений из группы
    application.add_handler(
        MessageHandler(
            filters.Chat(SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL), 
            forward_to_channel
        )
    )
    
    # Обработчик для callback кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    print(f"🚀 Бот запущен...")
    print(f"📁 Группа источник: {SOURCE_GROUP_ID}")
    print(f"📢 Канал назначения: {TARGET_CHANNEL_ID}")
    print("Нажмите Ctrl+C для остановки")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
