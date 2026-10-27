import numpy as np

from .cashflow import require_schedule
from .exceptions import InvalidInputError
from .pricing import ZERO_TOLERANCE
from .validation import validate_rate


def macaulay_duration(schedule, ytm, frequency=None):
    """Return the average time until the money arrives, in years."""
    require_schedule(schedule)
    ytm = validate_rate(ytm, "ytm", allow_negative=True)
    if frequency is None:
        frequency = schedule.attrs.get("frequency", 2)

    periods = schedule["periods"].to_numpy(dtype=float)
    cashflows = schedule["cashflow"].to_numpy(dtype=float)

    # What each payment is worth today.
    present_values = cashflows * np.power(1.0 + ytm / frequency, -periods)
    price = float(np.sum(present_values))

    # Checked against a tiny tolerance rather than == 0, because floating
    # point math usually lands on something like 1e-18 instead of a clean
    # zero, and an exact check would let it slip through.
    if abs(price) < ZERO_TOLERANCE:
        raise InvalidInputError(
            "the bond prices to zero at this yield, so duration is undefined"
        )

    # Average the payment times, weighting each by its present value.
    return float(np.sum(periods / frequency * present_values) / price)


def modified_duration(schedule, ytm, frequency=None):
    """Return the percentage the price falls when the yield rises one point."""
    ytm = validate_rate(ytm, "ytm", allow_negative=True)
    if frequency is None:
        frequency = schedule.attrs.get("frequency", 2)
    return macaulay_duration(schedule, ytm, frequency) / (1 + ytm / frequency)
 