import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, ContentType
import sqlite3
import random
import string
import uuid

# ──────── НАСТРОЙКИ ────────
BOT_TOKEN = "8458741733:AAFEUhMaLJJdmDiyJ1cQgoNSlqXTxUCi6OA"  # твой токен уже тут
ADMIN_ID = 6895862356  # ←←←←← СЮДА ВСТАВЬ СВОЙ ТЕЛЕГРАМ ID (обязательно!)

# Цены (можно менять)
PRICE_RUB = 1490
PRICE_USDT = 17
PRICE_TON = 500

# CryptoBot токен (пока оставь пустым, потом вставишь)
CRYPTOBOT_TOKEN = ""

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных
conn = sqlite3.connect('keys.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keys 
             (key_text TEXT, used INTEGER, user_id INTEGER, android_id TEXT, tg_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS payments 
             (user_id INTEGER, amount INTEGER, currency TEXT, date TEXT)''')
conn.commit()

def generate_key():
    return "PH-" + "".join(random.choices(string.asciiUpperCase + string.digits, k=6)) + \
           "-" + "".join(random.choices(string.asciiUpperCase + string.digits, k=6)) + \
           "-" + "".join(random.choices(string.asciiUpperCase + string.digits, k=6))

# ──────── КОМАНДЫ ────────
@dp.message(Command("start"))
async def start(message: Message):
    kb = [
        [types.KeyboardButton(text="Купить ключ навсегда — 1490 ₽")],
        [types.KeyboardButton(text="Оплата криптой (USDT/TON)")],
        [types.KeyboardButton(text="Проверить ключ")],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "🔥 <b>PhantomTG Premium</b>\n\n"
        "Одноразовый ключ навсегда — 1490 ₽\n"
        "После оплаты все функции мода открываются навсегда.\n\n"
        "Выбери способ оплаты 👇",
        reply_markup=keyboard, parse_mode="HTML"
    )

@dp.message(F.text == "Купить ключ навсегда — 1490 ₽")
async def buy_rub(message: Message):
    prices = [LabeledPrice(label="PhantomTG Premium навсегда", amount=PRICE_RUB * 100)]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="PhantomTG Premium — навсегда",
        description="Одноразовый ключ для полного доступа ко всем функциям мода",
        payload="premium_key",
        provider_token="381764678:TEST:749945490",  # ← ТЕСТОВЫЙ ТОКЕН (потом заменишь на боевой ЮKassa/CrystalPay)
        currency="RUB",
        prices=prices,
        start_parameter="phantomtg"
    )

@dp.message(F.text == "Проверить ключ")
async def check_key(message: Message):
    await message.answer("Пришли мне ключ в формате PH-XXXXXX-XXXXXX-XXXXXX")

# ──────── ОПЛАТА ────────
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    key = generate_key()
    c.execute("INSERT INTO keys (key_text, used, user_id) VALUES (?, 0, ?)", (key, user_id))
    conn.commit()
    
    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🔑 Твой ключ: <code>{key}</code>\n\n"
        "Зайди в мод → Настройки → Активация → вставить ключ\n"
        "Функции откроются навсегда ✊\n\n"
        "Скачать мод: @PhantomTG_official",
        parse_mode="HTML"
    )

# ──────── АДМИНКА ────────
@dp.message(Command("panel"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM payments")
    sales = c.fetchone()[0]
    await message.answer(f"Продано ключей: {sales}\nСделай /stats для полной статистики")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
