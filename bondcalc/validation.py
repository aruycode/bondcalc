import datetime as dt
 
from .exceptions import (
    InvalidDateError,
    InvalidInputError,
    InvalidRateError,
)
 
ALLOWED_FREQUENCIES = (1, 2, 4, 12)
 
 
def validate_face_value(face_value):
    """Return the face value as a float, or raise if it is not positive."""
    try:
        value = float(face_value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            "face_value must be a number, got {!r}".format(face_value)
        )
    if value <= 0:
        raise InvalidInputError("face_value must be positive, got {}".format(value))
    return value
 
 
def validate_rate(rate, name="rate", allow_negative=False):
    """Return a rate as a decimal float."""
    try:
        value = float(rate)
    except (TypeError, ValueError):
        raise InvalidRateError("{} must be a number, got {!r}".format(name, rate))
    if value > 1:
        raise InvalidRateError(
            "{} must be a decimal, not a percentage; got {} "
            "(did you mean {}?)".format(name, value, value / 100)
        )
    if value < 0 and not allow_negative:
        raise InvalidRateError("{} must not be negative, got {}".format(name, value))
    return value
 
 
def validate_frequency(frequency):
    """Return the coupon frequency as an int, or raise if it is not supported."""
    try:
        value = int(frequency)
    except (TypeError, ValueError):
        raise InvalidInputError(
            "frequency must be a whole number, got {!r}".format(frequency)
        )
    if value not in ALLOWED_FREQUENCIES:
        raise InvalidInputError(
            "frequency must be one of {}, got {}".format(ALLOWED_FREQUENCIES, value)
        )
    return value


def coerce_date(value, name="date"):
    """Turn the input into a date."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise InvalidDateError(
        "{} must be a date or an ISO string like '2026-06-30', "
        "got {!r}".format(name, value)
    )
 
 
def validate_bond_dates(issue, maturity):
    """Check that the bond matures after it was issued."""
    issue = coerce_date(issue, "issue")
    maturity = coerce_date(maturity, "maturity")
    if maturity <= issue:
        raise InvalidDateError(
            "maturity ({}) must be after issue ({})".format(maturity, issue)
        )
    return issue, maturity
 
 
def validate_positive_int(value, name):
    """Return the value as a positive whole number, or raise."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            "{} must be a whole number, got {!r}".format(name, value)
        )
    if result <= 0:
        raise InvalidInputError("{} must be positive, got {}".format(name, result))
    return result
 