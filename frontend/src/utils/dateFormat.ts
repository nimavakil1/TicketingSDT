import { format, toZonedTime } from 'date-fns-tz';

/**
 * Format a date string or Date object to CET timezone
 * @param date - Date string or Date object
 * @param formatString - Format string (default: 'MMM dd, yyyy HH:mm')
 * @returns Formatted date string in CET
 */
export const formatInCET = (date: string | Date, formatString: string = 'MMM dd, yyyy HH:mm'): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const timeZone = 'Europe/Paris'; // CET/CEST
  const zonedDate = toZonedTime(dateObj, timeZone);
  return format(zonedDate, formatString, { timeZone });
};
