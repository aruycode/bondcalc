from bondcalc import (
    BondCalcError,
    cashflow_schedule,
    current_yield,
    macaulay_duration,
    modified_duration,
    price_from_yield,
    yield_to_maturity,
)

FACE_VALUE = 1000
COUPON_RATE = 0.08
ISSUE = "2026-01-01"
MATURITY = "2029-01-01"
FREQUENCY = 2
MARKET_YIELD = 0.10


def heading(text):
    print("\n" + text)
    print("-" * len(text))


def main():
    heading("1. The bond")
    print(
        "{:,} face value, {:.0%} coupon paid {} times a year".format(
            FACE_VALUE, COUPON_RATE, FREQUENCY
        )
    )
    print("issued {}, matures {}".format(ISSUE, MATURITY))

    heading("2. The payments it will make")
    schedule = cashflow_schedule(
        FACE_VALUE, COUPON_RATE, ISSUE, MATURITY, frequency=FREQUENCY
    )
    print(schedule.to_string(index=False))
    print("\nThe last row is much bigger because it repays the principal.")

    heading("3. What it is worth at a {:.0%} yield".format(MARKET_YIELD))
    price = price_from_yield(schedule, MARKET_YIELD)
    print("price = {:,.4f}".format(price))
    print("\nWorked out by hand from the discount factors: 949.2430.")

    heading("4. Sanity check: price it at its own coupon rate")
    print("price at {:.0%} = {:,.4f}".format(COUPON_RATE, price_from_yield(schedule, COUPON_RATE)))
    print("\nA bond yielding exactly its coupon rate sells at face value.")

    heading("5. Now work backward from the price")
    solved = yield_to_maturity(price, schedule)
    print("price handed to the solver : {:,.4f}".format(price))
    print("yield it found             : {:.8f}".format(solved))
    print("yield we started from      : {:.8f}".format(MARKET_YIELD))
    print("\nThe pricer and the solver check each other here.")

    heading("6. How the solver narrows in")
    low, high = -0.99, 1.00
    print("{:>5} {:>11} {:>11} {:>11} {:>13}".format(
        "step", "low", "high", "midpoint", "price at mid"))
    for step in range(1, 11):
        middle = (low + high) / 2
        guess = price_from_yield(schedule, middle)
        print("{:>5} {:>11.6f} {:>11.6f} {:>11.6f} {:>13.4f}".format(
            step, low, high, middle, guess))
        if guess > price:
            low = middle
        else:
            high = middle
    print("\nTarget price is {:,.4f}.".format(price))
    print("Too expensive means the yield is too low, so we raise the floor.")
    print("The gap halves every step, so it always closes in.")

    heading("7. Other yield measures")
    print("current yield = {:.4%}".format(current_yield(FACE_VALUE * COUPON_RATE, price)))
    print("\nCoupon over price. It ignores the gain from redemption at face value.")

    heading("8. Interest rate risk")
    print("macaulay duration = {:.4f} years".format(macaulay_duration(schedule, MARKET_YIELD)))
    print("modified duration = {:.4f}".format(modified_duration(schedule, MARKET_YIELD)))
    print("\nThe bond runs 3 years but its money arrives on average in 2.72.")
    print("A 1 point rise in yield drops the price by about 2.59 percent.")

    heading("9. A property that must always hold")
    zero = cashflow_schedule(FACE_VALUE, 0.0, ISSUE, MATURITY, frequency=FREQUENCY)
    print("duration of a bond with no coupons = {:.4f} years".format(
        macaulay_duration(zero, MARKET_YIELD)
    ))
    print("\nNothing arrives before maturity, so it has to equal 3.0 exactly.")

    heading("10. What happens when the input is wrong")
    mistakes = [
        ("coupon rate typed as 8 instead of 0.08",
         lambda: cashflow_schedule(1000, 8, ISSUE, MATURITY)),
        ("maturity date before the issue date",
         lambda: cashflow_schedule(1000, 0.08, MATURITY, ISSUE)),
        ("coupons paid three times a year",
         lambda: cashflow_schedule(1000, 0.08, ISSUE, MATURITY, frequency=3)),
        ("a date written day first",
         lambda: cashflow_schedule(1000, 0.08, "01/01/2026", MATURITY)),
        ("a price the bond could never trade at",
         lambda: yield_to_maturity(50, schedule)),
    ]
    for description, attempt in mistakes:
        try:
            attempt()
        except BondCalcError as error:
            print("\n{}".format(description))
            print("  {} : {}".format(type(error).__name__, error))

    print(
        "\n\nEvery one of these is caught by name, and every one also answers"
        "\nto BondCalcError, so a caller can catch them one at a time or all"
        "\nat once."
    )


if __name__ == "__main__":
    main()