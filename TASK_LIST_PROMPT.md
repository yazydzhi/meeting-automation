# 🤖 AI Assistant Task-List Prompt for Meeting Automation Project

## 🎯 **PROJECT OVERVIEW**
You are an AI coding assistant working on a **Meeting Automation System** - a comprehensive Python-based solution for automating meeting workflows, calendar integration, and document management. This is a **production-ready system** that handles both personal and work accounts with sophisticated automation capabilities.

## 🔒 **CRITICAL SECURITY REQUIREMENTS**

### **NEVER INCLUDE IN CODE, COMMITS, OR DOCUMENTATION:**
- ❌ **Personal Names**: Real first names, last names, patronymics
- ❌ **Email Addresses**: Real email addresses (personal or work)
- ❌ **Local File Paths**: Real paths on user's machine (e.g., `/Users/azg/...`)
- ❌ **Company Names**: Real company names or identifiers
- ❌ **Real Event Data**: Actual meeting titles, descriptions, or calendar events
- ❌ **Contact Information**: Phone numbers, addresses, or personal details
- ❌ **User IDs**: Real user identifiers or account names
- ❌ **Internal URLs**: Real internal company URLs or systems

### **ALWAYS USE PLACEHOLDERS:**
- ✅ **Names**: `your_name`, `user_name`, `employee_name`
- ✅ **Emails**: `user@example.com`, `employee@company.com`
- ✅ **Paths**: `/Users/username/...`, `/path/to/project/...`
- ✅ **Companies**: `Company Name`, `Your Company`, `Example Corp`
- ✅ **Events**: `Meeting Title`, `Event Description`, `Sample Meeting`
- ✅ **URLs**: `https://example.com`, `https://company.com`

## 🏗️ **PROJECT ARCHITECTURE**

### **Core Components:**
```
meeting_automation/
├── meeting_automation_work.py      # Work account automation
├── meeting_automation_personal.py  # Personal account automation  
├── meeting_automation_universal.py # Universal orchestrator
├── src/
│   ├── calendar_alternatives.py    # Calendar providers (iCal, Google API)
│   ├── drive_alternatives.py       # Drive providers (Local, Google Drive)
│   ├── config_manager.py           # Configuration management
│   ├── service_manager.py          # System service management
│   ├── media_processor.py          # Media processing & compression
│   ├── drive_sync.py              # Drive synchronization
│   └── notion_templates.py        # Notion page templates
├── config/
│   ├── personal_exclusions.txt     # Personal event exclusions
│   └── employee_database.py       # Employee database (LOCAL ONLY)
├── tools/                          # Utility scripts
├── tests/                          # Test files
├── scripts/                        # Service control scripts
├── systemd/                        # Linux systemd configs
├── launchd/                        # macOS launchd configs
└── templates/                      # Notion templates
```

### **Key Technologies:**
- **Python 3.8+** with async support
- **Google Calendar API** (personal accounts)
- **iCal/Web Calendar** (work accounts)
- **Google Drive API** (personal accounts)
- **Local File System** (work accounts)
- **Notion API** (documentation & templates)
- **Telegram Bot API** (notifications)
- **FFmpeg** (media processing)
- **System Services** (launchd/systemd)

## 📋 **TASK EXECUTION GUIDELINES**

### **1. Code Development**
- **Always sanitize data** before logging or displaying
- **Use environment variables** for sensitive configuration
- **Implement proper error handling** without exposing internal details
- **Follow Python best practices** (PEP 8, type hints, docstrings)
- **Write comprehensive tests** for all new functionality

### **2. Configuration Management**
- **Never hardcode** personal information
- **Use .env files** for local configuration
- **Provide .env.example** files for public use
- **Validate configuration** at startup
- **Implement fallbacks** for missing configuration

### **3. Data Processing**
- **Sanitize calendar events** before processing
- **Mask personal identifiers** in logs
- **Use generic placeholders** for examples
- **Implement data validation** for all inputs
- **Handle edge cases** gracefully

### **4. Documentation & Commits**
- **Use generic examples** in all documentation
- **Never commit** personal data or real paths
- **Write clear commit messages** without sensitive details
- **Provide setup instructions** for new users
- **Include security considerations** in documentation

## 🚀 **COMMON TASKS & IMPLEMENTATIONS**

### **Calendar Integration**
```python
# ✅ CORRECT - Generic implementation
def process_calendar_event(event_data: dict) -> CalendarEvent:
    """Process calendar event with sanitized data."""
    title = event_data.get('summary', 'Meeting Title')
    attendees = [email for email in event_data.get('attendees', []) if '@' in email]
    
    return CalendarEvent(
        title=title,
        attendees=attendees,
        start=parse_datetime(event_data.get('start')),
        end=parse_datetime(event_data.get('end'))
    )

# ❌ WRONG - Contains real data
def process_calendar_event(event_data: dict) -> CalendarEvent:
    """Process calendar event."""
    title = event_data.get('summary', 'Team Standup')  # Real meeting name
    attendees = ['john.doe@company.com', 'jane.smith@company.com']  # Real emails
```

