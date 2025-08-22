#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный скрипт автоматизации встреч
Запускает обработку для личного и рабочего аккаунтов
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/universal_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_personal_automation(command: str):
    """Запустить автоматизацию для личного аккаунта."""
    try:
        logger.info("👤 Запуск автоматизации для личного аккаунта...")
        
        # Проверяем существование скрипта
        script_path = "meeting_automation_personal.py"
        if not os.path.exists(script_path):
            logger.error(f"❌ Скрипт не найден: {script_path}")
            return False
        
        # Запускаем скрипт
        import subprocess
        result = subprocess.run([
            sys.executable, script_path, command
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Личный аккаунт: обработка завершена успешно")
            if result.stdout:
                print("📤 Вывод личного аккаунта:")
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ Личный аккаунт: ошибка выполнения")
            if result.stderr:
                logger.error(f"Ошибка: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска личного аккаунта: {e}")
        return False

def run_work_automation(command: str):
    """Запустить автоматизацию для рабочего аккаунта."""
    try:
        logger.info("🏢 Запуск автоматизации для рабочего аккаунта...")
        
        # Проверяем существование скрипта
        script_path = "meeting_automation_work.py"
        if not os.path.exists(script_path):
            logger.error(f"❌ Скрипт не найден: {script_path}")
            return False
        
        # Запускаем скрипт
        import subprocess
        result = subprocess.run([
            sys.executable, script_path, command
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Рабочий аккаунт: обработка завершена успешно")
            if result.stdout:
                print("📤 Вывод рабочего аккаунта:")
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ Рабочий аккаунт: ошибка выполнения")
            if result.stderr:
                logger.error(f"Ошибка: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска рабочего аккаунта: {e}")
        return False

def check_configurations():
    """Проверить конфигурации для обоих аккаунтов."""
    logger.info("🔧 Проверка конфигураций...")
    
    configs = {
        'personal': 'env.personal',
        'work': 'env.work'
    }
    
    status = {}
    
    for account, config_file in configs.items():
        if os.path.exists(config_file):
            logger.info(f"✅ {account.capitalize()}: конфигурация найдена")
            status[account] = True
        else:
            logger.warning(f"⚠️ {account.capitalize()}: конфигурация не найдена ({config_file})")
            status[account] = False
    
    return status

def create_summary_report(personal_success: bool, work_success: bool) -> str:
    """Создать сводный отчет о выполнении."""
    report = "🔄 *СВОДНЫЙ ОТЧЕТ АВТОМАТИЗАЦИИ*\n"
    report += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Статус личного аккаунта
    if personal_success:
        report += "👤 *Личный аккаунт:* ✅ Успешно\n"
    else:
        report += "👤 *Личный аккаунт:* ❌ Ошибка\n"
    
    # Статус рабочего аккаунта
    if work_success:
        report += "🏢 *Рабочий аккаунт:* ✅ Успешно\n"
    else:
        report += "🏢 *Рабочий аккаунт:* ❌ Ошибка\n"
    
    # Общий статус
    if personal_success and work_success:
        report += "\n🎉 *Общий результат:* Все аккаунты обработаны успешно!"
    elif personal_success or work_success:
        report += "\n⚠️ *Общий результат:* Частично успешно"
    else:
        report += "\n❌ *Общий результат:* Все аккаунты завершились с ошибками"
    
    return report

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Универсальная автоматизация встреч')
    parser.add_argument('command', choices=['prepare', 'media', 'test'], 
                       help='Команда для выполнения')
    parser.add_argument('--personal-only', action='store_true',
                       help='Только личный аккаунт')
    parser.add_argument('--work-only', action='store_true',
                       help='Только рабочий аккаунт')
    parser.add_argument('--skip-config-check', action='store_true',
                       help='Пропустить проверку конфигураций')
    
    args = parser.parse_args()
    
    logger.info("🚀 Запуск универсальной автоматизации встреч")
    
    # Проверяем конфигурации
    if not args.skip_config_check:
        config_status = check_configurations()
        logger.info(f"📋 Статус конфигураций: {config_status}")
    
    # Определяем какие аккаунты запускать
    run_personal = not args.work_only
    run_work = not args.personal_only
    
    if args.personal_only:
        logger.info("👤 Запуск только для личного аккаунта")
    elif args.work_only:
        logger.info("🏢 Запуск только для рабочего аккаунта")
    else:
        logger.info("🔄 Запуск для обоих аккаунтов")
    
    # Запускаем автоматизацию
    personal_success = False
    work_success = False
    
    if run_personal:
        personal_success = run_personal_automation(args.command)
    
    if run_work:
        work_success = run_work_automation(args.command)
    
    # Создаем сводный отчет
    if run_personal and run_work:
        report = create_summary_report(personal_success, work_success)
        print("\n" + "="*50)
        print("📊 СВОДНЫЙ ОТЧЕТ:")
        print("="*50)
        print(report)
        
        # Логируем результат
        if personal_success and work_success:
            logger.info("🎉 Все аккаунты обработаны успешно")
        elif personal_success or work_success:
            logger.warning("⚠️ Частично успешное выполнение")
        else:
            logger.error("❌ Все аккаунты завершились с ошибками")
    
    logger.info("🏁 Универсальная автоматизация завершена")

if __name__ == "__main__":
    main()
