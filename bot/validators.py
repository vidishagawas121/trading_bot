"""
Input validation for trading bot CLI arguments.
All validators raise ValueError with a human-readable message on failure.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"}
SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_symbol(symbol: str) -> str:
    """Validate and normalise the trading symbol (e.g. BTCUSDT)."""
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. Expected uppercase letters/digits only, "
            "e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    """Validate order side: BUY or SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Validate order type: MARKET or LIMIT (and bonus types)."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Validate order quantity; must be a positive number."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    Validate price for LIMIT orders.
    - Required when order_type is LIMIT (or STOP/TAKE_PROFIT).
    - Ignored/optional for MARKET orders.
    """
    limit_types = {"LIMIT", "STOP", "TAKE_PROFIT"}
    if order_type in limit_types:
        if price is None:
            raise ValueError(
                f"Price is required for {order_type} orders."
            )
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
        if p <= 0:
            raise ValueError(f"Price must be greater than 0, got {p}.")
        return p
    # For MARKET / STOP_MARKET / TAKE_PROFIT_MARKET, price is ignored
    if price is not None:
        # Warn but do not fail — it will simply be omitted from the request
        pass
    return None


def validate_stop_price(stop_price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """Validate stop price for STOP_MARKET / STOP orders."""
    stop_types = {"STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"}
    if order_type in stop_types:
        if stop_price is None:
            raise ValueError(f"--stop-price is required for {order_type} orders.")
        try:
            sp = Decimal(str(stop_price))
        except InvalidOperation:
            raise ValueError(f"Invalid stop price '{stop_price}'.")
        if sp <= 0:
            raise ValueError(f"Stop price must be > 0, got {sp}.")
        return sp
    return None


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validators and return a clean, normalised params dict.
    Raises ValueError on the first validation failure encountered.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)

    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
        "price": clean_price,
        "stop_price": clean_stop,
    }
