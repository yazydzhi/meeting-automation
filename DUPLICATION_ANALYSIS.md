# 🔍 **АНАЛИЗ ДУБЛИРОВАНИЯ КОДА В SERVICE_MANAGER.PY**

## 📋 **Обзор файла**

**Файл:** `src/service_manager.py`  
**Размер:** 1917 строк  
**Класс:** `MeetingAutomationService`  
**Основная функция:** Управление сервисом автоматизации встреч

## 🔴 **ОБНАРУЖЕННЫЕ ДУБЛИРОВАНИЯ**

### **1. Дублирование в методах `run_personal_automation` и `run_work_automation`**

**Строки:** 423-487

#### **Дублирующийся код:**
```python
# Оба метода имеют идентичную структуру:
@retry(max_attempts=2, delay=3, backoff=2)
def run_personal_automation(self) -> Dict[str, Any]:
    try:
        if self.calendar_handler:
            return self.calendar_handler.process_account('personal')
        else:
            # Используем старый метод через universal script
            self.logger.info(f"👤 Запуск обработки личного аккаунта...")
            
            cmd = [
                sys.executable,
                'meeting_automation_universal.py',
                'calendar',
                '--account', 'personal'
            ]
            
            self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                self.logger.info("✅ Обработка личного аккаунта завершена успешно")
                return {"status": "success", "output": process.stdout}
            else:
                self.logger.error(f"❌ Ошибка обработки личного аккаунта: {process.stderr}")
                return {"status": "error", "output": process.stderr}
    except Exception as e:
        self.logger.error(f"❌ Ошибка обработки личного аккаунта: {e}")
        self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
        return {"status": "error", "output": str(e)}
```

**Различия только в:**
- Названии метода
- Логе сообщениях
- Параметре `--account`

#### **Рекомендация:**
Создать общий метод `_run_account_automation(account_type: str)` и вызывать его из обоих методов.

---

### **2. Дублирование в методах `process_audio_transcription` и `process_summaries`**

**Строки:** 548-647 и 1483-1582

#### **Дублирующийся код:**
```python
# Оба метода имеют идентичную структуру:
@retry(max_attempts=2, delay=3, backoff=2)
def process_audio_transcription(self) -> Dict[str, Any]:
    try:
        if self.transcription_handler:
            # Используем новый обработчик
            result = self.transcription_handler.process_transcription()
            self.last_transcription_stats = result
            return result
        else:
            # Используем старый метод
            self.logger.info("🎤 Начинаю обработку...")
            
            stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
            
            # Обрабатываем личный аккаунт
            if self.config_manager and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Проверка в папке личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_transcription(personal_folder, "personal")
                    if personal_result["processed"] > 0:
                        stats["details"].append(personal_result)
                        stats["processed"] += personal_result.get("processed", 0)
                        stats["errors"] += personal_result.get("errors", 0)
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Проверка в папке рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_transcription(work_folder, "work")
                    if work_result["processed"] > 0:
                        stats["details"].append(work_result)
                        stats["processed"] += work_result.get("processed", 0)
                        stats["errors"] += work_result.get("errors", 0)
            
            # Сохраняем статистику
            self.last_transcription_stats = stats
            return stats
            
    except Exception as e:
        self.logger.error(f"❌ Ошибка: {e}")
        error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
        self.last_transcription_stats = error_stats
        return error_stats
```

**Различия только в:**
- Названии метода
- Логе сообщениях
- Вызове обработчика (`process_transcription` vs `process_summaries`)
- Вызове вспомогательного метода (`_process_folder_transcription` vs `_process_folder_summaries`)
- Названии переменной статистики (`last_transcription_stats` vs `last_summary_stats`)

#### **Рекомендация:**
Создать общий метод `_process_with_accounts(process_type: str, handler_method: str, folder_method: str, stats_key: str)` и вызывать его из обоих методов.

---

### **3. Дублирование в методах `_process_folder_transcription` и `_process_folder_summaries`**

**Строки:** 647-716 и 1582-1650

#### **Дублирующийся код:**
```python
# Оба метода имеют идентичную структуру:
def _process_folder_transcription(self, folder_path: str, account_type: str) -> Dict[str, Any]:
    try:
        result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
        
        # Ищем файлы для обработки
        files_to_process = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):  # или '_transcript.txt'
                    file_path = os.path.join(root, file)
                    # Проверяем, нужно ли обрабатывать
                    if self._should_process_file(file_path):
                        files_to_process.append(file_path)
        
        if not files_to_process:
            self.logger.info(f"📁 В папке {folder_path} нет файлов для обработки")
            return result
        
        self.logger.info(f"📄 Найдено {len(files_to_process)} файлов для обработки")
        
        # Обрабатываем файлы
        for file_path in files_to_process:
            try:
                # Логика обработки файла
                result["processed"] += 1
                result["files"].append(file_path)
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки {file_path}: {e}")
                result["errors"] += 1
        
        return result
        
    except Exception as e:
        self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
        result["errors"] += 1
        return result
```

**Различия только в:**
- Расширении файлов (`.mp3` vs `_transcript.txt`)
- Логике проверки необходимости обработки
- Логике обработки файла

