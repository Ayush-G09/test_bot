import os
import pandas as pd
import ta
import requests
import time
from binance.client import Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Binance API setup
client = Client()

# Telegram credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Define parameters
SYMBOL = "ETHUSDT"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE
LOOKBACK_DAYS = 1  # Number of past days to fetch data

# Function to send messages to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, json=payload)

# Fetch historical data from Binance
def get_historical_data(symbol, interval, days):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

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

    # Convert necessary columns to float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df

# Calculate Bollinger Bands
def calculate_bollinger_bands(df, period=20, std_dev=2):
    bb = ta.volatility.BollingerBands(df["close"], window=period, window_dev=std_dev)
    df["upper_band"] = bb.bollinger_hband()
    df["middle_band"] = bb.bollinger_mavg()
    df["lower_band"] = bb.bollinger_lband()
    return df

# Calculate VWAP
def calculate_vwap(df):
    df["vwap"] = ta.volume.VolumeWeightedAveragePrice(df["high"], df["low"], df["close"], df["volume"]).volume_weighted_average_price()
    return df

# Calculate RSI and its moving average
def calculate_rsi(df, period=14, ma_period=10):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=period).rsi()
    df["rsi_ma"] = df["rsi"].rolling(window=ma_period).mean()
    return df

# Detect Shooting Star Pattern (Possible Reversal)
def is_shooting_star(row):
    body = abs(row["close"] - row["open"])
    upper_wick = row["high"] - max(row["close"], row["open"])
    lower_wick = min(row["close"], row["open"]) - row["low"]
    return (upper_wick > 2 * body) and (lower_wick < body)  # Long upper wick, small body, little/no lower wick

# Generate trading signals
def generate_signals(df):
    signals = []
    
    for i in range(1, len(df)):
        # Bullish Breakout Signal
        if (
            df["close"].iloc[i] >= df["upper_band"].iloc[i] and  # Close price touches upper BB
            df["close"].iloc[i] > df["vwap"].iloc[i] and         # Close price above VWAP
            df["rsi"].iloc[i] > df["rsi_ma"].iloc[i]             # RSI above its moving average
        ):
            signals.append((df.index[i], df["close"].iloc[i], "🚀 Breakout Signal"))

        # Bearish Reversal Signal
        elif (
            df["close"].iloc[i] >= df["upper_band"].iloc[i] and  # Near upper BB
            is_shooting_star(df.iloc[i])                         # Shooting Star pattern detected
        ):
            signals.append((df.index[i], df["close"].iloc[i], "⚠️ Potential Reversal"))
        
        # Buy Signal: Close price touches lower BB, below VWAP, and RSI < RSI MA
        elif (
            df["close"].iloc[i] <= df["lower_band"].iloc[i] and  # Close price touches lower BB
            df["close"].iloc[i] < df["vwap"].iloc[i] and         # Close price below VWAP
            df["rsi"].iloc[i] < df["rsi_ma"].iloc[i]             # RSI below its moving average
        ):
            signals.append((df.index[i], df["close"].iloc[i], "🛒 Buy Signal"))

    return signals

# Main execution loop
def run_bot():
    while True:
        df = get_historical_data(SYMBOL, INTERVAL, LOOKBACK_DAYS)
        df = calculate_bollinger_bands(df)
        df = calculate_vwap(df)
        df = calculate_rsi(df)

        signals = generate_signals(df)

        # Send trading signals to Telegram
        for timestamp, price, signal_type in signals:
            ist_time = timestamp + timedelta(hours=5, minutes=30)  # Convert UTC to IST
            message = f"📢 Trading Signal 📢\nTime (IST): {ist_time}\nPrice: {price}\nSignal: {signal_type}"
            send_telegram_message(message)

        # Wait before the next update (e.g., 5 minutes)
        print("Waiting for the next update...")
        time.sleep(300)  # Sleep for 5 minutes (300 seconds)

# Run the bot
if __name__ == "__main__":
    run_bot()
