import asyncio
import logging
import os
import random
import string
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, SuccessfulPayment
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, run_app
from aiohttp import web

# ──────── НАСТРОЙКИ из переменных Render ────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # твой ID
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "381764678:TEST:749945490")  # тестовый или боевой

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# База данных
conn = sqlite3.connect("keys.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keys 
             (key_text TEXT PRIMARY KEY, used INTEGER, user_id INTEGER, android_id TEXT, tg_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS payments 
             (user_id INTEGER, amount INTEGER, currency TEXT, date TEXT)''')
conn.commit()

def generate_key():
    parts = []
    for _ in range(3):
        parts.append("".join(random.choices(string.asciiUpperCase + string.digits, k=6)))
    return "PH-" + "-".join(parts)

# ──────── КОМАНДЫ ────────
@dp.message(Command("start"))
async def start(message: Message):
    kb = [
        [types.KeyboardButton(text="Купить ключ навсегда — 1490 ₽")],
        [types.KeyboardButton(text="Проверить ключ")],
        [types.KeyboardButton(text="Поддержка")],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "🔥 <b>PhantomTG Premium</b>\n\n"
        "Одноразовый ключ навсегда — 1490 ₽\n"
        "Все функции мода открываются навсегда после оплаты.\n\n"
        "Выбери действие 👇",
        reply_markup=keyboard
    )

@dp.message(F.text == "Купить ключ навсегда — 1490 ₽")
async def buy_rub(message: Message):
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="PhantomTG Premium — навсегда",
        description="Полный доступ ко всем функциям мода навсегда",
        payload="premium_key_1490",
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="PhantomTG Premium", amount=1490 * 100)],
        start_parameter="phantomtg-premium"
    )

@dp.message(F.text == "Проверить ключ")
async def check_key(message: Message):
    await message.answer("Пришли мне ключ в формате PH-XXXXXX-XXXXXX-XXXXXX")

@dp.message(F.text.startswith("PH-"))
async def activate_key(message: Message):
    key = message.text.strip()
    c.execute("SELECT used FROM keys WHERE key_text = ?", (key,))
    row = c.fetchone()
    if row and row[0] == 0:
        c.execute("UPDATE keys SET used = 1, user_id = ? WHERE key_text = ?", (message.from_user.id, key))
        conn.commit()
        await message.answer("✅ Ключ успешно активирован!\nВсе функции мода открыты навсегда 🔥")
    elif row and row[0] == 1:
        await message.answer("❌ Этот ключ уже использован")
    else:
        await message.answer("❌ Ключ не найден")

# ──────── ОПЛАТА ────────
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    key = generate_key()
    
    c.execute("INSERT INTO keys (key_text, used, user_id) VALUES (?, 0, ?)", (key, user_id))
    conn.commit()
    
    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"🔑 Твой ключ: <code>{key}</code>\n\n"
        "Зайди в мод → Настройки → Активация → вставить этот ключ\n"
        "Функции открываются навсегда ✊\n\n"
        "Скачать мод: @PhantomTG_official",
        disable_web_page_preview=True
    )

# Админка
@dp.message(Command("panel"))
async def panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE used = 1")
    sold = c.fetchone()[0]
    await message.answer(f"Всего ключей: {total}\nПродано: {sold}")

# ──────── WEBHOOK ЗАПУСК ДЛЯ RENDER ────────
async def on_startup(dispatcher: Dispatcher):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{os.getenv('RENDER_EXTERNAL_URL_PATH', '')}/webhook"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")

async def main():
    # Запуск webhook-сервера
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    app.on_startup.append(lambda _: on_startup(dp))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
    logging.info("Бот запущен на Render!")
    
    # Держим процесс живым
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
