# Инструкции для Claude Code

## Python окружение

**ВСЕГДА** используй virtualenv `breastcancer` для запуска Python скриптов:

```bash
source /home/crazyfrogspb/.virtualenvs/breastcancer/bin/activate && python scripts/имя_скрипта.py
```

## Пайплайн публикации нового поста

1. **Создание поста** - положить `post.md` и картинки в папку `post/`, запустить:
   ```bash
   source /home/crazyfrogspb/.virtualenvs/breastcancer/bin/activate && python scripts/create_post.py
   ```
   Скрипт интерактивный - требует ввода заголовка и других данных.

2. **Публикация в Telegram** - пользователь публикует пост в канале @varim_ml

3. **Добавление telegram_url** - добавить в front matter поста:
   ```yaml
   telegram_url: https://t.me/varim_ml/XXX
   ```

4. **Обновление просмотров** - синхронизирует views из Telegram для всех постов:
   ```bash
   source /home/crazyfrogspb/.virtualenvs/breastcancer/bin/activate && python scripts/update_views.py
   ```

5. **Обновление индекса** - обновляет `assets/posts_index.json`:
   ```bash
   source /home/crazyfrogspb/.virtualenvs/breastcancer/bin/activate && python scripts/update_posts_index.py
   ```

6. **Коммит и пуш**:
   ```bash
   git add _posts/ assets/posts_index.json && git commit -m "Add new post and update views" && git push
   ```

## Полезные скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/create_post.py` | Создание нового поста из папки `post/` |
| `scripts/update_views.py` | Синхронизация просмотров из Telegram |
| `scripts/update_posts_index.py` | Обновление `assets/posts_index.json` |
| `scripts/prepare_rag_data.py` | Генерация RAG-данных (инкрементальная) |
| `scripts/sync_telegraph.py` | Импорт постов из Telegraph |

## Jekyll / GitHub Pages

- Сайт: https://crazyfrogspb.github.io
- После пуша пересборка занимает 1-2 минуты
- `future: true` в `_config.yml` - публикуются посты с датой в будущем

## Особенности кода

- **YAML парсинг**: В URL-ах Telegraph бывает `---` (например `https://telegra.ph/Title---08-05`).
  НЕ использовать `split('---')` для парсинга front matter!
  Искать `---` только как отдельную строку (см. `update_posts_index.py`).

- **Картинки в постах**: Скрипт `create_post.py` ищет картинки и в корне проекта, и в папке `post/`.

## RAG-система

- RAG-данные хранятся в `assets/rag/rag_data.json`
- Обновление инкрементальное - генерируются эмбеддинги только для новых постов
- Cloudflare Worker для LLM: `https://varim-ml-rag.crazyfrogspb.workers.dev`
