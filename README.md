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
- INSTITUTION
- CALENDAR_CATEGORIES
- FTP_HOST
- FTP_PORT
- FTP_USERNAME
- FTP_PASSWORD
- FTP_REMOTE_PATH=/path/to/calendar/directory
```

## Excel File Format

Your OneDrive Excel file should have these columns:

- **Event Title** (required)
- **Calendar** (required) - Values: MUST MATCH CALENDAR_CATEGORIES ENV VAR
- **Start Date** (required)
- **Start Time** (optional - leave blank for all-day events)
- **End Date** (optional)
- **End Time** (optional)
- **Description** (optional)
- **Location** (optional)

## Generated Files

The system creates ICS files named:

- `{$INSTITUTION}-{CALENDAR_CATEGORIES}.ics` - eg ExampleInstitution-Events.ics
