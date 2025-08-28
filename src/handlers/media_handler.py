#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для медиа файлов
"""

import os
import time
from typing import Dict, Any, List
from .base_handler import BaseHandler, retry


class MediaHandler(BaseHandler):
    """Обработчик медиа файлов."""
    
    def __init__(self, config_manager, media_processor=None, logger=None, service_manager=None):
        """
        Инициализация обработчика медиа.
        
        Args:
            config_manager: Менеджер конфигурации
            media_processor: Существующий обработчик медиа (если есть)
            logger: Логгер
            service_manager: Ссылка на ServiceManager для доступа к кэшу
        """
        super().__init__(config_manager, logger)
        self.media_processor = media_processor
        self.service_manager = service_manager  # Для доступа к кэшу
        self.last_media_check = 0
        self.media_check_interval = 1800  # 30 минут по умолчанию
        self.last_media_stats = {}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process(self, quality: str = 'medium', *args, **kwargs) -> Dict[str, Any]:
        """
        Основной метод обработки медиа файлов.
        
        Args:
            quality: Качество сжатия ('low', 'medium', 'high')
            
        Returns:
            Результат обработки медиа
        """
        try:
            self._log_operation_start("обработку медиа файлов", quality=quality)
            
            # Проверяем, прошло ли достаточно времени с последней проверки
            current_time = time.time()
            if (current_time - self.last_media_check) < self.media_check_interval:
                self.logger.info("⏰ Медиа обработка еще не требуется")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0, "status": "skipped"}
            
            self.last_media_check = current_time
            
            # Пытаемся использовать существующий обработчик
            if self.media_processor:
                result = self.media_processor.process_media(quality)
                self.last_media_stats = result
                self._log_operation_end("обработку медиа файлов", result)
                return result
            
            # Используем собственную логику
            result = self._process_media_files(quality)
            self.last_media_stats = result
            self._log_operation_end("обработку медиа файлов", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, "обработка медиа файлов")
    
    def _process_media_files(self, quality: str) -> Dict[str, Any]:
        """
        Обработка медиа файлов с использованием universal script.
        
        Args:
            quality: Качество сжатия
            
        Returns:
            Результат обработки
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
            return self._create_error_result(e, "обработка медиа файлов")
    
    def _process_folder_media(self, folder_path: str, account_type: str, quality: str) -> Dict[str, Any]:
        """
        Обработка медиа файлов в конкретной папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            quality: Качество сжатия
            
        Returns:
            Результат обработки папки
        """
        try:
            result = {
                "account": account_type,
                "folder": folder_path,
                "processed": 0,
                "synced": 0,
                "errors": 0,
                "files": []
            }
            
            # Ищем видео файлы для обработки
            video_files = self._find_video_files(folder_path)
            
            if not video_files:
                self.logger.info(f"📁 В папке {folder_path} нет видео файлов для обработки")
                return result
            
            self.logger.info(f"🎬 Найдено {len(video_files)} видео файлов для обработки")
            
            # TASK-5: Сортируем файлы по времени создания (самый ранний = индекс 1)
            video_files_with_time = []
            for video_file in video_files:
                try:
                    creation_time = os.path.getctime(video_file)
                    video_files_with_time.append((video_file, creation_time))
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось получить время создания файла {video_file}: {e}")
                    # Если не удалось получить время, используем текущее время
                    video_files_with_time.append((video_file, time.time()))
            
            # Сортируем по времени создания (от самого раннего к самому позднему)
            video_files_with_time.sort(key=lambda x: x[1])
            
            self.logger.info(f"🔧 TASK-5: Файлы отсортированы по времени создания:")
            for i, (video_file, creation_time) in enumerate(video_files_with_time, 1):
                file_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(creation_time))
                self.logger.info(f"   {i}. {os.path.basename(video_file)} ({file_time})")
            
            # Обрабатываем каждый видео файл с правильным индексом
            for index, (video_file, creation_time) in enumerate(video_files_with_time, 1):
                try:
                    if self._process_video_file_with_index(video_file, quality, index):
                        result["processed"] += 1
                        result["files"].append(video_file)
                        self.logger.debug(f"✅ Обработан видео файл {index}: {video_file}")
                    else:
                        result["errors"] += 1
                        self.logger.warning(f"⚠️ Не удалось обработать видео файл {index}: {video_file}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки видео файла {index} {video_file}: {e}")
                    result["errors"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            result["errors"] += 1
            return result
    
    def _find_video_files(self, folder_path: str) -> List[str]:
        """
        Находит видео файлы в папке.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Список путей к видео файлам
        """
        try:
            video_files = []
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
            
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        # Проверяем, что это не уже сжатый файл
                        if not file.lower().endswith('_compressed.mp4'):
                            file_path = os.path.join(root, file)
                            
                            # ИНТЕГРАЦИЯ С МЕХАНИЗМОМ ИСКЛЮЧЕНИЯ: Проверяем, не обработан ли уже файл
                            if self.service_manager and self.service_manager._is_file_processed(file_path):
                                self.logger.info(f"⏭️ Файл уже обработан (пропускаем): {os.path.basename(file)}")
                                continue
                            
                            video_files.append(file_path)
            
            return video_files
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска видео файлов в {folder_path}: {e}")
            return []
    
    def _process_video_file_with_index(self, video_file: str, quality: str, file_index: int) -> bool:
        """
        TASK-5: Обрабатывает видео файл с поддержкой удаления оригиналов и умным именованием.
        
        Args:
            video_file: Путь к видео файлу
            quality: Качество сжатия
            file_index: Индекс файла для нумерации
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            self.logger.info(f"🎬 TASK-5: Обрабатываю видео #{file_index}: {os.path.basename(video_file)}")
            
            # TASK-5: Генерируем умные имена файлов на основе названия папки встречи
            meeting_folder = os.path.dirname(video_file)
            compressed_video, compressed_audio = self._generate_smart_filename(video_file, meeting_folder, file_index)
            
            # TASK-5: Проверяем настройку удаления оригиналов
            should_delete = self.config_manager.should_delete_original_videos()
            self.logger.info(f"🔧 TASK-5: Настройка удаления оригиналов: {should_delete}")
            
            # Реальная логика сжатия видео через FFmpeg
            video_success = self._compress_video(video_file, compressed_video, quality)
            if not video_success:
                self.logger.error(f"❌ Не удалось сжать видео: {video_file}")
                return False
            
            # Реальная логика извлечения аудио из сжатого видео
            audio_success = self._extract_audio(compressed_video, compressed_audio)
            if not audio_success:
                self.logger.error(f"❌ Не удалось извлечь аудио из сжатого видео: {compressed_video}")
                return False
            
            self.logger.info(f"✅ Создан сжатый видео файл: {compressed_video}")
            self.logger.info(f"✅ Создан сжатый аудио файл: {compressed_audio}")
            
            # ИНТЕГРАЦИЯ С МЕХАНИЗМОМ ИСКЛЮЧЕНИЯ: Отмечаем файл как обработанный
            if self.service_manager:
                self.service_manager._mark_file_processed(video_file)
                self.logger.info(f"✅ Файл отмечен как обработанный: {os.path.basename(video_file)}")
            
            # TASK-5: Логируем информацию о файлах
            if should_delete:
                self.logger.info(f"🔧 TASK-5: Система настроена на удаление оригиналов при совпадении длины")
                
                # TASK-5: Сравниваем длину оригинального и сжатого видео
                if self._compare_video_duration(video_file, compressed_video):
                    self.logger.info(f"🔧 TASK-5: Длины видео совпадают, удаляю оригинал: {os.path.basename(video_file)}")
                    try:
                        os.remove(video_file)
                        self.logger.info(f"✅ TASK-5: Оригинальный файл удален: {os.path.basename(video_file)}")
                    except Exception as e:
                        self.logger.error(f"❌ TASK-5: Не удалось удалить оригинальный файл {video_file}: {e}")
                else:
                    self.logger.warning(f"⚠️ TASK-5: Длины видео НЕ совпадают, оригинал сохранен: {os.path.basename(video_file)}")
            else:
                self.logger.info(f"🔧 TASK-5: Система настроена на сохранение оригиналов")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки видео файла {video_file}: {e}")
            return False
    
    def _process_video_file(self, video_file: str, quality: str) -> bool:
        """
        TASK-5: Обрабатывает видео файл с поддержкой удаления оригиналов (для обратной совместимости).
        
        Args:
            video_file: Путь к видео файлу
            quality: Качество сжатия
            
        Returns:
            True если обработка успешна, False иначе
        """
        # Вызываем новый метод с индексом 1 (для одного файла)
        return self._process_video_file_with_index(video_file, quality, 1)
    
    def set_media_check_interval(self, interval: int):
        """
        Устанавливает интервал проверки медиа файлов.
        
        Args:
            interval: Интервал в секундах
        """
        self.media_check_interval = interval
        self.logger.info(f"⏰ Установлен интервал проверки медиа: {interval} секунд")
    
    def get_media_stats(self) -> Dict[str, Any]:
        """
        Получает последнюю статистику обработки медиа.
        
        Returns:
            Последняя статистика
        """
        return self.last_media_stats
    
    def reset_media_check_timer(self):
        """Сбрасывает таймер проверки медиа."""
        self.last_media_check = 0
        self.logger.info("⏰ Таймер проверки медиа сброшен")
    
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
            import subprocess
            
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
    
    def _generate_smart_filename(self, video_file: str, meeting_folder: str, file_index: int = 1) -> tuple[str, str]:
        """
        Генерирует умные имена для сжатого видео и аудио файлов на основе названия папки встречи.
        
        Args:
            video_file: Путь к оригинальному видео файлу
            meeting_folder: Путь к папке встречи
            file_index: Индекс файла (для нумерации при нескольких файлах)
            
        Returns:
            Кортеж (имя_сжатого_видео, имя_сжатого_аудио)
        """
        try:
            # Получаем название папки встречи
            meeting_name = os.path.basename(meeting_folder)
            
            # Очищаем название от специальных символов для использования в имени файла
            safe_meeting_name = self._sanitize_filename(meeting_name)
            
            # Генерируем имена файлов
            if file_index == 1:
                compressed_video_name = f"{safe_meeting_name}_compressed.mp4"
                compressed_audio_name = f"{safe_meeting_name}_compressed.mp3"
            else:
                compressed_video_name = f"{safe_meeting_name}_{file_index}_compressed.mp4"
                compressed_audio_name = f"{safe_meeting_name}_{file_index}_compressed.mp3"
            
            # Формируем полные пути
            compressed_video_path = os.path.join(meeting_folder, compressed_video_name)
            compressed_audio_path = os.path.join(meeting_folder, compressed_audio_name)
            
            self.logger.info(f"🔧 TASK-5: Сгенерированы умные имена файлов:")
            self.logger.info(f"   📹 Видео: {compressed_video_name}")
            self.logger.info(f"   🎵 Аудио: {compressed_audio_name}")
            
            return compressed_video_path, compressed_audio_path
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации умных имен файлов: {e}")
            # Возвращаем стандартные имена в случае ошибки
            base_path = os.path.splitext(video_file)[0]
            return base_path + '_compressed.mp4', base_path + '_compressed.mp3'
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Очищает имя файла от недопустимых символов.
        
        Args:
            filename: Исходное имя файла
            
        Returns:
            Очищенное имя файла
        """
        # Заменяем недопустимые символы на подчеркивания
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Убираем множественные подчеркивания
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Убираем подчеркивания в начале и конце
        sanitized = sanitized.strip('_')
        
        # Ограничиваем длину имени файла
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def _compare_video_duration(self, original_file: str, compressed_file: str) -> bool:
        """
        TASK-5: Сравнивает длину оригинального и сжатого видео файлов.
        
        Args:
            original_file: Путь к оригинальному видео файлу
            compressed_file: Путь к сжатому видео файлу
            
        Returns:
            True если длины совпадают (с погрешностью 1 секунда), False иначе
        """
        try:
            import subprocess
            import json
            
            # Получаем длину оригинального файла
            cmd_original = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'json', original_file
            ]
            
            result_original = subprocess.run(cmd_original, capture_output=True, text=True, timeout=30)
            if result_original.returncode != 0:
                self.logger.error(f"❌ Не удалось получить длину оригинального файла: {result_original.stderr}")
                return False
            
            # Получаем длину сжатого файла
            cmd_compressed = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'json', compressed_file
            ]
            
            result_compressed = subprocess.run(cmd_compressed, capture_output=True, text=True, timeout=30)
            if result_compressed.returncode != 0:
                self.logger.error(f"❌ Не удалось получить длину сжатого файла: {result_compressed.stderr}")
                return False
            
            # Парсим JSON ответы
            try:
                original_data = json.loads(result_original.stdout)
                compressed_data = json.loads(result_compressed.stdout)
                
                original_duration = float(original_data['format']['duration'])
                compressed_duration = float(compressed_data['format']['duration'])
                
                # Сравниваем длину с погрешностью 1 секунда
                duration_diff = abs(original_duration - compressed_duration)
                
                self.logger.info(f"🔍 TASK-5: Сравнение длин видео:")
                self.logger.info(f"   📹 Оригинал: {original_duration:.2f} сек")
                self.logger.info(f"   🎥 Сжатый: {compressed_duration:.2f} сек")
                self.logger.info(f"   📊 Разница: {duration_diff:.2f} сек")
                
                # Возвращаем True если разница меньше 1 секунды
                return duration_diff < 1.0
                
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                self.logger.error(f"❌ Ошибка парсинга длин видео: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка сравнения длин видео: {e}")
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
            import subprocess
            
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
