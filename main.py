import asyncio
import logging
import os
import random
import string
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, SuccessfulPayment
from aiogram.client.default import DefaultBotProperties

# ──────── НАСТРОЙКИ ────────
BOT_TOKEN = "8458741733:AAFEUhMaLJJdmDiyJ1cQgoNSlqXTxUCi6OA" 
ADMIN_ID = 6895862356

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# База данных
conn = sqlite3.connect("keys.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keys 
             (key_text TEXT PRIMARY KEY, used INTEGER DEFAULT 0, user_id INTEGER, android_id TEXT, tg_id INTEGER, created_at TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS payments 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, currency TEXT, date TEXT)''')
conn.commit()

def generate_key():
    parts = []
    for _ in range(3):
        parts.append("".join(random.choices(string.ascii_uppercase + string.digits, k=6)))
    return "PH-" + "-".join(parts)

# ──────── КОМАНДЫ ────────
@dp.message(Command("start"))
async def start_handler(message: Message):
    kb = [
        [types.KeyboardButton(text="💳 Купить ключ навсегда — 1490 ₽")],
        [types.KeyboardButton(text="🔑 Проверить ключ")],
        [types.KeyboardButton(text="ℹ️ Поддержка")],
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)
    await message.answer(
        "🔥 <b>PhantomTG Premium — активация</b>\n\n"
        "Одноразовый ключ даёт <b>полный доступ навсегда</b>:\n"
        "• Анти-удаление сообщений\n"
        "• Режим призрака\n"
        "• Автоперевод и многое другое\n\n"
        "Цена: <b>1490 ₽</b> (или эквивалент в крипте позже)\n\n"
        "Выбери действие 👇",
        reply_markup=keyboard
    )

@dp.message(F.text == "💳 Купить ключ навсегда — 1490 ₽")
async def buy_rub_handler(message: Message):
    prices = [LabeledPrice(label="PhantomTG Premium навсегда", amount=1490 * 100)]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="🔑 PhantomTG Premium — навсегда",
        description="Полный доступ ко всем функциям мода. Ключ активируется один раз и работает вечно!",
        payload=f"premium_key_{message.from_user.id}",
        provider_token="381764678:TEST:749945490",  # тестовый, потом боевой
        currency="RUB",
        prices=prices,
        start_parameter="phantomtg_buy"
    )

@dp.message(F.text == "🔑 Проверить ключ")
async def check_key_handler(message: Message):
    await message.answer("📝 Пришли ключ в формате <code>PH-XXXXXX-XXXXXX-XXXXXX</code>\n\nПример: PH-A1B2C3-D4E5F6-G7H8I9", parse_mode="HTML")

@dp.message(F.text.startswith("PH-") & F.text.len >= 20)
async def validate_key_handler(message: Message):
    key = message.text.strip()
    c.execute("SELECT used, user_id FROM keys WHERE key_text = ?", (key,))
    row = c.fetchone()
    if row:
        if row[1] == message.from_user.id and row[0] == 0:
            c.execute("UPDATE keys SET used = 1, tg_id = ? WHERE key_text = ?", (message.from_user.id, key))
            conn.commit()
            await message.answer("✅ <b>Ключ активирован!</b>\n\nТеперь все премиум-функции доступны в моде PhantomTG.\nСпасибо за покупку! 🚀", parse_mode="HTML")
        elif row[0] == 1:
            await message.answer("❌ Этот ключ уже использован на другом устройстве/аккаунте.")
        else:
            await message.answer("❌ Ключ не привязан к твоему аккаунту.")
    else:
        await message.answer("❌ Неверный ключ. Проверь формат и попробуй снова.")

@dp.message(F.text == "ℹ️ Поддержка")
async def support_handler(message: Message):
    await message.answer("💬 Вопросы? Пиши админу: @твой_username\n\nИли /panel для статистики (только админ).")

# ──────── ОПЛАТА ────────
@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message, successful_payment: SuccessfulPayment):
    user_id = message.from_user.id
    key = generate_key()
    created_at = datetime.now().isoformat()
    
    c.execute("INSERT INTO keys (key_text, used, user_id, created_at) VALUES (?, 0, ?, ?)", (key, user_id, created_at))
    c.execute("INSERT INTO payments (user_id, amount, currency, date) VALUES (?, ?, ?, ?)", 
              (user_id, successful_payment.total_amount, successful_payment.currency, created_at))
    conn.commit()
    
    kb = [[types.KeyboardButton(text="🔑 Активировать ключ")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer(
        "🎉 <b>Оплата успешна!</b>\n\n"
        f"🔑 Твой уникальный ключ: <code>{key}</code>\n\n"
        "📱 <b>Как активировать:</b>\n"
        "1. Скачай мод @PhantomTG (APK из канала)\n"
        "2. Открой Настройки → Активация\n"
        "3. Вставь ключ и сохрани\n\n"
        "Функции откроются мгновенно! ✊\n\n"
        "Нажми кнопку ниже для активации в боте:",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Админ-панель
@dp.message(Command("panel"))
async def admin_panel_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещён.")
        return
    
    c.execute("SELECT COUNT(*) FROM keys")
    total_keys = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE used = 1")
    activated = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM payments")
    sales = c.fetchone()[0]
    
    stats_text = f"""
📊 <b>Статистика PhantomTG:</b>
• Сгенерировано ключей: {total_keys}
• Активировано: {activated}
• Продаж: {sales}
• Доход (₽): {sales * 1490}

Команды: /generate_key (ручной ключ)
    """
    await message.answer(stats_text, parse_mode="HTML")

@dp.message(Command("generate_key"))
async def generate_manual_key(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    key = generate_key()
    c.execute("INSERT INTO keys (key_text, used, created_at) VALUES (?, 0, ?)", (key, datetime.now().isoformat()))
    conn.commit()
    await message.answer(f"🔑 Ручной ключ: <code>{key}</code>\n(Выдай пользователю вручную)", parse_mode="HTML")

# ──────── POLLING ЗАПУСК (для Render) ────────
async def main():
    # Удаляем старый webhook
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🧹 Старый webhook удалён, переходим на polling")
    
    # Запуск polling
    await dp.start_polling(bot)
    logging.info("🚀 Бот запущен на polling!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
