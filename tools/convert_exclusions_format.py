#!/usr/bin/env python3
"""
Скрипт для конвертации формата исключений из старого в новый.
"""

import os
import sys
from dotenv import load_dotenv

def convert_exclusions_format():
    """Конвертирует исключения из старого формата в новый."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🔄 Конвертация формата исключений...")
    print("=" * 60)
    
    # Получаем текущие исключения
    old_exclusions = os.getenv('EVENT_EXCLUSIONS', '')
    if not old_exclusions:
        print("❌ EVENT_EXCLUSIONS не найден в .env файле")
        return False
    
    print(f"📝 Текущие исключения (старый формат):")
    print(f"   {old_exclusions}")
    print()
    
    # Парсим старый формат и конвертируем в новый
    new_exclusions = []
    
    for exclusion_str in old_exclusions.split(','):
        exclusion_str = exclusion_str.strip()
        if not exclusion_str:
            continue
        
        # Парсим старый формат: account_type:exclusion_type:value
        parts = exclusion_str.split(':', 2)
        if len(parts) == 3:
            account_type, exclusion_type, value = parts
            
            # Добавляем в новый формат
            if exclusion_type == 'regex':
                new_exclusions.append(f"regex:{value}")
            else:
                new_exclusions.append(value)
        else:
            print(f"⚠️ Неверный формат исключения: {exclusion_str}")
    
    # Убираем дубликаты
    new_exclusions = list(set(new_exclusions))
    
    # Формируем новую строку
    new_exclusions_str = ','.join(new_exclusions)
    
    print(f"📝 Новые исключения (новый формат):")
    print(f"   {new_exclusions_str}")
    print()
    
    # Обновляем .env файл
    try:
        # Читаем существующий .env файл
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Заменяем строку с EVENT_EXCLUSIONS
        updated_lines = []
        for line in lines:
            if line.strip().startswith('EVENT_EXCLUSIONS='):
                updated_lines.append(f"EVENT_EXCLUSIONS={new_exclusions_str}\n")
            else:
                updated_lines.append(line)
        
        # Записываем обновленный файл
        with open('.env', 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print("✅ .env файл успешно обновлен")
        print(f"📊 Конвертировано {len(new_exclusions)} исключений")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления .env файла: {e}")
        return False

if __name__ == "__main__":
    success = convert_exclusions_format()
    
    if success:
        print("\n🎉 Конвертация завершена успешно!")
    else:
        print("\n❌ Конвертация завершена с ошибками!")
        sys.exit(1)
