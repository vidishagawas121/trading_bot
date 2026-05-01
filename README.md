# 🤖 Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Status |
|---|---|
| Market & Limit orders | ✅ |
| BUY and SELL sides | ✅ |
| Stop-Market orders (bonus) | ✅ |
| Input validation with clear error messages | ✅ |
| Structured logging to file + console | ✅ |
| Full exception handling (API / network / input) | ✅ |
| Layered architecture (client / orders / validators / CLI) | ✅ |
| Account balance and open order listing | ✅ |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (auth, signing, requests)
│   ├── orders.py          # Order placement orchestration + output formatting
│   ├── validators.py      # Input validation for all order parameters
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # CLI entry point (argparse sub-commands)
├── logs/
│   └── trading_bot.log    # Auto-created; sample log included
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / download

```bash
git clone https://github.com/<your-username>/trading-bot.git
cd trading-bot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Navigate to **API Key** → generate a key pair
4. Copy the **API Key** and **Secret Key**

### 5. Set credentials

**Option A — environment variables (recommended)**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B — `.env` file** in the project root:

```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
```

---

## How to Run

### Test connectivity

```bash
python cli.py ping
```

### Place a MARKET order

```bash
# BUY 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# SELL 0.1 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.1
```

### Place a LIMIT order

```bash
# SELL 0.001 BTC at $100,000 (resting limit)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000

# BUY 0.002 BTC at $55,000 with IOC time-in-force
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002 --price 55000 --tif IOC
```

### Place a Stop-Market order (bonus)

```bash
# SELL stop-market at $90,000 trigger
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 90000
```

### List open orders

```bash
python cli.py orders
python cli.py orders --symbol BTCUSDT
```

### Show account balances

```bash
python cli.py account
```

### Adjust verbosity

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Example Output

```
============================================================
  ORDER REQUEST SUMMARY
============================================================
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
============================================================

============================================================
  ORDER RESPONSE
============================================================
  orderId        : 4007437269
  symbol         : BTCUSDT
  side           : BUY
  type           : MARKET
  origQty        : 0.001
  executedQty    : 0.001
  price          : 0
  avgPrice       : 96420.10
  status         : FILLED
  timeInForce    : GTC
  updateTime     : 1746089524182
============================================================

✅  Order placed successfully! OrderId: 4007437269
```

---

## Logging

Logs are written to `logs/trading_bot.log` (rotating, max 5 MB × 3 backups).

Each log entry includes:

- Timestamp (ISO 8601)
- Level (DEBUG / INFO / WARNING / ERROR)
- Module name
- Human-readable message

API errors, network failures, and validation errors are all captured with context.

---

## CLI Reference

```
usage: trading_bot [-h] [--base-url URL] [--log-level {DEBUG,INFO,WARNING,ERROR}]
                   <command> ...

Commands:
  place     Place a new order
  orders    List open orders
  account   Show account balances
  ping      Test connectivity

place arguments:
  --symbol      Trading pair, e.g. BTCUSDT          (required)
  --side        BUY or SELL                          (required)
  --type        MARKET | LIMIT | STOP_MARKET | STOP  (required)
  --quantity    Order size in base asset             (required)
  --price       Limit price (required for LIMIT)
  --stop-price  Trigger price (required for STOP_MARKET / STOP)
  --tif         Time-in-force: GTC|IOC|FOK|GTX       (default: GTC)
  --reduce-only Place a reduce-only order
```

---

## Assumptions

1. **Testnet only** — the default base URL is `https://testnet.binancefuture.com`. Pass `--base-url` to override.
2. **USDT-M Futures** — this bot targets the USD-margined perpetual futures market, not spot.
3. **No order book validation** — symbol precision (tick size, lot size) is not pre-checked; the exchange will reject requests that violate these rules with a clear error message.
4. **Credentials via env / .env** — no credentials are ever stored in source files.
5. **`reduce_only` defaults to False** — pass `--reduce-only` to override.

---

## Dependencies

```
requests>=2.31.0    # HTTP client
python-dotenv>=1.0.0  # .env file loading
```

Python 3.9+ required.
