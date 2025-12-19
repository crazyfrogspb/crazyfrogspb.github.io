#!/usr/bin/env python3

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, List

import aiofiles
import yaml

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RAGDataPreparer:
    def __init__(self):
        # Пути
        self.root_dir = Path(__file__).parent.parent
        self.posts_dir = self.root_dir / "_posts"
        self.assets_dir = self.root_dir / "assets"
        self.output_dir = self.assets_dir / "rag"

        # Создаем директорию для RAG данных
        self.output_dir.mkdir(exist_ok=True)

        # Конфигурация чанкинга (в токенах!)
        # rubert-mini-frida имеет max_seq_length=512 токенов
        # Префикс занимает ~30 токенов (worst case), остаётся 512-30=482 для контента
        # Используем 448 (87.5% от max) для безопасности
        self.chunk_size = 448  # токенов контента (было 512 символов)
        self.chunk_overlap = 75  # токенов перекрытия (~17%, было 64)

        # Модель для локальных эмбеддингов
        self.embedding_model = "sergeyzh/rubert-mini-frida"

        # Токенайзер (будет загружен при первом использовании)
        self.tokenizer = None

        # Базовый URL сайта
        self.base_url = "https://crazyfrogspb.github.io"

    async def load_posts(self) -> List[Dict]:
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
        # Формат: YYYY-MM-DD-slug.md
        parts = filename.split("-", 3)
        if len(parts) >= 4:
            year, month, day, slug = parts
            return f"{self.base_url}/{year}/{month}/{day}/{slug}/"
        return f"{self.base_url}/{filename}/"

    def clean_content(self, content: str) -> str:
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

    def ensure_tokenizer(self):
        """Загружает токенайзер если ещё не загружен"""
        if self.tokenizer is None:
            try:
                from transformers import AutoTokenizer

                logger.info(f"Загружаем токенайзер для {self.embedding_model}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_model)
                logger.info("✅ Токенайзер загружен")
            except ImportError:
                logger.error("transformers не установлен. Активируйте окружение breastcancer")
                raise
            except Exception as e:
                logger.error(f"Ошибка загрузки токенайзера: {e}")
                raise

    def create_chunks(self, post: Dict) -> List[Dict]:
        """Создает чанки из поста (токенный чанкинг)"""
        # Загружаем токенайзер если нужно
        self.ensure_tokenizer()

        content = self.clean_content(post["content"])

        # Токенизируем весь контент
        tokens = self.tokenizer.encode(content, add_special_tokens=False)

        # Если контент короткий, возвращаем как один чанк
        if len(tokens) <= self.chunk_size:
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
        start_token = 0
        chunk_index = 0

        while start_token < len(tokens):
            # Вырезаем чанк токенов
            end_token = start_token + self.chunk_size

            # Берём токены для текущего чанка
            chunk_tokens = tokens[start_token:end_token]

            # Декодируем обратно в текст
            chunk_content = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()

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
            start_token = end_token - self.chunk_overlap

        return chunks

    def create_summary_chunk(self, post: Dict) -> Dict:
        return {
            "post_id": post["id"],
            "post_title": post["title"],
            "post_url": post["url"],
            "chunk_index": -1,  # Специальный индекс для саммари
            "content": post["excerpt"],
            "type": "summary",
        }

    def create_title_chunk(self, post: Dict) -> Dict:
        return {
            "post_id": post["id"],
            "post_title": post["title"],
            "post_url": post["url"],
            "chunk_index": -2,  # Специальный индекс для заголовка
            "content": post["title"],
            "type": "title",
        }

    def generate_embeddings(self, texts_with_prefixes: List[str]) -> List[List[float]]:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers не установлен. Активируйте окружение breastcancer: workon breastcancer")
            return []

        try:
            logger.info(f"Загружаем модель {self.embedding_model}...")
            model = SentenceTransformer(self.embedding_model)

            # Генерируем эмбеддинги для всех текстов
            embeddings = model.encode(texts_with_prefixes, convert_to_tensor=False)
            embeddings = [emb.tolist() for emb in embeddings]

            logger.info(f"Сгенерировано {len(embeddings)} эмбеддингов с моделью {self.embedding_model}")
            return embeddings

        except Exception as e:
            logger.error(f"Ошибка загрузки модели {self.embedding_model}: {e}")
            return []

    def create_text_with_prefix(self, chunk: Dict) -> str:
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
        logger.info("Начинаем подготовку данных для RAG")

        # Загружаем посты
        posts = await self.load_posts()
        if not posts:
            logger.error("Посты не найдены")
            return

        # Создаем чанки
        all_chunks = []

        for post in posts:
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
                "chunk_size_tokens": self.chunk_size,  # В токенах!
                "chunk_overlap_tokens": self.chunk_overlap,  # В токенах!
                "chunking_method": "token-based",  # Было character-based
                "embedding_model": self.embedding_model if embeddings else "none",
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
