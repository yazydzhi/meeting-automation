#!/usr/bin/env python3
"""
Тест для проверки отправки уведомлений в Telegram.
"""

import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from config_manager import ConfigManager
    from telegram_api import TelegramAPI
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


def test_telegram_connection():
    """Тест соединения с Telegram API."""
    print("🔍 Тест соединения с Telegram API")
    print("=" * 50)
    
    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        telegram_config = config_manager.get_telegram_config()
        
        if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
            print("❌ Telegram не настроен")
            return False
        
        print(f"✅ Конфигурация загружена")
        print(f"   Bot Token: {'*' * 10 + telegram_config['bot_token'][-4:] if telegram_config['bot_token'] else 'НЕТ'}")
        print(f"   Chat ID: {telegram_config['chat_id']}")
        
        # Инициализируем Telegram API
        telegram_api = TelegramAPI(telegram_config)
        
        # Тестируем соединение
        if telegram_api.test_connection():
            print("✅ Соединение с Telegram установлено")
            return True
        else:
            print("❌ Не удалось установить соединение с Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False


def test_message_sending():
    """Тест отправки сообщений."""
    print("\n📱 Тест отправки сообщений")
    print("=" * 50)
    
    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        telegram_config = config_manager.get_telegram_config()
        
        if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
            print("❌ Telegram не настроен")
            return False
        
        # Инициализируем Telegram API
        telegram_api = TelegramAPI(telegram_config)
        
        # Тест 1: Простое сообщение
        print("📝 Тест 1: Простое сообщение")
        simple_message = "🧪 Тестовое сообщение от системы автоматизации встреч"
        if telegram_api.send_message(simple_message):
            print("✅ Простое сообщение отправлено")
        else:
            print("❌ Ошибка отправки простого сообщения")
            return False
        
        # Тест 2: HTML-разметка
        print("\n📝 Тест 2: HTML-разметка")
        html_message = """
🤖 <b>Тестовый отчет системы</b>

📊 <b>Статистика:</b>
   ✅ <b>Календарь:</b> Обработано 5 событий
   ✅ <b>Медиа:</b> Обработано 2 файла
   ✅ <b>Notion:</b> Синхронизировано 3 страницы

🎯 <b>Статус:</b> Система работает в штатном режиме
        """.strip()
        
        if telegram_api.send_message(html_message, parse_mode="HTML"):
            print("✅ HTML-сообщение отправлено")
        else:
            print("❌ Ошибка отправки HTML-сообщения")
            return False
        
        # Тест 3: Детальный отчет
        print("\n📝 Тест 3: Детальный отчет")
        detailed_message = """
🤖 <b>Детальный отчет системы автоматизации встреч</b>

⏰ <b>Время выполнения:</b> 2025-08-27 15:30:00
🔄 <b>Цикл:</b> #42

📋 <b>Статус аккаунтов:</b>
   👤 <b>Личный аккаунт:</b> ✅ Активен
   🏢 <b>Рабочий аккаунт:</b> ✅ Активен

📊 <b>Результаты выполнения:</b>
📅 <b>Календарные события:</b>
   👤 <b>Личный календарь:</b> ✅ Обработано 3 из 5 событий
   🏢 <b>Рабочий календарь:</b> ✅ Обработано 2 из 3 событий

🎬 <b>Медиа файлы:</b>
   ✅ Обработано 2 файлов
   📏 Общий размер: 156.7 MB

🎤 <b>Транскрипции:</b>
   ✅ Обработано 1 файлов
   ⏱️ Общая длительность: 45:30

📝 <b>Notion синхронизация:</b>
   ✅ Синхронизировано 5 страниц
   🔄 Обновлено: 2 страниц

⏱️ <b>Время выполнения цикла:</b> 12.45 секунд

🎯 <b>Статус:</b> ✅ Система работает в штатном режиме
        """.strip()
        
        if telegram_api.send_message(detailed_message, parse_mode="HTML"):
            print("✅ Детальный отчет отправлен")
        else:
            print("❌ Ошибка отправки детального отчета")
            return False
        
        print("\n✅ Все тесты отправки сообщений пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования отправки: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("🧪 Тестирование Telegram уведомлений")
    print("=" * 60)
    
    # Тест 1: Соединение
    if not test_telegram_connection():
        print("\n❌ Тест соединения не пройден")
        return False
    
    # Тест 2: Отправка сообщений
    if not test_message_sending():
        print("\n❌ Тест отправки сообщений не пройден")
        return False
    
    print("\n🎉 Все тесты пройдены успешно!")
    print("✅ Telegram уведомления работают корректно")
    print("✅ HTML-разметка отображается правильно")
    print("✅ Детальные отчеты отправляются")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