#### **Рекомендация:**
Создать общий метод `_process_folder_files(folder_path: str, account_type: str, file_extension: str, should_process_func: callable, process_file_func: callable)` и вызывать его из обоих методов.

---

### **4. Дублирование в методе `_has_changes`**

**Строки:** 780-850

#### **Дублирующийся код:**
```python
# Дублирование в создании словарей метрик:
current_metrics = {
    'personal_events': current_state.get('personal_events', {}).get('processed', 0),
    'work_events': current_state.get('work_events', {}).get('processed', 0),
    'media_processed': current_state.get('media_processed', {}).get('count', 0),
    'transcriptions': current_state.get('transcriptions', {}).get('count', 0),
    'notion_synced': current_state.get('notion_synced', {}).get('count', 0),
    'errors_count': current_state.get('errors_count', 0)
}

previous_metrics = {
    'personal_events': previous_state.get('personal_events', {}).get('processed', 0),
    'work_events': previous_state.get('work_events', {}).get('processed', 0),
    'media_processed': previous_state.get('media_processed', {}).get('count', 0),
    'transcriptions': previous_state.get('transcriptions', {}).get('count', 0),
    'notion_synced': previous_state.get('notion_synced', {}).get('count', 0),
    'errors_count': previous_state.get('errors_count', 0)
}

# Дублирование в создании словарей статусов:
current_statuses = {
    'personal_status': current_state.get('personal_events', {}).get('status', ''),
    'work_status': current_state.get('work_events', {}).get('status', ''),
    'media_status': current_state.get('media_processed', {}).get('status', ''),
    'transcription_status': current_state.get('transcriptions', {}).get('status', ''),
    'notion_status': current_state.get('notion_synced', {}).get('status', '')
}

previous_statuses = {
    'personal_status': previous_state.get('work_events', {}).get('status', ''),
    'work_status': previous_state.get('work_events', {}).get('status', ''),
    'media_status': previous_state.get('media_processed', {}).get('status', ''),
    'transcription_status': previous_state.get('transcriptions', {}).get('status', ''),
    'notion_status': current_state.get('notion_synced', {}).get('status', '')
}
```

#### **Рекомендация:**
Создать константы для ключей метрик и статусов, а также вспомогательные методы для извлечения значений.

---

## 📊 **СТАТИСТИКА ДУБЛИРОВАНИЯ**

### **Общий объем дублирующегося кода:**
- **Методы аккаунтов:** ~64 строки (32 + 32)
- **Методы обработки:** ~100 строк (50 + 50)
- **Вспомогательные методы:** ~70 строк (35 + 35)
- **Метод проверки изменений:** ~40 строк

**Итого:** ~274 строки дублирующегося кода (14.3% от общего объема)

### **Файлы для рефакторинга:**
1. `src/service_manager.py` - основной файл
2. `src/handlers/` - новые модули для обработчиков

---

## 🎯 **ПЛАН РЕФАКТОРИНГА**

### **Этап 1: Создание базовых классов**
1. `BaseAccountHandler` - базовый класс для обработки аккаунтов
2. `BaseProcessHandler` - базовый класс для обработки файлов
3. `BaseMetricsHandler` - базовый класс для работы с метриками

### **Этап 2: Создание специализированных обработчиков**
1. `CalendarAccountHandler` - обработка календарных событий
2. `TranscriptionHandler` - обработка транскрипций
3. `SummaryHandler` - генерация саммари
4. `MediaHandler` - обработка медиа файлов
5. `NotionHandler` - синхронизация с Notion

### **Этап 3: Рефакторинг service_manager.py**
1. Замена дублирующегося кода вызовами обработчиков
2. Упрощение основного цикла
3. Улучшение читаемости и поддерживаемости

### **Этап 4: Тестирование**
1. Создание unit тестов для каждого обработчика
2. Интеграционное тестирование
3. Проверка производительности

---

## 💡 **ПРЕИМУЩЕСТВА РЕФАКТОРИНГА**

### **До рефакторинга:**
- ❌ 274 строки дублирующегося кода
- ❌ Сложность поддержки и изменения
- ❌ Высокий риск ошибок при изменении
- ❌ Плохая читаемость кода

### **После рефакторинга:**
- ✅ Устранение дублирования кода
- ✅ Легкость поддержки и изменения
- ✅ Снижение риска ошибок
- ✅ Улучшение читаемости
- ✅ Возможность переиспользования кода
- ✅ Лучшая архитектура системы

---

## 📝 **ЗАКЛЮЧЕНИЕ**

Анализ показал значительное дублирование кода в `service_manager.py` (14.3% от общего объема). Основные проблемы:

1. **Дублирование методов аккаунтов** - можно объединить в один параметризованный метод
2. **Дублирование методов обработки** - можно создать базовый класс с общей логикой
3. **Дублирование вспомогательных методов** - можно параметризовать и объединить
4. **Дублирование в методе проверки изменений** - можно вынести в константы и вспомогательные методы

Рекомендуется провести поэтапный рефакторинг с созданием специализированных обработчиков для каждого типа задач.

---

*Анализ создан: 2025-08-27*  
*Статус: Завершено*  
*Следующий шаг: Создание плана рефакторинга*
