import datetime
import unittest

from bondcalc import cashflow, exceptions, pricing, risk, validation, yields

HAND_CALCULATED_PRICE = 949.24


def sample_bond(coupon_rate=0.08, maturity="2029-01-01", frequency=2):
    """Build the bond the tests are written around."""
    return cashflow.cashflow_schedule(
        1000, coupon_rate, "2026-01-01", maturity, frequency=frequency
    )


# ---------------------------------------------------------------- validation


class TestFaceValue(unittest.TestCase):
    def test_accepts_a_positive_number(self):
        self.assertEqual(validation.validate_face_value(1000), 1000.0)

    def test_rejects_zero_and_negatives(self):
        for bad in (0, -1, -1000):
            with self.assertRaises(exceptions.InvalidInputError):
                validation.validate_face_value(bad)

    def test_rejects_text(self):
        with self.assertRaises(exceptions.InvalidInputError):
            validation.validate_face_value("one thousand")


class TestRate(unittest.TestCase):
    def test_accepts_a_decimal(self):
        self.assertEqual(validation.validate_rate(0.05, "coupon_rate"), 0.05)

    def test_treats_a_number_above_one_as_a_percentage_mistake(self):
        with self.assertRaises(exceptions.InvalidRateError) as caught:
            validation.validate_rate(5, "coupon_rate")
        # The message has to suggest the fix, not just report the problem.
        self.assertIn("0.05", str(caught.exception))

    def test_rejects_negatives_unless_allowed(self):
        with self.assertRaises(exceptions.InvalidRateError):
            validation.validate_rate(-0.01, "coupon_rate")
        self.assertEqual(
            validation.validate_rate(-0.01, "ytm", allow_negative=True), -0.01
        )


class TestFrequency(unittest.TestCase):
    def test_accepts_the_supported_frequencies(self):
        for good in validation.ALLOWED_FREQUENCIES:
            self.assertEqual(validation.validate_frequency(good), good)

    def test_rejects_anything_else(self):
        for bad in (0, 3, 5, -2):
            with self.assertRaises(exceptions.InvalidInputError):
                validation.validate_frequency(bad)

    def test_message_lists_the_valid_choices(self):
        with self.assertRaises(exceptions.InvalidInputError) as caught:
            validation.validate_frequency(3)
        self.assertIn("(1, 2, 4, 12)", str(caught.exception))


class TestDates(unittest.TestCase):
    def test_reads_an_iso_string(self):
        self.assertEqual(
            validation.coerce_date("2026-06-30"), datetime.date(2026, 6, 30)
        )

    def test_accepts_a_date_and_a_datetime(self):
        self.assertEqual(
            validation.coerce_date(datetime.date(2026, 6, 30)),
            datetime.date(2026, 6, 30),
        )
        self.assertEqual(
            validation.coerce_date(datetime.datetime(2026, 6, 30, 15, 0)),
            datetime.date(2026, 6, 30),
        )

    def test_rejects_an_ambiguous_format_rather_than_guessing(self):
        with self.assertRaises(exceptions.InvalidDateError):
            validation.coerce_date("30/06/2026")

    def test_maturity_must_come_after_issue(self):
        with self.assertRaises(exceptions.InvalidDateError):
            validation.validate_bond_dates("2029-01-01", "2026-01-01")


class TestErrorHierarchy(unittest.TestCase):
    def test_every_error_can_be_caught_as_one_type(self):
        errors = [
            exceptions.InvalidInputError,
            exceptions.InvalidDateError,
            exceptions.InvalidRateError,
            exceptions.ScheduleError,
            exceptions.ConvergenceError,
        ]
        for error in errors:
            self.assertTrue(issubclass(error, exceptions.BondCalcError))

    def test_date_and_rate_errors_are_kinds_of_input_error(self):
        self.assertTrue(
            issubclass(exceptions.InvalidDateError, exceptions.InvalidInputError)
        )
        self.assertTrue(
            issubclass(exceptions.InvalidRateError, exceptions.InvalidInputError)
        )


# ------------------------------------------------------------------ cashflow


class TestCouponDates(unittest.TestCase):
    def test_last_date_is_maturity(self):
        dates = cashflow.coupon_dates("2026-01-01", "2029-01-01", frequency=2)
        self.assertEqual(dates[-1], datetime.date(2029, 1, 1))

    def test_count_matches_years_times_frequency(self):
        for frequency, expected in [(1, 3), (2, 6), (4, 12), (12, 36)]:
            dates = cashflow.coupon_dates("2026-01-01", "2029-01-01", frequency)
            self.assertEqual(len(dates), expected)

    def test_dates_come_out_in_order(self):
        dates = cashflow.coupon_dates("2026-01-01", "2031-01-01", frequency=4)
        self.assertEqual(dates, sorted(dates))

    def test_month_end_does_not_produce_an_impossible_date(self):
        # Six months back from 31 August must land on 28 February, not on
        # 31 February.
        dates = cashflow.coupon_dates("2025-08-31", "2026-08-31", frequency=2)
        self.assertEqual(dates[0], datetime.date(2026, 2, 28))

    def test_month_end_handles_a_leap_year(self):
        dates = cashflow.coupon_dates("2023-08-31", "2024-08-31", frequency=2)
        self.assertEqual(dates[0], datetime.date(2024, 2, 29))


