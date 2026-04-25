import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import quote

BOT_TOKEN = '8556771866:AAFXI0DCV1QcIK0Rva0U3DczhYb2v1yzR9k'
SOURCE_GROUP_ID = -1003968893490
TARGET_CHANNEL_ID = -1003819262906

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище постов: {message_id: {'chat_id': channel_id, 'author_id': user_id}}
active_posts = {}

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

async def close_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрывает пост по команде /close"""
    # Команда должна быть в группе отправителя
    if update.effective_chat.id != SOURCE_GROUP_ID:
        await update.message.reply_text("❌ Эта команда работает только в группе для постов")
        return

    # Проверяем, есть ли активные посты у этого пользователя
    user_id = update.effective_user.id
    user_posts = [msg_id for msg_id, data in active_posts.items() if data['author_id'] == user_id]
    
    if not user_posts:
        await update.message.reply_text("❌ У вас нет активных постов для закрытия")
        return

    closed_count = 0
    for message_id in user_posts:
        post_data = active_posts[message_id]
        
        try:
            # Кнопки для закрытого поста
            closed_keyboard = [
                [
                    InlineKeyboardButton("💳 Выплаты", url="https://t.me/milkywaypayments"),
                    InlineKeyboardButton("📚 Обучение", url="https://t.me/MilkywayObuchenie")
                ]
            ]
            closed_markup = InlineKeyboardMarkup(closed_keyboard)
            closed_text = "🔒 Набор закрыт, ожидайте следующие задания ❗️"

            # Редактируем пост в канале
            await context.bot.edit_message_text(
                chat_id=post_data['chat_id'],
                message_id=message_id,
                text=closed_text,
                reply_markup=closed_markup
            )
            
            # Удаляем из активных постов
            del active_posts[message_id]
            closed_count += 1
            logger.info(f"Пост {message_id} закрыт пользователем {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии поста {message_id}: {e}")
            await update.message.reply_text(f"❌ Ошибка при закрытии поста: {e}")

    if closed_count > 0:
        await update.message.reply_text(f"✅ Закрыто постов: {closed_count}")

async def close_all_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрывает все посты (только для админов)"""
    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    
    # Проверка на админа (опционально)
    # if update.effective_user.id not in ADMIN_IDS:
    #     await update.message.reply_text("❌ Только для админов")
    #     return
    
    if not active_posts:
        await update.message.reply_text("❌ Нет активных постов")
        return

    closed_count = 0
    for message_id, post_data in list(active_posts.items()):
        try:
            closed_keyboard = [
                [
                    InlineKeyboardButton("💳 Выплаты", url="https://t.me/milkywaypayments"),
                    InlineKeyboardButton("📚 Обучение", url="https://t.me/MilkywayObuchenie")
                ]
            ]
            closed_markup = InlineKeyboardMarkup(closed_keyboard)
            closed_text = "🔒 Все наборы закрыты ❗️"

            await context.bot.edit_message_text(
                chat_id=post_data['chat_id'],
                message_id=message_id,
                text=closed_text,
                reply_markup=closed_markup
            )
            
            del active_posts[message_id]
            closed_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии поста {message_id}: {e}")

    await update.message.reply_text(f"✅ Закрыто постов: {closed_count}")

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает сообщение из группы в канал"""
    try:
        # Проверяем, что сообщение из исходной группы
        if update.effective_chat.id != SOURCE_GROUP_ID:
            return

        # Игнорируем сообщения от самого бота
        if update.effective_user and update.effective_user.id == context.bot.id:
            return

        msg = update.effective_message
        if not msg:
            return
            
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
        if msg.text:
            sent_message = await context.bot.send_message(
                chat_id=TARGET_CHANNEL_ID, 
                text=message_text, 
                reply_markup=reply_markup
            )
        elif msg.photo:
            sent_message = await context.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID, 
                photo=msg.photo[-1].file_id, 
                caption=message_text, 
                reply_markup=reply_markup
            )
        elif msg.video:
            sent_message = await context.bot.send_video(
                chat_id=TARGET_CHANNEL_ID, 
                video=msg.video.file_id, 
                caption=message_text, 
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID, 
                text="❌ Неподдерживаемый тип файла"
            )
            return

        if sent_message:
            # Сохраняем пост в активные
            active_posts[sent_message.message_id] = {
                'chat_id': TARGET_CHANNEL_ID,
                'author_id': author.id,
                'author_name': author.first_name
            }

            await context.bot.send_message(
                chat_id=SOURCE_GROUP_ID, 
                text=f"✅ Отправлено в канал\n\n"
                     f"📌 Чтобы закрыть набор, напишите /close\n"
                     f"🔒 Пост закроется для новых откликов"
            )
            logger.info(f"Пост {sent_message.message_id} отправлен пользователем {author.id}")
            
    except Exception as e:
        logger.error(f"Ошибка в forward_to_channel: {e}")
        await context.bot.send_message(
            chat_id=SOURCE_GROUP_ID, 
            text=f"❌ Ошибка: {str(e)[:100]}"
        )

async def show_my_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные посты пользователя"""
    if update.effective_chat.id != SOURCE_GROUP_ID:
        return
    
    user_id = update.effective_user.id
    user_posts = [msg_id for msg_id, data in active_posts.items() if data['author_id'] == user_id]
    
    if not user_posts:
        await update.message.reply_text("📭 У вас нет активных постов")
    else:
        await update.message.reply_text(
            f"📊 Ваши активные посты: {len(user_posts)}\n\n"
            f"Чтобы закрыть пост, используйте команду /close"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 Бот для публикации заданий\n\n"
        "📝 Как использовать:\n"
        "1. Отправьте пост в группу\n"
        "2. Бот автоматически опубликует его в канале\n"
        "3. Когда набор завершится, напишите /close\n\n"
        "📌 Доступные команды:\n"
        "/close - закрыть ваш последний пост\n"
        "/myposts - показать ваши активные посты\n"
        "/close_all - закрыть все посты (админ)"
    )

def main():
    """Запуск бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("close", close_post))
        application.add_handler(CommandHandler("myposts", show_my_posts))
        application.add_handler(CommandHandler("close_all", close_all_posts))
        application.add_handler(MessageHandler(
            filters.Chat(chat_id=SOURCE_GROUP_ID) & (filters.TEXT | filters.PHOTO | filters.VIDEO), 
            forward_to_channel
        ))
        
        print("🚀 Бот запущен")
        print(f"📢 Отслеживается группа: {SOURCE_GROUP_ID}")
        print(f"📤 Посты отправляются в канал: {TARGET_CHANNEL_ID}")
        print("\n📌 Команды:")
        print("  /close - закрыть свой пост")
        print("  /myposts - показать свои посты")
        print("  /close_all - закрыть все посты")
        
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()