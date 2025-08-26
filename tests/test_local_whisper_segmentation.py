#!/usr/bin/env python3
"""Тест Energy и Adaptive сегментации с локальным Whisper"""

import os
import sys
import time
import json
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / 'src'))

def test_local_whisper_segmentation():
    """Тестируем Energy и Adaptive сегментацию с локальным Whisper"""
    print("🎯 ТЕСТ ENERGY И ADAPTIVE СЕГМЕНТАЦИИ + ЛОКАЛЬНЫЙ WHISPER")
    print("=" * 70)
    
    # Аудио файл для тестирования
    audio_file = "data/temp_audio/Альфа неипотечные сделки вторичка 01.08.2025 ч2_compressed_prepared_compressed.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Аудио файл не найден: {audio_file}")
        return
    
    try:
        # Импортируем AudioProcessor
        from audio_processor import AudioProcessor
        
        # Создаем экземпляр с локальным Whisper
        print("🚀 Инициализирую AudioProcessor с локальным Whisper...")
        
        # Устанавливаем переменные окружения для локального Whisper
        os.environ['TRANSCRIPTION_METHOD'] = 'whisper'
        os.environ['WHISPER_MODEL_LOCAL'] = 'base'
        
        processor = AudioProcessor()
        print(f"✅ Метод транскрипции: {processor.transcription_method}")
        
        # Тестируем Energy сегментацию
        print("\n⚡ Тестирую Energy сегментацию...")
        print("-" * 50)
        
        start_time = time.time()
        energy_result = processor.process_audio_file_with_advanced_segmentation(audio_file, 'energy')
        energy_time = time.time() - start_time
        
        if energy_result:
            print(f"✅ Energy сегментация завершена за {energy_time:.2f}с")
            print(f"📊 Сегментов: {energy_result.get('total_segments', 0)}")
            print(f"👥 Спикеров: {len(energy_result.get('speakers', {}))}")
            
            # Анализируем транскрипции
            analyze_transcriptions(energy_result, 'energy')
            
            # Сохраняем результат
            save_segmentation_result(audio_file, 'energy', energy_result, energy_time)
        else:
            print("❌ Energy сегментация не удалась")
        
        # Тестируем Adaptive сегментацию
        print("\n🧠 Тестирую Adaptive сегментацию...")
        print("-" * 50)
        
        start_time = time.time()
        adaptive_result = processor.process_audio_file_with_advanced_segmentation(audio_file, 'adaptive')
        adaptive_time = time.time() - start_time
        
        if adaptive_result:
            print(f"✅ Adaptive сегментация завершена за {adaptive_time:.2f}с")
            print(f"📊 Сегментов: {adaptive_result.get('total_segments', 0)}")
            print(f"👥 Спикеров: {len(adaptive_result.get('speakers', {}))}")
            
            # Анализируем транскрипции
            analyze_transcriptions(adaptive_result, 'adaptive')
            
            # Сохраняем результат
            save_segmentation_result(audio_file, 'adaptive', adaptive_result, adaptive_time)
        else:
            print("❌ Adaptive сегментация не удалась")
        
        # Сравниваем результаты
        if energy_result and adaptive_result:
            compare_results(energy_result, adaptive_result, energy_time, adaptive_time)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

def analyze_transcriptions(result: dict, method_name: str):
    """Анализируем качество транскрипций"""
    print(f"\n📝 АНАЛИЗ ТРАНСКРИПЦИЙ ({method_name.upper()}):")
    
    raw_transcriptions = result.get('raw_transcriptions', [])
    if not raw_transcriptions:
        print("❌ Нет транскрипций для анализа")
        return
    
    # Статистика по сегментам
    total_text_length = 0
    segment_lengths = []
    empty_segments = 0
    
    for trans in raw_transcriptions:
        text = trans.get('text', '')
        text_length = len(text)
        total_text_length += text_length
        segment_lengths.append(text_length)
        
        if text_length == 0:
            empty_segments += 1
    
    print(f"📊 Общая статистика:")
    print(f"   • Всего сегментов: {len(raw_transcriptions)}")
    print(f"   • Пустых сегментов: {empty_segments}")
    print(f"   • Общая длина текста: {total_text_length} символов")
    print(f"   • Средняя длина сегмента: {total_text_length / len(raw_transcriptions):.1f} символов")
    
    # Анализ по длине сегментов
    if segment_lengths:
        min_length = min(segment_lengths)
        max_length = max(segment_lengths)
        print(f"   • Минимальная длина: {min_length} символов")
        print(f"   • Максимальная длина: {max_length} символов")
    
    # Показываем несколько примеров
    print(f"\n📋 Примеры транскрипций:")
    for i, trans in enumerate(raw_transcriptions[:3]):  # Показываем первые 3
        text = trans.get('text', '')
        start_time = trans.get('start_time', 0)
        end_time = trans.get('end_time', 0)
        duration = trans.get('duration', 0)
        
        print(f"   Сегмент {i+1}: [{start_time}ms - {end_time}ms] ({duration}ms)")
        print(f"   Текст: {text[:100]}{'...' if len(text) > 100 else ''}")
        print()

