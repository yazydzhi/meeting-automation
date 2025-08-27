# 🕐 **ДОКУМЕНТАЦИЯ ПО ИСПРАВЛЕНИЮ ТАЙМЗОН**

## 📋 **Обзор проблемы**

### **Проблема:**
В системе автоматизации встреч были обнаружены проблемы с таймзонами при синхронизации между Google Calendar и Notion:

1. **Google Calendar возвращает время в UTC** (с 'Z' на конце)
2. **Система неправильно обрабатывала UTC время** - заменяла 'Z' на '+00:00', но все равно оставалась в UTC
3. **В Notion добавлялся '+03:00'** к уже конвертированному времени, что приводило к двойной конвертации
4. **Результат:** события в Notion отображались со сдвигом на 3 часа

### **Пример проблемы:**
```
Google Calendar: 10:00 UTC
Неправильная обработка: 10:00 UTC (заменяем Z на +00:00)
Добавляем +03:00: 10:00+03:00 (неправильно!)
Результат: событие отображается в 10:00 вместо 13:00
```

## 🔧 **Принятые исправления**

### **1. Добавлена функция конвертации таймзон**

**Файл:** `src/calendar_alternatives.py`

```python
def convert_utc_to_local(utc_dt: datetime, local_timezone: str = 'Europe/Moscow') -> datetime:
    """
    Конвертирует время из UTC в локальную таймзону.
    
    Args:
        utc_dt: Время в UTC
        local_timezone: Локальная таймзона (по умолчанию Europe/Moscow)
        
    Returns:
        Время в локальной таймзоне
    """
    try:
        # Создаем timezone объект для UTC
        utc_tz = timezone.utc
        
        # Если время не имеет timezone, считаем его UTC
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=utc_tz)
        
        # Конвертируем в локальную таймзону
        local_tz = pytz.timezone(local_timezone)
        local_dt = utc_dt.astimezone(local_tz)
        
        logger.debug(f"🕐 Конвертация времени: {utc_dt} UTC → {local_dt} {local_timezone}")
        return local_dt
        
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации времени {utc_dt}: {e}")
        # В случае ошибки возвращаем исходное время
        return utc_dt
```

### **2. Исправлен Google Calendar API провайдер**

**Файл:** `src/calendar_alternatives.py`

**Изменения:**
- Добавлен параметр `timezone` в конструктор
- Исправлена логика парсинга UTC времени
- Добавлена конвертация в локальную таймзону

```python
class GoogleCalendarAPIProvider(CalendarProvider):
    def __init__(self, credentials_path: str, calendar_id: str, timezone: str = 'Europe/Moscow'):
        self.credentials_path = credentials_path
        self.calendar_id = calendar_id
        self.timezone = timezone
        self.service = None

    # В методе get_events:
    if start.endswith('Z'):
        start_dt = datetime.fromisoformat(start[:-1]).replace(tzinfo=timezone.utc)
    else:
        start_dt = datetime.fromisoformat(start)
    
    # Конвертируем из UTC в локальную таймзону
    start_dt = convert_utc_to_local(start_dt, self.timezone)
```

### **3. Исправлен Web Calendar провайдер (iCal)**

**Файл:** `src/calendar_alternatives.py`

**Изменения:**
- Добавлен параметр `timezone` в конструктор
- Исправлен метод `_parse_ical_datetime` для правильной обработки таймзон
- Добавлена конвертация UTC времени (с 'Z') в локальную таймзону

```python
class WebCalendarProvider(CalendarProvider):
    def __init__(self, calendar_url: str, calendar_type: str = 'ical', timezone: str = 'Europe/Moscow'):
        self.calendar_url = calendar_url
        self.calendar_type = calendar_type
        self.timezone = timezone

    def _parse_ical_datetime(self, dt_string: str) -> datetime:
        # Для UTC времени (с Z на конце)
        if len(dt_string) == 16:  # YYYYMMDDTHHMMSSZ
            dt = datetime.strptime(dt_string, '%Y%m%dT%H%M%SZ')
            # Конвертируем из UTC в локальную таймзону
            return convert_utc_to_local(dt, self.timezone)
```

### **4. Исправлен Notion шаблон**

**Файл:** `src/notion_templates.py`

**Изменения:**
- Убрано дублирование '+03:00' к уже конвертированному времени
- Время теперь отправляется в Notion без таймзоны (Notion использует локальную)

