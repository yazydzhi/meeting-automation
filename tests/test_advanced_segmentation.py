#!/usr/bin/env python3
"""Тест продвинутых методов сегментации"""

import os
import sys
import time
import json
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / 'src'))

def test_advanced_segmentation():
    """Тестируем продвинутые методы сегментации"""
    print("🎯 ТЕСТ ПРОДВИНУТЫХ МЕТОДОВ СЕГМЕНТАЦИИ")
    print("=" * 60)
    
    # Аудио файл для тестирования
    audio_file = "data/temp_audio/Альфа неипотечные сделки вторичка 01.08.2025 ч2_compressed_prepared_compressed.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Аудио файл не найден: {audio_file}")
        return
    
    try:
        # Импортируем модуль
        from advanced_segmentation import AdvancedSegmentation
        
        # Создаем экземпляр
        print("🚀 Инициализирую AdvancedSegmentation...")
        segmenter = AdvancedSegmentation()
        
        # Тестируем интонационную сегментацию
        print("\n🎵 Тестирую интонационную сегментацию...")
        start_time = time.time()
        intonation_segments = segmenter.segment_by_intonation_patterns(audio_file)
        intonation_time = time.time() - start_time
        
        print(f"✅ Интонационная сегментация: {len(intonation_segments)} сегментов за {intonation_time:.2f}с")
        
        # Тестируем эмоциональную сегментацию
        print("\n😊 Тестирую эмоциональную сегментацию...")
        start_time = time.time()
        emotion_segments = segmenter.segment_by_emotional_patterns(audio_file)
        emotion_time = time.time() - start_time
        
        print(f"✅ Эмоциональная сегментация: {len(emotion_segments)} сегментов за {emotion_time:.2f}с")
        
        # Тестируем энергетическую сегментацию
        print("\n⚡ Тестирую энергетическую сегментацию...")
        start_time = time.time()
        energy_segments = segmenter.segment_by_energy_patterns(audio_file)
        energy_time = time.time() - start_time
        
        print(f"✅ Энергетическая сегментация: {len(energy_segments)} сегментов за {energy_time:.2f}с")
        
        # Тестируем контекстно-адаптивную сегментацию
        print("\n🧠 Тестирую контекстно-адаптивную сегментацию...")
        start_time = time.time()
        adaptive_segments = segmenter.segment_by_context_awareness(audio_file)
        adaptive_time = time.time() - start_time
        
        print(f"✅ Адаптивная сегментация: {len(adaptive_segments)} сегментов за {adaptive_time:.2f}с")
        
        # Сохраняем результаты
        save_segmentation_results(audio_file, {
            'intonation': {
                'segments': intonation_segments,
                'time': intonation_time,
                'count': len(intonation_segments)
            },
            'emotion': {
                'segments': emotion_segments,
                'time': emotion_time,
                'count': len(emotion_segments)
            },
            'energy': {
                'segments': energy_segments,
                'time': energy_time,
                'count': len(energy_segments)
            },
            'adaptive': {
                'segments': adaptive_segments,
                'time': adaptive_time,
                'count': len(adaptive_segments)
            }
        })
        
        # Выводим итоги
        print_comparison_summary({
            'intonation': intonation_segments,
            'emotion': emotion_segments,
            'energy': energy_segments,
            'adaptive': adaptive_segments
        })
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def save_segmentation_results(audio_file: str, results: dict):
    """Сохраняем результаты сегментации"""
    try:
        # Создаем папку для результатов
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = Path(f'data/audio_processing/{base_name}_advanced_segmentation')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем как JSON
        json_file = output_dir / 'segmentation_results.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            # Конвертируем numpy массивы в списки для JSON
            json_results = {}
            for method, data in results.items():
                json_results[method] = {
                    'time': data['time'],
                    'count': data['count'],
                    'segments': []
                }
                
                for segment in data['segments']:
                    # Убираем numpy массивы из сегментов
                    json_segment = {
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'duration': segment['duration'],
                        'start_sample': segment.get('start_sample', 0),
                        'end_sample': segment.get('end_sample', 0),
                        'segmentation_method': segment.get('segmentation_method', 'unknown')
                    }
                    json_results[method]['segments'].append(json_segment)
            
            json.dump(json_results, f, ensure_ascii=False, indent=2)
        
        # Сохраняем как Markdown
        md_file = output_dir / 'segmentation_results.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Результаты продвинутой сегментации\n\n")
            f.write(f"Файл: {audio_file}\n")
            f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Сравнение методов\n\n")
            f.write("| Метод | Количество сегментов | Время выполнения |\n")
            f.write("|-------|---------------------|------------------|\n")
            
            for method, data in results.items():
                f.write(f"| {method.title()} | {data['count']} | {data['time']:.2f}с |\n")
            
            f.write("\n## Детали сегментов\n\n")
            
            for method, data in results.items():
                f.write(f"### {method.title()}\n")
                f.write(f"- **Количество сегментов**: {data['count']}\n")
                f.write(f"- **Время выполнения**: {data['time']:.2f}с\n\n")
                
                if data['segments']:
                    f.write("| № | Начало (мс) | Конец (мс) | Длительность (мс) |\n")
                    f.write("|---|--------------|-------------|-------------------|\n")
                    
                    for i, segment in enumerate(data['segments']):
                        f.write(f"| {i+1} | {segment['start_time']} | {segment['end_time']} | {segment['duration']} |\n")
                
                f.write("\n")
        
        print(f"💾 Результаты сохранены в: {output_dir}")
        
    except Exception as e:
        print(f"⚠️ Ошибка сохранения результатов: {e}")

def print_comparison_summary(results: dict):
    """Выводим итоги сравнения"""
    print("\n" + "=" * 60)
    print("📊 ИТОГИ СЕГМЕНТАЦИИ")
    print("=" * 60)
    
    print("\n🏆 РЕЙТИНГ ПО КОЛИЧЕСТВУ СЕГМЕНТОВ:")
    sorted_by_count = sorted(results.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (method, segments) in enumerate(sorted_by_count, 1):
        print(f"{i}. {method.title()}: {len(segments)} сегментов")
    
    print("\n⏱️ РЕЙТИНГ ПО СКОРОСТИ:")
    # Здесь нужно будет добавить время выполнения, если оно доступно
    
    print("\n📁 РЕЗУЛЬТАТЫ СОХРАНЕНЫ В:")
    print("data/audio_processing/[имя_файла]_advanced_segmentation/")
    print("- segmentation_results.json - детальные результаты")
    print("- segmentation_results.md - отчет в Markdown")
    print("- [имя_файла]_visualizations/ - графики и визуализации")

if __name__ == "__main__":
    test_advanced_segmentation()