class TestSchedule(unittest.TestCase):
    def setUp(self):
        self.schedule = sample_bond()

    def test_one_row_for_each_payment(self):
        self.assertEqual(len(self.schedule), 6)

    def test_only_the_last_row_repays_principal(self):
        principal = self.schedule["principal"].tolist()
        self.assertEqual(principal[:-1], [0.0] * 5)
        self.assertEqual(principal[-1], 1000.0)

    def test_coupon_is_the_annual_amount_split_by_frequency(self):
        self.assertAlmostEqual(self.schedule["coupon"].iloc[0], 40.0)

    def test_cashflow_is_coupon_plus_principal(self):
        total = self.schedule["coupon"] + self.schedule["principal"]
        self.assertTrue((total == self.schedule["cashflow"]).all())

    def test_periods_count_up_from_one(self):
        self.assertEqual(self.schedule["periods"].tolist(), [1, 2, 3, 4, 5, 6])

    def test_years_is_periods_divided_by_frequency(self):
        ratio = self.schedule["periods"] / self.schedule["years"]
        self.assertTrue((abs(ratio - 2.0) < 1e-12).all())

    def test_a_bond_with_no_coupons_pays_only_at_maturity(self):
        zero = sample_bond(coupon_rate=0.0)
        self.assertEqual(zero["cashflow"].tolist()[:-1], [0.0] * 5)
        self.assertAlmostEqual(zero["cashflow"].iloc[-1], 1000.0)


class TestScheduleErrors(unittest.TestCase):
    def test_rejects_a_percentage_coupon(self):
        with self.assertRaises(exceptions.InvalidRateError):
            cashflow.cashflow_schedule(1000, 8, "2026-01-01", "2029-01-01")

    def test_rejects_a_negative_face_value(self):
        with self.assertRaises(exceptions.InvalidInputError):
            cashflow.cashflow_schedule(-1000, 0.08, "2026-01-01", "2029-01-01")

    def test_rejects_maturity_before_issue(self):
        with self.assertRaises(exceptions.InvalidDateError):
            cashflow.cashflow_schedule(1000, 0.08, "2029-01-01", "2026-01-01")

    def test_rejects_an_unsupported_frequency(self):
        with self.assertRaises(exceptions.InvalidInputError):
            cashflow.cashflow_schedule(
                1000, 0.08, "2026-01-01", "2029-01-01", frequency=3
            )

    def test_rejects_something_that_is_not_a_schedule(self):
        with self.assertRaises(exceptions.ScheduleError):
            cashflow.require_schedule([40, 40, 1040])


# ------------------------------------------------------------------- pricing


class TestPriceAgainstHandCalculation(unittest.TestCase):
    def setUp(self):
        self.schedule = sample_bond()

    def test_matches_the_hand_calculated_price(self):
        price = pricing.price_from_yield(self.schedule, 0.10)
        self.assertAlmostEqual(price, HAND_CALCULATED_PRICE, places=2)

    def test_a_bond_priced_at_its_coupon_rate_sells_at_par(self):
        price = pricing.price_from_yield(self.schedule, 0.08)
        self.assertAlmostEqual(price, 1000.0, places=6)

    def test_a_yield_below_the_coupon_gives_a_premium(self):
        self.assertGreater(pricing.price_from_yield(self.schedule, 0.06), 1000.0)

    def test_a_yield_above_the_coupon_gives_a_discount(self):
        self.assertLess(pricing.price_from_yield(self.schedule, 0.12), 1000.0)

    def test_price_falls_as_yield_rises(self):
        prices = [
            pricing.price_from_yield(self.schedule, y)
            for y in (0.02, 0.04, 0.06, 0.08, 0.10, 0.12)
        ]
        self.assertEqual(prices, sorted(prices, reverse=True))


class TestPresentValue(unittest.TestCase):
    def test_one_payment_one_period_away(self):
        self.assertAlmostEqual(
            pricing.present_value([105], [1], 0.10, frequency=1), 105 / 1.10
        )

    def test_a_zero_yield_leaves_the_cash_flows_alone(self):
        self.assertAlmostEqual(
            pricing.present_value([40, 40, 1040], [1, 2, 3], 0.0), 1120.0
        )

    def test_mismatched_lengths_are_rejected(self):
        with self.assertRaises(exceptions.ScheduleError):
            pricing.present_value([40, 1040], [1, 2, 3], 0.05)


