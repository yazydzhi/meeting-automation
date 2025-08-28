#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для обработки аккаунтов
"""

import os
import sys
import subprocess
import traceback
from typing import Dict, Any, Optional
from .base_handler import BaseHandler, retry
from .calendar_integration_handler import CalendarIntegrationHandler


class AccountHandler(BaseHandler):
    """Базовый класс для обработки аккаунтов."""
    
    def __init__(self, config_manager, calendar_handler=None, notion_handler=None, logger=None):
        """
        Инициализация обработчика аккаунтов.
        
        Args:
            config_manager: Менеджер конфигурации
            calendar_handler: Обработчик календаря (если есть)
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.calendar_handler = calendar_handler
        self.calendar_integration_handler = CalendarIntegrationHandler(config_manager, notion_handler, logger)
    
    def process(self, account_type: str = 'personal') -> Dict[str, Any]:
        """
        Основной метод обработки (реализация абстрактного метода).
        
        Args:
            account_type: Тип аккаунта ('personal' или 'work')
            
        Returns:
            Результат обработки аккаунта
        """
        return self.process_account(account_type)
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process_account(self, account_type: str) -> Dict[str, Any]:
        """
        Обрабатывает аккаунт указанного типа.
        
        Args:
            account_type: Тип аккаунта ('personal' или 'work')
            
        Returns:
            Результат обработки аккаунта
        """
        try:
            self._log_operation_start("обработку аккаунта", account_type=account_type)
            
            # Проверяем, включен ли аккаунт
            if not self._is_account_enabled(account_type):
                self.logger.info(f"⏭️ Аккаунт {account_type} пропущен (отключен в конфигурации)")
                return self._create_success_result(0, [f"Аккаунт {account_type} отключен"])
            
            # Пытаемся использовать новый обработчик интеграции календаря
            if self.calendar_integration_handler:
                result = self.calendar_integration_handler.process_calendar_events(account_type)
                self._log_operation_end(f"обработку аккаунта {account_type}", result)
                return result
            
            # Если calendar_integration_handler недоступен, возвращаем базовый результат
            # вместо вызова universal script (чтобы избежать рекурсии)
            self.logger.info(f"📅 Calendar integration handler недоступен, возвращаю базовый результат для {account_type}")
            result = self._create_success_result(0, [f"Аккаунт {account_type} обработан (базовый режим)"])
            self._log_operation_end(f"обработку аккаунта {account_type}", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, f"обработка аккаунта {account_type}")
    
    def _is_account_enabled(self, account_type: str) -> bool:
        """
        Проверяет, включен ли аккаунт.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            True если аккаунт включен, False иначе
        """
        if account_type == 'personal':
            return self.config_manager.is_personal_enabled()
        elif account_type == 'work':
            return self.config_manager.is_work_enabled()
        else:
            self.logger.warning(f"⚠️ Неизвестный тип аккаунта: {account_type}")
            return False
    
    def _run_universal_script(self, account_type: str) -> Dict[str, Any]:
        """
        Запускает обработку через universal script.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Результат выполнения скрипта
        """
        try:
            # Определяем эмодзи для типа аккаунта
            emoji = "👤" if account_type == "personal" else "🏢"
            account_name = "личного" if account_type == "personal" else "рабочего"
            
            self.logger.info(f"{emoji} Запуск обработки {account_name} аккаунта...")
            
            # Формируем команду
            cmd = [
                sys.executable,
                'meeting_automation_universal.py',
                'calendar',
                '--account', account_type
            ]
            
            self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
            
            # Выполняем команду
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                self.logger.info(f"✅ Обработка {account_name} аккаунта завершена успешно")
                return {
                    "status": "success",
                    "output": process.stdout,
                    "processed": 0,  # Нет реальной обработки, только проверка
                    "errors": 0,
                    "details": [f"Аккаунт {account_type} обработан через universal script"]
                }
            else:
                self.logger.error(f"❌ Ошибка обработки {account_name} аккаунта: {process.stderr}")
                return {
                    "status": "error",
                    "output": process.stderr,
                    "processed": 0,
                    "errors": 1,
                    "details": [f"Ошибка выполнения universal script для {account_type}"]
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска universal script для {account_type}: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return self._create_error_result(e, f"запуск universal script для {account_type}")
    
    def process_both_accounts(self) -> Dict[str, Any]:
        """
        Обрабатывает оба аккаунта параллельно.
        
        Returns:
            Объединенный результат обработки
        """
        try:
            self._log_operation_start("обработку обоих аккаунтов")
            
            results = {}
            total_processed = 0
            total_errors = 0
            
            # Обрабатываем личный аккаунт
            if self._is_account_enabled('personal'):
                personal_result = self.process_account('personal')
                results['personal'] = personal_result
                total_processed += personal_result.get('processed', 0)
                total_errors += personal_result.get('errors', 0)
            else:
                results['personal'] = {"status": "skipped", "output": "Аккаунт отключен"}
            
            # Обрабатываем рабочий аккаунт
            if self._is_account_enabled('work'):
                work_result = self.process_account('work')
                results['work'] = work_result
                total_processed += work_result.get('processed', 0)
                total_errors += work_result.get('errors', 0)
            else:
                results['work'] = {"status": "skipped", "output": "Аккаунт отключен"}
            
            # Формируем общий результат
            overall_result = {
                "status": "success" if total_errors == 0 else "partial_success",
                "personal": results['personal'],
                "work": results['work'],
                "total_processed": total_processed,
                "total_errors": total_errors
            }
            
            self._log_operation_end("обработку обоих аккаунтов", overall_result)
            return overall_result
            
        except Exception as e:
            return self._create_error_result(e, "обработка обоих аккаунтов")
    
    def get_account_config(self, account_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает конфигурацию аккаунта.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Конфигурация аккаунта или None
        """
        try:
            if account_type == 'personal':
                return self.config_manager.get_personal_config()
            elif account_type == 'work':
                return self.config_manager.get_work_config()
            else:
                self.logger.warning(f"⚠️ Неизвестный тип аккаунта: {account_type}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигурации для {account_type}: {e}")
            return None
