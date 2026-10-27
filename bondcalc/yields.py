from .cashflow import require_schedule
from .exceptions import ConvergenceError, InvalidInputError
from .pricing import price_from_yield

# The widest range the solver will search. The top is 1, not something
# bigger, because validate_rate treats any rate above 1 as a percentage
# typed by mistake. The solver follows the same rule as the rest of the
# package instead of being allowed to break it.
LOW_YIELD = -0.99
HIGH_YIELD = 1.00


def yield_to_maturity(price, schedule, frequency=None, tolerance=1e-10, max_steps=200):
    """Return the yield that makes the calculated price match the given price."""
    require_schedule(schedule)
    if frequency is None:
        frequency = schedule.attrs.get("frequency", 2)

    try:
        target = float(price)
    except (TypeError, ValueError):
        raise InvalidInputError("price must be a number, got {!r}".format(price))
    if target <= 0:
        raise InvalidInputError("price must be positive, got {}".format(target))

    low, high = LOW_YIELD, HIGH_YIELD
    highest = price_from_yield(schedule, low, frequency)
    lowest = price_from_yield(schedule, high, frequency)

    # A price outside this range is not one the bond can ever reach, so the
    # input is wrong rather than the method having failed.
    if not lowest <= target <= highest:
        raise ConvergenceError(
            "a price of {:.4f} is outside the range this bond can reach "
            "({:.4f} down to {:.4f}); check the price and the bond's "
            "terms".format(target, highest, lowest)
        )

    try:
        for _ in range(max_steps):
            middle = (low + high) / 2.0
            guess = price_from_yield(schedule, middle, frequency)
            if abs(guess - target) < tolerance:
                return middle
            if guess > target:
                low = middle
            else:
                high = middle
    except ZeroDivisionError as error:
        # Turn a bare arithmetic failure into something that names the bond
        # problem instead of the line of code that broke.
        raise ConvergenceError("the solver hit a division by zero: {}".format(error))

    raise ConvergenceError(
        "no yield found after {} steps; the closest was {:.8f}, which prices "
        "the bond at {:.4f} against a target of {:.4f}".format(
            max_steps, middle, guess, target
        )
    )


def current_yield(annual_coupon, price):
    """Return the annual coupon as a share of the price.

    A rough measure. It ignores any gain or loss from getting the face
    value back at maturity.
    """
    try:
        coupon = float(annual_coupon)
        value = float(price)
    except (TypeError, ValueError):
        raise InvalidInputError("annual_coupon and price must both be numbers")
    if value <= 0:
        raise InvalidInputError("price must be positive, got {}".format(value))
    return coupon / value