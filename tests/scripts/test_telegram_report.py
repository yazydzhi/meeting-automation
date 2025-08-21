#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Telegram отчета
"""

import os
import sys
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import json

def create_telegram_report(
    total_events: int,
    total_filtered: int,
    total_excluded: int,
    processed_events: list,
    excluded_events: list,
    days: int,
    limit: int
) -> str:
    """Создаёт красивый отчёт для Telegram."""
    
    # Эмодзи для разных статусов
    emoji_stats = "📊"
    emoji_success = "✅"
    emoji_excluded = "❌"
    emoji_processed = "📁"
    emoji_time = "⏰"
    emoji_calendar = "📅"
    
    # Заголовок отчета
    report = f"{emoji_stats} *ОТЧЕТ ОБ ОБРАБОТКЕ ВСТРЕЧ*\n\n"
    
    # Основная статистика
    report += f"{emoji_calendar} *Период:* {days} {'день' if days == 1 else 'дней'}\n"
    if limit:
        report += f"{emoji_time} *Лимит:* {limit} встреч\n"
    report += f"\n"
    
    # Статистика событий
    report += f"{emoji_stats} *СТАТИСТИКА:*\n"
    report += f"• Всего событий: {total_events}\n"
    report += f"• Обработано встреч: {total_filtered}\n"
    report += f"• Исключено событий: {total_excluded}\n\n"
    
    # Обработанные встречи
    if processed_events:
        report += f"{emoji_processed} *ОБРАБОТАННЫЕ ВСТРЕЧИ:*\n"
        for i, event in enumerate(processed_events[:10], 1):  # Показываем первые 10
            title = event.get("summary", "Без названия")
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            
            if start:
                try:
                    start_str = start.replace('Z', '+00:00')
                    start_dt = datetime.fromisoformat(start_str)
                    time_str = start_dt.strftime("%d.%m %H:%M")
                    report += f"{i}. {time_str} | {title}\n"
                except:
                    report += f"{i}. {title}\n"
            else:
                report += f"{i}. {title}\n"
        
        if len(processed_events) > 10:
            report += f"... и еще {len(processed_events) - 10} встреч\n"
        report += "\n"
    
    # Исключенные события
    if excluded_events:
        report += f"{emoji_excluded} *ИСКЛЮЧЕННЫЕ СОБЫТИЯ:*\n"
        for i, title in enumerate(excluded_events[:5], 1):  # Показываем первые 5
            report += f"• {title}\n"
        if len(excluded_events) > 5:
            report += f"... и еще {len(excluded_events) - 5} событий\n"
        report += "\n"
    
    # Итог
    report += f"{emoji_success} *ИТОГ:* Система успешно обработала {total_filtered} встреч"
    if total_excluded > 0:
        report += f" и исключила {total_excluded} личных событий"
    report += "."
    
    return report

def test_telegram_report():
    """Тестирует создание Telegram отчета."""
    
    # Тестовые данные
    total_events = 5
    total_filtered = 3
    total_excluded = 2
    days = 7
    limit = 5
    
    # Тестовые события
    processed_events = [
        {
            "summary": "Тестовая встреча",
            "start": {"dateTime": "2025-08-21T18:00:00Z"},
            "end": {"dateTime": "2025-08-21T19:00:00Z"}
        },
        {
            "summary": "Отчет по ИП",
            "start": {"dateTime": "2025-08-25T09:00:00Z"},
            "end": {"dateTime": "2025-08-25T10:00:00Z"}
        },
        {
            "summary": "Встреча с клиентом",
            "start": {"dateTime": "2025-08-28T14:30:00Z"},
            "end": {"dateTime": "2025-08-28T15:30:00Z"}
        }
    ]
    
    excluded_events = [
        "Андрей Голубев День рождения",
        "Татьяна Файнштейн День рождения"
    ]
    
    print("🧪 Тестируем создание Telegram отчета...")
    print("=" * 50)
    
    # Создаём отчёт
    report = create_telegram_report(
        total_events=total_events,
        total_filtered=total_filtered,
        total_excluded=total_excluded,
        processed_events=processed_events,
        excluded_events=excluded_events,
        days=days,
        limit=limit
    )
    
    print("📱 Созданный отчёт:")
    print("-" * 30)
    print(report)
    print("-" * 30)
    
    # Проверяем длину отчета
    report_length = len(report)
    print(f"📏 Длина отчета: {report_length} символов")
    
    # Проверяем наличие ключевых элементов
    checks = [
        ("Заголовок", "ОТЧЕТ ОБ ОБРАБОТКЕ ВСТРЕЧ" in report),
        ("Статистика", "СТАТИСТИКА" in report),
        ("Обработанные встречи", "ОБРАБОТАННЫЕ ВСТРЕЧИ" in report),
        ("Исключенные события", "ИСКЛЮЧЕННЫЕ СОБЫТИЯ" in report),
        ("Итог", "ИТОГ" in report),
        ("Эмодзи", "📊" in report and "✅" in report and "❌" in report)
    ]
    
    print("\n🔍 Проверка элементов отчета:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
    
    # Проверяем форматирование времени
    time_checks = [
        "21.08 18:00" in report,
        "25.08 09:00" in report,
        "28.08 14:30" in report
    ]
    
    print("\n⏰ Проверка форматирования времени:")
    for i, result in enumerate(time_checks):
        status = "✅" if result else "❌"
        time_str = ["21.08 18:00", "25.08 09:00", "28.08 14:30"][i]
        print(f"  {status} {time_str}")
    
    # Проверяем статистику
    stats_checks = [
        f"Всего событий: {total_events}" in report,
        f"Обработано встреч: {total_filtered}" in report,
        f"Исключено событий: {total_excluded}" in report
    ]
    
    print("\n📊 Проверка статистики:")
    for i, result in enumerate(stats_checks):
        status = "✅" if result else "❌"
        stat_name = ["Всего событий", "Обработано встреч", "Исключено событий"][i]
        print(f"  {status} {stat_name}")
    
    # Итоговая оценка
    all_checks = [check[1] for check in checks] + time_checks + stats_checks
    success_rate = sum(all_checks) / len(all_checks) * 100
    
    print(f"\n🎯 Итоговая оценка: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 Отчет создан отлично!")
    elif success_rate >= 70:
        print("✅ Отчет создан хорошо!")
    else:
        print("⚠️ Отчет требует доработки!")
    
    return report

def send_test_report():
    """Отправляет тестовый отчет в Telegram."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Не найдены настройки Telegram в .env")
        return False
    
    print(f"\n📤 Отправляем тестовый отчет в Telegram...")
    print(f"Bot Token: {token[:10]}...")
    print(f"Chat ID: {chat_id}")
    
    # Создаём тестовый отчёт
    report = test_telegram_report()
    
    try:
        # Отправляем в Telegram
        response = requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": report,
                "parse_mode": "Markdown"
            },
            timeout=15
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print("✅ Отчет успешно отправлен в Telegram!")
            print(f"Message ID: {result['result']['message_id']}")
            return True
        else:
            print(f"❌ Ошибка Telegram API: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Тестирование Telegram отчета")
    print("=" * 50)
    
    # Тест 1: Создание отчета
    print("\n1️⃣ Тест создания отчета:")
    test_telegram_report()
    
    # Тест 2: Отправка в Telegram
    print("\n2️⃣ Тест отправки в Telegram:")
    send_test_report()
    
    print("\n✨ Тестирование завершено!")
