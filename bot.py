from dotenv import load_dotenv
import os
import asyncio
import logging
import requests
from io import BytesIO
import aiohttp
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup



class TelegramBot:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    def __init__(self):
        load_dotenv("params.env")
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.router = Router()
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, or_f(Command("help"), (F.text == "ℹ️ Помощь")))
        self.router.message.register(self.cmd_echo, Command("echo"))
        self.router.message.register(self.cmd_buttons, or_f(Command("buttons"), (F.text == "🎯 Кнопки")))
        self.router.message.register(self.cmd_stats, or_f(Command("stats"), (F.text == "📊 Статистика")))
        self.router.message.register(self.show_links, or_f(F.text == "📊 Dota 2 информация"))
        self.dp.include_router(self.router)

    async def start(self):  # ✅ Отдельный метод для запуска
        await self.dp.start_polling(self.bot)

    # ========== КЛАВИАТУРЫ ==========
    # Обычная клавиатура (внизу экрана)
    def get_main_keyboard(self):
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="Добавить профиль")],
                [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📊 Dota 2 информация")]
            ],
            resize_keyboard=True
        )
        return keyboard

    # Inline-клавиатура (встроенная в сообщение)
    def get_inline_keyboard(self):
        buttons = [
            [InlineKeyboardButton(text="👍", callback_data="like"), 
            InlineKeyboardButton(text="👎", callback_data="dislike")],
            [InlineKeyboardButton(text="GitHub", url="https://github.com")],
            [InlineKeyboardButton(text="Удалить сообщение", callback_data="delete")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)    

    # ========== ОБРАБОТЧИКИ КОМАНД ==========

    # /start
    async def cmd_start(self, message: types.Message):
        user = message.from_user
        await message.answer(
            f"👋 Привет, {user.first_name} {user.last_name}!\n"
            f"Я Steam Game Recommender Bot\n"
            f"Используй /help для списка команд или воспользуйся клавиатурой команд.",
            reply_markup = self.get_main_keyboard()
        )

    # /help
    async def cmd_help(self, message: types.Message):
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
    async def cmd_echo(self, message: types.Message):
        # Получаем текст после команды /echo
        if len(message.text.split()) > 1:
            text = " ".join(message.text.split()[1:])
            await message.answer(f"📢 Вы сказали: {text}")
        else:
            await message.answer("Напишите что-нибудь после /echo")

    # /buttons
    async def cmd_buttons(self, message: types.Message):
        await message.answer(
            "Вот inline-кнопки:\n"
            "• Нажми 👍 или 👎\n"
            "• Перейди на GitHub\n"
            "• Удали это сообщение",
            reply_markup= self.get_inline_keyboard()
        )

    # /stats или кнопка "Статистика"
    async def cmd_stats(self, message: types.Message):
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
    async def show_links(self, message: types.Message):
        """Минимальный пример отправки информации об игре с картинкой"""
        
        app_id = 570
        
        try:
            # 1. Получаем данные об игре
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://store.steampowered.com/api/appdetails?appids={app_id}') as response:
                    data = await response.json()
                    game_data = data[str(app_id)]['data']
            
            caption = f"*{game_data['name']}*\n\n{game_data.get('short_description', '')}"
            image_url = game_data.get('header_image')
            
            if image_url:
                # 2. Скачиваем картинку
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as img_response:
                        img_bytes = await img_response.read()
                
                # 3. Создаем BufferedInputFile из байтов
                photo_file = BufferedInputFile(img_bytes, filename="dota2.jpg")
                
                # 4. Отправляем фото
                await message.answer_photo(
                    photo=photo_file,  # <-- Используем BufferedInputFile
                    caption=caption,
                    parse_mode='Markdown'
                )
            else:
                await message.answer(caption, parse_mode='Markdown')
                
        except Exception as e:
            await message.answer(f"Ошибка: {e}")

    # ========== ОБРАБОТКА CALLBACK-ЗАПРОСОВ ==========

    # Обработка нажатий на inline-кнопки
    # @dp.callback_query(F.data == "like")
    # async def process_like(callback: types.CallbackQuery):
    #     await callback.answer("Спасибо за лайк! ❤️")
    #     await callback.message.edit_text("Вы поставили 👍")

    # @dp.callback_query(F.data == "dislike")
    # async def process_dislike(callback: types.CallbackQuery):
    #     await callback.answer("Жаль, что не понравилось 😢")
    #     await callback.message.edit_text("Вы поставили 👎")

    # @dp.callback_query(F.data == "delete")
    # async def process_delete(callback: types.CallbackQuery):
    #     await callback.message.delete()
    #     await callback.answer("Сообщение удалено")

    # ========== ЗАПУСК БОТА ==========



async def main():
    bot = TelegramBot() 
    print("🤖 Бот запускается...")
    
    try:
        # Удаляем вебхук (если был)
        await bot.bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем поллинг
        await bot.start()
        
    except Exception as e:
        bot.logger.error(f"Ошибка: {e}")
    finally:
        # Закрываем сессию бота
        await bot.bot.session.close()

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())