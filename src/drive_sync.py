"""
Модуль для синхронизации файлов между Google Drive и локальной файловой системой.
Позволяет скачивать файлы для локальной обработки и загружать результаты обратно.
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io


class DriveSync:
    """Класс для синхронизации файлов с Google Drive."""
    
    def __init__(self, drive_service, sync_root: str = "data/synced"):
        """
        Инициализация синхронизатора.
        
        Args:
            drive_service: Сервис Google Drive API
            sync_root: Корневая папка для локальной синхронизации
        """
        self.drive_service = drive_service
        self.sync_root = Path(sync_root)
        self.sync_root.mkdir(parents=True, exist_ok=True)
        
        # Файл для отслеживания синхронизации
        self.sync_status_file = self.sync_root / ".sync_status.json"
        self.sync_status = self._load_sync_status()
    
    def _load_sync_status(self) -> Dict:
        """Загружает статус синхронизации."""
        if self.sync_status_file.exists():
            try:
                with open(self.sync_status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_sync_status(self) -> None:
        """Сохраняет статус синхронизации."""
        try:
            with open(self.sync_status_file, 'w', encoding='utf-8') as f:
                json.dump(self.sync_status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения статуса синхронизации: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Вычисляет MD5 хеш файла."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _get_drive_file_hash(self, file_id: str) -> str:
        """Получает MD5 хеш файла из Google Drive."""
        try:
            file_metadata = self.drive_service.files().get(
                fileId=file_id, 
                fields="md5Checksum"
            ).execute()
            return file_metadata.get('md5Checksum', '')
        except Exception:
            return ""
    
    def _needs_sync(self, file_id: str, local_path: str) -> bool:
        """
        Проверяет, нужна ли синхронизация файла.
        
        Args:
            file_id: ID файла в Google Drive
            local_path: Локальный путь к файлу
            
        Returns:
            True если файл нужно синхронизировать
        """
        # Если локальный файл не существует, нужна синхронизация
        if not os.path.exists(local_path):
            return True
        
        # Проверяем хеши
        local_hash = self._get_file_hash(local_path)
        drive_hash = self._get_drive_file_hash(file_id)
        
        if not drive_hash:
            return True
        
        return local_hash != drive_hash
    
    def sync_folder(self, folder_id: str, folder_name: str, 
                   file_types: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Синхронизирует папку Google Drive с локальной файловой системой.
        
        Args:
            folder_id: ID папки в Google Drive
            folder_name: Название папки
            file_types: Список типов файлов для синхронизации (None = все)
            
        Returns:
            Словарь с результатами синхронизации
        """
        results = {
            'folder_id': folder_id,
            'folder_name': folder_name,
            'files_found': 0,
            'files_synced': 0,
            'files_skipped': 0,
            'errors': [],
            'sync_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Создаем локальную папку
            local_folder = self.sync_root / folder_name
            local_folder.mkdir(parents=True, exist_ok=True)
            
            # Получаем список файлов в папке
            query = f"'{folder_id}' in parents and trashed=false"
            if file_types:
                type_filters = [f"mimeType='{mime_type}'" for mime_type in file_types]
                query += f" and ({' or '.join(type_filters)})"
            
            files_result = self.drive_service.files().list(
                q=query,
                fields="files(id,name,mimeType,size,md5Checksum,webViewLink)"
            ).execute()
            
            files = files_result.get('files', [])
            results['files_found'] = len(files)
            
            print(f"📁 Синхронизация папки: {folder_name}")
            print(f"📄 Найдено файлов: {len(files)}")
            
            for file_info in files:
                try:
                    file_id = file_info['id']
                    file_name = file_info['name']
                    file_size = int(file_info.get('size', 0))
                    mime_type = file_info.get('mimeType', '')
                    
                    # Формируем локальный путь
                    local_file_path = local_folder / file_name
                    
                    print(f"  📄 {file_name} ({self._format_size(file_size)})")
                    
                    # Проверяем, нужна ли синхронизация
                    if self._needs_sync(file_id, str(local_file_path)):
                        print(f"    🔄 Синхронизирую...")
                        
                        # Скачиваем файл
                        if self._download_file(file_id, str(local_file_path)):
                            # Обновляем статус синхронизации
                            self.sync_status[file_id] = {
                                'name': file_name,
                                'local_path': str(local_file_path),
                                'size': file_size,
                                'mime_type': mime_type,
                                'synced_at': datetime.now().isoformat(),
                                'local_hash': self._get_file_hash(str(local_file_path))
                            }
                            
                            results['files_synced'] += 1
                            print(f"    ✅ Синхронизирован")
                        else:
                            results['errors'].append(f"Ошибка скачивания: {file_name}")
                    else:
                        print(f"    ⏭️ Уже синхронизирован")
                        results['files_skipped'] += 1
                        
                except Exception as e:
                    error_msg = f"Ошибка обработки файла {file_info.get('name', 'Unknown')}: {e}"
                    print(f"    ❌ {error_msg}")
                    results['errors'].append(error_msg)
            
            # Сохраняем статус синхронизации
            self._save_sync_status()
            
        except Exception as e:
            error_msg = f"Ошибка синхронизации папки {folder_name}: {e}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
        
        results['sync_time'] = (datetime.now() - start_time).total_seconds()
        
        return results
    
    def _download_file(self, file_id: str, local_path: str) -> bool:
        """
        Скачивает файл из Google Drive.
        
        Args:
            file_id: ID файла в Google Drive
            local_path: Локальный путь для сохранения
            
        Returns:
            True если скачивание успешно
        """
        try:
            # Создаем временный файл
            temp_path = local_path + '.tmp'
            
            # Скачиваем файл
            request = self.drive_service.files().get_media(fileId=file_id)
            
            with open(temp_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"      📥 Прогресс: {int(status.progress() * 100)}%")
            
            # Переименовываем временный файл
            os.rename(temp_path, local_path)
            
            return True
            
        except Exception as e:
            error_msg = f"Ошибка скачивания файла {file_id}: {e}"
            print(f"      ❌ {error_msg}")
            
            # Удаляем временный файл при ошибке
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return False
    
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
    
    def get_local_path(self, folder_name: str) -> str:
        """
        Получает локальный путь к синхронизированной папке.
        
        Args:
            folder_name: Название папки
            
        Returns:
            Локальный путь к папке
        """
        return str(self.sync_root / folder_name)
    
    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Удаляет старые синхронизированные файлы.
        
        Args:
            max_age_days: Максимальный возраст файлов в днях
            
        Returns:
            Количество удаленных файлов
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        
        try:
            for folder_path in self.sync_root.iterdir():
                if folder_path.is_dir() and not folder_path.name.startswith('.'):
                    for file_path in folder_path.iterdir():
                        if file_path.is_file():
                            try:
                                file_age = file_path.stat().st_mtime
                                if file_age < cutoff_time:
                                    file_path.unlink()
                                    deleted_count += 1
                                    print(f"🗑️ Удален старый файл: {file_path}")
                            except Exception:
                                pass
        except Exception as e:
            print(f"⚠️ Ошибка очистки старых файлов: {e}")
        
        return deleted_count
    
    def get_sync_stats(self) -> Dict[str, any]:
        """Получает статистику синхронизации."""
        total_files = len(self.sync_status)
        total_size = sum(info.get('size', 0) for info in self.sync_status.values())
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_formatted': self._format_size(total_size),
            'last_sync': max((info.get('synced_at', '') for info in self.sync_status.values()), default=''),
            'folders_count': len(set(Path(info['local_path']).parent.name for info in self.sync_status.values()))
        }


def get_drive_sync(drive_service, sync_root: str = "data/synced") -> DriveSync:
    """
    Фабричная функция для создания DriveSync.
    
    Args:
        drive_service: Сервис Google Drive API
        sync_root: Корневая папка для локальной синхронизации
        
    Returns:
        Экземпляр DriveSync
    """
    return DriveSync(drive_service, sync_root)
