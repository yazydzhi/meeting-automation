# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Meeting Automation System - A comprehensive automation system that processes meetings from multiple accounts (personal/work) through a single unified configuration. The system handles calendar processing, media file compression/transcription, AI analysis through OpenAI, and integration with Notion for structured meeting notes.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp .env.example .env
# Edit .env file with your credentials
```

### Main Application Commands
```bash
# Universal script (main entry point)
python meeting_automation_universal.py media --account both
python meeting_automation_universal.py calendar --account personal
python meeting_automation_universal.py all --verbose

# Process single video file with full pipeline
python tools/auto_process_and_analyze.py "/path/to/video.mp4" \
  --title "Meeting Title" \
  --date "2025-08-21" \
  --config .env \
  --quality medium

# Process video files (compression + transcription)
python tools/process_video_full_flow.py "/path/to/video.mp4" \
  --quality medium \
  --codec h264

# Process MP3 files in folders
python tools/process_mp3_folders.py \
  --folders 5 \
  --output md \
  --cleanup
```

### System Service Management
```bash
# Load/start the LaunchAgent service
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Unload/stop the service
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Check service status
launchctl list | grep meeting

# Monitor service with built-in script
python ./scripts/monitor_service.py

# Control service with helper script
./scripts/service_control.sh status
./scripts/service_control.sh start
./scripts/service_control.sh stop
./scripts/service_control.sh restart
./scripts/service_control.sh logs [lines]
```

### Testing & Diagnostics
```bash
# Quick API check (all services)
python tests/scripts/test_quick_api_check.py

# Comprehensive Google APIs test
python tests/scripts/test_all_google_apis.py

# Detailed Google Drive testing
python tests/scripts/test_google_drive_detailed.py

# Test configuration only
python meeting_automation_universal.py test --config-only

# Check configuration programmatically
python -c "from src.config_manager import ConfigManager; config = ConfigManager(); print(config.get_config_summary())"
```

### Monitoring & Logs
```bash
# View real-time logs
tail -f logs/service.log
tail -f logs/universal_automation.log
tail -f logs/personal_automation.log
tail -f logs/work_automation.log

# Check for hanging processes
ps aux | grep meeting
ps aux | grep ffmpeg

# Kill hanging ffmpeg processes
python -c "from src.service_manager import MeetingAutomationService; service = MeetingAutomationService(); service._kill_hanging_ffmpeg_processes()"
```

### Single Test Commands
```bash
# Test audio processing
python meeting_automation_work.py media --quality medium --verbose

# Test specific account
python meeting_automation_personal.py prepare
python meeting_automation_work.py prepare

# Test media processing for single file
python -m pytest tests/test_media_processing.py::test_video_compression -v

# Test notion integration
python -m pytest tests/test_notion_work.py -v
```

## Architecture Overview

### Core Components

The system is built around a **unified configuration approach** where both personal and work accounts share common services (Telegram, Notion, OpenAI) but maintain separate calendar and drive configurations.

**Key Architecture Patterns:**
- **ConfigManager**: Central configuration handling with account-specific overrides
- **Universal Script**: Single entry point that processes multiple accounts based on ACCOUNT_TYPE
- **Service-Based Processing**: Separate processors for calendar, drive, media, notion, and transcription
- **Provider Abstraction**: Support for multiple calendar (iCal, Google API) and drive (local folders, Google Drive API) providers

### File Processing Pipeline

1. **Video Input** → **Compression** (ffmpeg with configurable codecs)
2. **Compressed Video** → **Audio Extraction** (MP3 format)
3. **Audio File** → **Transcription** (Whisper local/OpenAI API)
4. **Transcript** → **AI Analysis** (OpenAI GPT-4o-mini)
5. **Analysis Results** → **Notion Integration** (structured meeting notes)

### Account Configuration System

The system supports four account modes via `ACCOUNT_TYPE`:
- `personal`: Only personal account
- `work`: Only work account  
- `both`: Both accounts (default)
- `none`: Disable all accounts

Each account type has independent:
- Calendar providers (Google Calendar API, web iCal)
- Drive providers (Google Drive API, local folders)
- Local root directories for file processing

### Service Management Architecture

**Background Service** (macOS LaunchAgent):
- Runs every 5 minutes for calendar processing
- Runs every 30 minutes for media processing
- Automatic restart on failures
- Configurable intervals via plist file

**Service Components:**
- `service_manager.py`: Main service daemon
- `monitor_service.py`: Service health monitoring
- `service_control.sh`: Service control wrapper script

## Important Development Notes

### Configuration File Structure
The system uses a unified `.env` file for all configuration. Account-specific settings use prefixes:
- Personal: `PERSONAL_CALENDAR_ID`, `PERSONAL_LOCAL_DRIVE_ROOT`
- Work: `WORK_CALENDAR_ID`, `WORK_LOCAL_DRIVE_ROOT`
- Shared: `TELEGRAM_BOT_TOKEN`, `NOTION_TOKEN`, `OPENAI_API_KEY`

### Media Processing Constraints
- Video compression uses ffmpeg with configurable quality settings
- Supported codecs: h264, h265
- Audio processing includes noise reduction and normalization
- Transcription supports both local Whisper and OpenAI API
- Processing timeout: 30 minutes (configurable)

### API Integration Patterns
- **Notion**: Uses structured templates for meeting note creation
- **OpenAI**: Configurable models and parameters for transcript analysis
- **Google APIs**: Supports both OAuth credentials and service account patterns
- **Telegram**: Used for notifications and status reports

### Debugging Approaches
The codebase includes comprehensive testing infrastructure:
- Quick API health checks (`test_quick_api_check.py`)
- Detailed Google API diagnostics (`test_all_google_apis.py`)
- Google Drive specific testing (`test_google_drive_detailed.py`)
- Test reports are generated in `tests/reports/`

### Error Handling Strategy
- All processors implement graceful degradation
- Media processing continues even if individual files fail
- Service automatically retries failed operations
- Comprehensive logging to separate log files per account type

## Common Integration Points

When extending the system:

1. **New Account Types**: Extend `ConfigManager.get_*_config()` methods
2. **New Media Formats**: Modify `MediaProcessor` and `AudioProcessor`
3. **New Calendar Providers**: Implement in `calendar_alternatives.py`
4. **New Drive Providers**: Implement in `drive_alternatives.py`
5. **New Analysis Models**: Configure via `OPENAI_ANALYSIS_MODEL` and `TranscriptAnalyzer`

The system's modular design allows for easy extension while maintaining the unified configuration approach.
