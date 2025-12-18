# Полная документация блога "Варим ML" и RAG-системы

## Оглавление

1. [О проекте](#о-проекте)
2. [Блог на Jekyll и GitHub Pages](#блог-на-jekyll-и-github-pages)
3. [Workflow добавления постов](#workflow-добавления-постов)
4. [Обзор RAG-системы](#обзор-rag-системы)
5. [Архитектура RAG](#архитектура-rag)
6. [Data Preparation (Подготовка данных)](#data-preparation)
7. [ML компоненты](#ml-компоненты)
8. [Frontend компоненты](#frontend-компоненты)
9. [Backend компоненты](#backend-компоненты)
10. [Оптимизации и особенности](#оптимизации-и-особенности)
11. [Deployment и инфраструктура](#deployment-и-инфраструктура)
12. [Технические детали](#технические-детали)

---

## О проекте

**"Варим ML"** — это телеграм-канал и статический блог о машинном обучении, data science, MLOps и карьере в IT.

### Основные компоненты проекта:

1. **Telegram канал**: [@varim_ml](https://t.me/varim_ml) — основная площадка для публикаций
2. **Статический блог**: [crazyfrogspb.github.io](https://crazyfrogspb.github.io) — Jekyll сайт на GitHub Pages
3. **Telegraph статьи**: Длинные посты публикуются на [telegra.ph](https://telegra.ph)
4. **RAG-чат**: Интерактивный поиск и Q&A по контенту блога

### Технологический стек:

**Блог**:
- Jekyll 4.x (статический генератор сайтов)
- GitHub Pages (хостинг)
- Minima theme (кастомизированная тема)
- Markdown (формат постов)

**Автоматизация**:
- Python 3.x (скрипты для синхронизации)
- Telethon (Telegram API)
- OpenRouter API (генерация саммари)
- BeautifulSoup (парсинг HTML)

**RAG система**:
- ONNX Runtime Web (ML inference в браузере)
- Cloudflare Workers (serverless backend)
- OpenRouter API (LLM генерация)
- IndexedDB (кэширование модели)

---

## Блог на Jekyll и GitHub Pages

### Структура проекта

```
varim_ml/
├── _config.yml                 # Jekyll конфигурация
├── _posts/                     # Посты блога (Markdown)
│   ├── 2023-02-10-post.md
│   ├── 2025-11-11-post.md
│   └── ...
├── _layouts/                   # HTML шаблоны
│   ├── default.html
│   ├── post.html
│   └── tag.html
├── _includes/                  # Переиспользуемые компоненты
│   ├── header.html
│   ├── footer.html
│   └── ...
├── _site/                      # Сгенерированный сайт (git ignored)
├── assets/
│   ├── images/                 # Изображения постов
│   ├── js/                     # JavaScript
│   │   ├── vector-search.js
│   │   └── embedding-worker.js
│   ├── rag/                    # RAG данные
│   │   ├── rag_data.json
│   │   └── rag_data_compact.json
│   ├── onnx/                   # ONNX конфиг
│   └── posts_index.json        # Индекс всех постов
├── scripts/                    # Python скрипты
│   ├── sync_telegraph.py       # Синхронизация из Telegram
│   ├── prepare_rag_data.py     # Подготовка RAG данных
│   ├── create_post.py          # Создание поста вручную
│   ├── update_posts_index.py   # Обновление индекса
│   └── upload_to_hf.py         # Загрузка модели на HuggingFace
├── tags/                       # Страницы тегов
│   ├── жека.md
│   ├── llm.md
│   └── ...
├── index.html                  # Главная страница
├── rag-chat.html              # Страница RAG-чата
├── Gemfile                     # Ruby зависимости
├── .env                        # API ключи (git ignored)
└── README.md
```

### Jekyll конфигурация (`_config.yml`)

```yaml
title: Варим ML
description: Телеграм-канал о машинном обучении, data science и карьере в IT
baseurl: ""
url: "https://crazyfrogspb.github.io"

# Сборка
markdown: kramdown
theme: minima
plugins:
  - jekyll-feed
  - jekyll-seo-tag

# Permalink формат
permalink: /:year/:month/:day/:title/

# Exclude из сборки
exclude:
  - scripts/
  - cloudflare-worker/
  - .env
  - Gemfile
  - Gemfile.lock
```

### Формат поста

Каждый пост — это Markdown файл с YAML front matter:

**Имя файла**: `YYYY-MM-DD-slug.md` (например `2025-11-11-тревога-в-мире-llm.md`)

**Содержимое**:
```markdown
---
layout: post
title: "Тревога в мире LLM"
date: 2025-11-11 14:31:02 +0000
tags:
  - жека
  - llm
views: 2229
source_type: telegraph
source_url: https://telegra.ph/Trevoga-v-mire-LLM-11-10
telegram_url: https://t.me/varim_ml/168
telegraph_url: https://telegra.ph/Trevoga-v-mire-LLM-11-10
excerpt: |
  Пост посвящен растущей тревоге в мире LLM из-за отсутствия
  прорывов и замедления развития моделей.
---

# Введение

Контент поста в Markdown...

![Изображение](/assets/images/a1b2c3d4.png)

## Заключение

Выводы...
```

### Деплой на GitHub Pages

**Автоматический деплой** через GitHub Actions:

1. Push в `master` ветку
2. GitHub автоматически запускает Jekyll build
3. Сгенерированный сайт публикуется на `https://crazyfrogspb.github.io`
4. ~1-2 минуты до появления изменений

**Локальная разработка**:
```bash
# Установка зависимостей
bundle install

# Локальный сервер (http://localhost:4000)
bundle exec jekyll serve

# С автообновлением
bundle exec jekyll serve --livereload
```

**Что происходит при деплое**:

1. Jekyll читает `_posts/*.md`
2. Генерирует HTML из Markdown (через kramdown)
3. Применяет layouts из `_layouts/`
4. Копирует статику из `assets/`
5. Создает feed.xml (RSS)
6. Публикует в `_site/` → GitHub Pages

### URL структура

| Тип | URL | Файл |
|-----|-----|------|
| Главная | `/` | `index.html` |
| Пост | `/2023/02/10/post-slug/` | `_posts/2023-02-10-post-slug.md` |
| Тег | `/tags/жека/` | `tags/жека.md` |
| RAG чат | `/rag-chat.html` | `rag-chat.html` |
| Статика | `/assets/images/pic.jpg` | `assets/images/pic.jpg` |

---

## Workflow добавления постов

### Вариант 1: Автоматическая синхронизация из Telegram

**Используется**: Для постов опубликованных в [@varim_ml](https://t.me/varim_ml) с ссылками на Telegraph/Google Docs.

**Скрипт**: `scripts/sync_telegraph.py`

**Процесс**:

```bash
# 1. Настройка API ключей (один раз)
# Создать .env файл:
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
OPENROUTER_API_KEY=your_key

# 2. Авторизация в Telegram (один раз)
python scripts/setup_telegram_session.py

# 3. Синхронизация постов
python scripts/sync_telegraph.py
```

**Что делает скрипт**:

1. **Подключается к Telegram** через Telethon API
2. **Сканирует канал** @varim_ml (последние 1000 сообщений)
3. **Находит ссылки** на Telegraph или Google Docs
4. **Скачивает контент**:
   - HTML → Markdown конвертация
   - Изображения → `assets/images/`
   - Просмотры из Telegram API
5. **Генерирует excerpt** через Claude 3.5 Haiku (OpenRouter)
6. **Создает пост** в `_posts/YYYY-MM-DD-slug.md`
7. **Обновляет теги** (создает `tags/tag.md` если нужно)
8. **Обновляет индекс** (`assets/posts_index.json`)

**Кеширование**: Скрипт помнит обработанные URL (`.processed_urls.json`), не дублирует посты.

### Вариант 2: Ручное создание поста

**Используется**: Для постов написанных напрямую, без Telegraph.

**Скрипт**: `scripts/create_post.py`

**Процесс**:

```bash
python scripts/create_post.py
```

**Интерактивный процесс**:

1. **Заголовок**: Вводится вручную
2. **Slug**: Автогенерация из заголовка (транслитерация) или вручную
3. **Дата**: Текущая или кастомная
4. **Теги**: Через запятую (например: `жека, llm, research`)
5. **Telegram URL** (опционально): Для получения просмотров через API
6. **Views**: Автоматически из Telegram или вручную
7. **Source type**: `direct`, `medium`, `habr`, custom
8. **Контент**:
   - Вариант A: Загрузка из файла (Markdown)
   - Вариант B: Ввод вручную (тройной Enter для завершения)
9. **Обработка изображений**:
   - Локальные пути → копируются в `assets/images/`
   - URL → скачиваются в `assets/images/`
   - Ссылки автоматически заменяются на `/assets/images/{hash}.{ext}`
10. **Excerpt**: Автогенерация через LLM или ввод вручную
11. **Сохранение**: Создается `_posts/YYYY-MM-DD-slug.md`
12. **Обновление индекса**: Автоматически запускается `update_posts_index.py`
13. **Обновление RAG данных** (опционально): Скрипт предложит пересоздать RAG данные
    - Если окружение `breastcancer` активно → автоматически обновляет
    - Если нет → показывает инструкцию для ручного запуска

### Обновление RAG данных

#### Автоматически (при создании поста)

При запуске `create_post.py` в конце будет вопрос:

```
Пересоздать RAG данные? (требует окружение breastcancer) [y/N]: y
```

**Если окружение активно**:
```bash
# Активируй окружение ПЕРЕД запуском create_post.py
workon breastcancer
python scripts/create_post.py
# ... создание поста ...
# → RAG данные обновятся автоматически
```

**Если окружение не активно** - скрипт покажет инструкцию для ручного запуска.

#### Вручную (если пропустил или обновляешь старые посты)

```bash
# Активировать virtualenv с sentence-transformers
workon breastcancer

# Пересоздать RAG данные
python scripts/prepare_rag_data.py

# Загрузить модель на HuggingFace (если обновилась)
python scripts/upload_to_hf.py
```

**Что происходит**:

1. Читает все посты из `_posts/`
2. Чанкинг контента (512 символов, 50 overlap)
3. Генерация эмбеддингов (rubert-mini-frida)
4. Сохранение в `assets/rag/rag_data_compact.json` (~15MB)

### Деплой изменений

```bash
# 1. Коммит изменений
git add _posts/ assets/ tags/
git commit -m "Add new post: название"

# 2. Push в GitHub
git push origin master

# 3. GitHub Pages автоматически деплоит
# Ждем 1-2 минуты

# 4. Проверяем
# https://crazyfrogspb.github.io
```

---

## Обзор RAG-системы

**RAG-система** (Retrieval-Augmented Generation) для блога "Варим ML" - это полнофункциональная поисково-разговорная система, работающая **полностью в браузере пользователя** с бэкендом на Cloudflare Workers.

### Ключевые особенности:

- **Локальный ML inference в браузере**: ONNX модель rubert-mini-frida (123MB) запускается локально
- **Hybrid search**: Комбинация BM25 (keyword) + семантический поиск (30%/70%)
- **Query rephrasing**: Автоматическое переформулирование follow-up вопросов
- **Chat history**: Контекстная память последних 6 сообщений (3 Q&A пары)
- **LLM validation**: Валидация запросов на соответствие тематике блога
- **Serverless backend**: Cloudflare Workers с rate limiting и CORS
- **IndexedDB caching**: Модель кешируется локально после первой загрузки
- **Cited sources filtering**: Показываем только процитированные источники

---

## Архитектура RAG

```
┌─────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛЬ                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (rag-chat.html)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  RAGChat Controller                                     │ │
│  │  - Управление UI                                        │ │
│  │  - Chat history (последние 6 сообщений)               │ │
│  │  - Query rephrasing для follow-up вопросов            │ │
│  │  - Извлечение и фильтрация процитированных источников │ │
│  └───────────────┬────────────────────────────────────────┘ │
│                  │                                           │
│                  ▼                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  VectorSearch (vector-search.js)                     │  │
│  │  - Загрузка RAG данных (rag_data_compact.json)      │  │
│  │  - Управление Web Worker                             │  │
│  │  - Координация hybrid search                         │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                            │
│                 ▼                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Web Worker (embedding-worker.js)                    │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  HybridSearchEmbedder                           │  │  │
│  │  │  - ONNX Runtime Web (rubert-mini-frida)         │  │  │
│  │  │  - IndexedDB кеширование модели                 │  │  │
│  │  │  - BM25 scoring                                  │  │  │
│  │  │  - Semantic scoring (cosine similarity)         │  │  │
│  │  │  - Hybrid scoring (30% BM25 + 70% Semantic)     │  │  │
│  │  │  - Title chunks filtering (index -2)            │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP POST (search results + query)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          CLOUDFLARE WORKER (cloudflare-worker/worker.js)     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  CORS Handler                                           │ │
│  │  - Проверка origin                                      │ │
│  │  - Разрешенные домены + localhost                      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Rate Limiter (KV Storage)                             │ │
│  │  - 10 запросов на IP за 5 минут                       │ │
│  │  - Скользящее окно                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Routes                                                 │ │
│  │  • /chat - RAG чат (основной endpoint)                │ │
│  │  • /rephrase - Переформулирование запросов            │ │
│  │  • / - Legacy RAG endpoint                             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Query Validator                                        │ │
│  │  - LLM валидация (google/gemma-3-27b-it:free)         │ │
│  │  - Проверка тематики блога                            │ │
│  │  - Поддержка chat history для follow-up вопросов      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  LLM Response Generator                                 │ │
│  │  - OpenRouter API (бесплатные модели)                 │ │
│  │  - Model fallback (перебор при ошибках)               │ │
│  │  - System prompt с инструкциями для RAG               │ │
│  │  - Chat history integration                            │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP POST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    OPENROUTER API                            │
│  - google/gemma-3-27b-it:free                               │
│  - meta-llama/llama-3.3-70b-instruct:free                   │
│  - tngtech/deepseek-r1t-chimera:free                        │
└─────────────────────────────────────────────────────────────┘


СТАТИЧЕСКИЕ ДАННЫЕ:
┌─────────────────────────────────────────────────────────────┐
│  RAG Data (assets/rag/)                                      │
│  - rag_data_compact.json (~15MB)                            │
│    • 1666 chunks (78 posts)                                 │
│    • Embeddings (312 dimensions per chunk)                  │
│    • Metadata (model, dimension, chunk size)                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ONNX Model (HuggingFace CDN)                               │
│  - rubert-mini-frida.onnx (123MB)                           │
│  - Кешируется в IndexedDB после первой загрузки            │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Preparation

### Скрипт: `scripts/prepare_rag_data.py`

**Назначение**: Подготовка данных для RAG-системы из Jekyll постов блога.

### Этапы обработки:

#### 1. Загрузка постов (`load_posts()`)

```python
async def load_posts(self) -> List[Dict]
```

- Сканирует `_posts/*.md`
- Парсит YAML front matter:
  - `title`: заголовок поста
  - `date`: дата публикации
  - `tags`: теги
  - `excerpt`: краткое содержание (важно для summary chunks!)
  - `views`: количество просмотров
- Извлекает URL поста: `https://crazyfrogspb.github.io/YYYY/MM/DD/slug/`
- Читает контент поста (после front matter)

#### 2. Чистка контента (`clean_content()`)

```python
def clean_content(self, content: str) -> str
```

Удаляет Markdown разметку для лучшей обработки:
- Изображения: `![alt](url)` → удаляется
- Ссылки: `[text](url)` → `text`
- Заголовки: `### Header` → `Header`
- Форматирование: `**bold**`, `*italic*` → `bold`, `italic`
- Код блоки: ` ```code``` ` и `` `inline` `` → удаляется/очищается
- Множественные пробелы/переносы → один пробел

**Зачем**: Чистый текст улучшает качество эмбеддингов и BM25 поиска.

#### 3. Создание чанков

**Три типа чанков**:

##### A. Summary chunks (index = -1)

```python
def create_summary_chunk(self, post: Dict) -> Dict
```

- **Источник**: `excerpt` из YAML front matter
- **Когда создается**: Только если `excerpt` существует
- **Зачем**: Summary chunks содержат краткое описание всего поста
- **Пример**:
  ```
  Пост рассказывает о ключевых навыках и знаниях, необходимых сотруднику
  компании Цельс в области машинного обучения и инженерии данных.
  ```

##### B. Content chunks (index = 0, 1, 2, ...)

```python
def create_chunks(self, post: Dict) -> List[Dict]
```

- **Размер**: 512 символов
- **Перекрытие**: 50 символов (chunk overlap)
- **Разрыв**: По пробелам (не режет слова)
- **Зачем**: Разбиение длинных постов на фрагменты для более точного поиска

**Параметры чанкинга**:
```python
self.chunk_size = 512  # символов
self.chunk_overlap = 50  # символов перекрытия
```

**Почему overlap**: Контекст не теряется на границах чанков.

##### C. Title chunks (index = -2) - УДАЛЕНЫ

```python
def create_title_chunk(self, post: Dict) -> Dict
```

- **Источник**: `title` поста
- **Статус**: Удалены из генерации (строки 273-275 закомментированы)
- **Причина удаления**: Не содержат полезной информации, только дублируют заголовок
- **Фильтрация**: Также фильтруются в `embedding-worker.js:678` на случай старых данных

#### 4. Генерация эмбеддингов (`generate_embeddings()`)

**Модель**: `sergeyzh/rubert-mini-frida`
- **Размерность**: 312 dimensions
- **Библиотека**: sentence-transformers (локально)

**Почему rubert-mini-frida**:
- Оптимизирована для русского языка
- Компактная (123MB ONNX)
- Хорошая балансировка качества/размера

**Префиксы для эмбеддингов** (`create_text_with_prefix()`):

```python
def create_text_with_prefix(self, chunk: Dict) -> str:
    if chunk_type == "content":
        return f"search_document: {title}. {content}"
    elif chunk_type == "summary":
        return f"search_document: Краткое содержание: {title}. {content}"
    elif chunk_type == "title":
        return f"search_document: Заголовок статьи: {content}"
```

**Зачем префиксы**: Модель rubert-mini-frida обучена с инструкциями (`search_document:`, `search_query:`), что улучшает качество поиска.

**Батчинг**: 100 чанков за раз для эффективности.

#### 5. Сохранение данных (`save_rag_data()`)

**Два файла**:

1. **`rag_data.json`** (с отступами):
   ```json
   {
     "chunks": [...],
     "embeddings": [[...], [...], ...],
     "metadata": {
       "total_chunks": 1666,
       "chunk_size": 512,
       "chunk_overlap": 50,
       "embedding_model": "sergeyzh/rubert-mini-frida",
       "generation_method": "local",
       "embedding_dimension": 312
     }
   }
   ```

2. **`rag_data_compact.json`** (минифицированный, для браузера):
   - Без пробелов/отступов
   - ~15MB
   - Загружается в `VectorSearch`

**Структура chunk**:
```json
{
  "id": "2023-02-10-что-надо-знать-сотруднику-цельса_chunk_-1",
  "post_id": "2023-02-10-что-надо-знать-сотруднику-цельса",
  "post_title": "Что надо знать сотруднику Цельса?",
  "post_url": "https://crazyfrogspb.github.io/2023/02/10/...",
  "chunk_index": -1,
  "content": "Пост рассказывает о ключевых навыках...",
  "type": "summary"
}
```

---

## ML компоненты

### Web Worker: `assets/js/embedding-worker.js`

**Зачем Web Worker**:
- Тяжелые вычисления (ONNX inference) не блокируют UI
- Параллельная работа с основным потоком
- Лучший UX (чат остается отзывчивым)

### Класс: `HybridSearchEmbedder`

#### Инициализация

**Два режима работы**:

##### Что такое ONNX Runtime Web?

**ONNX (Open Neural Network Exchange)** - это открытый формат для представления моделей машинного обучения. Любую модель (PyTorch, TensorFlow, scikit-learn) можно конвертировать в ONNX формат.

**ONNX Runtime Web** (пакет `onnxruntime-web`) - это современная JavaScript библиотека от Microsoft для запуска ONNX моделей в браузере. Заменила устаревший пакет `onnxjs`.

**Ключевые возможности**:
- **В браузере**: Работает прямо на клиенте без сервера
- **На Node.js**: Можно использовать на backend
- **Cross-platform**: Автоматически выбирает оптимальный backend (WebAssembly, WebGL, WebGPU)

**Как это работает**:
```javascript
// 1. Загружаем ONNX модель (файл .onnx)
const modelData = await fetch('model.onnx').then(r => r.arrayBuffer());

// 2. Создаем inference session
const session = await ort.InferenceSession.create(modelData);

// 3. Подготавливаем входные данные (тензоры)
const inputTensor = new ort.Tensor('int64', [1, 2, 3], [1, 3]);

// 4. Запускаем модель
const results = await session.run({ 'input_ids': inputTensor });

// 5. Получаем результат
const output = results.last_hidden_state.data;
```

**Используемая версия**: `onnxruntime-web@1.16.3` (CDN: jsdelivr)

**Преимущества ONNX Runtime Web**:
- Не нужен Python или серверный ML backend
- Модель запускается локально (приватность данных)
- Кросс-платформенность (работает везде где есть JavaScript)
- Оптимизированный inference (WebAssembly + SIMD)
- Активная поддержка от Microsoft

**Недостатки**:
- Медленнее GPU на сервере (но для inference в браузере это норма)
- Большой размер моделей (нужно скачивать на клиент)
- Ограничения браузера (память, производительность)

**Альтернативы**:
- **Transformers.js**: Более высокоуровневая библиотека от HuggingFace
- **TensorFlow.js**: TensorFlow модели в браузере
- **MediaPipe**: Google решение для CV/NLP в браузере

**Важно**: В 2020 году Microsoft [мигрировала](https://github.com/microsoft/onnxjs/blob/master/docs/migration-to-ort-web.md) пакет `onnxjs` → `onnxruntime-web`. Старый пакет deprecated.

---

**Инициализация с ONNX Runtime Web**:

```javascript
async initializeONNX(corpusData)
```

**Этапы**:
- Загружает config: `/assets/onnx/config.json`
- Загружает tokenizer: `https://huggingface.co/sergeyzh/rubert-mini-frida/resolve/main/tokenizer.json`
- Загружает ONNX модель: `https://huggingface.co/crazyfrogspb/rubert-mini-frida-onnx/resolve/main/model.onnx`
- Создает inference session: `ort.InferenceSession.create(modelData)`

**Почему ONNX Runtime Web**:
- Легче (меньше зависимостей, ~1MB vs ~10MB Transformers.js)
- Быстрее (оптимизированный runtime, нативный WebAssembly)
- Лучший контроль (ручная токенизация, можем точно настроить)
- Меньший bundle size (важно для веб-приложения)
- Официальная поддержка от Microsoft

#### IndexedDB кеширование

##### Что такое IndexedDB?

**IndexedDB** - это встроенная NoSQL база данных в браузере для хранения больших объемов структурированных данных.

**Основные концепции**:

```javascript
// 1. База данных (Database) - контейнер для хранилищ
const dbName = 'my-app-db';

// 2. Object Store - как таблица в SQL (хранит объекты)
const storeName = 'users';

// 3. Индексы - для быстрого поиска
const index = objectStore.createIndex('email', 'email', { unique: true });

// 4. Транзакции - атомарные операции
const transaction = db.transaction(['users'], 'readwrite');
```

**Пример использования**:

```javascript
// Открываем/создаем БД
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('my-app-db', 1);

        // Создание структуры (при первом открытии)
        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            db.createObjectStore('files');
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Сохранение данных
async function saveFile(name, data) {
    const db = await openDB();
    const tx = db.transaction(['files'], 'readwrite');
    const store = tx.objectStore('files');
    await store.put(data, name);
}

// Чтение данных
async function getFile(name) {
    const db = await openDB();
    const tx = db.transaction(['files'], 'readonly');
    const store = tx.objectStore('files');
    return await store.get(name);
}
```

**Отличия от других хранилищ**:

| Технология | Размер | Тип данных | Асинхронность |
|------------|--------|------------|---------------|
| **LocalStorage** | ~5-10MB | Только строки | Синхронный |
| **SessionStorage** | ~5-10MB | Только строки | Синхронный |
| **IndexedDB** | ~50MB-∞ | Любые объекты, Blob, ArrayBuffer | Асинхронный |
| **Cache API** | ~50MB-∞ | Response объекты | Асинхронный |

**Преимущества IndexedDB**:
- **Большой размер**: Гигабайты данных (с разрешением пользователя)
- **Любые типы**: Объекты, массивы, ArrayBuffer, Blob
- **Производительность**: Индексы для быстрого поиска
- **Транзакции**: ACID гарантии
- **Асинхронность**: Не блокирует UI

**Недостатки**:
- Сложный API (callback-based, нужны обертки)
- Не синхронизируется между вкладками автоматически
- Может быть очищен браузером при нехватке места

**Альтернативы**:
- **Cache API**: Для кеширования HTTP ответов
- **FileSystem API**: Для работы с файловой системой
- **Web SQL** (deprecated): SQL база в браузере

**Почему IndexedDB для ONNX модели**:
- Размер 123MB (LocalStorage не подходит, лимит ~5MB)
- ArrayBuffer хранится нативно (не нужна сериализация)
- Персистентность (сохраняется между сессиями)
- Версионирование (можем инвалидировать кеш при обновлении)

---

**Проблема**: 123MB модель загружается каждый раз.

**Решение**: IndexedDB кеш с версионированием.

```javascript
const MODEL_CACHE_DB = 'onnx-model-cache';
const MODEL_CACHE_STORE = 'models';
const MODEL_VERSION = 'v1';
```

**Workflow**:

1. **Первая загрузка**:
   ```javascript
   // Проверяем кеш
   let modelData = await getModelFromCache(modelUrl);

   if (!modelData) {
       // Скачиваем с HuggingFace
       const response = await fetch(this.modelUrl);
       modelData = await response.arrayBuffer();

       // Сохраняем в IndexedDB
       await saveModelToCache(this.modelUrl, modelData);
   }
   ```

2. **Последующие загрузки**:
   - Модель мгновенно загружается из IndexedDB
   - Нет сетевого запроса
   - Экономия времени и трафика

**Инвалидация кеша**: Увеличиваем `MODEL_VERSION` при обновлении модели.

#### Токенизация

**Используемый метод**: `tokenizeWithHF(text)`

**Этапы**:

1. **Нормализация**:
   ```javascript
   const normalizedText = text.toLowerCase().trim();
   ```

2. **Pre-tokenization** (разбиение на слова):
   ```javascript
   const words = normalizedText.split(/\s+/);
   ```

3. **WordPiece токенизация** (`wordPieceTokenizeHF()`):
   - Использует vocab из `tokenizer.json`
   - Разбивает слова на подслова (subwords)
   - Добавляет префикс `##` для подслов
   - Пример: `"машинного"` → `["машин", "##ного"]`

4. **Добавление специальных токенов**:
   ```javascript
   const tokens = [clsId];  // [CLS]
   // ... wordpiece tokens ...
   tokens.push(sepId);      // [SEP]
   ```

5. **Truncation**:
   ```javascript
   if (tokens.length > 512) {
       tokens.length = 511;
       tokens.push(sepId);
   }
   ```

**Почему WordPiece**:
- Обрабатывает OOV (out-of-vocabulary) слова
- Лучше для русского языка (словоформы)
- Совместимость с BERT-подобными моделями

#### Генерация эмбеддингов

**Метод**: `encodeWithONNX(text)`

```javascript
async encodeWithONNX(text) {
    // 1. Токенизация
    const tokens = this.tokenizeWithHF(text);

    // 2. Конвертация в BigInt64Array (ONNX requirement)
    const tokensInt64 = new BigInt64Array(tokens.map(t => BigInt(t)));
    const maskInt64 = new BigInt64Array(tokens.map(() => 1n));

    // 3. Создание тензоров
    const inputIds = new ort.Tensor('int64', tokensInt64, [1, tokens.length]);
    const attentionMask = new ort.Tensor('int64', maskInt64, [1, tokens.length]);

    // 4. Inference
    const results = await this.session.run({
        'input_ids': inputIds,
        'attention_mask': attentionMask
    });

    // 5. Mean pooling
    const lastHiddenState = results.last_hidden_state;
    const embedding = this.meanPooling(lastHiddenState.data, tokens.length);

    // 6. L2 нормализация
    const norm = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    return embedding.map(val => val / norm);
}
```

**Mean pooling** (`meanPooling()`):
```javascript
meanPooling(hiddenStates, seqLength) {
    const embedding = new Array(312).fill(0);

    // Усредняем по всем токенам
    for (let i = 0; i < seqLength; i++) {
        for (let j = 0; j < 312; j++) {
            embedding[j] += hiddenStates[i * 312 + j];
        }
    }

    return embedding.map(val => val / seqLength);
}
```

**Зачем mean pooling**:
- Преобразует последовательность токенов (512 векторов) в один вектор (312 чисел)
- Сохраняет семантику всего текста

**Префикс для запросов**:
```javascript
const searchText = `search_query: ${text}`;
```

**Зачем**: Асимметричный поиск (документы имеют `search_document:`, запросы - `search_query:`).

#### BM25 (Keyword Search)

**Инициализация**: `initializeBM25(corpusData)`

```javascript
initializeBM25(corpusData) {
    // Токенизируем все документы
    this.corpus = corpusData.map(doc => this.simpleTokenize(doc.content));

    // Считаем document frequency для каждого термина
    this.corpus.forEach(doc => {
        const uniqueTerms = new Set(doc);
        uniqueTerms.forEach(term => {
            this.docFreq.set(term, (this.docFreq.get(term) || 0) + 1);
        });
    });

    // Средняя длина документа
    this.avgDocLength = totalLength / totalDocs;
}
```

**Simple Tokenization** (для BM25):
```javascript
simpleTokenize(text) {
    return text
        .toLowerCase()
        .replace(/[^\w\sа-яё]/gi, ' ')  // Только буквы/цифры
        .split(/\s+/)
        .filter(word => word.length > 2);  // Минимум 3 символа
}
```

**Почему простая токенизация**:
- BM25 работает с словами, не с subwords
- Быстрее чем WordPiece
- Достаточно для keyword matching

**BM25 Scoring** (`calculateBM25()`):

```javascript
calculateBM25(queryTerms, docIndex) {
    const doc = this.corpus[docIndex];
    let score = 0;

    for (const term of queryTerms) {
        // Term frequency в документе
        const tf = doc.filter(t => t === term).length;

        // Document frequency термина
        const df = this.docFreq.get(term) || 0;

        if (df > 0) {
            // IDF
            const idf = Math.log((N - df + 0.5) / (df + 0.5));

            // TF component
            const tfComponent = (tf * (k1 + 1)) /
                (tf + k1 * (1 - b + b * (docLength / avgDocLength)));

            score += idf * tfComponent;
        }
    }

    return score;
}
```

**Параметры**:
- `k1 = 1.2`: Насыщение term frequency
- `b = 0.75`: Влияние длины документа

**Формула BM25**:
```
score = Σ IDF(term) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl/avgdl))
```

Где:
- `IDF` = Inverse Document Frequency
- `tf` = term frequency в документе
- `dl` = длина документа
- `avgdl` = средняя длина документа

#### Hybrid Search

**Метод**: `hybridSearch(query, documents, topK)`

**Workflow**:

1. **Генерация query embedding**:
   ```javascript
   const queryEmbedding = await this.encode(query);
   ```

2. **Токенизация для BM25**:
   ```javascript
   const queryTerms = this.simpleTokenize(query);
   ```

3. **Scoring всех документов**:
   ```javascript
   const scores = documents.map((doc, index) => {
       const bm25Score = this.calculateBM25(queryTerms, index);
       const semanticScore = this.cosineSimilarity(queryEmbedding, doc.embedding);

       return { index, bm25Score, semanticScore, document: doc };
   });
   ```

4. **Min-Max нормализация**:
   ```javascript
   const bm25Norm = (bm25Score - minBM25) / (maxBM25 - minBM25);
   const semanticNorm = (semanticScore - minSemantic) / (maxSemantic - minSemantic);
   ```

   **Зачем**: BM25 и semantic scores имеют разные диапазоны. Нормализация к [0, 1] для честного комбинирования.

5. **Hybrid scoring**:
   ```javascript
   const hybridScore = 0.3 * bm25Norm + 0.7 * semanticNorm;
   ```

   **Веса**:
   - **30% BM25**: Keyword matching (точные совпадения слов)
   - **70% Semantic**: Семантическое сходство (смысл)

   **Почему такие веса**:
   - Semantic важнее для понимания смысла
   - BM25 помогает при точных терминах (названия, аббревиатуры)
   - Соотношение подобрано эмпирически

6. **Сортировка и фильтрация**:
   ```javascript
   const sortedScores = normalizedScores.sort((a, b) => b.score - a.score);

   // Фильтруем title chunks
   const filtered = sortedScores.filter(s => s.document.chunk_index !== -2);

   return filtered.slice(0, topK);
   ```

**Зачем фильтровать title chunks**:
- Title chunks содержат только заголовок поста
- Не дают контекста для ответа LLM
- Засоряют результаты поиска

#### Cosine Similarity

```javascript
cosineSimilarity(vec1, vec2) {
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;

    for (let i = 0; i < vec1.length; i++) {
        dotProduct += vec1[i] * vec2[i];
        norm1 += vec1[i] * vec1[i];
        norm2 += vec2[i] * vec2[i];
    }

    return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
}
```

**Диапазон**: [-1, 1]
- `1`: Идентичные векторы
- `0`: Ортогональные (нет сходства)
- `-1`: Противоположные

---

## Frontend компоненты

### VectorSearch: `assets/js/vector-search.js`

**Роль**: Координатор между UI и Web Worker.

#### Основные методы:

##### 1. `loadData()` - Загрузка RAG данных

```javascript
async loadData() {
    const response = await fetch('/assets/rag/rag_data_compact.json');
    const data = await response.json();

    this.chunks = data.chunks;           // 1666 chunks
    this.embeddings = data.embeddings;   // 1666 x 312 embeddings
    this.metadata = data.metadata;

    this.isLoaded = true;
}
```

**Размер**: ~15MB (минифицированный JSON)

##### 2. `initializeWorker()` - Инициализация Web Worker

```javascript
async initializeWorker() {
    this.worker = new Worker('/assets/js/embedding-worker.js');

    // Подготавливаем корпус для BM25
    const corpusData = this.chunks.map(chunk => ({
        content: chunk.content,
        type: chunk.type
    }));

    // Инициализируем worker
    await this.sendWorkerMessage('initialize', { corpusData });
}
```

**Timeout**:
- `initialize`: 120 секунд (загрузка ONNX модели)
- Остальные: 30 секунд

##### 3. `search()` - Hybrid search

```javascript
async search(query, options = {}) {
    const { limit = 5, threshold = 0.1 } = options;

    // Подготавливаем документы с эмбеддингами
    const documents = this.chunks.map((chunk, index) => ({
        ...chunk,
        embedding: this.embeddings[index],
        index
    }));

    // Выполняем hybrid search через worker
    const response = await this.sendWorkerMessage('hybrid_search', {
        query,
        documents,
        topK: limit * 2  // Берем больше для фильтрации
    });

    // Фильтруем по threshold
    const results = response.results
        .filter(result => result.score >= threshold)
        .slice(0, limit);

    return {
        chunks: results.map(result => ({
            ...result.document,
            score: result.score,
            bm25Score: result.bm25Score,
            semanticScore: result.semanticScore
        })),
        debug: { /* ... */ }
    };
}
```

**Параметры**:
- `limit`: Сколько чанков вернуть (по умолчанию 5, сейчас 7)
- `threshold`: Минимальный score (0.1)
- `topK: limit * 2`: Берем в 2 раза больше для запаса после фильтрации

### RAGChat: `rag-chat.html`

**Роль**: UI контроллер чата, управление историей, координация с backend.

#### Основные компоненты:

##### 1. Chat History

```javascript
constructor() {
    this.chatHistory = [];
    this.maxHistoryLength = 6;  // Последние 3 пары Q&A
}
```

**Зачем**:
- Контекст для follow-up вопросов
- LLM видит предыдущие Q&A
- Query rephrasing использует историю

**Управление**:

```javascript
// Добавление в историю
this.chatHistory.push(
    { role: 'user', content: message },
    { role: 'assistant', content: response.answer }
);

// Ограничение длины (FIFO)
if (this.chatHistory.length > this.maxHistoryLength) {
    this.chatHistory = this.chatHistory.slice(-this.maxHistoryLength);
}
```

**Почему 6 сообщений**:
- Баланс между контекстом и размером payload
- 3 Q&A пары достаточно для диалога
- Не перегружаем LLM контекстом

##### 2. Query Rephrasing

```javascript
async rephraseQuery(query, chatHistory) {
    if (chatHistory.length === 0) {
        return query;  // Нет истории - возвращаем как есть
    }

    const response = await fetch(
        this.cloudflareWorkerUrl.replace('/chat', '/rephrase'),
        {
            method: 'POST',
            body: JSON.stringify({ query, history: chatHistory })
        }
    );

    const data = await response.json();
    return data.rephrased_query || query;
}
```

**Зачем Query Rephrasing**:

**Проблема**: Follow-up вопросы зависят от контекста.

Примеры:
- User: "Расскажи про компанию Цельс"
- Assistant: "Цельс - компания в области медицинского AI..."
- User: "что это за компания?" ← Нет упоминания "Цельс"!

**Решение**: LLM переформулирует в standalone вопрос.

```
"что это за компания?"
    ↓ query rephrasing
"Что за компания Цельс?"
```

**Workflow**:

1. **Поиск**: Используется **переформулированный** запрос
   - Векторный поиск находит релевантные чанки про Цельс

2. **LLM**: Получает **оригинальный** запрос + историю
   - LLM видит контекст диалога
   - Отвечает естественно на "что это за компания?"

**Почему важно**:
- Поиск без контекста не найдет релевантные документы
- LLM должен видеть оригинальный вопрос для естественного ответа

##### 3. Send Message Flow

```javascript
async sendMessage() {
    const message = this.messageInput.value.trim();

    // 1. Добавляем в UI
    this.addMessage(message, 'user');
    this.showTyping();
    this.disableInput();

    try {
        // 2. Query rephrasing (если есть история)
        let searchQuery = message;
        if (this.chatHistory.length > 0) {
            searchQuery = await this.rephraseQuery(message, this.chatHistory);
            console.log('🔄 Переформулированный запрос:', searchQuery);
        }

        // 3. Hybrid search (переформулированный запрос)
        const searchResults = await this.vectorSearch.search(searchQuery, {
            limit: 7,
            threshold: 0.1
        });

        // 4. LLM генерация (оригинальный запрос + история)
        const response = await this.generateLLMResponse(
            message,              // Оригинальный запрос
            searchResults.chunks,
            this.chatHistory      // История
        );

        // 5. Извлекаем процитированные источники
        const citedNumbers = this.extractCitedSources(response.answer);

        // 6. Фильтруем sources
        const citedSources = citedNumbers
            .map(num => searchResults.chunks[num - 1])
            .filter(chunk => chunk !== undefined);

        // 7. Добавляем ответ с источниками
        this.addMessage(response.answer, 'assistant', citedSources);

        // 8. Обновляем историю
        this.chatHistory.push(
            { role: 'user', content: message },
            { role: 'assistant', content: response.answer }
        );

        if (this.chatHistory.length > this.maxHistoryLength) {
            this.chatHistory = this.chatHistory.slice(-this.maxHistoryLength);
        }

    } catch (error) {
        const errorMessage = error.message || 'Ошибка при обработке запроса';
        this.addMessage(errorMessage, 'assistant');
    } finally {
        this.hideTyping();
        this.enableInput();
    }
}
```

##### 4. Cited Sources Extraction

**Проблема**: Показываем все 7 найденных sources, даже если LLM использовал только 2.

**Решение**: Извлекаем номера из ответа LLM.

```javascript
extractCitedSources(text) {
    const citedNumbers = new Set();

    // Ищем паттерны [1], [2, 3], [1, 5, 7]
    const regex = /\[([\d,\s]+)\]/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
        const numbers = match[1];

        // Проверяем что это список чисел
        if (/^[\d,\s]+$/.test(numbers)) {
            const nums = numbers.split(',')
                .map(n => parseInt(n.trim()))
                .filter(n => !isNaN(n));
            nums.forEach(num => citedNumbers.add(num));
        }
    }

    return Array.from(citedNumbers).sort((a, b) => a - b);
}
```

**Примеры**:
- `"В Цельсе работают [1, 3] над медицинским AI"` → `[1, 3]`
- `"Компания Цельс [5] занимается..."` → `[5]`

**Фильтрация sources**:
```javascript
const citedSources = citedNumbers
    .map(num => searchResults.chunks[num - 1])  // num с 1, индексы с 0
    .filter(chunk => chunk !== undefined);
```

**Результат**: Показываем только источники, которые LLM реально использовал.

##### 5. Markdown to HTML

```javascript
markdownToHtml(markdown) {
    let html = markdown;

    // 1. Экранируем HTML теги
    html = html.replace(/</g, '&lt;').replace(/>/g, '&gt;');

    // 2. Markdown ссылки [text](url) → <a>
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank">$1</a>');

    // 3. Ссылки на источники [1, 5] → <a href="#source-N">
    html = html.replace(/\[([\d,\s]+)\]/g, (match, numbers) => {
        if (/^[\d,\s]+$/.test(numbers)) {
            const nums = numbers.split(',').map(n => n.trim());
            const links = nums.map(num =>
                `<a href="#source-${num}">${num}</a>`
            );
            return '[' + links.join(', ') + ']';
        }
        return match;
    });

    // 4. Форматирование **bold**, *italic*
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 5. Переносы строк
    html = html.replace(/\n/g, '<br>');

    return html;
}
```

**Особенности**:
- Якорные ссылки на источники (`#source-N`)
- Автоматическая прокрутка к источнику при клике
- Подсветка источника (`:target` CSS)

---

## Backend компоненты

### Cloudflare Worker: `cloudflare-worker/worker.js`

**Зачем Cloudflare Worker**:
- **Скрыть API ключ**: OpenRouter API key не виден клиенту
- **Rate limiting**: Защита от злоупотребления
- **CORS**: Безопасный доступ только с разрешенных доменов
- **Validation**: LLM проверяет соответствие тематике
- **Model fallback**: Автоматический переход на другую модель при ошибках
- **Serverless**: Масштабируется автоматически, платим только за использование

#### Конфигурация

```javascript
const CONFIG = {
    // Разрешенные домены
    ALLOWED_ORIGINS: [
        'https://crazyfrogspb.github.io',
        'http://localhost:4000',
        'http://127.0.0.1:4000',
        'http://localhost:4002',
        'http://127.0.0.1:4002'
    ],

    // Rate limiting
    RATE_LIMIT: {
        MAX_REQUESTS: 10,      // 10 запросов
        WINDOW_MINUTES: 5      // За 5 минут
    },

    // OpenRouter API
    OPENROUTER_BASE_URL: 'https://openrouter.ai/api/v1',

    // Модели (бесплатные)
    DEFAULT_MODEL: 'google/gemma-3-27b-it:free',
    FREE_MODELS: [
        'google/gemma-3-27b-it:free',
        'meta-llama/llama-3.3-70b-instruct:free',
        'tngtech/deepseek-r1t-chimera:free'
    ],

    VALIDATION_MODEL: 'google/gemma-3-27b-it:free',
    MAX_CONTEXT_LENGTH: 8000
};
```

**Почему только бесплатные модели**:
- Блог некоммерческий
- OpenRouter предоставляет free tier
- Достаточно для RAG задач

#### Роутинг

```javascript
if (url.pathname === '/chat') {
    // RAG чат (основной endpoint)
    return await handleRAGChatRequest(request);
} else if (url.pathname === '/rephrase') {
    // Переформулирование запросов
    return await handleRephraseRequest(request);
} else {
    // Legacy RAG endpoint
    return await handleRAGRequest(request);
}
```

**3 endpoint'а**:
1. `/chat` - Основной RAG чат с историей
2. `/rephrase` - Query rephrasing
3. `/` - Старый API (обратная совместимость)

#### CORS Handler

```javascript
function handleCORS(request) {
    const origin = request.headers.get('Origin');

    const isLocalhost = origin && (
        origin.includes('localhost') ||
        origin.includes('127.0.0.1')
    );

    const isAllowed = !origin ||
        CONFIG.ALLOWED_ORIGINS.includes(origin) ||
        isLocalhost;

    // Preflight (OPTIONS)
    if (request.method === 'OPTIONS') {
        if (isAllowed) {
            return new Response(null, {
                status: 200,
                headers: {
                    'Access-Control-Allow-Origin': origin || '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Max-Age': '86400'
                }
            });
        }
        return new Response('CORS not allowed', { status: 403 });
    }

    // Проверка origin
    if (origin && !isAllowed) {
        return new Response('CORS not allowed', { status: 403 });
    }

    return null;  // OK
}
```

**Зачем CORS**:
- Только разрешенные сайты могут вызывать API
- Защита от злоупотребления
- Localhost разрешен для разработки

#### Rate Limiting

**Хранилище**: Cloudflare KV (Key-Value)

```javascript
async function checkRateLimit(request) {
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const key = `rate_limit:${clientIP}`;

    const current = await RATE_LIMIT_KV.get(key);
    const now = Date.now();
    const windowMs = 5 * 60 * 1000;  // 5 минут

    if (current) {
        const data = JSON.parse(current);

        // Окно еще активно
        if (now - data.timestamp < windowMs) {
            if (data.count >= 10) {
                return new Response(JSON.stringify({
                    error: 'Rate limit exceeded',
                    message: 'Превышен лимит запросов. Попробуйте через 5 минут.',
                    retryAfter: Math.ceil((data.timestamp + windowMs - now) / 1000)
                }), { status: 429 });
            }

            // Увеличиваем счетчик
            data.count++;
            await RATE_LIMIT_KV.put(key, JSON.stringify(data), {
                expirationTtl: Math.ceil(windowMs / 1000)
            });
        } else {
            // Новое окно
            await RATE_LIMIT_KV.put(key, JSON.stringify({
                count: 1,
                timestamp: now
            }), { expirationTtl: Math.ceil(windowMs / 1000) });
        }
    } else {
        // Первый запрос
        await RATE_LIMIT_KV.put(key, JSON.stringify({
            count: 1,
            timestamp: now
        }), { expirationTtl: Math.ceil(windowMs / 1000) });
    }

    return null;  // OK
}
```

**Принцип**: Sliding window
- Ключ: IP адрес пользователя
- Счетчик: количество запросов
- Окно: 5 минут
- Лимит: 10 запросов

**Зачем**: Защита от:
- DoS атак
- Злоупотребления API
- Превышения лимитов OpenRouter

#### Query Validation

**Endpoint**: `/rephrase` и `/chat`

```javascript
async function validateQuery(query, history = []) {
    // Формируем контекст
    let userContent = `Запрос пользователя: "${query}"`;

    if (history.length > 0) {
        const historyText = history.map(msg =>
            `${msg.role === 'user' ? 'Пользователь' : 'Ассистент'}: ${msg.content}`
        ).join('\n');

        userContent = `История диалога:\n${historyText}\n\n` +
                     `Текущий запрос: "${query}"\n\n` +
                     `Оцени ТЕКУЩИЙ запрос в контексте диалога.`;
    }

    // Запрос к LLM
    const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: 'google/gemma-3-27b-it:free',
            messages: [
                { role: 'system', content: VALIDATION_PROMPT },
                { role: 'user', content: userContent }
            ],
            max_tokens: 10,
            temperature: 0.1
        })
    });

    const result = await response.json();
    const answer = result.choices[0].message.content.trim().toLowerCase();

    return answer.includes('да') || answer.includes('yes');
}
```

**Validation Prompt**:

```
Ты модератор чата для блога "Варим ML" - телеграм-канала о машинном обучении,
data science, MLOps и карьере в IT.

Определи, подходит ли запрос пользователя для этого чата.

Запрос ПОДХОДИТ, если он:
1. Касается машинного обучения, ИИ, data science, MLOps
2. Связан с карьерой в IT, разработкой, наймом, менеджментом
3. Просит найти или объяснить что-то из постов канала
4. Задает вопросы по темам, которые могут освещаться в ML-блоге
5. Уточняет какую-то информацию об авторе канала

Запрос НЕ ПОДХОДИТ, если он:
1. Касается политики, религии, любых чувствительных тем
2. Просит создать или найти контент, не связанный с ML/IT
3. Содержит оскорбления или неуместный контент
4. Не касается канала - например, пользователь просит написать код
5. Касается медицинских советов, юридических консультаций и т.п.

Отвечай только "ДА" или "НЕТ".
```

**Зачем валидация**:
- Фильтр нерелевантных запросов
- Экономия API квоты OpenRouter
- Улучшение UX (сразу говорим что не по теме)

**Почему история в validation**:

**Проблема**: "что это за компания?" - контекст-зависимый вопрос.

Без истории:
```
Запрос: "что это за компания?"
Валидация: НЕТ (нет упоминания ML/IT)
```

С историей:
```
История:
  User: "Расскажи про Цельс"
  Assistant: "Цельс - компания в области медицинского AI..."

Текущий запрос: "что это за компания?"
Валидация: ДА (уточнение про компанию из ML области)
```

#### Query Rephrasing Handler

**Endpoint**: `POST /rephrase`

```javascript
async function handleRephraseRequest(request) {
    const { query, history = [] } = await request.json();

    // Нет истории - возвращаем как есть
    if (history.length === 0) {
        return Response(JSON.stringify({ rephrased_query: query }));
    }

    // Формируем промпт
    const historyText = history.map(msg =>
        `${msg.role === 'user' ? 'Пользователь' : 'Ассистент'}: ${msg.content}`
    ).join('\n');

    const rephrasePrompt = `
Ты помощник для переформулирования вопросов.

История диалога:
${historyText}

Текущий вопрос пользователя: "${query}"

Переформулируй текущий вопрос в самостоятельный (standalone) вопрос,
который можно понять БЕЗ контекста истории.
Замени все местоимения и неявные ссылки на конкретные объекты из истории.

Примеры:
- "что это за компания?" → "Что за компания Цельс?"
- "расскажи подробнее" → "Расскажи подробнее про [конкретная тема]"
- "а какие еще?" → "[Конкретизированный вопрос]"

Отвечай ТОЛЬКО переформулированным вопросом, без пояснений.
`;

    // Запрос к LLM
    const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
        method: 'POST',
        body: JSON.stringify({
            model: CONFIG.DEFAULT_MODEL,
            messages: [{ role: 'user', content: rephrasePrompt }],
            max_tokens: 200,
            temperature: 0.3
        })
    });

    const result = await response.json();
    const rephrasedQuery = result.choices?.[0]?.message?.content?.trim() || query;

    return Response(JSON.stringify({
        rephrased_query: rephrasedQuery,
        original_query: query
    }));
}
```

**Почему отдельный endpoint**:
- Frontend может использовать для поиска
- Backend использует для validation
- Переиспользуемая логика

#### RAG Chat Handler

**Endpoint**: `POST /chat`

**Input**:
```json
{
  "query": "что это за компания?",
  "context": "[1] Цельс...\n[2] ML инженер...",
  "history": [
    { "role": "user", "content": "Расскажи про Цельс" },
    { "role": "assistant", "content": "Цельс - компания..." }
  ],
  "model": "google/gemma-3-27b-it:free"
}
```

**Workflow**:

1. **Валидация входных данных**:
   ```javascript
   if (!query || typeof query !== 'string') {
       return error('Invalid input');
   }
   if (!context || typeof context !== 'string') {
       return error('Invalid input');
   }
   if (!FREE_MODELS.includes(model)) {
       return error('Invalid model');
   }
   ```

2. **Query validation с историей**:
   ```javascript
   const isValidQuery = await validateQuery(query, history);
   if (!isValidQuery) {
       return new Response(JSON.stringify({
           error: 'Invalid query',
           message: 'Ваш запрос не соответствует тематике блога "Варим ML"'
       }), { status: 400 });
   }
   ```

3. **Обрезка контекста**:
   ```javascript
   let finalContext = context;
   if (context.length > 8000) {
       finalContext = context.substring(0, 8000) + '...';
   }
   ```

4. **System Prompt**:
   ```javascript
   const systemPrompt = `
Ты ассистент блога "Варим ML" - телеграм-канала о машинном обучении,
data science и карьере в IT.

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста из постов блога
2. Если в контексте нет информации для ответа, честно скажи об этом
3. Всегда указывай источники - номера постов [1], [2] и т.д.
4. Отвечай на русском языке, дружелюбно и профессионально
5. Если вопрос не по теме блога, вежливо перенаправь к релевантным темам

КОНТЕКСТ ИЗ ПОСТОВ БЛОГА:
${finalContext}

Отвечай на вопрос пользователя, основываясь только на этом контексте.
`;
   ```

5. **Формирование messages с историей**:
   ```javascript
   const messages = [
       { role: 'system', content: systemPrompt },
       ...history,  // История чата
       { role: 'user', content: query }  // Текущий запрос
   ];
   ```

6. **Model fallback (перебор моделей)**:
   ```javascript
   const modelsToTry = [model, ...FREE_MODELS.filter(m => m !== model)];

   for (const tryModel of modelsToTry) {
       try {
           const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
               method: 'POST',
               body: JSON.stringify({
                   model: tryModel,
                   messages: messages,
                   max_tokens: 1000,
                   temperature: 0.7,
                   top_p: 0.9
               })
           });

           if (response.ok) {
               const result = await response.json();
               answer = result.choices?.[0]?.message?.content?.trim();
               if (answer) break;
           }
       } catch (error) {
           console.log(`❌ Модель ${tryModel} не работает`);
       }
   }
   ```

   **Зачем fallback**: OpenRouter иногда блокирует модели в определенных регионах. Автоматически пробуем другие.

7. **Response**:
   ```javascript
   return new Response(JSON.stringify({
       answer: answer,
       model: usedModel,
       context_length: finalContext.length,
       query: query
   }), {
       status: 200,
       headers: {
           'Content-Type': 'application/json',
           'Access-Control-Allow-Origin': request.headers.get('Origin')
       }
   });
   ```

**Output**:
```json
{
  "answer": "Цельс - компания в области медицинского компьютерного зрения [1, 3]...",
  "model": "google/gemma-3-27b-it:free",
  "context_length": 2456,
  "query": "что это за компания?"
}
```

---

## Оптимизации и особенности

### 1. IndexedDB Model Caching

**Проблема**: ONNX модель 123MB загружается каждый раз при открытии страницы.

**Решение**:
- Первый визит: Скачиваем модель с HuggingFace, сохраняем в IndexedDB
- Последующие визиты: Мгновенная загрузка из IndexedDB

**Экономия**:
- **Времени**: ~30-60 секунд → <1 секунда
- **Трафика**: 123MB → 0MB (после первой загрузки)

**Версионирование**: `MODEL_VERSION = 'v1'` - увеличиваем при обновлении модели.

### 2. Query Rephrasing

**Проблема**: Follow-up вопросы не находят релевантные документы.

**Примеры проблем**:
- "что это за компания?" - нет упоминания названия
- "расскажи подробнее" - не понятно о чем
- "а какие еще?" - неясная ссылка

**Решение**: LLM переформулирует в standalone вопрос с учетом истории.

**Преимущества**:
- Поиск находит правильные документы
- LLM видит оригинальный вопрос (естественный диалог)
- Лучший UX (пользователь не повторяет контекст)

### 3. Cited Sources Filtering

**Проблема**: Показываем все 7 найденных источников, даже если LLM использовал 2.

**Решение**:
1. Парсим ответ LLM регулярным выражением
2. Извлекаем номера источников `[1]`, `[2, 3]`
3. Фильтруем sources - показываем только процитированные

**Преимущества**:
- Меньше шума в UI
- Пользователь видит только релевантные источники
- Лучшая читаемость

### 4. Title Chunks Filtering

**Проблема**: Title chunks (только заголовок поста) попадают в топ результаты, но не содержат контекста.

**Решение**:
1. **Data preparation**: Не создаем title chunks (строки 273-275 удалены)
2. **Runtime filtering**: `embedding-worker.js:678` фильтрует `chunk_index === -2`

**Зачем двойная защита**:
- Data preparation - для новых генераций
- Runtime filtering - для старых данных в кеше

### 5. Hybrid Search (BM25 + Semantic)

**Почему hybrid, а не только semantic**:

**BM25 преимущества**:
- Точные совпадения (named entities, аббревиатуры)
- Нет проблем с OOV (out-of-vocabulary)
- Быстрее (не нужен inference)

**Semantic преимущества**:
- Понимает синонимы
- Ловит семантику (не только keywords)
- Работает с парафразами

**Комбинация 30%/70%**:
- BM25 помогает при точных терминах
- Semantic доминирует для смысла
- Min-max нормализация для честного комбинирования

**Пример**:
```
Query: "как нанимать ML инженеров"

BM25 top:
1. "Вакансия ML/DL инженер" (точное совпадение "ML инженер")
2. "Процесс найма в Цельсе" (совпадение "нанимать")

Semantic top:
1. "Процесс найма в Цельсе" (семантически близко к "hiring")
2. "Навыки ML сотрудника" (связано с hiring ML engineers)

Hybrid (30% BM25 + 70% Semantic):
1. "Процесс найма в Цельсе" (высоко в обоих)
2. "Навыки ML сотрудника" (semantic win)
3. "Вакансия ML/DL инженер" (BM25 boost)
```

### 6. Chat History Management

**Почему только 6 сообщений (3 Q&A)**:

**Преимущества**:
- Умещается в контекст LLM
- Не перегружаем OpenRouter API
- Достаточно для диалога

**FIFO принцип**: Старые сообщения удаляются.

```javascript
if (this.chatHistory.length > 6) {
    this.chatHistory = this.chatHistory.slice(-6);  // Последние 6
}
```

### 7. Model Fallback

**Проблема**: OpenRouter блокирует модели в некоторых регионах.

**Решение**: Перебор моделей при ошибках.

```javascript
const modelsToTry = [
    model,  // Запрошенная
    ...FREE_MODELS.filter(m => m !== model)  // Остальные
];

for (const tryModel of modelsToTry) {
    // Try...
    if (success) break;
}
```

**Результат**: Система работает даже если одна модель недоступна.

### 8. Web Worker для ML Inference

**Проблема**: ONNX inference блокирует UI (тормозит чат).

**Решение**: Весь ML код в Web Worker.

**Преимущества**:
- UI остается отзывчивым
- Пользователь видит typing indicator
- Можно отправить новый запрос во время обработки

### 9. Chunk Overlap

**Параметр**: 50 символов overlap

**Зачем**: Контекст не теряется на границах чанков.

**Пример**:
```
Chunk 1: "...машинного обучения. Цельс занимается медицинским AI..."
                                     ↓ overlap
Chunk 2: "...медицинским AI. Мы работаем с рентгеновскими снимками..."
```

Если разрез без overlap попадет на "Цельс занимается", контекст потеряется.

---

## Deployment и инфраструктура

### GitHub Pages

**Статика**:
- `rag-chat.html` - UI
- `assets/js/vector-search.js` - VectorSearch класс
- `assets/js/embedding-worker.js` - Web Worker
- `assets/rag/rag_data_compact.json` - RAG данные (~15MB)

**Jekyll Build**:
```bash
bundle exec jekyll serve
```

**URL**: https://crazyfrogspb.github.io/rag-chat.html

### Cloudflare Workers

**Деплой**:
```bash
cd cloudflare-worker
wrangler deploy
```

**URL**: `https://varim-ml-rag-proxy.crazyfrogspb-rag.workers.dev`

**Environment Variables**:
- `OPENROUTER_API_KEY` - API ключ OpenRouter
- `RATE_LIMIT_KV` - KV namespace для rate limiting

**KV Setup**:
```bash
wrangler kv:namespace create "RATE_LIMIT_KV"
wrangler kv:namespace create "RATE_LIMIT_KV" --preview
```

### HuggingFace Model Hosting

**Репозиторий**: `crazyfrogspb/rubert-mini-frida-onnx`

**Файлы**:
- `model.onnx` (123MB) - ONNX модель
- `config.json` - Конфигурация модели
- `vocab.txt` - Словарь токенов

**Upload script**: `scripts/upload_to_hf.py`

```bash
python scripts/upload_to_hf.py
```

**CDN URL**: `https://huggingface.co/crazyfrogspb/rubert-mini-frida-onnx/resolve/main/model.onnx`

**Зачем HuggingFace**:
- GitHub ограничение 100MB на файл
- HuggingFace CDN бесплатный и быстрый
- Автоматический cache на edge locations

### CI/CD Flow

1. **Local development**:
   ```bash
   bundle exec jekyll serve
   node local-proxy.js  # Локальный прокси вместо Cloudflare Worker
   ```

2. **Регенерация RAG данных**:
   ```bash
   workon breastcancer  # Активируем virtualenv
   python scripts/prepare_rag_data.py
   ```

3. **Commit & Push**:
   ```bash
   git add assets/js/ rag-chat.html
   git commit -m "Update RAG system"
   git push origin master
   ```

4. **GitHub Pages автоматически деплоит** (~1-2 минуты)

5. **Cloudflare Worker** (если изменения в worker):
   ```bash
   cd cloudflare-worker
   wrangler deploy
   ```

### Monitoring

**Cloudflare Dashboard**:
- Request count
- Errors
- Latency
- Rate limit hits

**Browser Console**:
- Hybrid search debug logs
- Embedding generation logs
- Model cache status

**OpenRouter Dashboard**:
- API usage
- Model availability
- Error rates

---

## Технические детали

### Размеры и метрики

**Data**:
- Posts: 78
- Total chunks: 1666
  - Summary chunks: ~70 (один на пост с excerpt)
  - Content chunks: ~1596
- Embeddings: 1666 × 312 = 520,512 floats
- `rag_data_compact.json`: ~15MB

**Model**:
- rubert-mini-frida ONNX: 123MB
- Vocabulary: ~30k tokens
- Embedding dimension: 312

**Performance**:
- Model loading (first time): 30-60 секунд
- Model loading (cached): <1 секунда
- Search (hybrid): 100-300ms
- LLM response: 2-5 секунд

### Параметры чанкинга

```python
chunk_size = 512        # символов
chunk_overlap = 50      # символов
```

**Почему 512**:
- Не слишком большой (контекст не размывается)
- Не слишком маленький (достаточно контекста)
- Хорошо для sentence-transformer моделей

### BM25 параметры

```javascript
k1 = 1.2   // Term frequency saturation
b = 0.75   // Document length normalization
```

**Стандартные значения** из Okapi BM25.

### Hybrid search веса

```javascript
hybridScore = 0.3 * bm25Norm + 0.7 * semanticNorm
```

**Эмпирически подобраны**:
- Semantic важнее (70%) для понимания смысла
- BM25 помогает (30%) при точных терминах

### LLM параметры

**Validation**:
```javascript
{
  max_tokens: 10,
  temperature: 0.1
}
```
- `max_tokens: 10`: Нужно только "ДА"/"НЕТ"
- `temperature: 0.1`: Детерминированный ответ

**Rephrasing**:
```javascript
{
  max_tokens: 200,
  temperature: 0.3
}
```
- `max_tokens: 200`: Переформулированный вопрос
- `temperature: 0.3`: Немного креативности

**Answer Generation**:
```javascript
{
  max_tokens: 1000,
  temperature: 0.7,
  top_p: 0.9
}
```
- `max_tokens: 1000`: Развернутый ответ
- `temperature: 0.7`: Баланс между фактичностью и естественностью
- `top_p: 0.9`: Nucleus sampling

### Rate Limiting

```javascript
MAX_REQUESTS = 10
WINDOW_MINUTES = 5
```

**10 запросов за 5 минут на IP**:
- Достаточно для нормального использования
- Защита от злоупотребления
- Sliding window (не fixed)

### CORS Origins

```javascript
ALLOWED_ORIGINS = [
    'https://crazyfrogspb.github.io',  // Production
    'http://localhost:4000',            // Jekyll default
    'http://127.0.0.1:4000',
    'http://localhost:4002',            // Alternative port
    'http://127.0.0.1:4002'
]
```

**Почему несколько localhost**: Разные порты для разработки.

### API Endpoints Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/chat` | POST | RAG чат с историей | Rate limit |
| `/rephrase` | POST | Query rephrasing | Rate limit |
| `/` | POST | Legacy RAG (без истории) | Rate limit |

---

## Ключевые инсайты

### Почему не использовать только API эмбеддинги?

**Проблема**: Каждый поиск = API call.

**Решение**: Pre-computed embeddings + локальный inference.

**Преимущества**:
- Нет latency API вызова
- Не зависим от внешних сервисов
- Бесплатно (после генерации)

### Почему не использовать vector DB (Pinecone, Weaviate)?

**Проблема**: Нужен backend + платный сервис.

**Решение**: Все в браузере + Cloudflare Workers (serverless).

**Преимущества**:
- Нет затрат на hosting
- Автоматическое масштабирование
- Низкая latency (edge locations)

### Почему не использовать только OpenAI Embeddings?

**Проблема**:
- Дорого для бесплатного блога
- Latency API вызова
- Зависимость от внешнего сервиса

**Решение**: Локальная модель в браузере.

**Trade-off**:
- Первая загрузка долгая (123MB)
- Но: IndexedDB кеш решает проблему

### Почему именно rubert-mini-frida?

**Альтернативы**:
- `sentence-transformers/all-MiniLM-L6-v2` (английский)
- `intfloat/multilingual-e5-small` (многоязычная)

**Выбор rubert-mini-frida**:
- Оптимизирована для русского
- Компактная (123MB vs 400MB+ у больших моделей)
- Хорошее качество для RAG задач

### Почему Hybrid Search вместо только Semantic?

**Real-world пример**:

Query: "Цельс вакансия"

**Только Semantic**:
- Может найти: "Процесс найма", "ML инженер", "команда разработки"
- Может пропустить: Точное название "Цельс" в менее релевантных постах

**Только BM25**:
- Найдет: Все посты с "Цельс" и "вакансия"
- Проблема: Не понимает синонимы ("hiring" = "найм" = "вакансия")

**Hybrid**:
- BM25 гарантирует точные совпадения
- Semantic добавляет семантику
- Best of both worlds

---

## Итоги

**Полный стек RAG системы**:

1. **Data Preparation** (Python):
   - Jekyll posts → chunks + embeddings
   - sentence-transformers локально
   - Сохранение в JSON

2. **Frontend** (JavaScript):
   - VectorSearch координатор
   - Web Worker с ONNX Runtime Web
   - Hybrid search (BM25 + Semantic)
   - IndexedDB кеширование
   - Chat UI с историей

3. **Backend** (Cloudflare Workers):
   - CORS & Rate limiting
   - Query validation
   - Query rephrasing
   - LLM generation (OpenRouter)
   - Model fallback

4. **Infrastructure**:
   - GitHub Pages (статика)
   - Cloudflare Workers (serverless)
   - HuggingFace (model hosting)
   - OpenRouter (LLM API)

**Ключевые особенности**:
- Работает полностью в браузере (кроме LLM)
- Бесплатная инфраструктура
- Автоматическое масштабирование
- Быстрый поиск (hybrid)
- Контекстные диалоги (history + rephrasing)
- Защита от злоупотребления (rate limiting + validation)

**Результат**: Полнофункциональная RAG-система для блога без затрат на инфраструктуру.
