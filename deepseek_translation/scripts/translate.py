#!/usr/bin/env python3
"""
DeepSeek API переводчик с сохранением сегментов
"""

import json
import os
import requests
import time
import re
from pathlib import Path

class DeepSeekTranslator:
    def __init__(self, config_path="config/api_config.json"):
        """Инициализация с конфигурацией"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.api_key = self.config['api_key']
        self.api_url = self.config['api_url']
        self.model = self.config['model']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Для памяти переводов
        self.translation_memory = []
        
    def segment_text(self, text):
        """Сегментация текста на предложения/сегменты"""
        # Разделяем по заголовкам, спискам, абзацам
        segments = []
        
        # Разделяем по строкам и обрабатываем
        lines = text.split('\n')
        current_segment = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Заголовки - отдельные сегменты
            if line.startswith('#') or line.startswith('##') or line.startswith('###'):
                if current_segment:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                segments.append(line)
            # Элементы списка
            elif line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\.', line):
                if current_segment:
                    segments.append('\n'.join(current_segment))
                    current_segment = []
                segments.append(line)
            # Обычный текст
            else:
                # Разбиваем длинные абзацы на предложения
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for sentence in sentences:
                    if sentence.strip():
                        if len(sentence) > 200:
                            # Если предложение слишком длинное, разбиваем по запятым
                            parts = re.split(r'(?<=[,;:])\s+', sentence)
                            for part in parts:
                                if part.strip():
                                    segments.append(part.strip())
                        else:
                            segments.append(sentence.strip())
        
        if current_segment:
            segments.append('\n'.join(current_segment))
        
        return segments
    
    def translate_segment(self, segment):
        """Перевод одного сегмента через DeepSeek API"""
        prompt = f"""Ты профессиональный технический переводчик. Переведи следующий текст с русского на английский.

ВАЖНЫЕ ПРАВИЛА:
1. Сохрани всю разметку Markdown (заголовки, списки, форматирование)
2. Технические термины оставь без изменений (API, MVP, и т.д.)
3. Сохрани форматирование кода и JSON
4. Не добавляй пояснений, только перевод

Исходный текст:
{segment}

Перевод:"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты профессиональный переводчик технической документации."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.get('temperature', 0.3),
            "max_tokens": self.config.get('max_tokens', 2000)
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                translation = result['choices'][0]['message']['content'].strip()
                
                # Сохраняем в память переводов
                self.translation_memory.append({
                    'source': segment,
                    'target': translation,
                    'context': 'technical_spec'
                })
                
                return translation
            else:
                print(f"Ошибка API: {response.status_code}")
                print(response.text)
                return segment  # Возвращаем оригинал в случае ошибки
                
        except Exception as e:
            print(f"Ошибка при переводе: {e}")
            return segment
    
    def translate_file(self, source_path, target_path):
        """Перевод всего файла"""
        # Читаем исходный файл
        with open(source_path, 'r', encoding='utf-8') as f:
            source_text = f.read()
        
        print(f"Загружен файл: {source_path}")
        print(f"Размер: {len(source_text)} символов")
        
        # Сегментация
        segments = self.segment_text(source_text)
        print(f"Сегментов для перевода: {len(segments)}")
        
        # Перевод
        translated_segments = []
        
        for i, segment in enumerate(segments, 1):
            print(f"\nСегмент {i}/{len(segments)}:")
            print(f"Исходный: {segment[:100]}...")
            
            # Пропускаем пустые сегменты
            if not segment.strip():
                translated_segments.append(segment)
                continue
            
            translation = self.translate_segment(segment)
            translated_segments.append(translation)
            
            print(f"Перевод: {translation[:100]}...")
            
            # Задержка для избежания rate limit
            if i % 10 == 0:
                print("Пауза 2 секунды...")
                time.sleep(2)
            else:
                time.sleep(0.5)
        
        # Сохраняем перевод
        translated_text = '\n\n'.join(translated_segments)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        
        print(f"\n✅ Перевод сохранен в: {target_path}")
        
        # Сохраняем память переводов
        self.save_translation_memory()
        
        return translated_text
    
    def save_translation_memory(self):
        """Сохранение памяти переводов в JSON"""
        tm_path = Path("translation_memory") / "deepseek_tm.json"
        tm_path.parent.mkdir(exist_ok=True)
        
        with open(tm_path, 'w', encoding='utf-8') as f:
            json.dump(self.translation_memory, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Память переводов сохранена: {tm_path}")
    
    def save_as_tmx(self):
        """Конвертация JSON памяти переводов в TMX формат"""
        if not self.translation_memory:
            print("Память переводов пуста!")
            return
        
        tmx_template = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tmx SYSTEM "tmx14.dtd">
<tmx version="1.4">
  <header
    creationtool="DeepSeek Translator"
    creationtoolversion="1.0"
    segtype="sentence"
    o-tmf="Unknown"
    adminlang="en-US"
    srclang="ru"
    datatype="plaintext"
  />
  <body>
{tuv_entries}
  </body>
</tmx>'''
        
        tuv_entries = []
        for entry in self.translation_memory:
            source = entry['source'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            target = entry['target'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            tuv_entry = f'''    <tu>
      <tuv xml:lang="ru">
        <seg>{source}</seg>
      </tuv>
      <tuv xml:lang="en">
        <seg>{target}</seg>
      </tuv>
    </tu>'''
            tuv_entries.append(tuv_entry)
        
        tmx_content = tmx_template.format(tuv_entries='\n'.join(tuv_entries))
        
        tmx_path = Path("translation_memory") / "deepseek_translation.tmx"
        with open(tmx_path, 'w', encoding='utf-8') as f:
            f.write(tmx_content)
        
        print(f"✅ TMX файл создан: {tmx_path}")

def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DeepSeek Translator')
    parser.add_argument('--source', default='source/technical_specification_ru.md',
                       help='Исходный файл на русском')
    parser.add_argument('--target', default='translated/technical_specification_en.md',
                       help='Файл для сохранения перевода')
    parser.add_argument('--config', default='config/api_config.json',
                       help='Файл конфигурации API')
    
    args = parser.parse_args()
    
    # Проверяем существование файлов
    if not os.path.exists(args.source):
        print(f"❌ Исходный файл не найден: {args.source}")
        return
    
    if not os.path.exists(args.config):
        print(f"❌ Конфигурационный файл не найден: {args.config}")
        print("Создай config/api_config.json с твоим API ключом")
        return
    
    # Создаем папки
    os.makedirs(os.path.dirname(args.target), exist_ok=True)
    
    # Запускаем перевод
    translator = DeepSeekTranslator(args.config)
    translator.translate_file(args.source, args.target)
    translator.save_as_tmx()

if __name__ == "__main__":
    main()