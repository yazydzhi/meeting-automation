#!/usr/bin/env python3
"""
Главный скрипт для исправления всех проблем с Notion.
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def run_script(script_path, args=None):
    """Запускает скрипт и возвращает результат."""
    try:
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска {script_path}: {e}")
        return False

def main():
    """Главная функция для исправления проблем с Notion."""
    
    print("🔧 ИСПРАВЛЕНИЕ ПРОБЛЕМ С NOTION")
    print("=" * 60)
    print()
    
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального исправления добавьте --execute")
        print()
    else:
        print("⚠️ РЕАЛЬНОЕ ИСПРАВЛЕНИЕ - будут внесены изменения в Notion!")
        print("💡 Убедитесь, что у вас есть резервная копия данных")
        print()
        
        # Запрашиваем подтверждение
        response = input("Продолжить? (yes/no): ").lower().strip()
        if response not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена пользователем")
            return False
    
    print("📋 План исправления:")
    print("1. Анализ текущего состояния")
    print("2. Очистка дубликатов в Notion")
    print("3. Заполнение Event ID в Notion")
    print("4. Синхронизация данных")
    print("5. Финальная проверка")
    print()
    
    # Шаг 1: Анализ текущего состояния
    print("🔍 ШАГ 1: Анализ текущего состояния")
    print("-" * 40)
    
    print("📊 Проверка дубликатов в SQLite...")
    if not run_script("tools/check_notion_duplicates.py"):
        print("❌ Ошибка при проверке SQLite")
        return False
    
    print("\n📊 Проверка дубликатов в Notion...")
    if not run_script("tools/check_notion_api_duplicates.py"):
        print("❌ Ошибка при проверке Notion")
        return False
    
    print("\n📊 Анализ синхронизации...")
    if not run_script("tools/sync_notion_sqlite.py"):
        print("❌ Ошибка при анализе синхронизации")
        return False
    
    print("\n" + "="*60)
    
    # Шаг 2: Очистка дубликатов
    print("🧹 ШАГ 2: Очистка дубликатов в Notion")
    print("-" * 40)
    
    args = [] if dry_run else ["--execute"]
    if not run_script("tools/cleanup_notion_duplicates.py", args):
        print("❌ Ошибка при очистке дубликатов")
        return False
    
    print("\n" + "="*60)
    
    # Шаг 3: Заполнение Event ID
    print("🔧 ШАГ 3: Заполнение Event ID в Notion")
    print("-" * 40)
    
    args = [] if dry_run else ["--execute"]
    if not run_script("tools/fill_notion_event_ids.py", args):
        print("❌ Ошибка при заполнении Event ID")
        return False
    
    print("\n" + "="*60)
    
    # Шаг 4: Финальная проверка
    print("✅ ШАГ 4: Финальная проверка")
    print("-" * 40)
    
    print("📊 Повторная проверка дубликатов в Notion...")
    if not run_script("tools/check_notion_api_duplicates.py"):
        print("❌ Ошибка при финальной проверке")
        return False
    
    print("\n📊 Повторная проверка синхронизации...")
    if not run_script("tools/sync_notion_sqlite.py"):
        print("❌ Ошибка при финальной проверке синхронизации")
        return False
    
    print("\n" + "="*60)
    print("🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!")
    print("="*60)
    
    if dry_run:
        print("🔍 Все операции выполнены в тестовом режиме")
        print("💡 Для реального исправления запустите: python tools/fix_notion_issues.py --execute")
    else:
        print("✅ Все проблемы с Notion исправлены!")
        print("📊 Рекомендуется проверить результаты в Notion")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ Исправление завершено с ошибками!")
        sys.exit(1)
    else:
        print("\n✅ Исправление завершено успешно!")
