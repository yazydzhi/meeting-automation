#!/usr/bin/env python3
"""
Поиск Google токенов в системе
Проверяет все возможные места хранения токенов
"""

import os
import json
import glob
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def search_tokens_in_directory(base_path, pattern="*token*"):
    """Ищет токены в указанной директории"""
    tokens = []
    
    if not os.path.exists(base_path):
        return tokens
    
    try:
        # Ищем файлы с токенами
        search_pattern = os.path.join(base_path, "**", pattern)
        for file_path in glob.glob(search_pattern, recursive=True):
            if os.path.isfile(file_path):
                tokens.append(file_path)
    except Exception as e:
        print(f"  ❌ Ошибка поиска в {base_path}: {e}")
    
    return tokens

def analyze_token_file(file_path):
    """Анализирует файл токена"""
    print(f"\n🔍 Анализ: {file_path}")
    
    try:
        # Пробуем прочитать как JSON
        with open(file_path, 'r') as f:
            content = f.read().strip()
        
        # Проверяем, это JSON или простой токен
        if content.startswith('{'):
            try:
                token_data = json.loads(content)
                print(f"  ✅ JSON токен обнаружен")
                
                # Анализируем содержимое
                if 'scopes' in token_data:
                    scopes = token_data['scopes']
                    if isinstance(scopes, str):
                        scopes = scopes.split(' ')
                    
                    print(f"  📋 Scopes ({len(scopes)}):")
                    for scope in scopes:
                        if scope.strip():
                            scope_name = scope.split('/')[-1]
                            print(f"    - {scope_name}")
                    
                    # Проверяем типы API
                    calendar_scopes = [s for s in scopes if 'calendar' in s]
                    drive_scopes = [s for s in scopes if 'drive' in s]
                    
                    print(f"  🎯 API типы:")
                    print(f"    📅 Calendar: {len(calendar_scopes)} scopes")
                    print(f"    📁 Drive: {len(drive_scopes)} scopes")
                    
                    if 'client_id' in token_data:
                        client_id = token_data['client_id']
                        project_id = client_id.split('-')[0] if '-' in client_id else 'N/A'
                        print(f"  🏗️ Project ID: {project_id}")
                        print(f"  🔑 Client ID: {client_id}")
                    
                    return {
                        'type': 'json',
                        'scopes': scopes,
                        'calendar_scopes': len(calendar_scopes),
                        'drive_scopes': len(drive_scopes),
                        'client_id': token_data.get('client_id'),
                        'project_id': project_id if 'client_id' in token_data else None
                    }
                else:
                    print(f"  ⚠️ JSON без scopes")
                    return {'type': 'json_no_scopes'}
                    
            except json.JSONDecodeError:
                print(f"  ❌ Невалидный JSON")
                return {'type': 'invalid_json'}
        else:
            # Простой текстовый токен
            token_length = len(content)
            print(f"  📝 Простой токен (длина: {token_length})")
            return {'type': 'simple_text', 'length': token_length}
            
    except Exception as e:
        print(f"  ❌ Ошибка чтения: {e}")
        return {'type': 'error', 'error': str(e)}

def check_environment_tokens():
    """Проверяет токены из переменных окружения"""
    print("🔍 Проверяем токены из переменных окружения...")
    
    env_tokens = []
    
    # Проверяем переменные из .env
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    work_token = os.getenv('WORK_GOOGLE_TOKEN')
    
    if personal_token:
        env_tokens.append(('PERSONAL_GOOGLE_TOKEN', personal_token))
    
    if work_token:
        env_tokens.append(('WORK_GOOGLE_TOKEN', work_token))
    
    if env_tokens:
        print(f"  ✅ Найдено переменных: {len(env_tokens)}")
        for var_name, var_path in env_tokens:
            if os.path.exists(var_path):
                print(f"    ✅ {var_name}: {var_path}")
                analyze_token_file(var_path)
            else:
                print(f"    ❌ {var_name}: {var_path} (файл не найден)")
    else:
        print("  ❌ Переменные токенов не найдены")
    
    return env_tokens