```python
# Было (неправильно):
"start": f"{date_str}T{start_time}:00+03:00"  # +03:00 для московского времени

# Стало (правильно):
"start": f"{date_str}T{start_time}:00"  # Без таймзоны, Notion использует локальную
```

### **5. Обновлен Config Manager**

**Файл:** `src/config_manager.py`

**Изменения:**
- Добавлена передача `timezone` в calendar provider config
- Поддержка timezone для Google Calendar API и web календарей

```python
def get_calendar_provider_config(self, account_type: str = 'personal') -> Dict[str, Any]:
    if account_type == 'personal':
        config = {
            'provider_type': self.config['accounts']['personal']['calendar_provider'],
            'calendar_url': self.config['accounts']['personal']['ical_calendar_url']
        }
        
        # Добавляем timezone для Google Calendar API
        if config['provider_type'] == 'google_api':
            config['credentials_path'] = self.config['accounts']['personal'].get('google_credentials_path', '')
            config['calendar_id'] = self.config['accounts']['personal'].get('google_calendar_id', '')
            config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
        elif config['provider_type'] in ['web_ical', 'web_rss']:
            # Добавляем timezone для web календарей
            config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
        
        return config
```

### **6. Добавлена зависимость pytz**

**Файл:** `requirements.txt`

```txt
pytz==2024.1
```

## 🧪 **Тестирование исправлений**

### **Комплексный тест включает:**

1. **Конвертация UTC → Moscow время**
   - Вход: 10:00 UTC
   - Ожидаемый результат: 13:00 Moscow
   - Статус: ✅ Успешно

2. **Google Calendar провайдер**
   - Создание провайдера с timezone
   - Парсинг UTC времени
   - Конвертация в локальную таймзону
   - Статус: ✅ Успешно

3. **Web Calendar провайдер (iCal)**
   - Парсинг различных форматов дат
   - Обработка UTC времени (с Z)
   - Конвертация в локальную таймзону
   - Статус: ✅ Успешно

4. **Форматирование для Notion**
   - Создание объектов даты без дублирования таймзон
   - Отправка времени в локальной таймзоне
   - Статус: ✅ Успешно

## 📊 **Результаты исправлений**

### **До исправления:**
```
Google Calendar: 10:00 UTC
→ Неправильная обработка: 10:00 UTC
→ Добавляем +03:00: 10:00+03:00
→ Результат: событие в 10:00 (неправильно!)
```

### **После исправления:**
```
Google Calendar: 10:00 UTC
→ Правильная обработка: 10:00 UTC
→ Конвертируем в Moscow: 13:00 Moscow
→ Отправляем в Notion: 13:00 (без таймзоны)
→ Результат: событие в 13:00 (правильно!)
```

## 🔍 **Детали реализации**

### **Логика конвертации времени:**

1. **Google Calendar API:**
   - Получаем время в UTC (с 'Z' на конце)
   - Парсим как UTC время
   - Конвертируем в локальную таймзону из .env
   - Сохраняем в локальной таймзоне

2. **iCal календари:**
   - Определяем формат даты
   - Если есть 'Z' - это UTC время
   - Конвертируем в локальную таймзону
   - Если нет 'Z' - считаем локальным временем

3. **Notion:**
   - Время уже в локальной таймзоне
   - Отправляем без указания таймзоны
   - Notion автоматически использует локальную таймзону

### **Обработка ошибок:**

- При ошибках конвертации возвращаем исходное время
- Логируем все ошибки для диагностики
- Система продолжает работать даже при проблемах с таймзонами

## 🚀 **Развертывание**

### **Требования:**
1. Установить `pytz==2024.1`
2. Убедиться, что в `.env` установлен `TIMEZONE=Europe/Moscow`
3. Перезапустить сервис

### **Проверка:**
1. Создать тестовое событие в Google Calendar
2. Запустить синхронизацию
3. Проверить время в Notion (должно совпадать с календарем)

## 📝 **Заключение**

Исправления таймзон решают основную проблему синхронизации между Google Calendar и Notion:

✅ **Время событий теперь корректно отображается**  
✅ **Убрано дублирование таймзон**  
✅ **Поддержка различных форматов календарей**  
✅ **Настраиваемые таймзоны через .env**  
✅ **Обработка ошибок и логирование**  

Система теперь корректно работает с таймзонами и обеспечивает точную синхронизацию времени между всеми компонентами.

---

*Документация создана: 2025-08-27*  
*Версия: 1.0*  
*Статус: Завершено*
