#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подготовки RAG данных
"""

import asyncio
import json
import logging
from pathlib import Path

from prepare_rag_data import RAGDataPreparer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rag_data_preparation():
    """Тестирует подготовку RAG данных на небольшом наборе"""
    
    preparer = RAGDataPreparer()
    
    # Загружаем несколько постов для теста
    posts = await preparer.load_posts()
    
    if not posts:
        logger.error("Посты не найдены")
        return
    
    # Берем только первые 3 поста для теста
    test_posts = posts[:3]
    logger.info(f"Тестируем на {len(test_posts)} постах")
    
    # Создаем чанки
    all_chunks = []
    for post in test_posts:
        content_chunks = preparer.create_chunks(post)
        all_chunks.extend(content_chunks)
        
        if post["excerpt"]:
            summary_chunk = preparer.create_summary_chunk(post)
            all_chunks.append(summary_chunk)
    
    logger.info(f"Создано {len(all_chunks)} чанков")
    
    # Показываем примеры чанков
    for i, chunk in enumerate(all_chunks[:5]):
        logger.info(f"Чанк {i+1}: {chunk['type']} - {chunk['content'][:100]}...")
    
    # Тестируем генерацию эмбеддингов на небольшом батче
    test_texts = [chunk["content"] for chunk in all_chunks[:5]]
    
    logger.info("Тестируем генерацию эмбеддингов...")
    embeddings = await preparer.generate_embeddings(test_texts)
    
    if embeddings:
        logger.info(f"Успешно сгенерировано {len(embeddings)} эмбеддингов")
        logger.info(f"Размерность эмбеддингов: {len(embeddings[0])}")
        
        # Сохраняем тестовые данные
        test_data = {
            "chunks": all_chunks[:5],
            "embeddings": embeddings,
            "metadata": {
                "total_chunks": len(embeddings),
                "embedding_dimension": len(embeddings[0]),
                "test_mode": True
            }
        }
        
        test_file = preparer.output_dir / "test_rag_data.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Тестовые данные сохранены в {test_file}")
        
    else:
        logger.error("Не удалось сгенерировать эмбеддинги")


def analyze_existing_data():
    """Анализирует уже созданные RAG данные"""
    
    rag_file = Path(__file__).parent.parent / "assets" / "rag" / "rag_data.json"
    
    if not rag_file.exists():
        logger.info("RAG данные еще не созданы. Запустите prepare_rag_data.py")
        return
    
    with open(rag_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    chunks = data["chunks"]
    embeddings = data["embeddings"]
    metadata = data["metadata"]
    
    logger.info("=== Анализ RAG данных ===")
    logger.info(f"Всего чанков: {len(chunks)}")
    logger.info(f"Размерность эмбеддингов: {metadata.get('embedding_dimension', 'неизвестно')}")
    logger.info(f"Модель эмбеддингов: {metadata.get('embedding_model', 'неизвестно')}")
    
    # Анализ типов чанков
    content_chunks = [c for c in chunks if c["type"] == "content"]
    summary_chunks = [c for c in chunks if c["type"] == "summary"]
    
    logger.info(f"Контентных чанков: {len(content_chunks)}")
    logger.info(f"Саммари чанков: {len(summary_chunks)}")
    
    # Анализ размеров
    chunk_sizes = [len(c["content"]) for c in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes)
    min_size = min(chunk_sizes)
    max_size = max(chunk_sizes)
    
    logger.info(f"Средний размер чанка: {avg_size:.1f} символов")
    logger.info(f"Минимальный размер: {min_size} символов")
    logger.info(f"Максимальный размер: {max_size} символов")
    
    # Анализ постов
    unique_posts = set(c["post_id"] for c in chunks)
    logger.info(f"Уникальных постов: {len(unique_posts)}")
    
    # Примеры чанков
    logger.info("\n=== Примеры чанков ===")
    for chunk_type in ["content", "summary"]:
        example = next((c for c in chunks if c["type"] == chunk_type), None)
        if example:
            logger.info(f"\n{chunk_type.upper()} чанк:")
            logger.info(f"Пост: {example['post_title']}")
            logger.info(f"Содержание: {example['content'][:200]}...")


async def main():
    """Главная функция"""
    
    logger.info("=== Тест подготовки RAG данных ===")
    
    # Анализируем существующие данные
    analyze_existing_data()
    
    # Тестируем подготовку новых данных
    logger.info("\n=== Тестирование подготовки данных ===")
    await test_rag_data_preparation()


if __name__ == "__main__":
    asyncio.run(main())
