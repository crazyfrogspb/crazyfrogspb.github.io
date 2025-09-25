#!/usr/bin/env python3
"""
Тестовый скрипт для проверки очистки имен автора
"""

import sys
from pathlib import Path

# Добавляем путь к основному скрипту
sys.path.append(str(Path(__file__).parent))

from sync_telegraph import TelegraphSyncer

def test_author_cleanup():
    syncer = TelegraphSyncer()
    
    # Тестовый контент с именем автора
    test_content = """Evgeniy Nikitin

# Заголовок статьи

Это основной контент статьи, который должен остаться.

Evgenii Nikitin написал эту статью.

Больше контента здесь."""

    print("Исходный контент:")
    print(test_content)
    print("\n" + "="*50 + "\n")
    
    cleaned = syncer.clean_telegraph_author(test_content)
    
    print("Очищенный контент:")
    print(cleaned)

if __name__ == "__main__":
    test_author_cleanup()
