from dotenv import load_dotenv
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота (замените на свой)
load_dotenv("params.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЛАВИАТУРЫ ==========
# Обычная клавиатура
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="🎯 Кнопки")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🔗 Ссылки")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Inline-клавиатура
def get_inline_keyboard():
    buttons = [
        [InlineKeyboardButton(text="👍", callback_data="like"), 
         InlineKeyboardButton(text="👎", callback_data="dislike")],
        [InlineKeyboardButton(text="GitHub", url="https://github.com")],
        [InlineKeyboardButton(text="Удалить сообщение", callback_data="delete")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ОБРАБОТЧИКИ КОМАНД ==========

# /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    await message.answer(
        f"👋 Привет, {user.first_name}!\n"
        f"Я простой бот на aiogram\n"
        f"Используй /help для списка команд",
        reply_markup=get_main_keyboard()
    )

# /help
@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: types.Message):
    help_text = """
📚 <b>Доступные команды:</b>

/start - Начать диалог
/help - Эта справка
/echo [текст] - Повторить текст
/buttons - Показать inline-кнопки
/stats - Статистика

<b>Или используй кнопки внизу!</b>
    """
    await message.answer(help_text, parse_mode="HTML")

# /echo
@dp.message(Command("echo"))
async def cmd_echo(message: types.Message):
    # Получаем текст после команды /echo
    if len(message.text.split()) > 1:
        text = " ".join(message.text.split()[1:])
        await message.answer(f"📢 Вы сказали: {text}")
    else:
        await message.answer("Напишите что-нибудь после /echo")

# /buttons
@dp.message(Command("buttons"))
@dp.message(F.text == "🎯 Кнопки")
async def cmd_buttons(message: types.Message):
    await message.answer(
        "Вот inline-кнопки:\n"
        "• Нажми 👍 или 👎\n"
        "• Перейди на GitHub\n"
        "• Удали это сообщение",
        reply_markup=get_inline_keyboard()
    )

# /stats или кнопка "Статистика"
@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message):
    user = message.from_user
    stats_text = f"""
📊 <b>Ваша статистика:</b>

👤 <b>Имя:</b> {user.first_name}
🆔 <b>ID:</b> {user.id}
📝 <b>Username:</b> @{user.username if user.username else 'не указан'}
📅 <b>Дата регистрации:</b> {user.language_code}
    """
    await message.answer(stats_text, parse_mode="HTML")

# Кнопка "Ссылки"
@dp.message(F.text == "🔗 Ссылки")
async def show_links(message: types.Message):
    links_text = """
🔗 <b>Полезные ссылки:</b>

• <a href="https://docs.aiogram.dev/">Документация aiogram</a>
• <a href="https://core.telegram.org/bots/api">Telegram Bot API</a>
• <a href="https://github.com/aiogram/aiogram">GitHub aiogram</a>
    """
    await message.answer(links_text, parse_mode="HTML", disable_web_page_preview=True)

# ========== ОБРАБОТКА CALLBACK-ЗАПРОСОВ ==========

# Обработка нажатий на inline-кнопки
@dp.callback_query(F.data == "like")
async def process_like(callback: types.CallbackQuery):
    await callback.answer("Спасибо за лайк! ❤️")
    await callback.message.edit_text("Вы поставили 👍")

@dp.callback_query(F.data == "dislike")
async def process_dislike(callback: types.CallbackQuery):
    await callback.answer("Жаль, что не понравилось 😢")
    await callback.message.edit_text("Вы поставили 👎")

@dp.callback_query(F.data == "delete")
async def process_delete(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("Сообщение удалено")

# ========== ОБРАБОТКА РАЗНЫХ ТИПОВ СООБЩЕНИЙ ==========

# Обработка фото
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer(f"📸 Получил фото!\nID: {message.photo[-1].file_id}")

# Обработка документов
@dp.message(F.document)
async def handle_document(message: types.Message):
    doc = message.document
    await message.answer(f"📄 Документ: {doc.file_name}")

# Обработка стикеров
@dp.message(F.sticker)
async def handle_sticker(message: types.Message):
    await message.answer(f"🎨 Стикер!\nEmoji: {message.sticker.emoji}")

# Обработка голосовых сообщений
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer(f"🎤 Голосовое сообщение!\nДлительность: {message.voice.duration} сек")

# Обработка всех текстовых сообщений (кроме команд)
@dp.message(F.text)
async def handle_text(message: types.Message):
    # Пропускаем команды и кнопки
    if message.text.startswith('/') or message.text in ["ℹ️ Помощь", "🎯 Кнопки", "📊 Статистика", "🔗 Ссылки"]:
        return
    
    await message.answer(f"📝 Вы написали: {message.text}")

# ========== ЗАПУСК БОТА ==========

async def main():
    print("🤖 Бот запускается...")
    
    try:
        # Удаляем вебхук (если был)
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем поллинг
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        # Закрываем сессию бота
        await bot.session.close()

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())