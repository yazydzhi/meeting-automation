#!/usr/bin/env python3
"""
Audio Processor with Whisper Integration
Обработчик аудио файлов с использованием OpenAI Whisper API
и разделением на участников разговора
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import tempfile
import shutil

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager

try:
    import openai
    # Временно отключаем pydub для тестирования
    # from pydub import AudioSegment
    # from pydub.silence import split_on_silence
    print("⚠️ Pydub временно отключен для тестирования")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip install openai pydub")
    sys.exit(1)


class AudioProcessor:
    """Обработчик аудио файлов с Whisper и разделением на участников"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Инициализация процессора аудио"""
        self.config = ConfigManager(config_path)
        self.setup_logging()
        self.setup_openai()
        self.setup_directories()
        
    def setup_logging(self):
        """Настройка логирования"""
        log_level = self.config.get('LOG_LEVEL', 'INFO')
        log_file = self.config.get('LOG_FILE', 'logs/audio_processing.log')
        
        # Создаем директорию для логов если не существует
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_openai(self):
        """Настройка OpenAI API"""
        api_key = self.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY не найден в конфигурации")
            
        openai.api_key = api_key
        
        # Опционально устанавливаем организацию
        org_id = self.config.get('OPENAI_ORGANIZATION')
        if org_id:
            openai.organization = org_id
            
        self.logger.info("OpenAI API настроен успешно")
        
    def setup_directories(self):
        """Создание необходимых директорий"""
        dirs = [
            self.config.get('AUDIO_PROCESSING_ROOT', 'data/audio_processing'),
            self.config.get('TRANSCRIPT_OUTPUT_ROOT', 'data/transcripts'),
            self.config.get('TEMP_AUDIO_ROOT', 'data/temp_audio')
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            self.logger.debug(f"Директория создана/проверена: {dir_path}")
            
    def process_audio_file(self, audio_path: str, output_format: str = 'json') -> Dict:
        """
        Обработка аудио файла с Whisper
        
        Args:
            audio_path: Путь к аудио файлу
            output_format: Формат вывода ('json', 'txt', 'srt')
            
        Returns:
            Словарь с результатами обработки
        """
        self.logger.info(f"Начинаю обработку аудио файла: {audio_path}")
        
        # Проверяем существование файла
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Аудио файл не найден: {audio_path}")
            
        # Получаем настройки Whisper
        model = self.config.get('WHISPER_MODEL', 'base')
        language = self.config.get('WHISPER_LANGUAGE', 'ru')
        task = self.config.get('WHISPER_TASK', 'transcribe')
        
        try:
            # Временно возвращаем заглушку для тестирования
            self.logger.info("⚠️ Pydub временно отключен, возвращаю заглушку")
            
            # Формируем заглушку результата
            result = {
                'file_path': audio_path,
                'file_size': os.path.getsize(audio_path),
                'duration': 0,  # Будет заполнено когда pydub заработает
                'segments_count': 1,
                'speakers_count': 1,
                'transcription': [{
                    'speaker_id': 'Участник 1',
                    'segments': [{
                        'text': '[Pydub временно отключен для тестирования]',
                        'start_time': 0,
                        'end_time': 0,
                        'duration': 0
                    }],
                    'total_duration': 0
                }],
                'processing_time': datetime.now().isoformat(),
                'whisper_model': model,
                'language': language
            }
            
            # Не сохраняем результат автоматически - это делает вызывающий код
            # self._save_result(result, output_format)
            
            self.logger.info("⚠️ Заглушка создана успешно")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке аудио: {e}")
            raise
            
    def _split_audio_by_silence(self, audio: Any) -> List[Dict]:
        """
        Разделение аудио на сегменты по тишине
        
        Args:
            audio: Аудио сегмент
            
        Returns:
            Список сегментов с метаданными
        """
        # Настройки для разделения
        min_silence_len = int(self.config.get('SPEAKER_MIN_DURATION', 1.0) * 1000)
        silence_thresh = int(self.config.get('SPEAKER_SILENCE_THRESHOLD', 0.5) * 1000)
        
        # Разделяем по тишине
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=True
        )
        
        # Формируем сегменты с метаданными
        segments = []
        current_time = 0
        
        for i, chunk in enumerate(chunks):
            duration = len(chunk)
            segment = {
                'segment_id': i + 1,
                'audio_data': chunk,
                'start_time': current_time,
                'end_time': current_time + duration,
                'duration': duration
            }
            segments.append(segment)
            current_time += duration
            
        return segments
        
    def _save_segment_temp(self, segment: Dict, index: int) -> str:
        """
        Сохранение сегмента во временный файл
        
        Args:
            segment: Сегмент аудио
            index: Индекс сегмента
            
        Returns:
            Путь к временному файлу
        """
        temp_dir = self.config.get('TEMP_AUDIO_ROOT', 'data/temp_audio')
        temp_file = os.path.join(temp_dir, f"segment_{index:03d}.mp3")
        
        # Сохраняем сегмент
        segment['audio_data'].export(temp_file, format='mp3')
        return temp_file
        
    def _transcribe_with_whisper(self, audio_file: str, model: str, language: str, task: str) -> Dict:
        """
        Транскрипция аудио с помощью Whisper API
        
        Args:
            audio_file: Путь к аудио файлу
            model: Модель Whisper
            language: Язык аудио
            task: Тип задачи (transcribe/translate)
            
        Returns:
            Результат транскрипции
        """
        try:
            with open(audio_file, 'rb') as f:
                response = openai.Audio.transcribe(
                    model=f"whisper-{model}",
                    file=f,
                    language=language,
                    task=task,
                    response_format="verbose_json"
                )
                
            return {
                'text': response.get('text', ''),
                'language': response.get('language', language),
                'segments': response.get('segments', []),
                'confidence': response.get('confidence', 0.0)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка Whisper API: {e}")
            return {
                'text': f"[Ошибка транскрипции: {e}]",
                'language': language,
                'segments': [],
                'confidence': 0.0
            }
            
    def _group_by_speakers(self, transcriptions: List[Dict]) -> List[Dict]:
        """
        Группировка транскрипций по участникам
        
        Args:
            transcriptions: Список транскрипций
            
        Returns:
            Список групп по участникам
        """
        # Простая эвристика: если между сегментами большая пауза - новый участник
        speaker_groups = []
        current_speaker = []
        current_speaker_id = 1
        
        for i, trans in enumerate(transcriptions):
            if i == 0:
                current_speaker.append(trans)
            else:
                # Проверяем паузу между сегментами
                pause_duration = trans['start_time'] - transcriptions[i-1]['end_time']
                
                # Если пауза больше порога - новый участник
                if pause_duration > 2000:  # 2 секунды
                    if current_speaker:
                        speaker_groups.append({
                            'speaker_id': f"Участник {current_speaker_id}",
                            'segments': current_speaker,
                            'total_duration': sum(s['duration'] for s in current_speaker)
                        })
                        current_speaker_id += 1
                        current_speaker = []
                        
                current_speaker.append(trans)
                
        # Добавляем последнего участника
        if current_speaker:
            speaker_groups.append({
                'speaker_id': f"Участник {current_speaker_id}",
                'segments': current_speaker,
                'total_duration': sum(s['duration'] for s in current_speaker)
            })
            
        return speaker_groups
        
    def _save_result(self, result: Dict, output_format: str):
        """
        Сохранение результата в файл
        
        Args:
            result: Результат обработки
            output_format: Формат вывода
        """
        output_dir = self.config.get('TRANSCRIPT_OUTPUT_ROOT', 'data/transcripts')
        base_name = os.path.splitext(os.path.basename(result['file_path']))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format == 'json':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        elif output_format == 'txt':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Транскрипция аудио файла: {result['file_path']}\n")
                f.write(f"Длительность: {result['duration']}ms\n")
                f.write(f"Количество сегментов: {result['segments_count']}\n")
                f.write(f"Количество участников: {result['speakers_count']}\n")
                f.write("=" * 50 + "\n\n")
                
                for speaker in result['transcription']:
                    f.write(f"{speaker['speaker_id']}:\n")
                    for segment in speaker['segments']:
                        f.write(f"[{segment['start_time']}-{segment['end_time']}ms] {segment['text']}\n")
                    f.write("\n")
                    
        elif output_format == 'srt':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.srt")
            with open(output_file, 'w', encoding='utf-8') as f:
                subtitle_id = 1
                for speaker in result['transcription']:
                    for segment in speaker['segments']:
                        start_time = self._ms_to_srt_time(segment['start_time'])
                        end_time = self._ms_to_srt_time(segment['end_time'])
                        
                        f.write(f"{subtitle_id}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{speaker['speaker_id']}: {segment['text']}\n\n")
                        subtitle_id += 1
                        
        self.logger.info(f"Результат сохранен: {output_file}")
        
    def _ms_to_srt_time(self, milliseconds: int) -> str:
        """Конвертация миллисекунд в формат SRT времени"""
        seconds = milliseconds // 1000
        ms = milliseconds % 1000
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"
        
    def cleanup_temp_files(self):
        """Очистка временных файлов"""
        temp_dir = self.config.get('TEMP_AUDIO_ROOT', 'data/temp_audio')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            self.logger.info("Временные файлы очищены")


def main():
    """Основная функция для запуска из командной строки"""
    parser = argparse.ArgumentParser(description='Обработчик аудио с Whisper')
    parser.add_argument('audio_file', help='Путь к аудио файлу')
    parser.add_argument('--config', help='Путь к конфигурационному файлу')
    parser.add_argument('--output', choices=['json', 'txt', 'srt'], default='json',
                       help='Формат вывода (по умолчанию: json)')
    parser.add_argument('--cleanup', action='store_true', help='Очистить временные файлы')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    
    args = parser.parse_args()
    
    try:
        # Создаем процессор
        processor = AudioProcessor(args.config)
        
        # Обрабатываем аудио
        result = processor.process_audio_file(args.audio_file, args.output)
        
        # Выводим результат
        if args.verbose:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"✅ Обработка завершена успешно!")
            print(f"📁 Файл: {result['file_path']}")
            print(f"⏱️  Длительность: {result['duration']}ms")
            print(f"🔊 Сегментов: {result['segments_count']}")
            print(f"👥 Участников: {result['speakers_count']}")
            
        # Очищаем временные файлы если нужно
        if args.cleanup:
            processor.cleanup_temp_files()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
