import asyncio
import logging
import requests
import numpy as np
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Telegram API
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# Binance API для цены BTC
API_URL = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=100"

# Настройки RSI
RSI_PERIOD = 14
OVERSOLD = 30  # Перепроданность
OVERBOUGHT = 70  # Перекупленность

# Настройки MACD
SHORT_EMA = 12
LONG_EMA = 26
SIGNAL_EMA = 9

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Функция получения исторических данных
def get_btc_prices():
    try:
        response = requests.get(API_URL)
        data = response.json()
        prices = [float(candle[4]) for candle in data]  # Закрытия свечей
        return prices
    except Exception as e:
        logging.error(f"Ошибка получения цен: {e}")
        return None

# Функция расчета RSI
def calculate_rsi(prices, period=RSI_PERIOD):
    df = pd.DataFrame(prices, columns=["Close"])
    df["diff"] = df["Close"].diff()

    gain = df["diff"].apply(lambda x: x if x > 0 else 0)
    loss = df["diff"].apply(lambda x: -x if x < 0 else 0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / (avg_loss + 1e-10)  # Добавляем небольшое число для предотвращения деления на 0
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]  # Последнее значение RSI

# Функция расчета MACD
def calculate_macd(prices, short=SHORT_EMA, long=LONG_EMA, signal=SIGNAL_EMA):
    df = pd.DataFrame(prices, columns=["Close"])
    df["ShortEMA"] = df["Close"].ewm(span=short, adjust=False).mean()
    df["LongEMA"] = df["Close"].ewm(span=long, adjust=False).mean()
    df["MACD"] = df["ShortEMA"] - df["LongEMA"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()

    last_macd = df["MACD"].iloc[-1]
    last_signal = df["Signal"].iloc[-1]
    prev_macd = df["MACD"].iloc[-2]
    prev_signal = df["Signal"].iloc[-2]

    return last_macd, last_signal, prev_macd, prev_signal

# Функция проверки RSI и MACD и отправки уведомлений
async def check_indicators():
    prices = get_btc_prices()
    if prices:
        rsi = calculate_rsi(prices)
        macd, signal, prev_macd, prev_signal = calculate_macd(prices)

        print(f"RSI: {rsi:.2f}, MACD: {macd:.4f}, Signal: {signal:.4f}")  # Логирование в консоли

        messages = []
        if rsi < OVERSOLD:
            messages.append(f"⚠️ RSI = {rsi:.2f}, BTC перепродан! Возможен отскок 🚀")
        elif rsi > OVERBOUGHT:
            messages.append(f"⚠️ RSI = {rsi:.2f}, BTC перекуплен! Возможна коррекция 📉")

        if prev_macd < prev_signal and macd > signal:
            messages.append(f"🟢 MACD пересек сигнал вверх! Возможен рост 🚀")
        elif prev_macd > prev_signal and macd < signal:
            messages.append(f"🔴 MACD пересек сигнал вниз! Возможна коррекция 📉")

        for msg in messages:
            await bot.send_message(CHAT_ID, msg)

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Я бот для отслеживания RSI и MACD биткоина 📈")

# Запуск планировщика
async def on_startup(_):
    scheduler.add_job(check_indicators, "interval", minutes=30)  # Проверка каждые 30 минут
    scheduler.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