def search_common_locations():
    """Ищет токены в стандартных местах"""
    print("\n🔍 Поиск токенов в стандартных местах...")
    
    common_locations = [
        "~/Library/Application Support/Google",
        "~/.config/google",
        "~/.google",
        "~/.credentials",
        "~/Library/Preferences",
        "~/Library/Application Support/Google/DriveFS"
    ]
    
    all_tokens = []
    
    for location in common_locations:
        expanded_path = os.path.expanduser(location)
        print(f"\n📁 Проверяем: {expanded_path}")
        
        if os.path.exists(expanded_path):
            tokens = search_tokens_in_directory(expanded_path)
            if tokens:
                print(f"  ✅ Найдено токенов: {len(tokens)}")
                for token_path in tokens:
                    all_tokens.append(token_path)
                    analyze_token_file(token_path)
            else:
                print(f"  ⚠️ Токены не найдены")
        else:
            print(f"  ❌ Директория не существует")
    
    return all_tokens

def search_project_tokens():
    """Ищет токены в текущем проекте"""
    print("\n🔍 Поиск токенов в текущем проекте...")
    
    project_locations = [
        "./tokens",
        "./creds", 
        "./credentials",
        "./.tokens",
        "./.credentials"
    ]
    
    project_tokens = []
    
    for location in project_locations:
        if os.path.exists(location):
            print(f"\n📁 Проверяем: {location}")
            tokens = search_tokens_in_directory(location)
            if tokens:
                print(f"  ✅ Найдено токенов: {len(tokens)}")
                for token_path in tokens:
                    project_tokens.append(token_path)
                    analyze_token_file(token_path)
            else:
                print(f"  ⚠️ Токены не найдены")
        else:
            print(f"  ❌ Директория не существует: {location}")
    
    return project_tokens

def generate_token_report(env_tokens, common_tokens, project_tokens):
    """Генерирует отчет о найденных токенах"""
    print("\n" + "=" * 80)
    print("📊 ОТЧЕТ О ПОИСКЕ GOOGLE ТОКЕНОВ")
    print("=" * 80)
    
    total_tokens = len(env_tokens) + len(common_tokens) + len(project_tokens)
    
    print(f"\n📈 Общая статистика:")
    print(f"  🔧 Переменные окружения: {len(env_tokens)}")
    print(f"  🏠 Стандартные места: {len(common_tokens)}")
    print(f"  📁 Проект: {len(project_tokens)}")
    print(f"  📊 Всего найдено: {total_tokens}")
    
    if total_tokens == 0:
        print(f"\n❌ Токены не найдены!")
        print(f"💡 Рекомендации:")
        print(f"  1. Запустить авторизацию Google API")
        print(f"  2. Проверить настройки OAuth")
        print(f"  3. Убедиться, что API включены в Cloud Console")
    else:
        print(f"\n✅ Токены найдены!")
        print(f"💡 Следующие шаги:")
        print(f"  1. Проанализировать найденные токены")
        print(f"  2. Проверить права доступа (scopes)")
        print(f"  3. При необходимости пересоздать токены")
    
    print(f"\n{'=' * 80}")

def main():
    """Основная функция поиска токенов"""
    print("🔍 ПОИСК GOOGLE ТОКЕНОВ В СИСТЕМЕ")
    print("🎯 Проверяем все возможные места хранения")
    print("=" * 80)
    
    # Проверяем токены из переменных окружения
    env_tokens = check_environment_tokens()
    
    # Ищем в стандартных местах
    common_tokens = search_common_locations()
    
    # Ищем в проекте
    project_tokens = search_project_tokens()
    
    # Генерируем отчет
    generate_token_report(env_tokens, common_tokens, project_tokens)
    
    print("\n🎊 Поиск токенов завершен!")

if __name__ == '__main__':
    main()
