#!/usr/bin/env python3
"""
Тестовый скрипт для проверки получения просмотров из Telegram
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

async def test_views():
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        print("Не установлены TELEGRAM_API_ID и TELEGRAM_API_HASH")
        return
    
    client = TelegramClient("session", api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Пользователь не авторизован!")
        return
    
    entity = await client.get_entity("varim_ml")
    print(f"Получение сообщений из канала @varim_ml")
    
    count = 0
    async for message in client.iter_messages(entity, limit=10):
        if not message.text:
            continue
            
        if "telegra.ph" in message.text or "docs.google.com" in message.text:
            views = message.views if hasattr(message, "views") and message.views else 0
            print(f"ID: {message.id}, Просмотры: {views}, Дата: {message.date}")
            print(f"Текст: {message.text[:100]}...")
            print("-" * 50)
            count += 1
            
        if count >= 5:
            break
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_views())
