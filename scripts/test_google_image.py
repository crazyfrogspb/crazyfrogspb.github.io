#!/usr/bin/env python3
"""
Тестовый скрипт для проверки загрузки Google-изображений
"""

import asyncio
import aiohttp
import aiofiles
import hashlib
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_google_image_download():
    """Тестирует загрузку Google-изображения"""
    
    # URL изображения из вашего примера
    test_url = "https://lh4.googleusercontent.com/36eRiO69Zak85PnMVU2vsTpvucJUX5039eF7LENC4vnsB9WQczIXAVX0HH0LSNN7atHWTQzD3hyUe9X0V2ERw0a5zJ2FDErSDhsTT2GBuCcPE6rthVGu7GwnNdPnqr2WFSCNkx_WF1_BfqQwCAvzWwIxV9jqK9hh4Kdt1mkyfSijj4q8rhuoQ_79_awl"
    
    # Добавляем параметр размера для Google
    if "?" in test_url:
        test_url += "&sz=w2000"
    else:
        test_url += "?sz=w2000"
    
    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }
    
    # Создаем директорию для тестовых изображений
    test_dir = Path(__file__).parent.parent / "test_images"
    test_dir.mkdir(exist_ok=True)
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Попытка {attempt + 1}/{max_retries}: загрузка {test_url}")
                
                async with session.get(test_url, headers=headers) as response:
                    logger.info(f"Статус ответа: {response.status}")
                    logger.info(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
                    logger.info(f"Content-Length: {response.headers.get('content-length', 'unknown')}")
                    
                    if response.status == 200:
                        # Генерируем имя файла
                        img_hash = hashlib.md5(test_url.encode()).hexdigest()[:8]
                        content_type = response.headers.get('content-type', '')
                        
                        if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                            img_ext = 'jpg'
                        elif 'image/png' in content_type:
                            img_ext = 'png'
                        elif 'image/gif' in content_type:
                            img_ext = 'gif'
                        elif 'image/webp' in content_type:
                            img_ext = 'webp'
                        else:
                            img_ext = 'jpg'  # По умолчанию
                        
                        img_filename = f"test_google_{img_hash}.{img_ext}"
                        img_path = test_dir / img_filename
                        
                        # Сохраняем изображение
                        content = await response.read()
                        async with aiofiles.open(img_path, "wb") as f:
                            await f.write(content)
                        
                        logger.info(f"✅ Изображение успешно сохранено: {img_path}")
                        logger.info(f"Размер файла: {len(content)} байт")
                        return True
                        
                    else:
                        logger.warning(f"❌ Ошибка HTTP: {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            
            except Exception as e:
                logger.error(f"❌ Ошибка при попытке {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
    
    logger.error("❌ Не удалось загрузить изображение после всех попыток")
    return False

if __name__ == "__main__":
    asyncio.run(test_google_image_download())
