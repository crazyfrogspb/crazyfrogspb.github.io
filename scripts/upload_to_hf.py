#!/usr/bin/env python3

from huggingface_hub import HfApi, create_repo
import os
from dotenv import load_dotenv

load_dotenv()

# Токен HuggingFace
token = os.getenv("HUGGINGFACE_TOKEN")
if not token:
    raise ValueError(
        "HUGGINGFACE_TOKEN не найден в переменных окружения.\n"
        "Создайте файл .env и добавьте:\n"
        "HUGGINGFACE_TOKEN=your_token_here"
    )

# Создаем API клиент
api = HfApi(token=token)

# Параметры
repo_id = "crazyfrogspb/rubert-mini-frida-onnx"
repo_type = "model"

# Создаем репозиторий
print(f"Создаем репозиторий {repo_id}...")
create_repo(
    repo_id=repo_id,
    token=token,
    repo_type=repo_type,
    exist_ok=True
)
print("✅ Репозиторий создан или уже существует")

# Загружаем файлы
files_to_upload = [
    ("assets/onnx/rubert-mini-frida.onnx", "model.onnx"),
    ("assets/onnx/config.json", "config.json"),
    ("assets/onnx/vocab.txt", "vocab.txt")
]

for local_path, hf_path in files_to_upload:
    full_path = os.path.join("/media/crazyfrogspb/Repos/varim_ml", local_path)
    if os.path.exists(full_path):
        size_mb = os.path.getsize(full_path) / (1024 * 1024)
        print(f"📤 Загружаем {hf_path} ({size_mb:.1f} MB)...")

        api.upload_file(
            path_or_fileobj=full_path,
            path_in_repo=hf_path,
            repo_id=repo_id,
            repo_type=repo_type,
            token=token
        )
        print(f"✅ {hf_path} загружен")
    else:
        print(f"⚠️ Файл не найден: {full_path}")

print(f"\n🎉 Готово! Модель доступна: https://huggingface.co/{repo_id}")