class TestPricingErrors(unittest.TestCase):
    def test_a_percentage_yield_is_rejected(self):
        with self.assertRaises(exceptions.InvalidRateError):
            pricing.price_from_yield(sample_bond(), 10)

    def test_a_list_is_not_a_schedule(self):
        with self.assertRaises(exceptions.ScheduleError):
            pricing.price_from_yield([40, 40, 1040], 0.10, frequency=2)


# -------------------------------------------------------------------- yields


class TestYieldToMaturity(unittest.TestCase):
    def setUp(self):
        self.schedule = sample_bond()

    def test_recovers_the_yield_it_was_priced_at(self):
        # Price at a known yield, then solve back to it. If either the
        # pricer or the solver is wrong, this fails.
        for expected in (0.02, 0.05, 0.08, 0.10, 0.15, 0.30):
            price = pricing.price_from_yield(self.schedule, expected)
            self.assertAlmostEqual(
                yields.yield_to_maturity(price, self.schedule), expected, places=8
            )

    def test_a_bond_at_par_yields_its_coupon_rate(self):
        self.assertAlmostEqual(
            yields.yield_to_maturity(1000.0, self.schedule), 0.08, places=8
        )

    def test_a_discount_price_yields_more_than_the_coupon(self):
        self.assertGreater(yields.yield_to_maturity(900.0, self.schedule), 0.08)

    def test_a_premium_price_yields_less_than_the_coupon(self):
        self.assertLess(yields.yield_to_maturity(1100.0, self.schedule), 0.08)


class TestSolverFailures(unittest.TestCase):
    def setUp(self):
        self.schedule = sample_bond()

    def test_a_price_the_bond_can_never_reach_is_reported_as_such(self):
        with self.assertRaises(exceptions.ConvergenceError) as caught:
            yields.yield_to_maturity(50.0, self.schedule)
        # The message should show the range, so the user can see why.
        self.assertIn("outside the range", str(caught.exception))

    def test_a_price_above_the_maximum_is_also_rejected(self):
        with self.assertRaises(exceptions.ConvergenceError):
            yields.yield_to_maturity(1e9, self.schedule)

    def test_a_negative_price_is_an_input_error_not_a_solver_failure(self):
        with self.assertRaises(exceptions.InvalidInputError):
            yields.yield_to_maturity(-100.0, self.schedule)

    def test_too_few_steps_fails_loudly_rather_than_returning_a_guess(self):
        with self.assertRaises(exceptions.ConvergenceError) as caught:
            yields.yield_to_maturity(949.24, self.schedule, max_steps=2)
        self.assertIn("closest", str(caught.exception))


class TestCurrentYield(unittest.TestCase):
    def test_current_yield_is_coupon_over_price(self):
        self.assertAlmostEqual(yields.current_yield(80, 1000), 0.08)

    def test_current_yield_rejects_a_zero_price(self):
        with self.assertRaises(exceptions.InvalidInputError):
            yields.current_yield(80, 0)


# ---------------------------------------------------------------------- risk


class TestDuration(unittest.TestCase):
    def setUp(self):
        self.schedule = sample_bond()

    def test_matches_the_hand_calculation(self):
        # Weighted sum 5,159.04 divided by price 949.243 is 5.4347 periods,
        # which is 2.7174 years at two payments a year.
        self.assertAlmostEqual(
            risk.macaulay_duration(self.schedule, 0.10), 2.7174, places=4
        )

    def test_modified_duration_is_macaulay_divided_by_one_plus_period_yield(self):
        macaulay = risk.macaulay_duration(self.schedule, 0.10)
        modified = risk.modified_duration(self.schedule, 0.10)
        self.assertAlmostEqual(modified, macaulay / 1.05, places=10)

    def test_a_bond_with_no_coupons_has_duration_equal_to_its_maturity(self):
        # Nothing arrives before maturity, so the average arrival time is
        # simply the time to maturity. True at any yield.
        zero = sample_bond(coupon_rate=0.0)
        for ytm in (0.02, 0.08, 0.15):
            self.assertAlmostEqual(risk.macaulay_duration(zero, ytm), 3.0, places=8)

    def test_duration_is_shorter_than_maturity_when_coupons_are_paid(self):
        self.assertLess(risk.macaulay_duration(self.schedule, 0.10), 3.0)

    def test_a_bigger_coupon_shortens_duration(self):
        # More money arrives early, so the average time falls.
        self.assertGreater(
            risk.macaulay_duration(sample_bond(coupon_rate=0.02), 0.08),
            risk.macaulay_duration(sample_bond(coupon_rate=0.12), 0.08),
        )

    def test_a_longer_bond_has_a_longer_duration(self):
        self.assertGreater(
            risk.macaulay_duration(sample_bond(maturity="2036-01-01"), 0.10),
            risk.macaulay_duration(self.schedule, 0.10),
        )


if __name__ == "__main__":
    unittest.main()
