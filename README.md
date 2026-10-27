# bondcalc

A Python package for pricing bonds and measuring their interest rate risk.

# Installation and usage instructions

Needs Python 3.8 or later.

```
pip install pandas numpy
```

```python
from bondcalc import (
    cashflow_schedule, price_from_yield, yield_to_maturity, macaulay_duration
)
```

Every error inherits from `BondCalcError`, so a caller can catch one kind or all
of them.


# Modules

| Module | What it does |
|---|---|
| `cashflow` | Coupon dates and the payment table |
| `pricing` | Discounts the payments and sums them |
| `yields` | Yield to maturity, by bisection |
| `risk` | Macaulay and modified duration |
| `validation` | Input checks shared by every function |
| `exceptions` | The package's own error types |

