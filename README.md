# Calendar Automation System

Automated calendar system that reads events from spreadsheets and generates ICS files for subscription via iCAL.

## Features

- Reads event data from a spreadsheet
- Generates separate ICS files for any given category (default is Events)
- Supports events marked as "ALL" that appear in all calendars
- Uploads ICS files via FTP to web server
- Configurable update schedule via GitHub actions

## Environment Variables

Set these environment variables in your deployment:

```
- ORGANISATION (required)
- ORGANISER (required valid email address)
- CALENDAR_CATEGORIES (required comma separated list)
- FTP_HOST (required)
- FTP_PORT (optional - default 21)
- FTP_USERNAME (required)
- FTP_PASSWORD (required)
- FTP_REMOTE_PATH=/path/to/calendar/directory (optional - default '/')
- SPREADSHEET_URL (required - public URL to csv file)
- DEBUG_LOCAL (optional)
```

## CSV File structure

Your csv file should have these columns:

- **Event Title** (required)
- **Calendar** (required) - Values: MUST MATCH CALENDAR_CATEGORIES ENV VAR
- **Start Date** (required)
- **Start Time** (optional - leave blank for all-day events)
- **End Date** (optional)
- **End Time** (optional)
- **Description** (optional)
- **URL** (optional)
- **Location** (optional)

## Generated Files

The system creates ICS files named:

- `{$INSTITUTION}-{CALENDAR_CATEGORIES}.ics` - eg ExampleInstitution-Events.ics
