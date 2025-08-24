#!/usr/bin/env python3
"""
Модуль для отслеживания состояния обработки файлов в папках.
Создает и поддерживает файл .processing_status.json в каждой папке.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

class ProcessingStatus:
    """Класс для управления статусом обработки файлов в папке."""
    
    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        self.status_file = self.folder_path / '.processing_status.json'
        self.status_data = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Загружает статус из файла или создает новый."""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Ошибка загрузки статуса: {e}")
        
        # Создаем новый статус
        return {
            'folder_path': str(self.folder_path),
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'files': {},
            'processing_history': []
        }
    
    def _save_status(self):
        """Сохраняет статус в файл."""
        try:
            self.status_data['last_updated'] = datetime.now().isoformat()
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status_data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"❌ Ошибка сохранения статуса: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Вычисляет MD5 хеш файла."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"⚠️ Ошибка вычисления хеша для {file_path}: {e}")
            return ""
    
    def add_file(self, file_path: str, file_type: str = 'video'):
        """Добавляет файл в отслеживание."""
        file_path = Path(file_path)
        if not file_path.exists():
            return
        
        file_hash = self._calculate_file_hash(file_path)
        file_info = {
            'name': file_path.name,
            'type': file_type,
            'size': file_path.stat().st_size,
            'hash': file_hash,
            'added_at': datetime.now().isoformat(),
            'status': 'pending',
            'processing_steps': []
        }
        
        self.status_data['files'][file_path.name] = file_info
        self._save_status()
        print(f"📝 Добавлен файл в отслеживание: {file_path.name}")
    
    def mark_file_processed(self, file_name: str, step: str, output_files: List[str] = None):
        """Отмечает файл как обработанный на определенном этапе."""
        if file_name not in self.status_data['files']:
            print(f"⚠️ Файл {file_name} не найден в отслеживании")
            return
        
        file_info = self.status_data['files'][file_name]
        
        # Добавляем информацию об этапе обработки
        step_info = {
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'output_files': output_files or [],
            'status': 'success'
        }
        file_info['processing_steps'].append(step_info)
        
        # Проверяем, все ли этапы завершены успешно
        all_steps_success = all(
            step.get('status') == 'success' 
            for step in file_info.get('processing_steps', [])
        )
        
        # Добавляем информацию об этапе обработки
        step_info = {
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'output_files': output_files or [],
            'status': 'success'
        }
        file_info['processing_steps'].append(step_info)
        
        # Проверяем, все ли этапы завершены успешно
        all_steps_success = all(
            step.get('status') == 'success' 
            for step in file_info.get('processing_steps', [])
        )
        
        # Устанавливаем статус файла только если все этапы успешны
        if all_steps_success:
            file_info['status'] = 'processed'
        else:
            file_info['status'] = 'partially_processed'
        
        # Добавляем в историю
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': f'processed_{step}',
            'file': file_name,
            'output_files': output_files or []
        }
        self.status_data['processing_history'].append(history_entry)
        
        self._save_status()
        
        # Выводим сообщение о статусе
        if file_info['status'] == 'processed':
            print(f"✅ Файл {file_name} полностью обработан (этап: {step})")
        else:
            print(f"🔄 Файл {file_name} частично обработан (этап: {step})")
    
    def mark_file_failed(self, file_name: str, step: str, error: str):
        """Отмечает файл как неудачно обработанный."""
        if file_name not in self.status_data['files']:
            print(f"⚠️ Файл {file_name} не найден в отслеживании")
            return
        
        file_info = self.status_data['files'][file_name]
        
        # Добавляем информацию об ошибке
        step_info = {
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'status': 'failed'
        }
        file_info['processing_steps'].append(step_info)
        
        # Проверяем, есть ли успешные этапы
        successful_steps = [
            step for step in file_info.get('processing_steps', [])
            if step.get('status') == 'success'
        ]
        
        # Если есть успешные этапы, но текущий провалился - частично обработан
        if successful_steps:
            file_info['status'] = 'partially_processed'
        else:
            file_info['status'] = 'failed'
        
        # Добавляем в историю
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': f'failed_{step}',
            'file': file_name,
            'error': error
        }
        self.status_data['processing_history'].append(history_entry)
        
        self._save_status()
        print(f"❌ Файл {file_name} отмечен как неудачно обработанный (этап: {step})")
    
    def is_file_processed(self, file_name: str, step: str = None) -> bool:
        """Проверяет, обработан ли файл."""
        if file_name not in self.status_data['files']:
            return False
        
        file_info = self.status_data['files'][file_name]
        
        if step:
            # Проверяем конкретный этап
            for step_info in file_info.get('processing_steps', []):
                if step_info.get('step') == step and step_info.get('status') == 'success':
                    return True
            return False
        else:
            # Проверяем общий статус - только полностью обработанные файлы
            return file_info.get('status') == 'processed'
    
    def get_pending_files(self, file_type: str = None) -> List[str]:
        """Возвращает список файлов, ожидающих обработки."""
        pending = []
        for file_name, file_info in self.status_data['files'].items():
            if file_info.get('status') == 'pending':
                if file_type is None or file_info.get('type') == file_type:
                    pending.append(file_name)
        return pending
    
    def get_processed_files(self, file_type: str = None) -> List[str]:
        """Возвращает список обработанных файлов."""
        processed = []
        for file_name, file_info in self.status_data['files'].items():
            if file_info.get('status') == 'processed':
                if file_type is None or file_info.get('type') == file_type:
                    processed.append(file_name)
        return processed
    
    def get_file_status(self, file_name: str) -> Optional[Dict[str, Any]]:
        """Возвращает статус конкретного файла."""
        return self.status_data['files'].get(file_name)
    
    def cleanup_old_history(self, days: int = 30):
        """Очищает старую историю обработки."""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        # Фильтруем историю
        new_history = []
        for entry in self.status_data['processing_history']:
            try:
                entry_timestamp = datetime.fromisoformat(entry['timestamp']).timestamp()
                if entry_timestamp > cutoff_date:
                    new_history.append(entry)
            except ValueError:
                # Если не можем распарсить дату, оставляем
                new_history.append(entry)
        
        self.status_data['processing_history'] = new_history
        self._save_status()
        print(f"🧹 Очищена история обработки старше {days} дней")
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку по папке."""
        total_files = len(self.status_data['files'])
        pending_files = len(self.get_pending_files())
        processed_files = len(self.get_processed_files())
        partially_processed_files = len([f for f in self.status_data['files'].values() if f.get('status') == 'partially_processed'])
        failed_files = total_files - pending_files - processed_files - partially_processed_files
        
        return {
            'folder_path': str(self.folder_path),
            'total_files': total_files,
            'pending_files': pending_files,
            'processed_files': processed_files,
            'partially_processed_files': partially_processed_files,
            'failed_files': failed_files,
            'last_updated': self.status_data.get('last_updated'),
            'created_at': self.status_data.get('created_at')
        }
    
    def print_summary(self):
        """Выводит сводку в консоль."""
        summary = self.get_summary()
        print(f"\n📊 СВОДКА ПО ПАПКЕ: {summary['folder_path']}")
        print(f"📁 Всего файлов: {summary['total_files']}")
        print(f"⏳ Ожидают обработки: {summary['pending_files']}")
        print(f"✅ Полностью обработано: {summary['processed_files']}")
        print(f"🔄 Частично обработано: {summary['partially_processed_files']}")
        print(f"❌ Ошибки: {summary['failed_files']}")
        print(f"🕒 Последнее обновление: {summary['last_updated']}")
        
        if summary['total_files'] > 0:
            print(f"\n📋 ДЕТАЛИ:")
            for file_name, file_info in self.status_data['files'].items():
                status_icon = "✅" if file_info['status'] == 'processed' else "⏳" if file_info['status'] == 'pending' else "❌"
                print(f"   {status_icon} {file_name} ({file_info['status']})")
                
                if file_info.get('processing_steps'):
                    for step in file_info['processing_steps']:
                        step_icon = "✅" if step.get('status') != 'failed' else "❌"
                        print(f"      {step_icon} {step['step']}: {step.get('timestamp', 'N/A')}")
                        if step.get('error'):
                            print(f"         Ошибка: {step['error']}")
