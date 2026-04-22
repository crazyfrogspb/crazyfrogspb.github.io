#!/usr/bin/env python3
"""
Скрипт для обновления количества просмотров постов из Telegram
"""

import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
from telethon import TelegramClient
import yaml

load_dotenv()


def build_telethon_proxy():
    """Парсит TELEGRAM_PROXY вида socks5://user:pass@host:port в кортеж для Telethon."""
    raw = os.getenv("TELEGRAM_PROXY")
    if not raw:
        return None
    import socks
    u = urlparse(raw)
    scheme_map = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4, "http": socks.HTTP}
    proxy_type = scheme_map.get(u.scheme.lower())
    if proxy_type is None:
        raise ValueError(f"Unsupported proxy scheme: {u.scheme}")
    user = unquote(u.username) if u.username else None
    pwd = unquote(u.password) if u.password else None
    return (proxy_type, u.hostname, u.port, True, user, pwd)


async def update_views():
    """Обновляет views для всех постов с telegram_url"""

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("❌ Не установлены TELEGRAM_API_ID и TELEGRAM_API_HASH")
        return

    proxy = build_telethon_proxy()
    if proxy:
        print(f"🌐 Используем прокси {proxy[0]} {proxy[1]}:{proxy[2]}")

    # Подключаемся к Telegram
    client = TelegramClient("session", api_id, api_hash, proxy=proxy)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Пользователь не авторизован!")
        await client.disconnect()
        return

    entity = await client.get_entity("varim_ml")
    print(f"✅ Подключено к каналу @varim_ml")

    # Получаем все сообщения с views
    message_views = {}
    print("📊 Получаем просмотры из Telegram...")

    async for message in client.iter_messages(entity, limit=None):
        if message.views:
            message_views[message.id] = message.views

    print(f"✅ Получено {len(message_views)} сообщений с просмотрами")

    # Обновляем посты
    posts_dir = Path('_posts')
    updated_count = 0

    for post_file in posts_dir.glob('*.md'):
        try:
            content = post_file.read_text(encoding='utf-8')

            # Парсим front matter (правильный способ - по строкам)
            if content.startswith('---'):
                lines = content.split('\n')
                fm_end = None
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        fm_end = i
                        break

                if not fm_end:
                    continue

                front_matter_text = '\n'.join(lines[1:fm_end])
                front_matter = yaml.safe_load(front_matter_text)

                # Проверяем есть ли telegram_url
                telegram_url = front_matter.get('telegram_url', '')
                if not telegram_url:
                    continue

                # Извлекаем message_id из URL (формат: https://t.me/varim_ml/170)
                match = re.search(r'/(\d+)$', telegram_url)
                if not match:
                    continue

                message_id = int(match.group(1))

                # Получаем views для этого сообщения
                if message_id not in message_views:
                    print(f"⚠️  Не найдено сообщение {message_id} для {post_file.name}")
                    continue

                new_views = message_views[message_id]
                old_views = front_matter.get('views', 0)

                if new_views != old_views:
                    # Обновляем views в front matter
                    front_matter['views'] = new_views

                    # Формируем новый front matter
                    new_front_matter = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)

                    # Собираем новый контент
                    new_content = f"---\n{new_front_matter}---\n" + '\n'.join(lines[fm_end+1:])

                    # Записываем обратно
                    post_file.write_text(new_content, encoding='utf-8')

                    print(f"✅ {post_file.name}: {old_views} → {new_views}")
                    updated_count += 1

        except Exception as e:
            print(f"❌ Ошибка обработки {post_file}: {e}")
            continue

    await client.disconnect()

    print(f"\n✅ Обновлено постов: {updated_count}")
    print("\n💡 Не забудь запустить:")
    print("   python scripts/update_posts_index.py  # Обновить posts_index.json")


if __name__ == "__main__":
    asyncio.run(update_views())
