#!/usr/bin/env python3

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
import httpx
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

load_dotenv()


def get_image_extension(content_type: str, url: str) -> str:
    """Определяет расширение изображения из content-type или URL"""
    if "image/jpeg" in content_type or "image/jpg" in content_type:
        return "jpg"
    elif "image/png" in content_type:
        return "png"
    elif "image/gif" in content_type:
        return "gif"
    elif "image/webp" in content_type:
        return "webp"
    elif "image/svg" in content_type:
        return "svg"

    ext = url.split(".")[-1].split("?")[0].lower()
    return ext if ext in ["jpg", "jpeg", "png", "gif", "webp", "svg"] else "jpg"


# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TelegraphSyncer:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.channel_username = "varim_ml"

        # OpenRouter для генерации саммари
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_client = None
        if self.openrouter_api_key:
            self.openai_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key,
            )

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
        cache_file = self.root_dir / ".processed_urls.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Ошибка загрузки кэша URL: {e}")
        return set()

    def save_processed_urls(self):
        cache_file = self.root_dir / ".processed_urls.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_urls), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша URL: {e}")

    async def get_telegram_messages(self) -> List[Dict]:
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

                # Ищем Telegraph и Google Docs ссылки
                content_urls = self.extract_content_urls(message)
                if not content_urls:
                    continue

                # Извлекаем хэштеги
                hashtags = self.extract_hashtags(message.text)

                messages.append(
                    {
                        "id": message.id,
                        "date": message.date,
                        "text": message.text,
                        "content_urls": content_urls,
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

    def extract_content_urls(self, message) -> List[str]:
        urls = []

        # Проверяем entities
        if hasattr(message, "entities") and message.entities:
            for entity in message.entities:
                if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
                    if isinstance(entity, MessageEntityUrl):
                        url = message.text[entity.offset : entity.offset + entity.length]
                    else:
                        url = entity.url

                    if self.is_telegraph_url(url) or self.is_google_docs_url(url):
                        urls.append(url)

        # Дополнительно ищем в тексте Telegraph
        text_urls = re.findall(r"https?://(?:telegra\.ph|te\.legra\.ph)/[^\s\)]+", message.text or "")
        for url in text_urls:
            # Очищаем URL от лишних символов в конце
            url = re.sub(r"[^\w\-/]+$", "", url)
            if self.is_telegraph_url(url):
                urls.append(url)

        # Ищем Google Docs ссылки
        google_docs_urls = re.findall(r"https?://docs\.google\.com/document/d/[^\s\)]+", message.text or "")
        for url in google_docs_urls:
            # Очищаем URL от лишних символов в конце
            url = re.sub(r"[^\w\-/=?&.]+$", "", url)
            if self.is_google_docs_url(url):
                urls.append(url)

        return list(set(urls))

    def is_telegraph_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc in ["telegra.ph", "te.legra.ph"]

    def is_google_docs_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return "docs.google.com" in parsed.netloc and "/document/" in url

    def extract_hashtags(self, text: str) -> List[str]:
        if not text:
            return []

        hashtags = re.findall(r"#(\w+)", text)
        return list(set(tag.lower() for tag in hashtags))

    async def download_telegraph_content(self, url: str, max_retries: int = 5) -> Optional[Dict]:
        for attempt in range(max_retries):
            try:
                # Увеличиваем таймаут для медленных соединений
                timeout = aiohttp.ClientTimeout(total=60, connect=30)

                # Добавляем заголовки для обхода блокировок
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    logger.info(f"Попытка {attempt + 1}/{max_retries}: загружаем {url}")

                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.warning(f"HTTP {response.status} для {url}")
                            if attempt < max_retries - 1:
                                delay = min(2**attempt * 2, 30)  # Максимум 30 секунд
                                logger.info(f"Ждем {delay} секунд перед повтором...")
                                await asyncio.sleep(delay)
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

                        # Исправляем подписи к картинкам (figcaption -> курсив под картинкой)
                        content = self.fix_image_captions(content)

                        # Убираем имена автора, которые Telegraph добавляет автоматически
                        content = self.clean_telegraph_author(content)

                        # Извлекаем просмотры
                        views = self.extract_views(soup)

                        logger.info(f"Успешно загружен контент: {title}")
                        return {"title": title, "content": content, "views": views, "url": url}

            except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
                logger.error(f"Сетевая ошибка для {url} (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    delay = min(5 * (2**attempt), 60)  # Для сетевых ошибок ждем дольше
                    logger.info(f"Сетевая ошибка, ждем {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue

            except asyncio.TimeoutError as e:
                logger.error(f"Таймаут для {url} (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    delay = min(3 * (2**attempt), 45)
                    logger.info(f"Таймаут, ждем {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue

            except Exception as e:
                logger.error(f"Неожиданная ошибка для {url} (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    delay = min(2**attempt, 20)
                    logger.info(f"Общая ошибка, ждем {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue

        logger.error(f"Не удалось загрузить {url} после {max_retries} попыток")
        return None

    async def download_google_docs_content(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        try:
            # Преобразуем URL в экспортный формат
            if "/edit" in url:
                doc_id_match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", url)
                if doc_id_match:
                    doc_id = doc_id_match.group(1)
                    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
                else:
                    logger.warning(f"Не удалось извлечь ID документа из {url}")
                    return None
            else:
                export_url = url

            for attempt in range(max_retries):
                try:
                    timeout = aiohttp.ClientTimeout(total=30)
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }

                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(export_url, headers=headers) as response:
                            if response.status != 200:
                                logger.warning(f"Ошибка загрузки Google Docs {export_url}: {response.status}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2**attempt)
                                    continue
                                return None

                            html = await response.text()
                            soup = BeautifulSoup(html, "html.parser")

                            # Извлекаем заголовок
                            title_elem = soup.find("title")
                            title = title_elem.get_text().strip() if title_elem else "Google Docs"

                            # Убираем " - Google Docs" из заголовка
                            title = re.sub(r"\s*-\s*Google\s+Docs\s*$", "", title)

                            # Извлекаем основной контент
                            content_div = soup.find("div", {"id": "contents"}) or soup.find("body")
                            if not content_div:
                                logger.warning(f"Не найден контент документа в {url}")
                                return None

                            # Обрабатываем изображения
                            await self.process_images(content_div, session)

                            # Конвертируем в Markdown
                            content = self.h2t.handle(str(content_div))

                            return {"title": title, "content": content, "views": 0, "url": url}

                except Exception as e:
                    logger.error(f"Ошибка загрузки Google Docs {url} (попытка {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

        except Exception as e:
            logger.error(f"Ошибка обработки Google Docs URL {url}: {e}")

        return None

    async def process_images(self, article, session):
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
                # Специальная обработка для Google Drive/Googleusercontent
                if "googleusercontent.com" in src or "drive.google.com" in src:
                    src = await self.process_google_image(src, session)
                    if not src:
                        logger.warning(f"Не удалось обработать Google-изображение")
                        continue

                # Специальная обработка для i.ibb.co через HTTP/2
                if "i.ibb.co" in src or "ibb.co" in src:
                    img_hash = hashlib.md5(src.encode()).hexdigest()[:8]
                    img_filename = await self.download_image_http2(src, img_hash)
                    if img_filename:
                        img["src"] = f"/assets/images/{img_filename}"
                    else:
                        logger.error(f"Не удалось загрузить изображение с i.ibb.co: {src}")
                    continue

                # Скачиваем изображение с правильными заголовками
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                # Повторные попытки для Google-изображений
                max_retries = 3 if ("googleusercontent.com" in src or "drive.google.com" in src) else 1

                success = False
                for attempt in range(max_retries):
                    try:
                        async with session.get(src, headers=headers) as img_response:
                            if img_response.status == 200:
                                img_hash = hashlib.md5(src.encode()).hexdigest()[:8]
                                content_type = img_response.headers.get("content-type", "")
                                img_ext = get_image_extension(content_type, src)
                                img_filename = f"{img_hash}.{img_ext}"
                                img_path = self.images_dir / img_filename

                                # Сохраняем изображение
                                async with aiofiles.open(img_path, "wb") as f:
                                    await f.write(await img_response.read())

                                # Обновляем src в HTML
                                img["src"] = f"/assets/images/{img_filename}"
                                logger.info(f"Сохранено изображение: {img_filename}")
                                success = True
                                break
                            else:
                                logger.warning(f"Ошибка загрузки изображения {src}: HTTP {img_response.status}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2**attempt)

                    except Exception as retry_e:
                        logger.warning(f"Попытка {attempt + 1}/{max_retries} загрузки {src}: {retry_e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2**attempt)

                if not success:
                    logger.error(f"Не удалось загрузить изображение после {max_retries} попыток: {src}")

            except Exception as e:
                logger.warning(f"Ошибка обработки изображения {src}: {e}")

    async def process_google_image(self, src: str, session) -> Optional[str]:
        try:
            # Для Google Drive ссылок пытаемся получить прямую ссылку
            if "drive.google.com" in src:
                # Извлекаем file ID из ссылки
                import re

                file_id_match = re.search(r"/file/d/([a-zA-Z0-9-_]+)", src)
                if file_id_match:
                    file_id = file_id_match.group(1)
                    # Формируем прямую ссылку для скачивания
                    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    return direct_url

            # Для googleusercontent.com просто возвращаем исходный URL
            # но с дополнительными параметрами для обхода ограничений
            if "googleusercontent.com" in src:
                # Добавляем параметры для обхода ограничений
                if "?" in src:
                    return src + "&sz=w2000"  # Запрашиваем большой размер
                else:
                    return src + "?sz=w2000"

            return src

        except Exception as e:
            logger.warning(f"Ошибка обработки Google-изображения {src}: {e}")
            return src

    async def download_image_http2(self, src: str, img_hash: str) -> Optional[str]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # Используем httpx с HTTP/2
            async with httpx.AsyncClient(http2=True, timeout=30.0, follow_redirects=True) as client:
                response = await client.get(src, headers=headers)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    img_ext = get_image_extension(content_type, src)
                    img_filename = f"{img_hash}.{img_ext}"
                    img_path = self.images_dir / img_filename

                    # Сохраняем изображение
                    async with aiofiles.open(img_path, "wb") as f:
                        await f.write(response.content)

                    logger.info(f"Сохранено изображение (HTTP/2): {img_filename}")
                    return img_filename
                else:
                    logger.warning(f"Ошибка загрузки изображения через HTTP/2 {src}: HTTP {response.status_code}")
                    return None

        except Exception as e:
            logger.warning(f"Ошибка загрузки через HTTP/2 {src}: {e}")
            return None

    def fix_image_captions(self, content: str) -> str:
        """Исправляет подписи к картинкам: ![](img)Текст -> ![](img)\n*Текст*"""

        def fix_line(line: str) -> str:
            if not re.search(r"!\[.*?\]\(.*?\)\S", line):
                return line

            parts = []
            remaining = line.strip()

            while remaining:
                m = re.match(r"(!\[[^\]]*\]\([^)]+\))(.*)", remaining)
                if not m:
                    if remaining.strip():
                        parts.append(remaining.strip())
                    break

                img = m.group(1)
                after = m.group(2)

                next_img = re.match(r"(!\[[^\]]*\]\([^)]+\))", after)
                if next_img:
                    parts.append(img)
                    remaining = after
                    continue

                caption_match = re.match(r"(.+?)(!\[.+)", after)
                if caption_match:
                    caption = caption_match.group(1).strip()
                    remaining = caption_match.group(2)
                    parts.append(img)
                    if caption:
                        parts.append("")
                        parts.append(f"*{caption}*")
                    parts.append("")
                else:
                    caption = after.strip()
                    parts.append(img)
                    if caption:
                        parts.append("")
                        parts.append(f"*{caption}*")
                    remaining = ""

            return "\n".join(parts)

        lines = content.split("\n")
        return "\n".join(fix_line(line) for line in lines)

    def clean_telegraph_author(self, content: str) -> str:
        # Список возможных имен автора для удаления
        author_names = ["Evgeniy Nikitin", "Evgenii Nikitin", "Евгений Никитин", "Евгений", "Evgeniy", "Evgenii"]

        lines = content.split("\n")
        cleaned_lines = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Пропускаем первые несколько строк, если они содержат только имя автора
            if i < 3 and line_stripped in author_names:
                continue

            # Убираем строки, которые начинаются с имени автора и содержат мало текста
            if i < 5:  # Проверяем только первые 5 строк
                starts_with_author = any(line_stripped.startswith(name) for name in author_names)
                if starts_with_author and len(line_stripped) < 50:
                    continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def extract_views(self, soup) -> int:
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
        # Транслитерация и очистка заголовка
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")

        # Ограничиваем длину
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")

        return slug or "post"

    async def create_jekyll_post(self, content_data: Dict, message_data: Dict):
        date = message_data["date"]
        title = content_data["title"]
        slug = self.create_post_slug(title, date)

        # Имя файла поста
        filename = f"{date.strftime('%Y-%m-%d')}-{slug}.md"
        post_path = self.posts_dir / filename

        # Проверяем, существует ли уже пост
        if post_path.exists():
            logger.info(f"Пост уже существует: {filename}")
            return

        # Определяем тип источника
        source_url = content_data["url"]
        if self.is_telegraph_url(source_url):
            source_type = "telegraph"
        elif self.is_google_docs_url(source_url):
            source_type = "google_docs"
        else:
            source_type = "unknown"

        # Генерируем саммари
        excerpt = await self.generate_summary(content_data["content"], title)

        # Front matter
        front_matter = {
            "layout": "post",
            "title": title,
            "date": date.strftime("%Y-%m-%d %H:%M:%S %z"),
            "tags": message_data["hashtags"],
            "views": content_data.get("telegram_views", message_data["views"]),
            "source_type": source_type,
            "source_url": source_url,
            "telegram_url": message_data["url"],
            "excerpt": excerpt,
        }

        # Добавляем специфичные поля для Telegraph
        if source_type == "telegraph":
            front_matter["telegraph_url"] = source_url

        # Создаем содержимое поста
        content = (
            f"---\n{yaml.dump(front_matter, allow_unicode=True, default_flow_style=False, width=float('inf'))}---\n\n"
        )
        content += content_data["content"]

        # Сохраняем пост
        async with aiofiles.open(post_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Создан пост: {filename}")

    async def generate_summary(self, content: str, title: str) -> str:
        if not self.openai_client:
            logger.warning("OpenRouter API ключ не настроен, используем простое извлечение")
            return self.create_excerpt(content)

        try:
            # Очищаем контент от Markdown разметки для анализа
            clean_content = re.sub(r"!\[.*?\]\(.*?\)", "", content)  # Убираем изображения
            clean_content = re.sub(r"\[.*?\]\(.*?\)", "", clean_content)  # Убираем ссылки
            clean_content = re.sub(r"[#*`_~]", "", clean_content)  # Убираем Markdown символы
            clean_content = re.sub(r"\n+", " ", clean_content)  # Убираем переносы строк
            clean_content = clean_content.strip()

            # Ограничиваем длину для экономии токенов
            if len(clean_content) > 8000:
                clean_content = clean_content[:8000] + "..."

            prompt = f"""Создай краткое саммари (2-3 предложения) для поста на русском языке. Никак не оценивай личность или опыт автора, не добавляй эмоций, просто опиши, о чём пост.

Заголовок: {title}

Содержание:
{clean_content}

Саммари должно быть информативным для читателя. Авторский стиль саммери должен максимально соответствовать стилю поста. Не говори об "авторе" в третье лице, просто пиши, о чём пост. Отвечай только текстом саммари без дополнительных комментариев."""

            response = await self.openai_client.chat.completions.create(
                model="anthropic/claude-3.5-haiku",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.5,
            )

            summary = response.choices[0].message.content.strip()

            # Проверяем длину и обрезаем если нужно
            if len(summary) > 1000:
                summary = summary[:997] + "..."

            logger.info(f"Сгенерировано саммари: {summary[:50]}...")
            return summary

        except Exception as e:
            logger.warning(f"Ошибка генерации саммари: {e}")
            return self.create_excerpt(content)

    def create_excerpt(self, content: str) -> str:
        # Убираем Markdown разметку и берем первые 150 символов
        text = re.sub(r"[#*`\[\]()]", "", content)
        text = re.sub(r"\n+", " ", text).strip()

        if len(text) > 150:
            text = text[:150].rsplit(" ", 1)[0] + "..."

        return text

    async def update_tag_pages(self, all_tags: Set[str]):
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

                        # Парсим дату из имени файла для правильного URL
                        filename = post_file.stem  # например: "2025-09-22-title"
                        url_path = f"/{post_file.stem}/"

                        # Если имя файла в формате YYYY-MM-DD-title, преобразуем в Jekyll permalink
                        if len(filename) > 10 and filename[4] == "-" and filename[7] == "-":
                            try:
                                year = filename[:4]
                                month = filename[5:7]
                                day = filename[8:10]
                                title_part = filename[11:]  # все после даты
                                url_path = f"/{year}/{month}/{day}/{title_part}/"
                            except (ValueError, IndexError):
                                # Если не удалось распарсить, используем исходный формат
                                pass

                        posts_data.append(
                            {
                                "title": front_matter.get("title", ""),
                                "url": url_path,
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
        logger.info("Начинаем синхронизацию Telegraph статей")

        # Получаем сообщения из Telegram
        messages = await self.get_telegram_messages()
        if not messages:
            logger.warning("Сообщения не найдены")
            return

        all_tags = set()
        processed_count = 0

        for message in messages:
            for content_url in message["content_urls"]:
                if content_url in self.processed_urls:
                    continue

                logger.info(f"Обрабатываем: {content_url}")

                # Скачиваем контент в зависимости от типа URL
                if self.is_telegraph_url(content_url):
                    content_data = await self.download_telegraph_content(content_url)
                elif self.is_google_docs_url(content_url):
                    content_data = await self.download_google_docs_content(content_url)
                else:
                    logger.warning(f"Неподдерживаемый тип URL: {content_url}")
                    continue

                if not content_data:
                    continue

                # Добавляем просмотры из Telegram в content_data
                content_data["telegram_views"] = message["views"]

                # Создаем пост
                await self.create_jekyll_post(content_data, message)

                # Добавляем теги
                all_tags.update(message["hashtags"])

                # Отмечаем как обработанный
                self.processed_urls.add(content_url)
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
