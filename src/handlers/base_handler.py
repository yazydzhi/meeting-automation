#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для всех обработчиков
"""

import logging
import traceback
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import functools
import time


def retry(max_attempts=3, delay=5, backoff=2, exceptions=(Exception,)):
    """
    Декоратор для повторных попыток выполнения функции при возникновении исключений.
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (в секундах)
        backoff: Множитель для увеличения задержки с каждой попыткой
        exceptions: Кортеж исключений, которые следует перехватывать
        
    Returns:
        Декоратор функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            mtries, mdelay = max_attempts, delay
            
            # Получаем имя функции для логирования
            func_name = func.__name__
            
            while mtries > 1:
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    msg = f"❌ Ошибка в {func_name} (попытка {max_attempts - mtries + 1}/{max_attempts}): {e}"
                    self.logger.warning(msg)
                    
                    # Логируем стек вызовов для отладки
                    self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
                    
                    mtries -= 1
                    if mtries == 1:
                        self.logger.error(f"❌ Все попытки исчерпаны для {func_name}")
                        break
                        
                    self.logger.info(f"⏰ Повторная попытка через {mdelay} секунд...")
                    time.sleep(mdelay)
                    mdelay *= backoff
            
            # Последняя попытка
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков."""
    
    def __init__(self, config_manager, logger: Optional[logging.Logger] = None):
        """
        Инициализация базового обработчика.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер (если не передан, создается новый)
        """
        self.config_manager = config_manager
        
        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        else:
            self.logger = logger
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Основной метод обработки. Должен быть реализован в наследниках.
        
        Returns:
            Словарь с результатами обработки
        """
        pass
    
    def _create_error_result(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Создает стандартный результат ошибки.
        
        Args:
            error: Исключение
            context: Контекст ошибки
            
        Returns:
            Словарь с результатом ошибки
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"❌ {error_msg}")
        self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
        
        return {
            "status": "error",
            "error": error_msg,
            "processed": 0,
            "errors": 1,
            "details": [str(error)]
        }
    
    def _create_success_result(self, processed: int = 0, details: list = None) -> Dict[str, Any]:
        """
        Создает стандартный результат успешной обработки.
        
        Args:
            processed: Количество обработанных элементов
            details: Детали обработки
            
        Returns:
            Словарь с результатом успешной обработки
        """
        return {
            "status": "success",
            "processed": processed,
            "errors": 0,
            "details": details or []
        }
    
    def _log_operation_start(self, operation: str, **kwargs):
        """Логирует начало операции."""
        params = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.info(f"🚀 Начинаю {operation} {params}".strip())
    
    def _log_operation_end(self, operation: str, result: Dict[str, Any]):
        """Логирует завершение операции."""
        status = result.get("status", "unknown")
        processed = result.get("processed", 0)
        errors = result.get("errors", 0)
        
        if status in ["success", "no_files"]:
            self.logger.info(f"✅ {operation} завершена: обработано {processed}, ошибок {errors}")
        else:
            self.logger.error(f"❌ {operation} завершена с ошибками: {errors}")
    
    def _validate_config(self, required_keys: list, config: Dict[str, Any]) -> bool:
        """
        Проверяет наличие обязательных ключей в конфигурации.
        
        Args:
            required_keys: Список обязательных ключей
            config: Конфигурация для проверки
            
        Returns:
            True если все ключи присутствуют, False иначе
        """
        missing_keys = [key for key in required_keys if key not in config or not config[key]]
        
        if missing_keys:
            self.logger.error(f"❌ Отсутствуют обязательные ключи конфигурации: {missing_keys}")
            return False
        
        return True
