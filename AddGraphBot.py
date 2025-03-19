import asyncio
import logging
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Telegram API
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# Таймфреймы
TIMEFRAMES = {
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1d"
}

# RSI & MACD параметры
RSI_PERIOD = 14
OVERSOLD = 30
OVERBOUGHT = 70
SHORT_EMA = 12
LONG_EMA = 26
SIGNAL_EMA = 9

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Функция получения цен BTC
def get_btc_prices(timeframe):
    try:
        api_url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={timeframe}&limit=100"
        response = requests.get(api_url)
        data = response.json()
        prices = [float(candle[4]) for candle in data]  # Закрытия свечей
        return prices
    except Exception as e:
        logging.error(f"Ошибка получения цен для {timeframe}: {e}")
        return None

# Функция расчета RSI
def calculate_rsi(prices):
    df = pd.DataFrame(prices, columns=["Close"])
    df["diff"] = df["Close"].diff()
    gain = df["diff"].apply(lambda x: x if x > 0 else 0)
    loss = df["diff"].apply(lambda x: -x if x < 0 else 0)
    avg_gain = gain.rolling(window=RSI_PERIOD, min_periods=1).mean()
    avg_loss = loss.rolling(window=RSI_PERIOD, min_periods=1).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Функция расчета MACD
def calculate_macd(prices):
    df = pd.DataFrame(prices, columns=["Close"])
    df["ShortEMA"] = df["Close"].ewm(span=SHORT_EMA, adjust=False).mean()
    df["LongEMA"] = df["Close"].ewm(span=LONG_EMA, adjust=False).mean()
    df["MACD"] = df["ShortEMA"] - df["LongEMA"]
    df["Signal"] = df["MACD"].ewm(span=SIGNAL_EMA, adjust=False).mean()
    return df["MACD"], df["Signal"]

# Функция построения и сохранения графика
def create_plot(prices, rsi, macd, signal, timeframe):
    df = pd.DataFrame(prices, columns=["Close"])

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1, 1]})

    # 1️⃣ График цены BTC
    axes[0].plot(df.index, df["Close"], label="Цена BTC", color="blue")
    axes[0].set_title(f"Bitcoin ({timeframe})")
    axes[0].legend()

    # 2️⃣ График RSI
    axes[1].plot(df.index, rsi, label="RSI", color="purple")
    axes[1].axhline(y=70, color="red", linestyle="--", label="Перекупленность (70)")
    axes[1].axhline(y=30, color="green", linestyle="--", label="Перепроданность (30)")
    axes[1].set_title("RSI Индикатор")
    axes[1].legend()

    # 3️⃣ График MACD
    axes[2].plot(df.index, macd, label="MACD", color="orange")
    axes[2].plot(df.index, signal, label="Signal", color="red")
    axes[2].set_title("MACD Индикатор")
    axes[2].legend()

    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()

# Функция проверки индикаторов и отправки графиков
async def check_indicators():
    for label, timeframe in TIMEFRAMES.items():
        prices = get_btc_prices(timeframe)
        if prices:
            rsi = calculate_rsi(prices)
            macd, signal = calculate_macd(prices)

            # Создаем график
            create_plot(prices, rsi, macd, signal, label)

            # Отправляем график в Telegram
            with open("chart.png", "rb") as photo:
                await bot.send_photo(CHAT_ID, photo, caption=f"📊 Bitcoin ({label})")

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Я бот для отслеживания RSI и MACD с графиками 📈")

# Запуск планировщика
async def on_startup(_):
    scheduler.add_job(check_indicators, "interval", minutes=30)  # Проверка каждые 30 минут
    scheduler.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
