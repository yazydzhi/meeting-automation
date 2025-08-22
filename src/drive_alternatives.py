#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Альтернативные способы работы с Google Drive
"""

import os
import shutil
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class DriveFile:
    """Структура файла Google Drive."""
    name: str
    file_id: str
    mime_type: str
    size: int
    modified_time: datetime
    parents: List[str]
    web_view_link: str
    local_path: str = ""
    md5_hash: str = ""

class DriveProvider:
    """Базовый класс для провайдеров Google Drive."""
    
    def list_files(self, folder_id: str = None, query: str = None) -> List[DriveFile]:
        """Получить список файлов."""
        raise NotImplementedError
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Скачать файл."""
        raise NotImplementedError
    
    def upload_file(self, local_path: str, folder_id: str, filename: str = None) -> Optional[str]:
        """Загрузить файл."""
        raise NotImplementedError
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """Создать папку."""
        raise NotImplementedError
    
    def file_exists(self, name: str, parent_id: str = None) -> bool:
        """Проверить существование файла/папки."""
        raise NotImplementedError

class GoogleDriveAPIProvider(DriveProvider):
    """Стандартный провайдер Google Drive API."""
    
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service = None
    
    def _get_service(self):
        """Получить Google Drive сервис."""
        if self.service is None:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                
                if os.path.exists(self.credentials_path):
                    creds = Credentials.from_authorized_user_file(self.credentials_path)
                    self.service = build('drive', 'v3', credentials=creds)
                else:
                    logger.error(f"Файл учетных данных не найден: {self.credentials_path}")
                    return None
            except Exception as e:
                logger.error(f"Ошибка инициализации Google Drive API: {e}")
                return None
        return self.service
    
    def list_files(self, folder_id: str = None, query: str = None) -> List[DriveFile]:
        """Получить список файлов через Google Drive API."""
        service = self._get_service()
        if not service:
            return []
        
        try:
            # Формируем запрос
            if query:
                q = query
            elif folder_id:
                q = f"'{folder_id}' in parents and trashed=false"
            else:
                q = "trashed=false"
            
            results = service.files().list(
                q=q,
                fields="files(id,name,mimeType,size,modifiedTime,parents,webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            drive_files = []
            
            for file in files:
                # Парсим время модификации
                modified_time = datetime.fromisoformat(
                    file['modifiedTime'].replace('Z', '+00:00')
                )
                
                # Получаем родителей
                parents = file.get('parents', [])
                
                drive_file = DriveFile(
                    name=file['name'],
                    file_id=file['id'],
                    mime_type=file['mimeType'],
                    size=int(file.get('size', 0)),
                    modified_time=modified_time,
                    parents=parents,
                    web_view_link=file.get('webViewLink', '')
                )
                drive_files.append(drive_file)
            
            return drive_files
            
        except Exception as e:
            logger.error(f"Ошибка получения файлов через Google Drive API: {e}")
            return []
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Скачать файл через Google Drive API."""
        service = self._get_service()
        if not service:
            return False
        
        try:
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Скачиваем файл
            request = service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as f:
                downloader = request.execute()
                f.write(downloader)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка скачивания файла {file_id}: {e}")
            return False
    
    def upload_file(self, local_path: str, folder_id: str, filename: str = None) -> Optional[str]:
        """Загрузить файл через Google Drive API."""
        service = self._get_service()
        if not service:
            return None
        
        try:
            if not filename:
                filename = os.path.basename(local_path)
            
            # Метаданные файла
            file_metadata = {
                'name': filename,
                'parents': [folder_id] if folder_id else []
            }
            
            # Загружаем файл
            media = service.files().create(
                body=file_metadata,
                media_body=local_path,
                fields='id'
            ).execute()
            
            return media.get('id')
            
        except Exception as e:
            logger.error(f"Ошибка загрузки файла {local_path}: {e}")
            return None
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """Создать папку через Google Drive API."""
        service = self._get_service()
        if not service:
            return None
        
        try:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Ошибка создания папки {name}: {e}")
            return None
    
    def file_exists(self, name: str, parent_id: str = None) -> bool:
        """Проверить существование файла/папки через Google Drive API."""
        service = self._get_service()
        if not service:
            return False
        
        try:
            query = f"name='{name}' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = service.files().list(
                q=query,
                fields="files(id)",
                pageSize=1
            ).execute()
            
            return len(results.get('files', [])) > 0
            
        except Exception as e:
            logger.error(f"Ошибка проверки существования файла {name}: {e}")
            return False

class LocalDriveProvider(DriveProvider):
    """Локальный провайдер для работы с файловой системой."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
    
    def list_files(self, folder_id: str = None, query: str = None) -> List[DriveFile]:
        """Получить список файлов и папок из локальной файловой системы."""
        try:
            if folder_id:
                folder_path = self.root_path / folder_id
            else:
                folder_path = self.root_path
            
            if not folder_path.exists():
                return []
            
            files = []
            for item in folder_path.iterdir():
                stat = item.stat()
                
                if item.is_file():
                    # Вычисляем MD5 хеш для файлов
                    md5_hash = self._calculate_md5(item)
                    
                    drive_file = DriveFile(
                        name=item.name,
                        file_id=str(item.relative_to(self.root_path)),
                        mime_type=self._get_mime_type(item),
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        parents=[str(item.parent.relative_to(self.root_path))] if item.parent != self.root_path else [],
                        web_view_link=f"file://{item.absolute()}",
                        local_path=str(item.absolute()),
                        md5_hash=md5_hash
                    )
                    files.append(drive_file)
                    
                elif item.is_dir():
                    # Обрабатываем папки
                    drive_file = DriveFile(
                        name=item.name,
                        file_id=str(item.relative_to(self.root_path)),
                        mime_type='application/vnd.google-apps.folder',  # Стандартный mime-type для папок Google Drive
                        size=0,  # У папок нет размера
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        parents=[str(item.parent.relative_to(self.root_path))] if item.parent != self.root_path else [],
                        web_view_link=f"file://{item.absolute()}",
                        local_path=str(item.absolute()),
                        md5_hash=""  # У папок нет хеша
                    )
                    files.append(drive_file)
            
            return files
            
        except Exception as e:
            logger.error(f"Ошибка получения файлов из локальной файловой системы: {e}")
            return []
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Копировать файл в локальную файловую систему."""
        try:
            source_path = self.root_path / file_id
            if not source_path.exists():
                logger.error(f"Файл не найден: {source_path}")
                return False
            
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Копируем файл
            shutil.copy2(source_path, local_path)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка копирования файла {file_id}: {e}")
            return False
    
    def upload_file(self, local_path: str, folder_id: str, filename: str = None) -> Optional[str]:
        """Копировать файл в локальную файловую систему."""
        try:
            if not filename:
                filename = os.path.basename(local_path)
            
            if folder_id:
                dest_folder = self.root_path / folder_id
            else:
                dest_folder = self.root_path
            
            dest_folder.mkdir(parents=True, exist_ok=True)
            dest_path = dest_folder / filename
            
            # Копируем файл
            shutil.copy2(local_path, dest_path)
            
            return str(dest_path.relative_to(self.root_path))
            
        except Exception as e:
            logger.error(f"Ошибка копирования файла {local_path}: {e}")
            return None
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """Создать папку в локальной файловой системе."""
        try:
            if parent_id:
                folder_path = self.root_path / parent_id / name
            else:
                folder_path = self.root_path / name
            
            folder_path.mkdir(parents=True, exist_ok=True)
            return str(folder_path.relative_to(self.root_path))
            
        except Exception as e:
            logger.error(f"Ошибка создания папки {name}: {e}")
            return None
    
    def file_exists(self, name: str, parent_id: str = None) -> bool:
        """Проверить существование файла/папки в локальной файловой системе."""
        try:
            if parent_id:
                file_path = self.root_path / parent_id / name
            else:
                file_path = self.root_path / name
            
            return file_path.exists()
            
        except Exception as e:
            logger.error(f"Ошибка проверки существования файла {name}: {e}")
            return False
    
    def _calculate_md5(self, file_path: Path) -> str:
        """Вычислить MD5 хеш файла."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Определить MIME тип файла по расширению."""
        suffix = file_path.suffix.lower()
        
        mime_types = {
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        
        return mime_types.get(suffix, 'application/octet-stream')

class GoogleDriveDesktopProvider(DriveProvider):
    """Провайдер для работы через Google Drive для Desktop."""
    
    def __init__(self, drive_path: str):
        self.drive_path = Path(drive_path)
        if not self.drive_path.exists():
            raise ValueError(f"Путь Google Drive не найден: {drive_path}")
    
    def list_files(self, folder_id: str = None, query: str = None) -> List[DriveFile]:
        """Получить список файлов из Google Drive для Desktop."""
        try:
            if folder_id:
                folder_path = self.drive_path / folder_id
            else:
                folder_path = self.drive_path
            
            if not folder_path.exists():
                return []
            
            files = []
            for item in folder_path.iterdir():
                if item.is_file():
                    stat = item.stat()
                    
                    # Проверяем, что файл синхронизирован
                    if self._is_file_synced(item):
                        drive_file = DriveFile(
                            name=item.name,
                            file_id=str(item.relative_to(self.drive_path)),
                            mime_type=self._get_mime_type(item),
                            size=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                            parents=[str(item.parent.relative_to(self.drive_path))] if item.parent != self.drive_path else [],
                            web_view_link=f"file://{item.absolute()}",
                            local_path=str(item.absolute())
                        )
                        files.append(drive_file)
            
            return files
            
        except Exception as e:
            logger.error(f"Ошибка получения файлов из Google Drive для Desktop: {e}")
            return []
    
    def download_file(self, file_id: str, local_path: str) -> bool:
        """Копировать файл из Google Drive для Desktop."""
        try:
            source_path = self.drive_path / file_id
            if not source_path.exists():
                logger.error(f"Файл не найден: {source_path}")
                return False
            
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Копируем файл
            shutil.copy2(source_path, local_path)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка копирования файла {file_id}: {e}")
            return False
    
    def upload_file(self, local_path: str, folder_id: str, filename: str = None) -> Optional[str]:
        """Копировать файл в Google Drive для Desktop."""
        try:
            if not filename:
                filename = os.path.basename(local_path)
            
            if folder_id:
                dest_folder = self.drive_path / folder_id
            else:
                dest_folder = self.drive_path
            
            dest_folder.mkdir(parents=True, exist_ok=True)
            dest_path = dest_folder / filename
            
            # Копируем файл
            shutil.copy2(local_path, dest_path)
            
            return str(dest_path.relative_to(self.drive_path))
            
        except Exception as e:
            logger.error(f"Ошибка копирования файла {local_path}: {e}")
            return None
    
    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        """Создать папку в Google Drive для Desktop."""
        try:
            if parent_id:
                folder_path = self.drive_path / parent_id / name
            else:
                folder_path = self.drive_path / name
            
            folder_path.mkdir(parents=True, exist_ok=True)
            return str(folder_path.relative_to(self.drive_path))
            
        except Exception as e:
            logger.error(f"Ошибка создания папки {name}: {e}")
            return None
    
    def file_exists(self, name: str, parent_id: str = None) -> bool:
        """Проверить существование файла/папки в Google Drive для Desktop."""
        try:
            if parent_id:
                file_path = self.drive_path / parent_id / name
            else:
                file_path = self.drive_path / name
            
            return file_path.exists()
            
        except Exception as e:
            logger.error(f"Ошибка проверки существования файла {name}: {e}")
            return False
    
    def _is_file_synced(self, file_path: Path) -> bool:
        """Проверить, что файл синхронизирован с облаком."""
        # Google Drive для Desktop создает специальные файлы для отслеживания синхронизации
        # Проверяем наличие .gdoc файла или других индикаторов
        gdoc_file = file_path.with_suffix('.gdoc')
        return gdoc_file.exists() or not file_path.name.startswith('.')
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Определить MIME тип файла по расширению."""
        suffix = file_path.suffix.lower()
        
        mime_types = {
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        
        return mime_types.get(suffix, 'application/octet-stream')

def get_drive_provider(provider_type: str, **kwargs) -> DriveProvider:
    """Фабрика для создания провайдеров Google Drive."""
    
    if provider_type == 'google_api':
        return GoogleDriveAPIProvider(
            kwargs.get('credentials_path', '')
        )
    elif provider_type == 'local':
        return LocalDriveProvider(
            kwargs.get('root_path', 'data/local_drive')
        )
    elif provider_type == 'google_desktop':
        return GoogleDriveDesktopProvider(
            kwargs.get('drive_path', '')
        )
    else:
        raise ValueError(f"Неизвестный тип провайдера Google Drive: {provider_type}")

def sync_with_google_drive_desktop(local_path: str, drive_path: str, filename: str = None):
    """Синхронизировать файл с Google Drive для Desktop."""
    try:
        if not filename:
            filename = os.path.basename(local_path)
        
        drive_file_path = Path(drive_path) / filename
        
        # Копируем файл в Google Drive папку
        shutil.copy2(local_path, drive_file_path)
        
        logger.info(f"Файл {filename} скопирован в Google Drive для Desktop")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации с Google Drive для Desktop: {e}")
        return False
