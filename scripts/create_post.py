#!/usr/bin/env python3
"""
Скрипт для создания нового поста вручную с интерактивным шаблоном
"""

import asyncio
import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
import aiohttp
import yaml
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telethon import TelegramClient

# Загружаем переменные из .env
load_dotenv()


class PostCreator:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.posts_dir = self.root_dir / "_posts"
        self.images_dir = self.root_dir / "assets" / "images"

        # Создаем директорию для изображений
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Telegram API (для получения просмотров)
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.channel_username = "varim_ml"

        # OpenRouter для генерации excerpt
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_client = None
        if self.openrouter_api_key:
            self.openai_client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_api_key,
            )

    def slugify(self, text: str) -> str:
        """Создает slug из текста"""
        # Транслитерация кириллицы
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }

        text = text.lower()
        result = []
        for char in text:
            if char in translit_map:
                result.append(translit_map[char])
            elif char.isalnum() or char in ['-', '_']:
                result.append(char)
            elif char.isspace():
                result.append('-')

        slug = ''.join(result)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')

        # Ограничиваем длину
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')

        return slug or 'post'

    async def get_telegram_views(self, message_url: str) -> Optional[int]:
        """Получает количество просмотров из Telegram сообщения"""
        if not self.api_id or not self.api_hash:
            print("⚠️  TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены")
            return None

        # Извлекаем ID сообщения из URL
        match = re.search(r't\.me/\w+/(\d+)', message_url)
        if not match:
            print("⚠️  Не удалось извлечь ID сообщения из URL")
            return None

        message_id = int(match.group(1))

        try:
            session_file = self.root_dir / "session.session"
            if not session_file.exists():
                print("⚠️  Файл сессии не найден. Запустите scripts/setup_telegram_session.py")
                return None

            client = TelegramClient("session", self.api_id, self.api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                print("⚠️  Пользователь не авторизован")
                await client.disconnect()
                return None

            entity = await client.get_entity(self.channel_username)
            message = await client.get_messages(entity, ids=message_id)

            views = message.views if hasattr(message, 'views') and message.views else 0

            await client.disconnect()
            return views

        except Exception as e:
            print(f"⚠️  Ошибка получения просмотров: {e}")
            return None

    async def download_image(self, url: str) -> Optional[str]:
        """Скачивает изображение по URL и возвращает имя файла"""
        try:
            # Генерируем hash для имени файла
            img_hash = hashlib.md5(url.encode()).hexdigest()[:8]

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        print(f"⚠️  Ошибка скачивания {url}: HTTP {response.status}")
                        return None

                    # Определяем расширение
                    content_type = response.headers.get("content-type", "")
                    if "image/jpeg" in content_type or "image/jpg" in content_type:
                        img_ext = "jpg"
                    elif "image/png" in content_type:
                        img_ext = "png"
                    elif "image/gif" in content_type:
                        img_ext = "gif"
                    elif "image/webp" in content_type:
                        img_ext = "webp"
                    elif "image/svg" in content_type:
                        img_ext = "svg"
                    else:
                        # Пытаемся извлечь из URL
                        img_ext = url.split(".")[-1].split("?")[0].lower()
                        if img_ext not in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
                            img_ext = "jpg"

                    img_filename = f"{img_hash}.{img_ext}"
                    img_path = self.images_dir / img_filename

                    # Сохраняем изображение
                    async with aiofiles.open(img_path, "wb") as f:
                        await f.write(await response.read())

                    print(f"✅ Скачано: {img_filename} ({url})")
                    return img_filename

        except Exception as e:
            print(f"⚠️  Ошибка скачивания {url}: {e}")
            return None

    def copy_local_image(self, local_path: str) -> Optional[str]:
        """Копирует локальное изображение и возвращает имя файла"""
        try:
            source = Path(local_path).expanduser()

            # Если относительный путь, пробуем от корня проекта
            if not source.is_absolute():
                source = (self.root_dir / source).resolve()
            else:
                source = source.resolve()

            if not source.exists():
                print(f"⚠️  Файл не найден: {local_path}")
                return None

            # Генерируем hash для имени файла
            img_hash = hashlib.md5(str(source).encode()).hexdigest()[:8]
            img_ext = source.suffix.lstrip(".")

            if not img_ext or img_ext not in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
                img_ext = "jpg"

            img_filename = f"{img_hash}.{img_ext}"
            img_path = self.images_dir / img_filename

            # Копируем файл
            shutil.copy2(source, img_path)
            print(f"✅ Скопировано: {img_filename} ({local_path})")
            return img_filename

        except Exception as e:
            print(f"⚠️  Ошибка копирования {local_path}: {e}")
            return None

    async def process_images_in_content(self, content: str) -> str:
        """Обрабатывает все изображения в Markdown контенте"""
        print("\n🖼️  Обрабатываем изображения...")

        # Паттерн для Markdown изображений: ![alt](path)
        image_pattern = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')

        processed_content = content
        matches = list(image_pattern.finditer(content))

        if not matches:
            print("   Изображений не найдено")
            return content

        print(f"   Найдено изображений: {len(matches)}")

        for match in matches:
            alt_text = match.group(1)
            image_path = match.group(2)

            # Пропускаем если уже правильный путь
            if image_path.startswith("/assets/images/"):
                print(f"⏭️  Пропускаем (уже обработано): {image_path}")
                continue

            # Определяем тип: URL или локальный путь
            is_url = image_path.startswith(("http://", "https://", "//"))

            if is_url:
                # Скачиваем из интернета
                if image_path.startswith("//"):
                    image_path = "https:" + image_path
                new_filename = await self.download_image(image_path)
            else:
                # Копируем локальный файл
                new_filename = self.copy_local_image(image_path)

            if new_filename:
                new_path = f"/assets/images/{new_filename}"
                old_markdown = f"![{alt_text}]({image_path})"
                new_markdown = f"![{alt_text}]({new_path})"
                processed_content = processed_content.replace(old_markdown, new_markdown)

        print("✅ Обработка изображений завершена\n")
        return processed_content

    async def generate_excerpt(self, content: str, title: str) -> Optional[str]:
        """Генерирует excerpt через LLM"""
        if not self.openai_client:
            print("⚠️  OPENROUTER_API_KEY не настроен, пропускаем генерацию excerpt")
            return None

        try:
            # Очищаем контент от Markdown разметки
            clean_content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
            clean_content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_content)
            clean_content = re.sub(r"[#*`_~]", "", clean_content)
            clean_content = re.sub(r"\n+", " ", clean_content)
            clean_content = clean_content.strip()

            # Ограничиваем длину
            if len(clean_content) > 8000:
                clean_content = clean_content[:8000] + "..."

            prompt = f"""Создай краткое саммари (2-3 предложения) для поста на русском языке. Никак не оценивай личность или опыт автора, не добавляй эмоций, просто опиши, о чём пост.

Заголовок: {title}

Содержание:
{clean_content}

Саммари должно быть информативным для читателя. Авторский стиль саммери должен максимально соответствовать стилю поста. Не говори об "авторе" в третье лице, просто пиши, о чём пост. Отвечай только текстом саммари без дополнительных комментариев."""

            print("🤖 Генерируем excerpt через Claude 3.5 Haiku...")
            response = await self.openai_client.chat.completions.create(
                model="anthropic/claude-3.5-haiku",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.5,
            )

            excerpt = response.choices[0].message.content.strip()

            if len(excerpt) > 1000:
                excerpt = excerpt[:997] + "..."

            print(f"✅ Excerpt сгенерирован: {excerpt[:80]}...")
            return excerpt

        except Exception as e:
            print(f"⚠️  Ошибка генерации excerpt: {e}")
            return None

    async def create_post(self):
        """Интерактивное создание поста"""
        print("=" * 70)
        print("📝 Создание нового поста для Варим ML")
        print("=" * 70)
        print()

        # 1. Заголовок
        title = input("Заголовок поста: ").strip()
        if not title:
            print("❌ Заголовок обязателен")
            return

        # 2. Slug (автоматически или вручную)
        suggested_slug = self.slugify(title)
        print(f"\nПредложенный slug: {suggested_slug}")
        custom_slug = input("Нажмите Enter для использования или введите свой: ").strip()
        slug = custom_slug if custom_slug else suggested_slug

        # 3. Дата
        print(f"\nТекущая дата/время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        custom_date = input("Нажмите Enter для использования текущей или введите дату (YYYY-MM-DD HH:MM:SS): ").strip()

        if custom_date:
            try:
                post_date = datetime.strptime(custom_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print("⚠️  Неверный формат даты, используем текущую")
                post_date = datetime.now()
        else:
            post_date = datetime.now()

        # 4. Теги
        print("\nТеги (через запятую, например: жека, llm, research)")
        tags_input = input("Теги: ").strip()
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        # 5. Telegram URL (опционально)
        telegram_url = input("\nTelegram URL (опционально, для получения просмотров): ").strip()

        views = 0
        if telegram_url:
            print("🔍 Получаем просмотры из Telegram...")
            views = await self.get_telegram_views(telegram_url)
            if views is not None:
                print(f"✅ Просмотров: {views}")
            else:
                views_input = input("Не удалось получить автоматически. Введите количество просмотров вручную (или 0): ").strip()
                views = int(views_input) if views_input.isdigit() else 0
        else:
            views_input = input("Количество просмотров (или 0): ").strip()
            views = int(views_input) if views_input.isdigit() else 0

        # 6. Source type
        print("\nТип источника (например: direct, manual, medium, habr, custom)")
        source_type = input("Source type [direct]: ").strip() or "direct"

        # 7. Source URL (опционально)
        source_url = input("Source URL (опционально): ").strip()

        # 8. Контент
        print("\n" + "=" * 70)
        print("Способ ввода контента:")
        print("  1) Вставить вручную (завершите тройным Enter)")
        print("  2) Загрузить из файла")
        print("=" * 70)

        content_method = input("Выберите способ [1/2]: ").strip() or "1"

        if content_method == "2":
            # Загрузка из файла
            content_file = input("Путь к файлу с контентом (Markdown): ").strip()
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                print(f"✅ Загружено {len(content)} символов")
            except Exception as e:
                print(f"❌ Ошибка чтения файла: {e}")
                return
        else:
            # Ручной ввод
            print("\nВведите контент поста в Markdown (завершите тройным Enter):")
            content_lines = []
            empty_count = 0
            while True:
                line = input()
                if line == "":
                    empty_count += 1
                    if empty_count >= 3:
                        break
                else:
                    # Добавляем накопленные пустые строки
                    content_lines.extend([""] * empty_count)
                    empty_count = 0
                    content_lines.append(line)

            content = "\n".join(content_lines).strip()

        if not content:
            print("❌ Контент не может быть пустым")
            return

        # 9. Обработка изображений
        content = await self.process_images_in_content(content)

        # 10. Excerpt (автоматически или вручную)
        print("\n" + "=" * 70)
        generate_excerpt = input("Сгенерировать excerpt автоматически через LLM? [Y/n]: ").strip().lower()

        excerpt = None
        if generate_excerpt != 'n':
            excerpt = await self.generate_excerpt(content, title)

        if not excerpt:
            print("Введите excerpt вручную (2-3 предложения):")
            excerpt = input().strip()
            if not excerpt:
                # Создаем простой excerpt из первых 150 символов
                text = re.sub(r"[#*`\[\]()]", "", content)
                text = re.sub(r"\n+", " ", text).strip()
                if len(text) > 150:
                    excerpt = text[:150].rsplit(" ", 1)[0] + "..."
                else:
                    excerpt = text

        # 11. Создаем файл
        filename = f"{post_date.strftime('%Y-%m-%d')}-{slug}.md"
        post_path = self.posts_dir / filename

        if post_path.exists():
            overwrite = input(f"\n⚠️  Файл {filename} уже существует. Перезаписать? [y/N]: ").strip().lower()
            if overwrite != 'y':
                print("❌ Отменено")
                return

        # Формируем front matter
        front_matter = {
            "layout": "post",
            "title": title,
            "date": post_date.strftime("%Y-%m-%d %H:%M:%S +0000"),
            "tags": tags,
            "views": views,
            "source_type": source_type,
            "excerpt": excerpt,
        }

        if source_url:
            front_matter["source_url"] = source_url

        if telegram_url:
            front_matter["telegram_url"] = telegram_url

        # Создаем содержимое файла
        post_content = f"---\n{yaml.dump(front_matter, allow_unicode=True, default_flow_style=False, width=float('inf'))}---\n\n{content}\n"

        # Сохраняем
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(post_content)

        print("\n" + "=" * 70)
        print(f"✅ Пост создан: {post_path}")
        print("=" * 70)

        # 12. Обновляем индекс
        update_index = input("\nОбновить posts_index.json? [Y/n]: ").strip().lower()
        if update_index != 'n':
            import subprocess
            try:
                result = subprocess.run(
                    ["python", "scripts/update_posts_index.py"],
                    cwd=self.root_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("✅ Индекс обновлен")
                else:
                    print(f"⚠️  Ошибка обновления индекса: {result.stderr}")
            except Exception as e:
                print(f"⚠️  Не удалось обновить индекс: {e}")
                print("Запустите вручную: python scripts/update_posts_index.py")

        # 13. Пересоздать RAG данные?
        update_rag = input("\nПересоздать RAG данные? (требует окружение breastcancer) [y/N]: ").strip().lower()
        if update_rag == 'y':
            try:
                # Пробуем импортировать и запустить prepare_rag_data
                print("\n📊 Обновляем RAG данные...")
                from prepare_rag_data import RAGDataPreparer

                rag_preparer = RAGDataPreparer()
                await rag_preparer.process_posts()

                print("✅ RAG данные обновлены")
                print("\n💡 Не забудь загрузить модель на HuggingFace если нужно:")
                print("  python scripts/upload_to_hf.py")

            except ImportError as e:
                print("\n⚠️  sentence-transformers не установлен.")
                print("📊 Запустите вручную:")
                print("  workon breastcancer")
                print("  python scripts/prepare_rag_data.py")
                print("  python scripts/upload_to_hf.py  # если нужно загрузить на HuggingFace")
            except Exception as e:
                print(f"\n❌ Ошибка обновления RAG данных: {e}")
                print("📊 Запустите вручную:")
                print("  python scripts/prepare_rag_data.py")

        print("\n🎉 Готово!")


async def main():
    creator = PostCreator()
    await creator.create_post()


if __name__ == "__main__":
    asyncio.run(main())
