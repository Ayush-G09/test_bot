import time
import pandas as pd
import ta
from binance.client import Client
from datetime import datetime, timedelta
from telegram import Bot

# Initialize Binance client (use your API keys if needed)
client = Client(testnet=True)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token"
TELEGRAM_CHAT_ID = "your_telegram_chat_id"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Define parameters
symbol = "ETHUSDT"
interval = Client.KLINE_INTERVAL_5MINUTE
lookback_days = 1  # Number of past days to fetch data

def get_historical_data():
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=lookback_days)

    klines = client.get_klines(
        symbol=symbol, interval=interval,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000)
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df.set_index("timestamp", inplace=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df

def calculate_indicators(df):
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["upper_band"] = bb.bollinger_hband()
    df["middle_band"] = bb.bollinger_mavg()
    df["lower_band"] = bb.bollinger_lband()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    return df

def send_telegram_message(message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

def detect_signals(df):
    latest = df.iloc[-1]
    if latest["close"] >= latest["upper_band"] and latest["rsi"] > 70:
        send_telegram_message(f"📈 Breakout Alert! ETH Price: {latest['close']}")
    elif latest["rsi"] < 30:
        send_telegram_message(f"📉 RSI Oversold! ETH Price: {latest['close']}")

# Run bot continuously
while True:
    df = get_historical_data()
    df = calculate_indicators(df)
    detect_signals(df)
    time.sleep(300)  # Wait for 5 minutes before fetching new data
