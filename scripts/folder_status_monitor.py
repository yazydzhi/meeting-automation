#!/usr/bin/env python3
"""
Скрипт для комплексного мониторинга состояния папок встреч.
Показывает этапы обработки, календарные события и записи в Notion.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config_manager import ConfigManager
    from notion_api import NotionAPI
    from calendar_alternatives import get_calendar_events, get_calendar_provider
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


class FolderStatusMonitor:
    """Мониторинг состояния папок встреч."""
    
    def __init__(self, config_path: str = ".env"):
        """Инициализация монитора."""
        self.config_manager = ConfigManager(config_path)
        self.logger = self._setup_logging()
        
        # Инициализируем API
        self.notion_api = None
        
        try:
            if self.config_manager.get_notion_config().get('token'):
                self.notion_api = NotionAPI(self.config_manager.get_notion_config())
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось инициализировать Notion API: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def scan_meeting_folders(self) -> Dict[str, List[Dict[str, Any]]]:
        """Сканирование папок встреч."""
        folders_status = {}
        
        # Сканируем личный аккаунт
        if self.config_manager.is_personal_enabled():
            personal_config = self.config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                folders_status['personal'] = self._scan_account_folders(personal_folder, 'personal')
        
        # Сканируем рабочий аккаунт
        if self.config_manager.is_work_enabled():
            work_config = self.config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                folders_status['work'] = self._scan_account_folders(work_folder, 'work')
        
        return folders_status
    
    def _scan_account_folders(self, root_folder: str, account_type: str) -> List[Dict[str, Any]]:
        """Сканирование папок конкретного аккаунта."""
        folders = []
        
        try:
            for item in os.listdir(root_folder):
                item_path = os.path.join(root_folder, item)
                if os.path.isdir(item_path) and any(char.isdigit() for char in item):
                    # Это папка встречи
                    folder_status = self._analyze_meeting_folder(item_path, account_type)
                    folders.append(folder_status)
        except Exception as e:
            self.logger.error(f"❌ Ошибка сканирования папок {root_folder}: {e}")
        
        return folders
    
    def _analyze_meeting_folder(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """Анализ состояния папки встречи."""
        folder_name = os.path.basename(folder_path)
        
        status = {
            'folder_name': folder_name,
            'folder_path': folder_path,
            'account_type': account_type,
            'scan_time': datetime.now().isoformat(),
            'files': {},
            'processing_status': {},
            'calendar_event': None,
            'notion_record': None,
            'overall_status': 'unknown'
        }
        
        # Анализируем файлы
        status['files'] = self._analyze_folder_files(folder_path)
        
        # Анализируем статус обработки
        status['processing_status'] = self._analyze_processing_status(folder_path)
        
        # Ищем событие в календаре
        status['calendar_event'] = self._find_calendar_event(folder_name, account_type)
        
        # Ищем запись в Notion
        status['notion_record'] = self._find_notion_record(folder_name, account_type)
        
        # Определяем общий статус
        status['overall_status'] = self._determine_overall_status(status)
        
        return status
    
    def _analyze_folder_files(self, folder_path: str) -> Dict[str, Any]:
        """Анализ файлов в папке."""
        files_info = {
            'original_video': [],
            'compressed_video': [],
            'audio_files': [],
            'transcripts': [],
            'summaries': [],
            'notion_data': [],
            'status_files': [],
            'other_files': []
        }
        
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    file_info = self._categorize_file(item, item_path)
                    
                    for category in files_info:
                        if file_info['category'] == category:
                            files_info[category].append(file_info)
                            break
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа файлов {folder_path}: {e}")
        
        return files_info
    
    def _categorize_file(self, filename: str, file_path: str) -> Dict[str, Any]:
        """Категоризация файла."""
        file_info = {
            'name': filename,
            'path': file_path,
            'size': os.path.getsize(file_path),
            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'category': 'other_files'
        }
        
        filename_lower = filename.lower()
        
        # Видео файлы
        if filename_lower.endswith(('.mp4', '.mkv', '.avi', '.mov')):
            if 'compressed' in filename_lower:
                file_info['category'] = 'compressed_video'
            else:
                file_info['category'] = 'original_video'
        
        # Аудио файлы
        elif filename_lower.endswith('.mp3'):
            file_info['category'] = 'audio_files'
        
        # Транскрипции
        elif 'transcript' in filename_lower and filename_lower.endswith('.txt'):
            file_info['category'] = 'transcripts'
        
        # Саммари
        elif 'summary' in filename_lower and filename_lower.endswith('.txt'):
            file_info['category'] = 'summaries'
        
        # Данные Notion
        elif 'notion' in filename_lower and filename_lower.endswith('.json'):
            file_info['category'] = 'notion_data'
        
        # Статус файлы
        elif 'статус' in filename_lower or 'status' in filename_lower:
            file_info['category'] = 'status_files'
        
        return file_info
    
    def _analyze_processing_status(self, folder_path: str) -> Dict[str, Any]:
        """Анализ статуса обработки."""
        status = {
            'video_compression': 'not_started',
            'audio_extraction': 'not_started',
            'transcription': 'not_started',
            'summary_generation': 'not_started',
            'notion_sync': 'not_started',
            'completion_percentage': 0
        }
        
        try:
            # Проверяем наличие сжатых видео
            compressed_videos = [f for f in os.listdir(folder_path) 
                              if f.lower().endswith(('.mp4', '.mkv')) and 'compressed' in f.lower()]
            if compressed_videos:
                status['video_compression'] = 'completed'
            
            # Проверяем наличие аудио файлов
            audio_files = [f for f in os.listdir(folder_path) 
                          if f.lower().endswith('.mp3') and 'compressed' in f.lower()]
            if audio_files:
                status['audio_extraction'] = 'completed'
            
            # Проверяем наличие транскрипций
            transcripts = [f for f in os.listdir(folder_path) 
                          if 'transcript' in f.lower() and f.lower().endswith('.txt')]
            if transcripts:
                status['transcription'] = 'completed'
            
            # Проверяем наличие саммари
            summaries = [f for f in os.listdir(folder_path) 
                        if 'summary' in f.lower() and f.lower().endswith('.txt')]
            if summaries:
                status['summary_generation'] = 'completed'
            
            # Проверяем наличие данных Notion
            notion_data = [f for f in os.listdir(folder_path) 
                          if 'notion' in f.lower() and f.lower().endswith('.json')]
            if notion_data:
                status['notion_sync'] = 'completed'
            
            # Вычисляем процент завершения
            completed_steps = sum(1 for step in status.values() if step == 'completed')
            total_steps = len([k for k in status.keys() if k != 'completion_percentage'])
            status['completion_percentage'] = int((completed_steps / total_steps) * 100)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа статуса обработки {folder_path}: {e}")
        
        return status
    
    def _find_calendar_event(self, folder_name: str, account_type: str) -> Optional[Dict[str, Any]]:
        """Поиск события в календаре."""
        try:
            # Извлекаем дату из названия папки
            date_match = self._extract_date_from_folder_name(folder_name)
            if not date_match:
                return None
            
            # Получаем настройки календаря для аккаунта
            if account_type == 'personal':
                config = self.config_manager.get_personal_config()
                provider_type = config.get('calendar_provider', 'web_ical')
                calendar_url = config.get('ical_calendar_url')
            elif account_type == 'work':
                config = self.config_manager.get_work_config()
                provider_type = config.get('calendar_provider', 'web_ical')
                calendar_url = config.get('ical_calendar_url')
            else:
                return None
            
            if not calendar_url:
                return None
            
            # Ищем события в календаре
            start_date = date_match.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date_match.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            events = get_calendar_events(provider_type, start_date, end_date, calendar_url=calendar_url)
            
            if events:
                # Ищем наиболее подходящее событие
                for event in events:
                    if self._event_matches_folder(event, folder_name):
                        return {
                            'id': getattr(event, 'id', None),
                            'summary': getattr(event, 'title', 'Без названия'),
                            'start': event.start.isoformat() if event.start else None,
                            'end': event.end.isoformat() if event.end else None,
                            'status': 'confirmed',
                            'attendees': getattr(event, 'attendees', [])
                        }
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка поиска в календаре: {e}")
        
        return None
    
    def _extract_date_from_folder_name(self, folder_name: str) -> Optional[datetime]:
        """Извлечение даты из названия папки."""
        try:
            # Пытаемся найти дату в формате YYYY-MM-DD
            import re
            date_pattern = r'(\d{4}-\d{2}-\d{2})'
            match = re.search(date_pattern, folder_name)
            if match:
                return datetime.strptime(match.group(1), '%Y-%m-%d')
            
            # Альтернативные форматы
            patterns = [
                r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
                r'(\d{2}\.\d{2}\.\d{4})',  # DD.MM.YYYY
                r'(\d{4}\.\d{2}\.\d{2})',  # YYYY.MM.DD
            ]
            
            for pattern in patterns:
                match = re.search(pattern, folder_name)
                if match:
                    date_str = match.group(1)
                    if '.' in date_str:
                        if len(date_str.split('.')[0]) == 4:  # YYYY.MM.DD
                            return datetime.strptime(date_str, '%Y.%m.%d')
                        else:  # DD.MM.YYYY
                            return datetime.strptime(date_str, '%d.%m.%Y')
                    else:  # DD-MM-YYYY
                        return datetime.strptime(date_str, '%d-%m-%Y')
            
        except Exception as e:
            self.logger.debug(f"Не удалось извлечь дату из '{folder_name}': {e}")
        
        return None
    
    def _event_matches_folder(self, event: Dict[str, Any], folder_name: str) -> bool:
        """Проверка соответствия события названию папки."""
        event_summary = event.get('summary', '').lower()
        folder_lower = folder_name.lower()
        
        # Простая проверка по ключевым словам
        keywords = ['встреча', 'meeting', 'интервью', 'interview', 'демо', 'demo']
        
        for keyword in keywords:
            if keyword in folder_lower and keyword in event_summary:
                return True
        
        # Проверка по времени (если есть время в названии папки)
        time_match = self._extract_time_from_folder_name(folder_name)
        if time_match and event.get('start'):
            event_time = event['start']
            if isinstance(event_time, str):
                try:
                    event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    # Проверяем, что время совпадает с точностью до часа
                    if abs(event_dt.hour - time_match.hour) <= 1:
                        return True
                except:
                    pass
        
        return False
    
    def _extract_time_from_folder_name(self, folder_name: str) -> Optional[datetime]:
        """Извлечение времени из названия папки."""
        try:
            import re
            # Ищем время в формате HH-MM или HH:MM
            time_pattern = r'(\d{1,2})[-:](\d{2})'
            match = re.search(time_pattern, folder_name)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        except:
            pass
        return None
    
    def _find_notion_record(self, folder_name: str, account_type: str) -> Optional[Dict[str, Any]]:
        """Поиск записи в Notion."""
        if not self.notion_api:
            return None
        
        try:
            # Ищем записи в базе данных Notion
            database_id = self.config_manager.get_notion_config().get('database_id')
            if not database_id:
                return None
            
            # Ищем по названию папки или ключевым словам
            query = self._build_notion_query(folder_name, account_type)
            results = self.notion_api.search_database(database_id, query)
            
            if results and len(results) > 0:
                record = results[0]  # Берем первую найденную запись
                return {
                    'id': record.get('id'),
                    'title': record.get('properties', {}).get('Title', {}).get('title', [{}])[0].get('plain_text', ''),
                    'status': record.get('properties', {}).get('Status', {}).get('select', {}).get('name', ''),
                    'created': record.get('created_time'),
                    'updated': record.get('last_edited_time'),
                    'url': record.get('url')
                }
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка поиска в Notion: {e}")
        
        return None
    
    def _build_notion_query(self, folder_name: str, account_type: str) -> Dict[str, Any]:
        """Построение запроса для поиска в Notion."""
        # Извлекаем ключевые слова из названия папки
        keywords = []
        
        # Убираем дату и время
        import re
        clean_name = re.sub(r'\d{4}-\d{2}-\d{2}', '', folder_name)
        clean_name = re.sub(r'\d{1,2}[-:]\d{2}', '', clean_name)
        
        # Разбиваем на слова
        words = clean_name.split()
        keywords = [word for word in words if len(word) > 2 and not word.isdigit()]
        
        # Добавляем информацию об аккаунте
        if account_type == 'personal':
            keywords.append('личный')
        elif account_type == 'work':
            keywords.append('рабочий')
        
        return {
            'filter': {
                'or': [
                    {
                        'property': 'Title',
                        'rich_text': {
                            'contains': keyword
                        }
                    } for keyword in keywords[:3]  # Ограничиваем количество ключевых слов
                ]
            }
        }
    
    def _determine_overall_status(self, folder_status: Dict[str, Any]) -> str:
        """Определение общего статуса папки."""
        processing = folder_status['processing_status']
        
        if processing['completion_percentage'] == 100:
            return 'completed'
        elif processing['completion_percentage'] >= 75:
            return 'near_completion'
        elif processing['completion_percentage'] >= 50:
            return 'in_progress'
        elif processing['completion_percentage'] >= 25:
            return 'started'
        else:
            return 'not_started'
    
    def generate_report(self, folders_status: Dict[str, List[Dict[str, Any]]]) -> str:
        """Генерация отчета."""
        report = []
        report.append("🤖 *КОМПЛЕКСНЫЙ ОТЧЕТ О СОСТОЯНИИ ПАПОК ВСТРЕЧ*")
        report.append(f"⏰ Время сканирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_folders = 0
        completed_folders = 0
        
        for account_type, folders in folders_status.items():
            if not folders:
                continue
            
            report.append(f"👥 *{account_type.upper()} АККАУНТ*")
            report.append(f"📁 Всего папок: {len(folders)}")
            report.append("")
            
            for folder in folders:
                total_folders += 1
                if folder['overall_status'] == 'completed':
                    completed_folders += 1
                
                report.append(f"📂 *{folder['folder_name']}*")
                report.append(f"   🎯 Статус: {self._get_status_emoji(folder['overall_status'])} {folder['overall_status']}")
                report.append(f"   📊 Прогресс: {folder['processing_status']['completion_percentage']}%")
                
                # Детали обработки
                processing = folder['processing_status']
                report.append("   🔄 Этапы обработки:")
                report.append(f"      🎬 Видео: {self._get_step_status(processing['video_compression'])}")
                report.append(f"      🎵 Аудио: {self._get_step_status(processing['audio_extraction'])}")
                report.append(f"      📝 Транскрипция: {self._get_step_status(processing['transcription'])}")
                report.append(f"      📋 Саммари: {self._get_step_status(processing['summary_generation'])}")
                report.append(f"      🔗 Notion: {self._get_step_status(processing['notion_sync'])}")
                
                # Календарное событие
                if folder['calendar_event']:
                    event = folder['calendar_event']
                    report.append(f"   📅 Календарь: ✅ {event.get('summary', 'Без названия')}")
                    if event.get('start'):
                        report.append(f"      ⏰ Время: {event['start']}")
                else:
                    report.append("   📅 Календарь: ❌ Событие не найдено")
                
                # Запись в Notion
                if folder['notion_record']:
                    record = folder['notion_record']
                    report.append(f"   📚 Notion: ✅ {record.get('title', 'Без названия')}")
                    report.append(f"      🔗 Ссылка: {record.get('url', 'N/A')}")
                else:
                    report.append("   📚 Notion: ❌ Запись не найдена")
                
                # Файлы
                files = folder['files']
                if files['original_video']:
                    report.append(f"   🎥 Оригинальные видео: {len(files['original_video'])}")
                if files['compressed_video']:
                    report.append(f"   🎬 Сжатые видео: {len(files['compressed_video'])}")
                if files['transcripts']:
                    report.append(f"   📄 Транскрипции: {len(files['transcripts'])}")
                if files['summaries']:
                    report.append(f"   📋 Саммари: {len(files['summaries'])}")
                
                report.append("")
        
        # Общая статистика
        report.append("📊 *ОБЩАЯ СТАТИСТИКА*")
        report.append(f"📁 Всего папок встреч: {total_folders}")
        report.append(f"✅ Завершено: {completed_folders}")
        report.append(f"🔄 В процессе: {total_folders - completed_folders}")
        if total_folders > 0:
            completion_rate = int((completed_folders / total_folders) * 100)
            report.append(f"📈 Процент завершения: {completion_rate}%")
        
        report.append("")
        report.append("🔄 *Следующее сканирование:* через 5 минут")
        report.append("📱 *Уведомления:* автоматически")
        
        return "\n".join(report)
    
    def _get_status_emoji(self, status: str) -> str:
        """Получение эмодзи для статуса."""
        emoji_map = {
            'completed': '✅',
            'near_completion': '🟡',
            'in_progress': '🔄',
            'started': '🟠',
            'not_started': '❌'
        }
        return emoji_map.get(status, '❓')
    
    def _get_step_status(self, step_status: str) -> str:
        """Получение статуса этапа."""
        emoji_map = {
            'completed': '✅',
            'in_progress': '🔄',
            'not_started': '❌'
        }
        return f"{emoji_map.get(step_status, '❓')} {step_status}"
    
    def save_report(self, report: str, output_file: str = None) -> str:
        """Сохранение отчета в файл."""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"folder_status_report_{timestamp}.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.logger.info(f"✅ Отчет сохранен в файл: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения отчета: {e}")
            return None
    
    def run_monitoring(self, save_to_file: bool = False, output_file: str = None) -> str:
        """Запуск мониторинга."""
        self.logger.info("🚀 Запуск комплексного мониторинга папок встреч...")
        
        try:
            # Сканируем папки
            folders_status = self.scan_meeting_folders()
            
            if not folders_status:
                self.logger.warning("⚠️ Не найдено папок встреч для мониторинга")
                return "Не найдено папок встреч"
            
            # Генерируем отчет
            report = self.generate_report(folders_status)
            
            # Сохраняем в файл если нужно
            if save_to_file:
                saved_file = self.save_report(report, output_file)
                if saved_file:
                    report += f"\n\n💾 Отчет сохранен в файл: {saved_file}"
            
            self.logger.info("✅ Мониторинг завершен успешно")
            return report
            
        except Exception as e:
            error_msg = f"❌ Ошибка мониторинга: {e}"
            self.logger.error(error_msg)
            return error_msg


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Мониторинг состояния папок встреч')
    parser.add_argument('--config', default='.env', help='Путь к файлу конфигурации')
    parser.add_argument('--save', action='store_true', help='Сохранить отчет в файл')
    parser.add_argument('--output', help='Путь к выходному файлу')
    parser.add_argument('--telegram', action='store_true', help='Отправить отчет в Telegram')
    
    args = parser.parse_args()
    
    # Создаем монитор
    monitor = FolderStatusMonitor(args.config)
    
    # Запускаем мониторинг
    report = monitor.run_monitoring(args.save, args.output)
    
    # Выводим отчет
    print(report)
    
    # Отправляем в Telegram если нужно
    if args.telegram:
        try:
            from telegram_api import TelegramAPI
            telegram_config = monitor.config_manager.get_telegram_config()
            if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
                telegram_api = TelegramAPI(telegram_config)
                success = telegram_api.send_message(report, parse_mode="Markdown")
                if success:
                    print("✅ Отчет отправлен в Telegram")
                else:
                    print("❌ Не удалось отправить отчет в Telegram")
            else:
                print("⚠️ Telegram не настроен")
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")


if __name__ == "__main__":
    main()
