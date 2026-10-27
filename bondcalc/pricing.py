import numpy as np

from .cashflow import require_schedule
from .exceptions import ScheduleError
from .validation import validate_frequency, validate_rate

# Anything smaller than this counts as zero. Floating point math rarely
# lands on an exact 0.0, so comparing with == 0 would miss it.
ZERO_TOLERANCE = 1e-12


def present_value(cashflows, periods, ytm, frequency=2):
    """Return today's value of a list of future payments.

    This is the one place the discounting happens. Each payment is divided
    by (1 + ytm / frequency) once for every period it is away.
    """
    ytm = validate_rate(ytm, "ytm", allow_negative=True)
    frequency = validate_frequency(frequency)

    cashflows = np.asarray(cashflows, dtype=float)
    periods = np.asarray(periods, dtype=float)
    if cashflows.shape != periods.shape:
        raise ScheduleError(
            "got {} cash flows but {} time points; they must match".format(
                cashflows.size, periods.size
            )
        )

    growth = 1.0 + ytm / frequency
    if growth <= ZERO_TOLERANCE:
        raise ScheduleError("a yield of {} leaves nothing to discount".format(ytm))
    return float(np.sum(cashflows * np.power(growth, -periods)))


def price_from_yield(schedule, ytm, frequency=None):
    """Return the price of the bond in this schedule at the given yield."""
    require_schedule(schedule)
    if frequency is None:
        frequency = schedule.attrs.get("frequency", 2)
    return present_value(
        schedule["cashflow"].to_numpy(),
        schedule["periods"].to_numpy(),
        ytm,
        frequency,
    )