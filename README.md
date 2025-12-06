# 🤖 Interactive Brokers Forex Trading Bot

Automated trading bot for Interactive Brokers with breakout strategy, risk management, and session filters.

## 📋 Features

- ✅ **Breakout Strategy**: Detects long/short breakouts above/below historical highs/lows
- ✅ **Risk Management**: Automatic position sizing based on % risk per trade
- ✅ **Trailing Stop**: Dynamic stop loss that follows profits
- ✅ **Take Profit**: Automatic profit exit at target pips
- ✅ **Session Filter**: Trade only during Sydney, Tokyo, London, or New York sessions
- ✅ **Logging**: Complete logging of all actions
- ✅ **Paper Trading**: Safe testing without real money

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- Interactive Brokers Account (Paper or Live)
- TWS (Trader Workstation) or IB Gateway

### 1. Clone Repository

```bash
git clone https://github.com/your-username/ib-trading-bot.git
cd ib-trading-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
ib_insync>=0.9.86
pandas>=2.0.0
numpy>=1.24.0
```

### 3. Interactive Brokers Setup

1. **Install TWS or IB Gateway**
   - Download: [Interactive Brokers](https://www.interactivebrokers.com/en/trading/tws.php)

2. **Enable API**
   - Open TWS → File → Global Configuration → API → Settings
   - ✅ Enable "Enable ActiveX and Socket Clients"
   - ✅ Disable "Read-Only API" (for trading)
   - Set port:
     - **7497** for Paper Trading (recommended for testing)
     - **7496** for Live Trading

3. **Configure Trusted IPs**
   - Add IP address `127.0.0.1` (localhost)

## ⚙️ Configuration

Adjust bot settings in `trading_bot.py`:

```python
config = {
    'symbol': 'EURUSD',              # Currency pair
    'lookback_period': 20,           # Breakout lookback (bars)
    'risk_percent': 10.0,            # Risk per trade in %
    'take_profit_pips': 40,          # Take profit in pips
    'trailing_stop_pips': 20,        # Trailing stop in pips
    'leverage': 100,                 # Leverage
    'sessions': {
        'sydney': True,              # Sydney session (22:00-07:00 UTC)
        'tokyo': True,               # Tokyo session (00:00-09:00 UTC)
        'london': True,              # London session (08:00-17:00 UTC)
        'new_york': True             # New York session (13:00-22:00 UTC)
    }
}
```

### Supported Currency Pairs

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCHF
- Any other forex pair supported by IB

## 🚀 Start Bot

### Paper Trading (recommended for testing)

```bash
python trading_bot.py
```

Default port is **7497** (Paper Trading).

### Live Trading

⚠️ **For advanced users only!**

Change in the `connect()` method:

```python
bot.connect(host='127.0.0.1', port=7496)  # Live trading port
```

## 📊 How the Strategy Works

### Breakout Detection

1. Bot calculates highest high and lowest low of last X periods (default: 20)
2. **Long Signal**: Price breaks above previous high
3. **Short Signal**: Price breaks below previous low

### Risk Management

- **Position size** is automatically calculated:
  ```
  Risk Amount = Capital × Risk%
  Position Size = Risk Amount / (Stop Loss in Pips × Pip Value)
  ```

- **Example** (10,000 USD capital, 10% risk, 20 pips SL):
  - Risk = 1,000 USD
  - At EUR/USD ≈ 1.10 → Position of ~500,000 units (5 mini lots)
  - At 20 pips stop loss = exactly 1,000 USD loss

### Exit Strategy

- **Take Profit**: Fixed at X pips profit (default: 40 pips)
- **Trailing Stop**: Follows price at Y pips distance (default: 20 pips)
- Position automatically closes when either is triggered

## 📝 Logging

The bot creates two logs:

1. **Console Output**: Real-time information
2. **trading_bot.log**: Complete history of all trades and events

### Log Level

```python
# Adjust in trading_bot.py:
logging.basicConfig(level=logging.INFO)  # INFO, DEBUG, WARNING, ERROR
```

## 🛡️ Security & Best Practices

### ⚠️ Important Notes

- ✅ **Always start with Paper Trading**
- ✅ **Risk per trade under 2-5%** for real trading
- ✅ **Monitor bot regularly**
- ✅ **TWS/Gateway must be open during bot runtime**
- ❌ **No sensitive data in code** (API keys, passwords)
- ❌ **Don't run multiple bots on same symbol simultaneously**

### Recommended Settings for Live Trading

```python
config = {
    'risk_percent': 2.0,      # Conservative: 1-2%
    'take_profit_pips': 40,
    'trailing_stop_pips': 20,
}
```

## 🔍 Troubleshooting

### Bot doesn't connect to TWS

```
❌ Connection failed
```

**Solution:**
- Is TWS/Gateway running?
- Is API enabled in TWS?
- Correct port? (7497=Paper, 7496=Live)
- Is firewall blocking connection?

### "Invalid contract" Error

```
❌ Invalid contract: EURUSD
```

**Solution:**
- Forex symbols must be without separator: `EURUSD` not `EUR/USD`
- Check if IB supports the currency pair

### Bot doesn't place orders

**Possible causes:**
- Outside trading sessions (check session filter)
- No breakout signal present
- Position already open
- Insufficient margin

**Debug:**
```python
# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG)
```

### Position larger than expected

**Solution:**
- Check `risk_percent` setting
- Verify leverage calculation
- For smaller positions: reduce risk (e.g., 1-2%)

## 📈 Backtesting

This bot is optimized for live/paper trading. For backtesting, I recommend:

- **Backtrader**: Python backtesting framework
- **VectorBT**: Fast vector-based backtesting
- **QuantConnect**: Cloud-based backtesting platform

## 🛠️ Extensions

### Add Telegram Notifications

```python
pip install python-telegram-bot

# In trading_bot.py:
from telegram import Bot

bot = Bot(token='YOUR_TOKEN')
bot.send_message(chat_id='YOUR_CHAT_ID', text='Trade placed!')
```

### Add Dashboard

```python
pip install dash plotly

# Create separate dashboard.py for web interface
```

### Multiple Symbols Simultaneously

Create multiple bot instances with different `client_id`:

```python
bot1 = ForexBreakoutBot(config_eurusd)
bot1.connect(client_id=1)

bot2 = ForexBreakoutBot(config_gbpusd)
bot2.connect(client_id=2)
```

## 📜 License

MIT License - free to use for private and commercial purposes.

## ⚠️ Disclaimer

**Trading involves substantial risk!**

- This bot is provided for educational purposes
- No guarantee of profitability
- Past performance is not indicative of future results
- Only use capital you can afford to lose
- Test extensively with paper trading before going live
- The author assumes no liability for financial losses

## 🤝 Support & Contribution

- **Issues**: Report problems via GitHub Issues
- **Pull Requests**: Improvements are welcome!
- **Discussions**: GitHub Discussions for questions

## 📚 Additional Resources

- [IB API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- [Forex Trading Basics](https://www.investopedia.com/forex-trading-4427557)

---

**Happy Trading! 🚀**

*Created for Interactive Brokers Traders | Version 1.0*
