"""
Модуль для обработки медиа файлов в папках Google Drive.
Включает конвертацию видео в аудио и управление статусом обработки.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import subprocess
import shutil

# Поддерживаемые видео форматы
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.webm', '.avi', '.mov', '.wmv', '.flv', '.m4v',
    '.3gp', '.ogv', '.ts', '.mts', '.m2ts', '.vob', '.asf', '.rm'
}

# Поддерживаемые аудио форматы для вывода
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}

# Статус файл для отслеживания обработки
STATUS_EXTENSION = '.processed_media'


class MediaProcessor:
    """Класс для обработки медиа файлов в папках Google Drive."""
    
    def __init__(self, drive_service, output_format: str = 'mp3', 
                 video_compression: bool = True, video_quality: str = 'medium', 
                 video_codec: str = 'h264'):
        """
        Инициализация процессора медиа.
        
        Args:
            drive_service: Сервис Google Drive API
            output_format: Формат выходного аудио файла (без точки)
            video_compression: Включить ли компрессию видео
            video_quality: Качество компрессии видео (low, medium, high, ultra)
            video_codec: Кодек для компрессии видео (h264, h265, vp9)
        """
        self.drive_service = drive_service
        self.output_format = output_format
        self.video_compression = video_compression
        self.video_quality = video_quality
        self.video_codec = video_codec
        self.processed_files = set()
        self.errors = []
        
        # Проверяем наличие ffmpeg
        if not self._check_ffmpeg():
            # Вместо ошибки, просто логируем предупреждение
            print("⚠️ ffmpeg не найден. Медиа обработка будет пропущена.")
            self.ffmpeg_available = False
        else:
            self.ffmpeg_available = True
    
    def _check_ffmpeg(self) -> bool:
        """Проверяет наличие ffmpeg в системе."""
        try:
            # Сначала проверяем в текущем PATH
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Пытаемся найти ffmpeg в стандартных местах
        ffmpeg_paths = [
            "/opt/homebrew/bin/ffmpeg",  # macOS Homebrew
            "/usr/local/bin/ffmpeg",     # macOS/Linux
            "/usr/bin/ffmpeg",           # Linux
            "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
        ]
        
        for path in ffmpeg_paths:
            if os.path.exists(path):
                try:
                    result = subprocess.run([path, '-version'], 
                                          capture_output=True, check=True, timeout=5)
                    return True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue
        
        return False
    
    def _get_file_hash(self, file_path: str) -> str:
        """Вычисляет MD5 хеш файла для отслеживания изменений."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _is_already_processed(self, file_path: str) -> bool:
        """
        Проверяет, был ли файл уже обработан.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл уже обработан
        """
        status_file = file_path + STATUS_EXTENSION
        
        # Проверяем существование статус файла
        if not os.path.exists(status_file):
            return False
        
        # Проверяем содержимое статус файла
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Проверяем хеш файла
            current_hash = self._get_file_hash(file_path)
            if status_data.get('file_hash') != current_hash:
                return False
            
            # Проверяем размер файла
            current_size = os.path.getsize(file_path)
            if status_data.get('file_size') != current_size:
                return False
            
            # Проверяем время модификации
            current_mtime = os.path.getmtime(file_path)
            if status_data.get('file_mtime') != current_mtime:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _create_status_file(self, file_path: str, output_path: str, 
                           processing_time: float) -> None:
        """
        Создает файл статуса для обработанного файла.
        
        Args:
            file_path: Путь к исходному файлу
            output_path: Путь к выходному файлу
            processing_time: Время обработки в секундах
        """
        status_file = file_path + STATUS_EXTENSION
        
        status_data = {
            'original_file': file_path,
            'output_file': output_path,
            'file_hash': self._get_file_hash(file_path),
            'file_size': os.path.getsize(file_path),
            'file_mtime': os.path.getmtime(file_path),
            'output_size': os.path.getsize(output_path) if os.path.exists(output_path) else 0,
            'processing_time': processing_time,
            'processed_at': datetime.now().isoformat(),
            'ffmpeg_version': self._get_ffmpeg_version()
        }
        
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.errors.append(f"Ошибка создания статус файла: {e}")
    
    def _get_ffmpeg_version(self) -> str:
        """Получает версию ffmpeg."""
        if not hasattr(self, 'ffmpeg_available') or not self.ffmpeg_available:
            return "Not available"
        
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            lines = result.stdout.split('\n')
            if lines:
                return lines[0].strip()
        except Exception:
            pass
        return "Unknown"
    
    def _generate_output_filename(self, input_path: str, folder_name: str) -> str:
        """
        Генерирует имя выходного аудио файла.
        
        Args:
            input_path: Путь к входному файлу
            folder_name: Название папки
            
        Returns:
            Путь к выходному файлу
        """
        input_dir = os.path.dirname(input_path)
        input_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # Очищаем название папки от недопустимых символов
        safe_folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
        
        # Формируем имя выходного файла
        output_name = f"{safe_folder_name}_compressed.{self.output_format}"
        output_path = os.path.join(input_dir, output_name)
        
        return output_path
    
    def convert_video_to_audio(self, input_path: str, output_path: str, 
                              quality: str = 'medium') -> bool:
        """
        Конвертирует видео файл в аудио.
        
        Args:
            input_path: Путь к входному видео файлу
            output_path: Путь к выходному аудио файлу
            quality: Качество аудио (low, medium, high)
            
        Returns:
            True если конвертация успешна
        """
        # Проверяем доступность ffmpeg
        if not hasattr(self, 'ffmpeg_available') or not self.ffmpeg_available:
            print("⚠️ ffmpeg недоступен, пропускаю конвертацию")
            return False
        
        # Настройки качества
        quality_settings = {
            'low': {'bitrate': '64k', 'sample_rate': '22050'},
            'medium': {'bitrate': '128k', 'sample_rate': '44100'},
            'high': {'bitrate': '256k', 'sample_rate': '48000'}
        }
        
        settings = quality_settings.get(quality, quality_settings['medium'])
        
        # Команда ffmpeg
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vn',  # Без видео
            '-acodec', 'libmp3lame' if self.output_format == 'mp3' else 'aac',
            '-ab', settings['bitrate'],
            '-ar', settings['sample_rate'],
            '-y',  # Перезаписать выходной файл
            output_path
        ]
        
        try:
            print(f"🔄 Конвертирую {os.path.basename(input_path)} в аудио...")
            
            # Запускаем ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут таймаут
            )
            
            if result.returncode == 0:
                print(f"✅ Конвертация завершена: {os.path.basename(output_path)}")
                return True
            else:
                error_msg = f"Ошибка ffmpeg: {result.stderr}"
                print(f"❌ {error_msg}")
                self.errors.append(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Таймаут конвертации (5 минут)"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Ошибка конвертации: {e}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def compress_video(self, input_path: str, output_path: str, 
                      quality: str = 'medium', codec: str = 'h264') -> bool:
        """
        Сжимает видео файл для уменьшения размера.
        
        Args:
            input_path: Путь к входному видео файлу
            output_path: Путь к выходному сжатому видео файлу
            quality: Качество сжатия (low, medium, high, ultra)
            codec: Кодек для сжатия (h264, h265, vp9)
            
        Returns:
            True если компрессия успешна
        """
        # Проверяем доступность ffmpeg
        if not hasattr(self, 'ffmpeg_available') or not self.ffmpeg_available:
            print("⚠️ ffmpeg недоступен, пропускаю компрессию")
            return False
        
        # Настройки качества для разных кодеков
        quality_settings = {
            'h264': {
                'low': {'crf': '28', 'preset': 'fast', 'maxrate': '1000k'},
                'medium': {'crf': '23', 'preset': 'medium', 'maxrate': '2000k'},
                'high': {'crf': '18', 'preset': 'slow', 'maxrate': '4000k'},
                'ultra': {'crf': '15', 'preset': 'veryslow', 'maxrate': '8000k'}
            },
            'h265': {
                'low': {'crf': '30', 'preset': 'fast', 'maxrate': '800k'},
                'medium': {'crf': '25', 'preset': 'medium', 'maxrate': '1500k'},
                'high': {'crf': '20', 'preset': 'slow', 'maxrate': '3000k'},
                'ultra': {'crf': '17', 'preset': 'veryslow', 'maxrate': '6000k'}
            },
            'vp9': {
                'low': {'crf': '32', 'deadline': 'realtime', 'maxrate': '800k'},
                'medium': {'crf': '27', 'deadline': 'good', 'maxrate': '1500k'},
                'high': {'crf': '22', 'deadline': 'best', 'maxrate': '3000k'},
                'ultra': {'crf': '19', 'deadline': 'best', 'maxrate': '6000k'}
            }
        }
        
        # Получаем настройки для выбранного качества и кодека
        if codec not in quality_settings:
            codec = 'h264'  # По умолчанию h264
        
        if quality not in quality_settings[codec]:
            quality = 'medium'  # По умолчанию medium
        
        settings = quality_settings[codec][quality]
        
        # Формируем команду ffmpeg в зависимости от кодека
        if codec == 'h264':
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-crf', settings['crf'],
                '-preset', settings['preset'],
                '-maxrate', settings['maxrate'],
                '-bufsize', str(int(settings['maxrate'].replace('k', '')) * 2) + 'k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
        elif codec == 'h265':
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx265',
                '-crf', settings['crf'],
                '-preset', settings['preset'],
                '-maxrate', settings['maxrate'],
                '-bufsize', str(int(settings['maxrate'].replace('k', '')) * 2) + 'k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
        elif codec == 'vp9':
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libvpx-vp9',
                '-crf', settings['crf'],
                '-deadline', settings['deadline'],
                '-maxrate', settings['maxrate'],
                '-bufsize', str(int(settings['maxrate'].replace('k', '')) * 2) + 'k',
                '-c:a', 'libopus',
                '-b:a', '128k',
                '-y',
                output_path
            ]
        
        try:
            print(f"🎬 Сжимаю {os.path.basename(input_path)} ({codec}, {quality})...")
            
            # Запускаем ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 минут таймаут для компрессии
            )
            
            if result.returncode == 0:
                # Получаем размеры файлов для сравнения
                input_size = os.path.getsize(input_path)
                output_size = os.path.getsize(output_path)
                compression_ratio = (1 - output_size / input_size) * 100
                
                print(f"✅ Компрессия завершена: {os.path.basename(output_path)}")
                print(f"   📊 Размер: {self._format_size(input_size)} → {self._format_size(output_size)}")
                print(f"   📉 Сжатие: {compression_ratio:.1f}%")
                return True
            else:
                error_msg = f"Ошибка ffmpeg при компрессии: {result.stderr}"
                print(f"❌ {error_msg}")
                self.errors.append(error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Таймаут компрессии (10 минут)"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Ошибка компрессии: {e}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def process_folder(self, folder_id: str, folder_name: str, 
                      local_path: str = None) -> Dict[str, any]:
        """
        Обрабатывает папку Google Drive на предмет видео файлов.
        
        Args:
            folder_id: ID папки в Google Drive
            folder_name: Название папки
            local_path: Локальный путь для синхронизации (опционально)
            
        Returns:
            Словарь с результатами обработки
        """
        results = {
            'folder_id': folder_id,
            'folder_name': folder_name,
            'files_found': 0,
            'files_processed': 0,
            'files_skipped': 0,
            'errors': [],
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Получаем список файлов в папке
            query = f"'{folder_id}' in parents and trashed=false"
            files_result = self.drive_service.files().list(
                q=query,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files = files_result.get('files', [])
            video_files = [f for f in files if self._is_video_file(f)]
            
            results['files_found'] = len(video_files)
            print(f"📁 Папка: {folder_name}")
            print(f"🎥 Найдено видео файлов: {len(video_files)}")
            
            for video_file in video_files:
                try:
                    file_name = video_file['name']
                    file_id = video_file['id']
                    file_size = int(video_file.get('size', 0))
                    
                    print(f"  🎬 {file_name} ({self._format_size(file_size)})")
                    
                    # Если есть локальный путь, обрабатываем локально
                    if local_path:
                        local_file_path = os.path.join(local_path, file_name)
                        if os.path.exists(local_file_path):
                            if self._is_already_processed(local_file_path):
                                print(f"    ⏭️ Уже обработан, пропускаю")
                                results['files_skipped'] += 1
                                continue
                            
                            # Генерируем имя выходного файла
                            output_path = self._generate_output_filename(
                                local_file_path, folder_name
                            )
                            
                            # Сначала сжимаем видео (если включено)
                            compressed_video_path = None
                            if self.video_compression and file_size > 50 * 1024 * 1024:  # Только файлы больше 50MB
                                compressed_name = f"{os.path.splitext(file_name)[0]}_compressed.mp4"
                                compressed_video_path = os.path.join(local_path, compressed_name)
                                
                                if self.compress_video(local_file_path, compressed_video_path, 
                                                     self.video_quality, self.video_codec):
                                    print(f"    🎬 Видео сжато: {compressed_name}")
                                    # Используем сжатое видео для дальнейшей обработки
                                    local_file_path = compressed_video_path
                                else:
                                    print(f"    ⚠️ Компрессия видео не удалась, используем оригинал")
                            
                            # Конвертируем в аудио
                            if self.convert_video_to_audio(local_file_path, output_path):
                                # Создаем статус файл
                                processing_time = (datetime.now() - start_time).total_seconds()
                                self._create_status_file(local_file_path, output_path, processing_time)
                                results['files_processed'] += 1
                                
                                # Загружаем аудио файл в Google Drive
                                self._upload_audio_to_drive(output_path, folder_id, folder_name)
                                
                                # Если было создано сжатое видео, загружаем его тоже
                                if compressed_video_path and os.path.exists(compressed_video_path):
                                    self._upload_video_to_drive(compressed_video_path, folder_id, folder_name)
                            else:
                                results['errors'].append(f"Ошибка конвертации: {file_name}")
                        else:
                            print(f"    ⚠️ Локальный файл не найден: {local_file_path}")
                    else:
                        # Обрабатываем файл напрямую из Google Drive
                        print(f"    ⚠️ Локальный путь не указан, пропускаю")
                        results['files_skipped'] += 1
                        
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {video_file.get('name', 'Unknown')}: {e}"
                    print(f"    ❌ {error_msg}")
                    results['errors'].append(error_msg)
            
        except Exception as e:
            error_msg = f"Ошибка обработки папки {folder_name}: {e}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
        
        results['processing_time'] = (datetime.now() - start_time).total_seconds()
        results['errors'].extend(self.errors)
        
        return results
    
    def _is_video_file(self, file_info: Dict) -> bool:
        """Проверяет, является ли файл видео."""
        mime_type = file_info.get('mimeType', '')
        name = file_info.get('name', '')
        
        # Проверяем MIME тип
        if mime_type.startswith('video/'):
            return True
        
        # Проверяем расширение
        file_ext = os.path.splitext(name)[1].lower()
        return file_ext in VIDEO_EXTENSIONS
    
    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла в читаемом виде."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _upload_audio_to_drive(self, audio_path: str, folder_id: str, folder_name: str) -> bool:
        """
        Загружает сконвертированный аудио файл в Google Drive.
        
        Args:
            audio_path: Путь к локальному аудио файлу
            folder_id: ID папки в Google Drive
            folder_name: Название папки
            
        Returns:
            True если загрузка успешна
        """
        try:
            if not os.path.exists(audio_path):
                print(f"    ⚠️ Аудио файл не найден: {audio_path}")
                return False
            
            # Определяем MIME тип
            mime_type = 'audio/mpeg' if audio_path.endswith('.mp3') else 'audio/mp4'
            
            # Метаданные файла
            file_metadata = {
                'name': os.path.basename(audio_path),
                'parents': [folder_id],
                'description': f'Автоматически сконвертировано из видео в папке "{folder_name}"'
            }
            
            # Загружаем файл
            media = self.drive_service.files().create(
                body=file_metadata,
                media_body=audio_path,
                fields='id,name,webViewLink'
            ).execute()
            
            file_id = media.get('id')
            web_link = media.get('webViewLink', '')
            
            print(f"    ✅ Аудио загружено в Drive: {os.path.basename(audio_path)}")
            print(f"       🔗 {web_link}")
            
            return True
            
        except Exception as e:
            error_msg = f"Ошибка загрузки аудио в Drive: {e}"
            print(f"    ❌ {error_msg}")
            self.errors.append(error_msg)
            return False


    def _upload_video_to_drive(self, video_path: str, folder_id: str, folder_name: str) -> bool:
        """
        Загружает сжатый видео файл в Google Drive.
        
        Args:
            video_path: Путь к локальному видео файлу
            folder_id: ID папки в Google Drive
            folder_name: Название папки
            
        Returns:
            True если загрузка успешна
        """
        try:
            if not os.path.exists(video_path):
                print(f"    ⚠️ Видео файл не найден: {video_path}")
                return False
            
            # Определяем MIME тип
            mime_type = 'video/mp4'  # Всегда mp4 для сжатых файлов
            
            # Метаданные файла
            file_metadata = {
                'name': os.path.basename(video_path),
                'parents': [folder_id],
                'description': f'Автоматически сжат из оригинального видео в папке "{folder_name}"'
            }
            
            # Загружаем файл
            media = self.drive_service.files().create(
                body=file_metadata,
                media_body=video_path,
                fields='id,name,webViewLink'
            ).execute()
            
            file_id = media.get('id')
            web_link = media.get('webViewLink', '')
            
            print(f"    ✅ Сжатое видео загружено в Drive: {os.path.basename(video_path)}")
            print(f"       🔗 {web_link}")
            
            return True
            
        except Exception as e:
            error_msg = f"Ошибка загрузки видео в Drive: {e}"
            print(f"    ❌ {error_msg}")
            self.errors.append(error_msg)
            return False


def get_media_processor(drive_service, output_format: str = 'mp3', 
                       video_compression: bool = True, video_quality: str = 'medium', 
                       video_codec: str = 'h264') -> MediaProcessor:
    """
    Фабричная функция для создания MediaProcessor.
    
    Args:
        drive_service: Сервис Google Drive API
        output_format: Формат выходного аудио файла
        video_compression: Включить ли компрессию видео
        video_quality: Качество компрессии видео (low, medium, high, ultra)
        video_codec: Кодек для компрессии видео (h264, h265, vp9)
        
    Returns:
        Экземпляр MediaProcessor
        
    Raises:
        RuntimeError: Если ffmpeg не найден
    """
    return MediaProcessor(drive_service, output_format, video_compression, video_quality, video_codec)
