#!/usr/bin/env python3
"""
Audio Processor with Whisper Integration
Обработчик аудио файлов с использованием OpenAI Whisper API
и разделением на участников разговора
"""

import os
import sys
import json
import tempfile
import subprocess
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import time # Добавляем для повторных попыток
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(str(Path(__file__).parent.parent))

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    import librosa
    import numpy as np
    from scipy.signal import find_peaks
    import noisereduce as nr
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите зависимости: pip install pydub librosa numpy scipy noisereduce")
    sys.exit(1)

from src.config_manager import ConfigManager

class AudioProcessor:
    """Обработчик аудио файлов с Whisper и улучшенными алгоритмами"""
    
    def __init__(self, config_file: str = None):
        """Инициализация AudioProcessor"""
        # Сначала загружаем конфигурацию
        self.config = self._load_config(config_file)
        
        # Затем настраиваем логирование
        self.logger = self._setup_logging()
        
        # Инициализируем транскриптор в зависимости от настроек
        self.transcription_method = self.config.get('TRANSCRIPTION_METHOD', 'openai')
        
        if self.transcription_method == 'openai':
            self.client = self._setup_openai()
        elif self.transcription_method == 'whisper':
            self.whisper_model = self._setup_openai_whisper()
        else:
            raise ValueError(f"Неизвестный метод транскрипции: {self.transcription_method}. Поддерживаемые: openai, whisper")
            
        # В конце создаем директории
        self._setup_directories()
        
    def _load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        try:
            if config_file and os.path.exists(config_file):
                # Загружаем из указанного файла
                config_manager = ConfigManager(config_file)
                return config_manager.config
            else:
                # Загружаем из переменных окружения
                config = {}
                
                # OpenAI настройки
                config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
                config['WHISPER_MODEL'] = os.getenv('WHISPER_MODEL', 'whisper-1')
                config['WHISPER_BEAM_SIZE'] = int(os.getenv('WHISPER_BEAM_SIZE', '5'))
                config['WHISPER_TEMPERATURE'] = float(os.getenv('WHISPER_TEMPERATURE', '0.0'))
                
                # Метод транскрипции
                config['TRANSCRIPTION_METHOD'] = os.getenv('TRANSCRIPTION_METHOD', 'openai')
                
                # Локальный Whisper настройки
                config['WHISPER_MODEL_LOCAL'] = os.getenv('WHISPER_MODEL_LOCAL', 'base')
                
                return config
                
        except Exception as e:
            # Возвращаем базовую конфигурацию
            return {
                'TRANSCRIPTION_METHOD': 'openai',
                'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),  # Добавляем API ключ
                'WHISPER_MODEL': 'whisper-1',
                'WHISPER_MODEL_LOCAL': 'base',
                'TEMP_AUDIO_ROOT': 'data/temp_audio',
                'TRANSCRIPT_OUTPUT_ROOT': 'data/transcripts',
                'AUDIO_PROCESSING_ROOT': 'data/audio_processing',
                'LOG_FILE': 'logs/audio_processing.log'
            }
            
    def _setup_faster_whisper(self):
        """Настройка faster-whisper модели"""
        try:
            from faster_whisper import WhisperModel
            
            model_size = self.config.get('FASTER_WHISPER_MODEL', 'base')
            device = self.config.get('FASTER_WHISPER_DEVICE', 'cpu')
            compute_type = self.config.get('FASTER_WHISPER_COMPUTE_TYPE', 'float32')
            
            self.logger.info(f"Загружаю faster-whisper модель: {model_size} на {device}")
            
            model = WhisperModel(
                model_size_or_path=model_size,
                device=device,
                compute_type=compute_type,
                download_root=None,  # Используем кэш по умолчанию
                local_files_only=False
            )
            
            self.logger.info(f"faster-whisper модель {model_size} загружена успешно")
            return model
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки faster-whisper: {e}")
            raise
            
    def _setup_logging(self):
        """Настройка логирования"""
        log_level = self.config.get('LOG_LEVEL', 'INFO')
        log_file = self.config.get('LOG_FILE', 'logs/audio_processing.log')
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        return logger
            
    def _setup_openai(self):
        """Настройка OpenAI API"""
        api_key = self.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY не найден в конфигурации")
            
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.logger.info("OpenAI API настроен успешно")
        except ImportError:
            raise ImportError("Установите openai: pip install openai")
            
    def _setup_openai_whisper(self):
        """Настройка оригинального OpenAI Whisper"""
        try:
            import whisper
            
            model_size = self.config.get('WHISPER_MODEL_LOCAL', 'base')
            self.logger.info(f"Загружаю OpenAI Whisper модель: {model_size}")
            
            model = whisper.load_model(model_size)
            
            self.logger.info(f"OpenAI Whisper модель {model_size} загружена успешно")
            return model
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки OpenAI Whisper: {e}")
            raise
            
    def _setup_directories(self):
        """Создание необходимых директорий"""
        dirs = [
            self.config.get('TEMP_AUDIO_ROOT', 'data/temp_audio'),
            self.config.get('TRANSCRIPT_OUTPUT_ROOT', 'data/transcripts'),
            self.config.get('AUDIO_PROCESSING_ROOT', 'data/audio_processing')
        ]
        
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
            
    def process_audio_file(self, audio_file_path: str, output_format: str = 'json') -> Dict[str, Any]:
        """Основной метод обработки аудио файла"""
        self.logger.info(f"Начинаю обработку файла: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Аудио файл не найден: {audio_file_path}")
            
        # Шаг 1: Подготовка аудио (конвертация, нормализация, устранение эха)
        prepared_audio_path = self._prepare_audio(audio_file_path)
        
        # Шаг 2: Разделение на сегменты по характеристикам голоса
        segments = self._split_audio_by_voice_characteristics(prepared_audio_path)
        self.logger.info(f"Аудио разделено на {len(segments)} сегментов")
        
        # Шаг 3: Транскрипция каждого сегмента
        transcriptions = []
        for i, segment in enumerate(segments):
            self.logger.info(f"Транскрибирую сегмент {i+1}/{len(segments)}")
            transcript = self._transcribe_with_whisper(segment, prepared_audio_path)
            if transcript:
                transcriptions.append({
                    'segment': i + 1,
                    'start_time': segment['start_time'],
                    'end_time': segment['end_time'],
                    'text': transcript,
                    'duration': segment['duration']
                })
                
        # Шаг 4: Группировка по спикерам с улучшенной логикой
        speaker_groups = self._group_by_speakers_improved(transcriptions)
        
        # Шаг 5: Формирование результата
        result = {
            'file_path': audio_file_path,
            'file_size': os.path.getsize(audio_file_path),
            'processed_at': datetime.now().isoformat(),
            'total_segments': len(segments),
            'total_duration': sum(seg['duration'] for seg in segments),
            'speakers': speaker_groups,
            'raw_transcriptions': transcriptions,
            'processing_info': {
                'echo_removed': self.config.get('REMOVE_ECHO', True),
                'audio_normalized': self.config.get('AUDIO_NORMALIZE', True),
                'voice_analysis_method': self.config.get('VOICE_ANALYSIS_METHOD', 'mfcc'),
                'whisper_model': self.config.get('WHISPER_MODEL', 'whisper-1'),
                'original_audio_file': audio_file_path,
                'prepared_audio_file': prepared_audio_path
            }
        }
        
        self.logger.info(f"Обработка завершена. Результат: {len(speaker_groups)} спикеров")
        self.logger.info(f"Структура результата: {list(result.keys())}")
        self.logger.info(f"Количество транскрипций: {len(transcriptions)}")
        self.logger.info(f"Размер файла: {result['file_size']} байт")
        self.logger.info(f"Общая длительность: {result['total_duration']} мс")
        
        # Очищаем временные файлы
        # self.cleanup_temp_files()  # Временно отключено для диагностики
        
        return result
        
    def process_audio_file_full(self, audio_file_path: str, output_format: str = 'json') -> Dict[str, Any]:
        """Транскрипция полного аудио файла без сегментации"""
        self.logger.info(f"Начинаю транскрипцию полного файла: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Аудио файл не найден: {audio_file_path}")
            
        # Шаг 1: Подготовка аудио (конвертация, нормализация, устранение эха)
        prepared_audio_path = self._prepare_audio(audio_file_path)
        
        # Шаг 2: Транскрипция полного файла
        self.logger.info("Транскрибирую полный аудио файл...")
        full_transcript = self._transcribe_full_audio(prepared_audio_path)
        
        if not full_transcript:
            raise Exception("Не удалось получить транскрипцию полного файла")
            
        # Шаг 3: Формирование результата
        result = {
            'file_path': audio_file_path,
            'file_size': os.path.getsize(audio_file_path),
            'processed_at': datetime.now().isoformat(),
            'total_segments': 1,
            'total_duration': self._get_audio_duration(prepared_audio_path),
            'speakers': {
                'Участник 1': [{
                    'segment': 1,
                    'start_time': 0,
                    'end_time': self._get_audio_duration(prepared_audio_path),
                    'text': full_transcript,
                    'duration': self._get_audio_duration(prepared_audio_path)
                }]
            },
            'raw_transcriptions': [{
                'segment': 1,
                'start_time': 0,
                'end_time': self._get_audio_duration(prepared_audio_path),
                'text': full_transcript,
                'duration': self._get_audio_duration(prepared_audio_path)
            }],
            'processing_info': {
                'echo_removed': self.config.get('REMOVE_ECHO', True),
                'audio_normalized': self.config.get('AUDIO_NORMALIZE', True),
                'transcription_method': 'full_file',
                'whisper_model': self.config.get('WHISPER_MODEL', 'whisper-1'),
                'original_audio_file': audio_file_path,
                'prepared_audio_file': prepared_audio_path
            }
        }
        
        self.logger.info(f"Транскрипция завершена. Размер файла: {result['file_size']} байт")
        self.logger.info(f"Длительность аудио: {result['total_duration']} мс")
        self.logger.info(f"Длина транскрипта: {len(full_transcript)} символов")
        
        return result
        
    def _prepare_audio(self, audio_file_path: str) -> str:
        """Подготовка аудио: конвертация, нормализация, устранение эха, сжатие для API"""
        try:
            # Создаем временный файл для подготовленного аудио
            temp_dir = self.config.get('TEMP_AUDIO_ROOT', 'data/temp_audio')
            os.makedirs(temp_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            prepared_audio_path = os.path.join(temp_dir, f"{base_name}_prepared.wav")
            
            # Определяем формат входного файла
            file_ext = os.path.splitext(audio_file_path)[1].lower()
            
            # Команда FFmpeg для подготовки аудио с сжатием
            ffmpeg_cmd = [
                'ffmpeg', '-i', audio_file_path,
                '-vn',  # убираем видео
                '-ac', '1',  # моно
                '-ar', '16000',  # 16 кГц
                '-b:a', '64k',  # битрейт 64 кбит/с для уменьшения размера
            ]
            
            # Добавляем фильтры в зависимости от настроек
            filters = []
            
            # Нормализация громкости
            if self.config.get('AUDIO_NORMALIZE', True):
                filters.append('loudnorm=I=-16:TP=-1.5:LRA=11')
            
            # Устранение эха
            if self.config.get('REMOVE_ECHO', True):
                echo_method = self.config.get('ECHO_REMOVAL_METHOD', 'ffmpeg')
                if echo_method == 'ffmpeg':
                    filters.extend([
                        'highpass=f=200',  # убираем низкие частоты
                        'lowpass=f=8000',   # убираем высокие частоты
                        'anlmdn',           # нелинейное шумоподавление
                        'anlms'             # адаптивное шумоподавление
                    ])
                elif echo_method == 'aggressive':
                    filters.extend([
                        'highpass=f=150',
                        'lowpass=f=4000',
                        'anlmdn',
                        'anlms',
                        'compand=0.2|0.2:1|1:-90/-60/-40/-20/-10/0:8:0:-90:0.1'
                    ])
            
            # Применяем фильтры
            if filters:
                ffmpeg_cmd.extend(['-af', ','.join(filters)])
            
            # Выходной файл
            ffmpeg_cmd.extend(['-y', prepared_audio_path])
            
            # Выполняем команду
            self.logger.info(f"Подготавливаю аудио: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg ошибка: {result.stderr}")
                # Пробуем упрощенную команду без сложных фильтров, но с сжатием
                simple_cmd = [
                    'ffmpeg', '-i', audio_file_path,
                    '-vn', '-ac', '1', '-ar', '16000', '-b:a', '64k',
                    '-y', prepared_audio_path
                ]
                self.logger.info(f"Пробую упрощенную команду: {' '.join(simple_cmd)}")
                result = subprocess.run(simple_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.logger.error(f"Упрощенная команда тоже не сработала: {result.stderr}")
                    return audio_file_path
            else:
                self.logger.warning(f"FFmpeg предупреждение: {result.stderr}")
            
            # Проверяем размер файла
            file_size = os.path.getsize(prepared_audio_path)
            self.logger.info(f"Размер подготовленного файла: {file_size / (1024*1024):.2f} MB")
            
            # Если файл все еще слишком большой, дополнительно сжимаем
            if file_size > 20 * 1024 * 1024:  # Больше 20 MB
                self.logger.info("Файл слишком большой, дополнительно сжимаю...")
                compressed_path = prepared_audio_path.replace('.wav', '_compressed.wav')
                compress_cmd = [
                    'ffmpeg', '-i', prepared_audio_path,
                    '-vn', '-ac', '1', '-ar', '8000', '-b:a', '32k',  # Еще больше сжимаем
                    '-y', compressed_path
                ]
                result = subprocess.run(compress_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    prepared_audio_path = compressed_path
                    file_size = os.path.getsize(prepared_audio_path)
                    self.logger.info(f"Размер после сжатия: {file_size / (1024*1024):.2f} MB")
            
            self.logger.info(f"Аудио подготовлено: {prepared_audio_path}")
            return prepared_audio_path
            
        except Exception as e:
            self.logger.error(f"Ошибка подготовки аудио: {e}")
            return audio_file_path
            
    def _remove_echo_python(self, audio_path: str):
        """Дополнительное устранение эха через Python"""
        try:
            # Загружаем аудио
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Применяем шумоподавление
            y_clean = nr.reduce_noise(
                y=y, sr=sr,
                stationary=False,
                prop_decrease=self.config.get('NOISE_REDUCE_PROP_DECREASE', 0.9),
                n_std_thresh_stationary=self.config.get('NOISE_REDUCE_STD_THRESH', 2.0)
            )
            
            # Сохраняем обратно
            librosa.output.write_wav(audio_path, y_clean, sr)
            
        except Exception as e:
            self.logger.warning(f"Не удалось применить Python шумоподавление: {e}")
            
    def _split_audio_by_voice_characteristics(self, audio_file_path: str) -> List[Dict[str, Any]]:
        """Разделение аудио по характеристикам голоса (тон, тембр, MFCC)"""
        try:
            # Загружаем аудио
            y, sr = librosa.load(audio_file_path, sr=16000)
            
            # Определяем метод анализа
            method = self.config.get('VOICE_ANALYSIS_METHOD', 'mfcc')
            
            if method == 'mfcc':
                change_points = self._detect_speaker_changes_mfcc(y, sr)
            elif method == 'spectral':
                change_points = self._detect_speaker_changes_spectral(y, sr)
            elif method == 'combined':
                change_points = self._detect_speaker_changes_combined(y, sr)
            else:
                # Fallback на старый метод
                return self._split_audio_by_silence_fallback(audio_file_path)
            
            # Создаем сегменты
            segments = self._create_segments_from_changes(y, sr, change_points)
            
            # Если сегменты слишком короткие, группируем их
            min_duration = self.config.get('MIN_SEGMENT_DURATION', 5000)  # 5 секунд
            segments = self._merge_short_segments(segments, min_duration)
            
            # Сохраняем отдельные сегменты для анализа
            self._save_segments_for_analysis(segments, audio_file_path)
            
            self.logger.info(f"Создано {len(segments)} сегментов по анализу голоса")
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка при анализе голоса: {e}")
            return self._split_audio_by_silence_fallback(audio_file_path)
            
    def _save_segments_for_analysis(self, segments: List[Dict[str, Any]], original_audio_path: str):
        """Сохраняет отдельные сегменты для анализа"""
        try:
            # Создаем папку для сегментов
            base_name = os.path.splitext(os.path.basename(original_audio_path))[0]
            segments_dir = os.path.join(
                self.config.get('AUDIO_PROCESSING_ROOT', 'data/audio_processing'),
                f"{base_name}_segments"
            )
            os.makedirs(segments_dir, exist_ok=True)
            
            # Сохраняем каждый сегмент
            for i, segment in enumerate(segments):
                segment_filename = f"segment_{i+1:03d}_{segment['start_time']:06d}ms_{segment['end_time']:06d}ms.wav"
                segment_path = os.path.join(segments_dir, segment_filename)
                
                # Сохраняем аудио сегмента
                import soundfile as sf
                sf.write(segment_path, segment['audio'], 16000)
                
                # Создаем метаданные сегмента
                metadata = {
                    'segment_number': i + 1,
                    'start_time_ms': segment['start_time'],
                    'end_time_ms': segment['end_time'],
                    'duration_ms': segment['duration'],
                    'start_time_s': segment['start_time'] / 1000,
                    'end_time_s': segment['end_time'] / 1000,
                    'duration_s': segment['duration'] / 1000,
                    'audio_file': segment_filename
                }
                
                # Сохраняем метаданные
                metadata_path = segment_path.replace('.wav', '.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Создаем общий файл с информацией о сегментах
            segments_info = {
                'original_file': original_audio_path,
                'total_segments': len(segments),
                'total_duration_ms': sum(seg['duration'] for seg in segments),
                'total_duration_s': sum(seg['duration'] for seg in segments) / 1000,
                'segments': []
            }
            
            for i, segment in enumerate(segments):
                segments_info['segments'].append({
                    'segment_number': i + 1,
                    'start_time_ms': segment['start_time'],
                    'end_time_ms': segment['end_time'],
                    'duration_ms': segment['duration'],
                    'start_time_s': segment['start_time'] / 1000,
                    'end_time_s': segment['end_time'] / 1000,
                    'duration_s': segment['duration'] / 1000,
                    'audio_file': f"segment_{i+1:03d}_{segment['start_time']:06d}ms_{segment['end_time']:06d}ms.wav",
                    'metadata_file': f"segment_{i+1:03d}_{segment['start_time']:06d}ms_{segment['end_time']:06d}ms.json"
                })
            
            # Сохраняем общую информацию
            info_path = os.path.join(segments_dir, 'segments_info.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(segments_info, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Сегменты сохранены для анализа в: {segments_dir}")
            
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить сегменты для анализа: {e}")
            
    def _detect_speaker_changes_mfcc(self, y: np.ndarray, sr: int) -> List[int]:
        """Определение смены говорящего по MFCC с улучшенными параметрами"""
        try:
            # Улучшенные параметры MFCC
            hop_length = int(self.config.get('MFCC_HOP_SIZE', 5) * sr / 1000)  # 5мс для более точного анализа
            n_fft = int(self.config.get('MFCC_WINDOW_SIZE', 20) * sr / 1000)   # 20мс окно
            
            # Извлекаем MFCC с большим количеством коэффициентов
            mfcc = librosa.feature.mfcc(
                y=y, sr=sr, n_mfcc=20,  # Увеличиваем количество коэффициентов
                hop_length=hop_length, n_fft=n_fft
            )
            
            # Нормализуем MFCC
            mfcc_normalized = (mfcc - np.mean(mfcc, axis=1, keepdims=True)) / (np.std(mfcc, axis=1, keepdims=True) + 1e-8)
            
            # Вычисляем расстояние между соседними фреймами
            distances = []
            for i in range(1, mfcc_normalized.shape[1]):
                dist = np.linalg.norm(mfcc_normalized[:, i] - mfcc_normalized[:, i-1])
                distances.append(dist)
            
            # Адаптивный порог для определения изменений
            threshold = np.mean(distances) + self.config.get('VOICE_CHANGE_THRESHOLD', 1.2) * np.std(distances)
            
            # Минимальное расстояние между изменениями (2 секунды)
            min_distance = int(2.0 * sr / hop_length)
            
            # Находим пики изменения
            change_points = find_peaks(
                distances, 
                height=threshold, 
                distance=min_distance,
                prominence=np.std(distances) * 0.5  # Добавляем проверку на значимость пика
            )[0]
            
            # Конвертируем в временные метки
            change_times = [int(point * hop_length / sr * 1000) for point in change_points]
            
            # Добавляем начало и конец, если их нет
            if not change_times or change_times[0] > 5000:  # Если первое изменение после 5 секунд
                change_times.insert(0, 0)
            
            total_duration = len(y) / sr * 1000
            if not change_times or change_times[-1] < total_duration - 5000:  # Если последнее изменение за 5 секунд до конца
                change_times.append(int(total_duration))
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка MFCC анализа: {e}")
            return []
            
    def _detect_speaker_changes_spectral(self, y: np.ndarray, sr: int) -> List[int]:
        """Определение смены говорящего по спектральным характеристикам с улучшениями"""
        try:
            # Улучшенные параметры
            hop_length = int(5 * sr / 1000)  # 5мс для более точного анализа
            
            # Извлекаем больше спектральных признаков
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop_length)[0]
            
            # Комбинируем признаки
            features = np.vstack([
                spectral_centroid, spectral_rolloff, spectral_bandwidth,
                np.mean(spectral_contrast, axis=0)  # Среднее по контрасту
            ])
            
            # Нормализуем признаки
            features_normalized = (features - np.mean(features, axis=1, keepdims=True)) / (np.std(features, axis=1, keepdims=True) + 1e-8)
            
            # Вычисляем изменения с весами для разных признаков
            weights = [1.0, 0.8, 0.6, 0.4]  # Веса для разных признаков
            changes = np.zeros(features_normalized.shape[1] - 1)
            
            for i in range(features_normalized.shape[1] - 1):
                for j, weight in enumerate(weights):
                    changes[i] += weight * (features_normalized[j, i+1] - features_normalized[j, i]) ** 2
            
            # Адаптивный порог
            threshold = np.mean(changes) + self.config.get('VOICE_CHANGE_THRESHOLD', 1.2) * np.std(changes)
            min_distance = int(2.0 * sr / hop_length)  # 2 секунды
            
            # Находим пики
            change_points = find_peaks(
                changes, 
                height=threshold, 
                distance=min_distance,
                prominence=np.std(changes) * 0.5
            )[0]
            
            # Конвертируем в миллисекунды
            change_times = [int(point * hop_length / sr * 1000) for point in change_points]
            
            # Добавляем начало и конец
            if not change_times or change_times[0] > 5000:
                change_times.insert(0, 0)
            
            total_duration = len(y) / sr * 1000
            if not change_times or change_times[-1] < total_duration - 5000:
                change_times.append(int(total_duration))
            
            return change_times
            
        except Exception as e:
            self.logger.error(f"Ошибка спектрального анализа: {e}")
            return []
            
    def _detect_speaker_changes_combined(self, y: np.ndarray, sr: int) -> List[int]:
        """Комбинированный метод определения смены говорящего"""
        try:
            # Получаем результаты от разных методов
            mfcc_changes = self._detect_speaker_changes_mfcc(y, sr)
            spectral_changes = self._detect_speaker_changes_spectral(y, sr)
            
            # Объединяем и убираем дубликаты
            all_changes = mfcc_changes + spectral_changes
            all_changes.sort()
            
            # Убираем близкие изменения (в пределах 500мс)
            filtered_changes = []
            for change in all_changes:
                if not filtered_changes or change - filtered_changes[-1] > 500:
                    filtered_changes.append(change)
            
            return filtered_changes
            
        except Exception as e:
            self.logger.error(f"Ошибка комбинированного анализа: {e}")
            return []
            
    def _create_segments_from_changes(self, y: np.ndarray, sr: int, change_points: List[int]) -> List[Dict[str, Any]]:
        """Создание сегментов из точек изменения с улучшенной логикой"""
        segments = []
        
        # Сортируем точки изменения
        change_points = sorted(change_points)
        
        # Создаем сегменты между точками изменения
        for i in range(len(change_points)):
            start_time = change_points[i]
            
            if i + 1 < len(change_points):
                end_time = change_points[i + 1]
            else:
                end_time = int(len(y) / sr * 1000)
            
            duration = end_time - start_time
            
            # Проверяем минимальную длительность сегмента
            min_duration = self.config.get('MIN_SEGMENT_DURATION', 5000)  # 5 секунд
            
            if duration >= min_duration:
                # Извлекаем аудио для сегмента
                start_sample = int(start_time / 1000 * sr)
                end_sample = int(end_time / 1000 * sr)
                
                if start_sample < len(y) and end_sample <= len(y):
                    segment_audio = y[start_sample:end_sample]
                    
                    segments.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'audio': segment_audio,
                        'start_sample': start_sample,
                        'end_sample': end_sample
                    })
                else:
                    self.logger.warning(f"Некорректные границы сегмента: {start_sample}-{end_sample}, длина аудио: {len(y)}")
            else:
                self.logger.info(f"Сегмент слишком короткий: {duration}мс, пропускаю")
        
        return segments
        
    def _merge_short_segments(self, segments: List[Dict[str, Any]], min_duration: int) -> List[Dict[str, Any]]:
        """Объединение коротких сегментов с улучшенной логикой"""
        if not segments:
            return segments
            
        merged = []
        current_segment = segments[0].copy()
        
        for segment in segments[1:]:
            # Если текущий сегмент слишком короткий, объединяем
            if current_segment['duration'] < min_duration:
                # Объединяем с текущим сегментом
                current_segment['end_time'] = segment['end_time']
                current_segment['duration'] = segment['end_time'] - current_segment['start_time']
                
                # Объединяем аудио
                if 'audio' in current_segment and 'audio' in segment:
                    current_segment['audio'] = np.concatenate([current_segment['audio'], segment['audio']])
                
                # Обновляем границы сэмплов
                if 'end_sample' in segment:
                    current_segment['end_sample'] = segment['end_sample']
                
                self.logger.info(f"Объединил короткий сегмент: {current_segment['start_time']}мс - {current_segment['end_time']}мс")
            else:
                # Добавляем текущий сегмент и начинаем новый
                merged.append(current_segment)
                current_segment = segment.copy()
        
        # Добавляем последний сегмент
        merged.append(current_segment)
        
        self.logger.info(f"После объединения: {len(merged)} сегментов")
        return merged
        
    def _split_audio_by_silence_fallback(self, audio_file_path: str) -> List[Dict[str, Any]]:
        """Fallback: разделение по тишине (старый метод)"""
        try:
            # Загружаем аудио файл
            audio = AudioSegment.from_file(audio_file_path)
            
            # Параметры для разделения по тишине
            min_silence_len = self.config.get('SPEAKER_MIN_DURATION', 3000)  # 3 секунды
            silence_thresh = self.config.get('SPEAKER_SILENCE_THRESHOLD', -35)  # -35 dB
            
            # Убеждаемся, что параметры имеют правильный тип
            try:
                if isinstance(min_silence_len, str):
                    min_silence_len = float(min_silence_len) * 1000
                min_silence_len = int(min_silence_len)
                
                if isinstance(silence_thresh, str):
                    silence_thresh = float(silence_thresh)
                silence_thresh = int(silence_thresh)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Ошибка конвертации параметров, используем значения по умолчанию: {e}")
                min_silence_len = 3000  # 3 секунды
                silence_thresh = -35     # -35 dB
            
            # Разделяем по тишине
            chunks = split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=200  # оставляем немного тишины
            )
            
            # Если сегменты не найдены, используем fallback по времени
            if not chunks:
                self.logger.info("Сегменты по тишине не найдены, используем fallback - разделение по времени")
                segment_duration = self.config.get('FALLBACK_SEGMENT_DURATION', 30000)  # 30 секунд
                chunks = []
                for i in range(0, len(audio), segment_duration):
                    chunk = audio[i:i + segment_duration]
                    if len(chunk) > 0:
                        chunks.append(chunk)
            
            # Создаем информацию о сегментах
            segments = []
            current_time = 0
            
            for i, chunk in enumerate(chunks):
                duration = len(chunk)
                segment_info = {
                    'start_time': current_time,
                    'end_time': current_time + duration,
                    'duration': duration,
                    'audio': chunk
                }
                segments.append(segment_info)
                current_time += duration
                
            return segments
            
        except Exception as e:
            self.logger.error(f"Ошибка при разделении аудио: {e}")
            # Возвращаем один сегмент с полным файлом
            audio = AudioSegment.from_file(audio_file_path)
            return [{
                'start_time': 0,
                'end_time': len(audio),
                'duration': len(audio),
                'audio': audio
            }]

    def _save_segment_temp(self, segment: Dict[str, Any], segment_index: int) -> str:
        """Сохранение сегмента во временный файл"""
        temp_dir = self.config.get('TEMP_AUDIO_ROOT', 'temp/audio')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = os.path.join(temp_dir, f"segment_{segment_index}.wav")
        
        # Если у нас есть numpy массив, конвертируем его
        if 'audio' in segment and isinstance(segment['audio'], np.ndarray):
            # Сохраняем numpy массив как WAV
            import soundfile as sf
            sf.write(temp_file, segment['audio'], 16000)
        else:
            # Fallback на pydub
            segment['audio'].export(temp_file, format="wav")
            
        return temp_file
        
    def _transcribe_with_whisper(self, segment: Dict[str, Any], prepared_audio_path: str) -> Optional[str]:
        """Транскрипция сегмента через OpenAI Whisper API"""
        try:
            # Получаем параметры конфигурации
            model = self.config.get('WHISPER_MODEL', 'whisper-1')
            language = self.config.get('WHISPER_LANGUAGE', 'ru')
            
            # Создаем временный файл для сегмента
            temp_file = self._save_segment_temp(segment, segment['start_time'])
            
            with open(temp_file, "rb") as audio_file:
                # Создаем параметры для API
                params = {
                    'model': model,
                    'file': audio_file,
                    'response_format': 'verbose_json'
                }
                
                # Добавляем язык только если он не None
                if language and language != 'auto':
                    params['language'] = language
                
                # OpenAI API не поддерживает beam_size и temperature для transcriptions
                # Эти параметры доступны только для chat completions
                
                response = self.client.audio.transcriptions.create(**params)
                
            # Удаляем временный файл
            os.remove(temp_file)
            
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Ошибка транскрипции сегмента: {e}")
            return None
            
    def _transcribe_full_audio(self, audio_file_path: str) -> Optional[str]:
        """Транскрипция полного аудио файла с повторными попытками"""
        if self.transcription_method == 'whisper':
            return self._transcribe_with_openai_whisper_local(audio_file_path)
        else:
            return self._transcribe_with_openai_api(audio_file_path)
            
    def _transcribe_with_openai_api(self, audio_file_path: str) -> Optional[str]:
        """Транскрипция через OpenAI API с повторными попытками"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Попытка OpenAI транскрипции {attempt + 1}/{max_retries}")
                
                # Открываем файл для отправки в Whisper
                with open(audio_file_path, 'rb') as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model=self.config.get('WHISPER_MODEL', 'whisper-1'),
                        file=audio_file,
                        response_format='verbose_json',
                        language='ru'  # Указываем русский язык для лучшего качества
                    )
                    
                    # Извлекаем текст из ответа
                    if hasattr(response, 'text'):
                        self.logger.info("OpenAI транскрипция успешно завершена")
                        return response.text
                    elif hasattr(response, 'content'):
                        self.logger.info("OpenAI транскрипция успешно завершена")
                        return response.content
                    else:
                        self.logger.error(f"Неожиданный формат ответа OpenAI: {type(response)}")
                        return None
                        
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"Попытка {attempt + 1} не удалась: {error_msg}")
                
                if attempt < max_retries - 1:
                    self.logger.info(f"Ожидаю {retry_delay} секунд перед повторной попыткой...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку
                else:
                    self.logger.error(f"Все попытки OpenAI транскрипции исчерпаны: {error_msg}")
                    return None
        
        return None
            
    def _transcribe_with_openai_whisper_local(self, audio_file_path: str) -> Optional[str]:
        """Транскрипция через локальный OpenAI Whisper"""
        try:
            self.logger.info("Транскрибирую через OpenAI Whisper (локально)...")
            
            # Транскрибируем аудио
            result = self.whisper_model.transcribe(
                audio_file_path,
                language='ru',
                task='transcribe'
            )
            
            # Извлекаем текст
            full_text = result['text'].strip()
            
            self.logger.info(f"OpenAI Whisper (локально) транскрипция завершена. Длина: {len(full_text)} символов")
            return full_text
            
        except Exception as e:
            self.logger.error(f"Ошибка OpenAI Whisper (локально) транскрипции: {e}")
            return None
            
    def _get_audio_duration(self, audio_file_path: str) -> int:
        """Получение длительности аудио файла в миллисекундах"""
        try:
            # Используем librosa для получения длительности
            y, sr = librosa.load(audio_file_path, sr=None)
            duration_ms = int(len(y) / sr * 1000)
            return duration_ms
        except Exception as e:
            self.logger.warning(f"Не удалось определить длительность: {e}")
            return 0
            
    def _group_by_speakers_improved(self, transcriptions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Улучшенная группировка транскрипций по спикерам"""
        if not transcriptions:
            self.logger.warning("Нет транскрипций для группировки")
            return {}
            
        # Улучшенная эвристика: группируем по времени и паузам
        speakers = {}
        current_speaker = 0
        max_speakers = self.config.get('MAX_SPEAKERS', 10)
        
        for i, trans in enumerate(transcriptions):
            # Если это первый сегмент или прошло много времени, начинаем нового спикера
            pause_threshold = self.config.get('SPEAKER_PAUSE_THRESHOLD', 5000)  # 5 секунд
            
            if i == 0 or (i > 0 and trans['start_time'] - transcriptions[i-1]['end_time'] > pause_threshold):
                current_speaker = (current_speaker + 1) % max_speakers
            
            speaker_name = f"Участник {current_speaker + 1}"
            if speaker_name not in speakers:
                speakers[speaker_name] = []
                
            speakers[speaker_name].append({
                'text': trans['text'],
                'start_time': trans['start_time'],
                'end_time': trans['end_time'],
                'duration': trans['duration']
            })
            
        self.logger.info(f"Сгруппировано в {len(speakers)} спикеров")
        return speakers
        
    def _save_result(self, result: Dict[str, Any], output_format: str = 'json'):
        """Сохранение результата в файл"""
        output_dir = self.config.get('TRANSCRIPT_OUTPUT_ROOT', 'data/transcripts')
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(result['file_path']))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == 'json':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        elif output_format == 'txt':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Транскрипция: {result['file_path']}\n")
                f.write(f"Обработано: {result['processed_at']}\n")
                f.write(f"Всего сегментов: {result['total_segments']}\n")
                f.write(f"Общая длительность: {result['total_duration']} мс\n\n")
                
                for speaker, segments in result['speakers'].items():
                    f.write(f"=== {speaker} ===\n")
                    for seg in segments:
                        f.write(f"[{self._ms_to_srt_time(seg['start_time'])} - {self._ms_to_srt_time(seg['end_time'])}]\n")
                        f.write(f"{seg['text']}\n\n")
                        
        elif output_format == 'srt':
            output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.srt")
            with open(output_file, 'w', encoding='utf-8') as f:
                subtitle_index = 1
                for speaker, segments in result['speakers'].items():
                    for seg in segments:
                        f.write(f"{subtitle_index}\n")
                        f.write(f"{self._ms_to_srt_time(seg['start_time'])} --> {self._ms_to_srt_time(seg['end_time'])}\n")
                        f.write(f"{speaker}: {seg['text']}\n\n")
                        subtitle_index += 1
                        
        self.logger.info(f"Результат сохранен в: {output_file}")
        
    def _ms_to_srt_time(self, ms: int) -> str:
        """Конвертация миллисекунд в формат времени SRT"""
        seconds = ms // 1000
        milliseconds = ms % 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
    def cleanup_temp_files(self):
        """Очистка временных файлов"""
        temp_dir = self.config.get('TEMP_AUDIO_ROOT', 'temp/audio')
        if os.path.exists(temp_dir):
            try:
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                self.logger.info("Временные файлы очищены")
            except Exception as e:
                self.logger.warning(f"Не удалось очистить временные файлы: {e}")

def main():
    """Основная функция для командной строки"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Обработчик аудио файлов с Whisper')
    parser.add_argument('audio_file', help='Путь к аудио файлу')
    parser.add_argument('--format', choices=['json', 'txt', 'srt'], default='json',
                       help='Формат выходного файла')
    parser.add_argument('--config', help='Путь к файлу конфигурации')
    
    args = parser.parse_args()
    
    try:
        processor = AudioProcessor(args.config)
        result = processor.process_audio_file(args.audio_file, args.format)
        processor._save_result(result, args.format)
        print(f"✅ Обработка завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
