#!/usr/bin/env python3
"""
Скрипт для синхронизации статей Telegraph из канала @varim_ml
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp
import html2text
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TelegraphSyncer:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.channel_username = "varim_ml"

        # Пути
        self.root_dir = Path(__file__).parent.parent
        self.posts_dir = self.root_dir / "_posts"
        self.tags_dir = self.root_dir / "tags"
        self.assets_dir = self.root_dir / "assets"
        self.images_dir = self.assets_dir / "images"

        # Создаем директории
        self.posts_dir.mkdir(exist_ok=True)
        self.tags_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

        # Конвертер HTML в Markdown
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.body_width = 0

        # Кэш обработанных URL
        self.processed_urls = self.load_processed_urls()

    def load_processed_urls(self) -> Set[str]:
        """Загружает список уже обработанных URL"""
        cache_file = self.root_dir / ".processed_urls.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Ошибка загрузки кэша URL: {e}")
        return set()

    def save_processed_urls(self):
        """Сохраняет список обработанных URL"""
        cache_file = self.root_dir / ".processed_urls.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_urls), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша URL: {e}")

    async def get_telegram_messages(self) -> List[Dict]:
        """Получает сообщения из Telegram канала"""
        if not self.api_id or not self.api_hash:
            logger.error("Не установлены TELEGRAM_API_ID и TELEGRAM_API_HASH")
            logger.info("Создайте файл .env с переменными TELEGRAM_API_ID и TELEGRAM_API_HASH")
            return []

        # Проверяем наличие файла сессии
        session_file = self.root_dir / "session.session"
        if not session_file.exists():
            logger.error("Файл сессии не найден!")
            logger.info("Запустите scripts/setup_telegram_session.py для создания сессии")
            return []

        messages = []

        try:
            client = TelegramClient("session", self.api_id, self.api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                logger.error("Пользователь не авторизован!")
                logger.info("Запустите scripts/setup_telegram_session.py для авторизации")
                await client.disconnect()
                return []

            entity = await client.get_entity(self.channel_username)
            logger.info(f"Получение сообщений из канала @{self.channel_username}")

            async for message in client.iter_messages(entity, limit=1000):
                if not message.text:
                    continue

                # Ищем Telegraph ссылки
                telegraph_urls = self.extract_telegraph_urls(message)
                if not telegraph_urls:
                    continue

                # Извлекаем хэштеги
                hashtags = self.extract_hashtags(message.text)

                messages.append(
                    {
                        "id": message.id,
                        "date": message.date,
                        "text": message.text,
                        "telegraph_urls": telegraph_urls,
                        "hashtags": hashtags,
                        "views": message.views if hasattr(message, "views") and message.views else 0,
                        "url": f"https://t.me/{self.channel_username}/{message.id}",
                    }
                )

            logger.info(f"Найдено {len(messages)} сообщений с Telegraph ссылками")
            await client.disconnect()
            return messages

        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")
            return []

    def extract_telegraph_urls(self, message) -> List[str]:
        """Извлекает Telegraph URL из сообщения"""
        urls = []

        # Проверяем entities
        if hasattr(message, "entities") and message.entities:
            for entity in message.entities:
                if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
                    if isinstance(entity, MessageEntityUrl):
                        url = message.text[entity.offset : entity.offset + entity.length]
                    else:
                        url = entity.url

                    if self.is_telegraph_url(url):
                        urls.append(url)

        # Дополнительно ищем в тексте
        text_urls = re.findall(r"https?://(?:telegra\.ph|te\.legra\.ph)/[^\s\)]+", message.text or "")
        for url in text_urls:
            # Очищаем URL от лишних символов в конце
            url = re.sub(r"[^\w\-/]+$", "", url)
            if self.is_telegraph_url(url):
                urls.append(url)

        return list(set(urls))  # Убираем дубликаты

    def is_telegraph_url(self, url: str) -> bool:
        """Проверяет, является ли URL ссылкой на Telegraph"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ["telegra.ph", "te.legra.ph"]
        except:
            return False

    def extract_hashtags(self, text: str) -> List[str]:
        """Извлекает хэштеги из текста"""
        if not text:
            return []

        hashtags = re.findall(r"#(\w+)", text)
        # Приводим к нижнему регистру и убираем дубликаты
        return list(set(tag.lower() for tag in hashtags))

    async def download_telegraph_content(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """Скачивает контент Telegraph статьи с повторными попытками"""
        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.warning(f"Ошибка загрузки {url}: {response.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2**attempt)  # Экспоненциальная задержка
                                continue
                            return None

                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                        # Извлекаем заголовок
                        title_elem = soup.find("h1")
                        title = title_elem.get_text().strip() if title_elem else "Без заголовка"

                        # Извлекаем основной контент
                        article = soup.find("article")
                        if not article:
                            logger.warning(f"Не найден контент статьи в {url}")
                            return None

                        # Обрабатываем изображения
                        await self.process_images(article, session)

                        # Конвертируем в Markdown
                        content = self.h2t.handle(str(article))

                        # Извлекаем просмотры
                        views = self.extract_views(soup)

                        return {"title": title, "content": content, "views": views, "url": url}

            except Exception as e:
                logger.error(f"Ошибка загрузки {url} (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Экспоненциальная задержка
                    continue

        return None

    async def process_images(self, article, session):
        """Обрабатывает изображения в статье"""
        images = article.find_all("img")

        for img in images:
            src = img.get("src")
            if not src:
                continue

            # Делаем URL абсолютным
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://telegra.ph" + src

            try:
                # Скачиваем изображение
                async with session.get(src) as img_response:
                    if img_response.status == 200:
                        # Генерируем имя файла
                        img_hash = hashlib.md5(src.encode()).hexdigest()[:8]
                        img_ext = src.split(".")[-1].split("?")[0] or "jpg"
                        img_filename = f"{img_hash}.{img_ext}"
                        img_path = self.images_dir / img_filename

                        # Сохраняем изображение
                        async with aiofiles.open(img_path, "wb") as f:
                            await f.write(await img_response.read())

                        # Обновляем src в HTML
                        img["src"] = f"/assets/images/{img_filename}"

            except Exception as e:
                logger.warning(f"Ошибка обработки изображения {src}: {e}")

    def extract_views(self, soup) -> int:
        """Извлекает количество просмотров"""
        try:
            views_elem = soup.find("span", class_="tl_article_header_views")
            if views_elem:
                views_text = views_elem.get_text().strip()
                # Извлекаем число из текста типа "1.2K views"
                match = re.search(r"([\d.]+)([KM]?)", views_text)
                if match:
                    num, suffix = match.groups()
                    views = float(num)
                    if suffix == "K":
                        views *= 1000
                    elif suffix == "M":
                        views *= 1000000
                    return int(views)
        except:
            pass
        return 0

    def create_post_slug(self, title: str, date: datetime) -> str:
        """Создает slug для поста"""
        # Транслитерация и очистка заголовка
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")

        # Ограничиваем длину
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")

        return slug or "post"

    async def create_jekyll_post(self, telegraph_data: Dict, message_data: Dict):
        """Создает Jekyll пост"""
        date = message_data["date"]
        title = telegraph_data["title"]
        slug = self.create_post_slug(title, date)

        # Имя файла поста
        filename = f"{date.strftime('%Y-%m-%d')}-{slug}.md"
        post_path = self.posts_dir / filename

        # Проверяем, существует ли уже пост
        if post_path.exists():
            logger.info(f"Пост уже существует: {filename}")
            return

        # Front matter
        front_matter = {
            "layout": "post",
            "title": title,
            "date": date.strftime("%Y-%m-%d %H:%M:%S %z"),
            "tags": message_data["hashtags"],
            "views": telegraph_data["views"],
            "telegraph_url": telegraph_data["url"],
            "telegram_url": message_data["url"],
            "excerpt": self.create_excerpt(telegraph_data["content"]),
        }

        # Создаем содержимое поста
        content = f"---\n{yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)}---\n\n"
        content += telegraph_data["content"]

        # Сохраняем пост
        async with aiofiles.open(post_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Создан пост: {filename}")

    def create_excerpt(self, content: str) -> str:
        """Создает краткое описание поста"""
        # Убираем Markdown разметку и берем первые 150 символов
        text = re.sub(r"[#*`\[\]()]", "", content)
        text = re.sub(r"\n+", " ", text).strip()

        if len(text) > 150:
            text = text[:150].rsplit(" ", 1)[0] + "..."

        return text

    async def update_tag_pages(self, all_tags: Set[str]):
        """Обновляет страницы тегов"""
        for tag in all_tags:
            tag_file = self.tags_dir / f"{tag}.md"

            if not tag_file.exists():
                content = f"""---
layout: tag
tag: {tag}
title: "Посты с тегом #{tag}"
---
"""
                async with aiofiles.open(tag_file, "w", encoding="utf-8") as f:
                    await f.write(content)

                logger.info(f"Создана страница тега: {tag}")

    async def update_posts_index(self):
        """Обновляет индекс постов для фильтрации"""
        posts_data = []

        # Читаем все посты
        for post_file in self.posts_dir.glob("*.md"):
            try:
                async with aiofiles.open(post_file, "r", encoding="utf-8") as f:
                    content = await f.read()

                # Парсим front matter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])

                        posts_data.append(
                            {
                                "title": front_matter.get("title", ""),
                                "url": f"/{post_file.stem}/",
                                "date": front_matter.get("date", ""),
                                "tags": front_matter.get("tags", []),
                                "views": front_matter.get("views", 0),
                                "excerpt": front_matter.get("excerpt", ""),
                                "telegraph_url": front_matter.get("telegraph_url"),
                                "telegram_url": front_matter.get("telegram_url"),
                            }
                        )
            except Exception as e:
                logger.warning(f"Ошибка обработки поста {post_file}: {e}")

        # Сортируем по дате (новые первыми)
        posts_data.sort(key=lambda x: x["date"], reverse=True)

        # Сохраняем индекс
        index_data = {"posts": posts_data, "last_updated": datetime.now().isoformat(), "total_posts": len(posts_data)}

        index_file = self.assets_dir / "posts_index.json"
        async with aiofiles.open(index_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(index_data, ensure_ascii=False, indent=2))

        logger.info(f"Обновлен индекс постов: {len(posts_data)} постов")

    async def sync(self):
        """Основной метод синхронизации"""
        logger.info("Начинаем синхронизацию Telegraph статей")

        # Получаем сообщения из Telegram
        messages = await self.get_telegram_messages()
        if not messages:
            logger.warning("Сообщения не найдены")
            return

        all_tags = set()
        processed_count = 0

        for message in messages:
            for telegraph_url in message["telegraph_urls"]:
                if telegraph_url in self.processed_urls:
                    continue

                logger.info(f"Обрабатываем: {telegraph_url}")

                # Скачиваем контент
                telegraph_data = await self.download_telegraph_content(telegraph_url)
                if not telegraph_data:
                    continue

                # Создаем пост
                await self.create_jekyll_post(telegraph_data, message)

                # Добавляем теги
                all_tags.update(message["hashtags"])

                # Отмечаем как обработанный
                self.processed_urls.add(telegraph_url)
                processed_count += 1

                # Небольшая пауза между запросами
                await asyncio.sleep(1)

        # Обновляем страницы тегов
        await self.update_tag_pages(all_tags)

        # Обновляем индекс постов
        await self.update_posts_index()

        # Сохраняем кэш
        self.save_processed_urls()

        logger.info(f"Синхронизация завершена. Обработано {processed_count} новых статей")


async def main():
    syncer = TelegraphSyncer()
    await syncer.sync()


if __name__ == "__main__":
    asyncio.run(main())
