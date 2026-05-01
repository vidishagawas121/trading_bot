"""
Binance Futures Testnet REST API client.

Handles authentication (HMAC-SHA256 signature), request building,
response parsing, and low-level error handling.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("client")

# ---------------------------------------------------------------------------
# Default base URL for USDT-M Futures Testnet
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error payload."""

    def __init__(self, code: int, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"Binance API error {code}: {message} (HTTP {status_code})")


class BinanceFuturesClient:
    """
    Lightweight wrapper around the Binance USDT-M Futures REST API.

    Only signed endpoints are covered (order placement, account info).
    Public endpoints (exchange info, ticker) are also exposed for validation.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 10,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceFuturesClient initialised | base_url=%s", self._base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        """Current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 hex signature over the query string."""
        query = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request.

        Args:
            method:  HTTP verb (GET, POST, DELETE).
            path:    API path, e.g. '/fapi/v1/order'.
            params:  Query / body parameters.
            signed:  Whether to append timestamp + signature.

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            BinanceAPIError:   API returned an error payload.
            requests.Timeout:  Request timed out.
            requests.ConnectionError: Network failure.
        """
        params = dict(params or {})

        if signed:
            params["timestamp"] = self._timestamp()
            params["signature"] = self._sign(params)

        url = f"{self._base_url}{path}"

        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("→ %s %s | params=%s", method.upper(), url, log_params)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self._timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self._timeout
                )
        except requests.Timeout as exc:
            logger.error("Request timed out: %s %s", method, url)
            raise
        except requests.ConnectionError as exc:
            logger.error("Connection error: %s %s | %s", method, url, exc)
            raise

        logger.debug(
            "← HTTP %s | body=%s", response.status_code, response.text[:500]
        )

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            # Binance error payload: {"code": -1121, "msg": "Invalid symbol."}
            raise BinanceAPIError(
                code=data.get("code", -1),
                message=data.get("msg", "Unknown error"),
                status_code=response.status_code,
            )

        if not response.ok:
            raise BinanceAPIError(
                code=response.status_code,
                message=response.text,
                status_code=response.status_code,
            )

        return data

    # ------------------------------------------------------------------
    # Public / unsigned endpoints
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._request("GET", "/fapi/v1/ping")
            return True
        except Exception as exc:
            logger.warning("Ping failed: %s", exc)
            return False

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange trading rules and symbol information."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return exchange info for a single symbol, or None if not found."""
        info = self.get_exchange_info()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol.upper():
                return s
        return None

    # ------------------------------------------------------------------
    # Signed endpoints
    # ------------------------------------------------------------------

    def get_account(self) -> Dict[str, Any]:
        """Fetch account information (balance, positions, etc.)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        stop_price: Optional[Decimal] = None,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures.

        Args:
            symbol:        Trading pair, e.g. 'BTCUSDT'.
            side:          'BUY' or 'SELL'.
            order_type:    'MARKET', 'LIMIT', 'STOP_MARKET', etc.
            quantity:      Order quantity (base asset).
            price:         Limit price (required for LIMIT orders).
            time_in_force: 'GTC', 'IOC', 'FOK', 'GTX'. Ignored for MARKET.
            stop_price:    Stop trigger price for STOP_MARKET / STOP orders.
            reduce_only:   If True, the order only reduces an existing position.

        Returns:
            Raw Binance order response dict.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
            symbol, side, order_type, quantity, price,
        )

        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)

        logger.info(
            "Order placed   | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )

        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order | orderId=%s symbol=%s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
