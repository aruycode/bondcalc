import datetime as dt

import pandas as pd

from .exceptions import ScheduleError
from .validation import (
    validate_bond_dates,
    validate_face_value,
    validate_frequency,
    validate_rate,
)


def _add_months(date, months):
    """Move a date forward or back by whole months.

    If the day does not exist in the new month, use the last day instead.
    Six months back from 31 August is 28 February, not 31 February.
    """
    total = date.month - 1 + months
    year = date.year + total // 12
    month = total % 12 + 1

    # The day before the first of next month is the last day of this one.
    # That gets February right without a leap year rule of our own.
    next_month = dt.date(year + (month == 12), month % 12 + 1, 1)
    last_day = (next_month - dt.timedelta(days=1)).day

    return dt.date(year, month, min(date.day, last_day))


def coupon_dates(issue, maturity, frequency=2):
    """Return the dates the bond pays a coupon, in order.

    We count backward from maturity, so the last payment always lands
    exactly on the maturity date.
    """
    issue, maturity = validate_bond_dates(issue, maturity)
    frequency = validate_frequency(frequency)

    step = 12 // frequency
    dates = []
    k = 0
    while _add_months(maturity, -step * k) > issue:
        dates.append(_add_months(maturity, -step * k))
        k += 1
    return sorted(dates)


def cashflow_schedule(face_value, coupon_rate, issue, maturity, frequency=2):
    """Build the table of payments the bondholder expects.

    One row per payment: the date, how many periods away it is, the same
    distance in years, the coupon, the principal (0 except on the last
    row), and the two added together.
    """
    face_value = validate_face_value(face_value)
    coupon_rate = validate_rate(coupon_rate, "coupon_rate")
    frequency = validate_frequency(frequency)
    issue, maturity = validate_bond_dates(issue, maturity)

    dates = coupon_dates(issue, maturity, frequency)
    coupon = face_value * coupon_rate / frequency

    rows = []
    for k, date in enumerate(dates, start=1):
        principal = face_value if date == maturity else 0.0
        rows.append(
            {
                "date": date,
                "periods": k,
                "years": k / frequency,
                "coupon": coupon,
                "principal": principal,
                "cashflow": coupon + principal,
            }
        )

    schedule = pd.DataFrame(rows)
    schedule.attrs["frequency"] = frequency
    return schedule


def require_schedule(schedule):
    """Raise unless this really is a table from cashflow_schedule()."""
    if not isinstance(schedule, pd.DataFrame) or schedule.empty:
        raise ScheduleError(
            "expected a schedule from cashflow_schedule(), got {}".format(
                type(schedule).__name__
            )
        )
    if not {"periods", "cashflow"}.issubset(schedule.columns):
        raise ScheduleError(
            "the schedule is missing columns; was it built by "
            "cashflow_schedule()?"
        )
    return schedule
