#!/usr/bin/env python3
"""
Trading Bot CLI Entry Point
============================

Place MARKET and LIMIT orders on Binance Futures Testnet (USDT-M).

Usage examples
--------------
# Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

# Stop-Market SELL (bonus)
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 60000

# List open orders
python cli.py orders --symbol BTCUSDT

# Account balance
python cli.py account
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path when running as `python cli.py`
sys.path.insert(0, str(Path(__file__).parent))

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_credentials() -> tuple[str, str]:
    """
    Load API key and secret.

    Priority order:
      1. BINANCE_API_KEY / BINANCE_API_SECRET environment variables
      2. .env file in the project root (simple KEY=VALUE format)

    Raises:
        SystemExit if credentials are not found.
    """
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k == "BINANCE_API_KEY":
                        api_key = v
                    elif k == "BINANCE_API_SECRET":
                        api_secret = v

    if not api_key or not api_secret:
        print(
            "\n❌  Missing credentials.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables,\n"
            "or create a .env file in the project root.\n"
        )
        sys.exit(1)

    return api_key, api_secret


def _build_client(args: argparse.Namespace) -> BinanceFuturesClient:
    api_key, api_secret = _load_credentials()
    base_url = getattr(args, "base_url", "https://testnet.binancefuture.com")
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def cmd_place(args: argparse.Namespace, logger) -> None:
    """Handle the 'place' sub-command."""
    client = _build_client(args)

    # Ping before placing
    if not client.ping():
        print("⚠️  Warning: testnet ping failed — proceeding anyway.\n")

    place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=getattr(args, "price", None),
        stop_price=getattr(args, "stop_price", None),
        time_in_force=getattr(args, "tif", "GTC"),
        reduce_only=getattr(args, "reduce_only", False),
    )


def cmd_orders(args: argparse.Namespace, logger) -> None:
    """Handle the 'orders' sub-command (list open orders)."""
    client = _build_client(args)
    symbol = getattr(args, "symbol", None)

    try:
        open_orders = client.get_open_orders(symbol=symbol)
    except Exception as exc:
        logger.error("Failed to fetch open orders: %s", exc)
        print(f"❌  Error: {exc}")
        sys.exit(1)

    if not open_orders:
        print("\nNo open orders found.\n")
        return

    print(f"\n{'='*60}")
    print(f"  OPEN ORDERS{(' for ' + symbol) if symbol else ''}")
    print(f"{'='*60}")
    for o in open_orders:
        print(
            f"  [{o.get('orderId')}] {o.get('symbol')} | {o.get('side')} "
            f"{o.get('type')} | qty={o.get('origQty')} price={o.get('price')} "
            f"status={o.get('status')}"
        )
    print(f"{'='*60}\n")


def cmd_account(args: argparse.Namespace, logger) -> None:
    """Handle the 'account' sub-command (print USDT balance)."""
    client = _build_client(args)

    try:
        account = client.get_account()
    except Exception as exc:
        logger.error("Failed to fetch account: %s", exc)
        print(f"❌  Error: {exc}")
        sys.exit(1)

    assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    print(f"\n{'='*60}")
    print("  ACCOUNT BALANCES (non-zero)")
    print(f"{'='*60}")
    for a in assets:
        print(
            f"  {a['asset']:<8} wallet={a['walletBalance']:<14} "
            f"available={a['availableBalance']}"
        )
    print(f"{'='*60}\n")


def cmd_ping(args: argparse.Namespace, logger) -> None:
    """Check connectivity to the Binance Futures Testnet."""
    client = _build_client(args)
    if client.ping():
        print("✅  Testnet is reachable.\n")
    else:
        print("❌  Testnet ping failed.\n")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        default="https://testnet.binancefuture.com",
        metavar="URL",
        help="Binance Futures base URL (default: testnet)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ---- place ----
    place_p = sub.add_parser("place", help="Place a new order")
    place_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    place_p.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], type=str.upper, help="BUY or SELL"
    )
    place_p.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"],
        type=str.upper,
        metavar="TYPE",
        help="Order type: MARKET | LIMIT | STOP_MARKET | STOP | TAKE_PROFIT | TAKE_PROFIT_MARKET",
    )
    place_p.add_argument("--quantity", required=True, type=float, help="Order quantity (base asset)")
    place_p.add_argument("--price", type=float, default=None, help="Limit price (required for LIMIT)")
    place_p.add_argument(
        "--stop-price", dest="stop_price", type=float, default=None,
        help="Stop trigger price (STOP_MARKET / STOP orders)"
    )
    place_p.add_argument(
        "--tif", default="GTC",
        choices=["GTC", "IOC", "FOK", "GTX"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )
    place_p.add_argument(
        "--reduce-only", dest="reduce_only", action="store_true",
        help="Place a reduce-only order",
    )
    place_p.set_defaults(func=cmd_place)

    # ---- orders ----
    orders_p = sub.add_parser("orders", help="List open orders")
    orders_p.add_argument("--symbol", default=None, help="Filter by symbol")
    orders_p.set_defaults(func=cmd_orders)

    # ---- account ----
    account_p = sub.add_parser("account", help="Show account balances")
    account_p.set_defaults(func=cmd_account)

    # ---- ping ----
    ping_p = sub.add_parser("ping", help="Test connectivity to the testnet")
    ping_p.set_defaults(func=cmd_ping)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(getattr(args, "log_level", "INFO"))
    log = get_logger("cli")

    log.info("Command: %s | args=%s", args.command, vars(args))

    try:
        args.func(args, log)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