def save_segmentation_result(audio_file: str, method: str, result: dict, processing_time: float):
    """Сохраняем результат сегментации"""
    try:
        # Создаем папку для результатов
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = Path(f'data/audio_processing/{base_name}_local_whisper_test/{method}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем как JSON
        json_file = output_dir / 'result.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            # Убираем numpy массивы для JSON
            json_result = {}
            for key, value in result.items():
                if key == 'raw_transcriptions':
                    json_result[key] = []
                    for trans in value:
                        json_trans = {
                            'segment': trans.get('segment'),
                            'start_time': trans.get('start_time'),
                            'end_time': trans.get('end_time'),
                            'duration': trans.get('duration'),
                            'text': trans.get('text'),
                            'segmentation_method': trans.get('segmentation_method')
                        }
                        json_result[key].append(json_trans)
                elif key == 'speakers':
                    json_result[key] = {}
                    for speaker, segments in value.items():
                        json_result[key][speaker] = []
                        for seg in segments:
                            json_seg = {
                                'segment': seg.get('segment'),
                                'start_time': seg.get('start_time'),
                                'end_time': seg.get('end_time'),
                                'duration': seg.get('duration'),
                                'text': seg.get('text')
                            }
                            json_result[key][speaker].append(json_seg)
                else:
                    json_result[key] = value
            
            # Добавляем информацию о времени обработки
            json_result['processing_time'] = processing_time
            json_result['method'] = method
            
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        # Сохраняем как TXT
        txt_file = output_dir / 'transcript.txt'
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"ТРАНСКРИПЦИЯ: {method.upper()} СЕГМЕНТАЦИЯ + ЛОКАЛЬНЫЙ WHISPER\n")
            f.write(f"Файл: {audio_file}\n")
            f.write(f"Время обработки: {result.get('processed_at', '')}\n")
            f.write(f"Время выполнения: {processing_time:.2f}с\n")
            f.write(f"Сегментов: {result.get('total_segments', 0)}\n")
            f.write(f"Спикеров: {len(result.get('speakers', {}))}\n")
            f.write(f"Метод сегментации: {result.get('segmentation_method', 'unknown')}\n")
            f.write("-" * 80 + "\n\n")
            
            for trans in result.get('raw_transcriptions', []):
                f.write(f"[{trans.get('start_time', 0)}ms - {trans.get('end_time', 0)}ms] ")
                f.write(f"Сегмент {trans.get('segment', '?')} ({trans.get('segmentation_method', 'unknown')})\n")
                f.write(f"Длительность: {trans.get('duration', 0)}ms\n")
                f.write(f"Текст: {trans.get('text', '')}\n")
                f.write("-" * 40 + "\n\n")
        
        print(f"💾 Результат сохранен: {output_dir}")
        
    except Exception as e:
        print(f"⚠️ Ошибка сохранения результата {method}: {e}")

def compare_results(energy_result: dict, adaptive_result: dict, energy_time: float, adaptive_time: float):
    """Сравниваем результаты двух методов"""
    print("\n" + "=" * 70)
    print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("=" * 70)
    
    # Сравниваем количество сегментов
    energy_segments = energy_result.get('total_segments', 0)
    adaptive_segments = adaptive_result.get('total_segments', 0)
    
    print(f"🔢 КОЛИЧЕСТВО СЕГМЕНТОВ:")
    print(f"   • Energy: {energy_segments}")
    print(f"   • Adaptive: {adaptive_segments}")
    print(f"   • Разница: {abs(energy_segments - adaptive_segments)}")
    
    # Сравниваем время обработки
    print(f"\n⏱️ ВРЕМЯ ОБРАБОТКИ:")
    print(f"   • Energy: {energy_time:.2f}с")
    print(f"   • Adaptive: {adaptive_time:.2f}с")
    print(f"   • Разница: {abs(energy_time - adaptive_time):.2f}с")
    
    # Сравниваем качество транскрипций
    energy_transcriptions = energy_result.get('raw_transcriptions', [])
    adaptive_transcriptions = adaptive_result.get('raw_transcriptions', [])
    
    energy_text_length = sum(len(t.get('text', '')) for t in energy_transcriptions)
    adaptive_text_length = sum(len(t.get('text', '')) for t in adaptive_transcriptions)
    
    print(f"\n📝 КАЧЕСТВО ТРАНСКРИПЦИЙ:")
    print(f"   • Energy: {energy_text_length} символов")
    print(f"   • Adaptive: {adaptive_text_length} символов")
    print(f"   • Разница: {abs(energy_text_length - adaptive_text_length)} символов")
    
    # Сравниваем количество спикеров
    energy_speakers = len(energy_result.get('speakers', {}))
    adaptive_speakers = len(adaptive_result.get('speakers', {}))
    
    print(f"\n👥 КОЛИЧЕСТВО СПИКЕРОВ:")
    print(f"   • Energy: {energy_speakers}")
    print(f"   • Adaptive: {adaptive_speakers}")
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if energy_segments > adaptive_segments:
        print("   • Energy дает более детальную сегментацию")
    else:
        print("   • Adaptive дает более детальную сегментацию")
    
    if energy_time < adaptive_time:
        print("   • Energy работает быстрее")
    else:
        print("   • Adaptive работает быстрее")
    
    if energy_text_length > adaptive_text_length:
        print("   • Energy дает более длинные транскрипции")
    else:
        print("   • Adaptive дает более длинные транскрипции")
    
    print(f"\n📁 Все результаты сохранены в папке: data/audio_processing/[имя_файла]_local_whisper_test/")

if __name__ == "__main__":
    test_local_whisper_segmentation()
