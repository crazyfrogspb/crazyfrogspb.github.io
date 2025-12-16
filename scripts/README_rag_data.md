# Подготовка данных для RAG-поиска

Скрипт `prepare_rag_data.py` подготавливает данные для векторного поиска в браузере.

## Что делает скрипт

1. **Загружает все посты** из директории `_posts/`
2. **Создает чанки заголовков** - отдельные чанки из названий постов
3. **Создает саммари-чанки** - отдельные чанки из excerpt постов
4. **Чанкинг контента** - разбивает посты на фрагменты по 512 символов с перекрытием 50 символов
5. **Добавляет префиксы** - `search_document:` для улучшения качества поиска
6. **Генерирует эмбеддинги** - векторные представления с помощью rubert-mini-frida
7. **Сохраняет данные** в формате JSON для загрузки в браузер

## Установка зависимостей

```bash
# Основные зависимости (уже есть в requirements.txt)
pip install aiohttp aiofiles pyyaml python-dotenv

# Для эмбеддингов (ОБЯЗАТЕЛЬНО)
pip install sentence-transformers torch
```

## Настройка

### Локальные эмбеддинги

Скрипт использует **только локальные эмбеддинги** через `sentence-transformers`:

1. **rubert-mini-frida** (приоритет) - лучшая для русского языка
   - Размер модели: ~500MB
   - Размерность: 312
   - Качество: отлично для русского

2. **Запасные модели** (если основная не загрузится):
   - paraphrase-multilingual-MiniLM-L12-v2
   - distiluse-base-multilingual-cased
   - all-MiniLM-L6-v2

**Преимущества:**
- ✅ Бесплатно
- ✅ Работает офлайн
- ✅ Нет лимитов API
- ✅ Приватность (данные не покидают сервер)

**Недостатки:**
- ⚠️ Требует ~2GB RAM
- ⚠️ Первый запуск скачает модель (~500MB)

## Запуск

```bash
cd scripts
python prepare_rag_data.py
```

## Результат

Скрипт создает файлы в `assets/rag/`:

### `rag_data.json` (полная версия)
```json
{
  "chunks": [
    {
      "id": "2025-09-22-post_chunk_0",
      "post_id": "2025-09-22-post",
      "post_title": "Заголовок поста",
      "post_url": "https://crazyfrogspb.github.io/2025/09/22/post/",
      "chunk_index": 0,
      "content": "Текст чанка...",
      "type": "content"
    }
  ],
  "embeddings": [
    [0.1, 0.2, 0.3, ...],  // 384-мерный вектор
  ],
  "metadata": {
    "total_chunks": 1500,
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384
  }
}
```

### `rag_data_compact.json` (для браузера)
Минифицированная версия без отступов для быстрой загрузки.

## Типы чанков

### Content chunks (`type: "content"`)
- Фрагменты основного текста постов
- `chunk_index`: 0, 1, 2, ... (порядковый номер в посте)
- Размер: ~500 символов

### Summary chunks (`type: "summary"`)  
- Саммари постов из поля `excerpt`
- `chunk_index`: -1 (специальный индекс)
- Размер: переменный

## Конфигурация

В классе `RAGDataPreparer` можно настроить:

```python
# Размер чанков
self.chunk_size = 500  # символов
self.chunk_overlap = 50  # символов перекрытия

# Модель эмбеддингов
self.embedding_model = "text-embedding-3-small"  # OpenRouter
# или "all-MiniLM-L6-v2" для локальных

# Размер батча для генерации эмбеддингов
batch_size = 100  # чанков за раз
```

## Обработка контента

Скрипт очищает Markdown разметку:

- ✅ Убирает изображения `![alt](url)`
- ✅ Убирает ссылки, оставляя текст `[text](url)` → `text`
- ✅ Убирает заголовки `### Header` → `Header`
- ✅ Убирает форматирование `**bold**` → `bold`
- ✅ Убирает код блоки
- ✅ Нормализует пробелы

## Размер данных

Примерная оценка для 164 постов:

- **Чанков**: ~1500-2000
- **Эмбеддингов**: 384 измерения × 1500 чанков = ~2.3MB
- **Общий размер**: ~3-4MB (сжимается до ~1MB gzip)

## Обновление данных

Для обновления после добавления новых постов:

```bash
# 1. Синхронизируем посты из Telegram
python scripts/sync_telegraph.py

# 2. Обновляем RAG данные
python scripts/prepare_rag_data.py
```

## Troubleshooting

### sentence-transformers не установлен

```
sentence-transformers не установлен
```

**Решение**:
```bash
pip install sentence-transformers torch
```

### Модель не загружается

```
OSError: Can't load weights for 'sergeyzh/rubert-mini-frida'
```

**Решение**: Скрипт автоматически попробует запасные модели. Убедитесь, что есть доступ к интернету для первой загрузки.

### Мало памяти

```
RuntimeError: CUDA out of memory
```

**Решение**: Уменьшите размер батча в скрипте:

```python
batch_size = 50  # вместо 100
```

### Файлы слишком большие

**Решение**: Увеличьте размер чанков:

```python
self.chunk_size = 800  # вместо 500
```

## Интеграция с фронтендом

Данные загружаются в браузер через:

```javascript
// Загрузка данных
const response = await fetch('/assets/rag/rag_data_compact.json');
const ragData = await response.json();

// Использование
const chunks = ragData.chunks;
const embeddings = ragData.embeddings;
const metadata = ragData.metadata;
```
