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

# Функция проверки RSI и отправки уведомлений
async def check_rsi():
    prices = get_btc_prices()
    if prices:
        rsi = calculate_rsi(prices)
        print(f"RSI: {rsi}")  # Логирование в консоли

        if rsi < OVERSOLD:
            await bot.send_message(CHAT_ID, f"⚠️ RSI = {rsi:.2f}, BTC перепродан! Возможен отскок 🚀")
        elif rsi > OVERBOUGHT:
            await bot.send_message(CHAT_ID, f"⚠️ RSI = {rsi:.2f}, BTC перекуплен! Возможна коррекция 📉")

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Я бот для отслеживания RSI биткоина 📈")

# Запуск планировщика
async def on_startup(_):
    scheduler.add_job(check_rsi, "interval", minutes=30)  # Проверка каждые 30 минут
    scheduler.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
