import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import random
from datetime import datetime, timedelta
import threading
import time
import requests

# ========== توکن ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN)

# ========== دیتابیس ==========
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': [],
        'admins': [],
        'banned': [],
        'notes': {},
        'scores': {},
        'homeworks': []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== تنظیمات ==========
ADMIN_ID = 8481909076
ANONYMOUS_ID = 1087968824

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id == ANONYMOUS_ID

def is_banned(user_id):
    return user_id in load_data().get('banned', [])

def add_score(user_id, points):
    data = load_data()
    uid = str(user_id)
    data['scores'][uid] = data['scores'].get(uid, 0) + points
    save_data(data)
    return data['scores'][uid]

# ========== کیبورد اصلی ==========
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(KeyboardButton("📚 جزوه‌ها"), KeyboardButton("📤 آپلود جزوه"))
    keyboard.add(KeyboardButton("🏆 امتیاز من"), KeyboardButton("🎮 بازی"))
    keyboard.add(KeyboardButton("🌤 آب و هوا"), KeyboardButton("❓ راهنما"))
    if is_admin(user_id):
        keyboard.add(KeyboardButton("👑 پنل ادمین"))
    return keyboard

# ========== استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    data = load_data()
    if user_id not in data['users']:
        data['users'].append(user_id)
        data['scores'][str(user_id)] = 0
        save_data(data)
    
    bot.send_message(
        message.chat.id,
        f"🎉 سلام {message.from_user.first_name}!\n\nبه ربات گروه خوش اومدی!\n\nاز دکمه‌های زیر استفاده کن:",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== راهنما ==========
@bot.message_handler(func=lambda m: m.text == "❓ راهنما")
def help_menu(message):
    help_text = """
📚 **راهنمای ربات**

📌 **جزوه‌ها:**
• 📚 جزوه‌ها - مشاهده و دانلود جزوه
• 📤 آپلود جزوه - اشتراک جزوه جدید

🏆 **امتیازدهی:**
• +10 برای آپلود جزوه
• +2 برای دانلود جزوه
• +1 برای فعالیت روزانه

🎮 **بازی‌ها:**
• تاس انداختن و امتیاز گرفتن

🌤 **آب و هوا:**
• دریافت آب و هوای همدان
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# ========== جزوه‌ها ==========
@bot.message_handler(func=lambda m: m.text == "📚 جزوه‌ها")
def show_notes(message):
    data = load_data()
    categories = data.get('notes', {})
    
    if not categories:
        bot.reply_to(message, "📭 هنوز جزوه‌ای آپلود نشده!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories.keys():
        count = len(categories[cat])
        keyboard.add(InlineKeyboardButton(f"📁 {cat} ({count})", callback_data=f"cat_{cat}"))
    
    bot.send_message(message.chat.id, "📚 **دسته‌بندی جزوه‌ها:**", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def show_category(call):
    category = call.data.replace("cat_", "")
    data = load_data()
    notes = data['notes'].get(category, [])
    
    if not notes:
        bot.answer_callback_query(call.id, "هیچ جزوه‌ای نیست!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, note in enumerate(notes[-10:]):
        keyboard.add(InlineKeyboardButton(f"📄 {note['name'][:35]}", callback_data=f"view_{category}_{i}"))
    keyboard.add(InlineKeyboardButton("🔙 برگشت", callback_data="back_notes"))
    
    bot.edit_message_text(
        f"📁 **{category}** ({len(notes)} جزوه)",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_note(call):
    parts = call.data.split("_")
    category = parts[1]
    index = int(parts[2])
    
    data = load_data()
    notes = data['notes'].get(category, [])
    
    if index >= len(notes):
        bot.answer_callback_query(call.id, "جزوه یافت نشد!")
        return
    
    note = notes[-(index + 1)]
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📥 دانلود", callback_data=f"download_{category}_{index}"),
        InlineKeyboardButton("🔙 برگشت", callback_data=f"cat_{category}")
    )
    
    bot.send_message(
        call.message.chat.id,
        f"📄 **{note['name']}**\n👤 {note.get('uploader_name', 'ناشناس')}\n📅 {note.get('date', 'نامشخص')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("download_"))
def download_note(call):
    parts = call.data.split("_")
    category = parts[1]
    index = int(parts[2])
    
    data = load_data()
    notes = data['notes'].get(category, [])
    
    if index >= len(notes):
        bot.answer_callback_query(call.id, "جزوه یافت نشد!")
        return
    
    note = notes[-(index + 1)]
    bot.send_document(call.message.chat.id, note['file_id'])
    add_score(call.from_user.id, 2)
    bot.answer_callback_query(call.id, "✅ جزوه ارسال شد! +2 امتیاز")

@bot.callback_query_handler(func=lambda call: call.data == "back_notes")
def back_to_notes(call):
    data = load_data()
    categories = data.get('notes', {})
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories.keys():
        count = len(categories[cat])
        keyboard.add(InlineKeyboardButton(f"📁 {cat} ({count})", callback_data=f"cat_{cat}"))
    
    bot.edit_message_text(
        "📚 **دسته‌بندی جزوه‌ها:**",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

# ========== آپلود جزوه ==========
@bot.message_handler(func=lambda m: m.text == "📤 آپلود جزوه")
def upload_note(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 شما بن هستید!")
        return
    
    msg = bot.reply_to(
        message,
        "📤 **آپلود جزوه**\n\n"
        "اول نام دسته رو بفرست (مثل `ریاضی`)\n"
        "بعد فایل رو بفرست.\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, get_category)

def get_category(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    category = message.text.strip()
    msg = bot.reply_to(message, f"دسته **{category}** انتخاب شد.\nحالا فایل جزوه رو بفرست:")
    bot.register_next_step_handler(msg, save_note, category)

def save_note(message, category):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    if not (message.document or message.photo):
        bot.reply_to(message, "❌ لطفا یک فایل معتبر بفرست!")
        return
    
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    file_name = message.document.file_name if message.document else f"image_{int(time.time())}.jpg"
    
    data = load_data()
    if category not in data['notes']:
        data['notes'][category] = []
    
    data['notes'][category].append({
        'file_id': file_id,
        'name': file_name,
        'uploader': message.from_user.id,
        'uploader_name': message.from_user.first_name,
        'date': str(datetime.now())
    })
    save_data(data)
    
    score = add_score(message.from_user.id, 10)
    bot.reply_to(message, f"✅ جزوه «{file_name}» در دسته {category} ذخیره شد!\n🌟 +10 امتیاز (کل: {score})")

# ========== امتیاز من ==========
@bot.message_handler(func=lambda m: m.text == "🏆 امتیاز من")
def my_score(message):
    data = load_data()
    uid = str(message.from_user.id)
    score = data['scores'].get(uid, 0)
    
    level = 1 + (score // 100)
    next_level = (level * 100) - score
    
    bot.send_message(
        message.chat.id,
        f"🏆 **کارنامه {message.from_user.first_name}**\n\n"
        f"🌟 امتیاز: {score}\n"
        f"📊 سطح: {level}\n"
        f"🔜 تا سطح بعد: {next_level} امتیاز",
        parse_mode='Markdown'
    )

# ========== بازی ==========
@bot.message_handler(func=lambda m: m.text == "🎮 بازی")
def games_menu(message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎲 تاس", callback_data="game_dice"),
        InlineKeyboardButton("🎯 حدس عدد", callback_data="game_number")
    )
    bot.send_message(message.chat.id, "🎮 **یک بازی رو انتخاب کن:**", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    dice = random.randint(1, 6)
    points = dice * 2
    add_score(call.from_user.id, points)
    bot.send_dice(call.message.chat.id)
    bot.send_message(call.message.chat.id, f"🎲 عدد {dice} اومد!\n🌟 +{points} امتیاز")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_number")
def play_number(call):
    number = random.randint(1, 50)
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎯 یه عدد بین 1 تا 50 حدس بزن:")
    bot.register_next_step_handler(msg, check_guess, number, 3)

def check_guess(message, target, attempts):
    try:
        guess = int(message.text)
        if guess == target:
            add_score(message.from_user.id, 15)
            bot.reply_to(message, f"🎉 تبریک! درست بود! +15 امتیاز")
        elif attempts > 1:
            hint = "بزرگ‌تر" if guess < target else "کوچک‌تر"
            msg = bot.reply_to(message, f"❌ نه! عدد {hint} از {guess} هست.\n🔁 {attempts-1} شانس دیگه داری!")
            bot.register_next_step_handler(msg, check_guess, target, attempts-1)
        else:
            bot.reply_to(message, f"😔 بازی تموم شد! عدد {target} بود.")
    except:
        bot.reply_to(message, "❌ یه عدد بفرست!")

# ========== آب و هوا ==========
@bot.message_handler(func=lambda m: m.text == "🌤 آب و هوا")
def weather(message):
    try:
        response = requests.get("https://wttr.in/Hamedan?format=%C+%t+%w&lang=fa")
        weather_data = response.text.strip()
        bot.reply_to(message, f"🌤 **آب و هوای همدان**\n\n{weather_data}", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ خطا در دریافت آب و هوا!")

# ========== پنل ادمین ==========
@bot.message_handler(func=lambda m: m.text == "👑 پنل ادمین")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("📢 اعلان", callback_data="admin_broadcast"),
        InlineKeyboardButton("🚫 بن", callback_data="admin_ban"),
        InlineKeyboardButton("🗑 پاکسازی", callback_data="admin_purge")
    )
    bot.send_message(message.chat.id, "👑 **پنل ادمین**", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    data = load_data()
    total_notes = sum(len(n) for n in data['notes'].values())
    stats = f"📊 **آمار**\n\n👥 کاربران: {len(data['users'])}\n📚 جزوات: {total_notes}\n🏆 مجموع امتیاز: {sum(data['scores'].values())}"
    bot.send_message(call.message.chat.id, stats, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def broadcast_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 متن اعلان رو بفرست:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    data = load_data()
    users = data.get('users', [])
    success = 0
    
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **اعلان گروهی:**\n\n{message.text}")
            success += 1
        except:
            pass
        time.sleep(0.05)
    
    bot.reply_to(message, f"✅ اعلان به {success} نفر ارسال شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban")
def ban_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🚫 ایدی یا یوزرنیم کاربر رو برای بن بفرست:")
    bot.register_next_step_handler(msg, ban_user)

def ban_user(message):
    try:
        target = message.text
        if target.startswith('@'):
            user = bot.get_chat(target)
            user_id = user.id
        else:
            user_id = int(target)
        
        data = load_data()
        if user_id not in data['banned']:
            data['banned'].append(user_id)
        save_data(data)
        
        bot.reply_to(message, f"✅ کاربر {target} بن شد!")
    except:
        bot.reply_to(message, "❌ کاربر پیدا نشد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_purge")
def purge_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🗑 تعداد پیام برای پاک کردن رو بفرست (حداکثر 50):")
    bot.register_next_step_handler(msg, purge_messages)

def purge_messages(message):
    try:
        count = min(int(message.text), 50)
        chat_id = message.chat.id
        msg_id = message.message_id
        
        deleted = 0
        for i in range(count):
            try:
                bot.delete_message(chat_id, msg_id - i)
                deleted += 1
            except:
                pass
            time.sleep(0.1)
        
        bot.reply_to(message, f"✅ {deleted} پیام پاک شد!")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کن!")

# ========== عضو جدید ==========
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            continue
        bot.send_message(message.chat.id, f"🎉 به {member.first_name} عزیز خوش اومدی!")
        add_score(member.id, 5)

# ========== فعالیت روزانه ==========
@bot.message_handler(func=lambda m: True)
def daily_activity(message):
    if is_banned(message.from_user.id):
        bot.delete_message(message.chat.id, message.message_id)
        return
    
    data = load_data()
    uid = str(message.from_user.id)
    
    last = data.get('last_active', {}).get(uid, 0)
    if time.time() - last > 300:  # هر 5 دقیقه یک بار
        add_score(message.from_user.id, 1)
        if 'last_active' not in data:
            data['last_active'] = {}
        data['last_active'][uid] = time.time()
        save_data(data)

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات روشن شد!")
    bot.infinity_polling(timeout=60)