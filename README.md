# Calendar Automation System

Automated calendar system that reads events from OneDrive Excel and generates ICS files for subscription.

## Features

- Reads event data from OneDrive Excel spreadsheet
- Generates separate ICS files for three calendars: Naazira, Hifz, Aalim
- Supports events marked as "ALL" that appear in all calendars
- Uploads ICS files via FTP to web server
- Configurable update schedule
- Comprehensive logging

## Environment Variables

Set these environment variables in your deployment:

```
- ONEDRIVE_RESID
- ONEDRIVE_AUTHKEY
- FTP_HOST
- FTP_PORT
- FTP_USERNAME
- FTP_PASSWORD
- FTP_REMOTE_PATH=/path/to/calendar/directory
- CALENDAR_UPDATE_SCHEDULE_MINS
```

## Excel File Format

Your OneDrive Excel file should have these columns:

- **Event Title** (required)
- **Calendar** (required) - Values: "naazira", "hifz", "aalim", or "ALL"
- **Start Date** (required)
- **Start Time** (optional - leave blank for all-day events)
- **End Date** (optional)
- **End Time** (optional)
- **Description** (optional)
- **Location** (optional)

## Generated Files

The system creates three ICS files:

- `hifz_calendar_naazira.ics` - Mahmoodia-Naazira calendar
- `hifz_calendar_hifz.ics` - Mahmoodia-Hifz calendar
- `hifz_calendar_aalim.ics` - Mahmoodia-Aalim calendar
