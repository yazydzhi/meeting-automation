#!/usr/bin/env python3
"""
Модуль для обработки медиа файлов (сжатие видео и извлечение аудио)
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


class MediaProcessor:
    """Обработчик медиа файлов."""
    
    def __init__(self, config_manager: ConfigManager, logger: Optional[logging.Logger] = None):
        """
        Инициализация обработчика медиа файлов.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер (опционально)
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        self._setup_ffmpeg_path()
    
    def _setup_ffmpeg_path(self):
        """Настройка PATH для ffmpeg."""
        try:
            # Устанавливаем правильный PATH для ffmpeg
            env = os.environ.copy()
            
            # Для macOS (homebrew)
            if os.path.exists('/opt/homebrew/bin/ffmpeg'):
                os.environ['PATH'] = f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"
                self.logger.info("✅ Добавлен путь к ffmpeg (homebrew)")
            # Для Linux
            elif os.path.exists('/usr/bin/ffmpeg'):
                os.environ['PATH'] = f"/usr/bin:{os.environ.get('PATH', '')}"
                self.logger.info("✅ Добавлен путь к ffmpeg (Linux)")
            else:
                self.logger.info("⚠️ Путь к ffmpeg не найден, используем системный PATH")
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка настройки PATH для ffmpeg: {e}")
    
    def process_media(self, quality: str = 'medium') -> Dict[str, Any]:
        """
        Обработка медиа файлов.
        
        Args:
            quality: Качество сжатия видео ('low', 'medium', 'high')
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            self.logger.info("🎬 Запуск обработки медиа файлов...")
            
            results = []
            total_processed = 0
            total_synced = 0
            
            # Обрабатываем личный аккаунт
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_media(personal_folder, "personal", quality)
                    results.append(personal_result)
                    total_processed += personal_result.get("processed", 0)
                    total_synced += personal_result.get("synced", 0)
                else:
                    self.logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_media(work_folder, "work", quality)
                    results.append(work_result)
                    total_processed += work_result.get("processed", 0)
                    total_synced += work_result.get("synced", 0)
                else:
                    self.logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
            
            self.logger.info(f"✅ Обработка медиа завершена: обработано {total_processed}, найдено {total_synced}")
            return {
                "status": "success", 
                "message": "Media processing completed", 
                "results": results,
                "total_processed": total_processed,
                "total_synced": total_synced
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки медиа: {e}")
            return {"status": "error", "message": str(e)}
    
    def _process_folder_media(self, folder_path: str, account_type: str, quality: str) -> Dict[str, Any]:
        """
        Обработка медиа файлов в конкретной папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            quality: Качество сжатия видео
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            result = {"status": "success", "folder": folder_path, "processed": 0, "synced": 0, "total_videos": 0, "processed_files": []}
            
            # Ищем видео файлы
            video_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        # Исключаем уже сжатые файлы
                        if 'compressed' not in file.lower():
                            video_files.append(os.path.join(root, file))
            
            if not video_files:
                self.logger.info(f"📁 В папке {folder_path} нет новых видео файлов для обработки")
                return result
            
            self.logger.info(f"🎥 Найдено {len(video_files)} новых видео файлов для обработки")
            result["total_videos"] = len(video_files)
            
            # Обрабатываем каждый видео файл
            for video_file in video_files:
                try:
                    self.logger.info(f"🎬 Обрабатываю видео: {os.path.basename(video_file)}")
                    
                    # Создаем имя для сжатого файла
                    base_name = os.path.splitext(video_file)[0]
                    compressed_video = f"{base_name}_compressed.mp4"
                    compressed_audio = f"{base_name}_compressed.mp3"
                    
                    # Сжимаем видео
                    video_success = self._compress_video(video_file, compressed_video, quality)
                    if video_success:
                        result["processed"] += 1
                        result["processed_files"].append({
                            "file": os.path.basename(video_file),
                            "type": "video",
                            "output": compressed_video,
                            "status": "success"
                        })
                        self.logger.info(f"✅ Видео сжато: {os.path.basename(compressed_video)}")
                    
                    # Извлекаем аудио
                    audio_success = self._extract_audio(video_file, compressed_audio)
                    if audio_success:
                        result["processed"] += 1
                        result["processed_files"].append({
                            "file": os.path.basename(video_file),
                            "type": "audio",
                            "output": compressed_audio,
                            "status": "success"
                        })
                        self.logger.info(f"✅ Аудио извлечено: {os.path.basename(compressed_audio)}")
                    
                    result["synced"] += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки {os.path.basename(video_file)}: {e}")
                    result["processed_files"].append({
                        "file": os.path.basename(video_file),
                        "type": "error",
                        "error": str(e),
                        "status": "error"
                    })
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"status": "error", "folder": folder_path, "processed": 0, "synced": 0, "total_videos": 0, "processed_files": [], "error": str(e)}
    
    def _compress_video(self, input_file: str, output_file: str, quality: str) -> bool:
        """
        Сжатие видео файла через FFmpeg.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            quality: Качество сжатия
            
        Returns:
            True, если сжатие прошло успешно
        """
        try:
            # Определяем параметры качества
            quality_params = {
                'low': ['-crf', '28', '-preset', 'fast'],
                'medium': ['-crf', '23', '-preset', 'medium'],
                'high': ['-crf', '18', '-preset', 'slow']
            }
            
            params = quality_params.get(quality, quality_params['medium'])
            
            cmd = [
                'ffmpeg', '-i', input_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '128k'
            ] + params + [
                '-y',  # Перезаписывать существующие файлы
                output_file
            ]
            
            self.logger.info(f"🎬 Запуск FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 минут
            
            if result.returncode == 0:
                self.logger.info(f"✅ Видео успешно сжато: {output_file}")
                return True
            else:
                self.logger.error(f"❌ Ошибка сжатия видео: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Таймаут сжатия видео: {input_file}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка сжатия видео {input_file}: {e}")
            return False
    
    def _extract_audio(self, input_file: str, output_file: str) -> bool:
        """
        Извлечение аудио из видео файла.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            
        Returns:
            True, если извлечение прошло успешно
        """
        try:
            cmd = [
                'ffmpeg', '-i', input_file,
                '-vn',  # Без видео
                '-c:a', 'mp3',
                '-b:a', '128k',
                '-ar', '44100',
                '-y',  # Перезаписывать существующие файлы
                output_file
            ]
            
            self.logger.info(f"🎵 Извлечение аудио: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 минут
            
            if result.returncode == 0:
                self.logger.info(f"✅ Аудио успешно извлечено: {output_file}")
                return True
            else:
                self.logger.error(f"❌ Ошибка извлечения аудио: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Таймаут извлечения аудио: {input_file}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения аудио {input_file}: {e}")
            return False


def get_media_processor(config_manager: ConfigManager, logger: Optional[logging.Logger] = None) -> MediaProcessor:
    """
    Получение обработчика медиа файлов.
    
    Args:
        config_manager: Менеджер конфигурации
        logger: Логгер (опционально)
        
    Returns:
        Обработчик медиа файлов
    """
    return MediaProcessor(config_manager, logger)
