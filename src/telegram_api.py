"""
Telegram API для отправки уведомлений.
"""

import logging
import requests
from typing import Optional, Dict, Any


class TelegramAPI:
    """API для работы с Telegram Bot."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Telegram API.
        
        Args:
            config: Конфигурация с bot_token и chat_id
        """
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot_token и chat_id обязательны")
        
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        """
        Отправка сообщения в Telegram.
        
        Args:
            text: Текст сообщения
            parse_mode: Режим парсинга (Markdown, HTML)
            
        Returns:
            True если сообщение отправлено успешно
        """
        try:
            data = {
                'chat_id': self.chat_id,
                'text': text
            }
            
            if parse_mode:
                data['parse_mode'] = parse_mode
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    self.logger.info(f"✅ Сообщение отправлено в Telegram (ID: {result['result']['message_id']})")
                    return True
                else:
                    self.logger.error(f"❌ Telegram API вернул ошибку: {result.get('description', 'Unknown error')}")
                    return False
            else:
                self.logger.error(f"❌ HTTP ошибка {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error("⏰ Таймаут отправки сообщения в Telegram")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ошибка сети при отправке в Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при отправке в Telegram: {e}")
            return False
    
    def send_photo(self, photo_path: str, caption: Optional[str] = None) -> bool:
        """
        Отправка фото в Telegram.
        
        Args:
            photo_path: Путь к файлу фото
            caption: Подпись к фото
            
        Returns:
            True если фото отправлено успешно
        """
        try:
            with open(photo_path, 'rb') as photo:
                data = {
                    'chat_id': self.chat_id
                }
                
                if caption:
                    data['caption'] = caption
                
                files = {
                    'photo': photo
                }
                
                response = requests.post(
                    f"{self.base_url}/sendPhoto",
                    data=data,
                    files=files,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        self.logger.info(f"✅ Фото отправлено в Telegram (ID: {result['result']['message_id']})")
                        return True
                    else:
                        self.logger.error(f"❌ Telegram API вернул ошибку: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    self.logger.error(f"❌ HTTP ошибка {response.status_code}: {response.text}")
                    return False
                    
        except FileNotFoundError:
            self.logger.error(f"❌ Файл фото не найден: {photo_path}")
            return False
        except requests.exceptions.Timeout:
            self.logger.error("⏰ Таймаут отправки фото в Telegram")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ошибка сети при отправке фото в Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при отправке фото в Telegram: {e}")
            return False
    
    def send_document(self, document_path: str, caption: Optional[str] = None) -> bool:
        """
        Отправка документа в Telegram.
        
        Args:
            document_path: Путь к файлу документа
            caption: Подпись к документу
            
        Returns:
            True если документ отправлен успешно
        """
        try:
            with open(document_path, 'rb') as document:
                data = {
                    'chat_id': self.chat_id
                }
                
                if caption:
                    data['caption'] = caption
                
                files = {
                    'document': document
                }
                
                response = requests.post(
                    f"{self.base_url}/sendDocument",
                    data=data,
                    files=files,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        self.logger.info(f"✅ Документ отправлен в Telegram (ID: {result['result']['message_id']})")
                        return True
                    else:
                        self.logger.error(f"❌ Telegram API вернул ошибку: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    self.logger.error(f"❌ HTTP ошибка {response.status_code}: {response.text}")
                    return False
                    
        except FileNotFoundError:
            self.logger.error(f"❌ Файл документа не найден: {document_path}")
            return False
        except requests.exceptions.Timeout:
            self.logger.error("⏰ Таймаут отправки документа в Telegram")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ошибка сети при отправке документа в Telegram: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при отправке документа в Telegram: {e}")
            return False
    
    def get_me(self) -> Optional[Dict[str, Any]]:
        """
        Получение информации о боте.
        
        Returns:
            Информация о боте или None при ошибке
        """
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    return result['result']
                else:
                    self.logger.error(f"❌ Telegram API вернул ошибку: {result.get('description', 'Unknown error')}")
                    return None
            else:
                self.logger.error(f"❌ HTTP ошибка {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("⏰ Таймаут получения информации о боте")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Ошибка сети при получении информации о боте: {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Неожиданная ошибка при получении информации о боте: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Тестирование соединения с Telegram API.
        
        Returns:
            True если соединение работает
        """
        try:
            bot_info = self.get_me()
            if bot_info:
                self.logger.info(f"✅ Соединение с Telegram установлено: @{bot_info.get('username', 'Unknown')}")
                return True
            else:
                self.logger.error("❌ Не удалось получить информацию о боте")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка тестирования соединения: {e}")
            return False
