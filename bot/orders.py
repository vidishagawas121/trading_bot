"""
Order placement orchestration layer.

This module sits between the CLI and the raw API client.
It runs validation, calls the client, formats results, and handles errors.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.validators import validate_all
from bot.logging_config import get_logger

logger = get_logger("orders")


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _format_order_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and rename the most relevant fields from a Binance order response."""
    return {
        "orderId": raw.get("orderId"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "origQty": raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "price": raw.get("price"),
        "avgPrice": raw.get("avgPrice"),
        "status": raw.get("status"),
        "timeInForce": raw.get("timeInForce"),
        "updateTime": raw.get("updateTime"),
    }


def _print_summary(params: Dict[str, Any]) -> None:
    """Print order request summary to stdout."""
    print("\n" + "=" * 60)
    print("  ORDER REQUEST SUMMARY")
    print("=" * 60)
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"  Stop Price : {params['stop_price']}")
    print("=" * 60)


def _print_response(result: Dict[str, Any]) -> None:
    """Print order response details to stdout."""
    print("\n" + "=" * 60)
    print("  ORDER RESPONSE")
    print("=" * 60)
    for key, value in result.items():
        if value is not None and value != "":
            print(f"  {key:<15}: {value}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Validate inputs, place an order via the client, and print results.

    Args:
        client:         Authenticated BinanceFuturesClient.
        symbol:         e.g. 'BTCUSDT'.
        side:           'BUY' or 'SELL'.
        order_type:     'MARKET', 'LIMIT', 'STOP_MARKET', etc.
        quantity:       Order size.
        price:          Limit price (LIMIT orders).
        stop_price:     Stop trigger price (STOP_MARKET / STOP).
        time_in_force:  GTC / IOC / FOK. Only for LIMIT.
        reduce_only:    Only reduce an existing position.

    Returns:
        Formatted response dict on success, None on failure.
    """
    # ---- Validate --------------------------------------------------------
    try:
        params = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n❌  Validation error: {exc}")
        return None

    _print_summary(params)

    # ---- Place order -------------------------------------------------------
    try:
        raw_response = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params.get("price"),
            time_in_force=time_in_force,
            stop_price=params.get("stop_price"),
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error(
            "API error placing order | code=%s msg=%s http=%s",
            exc.code, exc.message, exc.status_code,
        )
        print(f"\n❌  Binance API error [{exc.code}]: {exc.message}")
        return None
    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        print(f"\n❌  Unexpected error: {exc}")
        return None

    # ---- Display results ---------------------------------------------------
    result = _format_order_response(raw_response)
    _print_response(result)
    print(f"\n✅  Order placed successfully! OrderId: {result['orderId']}\n")
    logger.info("Order success | formatted=%s", json.dumps(result))
    return result
