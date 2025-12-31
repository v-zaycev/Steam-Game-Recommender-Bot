# main.py
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
import uvicorn
import logging

# 1. Создаем FastAPI приложение
app = FastAPI(title="Telegram Bot Webhook")

# 2. Инициализируем бота
bot = Bot(token="ВАШ_ТОКЕН")
dp = Dispatcher()

# 3. Ваши обработчики
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(f"Эхо: {message.text}")

# 4. Webhook эндпоинт
@app.post("/webhook")
async def webhook(request: Request):
    """Основной endpoint для вебхука"""
    try:
        # Получаем обновление от Telegram
        update_data = await request.json()
        update = Update(**update_data)
        
        # Передаем обновление в диспетчер
        await dp.feed_update(bot, update)
        
        return {"status": "ok"}
    
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error"}, 500

# 5. Проверочный endpoint
@app.get("/")
async def root():
    return {"status": "Bot is running"}

# 6. Настройка вебхука при запуске
@app.on_event("startup")
async def on_startup():
    """Устанавливаем вебхук при запуске сервера"""
    webhook_url = "https://ваш-домен.ру/webhook"
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True
    )
    logging.info(f"Webhook set to: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    """Удаляем вебхук при остановке"""
    await bot.delete_webhook()
    await bot.session.close()
    logging.info("Bot stopped")

# 7. Запуск
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Только для разработки!
    )