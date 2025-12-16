#!/usr/bin/env python3
"""
Конвертация rubert-mini-frida в ONNX формат для использования в браузере
"""

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import onnx
import os
from pathlib import Path

def convert_rubert_to_onnx():
    """Конвертирует rubert-mini-frida в ONNX формат"""
    
    model_name = "sergeyzh/rubert-mini-frida"
    output_dir = Path("assets/onnx")
    output_dir.mkdir(exist_ok=True)
    
    print(f"🔄 Загружаем модель {model_name}...")
    
    # Загружаем модель и токенайзер
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    
    print("✅ Модель загружена")
    
    # Подготавливаем пример входных данных
    sample_text = "search_query: тестовый запрос"
    inputs = tokenizer(
        sample_text,
        max_length=512,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )
    
    print("🔄 Конвертируем в ONNX...")
    
    # Экспортируем в ONNX
    onnx_path = output_dir / "rubert-mini-frida.onnx"
    
    torch.onnx.export(
        model,
        (inputs["input_ids"], inputs["attention_mask"]),
        str(onnx_path),
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["input_ids", "attention_mask"],
        output_names=["last_hidden_state"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "sequence"},
            "attention_mask": {0: "batch_size", 1: "sequence"},
            "last_hidden_state": {0: "batch_size", 1: "sequence"}
        }
    )
    
    print(f"✅ ONNX модель сохранена: {onnx_path}")
    
    # Сохраняем токенайзер
    vocab_path = output_dir / "vocab.txt"
    tokenizer_vocab = tokenizer.get_vocab()
    
    # Сортируем по индексам
    sorted_vocab = sorted(tokenizer_vocab.items(), key=lambda x: x[1])
    
    with open(vocab_path, 'w', encoding='utf-8') as f:
        for token, _ in sorted_vocab:
            f.write(f"{token}\n")
    
    print(f"✅ Vocab сохранен: {vocab_path}")
    
    # Сохраняем конфиг
    config_path = output_dir / "config.json"
    config = {
        "model_name": model_name,
        "max_length": 512,
        "embedding_dimension": 312,
        "vocab_size": len(tokenizer_vocab),
        "special_tokens": {
            "cls_token": tokenizer.cls_token,
            "sep_token": tokenizer.sep_token,
            "pad_token": tokenizer.pad_token,
            "unk_token": tokenizer.unk_token,
            "cls_token_id": tokenizer.cls_token_id,
            "sep_token_id": tokenizer.sep_token_id,
            "pad_token_id": tokenizer.pad_token_id,
            "unk_token_id": tokenizer.unk_token_id
        }
    }
    
    import json
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Конфиг сохранен: {config_path}")
    
    # Тестируем ONNX модель
    print("🧪 Тестируем ONNX модель...")
    
    import onnxruntime as ort
    
    # Создаем сессию
    session = ort.InferenceSession(str(onnx_path))
    
    # Тестовый запуск
    ort_inputs = {
        "input_ids": inputs["input_ids"].numpy(),
        "attention_mask": inputs["attention_mask"].numpy()
    }
    
    ort_outputs = session.run(None, ort_inputs)
    
    # Сравниваем с оригинальной моделью
    with torch.no_grad():
        torch_outputs = model(**inputs)
    
    # Проверяем близость результатов
    diff = torch.abs(torch.tensor(ort_outputs[0]) - torch_outputs.last_hidden_state).max()
    print(f"📊 Максимальная разница между PyTorch и ONNX: {diff:.6f}")
    
    if diff < 1e-4:
        print("✅ ONNX модель работает корректно!")
    else:
        print("⚠️ Большая разница между моделями, проверьте конвертацию")
    
    print(f"\n🎉 Конвертация завершена!")
    print(f"📁 Файлы сохранены в: {output_dir}")
    print(f"   - {onnx_path.name} ({onnx_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"   - {vocab_path.name} ({vocab_path.stat().st_size / 1024:.1f} KB)")
    print(f"   - {config_path.name}")

if __name__ == "__main__":
    convert_rubert_to_onnx()
