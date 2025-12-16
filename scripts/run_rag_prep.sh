#!/bin/bash

# Скрипт для запуска подготовки RAG данных в окружении breastcancer

echo "=== Подготовка RAG данных для Варим ML ==="

# Проверяем, что мы в правильной директории
if [ ! -f "_config.yml" ]; then
    echo "Ошибка: Запустите скрипт из корня проекта varim_ml"
    exit 1
fi

# Активируем окружение breastcancer
echo "Активируем окружение breastcancer..."
source ~/.virtualenvs/breastcancer/bin/activate

# Проверяем, что sentence-transformers установлен
echo "Проверяем зависимости..."
python -c "import sentence_transformers; print('sentence-transformers OK')" 2>/dev/null || {
    echo "Ошибка: sentence-transformers не найден в окружении breastcancer"
    echo "Установите: pip install sentence-transformers"
    exit 1
}

# Запускаем подготовку данных
echo "Запускаем подготовку RAG данных..."
python scripts/prepare_rag_data.py

# Проверяем результат
if [ -f "assets/rag/rag_data.json" ]; then
    echo "✅ RAG данные успешно созданы!"
    echo "📁 Файлы:"
    ls -lh assets/rag/
    
    echo ""
    echo "📊 Статистика:"
    python -c "
import json
with open('assets/rag/rag_data.json', 'r') as f:
    data = json.load(f)
print(f'Чанков: {len(data[\"chunks\"])}')
print(f'Эмбеддингов: {len(data[\"embeddings\"])}')
print(f'Размерность: {data[\"metadata\"][\"embedding_dimension\"]}')
print(f'Модель: {data[\"metadata\"][\"embedding_model\"]}')
"
else
    echo "❌ Ошибка: RAG данные не созданы"
    exit 1
fi

echo ""
echo "🎉 Готово! Теперь можно переходить к реализации фронтенда."
