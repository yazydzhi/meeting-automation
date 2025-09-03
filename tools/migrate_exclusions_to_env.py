#!/usr/bin/env python3
"""
Скрипт для миграции файлов исключений в формат .env.
"""

import os
import sys
from typing import List, Dict

def read_exclusions_file(file_path: str) -> List[str]:
    """
    Читает файл исключений.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Список исключений
    """
    exclusions = []
    
    if not os.path.exists(file_path):
        return exclusions
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if line and not line.startswith('#'):
                    exclusions.append(line)
    except Exception as e:
        print(f"❌ Ошибка чтения файла {file_path}: {e}")
    
    return exclusions

def generate_env_exclusions(work_exclusions: List[str], personal_exclusions: List[str]) -> str:
    """
    Генерирует строку исключений для .env файла.
    
    Args:
        work_exclusions: Исключения для рабочего календаря
        personal_exclusions: Исключения для личного календаря
        
    Returns:
        Строка исключений в формате .env
    """
    env_exclusions = []
    
    # Добавляем исключения для личного календаря
    for exclusion in personal_exclusions:
        env_exclusions.append(f"personal:keyword:{exclusion}")
    
    # Добавляем исключения для рабочего календаря
    for exclusion in work_exclusions:
        env_exclusions.append(f"work:keyword:{exclusion}")
    
    return ",".join(env_exclusions)

def update_env_file(env_exclusions: str, env_file_path: str = ".env") -> bool:
    """
    Обновляет .env файл с исключениями.
    
    Args:
        env_exclusions: Строка исключений
        env_file_path: Путь к .env файлу
        
    Returns:
        True если файл обновлен успешно
    """
    try:
        # Читаем существующий .env файл
        existing_lines = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Удаляем старые EVENT_EXCLUSIONS
        filtered_lines = []
        for line in existing_lines:
            if not line.strip().startswith('EVENT_EXCLUSIONS='):
                filtered_lines.append(line)
        
        # Добавляем новые исключения
        filtered_lines.append(f"EVENT_EXCLUSIONS={env_exclusions}\n")
        
        # Записываем обновленный файл
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обновления .env файла: {e}")
        return False

def main():
    """Основная функция миграции."""
    print("🔄 Миграция файлов исключений в формат .env...")
    print("=" * 60)
    
    # Пути к файлам исключений
    work_exclusions_file = "config/work_exclusions.txt"
    personal_exclusions_file = "config/personal_exclusions.txt"
    
    # Читаем файлы исключений
    print("📖 Чтение файлов исключений...")
    work_exclusions = read_exclusions_file(work_exclusions_file)
    personal_exclusions = read_exclusions_file(personal_exclusions_file)
    
    print(f"📊 Найдено исключений:")
    print(f"  🔧 Рабочий календарь: {len(work_exclusions)}")
    print(f"  👤 Личный календарь: {len(personal_exclusions)}")
    
    if not work_exclusions and not personal_exclusions:
        print("⚠️ Файлы исключений пусты или не найдены")
        return
    
    # Показываем найденные исключения
    if work_exclusions:
        print(f"\n🔧 Исключения рабочего календаря:")
        for exclusion in work_exclusions:
            print(f"  • {exclusion}")
    
    if personal_exclusions:
        print(f"\n👤 Исключения личного календаря:")
        for exclusion in personal_exclusions:
            print(f"  • {exclusion}")
    
    # Генерируем строку для .env
    env_exclusions = generate_env_exclusions(work_exclusions, personal_exclusions)
    
    print(f"\n📝 Сгенерированная строка для .env:")
    print(f"EVENT_EXCLUSIONS={env_exclusions}")
    
    # Проверяем, существует ли .env файл
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"\n⚠️ Файл {env_file} не найден")
        print("💡 Создайте .env файл на основе env.example и запустите миграцию снова")
        return
    
    # Обновляем .env файл
    print(f"\n📝 Обновление файла {env_file}...")
    if update_env_file(env_exclusions, env_file):
        print("✅ .env файл успешно обновлен")
        
        # Предлагаем удалить старые файлы
        print(f"\n🗑️ Старые файлы исключений:")
        print(f"  • {work_exclusions_file}")
        print(f"  • {personal_exclusions_file}")
        
        response = input("\n❓ Удалить старые файлы исключений? (y/N): ").strip().lower()
        if response in ['y', 'yes', 'да']:
            try:
                if os.path.exists(work_exclusions_file):
                    os.remove(work_exclusions_file)
                    print(f"✅ Удален: {work_exclusions_file}")
                
                if os.path.exists(personal_exclusions_file):
                    os.remove(personal_exclusions_file)
                    print(f"✅ Удален: {personal_exclusions_file}")
                
                print("🎉 Миграция завершена успешно!")
                
            except Exception as e:
                print(f"❌ Ошибка удаления файлов: {e}")
        else:
            print("ℹ️ Старые файлы сохранены")
    else:
        print("❌ Ошибка обновления .env файла")

if __name__ == "__main__":
    main()
