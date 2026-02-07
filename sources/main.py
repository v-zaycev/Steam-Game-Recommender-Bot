import asyncio

from bot import TelegramBot

async def main():
    bot = TelegramBot() 
    print("Бот запускается...")
    
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