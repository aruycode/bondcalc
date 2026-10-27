class BondCalcError(Exception):
    """Base class for every error raised by bondcalc."""


class InvalidInputError(BondCalcError):
    """Wrong type, sign, or is outside the allowed set."""


class InvalidDateError(InvalidInputError):
    """Wrong date, or two dates are inconsistent with each other."""


class InvalidRateError(InvalidInputError):
    """A rate is negative, or looks like a percentage."""


class ScheduleError(BondCalcError):
    """A cash flow schedule is empty or does not match the data given with it."""


class ConvergenceError(BondCalcError):
    """The yield solver could not find an answer."""
