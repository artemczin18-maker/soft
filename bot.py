import telebot
import requests
import json
import random
import string
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

class S(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', 10000), S).serve_forever(), daemon=True).start()

TOKEN = "8954970328:AAGgtEdrWQ565LIdf-yEbZSoPLCbOvbzke8"
ADMIN_ID = 7984990535
SUPPORT_USER = "@dwnside"
CRYPTO_TOKEN = "583888:AAvkyapiOvVdkUY8yTfKsoomlA6nfuXOlnE"
CRYPTO_API = "https://pay.crypt.bot/api"

TARIFFS = {
    "week": {"name": "1 неделя", "price": 199, "days": 7},
    "month": {"name": "1 месяц", "price": 400, "days": 30},
    "year": {"name": "1 год", "price": 1800, "days": 365}
}

USERS = {}
PENDING = {}

bot = telebot.TeleBot(TOKEN)

def generate_key():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f"GHOST-{parts[0]}-{parts[1]}-{parts[2]}"

def create_invoice(amount_rub, uid, tariff):
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {
        "asset": "USDT",
        "amount": round(amount_rub / 90, 2),
        "description": f"Подписка {TARIFFS[tariff]['name']}",
        "hidden_message": f"{uid}_{tariff}",
        "expires_in": 1800
    }
    r = requests.post(f"{CRYPTO_API}/createInvoice", json=data, headers=headers)
    if r.status_code == 200:
        inv = r.json()["result"]
        PENDING[inv["invoice_id"]] = (uid, tariff)
        return inv
    return None

def check_payment(inv_id):
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    r = requests.post(f"{CRYPTO_API}/getInvoices", json={"invoice_ids": [inv_id]}, headers=headers)
    if r.status_code == 200:
        return r.json()["result"]["items"][0]["status"]
    return "error"

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛒 Купить софт", "👤 Профиль")
    markup.row("📞 Поддержка")
    return markup

def buy_menu():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📅 1 неделя — 199₽", callback_data="buy_week"))
    markup.add(telebot.types.InlineKeyboardButton("📅 1 месяц — 400₽", callback_data="buy_month"))
    markup.add(telebot.types.InlineKeyboardButton("📅 1 год — 1800₽", callback_data="buy_year"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return markup

def pay_menu(tariff):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💵 USDT", callback_data=f"pay_usdt_{tariff}"))
    markup.add(telebot.types.InlineKeyboardButton("💎 Telegram Stars", callback_data=f"pay_stars_{tariff}"))
    markup.add(telebot.types.InlineKeyboardButton("₽ Рубли", callback_data=f"pay_rub_{tariff}"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="back_buy"))
    return markup

def activate_sub(uid, days):
    now = datetime.now()
    if uid not in USERS:
        USERS[uid] = {"sub_end": None, "purchases": [], "keys": []}
    if USERS[uid].get("sub_end") and USERS[uid]["sub_end"] > now:
        USERS[uid]["sub_end"] += timedelta(days=days)
    else:
        USERS[uid]["sub_end"] = now + timedelta(days=days)

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in USERS:
        USERS[uid] = {"sub_end": None, "purchases": [], "keys": []}
    bot.send_message(message.chat.id,
        "🤖 Добро пожаловать в магазин софта!\n\nВыбери действие:",
        reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🛒 Купить софт")
def buy(message):
    bot.send_message(message.chat.id, "📋 Выбери тариф:", reply_markup=buy_menu())

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    uid = message.from_user.id
    u = USERS.get(uid, {"sub_end": None, "purchases": [], "keys": []})
    
    sub_text = "Нет активной подписки"
    if u.get("sub_end"):
        remaining = (u["sub_end"] - datetime.now()).days
        if remaining > 0:
            sub_text = f"Активна до: {u['sub_end'].strftime('%d.%m.%Y')} ({remaining} дн)"
        else:
            sub_text = "Подписка истекла"
    
    keys_text = ""
    if u.get("keys"):
        keys_text = "\n\n🔑 Ключи:\n" + "\n".join([f"• {k['key']} ({k['tariff']}, до {k['end'].strftime('%d.%m')})" for k in u["keys"]])
    
    text = f"👤 Профиль\n\n📅 Подписка: {sub_text}\n🛒 Покупок: {len(u.get('purchases', []))}{keys_text}"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📞 Поддержка")
def support(message):
    bot.send_message(message.chat.id,
        f"📞 Связь с поддержкой: {SUPPORT_USER}\nНапиши в личные сообщения.",
        reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def buy_tariff(call):
    tariff = call.data.split("_")[1]
    t = TARIFFS[tariff]
    bot.edit_message_text(
        f"📋 Тариф: {t['name']}\n💰 Цена: {t['price']}₽\n📅 Срок: {t['days']} дней\n\nВыбери способ оплаты:",
        call.message.chat.id, call.message.message_id, reply_markup=pay_menu(tariff))

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_usdt_"))
def pay_usdt(call):
    uid = call.from_user.id
    tariff = call.data.split("_")[2]
    price = TARIFFS[tariff]["price"]
    
    inv = create_invoice(price, uid, tariff)
    if inv:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("💵 Оплатить USDT", url=inv["pay_url"]))
        markup.add(telebot.types.InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{inv['invoice_id']}"))
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data=f"buy_{tariff}"))
        
        bot.edit_message_text(
            f"📥 Счёт на {price}₽ (~{round(price/90,2)} USDT)\n📅 Тариф: {TARIFFS[tariff]['name']}\n⏳ Действует 30 минут",
            call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка создания счёта", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("check_"))
def check_usdt(call):
    inv_id = int(call.data.split("_")[1])
    status = check_payment(inv_id)
    
    if status == "paid":
        uid, tariff = PENDING.get(inv_id, (None, None))
        if uid:
            days = TARIFFS[tariff]["days"]
            activate_sub(uid, days)
            key = generate_key()
            if uid not in USERS:
                USERS[uid] = {"sub_end": None, "purchases": [], "keys": []}
            USERS[uid]["purchases"].append({"tariff": tariff, "date": datetime.now().strftime("%d.%m.%Y")})
            USERS[uid]["keys"].append({
                "key": key,
                "tariff": TARIFFS[tariff]["name"],
                "end": USERS[uid]["sub_end"]
            })
            
            bot.send_message(call.message.chat.id,
                f"✅ Подписка активирована!\n📅 Тариф: {TARIFFS[tariff]['name']}\n📅 До: {USERS[uid]['sub_end'].strftime('%d.%m.%Y')}\n\n🔑 Раздел ключ: {key}\n\n📁 Для получения файла напиши в лс: {SUPPORT_USER}")
            del PENDING[inv_id]
    elif status == "expired":
        bot.send_message(call.message.chat.id, "⏰ Счёт истёк")
        del PENDING[inv_id]
    else:
        bot.answer_callback_query(call.id, "⏳ Оплата ещё не поступила", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_stars_"))
def pay_stars(call):
    tariff = call.data.split("_")[2]
    t = TARIFFS[tariff]
    
    prices = [telebot.types.LabeledPrice(label=t['name'], amount=t['price'] * 100)]
    bot.send_invoice(
        call.message.chat.id,
        title="Подписка на софт",
        description=f"Тариф: {t['name']} ({t['days']} дней)",
        invoice_payload=f"sub_{tariff}_{call.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    payload = message.successful_payment.invoice_payload
    _, tariff, uid_str = payload.split("_")
    uid = int(uid_str)
    days = TARIFFS[tariff]["days"]
    
    activate_sub(uid, days)
    key = generate_key()
    if uid not in USERS:
        USERS[uid] = {"sub_end": None, "purchases": [], "keys": []}
    USERS[uid]["purchases"].append({"tariff": tariff, "date": datetime.now().strftime("%d.%m.%Y")})
    USERS[uid]["keys"].append({
        "key": key,
        "tariff": TARIFFS[tariff]["name"],
        "end": USERS[uid]["sub_end"]
    })
    
    bot.send_message(message.chat.id,
        f"✅ Подписка активирована!\n📅 Тариф: {TARIFFS[tariff]['name']}\n📅 До: {USERS[uid]['sub_end'].strftime('%d.%m.%Y')}\n\n🔑 Раздел ключ: {key}\n\n📁 Для получения файла напиши в лс: {SUPPORT_USER}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_rub_"))
def pay_rub(call):
    tariff = call.data.split("_")[2]
    t = TARIFFS[tariff]
    bot.send_message(call.message.chat.id,
        f"📞 Для покупки за рубли напиши в лс: {SUPPORT_USER}\n\nТема: Покупка софта ({t['name']} — {t['price']}₽)\n\nПосле оплаты подписка будет активирована вручную.")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def back_main(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🤖 Главное меню\n\nВыбери действие:", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "back_buy")
def back_buy(call):
    bot.edit_message_text("📋 Выбери тариф:", call.message.chat.id, call.message.message_id, reply_markup=buy_menu())

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = len(USERS)
    active_subs = sum(1 for u in USERS.values() if u.get("sub_end") and u["sub_end"] > datetime.now())
    
    bot.send_message(message.chat.id,
        f"📊 Админ-панель\n\n👥 Пользователей: {total_users}\n✅ Активных подписок: {active_subs}")

print("SOFT SHOP BOT STARTED")
bot.polling(none_stop=True)
