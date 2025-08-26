#!/usr/bin/env python3
"""Тест интеграции новых методов сегментации с AudioProcessor"""

import os
import sys
import time
import json
from pathlib import Path

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent / 'src'))

def test_integration():
    """Тестируем интеграцию новых методов сегментации"""
    print("🎯 ТЕСТ ИНТЕГРАЦИИ НОВЫХ МЕТОДОВ СЕГМЕНТАЦИИ")
    print("=" * 70)
    
    # Аудио файл для тестирования
    audio_file = "data/temp_audio/Альфа неипотечные сделки вторичка 01.08.2025 ч2_compressed_prepared_compressed.wav"
    
    if not os.path.exists(audio_file):
        print(f"❌ Аудио файл не найден: {audio_file}")
        return
    
    try:
        # Импортируем AudioProcessor
        from audio_processor import AudioProcessor
        
        # Создаем экземпляр
        print("🚀 Инициализирую AudioProcessor...")
        processor = AudioProcessor()
        
        # Тестируем разные методы сегментации
        methods = ['energy', 'intonation', 'emotion', 'adaptive']
        
        results = {}
        
        for method in methods:
            print(f"\n🎵 Тестирую метод: {method.upper()}")
            print("-" * 50)
            
            try:
                start_time = time.time()
                
                # Запускаем продвинутую сегментацию
                result = processor.process_audio_file_with_advanced_segmentation(audio_file, method)
                
                processing_time = time.time() - start_time
                
                if result:
                    results[method] = {
                        'success': True,
                        'time': processing_time,
                        'segments': result.get('total_segments', 0),
                        'speakers': len(result.get('speakers', {})),
                        'total_text_length': sum(len(t.get('text', '')) for t in result.get('raw_transcriptions', [])),
                        'segmentation_method': result.get('segmentation_method', 'unknown')
                    }
                    
                    print(f"✅ Успешно! Время: {processing_time:.2f}с")
                    print(f"📊 Сегментов: {results[method]['segments']}")
                    print(f"👥 Спикеров: {results[method]['speakers']}")
                    print(f"📝 Общая длина текста: {results[method]['total_text_length']} символов")
                    
                    # Сохраняем результат
                    save_method_result(audio_file, method, result)
                    
                else:
                    results[method] = {
                        'success': False,
                        'error': 'Результат пустой',
                        'time': processing_time
                    }
                    print("❌ Результат пустой")
                    
            except Exception as e:
                results[method] = {
                    'success': False,
                    'error': str(e),
                    'time': 0
                }
                print(f"❌ Ошибка: {e}")
        
        # Выводим итоги
        print_comparison_summary(results)
        
        # Сохраняем общие результаты
        save_overall_results(audio_file, results)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

def save_method_result(audio_file: str, method: str, result: dict):
    """Сохраняем результат конкретного метода"""
    try:
        # Создаем папку для результатов
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = Path(f'data/audio_processing/{base_name}_integration_test/{method}')
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
            
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        # Сохраняем как TXT
        txt_file = output_dir / 'transcript.txt'
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"Транскрипция: {method.upper()}\n")
            f.write(f"Файл: {audio_file}\n")
            f.write(f"Время обработки: {result.get('processed_at', '')}\n")
            f.write(f"Сегментов: {result.get('total_segments', 0)}\n")
            f.write(f"Спикеров: {len(result.get('speakers', {}))}\n")
            f.write("-" * 50 + "\n\n")
            
            for trans in result.get('raw_transcriptions', []):
                f.write(f"[{trans.get('start_time', 0)}ms - {trans.get('end_time', 0)}ms] ")
                f.write(f"Сегмент {trans.get('segment', '?')} ({trans.get('segmentation_method', 'unknown')})\n")
                f.write(f"{trans.get('text', '')}\n\n")
        
        print(f"💾 Результат сохранен: {output_dir}")
        
    except Exception as e:
        print(f"⚠️ Ошибка сохранения результата {method}: {e}")

