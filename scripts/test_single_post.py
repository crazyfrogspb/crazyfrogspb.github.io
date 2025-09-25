#!/usr/bin/env python3
"""
Тестовый скрипт для проверки синхронизации одного поста
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к основному скрипту
sys.path.append(str(Path(__file__).parent))

from sync_telegraph import TelegraphSyncer


async def test_single_post():
    syncer = TelegraphSyncer()

    # Получаем сообщения
    messages = await syncer.get_telegram_messages()
    if not messages:
        print("Сообщения не найдены")
        return

    # Берем первое сообщение с Telegraph ссылкой
    for message in messages[:3]:  # Проверяем первые 3 сообщения
        for content_url in message["content_urls"]:
            print(f"Тестируем: {content_url}")
            print(f"Просмотры в Telegram: {message['views']}")

            # Скачиваем контент
            if syncer.is_telegraph_url(content_url):
                content_data = await syncer.download_telegraph_content(content_url)
            elif syncer.is_google_docs_url(content_url):
                content_data = await syncer.download_google_docs_content(content_url)
            else:
                continue

            if not content_data:
                print("Не удалось загрузить контент")
                continue

            print(f"Заголовок: {content_data['title']}")
            print(f"Просмотры из Telegraph: {content_data.get('views', 0)}")

            # Добавляем просмотры из Telegram
            content_data["telegram_views"] = message["views"]

            # Генерируем саммари (если настроен OpenRouter)
            if syncer.openai_client:
                summary = await syncer.generate_summary(content_data["content"], content_data["title"])
                print(f"Сгенерированное саммари ({len(summary)} символов): {summary}")
            else:
                print("OpenRouter не настроен, используем простое извлечение")
                summary = syncer.create_excerpt(content_data["content"])
                print(f"Простое извлечение ({len(summary)} символов): {summary}")

            return  # Тестируем только один пост


if __name__ == "__main__":
    asyncio.run(test_single_post())
