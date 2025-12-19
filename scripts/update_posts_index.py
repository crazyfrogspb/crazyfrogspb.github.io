#!/usr/bin/env python3
"""
Скрипт для обновления индекса постов
"""

import json
import re
from pathlib import Path
from datetime import datetime
import yaml

def update_posts_index():
    """Обновляет файл assets/posts_index.json на основе постов в _posts/"""
    
    posts_dir = Path('_posts')
    posts = []
    
    if not posts_dir.exists():
        print("Директория _posts не найдена")
        return
    
    for post_file in posts_dir.glob('*.md'):
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разделяем front matter и контент
            # Ищем --- только в начале строки (чтобы не ломать URL с --- внутри)
            if content.startswith('---'):
                # Находим второй --- в начале строки
                lines = content.split('\n')
                fm_end = None
                for i, line in enumerate(lines[1:], 1):  # Пропускаем первую строку с ---
                    if line.strip() == '---':
                        fm_end = i
                        break

                if fm_end:
                    front_matter_text = '\n'.join(lines[1:fm_end])
                    front_matter = yaml.safe_load(front_matter_text)

                    # Извлекаем дату из имени файла
                    date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})-', post_file.name)
                    if date_match:
                        year, month, day = date_match.groups()
                        url_path = f"/{year}/{month}/{day}/{post_file.stem[11:]}/"
                    else:
                        url_path = f"/{post_file.stem}/"

                    posts.append({
                        'title': front_matter.get('title', post_file.stem),
                        'url': url_path,
                        'date': str(front_matter.get('date', '')),
                        'tags': front_matter.get('tags', []),
                        'views': front_matter.get('views', 0),
                        'excerpt': front_matter.get('excerpt', ''),
                        'telegraph_url': front_matter.get('telegraph_url', ''),
                        'telegram_url': front_matter.get('telegram_url', '')
                    })
                    
        except Exception as e:
            print(f"Ошибка обработки {post_file}: {e}")
            continue
    
    # Сортируем по дате (новые сначала)
    posts.sort(key=lambda x: x['date'], reverse=True)
    
    # Создаем JSON
    posts_index = {
        'posts': posts,
        'last_updated': datetime.now().isoformat(),
        'total_posts': len(posts)
    }
    
    # Создаем директорию если не существует
    assets_dir = Path('assets')
    assets_dir.mkdir(exist_ok=True)
    
    # Сохраняем
    index_file = assets_dir / 'posts_index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(posts_index, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Обновлен индекс: {len(posts)} постов")
    print(f"📄 Файл сохранен: {index_file}")
    
    # Показываем последние 5 постов
    print("\n📝 Последние посты:")
    for i, post in enumerate(posts[:5]):
        print(f"  {i+1}. {post['title']}")
        print(f"     📅 {post['date']}")
        print(f"     🏷️  {', '.join(post['tags'])}")
        print(f"     👁️  {post['views']} просмотров")
        print()

if __name__ == '__main__':
    update_posts_index()