def save_overall_results(audio_file: str, results: dict):
    """Сохраняем общие результаты сравнения"""
    try:
        # Создаем папку для общих результатов
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        output_dir = Path(f'data/audio_processing/{base_name}_integration_test')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем как JSON
        json_file = output_dir / 'overall_results.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Сохраняем как Markdown
        md_file = output_dir / 'overall_results.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Результаты интеграции методов сегментации\n\n")
            f.write(f"Файл: {audio_file}\n")
            f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Сравнение методов\n\n")
            f.write("| Метод | Статус | Время (с) | Сегментов | Спикеров | Длина текста |\n")
            f.write("|-------|---------|-----------|-----------|----------|--------------|\n")
            
            for method, data in results.items():
                if data['success']:
                    f.write(f"| {method.upper()} | ✅ | {data['time']:.2f} | {data['segments']} | {data['speakers']} | {data['total_text_length']} |\n")
                else:
                    f.write(f"| {method.upper()} | ❌ | - | - | - | - |\n")
            
            f.write("\n## Детали\n\n")
            
            for method, data in results.items():
                f.write(f"### {method.upper()}\n")
                f.write(f"- **Статус**: {'✅ Успешно' if data['success'] else '❌ Ошибка'}\n")
                
                if data['success']:
                    f.write(f"- **Время обработки**: {data['time']:.2f}с\n")
                    f.write(f"- **Количество сегментов**: {data['segments']}\n")
                    f.write(f"- **Количество спикеров**: {data['speakers']}\n")
                    f.write(f"- **Общая длина текста**: {data['total_text_length']} символов\n")
                    f.write(f"- **Метод сегментации**: {data['segmentation_method']}\n")
                else:
                    f.write(f"- **Ошибка**: {data.get('error', 'Неизвестная ошибка')}\n")
                
                f.write("\n")
        
        print(f"💾 Общие результаты сохранены: {output_dir}")
        
    except Exception as e:
        print(f"⚠️ Ошибка сохранения общих результатов: {e}")

def print_comparison_summary(results: dict):
    """Выводим итоги сравнения"""
    print("\n" + "=" * 70)
    print("📊 ИТОГИ ИНТЕГРАЦИИ")
    print("=" * 70)
    
    successful_methods = [r for r in results.values() if r['success']]
    failed_methods = [r for r in results.values() if not r['success']]
    
    print(f"✅ Успешных методов: {len(successful_methods)}")
    print(f"❌ Неудачных методов: {len(failed_methods)}")
    
    if successful_methods:
        print("\n🏆 РЕЙТИНГ ПО СКОРОСТИ:")
        sorted_by_speed = sorted(successful_methods, key=lambda x: x['time'])
        for i, method in enumerate(sorted_by_speed, 1):
            method_name = [k for k, v in results.items() if v == method][0]
            print(f"{i}. {method_name.upper()}: {method['time']:.2f}с")
        
        print("\n📊 РЕЙТИНГ ПО КОЛИЧЕСТВУ СЕГМЕНТОВ:")
        sorted_by_segments = sorted(successful_methods, key=lambda x: x['segments'], reverse=True)
        for i, method in enumerate(sorted_by_segments, 1):
            method_name = [k for k, v in results.items() if v == method][0]
            print(f"{i}. {method_name.upper()}: {method['segments']} сегментов")
        
        print("\n📝 РЕЙТИНГ ПО ДЛИНЕ ТЕКСТА:")
        sorted_by_text = sorted(successful_methods, key=lambda x: x['total_text_length'], reverse=True)
        for i, method in enumerate(sorted_by_text, 1):
            method_name = [k for k, v in results.items() if v == method][0]
            print(f"{i}. {method_name.upper()}: {method['total_text_length']} символов")
    
    if failed_methods:
        print("\n❌ НЕУДАЧНЫЕ МЕТОДЫ:")
        for method_name, method_data in results.items():
            if not method_data['success']:
                print(f"- {method_name.upper()}: {method_data.get('error', 'Неизвестная ошибка')}")
    
    print(f"\n💾 Все результаты сохранены в папке: data/audio_processing/[имя_файла]_integration_test/")

if __name__ == "__main__":
    test_integration()
