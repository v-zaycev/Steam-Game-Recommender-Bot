from dotenv import load_dotenv
import os
import logging
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sources.database_api import PgsqlApiClient
from sources.steam_api_client import SteamAPIClient
from sources.utils import States, is_valid_steamid64 


class TelegramBot:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    users = {}

    def __init__(self):
        load_dotenv("params.env")
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.db_client = PgsqlApiClient()
        self.api_client = SteamAPIClient(os.getenv("STEAM_API_KEY"))
        self.api_client.session = aiohttp.ClientSession()
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.router = Router()
        self.set_message_handlers()

    def set_message_handlers(self):
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, or_f(Command("help"), (F.text == "Помощь")))

        self.router.message.register(self.cmd_trends, or_f(Command("trends"), (F.text == "Тренды")))
        self.router.message.register(self.cmd_recommend, or_f(Command("recommend"), (F.text == "Рекомендации")))
        self.router.message.register(self.cmd_friends_updtaes, or_f(Command("friends_updates"), (F.text == "Обновления друзей")))
        
        self.router.message.register(self.cmd_similar, or_f(Command("similar"), (F.text == "Похожее")))
        self.router.message.register(self.cmd_similar_get, States.similar_game_id_waiting)

        self.router.message.register(self.cmd_add_id, or_f(Command("account_update"), (F.text == "Добавить профиль")))
        self.router.message.register(self.cmd_get_id, States.id_waiting)

        self.router.message.register(self.cmd_get_game_id, or_f(Command("info"), (F.text == "Информация по игре")))
        self.router.message.register(self.cmd_show_game_info, States.info_game_id_waiting)

        self.dp.include_router(self.router)

    async def start(self):
        await self.dp.start_polling(self.bot)

    def check_steam_id(self, tg_id : int) -> bool:
        if tg_id in self.users and self.users[tg_id] is not None:
            return True
        else:
            res = self.db_client.get_steam_id(tg_id)
            self.users[tg_id] = res
            return  res is not None
        
    #Keyboard layout
    def get_main_keyboard(self, tg_id : int):
        if self.check_steam_id(tg_id):
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Помощь"), KeyboardButton(text="Добавить профиль")],
                    [KeyboardButton(text="Похожее"), KeyboardButton(text="Информация по игре")],
                    [KeyboardButton(text="Рекомендации"), KeyboardButton(text="Обновления друзей")],
                    [KeyboardButton(text="Тренды")]
                    
                ],
                resize_keyboard=True
            )
        else:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Помощь"), KeyboardButton(text="Добавить профиль")],
                    [KeyboardButton(text="Похожее"), KeyboardButton(text="Информация по игре")],
                    [KeyboardButton(text="Тренды")]
                ],
                resize_keyboard=True
            )
            
        return keyboard

    #/start
    async def cmd_start(self, message: types.Message):
        user_id = message.from_user.id
        self.db_client.add_telegram_user(user_id)
        await message.answer(
            f"👋 Привет!\n"
            f"Я Steam Game Recommender Bot, помогу тебе следить за новыми играми и интересами твоих друзей.\n"
            f"Используй /help для списка команд или воспользуйся клавиатурой команд.",
            reply_markup = self.get_main_keyboard(message.from_user.id)
        )

    #/add_id
    async def cmd_add_id(self, message: types.Message, state: FSMContext):
        await state.set_state(States.id_waiting)  # ВКЛЮЧИЛИ флаг
        await message.answer(
            "Введите steam id:", 
            reply_markup=ReplyKeyboardRemove())

    async def cmd_get_id(self, message: types.Message, state: FSMContext):
        if not is_valid_steamid64(message.text):
            await message.answer("Неверный формат, попробуйте ещё раз.")
            return
        steam_id = int(message.text)
        steam_ids = await self.api_client.get_user_friends(steam_id)
        ids_data = await self.api_client.get_player_summaries(steam_ids + [steam_id]) 
        self.db_client.add_steam_users(ids_data)
        self.db_client.add_steam_friends(steam_id, steam_ids)
        await message.answer(
            f"Id {steam_id} установлен, данные обновляются",
            reply_markup = self.get_main_keyboard(message.from_user.id)
        )
        for id in steam_ids + [steam_id]:
            data = await self.api_client.get_user_owned_games(id)
            to_ignore = []
            for app in data:
                if self.db_client.get_game_info(app['appid']) is None:
                    game = await self.api_client.get_game_info(int(app['appid']))
                    if game != (None,None):
                        self.db_client.add_game(game)
                    else:
                        to_ignore.append(app['appid'])
                    await asyncio.sleep(1)
            await asyncio.sleep(1)
            data = [item for item in data if item['appid'] not in to_ignore]
            self.db_client.add_user_games(id, data)

        await state.clear()
        self.db_client.update(
            attributes=['steam_id'],
            table='bot_users',
            data=[str(steam_id)],
            id_column='tg_id',
            id=message.from_user.id
        )
        await message.answer(
            f"Данные обновлены, расширенный функционал доступен",
            reply_markup = self.get_main_keyboard(message.from_user.id)
        )


    async def cmd_get_game_id(self, message: types.Message, state: FSMContext):
        await state.set_state(States.info_game_id_waiting)  # ВКЛЮЧИЛИ флаг
        await message.answer(
            "Введите id игры:", 
            reply_markup=ReplyKeyboardRemove())

    #/help
    async def cmd_help(self, message: types.Message):
        help_text = """
<b>Доступные команды:</b>

/start - Начать диалог
/help - Эта справка
/account_update - добавить свой steam_id (либо изменить на новый) для продвинутых функций 
/trends - Информация о самых продаваемых вещах в текущий момент, а также о новых и грядущих релизах
/info - Краткое описание запрашиваемой игры
/similar - Поиск игр, похожих на данную
/recommend - Рекомендации на основе ваших предпочтений
/friends_updates - Игры, недавно добавленные вашими друзьями

<b>Или используй кнопки внизу!</b>
        """
        await message.answer(
            help_text, 
            parse_mode="HTML",
            reply_markup=self.get_main_keyboard(message.from_user.id)
            )

    #/trends 
    async def cmd_trends(self, message: types.Message):
        answer_text = await self.format_trends_for_telegram()
        print(answer_text)
        await message.answer( 
            answer_text,
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard(message.from_user.id)
        )

    #/recommend
    async def cmd_recommend(self, message: types.Message):
        self.check_steam_id(message.from_user.id)
        recomendations = self.db_client.get_recommendations(self.users[message.from_user.id])
        answer_text = "<b>Рекомендации на основе ваших игр:</b>\n"
        for i, recomendations in enumerate(recomendations):
            answer_text += f"{i+1}. <code>{recomendations[0]}</code> - {recomendations[1]}\n"
        await message.answer( 
            answer_text,
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard(message.from_user.id)
        )

    #/similar
    async def cmd_similar(self, message: types.Message, state: FSMContext):
        await state.set_state(States.similar_game_id_waiting)
        await message.answer(
            "Введите id игры:", 
            reply_markup=ReplyKeyboardRemove())

    async def cmd_similar_get(self, message: types.Message, state: FSMContext):
        try:
            app_id = int(message.text)
            similar = self.db_client.get_similar_games(app_id)

            if len(similar) > 0:
                answer_text = f"<b>Игры похожие на <code>{app_id}</code>:</b>\n"
                for i, (id, name) in enumerate(similar):
                    answer_text += f"{i+1}. <code>{id}</code> - {name}\n"
            else:
                answer_text = "Не удалось подобрать похожие игры\n"
            await message.answer( 
                answer_text,
                parse_mode='HTML',
                reply_markup=self.get_main_keyboard(message.from_user.id)
            )
            await state.clear()
        except Exception:
            await message.answer(
                f"Не удалось получить информацию об игре, возможно игры с таким id не существует.",
                reply_markup = self.get_main_keyboard(message.from_user.id)
            )
            raise
    
    #/friends_updates
    async def cmd_friends_updtaes(self, message: types.Message):
        top_updates = self.db_client.get_friends_updates(self.users[message.from_user.id])
        answer_text = "<b>Что недавно добавляли себе ваши друзья:</b>\n"
        for i, top_updates in enumerate(top_updates):
            answer_text += f"{i+1}. <code>{top_updates[0]}</code> - {top_updates[1]}\n"
        await message.answer( 
            answer_text,
            parse_mode='HTML',
            reply_markup=self.get_main_keyboard(message.from_user.id)
        )
    
    async def cmd_show_game_info(self, message: types.Message, state: FSMContext):        
        try:
            app_id = int(message.text)

            in_base = self.db_client.get_game_info(app_id)

            if in_base is None:
                game_data = (await self.api_client.get_game_info(app_id))
                self.db_client.add_game(game_data)

                game_data = game_data[1]
                caption = f"<b>{game_data['name']}</b>\n\n{game_data.get('short_description', '')}"
                image_url = game_data.get('header_image')
            else:
                caption = f"<b>{in_base[0]}</b>\n\n{in_base[1]}"
                image_url = in_base[2]
                print("success db check")
            
            if image_url:
                await message.answer_photo(
                    photo=image_url, 
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup = self.get_main_keyboard(message.from_user.id)
                )
            else:
                await message.answer(
                    caption, 
                    parse_mode='HTML',
                    reply_markup = self.get_main_keyboard(message.from_user.id)
                )
            await state.clear()
        except Exception:
            await message.answer(
                f"Не удалось получить информацию об игре, возможно игры с таким id не существует.",
                reply_markup = self.get_main_keyboard(message.from_user.id)
            )
            raise

    async def format_trends_for_telegram(self) -> str:
        """Форматирует данные для отправки в Telegram"""
        games_data = await self.api_client.get_featured_games_summary()
        
        message_lines = []
        
        # 1. Топ продаж
        message_lines.append("<b>Самое продаваемое:</b>")
        for i, game in enumerate(games_data['top_sellers'], 1):
            message_lines.append(f"{i}. <code>{game['id']}</code> - {game['name']}")
        message_lines.append("")
        
        # 2. Новые релизы
        message_lines.append("<b>Недавние релизы:</b>")
        message_lines.append("Что только что вышло (последние 30 дней):")
        for i, game in enumerate(games_data['new_releases'], 1):
            message_lines.append(f"{i}. <code>{game['id']}</code> - {game['name']}")
        message_lines.append("")
        
        # 3. Скоро выйдут
        message_lines.append("<b>Грядущие релизы:</b>")
        message_lines.append("На что можно потратить деньги в будущем:")
        for i, game in enumerate(games_data['coming_soon'], 1):
            message_lines.append(f"{i}. <code>{game['id']}</code> - {game['name']}")
            message_lines.append(f"   🗓️ {game['release_date']}")
        
        return "\n".join(message_lines)

