import ftplib
import hashlib
import io
import logging
import os
import uuid
import validators
from datetime import datetime, timedelta

import pandas as pd
from icalendar import Calendar, Event, Alarm, vCalAddress

if os.getenv("DEBUG_LOCAL"):
    from dotenv import load_dotenv
    load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CalendarUpdater:
    """Handles calendar updates from shareable spreadsheet to ICS files via FTP."""

    def __init__(self):
        """Initialize with environment variables."""
        self.organisation = os.getenv('ORGANISATION')
        self.organiser = os.getenv('ORGANISER')
        self.categories = os.getenv('CALENDAR_CATEGORIES', 'Events').split(',')

        self.spreadsheet_url = os.getenv('SPREADSHEET_URL')

        self.ftp_host = os.getenv('FTP_HOST')
        self.ftp_port = int(os.getenv('FTP_PORT', '21'))
        self.ftp_username = os.getenv('FTP_USERNAME')
        self.ftp_password = os.getenv('FTP_PASSWORD')
        self.ftp_remote_path = os.getenv('FTP_REMOTE_PATH', '/')

        self._validate_credentials()

    def _validate_credentials(self):
        """Validate required environment variables."""
        if not self.spreadsheet_url:
            raise ValueError(
                'Spreadsheet URL not found in environment variables'
            )

        if (
            not self.organisation
            or not self.organiser
            or not validators.email(self.organiser)
        ):
            raise ValueError(
                'Organisation or Organiser not set in environment variables'
            )

        if not all([self.ftp_host, self.ftp_username, self.ftp_password]):
            raise ValueError(
                'FTP credentials not found in environment variables'
            )

    def read_spreadsheet(self):
        """Read Spreadsheet file using public share link access method."""
        try:
            if not validators.url(self.spreadsheet_url):
                raise ValueError(
                    f"Invalid spreadsheet URL: {self.spreadsheet_url}"
                )
            logger.info(f'Reading spreadsheet file from {self.spreadsheet_url[:40]}')
            df = pd.read_csv(self.spreadsheet_url,
                             parse_dates=['Start Date', 'End Date'],
                             date_format="%d/%m/%Y")
            logger.info(f'Successfully read {len(df)} events from File')
            return df
        except Exception as error:
            logger.error(f'Error reading spreadsheet file: {error}')
            return None

    def _create_calendar_event(self, row):
        # logger.info("Create an ICS event from a row.")
        event = Event()
        self._set_event_organiser(event)
        event.add('summary', str(row.get('Event Title', 'Untitled Event')))

        if pd.notna(row.get('Description')):
            description = (
                str(row.get('Description', ''))
                .replace('\r\n', '\\n')
                .replace('\n', '\\n')
            )
            event.add('description', description)

        if pd.notna(row.get('Location')):
            event.add('location', str(row.get('Location')))

        if pd.notna(row.get('URL')):
            url = row.get('URL')
            if url and validators.url(url):
                event.add('url', url)
            else:
                logger.warning(f"Invalid URL skipped: {url}")

        self._set_event_datetime(event, row)
        self._add_event_alarm(event)
        self._set_event_uid(event, row)

        event.add('dtstamp', datetime.now())
        return event

    def _set_event_organiser(self, event):
        organiser = vCalAddress(f'MAILTO:{self.organiser}')
        organiser.name = self.organisation
        event.add('organizer', organiser)

    def _set_event_datetime(self, event, row):
        # logger.info("Set event start and end datetime.")
        start_date = row.get('Start Date')
        start_time = row.get('Start Time')
        end_date = row.get('End Date', start_date)
        end_time = row.get('End Time')

        try:
            if pd.isna(start_time) or start_time == '':
                self._set_all_day_event(event, start_date, end_date)
            else:
                self._set_timed_event(event, start_date, start_time,
                                      end_date, end_time)
        except Exception as error:
            logger.warning(
                (
                    f"Error parsing dates for event "
                    f"'{event.get('summary', 'Unknown')}': {error}"
                )
            )
            self._set_default_event_time(event)

    def _set_all_day_event(self, event, start_date, end_date):
        event['dtstart'] = pd.to_datetime(start_date).date()
        if pd.notna(end_date):
            event['dtend'] = (
                pd.to_datetime(end_date).date() + timedelta(days=1)
            )
        else:
            event['dtend'] = (
                pd.to_datetime(start_date).date() + timedelta(days=1)
            )
        event['X-MICROSOFT-CDO-ALLDAYEVENT'] = 'TRUE'

    def _set_timed_event(self, event, start_date, start_time,
                         end_date, end_time):
        """Set timed event dates."""
        start_datetime = pd.to_datetime(f'{start_date} {start_time}')
        if pd.notna(end_time) and pd.notna(end_date):
            end_datetime = pd.to_datetime(f'{end_date} {end_time}')
        else:
            end_datetime = start_datetime + timedelta(hours=2)

        event['dtstart'] = start_datetime
        event['dtend'] = end_datetime

    def _set_default_event_time(self, event):
        """Set default event time if parsing fails."""
        event['dtstart'] = datetime.now().date()
        event['dtend'] = datetime.now().date() + timedelta(days=1)
        event['X-MICROSOFT-CDO-ALLDAYEVENT'] = 'TRUE'

    def _add_event_alarm(self, event):
        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', event.get('summary', ''))
        alarm.add('trigger', timedelta(days=-1))
        event.add_component(alarm)

    def _set_event_uid(self, event, row):
        uid_components = [
            str(row.get('Event Title', '')),
            str(row.get('Start Date', '')),
            str(row.get('Start Time', '')),
            str(row.get('End Date', '')),
            str(row.get('End Time', '')),
            str(row.get('Calendar', '')),
            str(row.get('Location', '')),
            str(row.get('Description', ''))
        ]

        uid_string = '|'.join(uid_components)
        uid_hash = hashlib.sha256(uid_string.encode('utf-8')).hexdigest()

        uid = (
            f"{uid_hash[:8]}-{uid_hash[8:12]}-{uid_hash[12:16]}-"
            f"{uid_hash[16:20]}-{uid_hash[20:32]}"
        )

        event.add('uid', f"{uid}@{self.organiser.lower()}")

    def generate_ics_files(self, df):
        """Generate separate ICS files for each calendar category."""
        calendars = {}

        for category in self.categories:
            logger.info(f'Processing calendar: {category}')
            calendar_events = self._filter_events_by_category(df, category)

            if calendar_events.empty:
                logger.warning(f'No events found for category: {category}')
                continue

            cal = self._create_calendar(category)
            self._add_events_to_calendar(cal, calendar_events)

            calendars[category] = cal

        return calendars

    def _filter_events_by_category(self, df, category):
        """Filter events for specific category or ALL."""
        return df[
            (df['Calendar'].str.lower() == category.lower()) |
            (df['Calendar'].str.upper() == 'ALL')
        ]

    def _create_calendar(self, category):
        # logger.info("Create calendar with proper metadata.")
        cal = Calendar()
        cal.uid = str(uuid.uuid4())
        cal.add('prodid', f'-//{self.organisation}//EN')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', f'{self.organisation} - {category.title()}')
        cal.add('REFRESH-INTERVAL;VALUE=DURATION', 'P1H')
        return cal

    def _add_events_to_calendar(self, cal, calendar_events):
        for _, row in calendar_events.iterrows():
            if pd.notna(row.get('Event Title')):
                event = self._create_calendar_event(row)
                cal.add_component(event)

        logger.info(f"Processed {len(cal.events)} events")

    def upload_ics_files(self, calendars):
        """Upload ICS files to FTP server."""
        if os.getenv('DEBUG_LOCAL'):
            logger.info('Skipping FTP upload in local debug mode')
            for category, cal in calendars.items():
                filename = (
                    f"{self.organisation.lower().replace(' ', '-')}-"
                    f"{category.lower().replace(' ', '-')}.ics"
                )
                with open(filename, 'wb') as f:
                    f.write(cal.to_ical())
                logger.info(f'Local file created: {filename}')
            return

        ftp = None

        try:
            ftp = self._connect_to_ftp()
            self._upload_files_to_ftp(ftp, calendars)
        except Exception as error:
            logger.error(f'FTP connection error: {error}')
        finally:
            self._close_ftp_connection(ftp)

    def _connect_to_ftp(self):
        """Establish FTP connection."""
        logger.info(f'Connecting to FTP server: {self.ftp_host}:{self.ftp_port}')
        ftp = ftplib.FTP()
        ftp.connect(self.ftp_host, self.ftp_port)
        ftp.login(self.ftp_username, self.ftp_password)
        ftp.cwd(self.ftp_remote_path)
        return ftp

    def _upload_files_to_ftp(self, ftp, calendars):
        """Upload calendar files via FTP."""
        for category, cal in calendars.items():
            try:
                filename = (
                    f"{self.organisation.lower().replace(' ', '-')}-"
                    f"{category.lower().replace(' ', '-')}.ics"
                )
                logger.info(f'Preparing to upload {filename}')
                ics_content = cal.to_ical()
                file_obj = io.BytesIO(ics_content)
                file_obj.seek(0)
                ftp.storbinary(f'STOR {filename}', file_obj)
                logger.info(f'Successfully uploaded {filename}')
            except Exception as error:
                logger.error(f'Error uploading {category}: {error}')

    def _close_ftp_connection(self, ftp):
        """Close FTP connection safely."""
        if ftp:
            try:
                ftp.quit()
            except Exception:
                ftp.close()
        logger.info('FTP connection closed')

    def update_calendars(self):
        """Main function to update all calendars."""
        logger.info('Starting calendar update process...')

        df = self.read_spreadsheet()
        if df is None:
            logger.error('Failed to read spreadsheet data, skipping update')
            return

        if not self._validate_dataframe(df):
            return

        calendars = self.generate_ics_files(df)
        self.upload_ics_files(calendars)

        logger.info('Calendar update process completed')

    def _validate_dataframe(self, df):
        """Validate DataFrame has required columns."""
        required_columns = ['Event Title', 'Calendar', 'Start Date']
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]
        if missing_columns:
            logger.error(f'Missing required columns: {missing_columns}')
            return False
        return True


def main():
    try:
        updater = CalendarUpdater()
        updater.update_calendars()
    except KeyboardInterrupt:
        logger.info('Calendar updater stopped by user')
    except Exception as error:
        logger.error(f'Fatal error: {error}')


if __name__ == '__main__':
    main()
