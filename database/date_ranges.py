import calendar
from datetime import date, datetime

INVALID_RANGE_MESSAGE = "Start date must be before end date."


def parse_date(value):
    """Parse a YYYY-MM-DD string into a date, or return None if it is not valid."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def months_ago(today, months):
    """Return the date `months` calendar months before `today`, clamped to the month's last day."""
    month_index = today.year * 12 + today.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))


def filter_presets(today):
    end = today.isoformat()
    return [
        {"key": "month", "label": "This Month",
         "date_from": today.replace(day=1).isoformat(), "date_to": end},
        {"key": "3m", "label": "Last 3 Months",
         "date_from": months_ago(today, 3).isoformat(), "date_to": end},
        {"key": "6m", "label": "Last 6 Months",
         "date_from": months_ago(today, 6).isoformat(), "date_to": end},
        {"key": "all", "label": "All Time", "date_from": None, "date_to": None},
    ]


def resolve_date_range(raw_from, raw_to):
    """Turn raw query-string values into (date_from, date_to, error).

    Dates are ISO strings or None. A filter needs two valid dates in order;
    anything else falls back to (None, None), with an error message only when
    both dates were valid but reversed.
    """
    parsed_from = parse_date(raw_from)
    parsed_to = parse_date(raw_to)
    if parsed_from is None or parsed_to is None:
        return None, None, None
    if parsed_from > parsed_to:
        return None, None, INVALID_RANGE_MESSAGE
    return parsed_from.isoformat(), parsed_to.isoformat(), None


def active_preset_key(presets, date_from, date_to):
    """Return the key of the preset matching the range, or None for a custom range."""
    return next(
        (p["key"] for p in presets if (p["date_from"], p["date_to"]) == (date_from, date_to)),
        None,
    )
