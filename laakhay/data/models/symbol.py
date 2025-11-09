"""Trading symbol data model with trading constraints and helpers."""

from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from pydantic import BaseModel, ConfigDict, Field


class Symbol(BaseModel):
    """Trading symbol information and constraints.

    Optional metadata fields are populated from the provider's exchangeInfo
    response when available. Helper methods use these constraints to round
    prices/quantities and validate orders.
    """

    symbol: str = Field(..., min_length=1)
    base_asset: str = Field(..., min_length=1)
    quote_asset: str = Field(..., min_length=1)

    # Optional trading constraints/metadata
    tick_size: Decimal | None = None
    step_size: Decimal | None = None
    min_notional: Decimal | None = None

    # Futures-only extras (ignored for spot)
    contract_type: str | None = None
    delivery_date: int | datetime | None = None

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # --- Helpers ---
    def round_price(self, price: Decimal) -> Decimal:
        """Floor the price to the nearest tick size increment.

        If tick_size is not available, returns the input price unchanged.
        """
        if self.tick_size is None:
            return price
        inc = self.tick_size
        n = (price / inc).to_integral_value(rounding=ROUND_FLOOR)
        return (n * inc).quantize(inc)

    def round_quantity(self, qty: Decimal) -> Decimal:
        """Floor the quantity to the nearest step size increment.

        If step_size is not available, returns the input quantity unchanged.
        """
        if self.step_size is None:
            return qty
        inc = self.step_size
        n = (qty / inc).to_integral_value(rounding=ROUND_FLOOR)
        return (n * inc).quantize(inc)

    def is_valid_order(self, price: Decimal, quantity: Decimal) -> bool:
        """Validate if an order (price x quantity) satisfies constraints.

        Checks tick_size, step_size alignment and min_notional threshold.
        Missing constraints are ignored.
        """
        # Tick size alignment
        if self.tick_size is not None and self.round_price(price) != price:
            return False

        # Step size alignment
        if self.step_size is not None and self.round_quantity(quantity) != quantity:
            return False

        # Notional threshold
        if self.min_notional is not None:
            notional = price * quantity
            if notional < self.min_notional:
                return False

        return True
