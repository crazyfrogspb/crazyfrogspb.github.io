#!/usr/bin/env python3
"""
Скрипт для подготовки данных для RAG-поиска:
1. Чанкинг постов на фрагменты
2. Генерация эмбеддингов через OpenRouter
3. Подготовка данных для клиентского векторного поиска
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List

import aiofiles
import yaml

# Локальная генерация эмбеддингов, .env не нужен

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RAGDataPreparer:
    def __init__(self):
        # Используем только локальные эмбеддинги, API ключи не нужны

        # Пути
        self.root_dir = Path(__file__).parent.parent
        self.posts_dir = self.root_dir / "_posts"
        self.assets_dir = self.root_dir / "assets"
        self.output_dir = self.assets_dir / "rag"

        # Создаем директорию для RAG данных
        self.output_dir.mkdir(exist_ok=True)

        # Конфигурация чанкинга
        self.chunk_size = 512  # символов
        self.chunk_overlap = 50  # символов перекрытия

        # Модели для локальных эмбеддингов (в порядке приоритета для русского языка)
        self.embedding_models = [
            "sergeyzh/rubert-mini-frida",  # Лучшая для русского языка
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # Многоязычная
            "sentence-transformers/distiluse-base-multilingual-cased",  # Альтернатива
            "sentence-transformers/all-MiniLM-L6-v2",  # Быстрая, многоязычная
            "all-MiniLM-L6-v2",  # Короткое имя
            "paraphrase-multilingual-MiniLM-L12-v2",  # Короткое имя
        ]
        self.current_model_index = 0

        # Базовый URL сайта
        self.base_url = "https://crazyfrogspb.github.io"

    async def load_posts(self) -> List[Dict]:
        """Загружает все посты из директории _posts"""
        posts = []

        for post_file in self.posts_dir.glob("*.md"):
            try:
                async with aiofiles.open(post_file, "r", encoding="utf-8") as f:
                    content = await f.read()

                # Парсим front matter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        post_content = parts[2].strip()

                        # Извлекаем URL поста
                        post_url = self.extract_post_url(post_file.stem, front_matter)

                        posts.append(
                            {
                                "id": post_file.stem,
                                "title": front_matter.get("title", ""),
                                "date": front_matter.get("date", ""),
                                "tags": front_matter.get("tags", []),
                                "excerpt": front_matter.get("excerpt", ""),
                                "content": post_content,
                                "url": post_url,
                                "telegraph_url": front_matter.get("telegraph_url"),
                                "telegram_url": front_matter.get("telegram_url"),
                                "views": front_matter.get("views", 0),
                            }
                        )

            except Exception as e:
                logger.warning(f"Ошибка обработки поста {post_file}: {e}")

        logger.info(f"Загружено {len(posts)} постов")
        return posts

    def extract_post_url(self, filename: str, front_matter: Dict) -> str:
        """Извлекает URL поста на основе имени файла"""
        # Формат: YYYY-MM-DD-slug.md
        parts = filename.split("-", 3)
        if len(parts) >= 4:
            year, month, day, slug = parts
            return f"{self.base_url}/{year}/{month}/{day}/{slug}/"
        return f"{self.base_url}/{filename}/"

    def clean_content(self, content: str) -> str:
        """Очищает контент от Markdown разметки для чанкинга"""
        # Убираем изображения
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

        # Убираем ссылки, оставляя текст
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)

        # Убираем Markdown заголовки, оставляя текст
        content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)

        # Убираем жирный и курсивный текст
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^*]+)\*", r"\1", content)

        # Убираем код блоки
        content = re.sub(r"```[^`]*```", "", content, flags=re.DOTALL)
        content = re.sub(r"`([^`]+)`", r"\1", content)

        # Убираем лишние пробелы и переносы
        content = re.sub(r"\n+", " ", content)
        content = re.sub(r"\s+", " ", content)

        return content.strip()

    def create_chunks(self, post: Dict) -> List[Dict]:
        """Создает чанки из поста"""
        content = self.clean_content(post["content"])

        # Если контент короткий, возвращаем как один чанк
        if len(content) <= self.chunk_size:
            return [
                {
                    "post_id": post["id"],
                    "post_title": post["title"],
                    "post_url": post["url"],
                    "chunk_index": 0,
                    "content": content,
                    "type": "content",
                }
            ]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + self.chunk_size

            # Если не последний чанк, ищем ближайший пробел для разрыва
            if end < len(content):
                space_pos = content.rfind(" ", start, end)
                if space_pos > start:
                    end = space_pos

            chunk_content = content[start:end].strip()

            if chunk_content:
                chunks.append(
                    {
                        "post_id": post["id"],
                        "post_title": post["title"],
                        "post_url": post["url"],
                        "chunk_index": chunk_index,
                        "content": chunk_content,
                        "type": "content",
                    }
                )
                chunk_index += 1

            # Следующий чанк начинается с перекрытием
            start = end - self.chunk_overlap
            if start < 0:
                start = end

        return chunks

    def create_summary_chunk(self, post: Dict) -> Dict:
        """Создает чанк из саммари поста"""
        return {
            "post_id": post["id"],
            "post_title": post["title"],
            "post_url": post["url"],
            "chunk_index": -1,  # Специальный индекс для саммари
            "content": post["excerpt"],
            "type": "summary",
        }

    def create_title_chunk(self, post: Dict) -> Dict:
        """Создает чанк из заголовка поста"""
        return {
            "post_id": post["id"],
            "post_title": post["title"],
            "post_url": post["url"],
            "chunk_index": -2,  # Специальный индекс для заголовка
            "content": post["title"],
            "type": "title",
        }

    def generate_embeddings(self, texts_with_prefixes: List[str]) -> List[List[float]]:
        """Генерирует эмбеддинги локально через sentence-transformers с перебором моделей"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers не установлен. Активируйте окружение breastcancer: workon breastcancer")
            return []

        # Перебираем модели до успешной загрузки
        for i in range(self.current_model_index, len(self.embedding_models)):
            model_name = self.embedding_models[i]
            try:
                logger.info(f"Пробуем модель {model_name}...")
                model = SentenceTransformer(model_name)

                # Тестируем на одном тексте
                test_embedding = model.encode(["тест"], convert_to_tensor=False)
                if len(test_embedding) > 0:
                    logger.info(f"Модель {model_name} успешно загружена")
                    self.current_model_index = i

                    # Генерируем эмбеддинги для всех текстов
                    embeddings = model.encode(texts_with_prefixes, convert_to_tensor=False)
                    embeddings = [emb.tolist() for emb in embeddings]

                    logger.info(f"Сгенерировано {len(embeddings)} эмбеддингов с моделью {model_name}")
                    return embeddings

            except Exception as e:
                logger.warning(f"Ошибка с моделью {model_name}: {e}")
                continue

        logger.error("Не удалось загрузить ни одну модель эмбеддингов")
        return []

    def create_text_with_prefix(self, chunk: Dict) -> str:
        """Создает текст с префиксом для эмбеддинга"""
        chunk_type = chunk["type"]
        content = chunk["content"]
        title = chunk["post_title"]

        if chunk_type == "content":
            # Для контентных чанков добавляем префикс поиска документа
            return f"search_document: {title}. {content}"
        elif chunk_type == "summary":
            # Для саммари добавляем префикс поиска документа с указанием что это краткое содержание
            return f"search_document: Краткое содержание: {title}. {content}"
        elif chunk_type == "title":
            # Для заголовков добавляем специальный префикс
            return f"search_document: Заголовок статьи: {content}"
        else:
            # Fallback
            return f"search_document: {content}"

    async def process_posts(self):
        """Основной метод обработки постов"""
        logger.info("Начинаем подготовку данных для RAG")

        # Загружаем посты
        posts = await self.load_posts()
        if not posts:
            logger.error("Посты не найдены")
            return

        # Создаем чанки
        all_chunks = []

        for post in posts:
            # Чанк заголовка
            title_chunk = self.create_title_chunk(post)
            all_chunks.append(title_chunk)

            # Чанк саммари (если есть)
            if post["excerpt"]:
                summary_chunk = self.create_summary_chunk(post)
                all_chunks.append(summary_chunk)

            # Чанки контента
            content_chunks = self.create_chunks(post)
            all_chunks.extend(content_chunks)

        logger.info(f"Создано {len(all_chunks)} чанков")

        # Генерируем эмбеддинги батчами
        batch_size = 100  # Размер батча для локальной обработки
        embeddings = []

        for i in range(0, len(all_chunks), batch_size):
            batch_chunks = all_chunks[i : i + batch_size]
            batch_texts = [self.create_text_with_prefix(chunk) for chunk in batch_chunks]

            logger.info(
                f"Генерируем эмбеддинги для батча {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}"
            )

            batch_embeddings = self.generate_embeddings(batch_texts)
            if not batch_embeddings:
                logger.error(f"Не удалось сгенерировать эмбеддинги для батча {i//batch_size + 1}")
                return

            embeddings.extend(batch_embeddings)

        # Сохраняем данные
        await self.save_rag_data(all_chunks, embeddings)

        logger.info("Подготовка данных для RAG завершена")

    async def save_rag_data(self, chunks: List[Dict], embeddings: List[List[float]]):
        """Сохраняет данные для RAG"""
        # Подготавливаем данные для сохранения
        rag_data = {
            "chunks": [],
            "embeddings": embeddings,
            "metadata": {
                "total_chunks": len(chunks),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "embedding_model": self.embedding_models[self.current_model_index] if embeddings else "none",
                "generation_method": "local",
                "embedding_dimension": len(embeddings[0]) if embeddings else 0,
            },
        }

        # Добавляем чанки без эмбеддингов (они отдельно)
        for chunk in chunks:
            rag_data["chunks"].append(
                {
                    "id": f"{chunk['post_id']}_chunk_{chunk['chunk_index']}",
                    "post_id": chunk["post_id"],
                    "post_title": chunk["post_title"],
                    "post_url": chunk["post_url"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "type": chunk["type"],
                }
            )

        # Сохраняем основной файл
        rag_file = self.output_dir / "rag_data.json"
        async with aiofiles.open(rag_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(rag_data, ensure_ascii=False, indent=2))

        logger.info(f"Данные RAG сохранены в {rag_file}")

        # Создаем компактную версию для загрузки в браузер
        compact_data = {"chunks": rag_data["chunks"], "embeddings": embeddings, "metadata": rag_data["metadata"]}

        compact_file = self.output_dir / "rag_data_compact.json"
        async with aiofiles.open(compact_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(compact_data, ensure_ascii=False, separators=(",", ":")))

        logger.info(f"Компактные данные RAG сохранены в {compact_file}")


async def main():
    preparer = RAGDataPreparer()
    await preparer.process_posts()


if __name__ == "__main__":
    asyncio.run(main())
