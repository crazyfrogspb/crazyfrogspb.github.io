#!/usr/bin/env python3
"""
Скрипт для первоначальной настройки Telegram сессии
Запустите этот скрипт один раз для создания файла сессии
"""

import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

async def setup_session():
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ Не установлены TELEGRAM_API_ID и TELEGRAM_API_HASH")
        print("Создайте файл .env с этими переменными")
        return
    
    print("🔧 Настройка Telegram сессии...")
    print("Вам потребуется ввести номер телефона и код подтверждения")
    
    # Создаем клиент с именем сессии
    client = TelegramClient('session', api_id, api_hash)
    
    try:
        # Подключаемся и авторизуемся
        await client.start()
        
        # Проверяем, что авторизация прошла успешно
        me = await client.get_me()
        print(f"✅ Успешно авторизованы как: {me.first_name}")
        print(f"📱 Номер телефона: {me.phone}")
        
        # Проверяем доступ к каналу
        try:
            entity = await client.get_entity('varim_ml')
            print(f"✅ Доступ к каналу @varim_ml подтвержден")
            print(f"📊 Название канала: {entity.title}")
        except Exception as e:
            print(f"⚠️ Предупреждение: Не удалось получить доступ к каналу @varim_ml: {e}")
            print("Убедитесь, что вы подписаны на канал")
        
        print("\n🎉 Настройка завершена!")
        print("Теперь можно запускать sync_telegraph.py без интерактивного ввода")
        
    except Exception as e:
        print(f"❌ Ошибка при настройке: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(setup_session())