### **File Path Handling**
```python
# ✅ CORRECT - Configurable paths
def get_media_folder(account_type: str) -> str:
    """Get media folder path from configuration."""
    base_path = os.getenv('MEDIA_BASE_PATH', '/Users/username/Downloads')
    folder_name = os.getenv(f'{account_type.upper()}_FOLDER', 'meetings')
    return os.path.join(base_path, folder_name)

# ❌ WRONG - Hardcoded real paths
def get_media_folder(account_type: str) -> str:
    """Get media folder path."""
    if account_type == 'work':
        return '/Users/azg/Downloads/02 - v.yazydzhi@cian.ru'  # Real path
    else:
        return '/Users/azg/Downloads/01 - yazydzhi@gmail.com'  # Real path
```

### **Employee Database**
```python
# ✅ CORRECT - Generic employee handling
def get_employee_name(email: str) -> str:
    """Get employee name from database."""
    if email in EMPLOYEE_DATABASE:
        surname, name, patronymic = EMPLOYEE_DATABASE[email]
        return f"{surname} {name} {patronymic}".strip()
    return email

# ❌ WRONG - Contains real names
EMPLOYEE_DATABASE = {
    'john.doe@company.com': ('Doe', 'John', ''),
    'jane.smith@company.com': ('Smith', 'Jane', 'Marie')
}
```

## 🔧 **DEVELOPMENT WORKFLOW**

### **Before Starting Work:**
1. **Review security requirements** above
2. **Check existing code** for personal data patterns
3. **Plan data sanitization** strategy
4. **Prepare generic examples** for documentation

### **During Development:**
1. **Use placeholder data** for all examples
2. **Implement proper validation** for inputs
3. **Add comprehensive logging** without sensitive data
4. **Write tests** with mock data

### **Before Committing:**
1. **Review all changes** for personal data
2. **Check commit message** for sensitive information
3. **Validate configuration** examples
4. **Test with generic data**

### **Code Review Checklist:**
- [ ] No personal names or emails in code
- [ ] No hardcoded local paths
- [ ] No real company identifiers
- [ ] No actual event data
- [ ] All examples use placeholders
- [ ] Configuration is externalized
- [ ] Error messages are generic
- [ ] Logs don't contain sensitive data

## 📚 **RESOURCE PATTERNS**

### **Safe Placeholder Examples:**
```python
# Configuration
GOOGLE_CREDENTIALS=creds/client_secret.json
PERSONAL_CALENDAR_ID=user@example.com
NOTION_TOKEN=your_notion_token_here

# File paths
MEDIA_BASE_PATH=/Users/username/Downloads
WORK_FOLDER=work_meetings
PERSONAL_FOLDER=personal_meetings

# Company information
COMPANY_NAME=Your Company
DOMAIN=example.com
```

### **Generic Event Examples:**
```python
# Meeting titles
"Team Standup"
"Project Review"
"Client Meeting"
"Daily Sync"

# Event descriptions
"Regular team meeting to discuss progress"
"Review of project milestones and next steps"
"Meeting with client to discuss requirements"
```

## 🎯 **SPECIFIC PROJECT TASKS**

### **Calendar Integration Tasks:**
- Implement new calendar provider
- Add recurring event support (RRULE)
- Handle timezone conversions
- Process calendar attachments

### **Media Processing Tasks:**
- Add new video codec support
- Implement audio transcription
- Optimize compression algorithms
- Add batch processing capabilities

### **Notion Integration Tasks:**
- Create new page templates
- Add property mapping
- Implement page updates
- Handle API rate limits

### **Service Management Tasks:**
- Add new service configurations
- Implement health monitoring
- Add performance metrics
- Handle service failures

## 🚨 **EMERGENCY PROCEDURES**

### **If Personal Data is Accidentally Committed:**
1. **Immediately stop** any further commits
2. **Use git filter-branch** to remove sensitive data
3. **Force push** cleaned history
4. **Review all branches** for contamination
5. **Update .gitignore** to prevent recurrence
6. **Document incident** for future reference

### **If Configuration is Exposed:**
1. **Rotate all tokens** and credentials
2. **Update environment files** with new values
3. **Review access logs** for unauthorized usage
4. **Implement additional security** measures
5. **Notify stakeholders** if necessary

## 📖 **LEARNING RESOURCES**

### **Security Best Practices:**
- OWASP Guidelines for Python
- Git Security Best Practices
- Data Privacy Regulations (GDPR, CCPA)
- Secure Configuration Management

### **Python Development:**
- PEP 8 Style Guide
- Python Type Hints
- Async Programming Patterns
- Testing Best Practices

### **System Integration:**
- Google API Best Practices
- Notion API Documentation
- FFmpeg Command Line Usage
- System Service Management

---

**Remember**: This project handles sensitive meeting data and personal information. Always prioritize security, privacy, and data protection in every line of code, commit, and documentation you create or modify.

**Motto**: "Secure by Design, Private by Default, Generic by Example"
