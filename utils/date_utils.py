"""
Working day calculations excluding weekends and public holidays
"""
import json
from datetime import datetime, timedelta
from pathlib import Path


class WorkingDayCalculator:
    """Calculate working days between dates, excluding weekends and holidays"""
    
    def __init__(self):
        self.holidays = self._load_holidays()
    
    def _load_holidays(self) -> set:
        """Load public holidays from JSON file"""
        holidays_path = Path("data/holidays.json")
        if holidays_path.exists():
            with open(holidays_path, 'r') as f:
                data = json.load(f)
                # Flatten all years into a single set of date strings
                all_holidays = []
                for year_holidays in data.values():
                    all_holidays.extend(year_holidays)
                return set(all_holidays)
        return set()
    
    def is_working_day(self, date: datetime) -> bool:
        """Check if a date is a working day (Mon-Fri, not a holiday)"""
        # Check if weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if holiday
        date_str = date.strftime("%Y-%m-%d")
        if date_str in self.holidays:
            return False
        
        return True
    
    def working_days_between(self, start_date: datetime, end_date: datetime) -> int:
        """
        Calculate number of working days between two dates.
        Excludes weekends and public holidays.
        """
        if start_date > end_date:
            return 0
        
        working_days = 0
        current_date = start_date
        
        while current_date < end_date:
            if self.is_working_day(current_date):
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    def add_working_days(self, start_date: datetime, days_to_add: int) -> datetime:
        """Add N working days to a date"""
        current_date = start_date
        days_added = 0
        
        while days_added < days_to_add:
            current_date += timedelta(days=1)
            if self.is_working_day(current_date):
                days_added += 1
        
        return current_date
