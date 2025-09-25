# Инструкция по настройке Varim ML Blog

## Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/crazyfrogspb/varim_ml.git
cd varim_ml
```

### 2. Установка системных зависимостей

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ruby-full ruby-dev build-essential zlib1g-dev
```

#### macOS:
```bash
brew install ruby
```

### 3. Настройка Ruby окружения
```bash
# Установка зависимостей Jekyll
bundle install

# Если возникают проблемы с правами:
bundle config set --local path 'vendor/bundle'
bundle install
```

### 4. Настройка Python окружения
```bash
# Создание виртуального окружения
mkvirtualenv varim_ml

# Активация окружения
workon varim_ml

# Установка зависимостей
pip install -r requirements.txt
```

### 5. Настройка Telegram API

1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Войдите с помощью номера телефона
3. Создайте новое приложение в разделе "API development tools"
4. Получите `api_id` и `api_hash`

### 6. Настройка переменных окружения

Создайте файл `.env` в корне проекта:
```bash
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
```

Или экспортируйте переменные:
```bash
export TELEGRAM_API_ID=your_api_id_here
export TELEGRAM_API_HASH=your_api_hash_here
```

### 7. Запуск локального сервера Jekyll
```bash
bundle exec jekyll serve --host 0.0.0.0 --port 4000
```

Сайт будет доступен по адресу: http://localhost:4000

### 8. Тестирование синхронизации
```bash
workon varim_ml
python scripts/sync_telegraph.py
```

## Настройка GitHub Pages

### 1. Настройка репозитория
1. Создайте репозиторий на GitHub
2. Загрузите код:
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Настройка GitHub Pages
1. Перейдите в Settings → Pages
2. Выберите источник: "GitHub Actions"

### 3. Настройка Secrets
В Settings → Secrets and variables → Actions добавьте:
- `TELEGRAM_API_ID`: ваш API ID
- `TELEGRAM_API_HASH`: ваш API Hash

### 4. Запуск автоматической синхронизации
После настройки secrets GitHub Actions будет:
- Запускаться каждый день в 6:00 UTC
- Синхронизировать новые посты из @varim_ml
- Автоматически публиковать изменения

## Ручное управление

### Запуск синхронизации вручную
1. Перейдите в Actions → Manual Telegraph Sync
2. Нажмите "Run workflow"
3. Выберите опции:
   - **Force re-sync**: обработать все посты заново
   - **Limit messages**: ограничить количество сообщений

### Создание постов вручную
Создайте файл `_posts/YYYY-MM-DD-название.md`:
```yaml
---
layout: post
title: "Заголовок поста"
date: 2024-01-01 12:00:00 +0300
tags: [машинное-обучение, python]
views: 0
excerpt: "Краткое описание"
---

Содержимое поста в Markdown...
```

## Структура проекта

```
varim_ml/
├── _posts/                 # Jekyll посты
├── _layouts/              # Шаблоны страниц
├── assets/
│   ├── css/              # Стили
│   ├── js/               # JavaScript для фильтрации
│   ├── images/           # Изображения из Telegraph
│   └── posts_index.json  # Индекс постов
├── tags/                 # Страницы тегов
├── scripts/
│   └── sync_telegraph.py # Скрипт синхронизации
├── .github/workflows/    # GitHub Actions
├── _config.yml           # Конфигурация Jekyll
├── Gemfile              # Ruby зависимости
└── requirements.txt     # Python зависимости
```

## Возможные проблемы

### Jekyll не запускается
```bash
# Проверьте версию Ruby
ruby --version

# Переустановите зависимости
bundle clean --force
bundle install
```

### Ошибки компиляции gem'ов
```bash
# Установите дополнительные пакеты
sudo apt install gcc make

# Для macOS
xcode-select --install
```

### Проблемы с Python зависимостями
```bash
# Обновите pip
pip install --upgrade pip

# Переустановите зависимости
pip install -r requirements.txt --force-reinstall
```

### Ошибки Telegram API
- Проверьте правильность API_ID и API_HASH
- Убедитесь, что переменные окружения установлены
- При первом запуске может потребоваться ввод кода подтверждения

## Дополнительные возможности

### Кастомизация дизайна
Редактируйте файлы в `assets/css/` и `_layouts/`

### Добавление новых фильтров
Модифицируйте `assets/js/posts-filter.js`

### Изменение логики синхронизации
Редактируйте `scripts/sync_telegraph.py`

## Поддержка

При возникновении проблем:
1. Проверьте логи GitHub Actions
2. Убедитесь в правильности настройки API ключей
3. Создайте issue в репозитории
