import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import random
from datetime import datetime, timedelta
import threading
import time
import requests
import re

# ========== توکن ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN)

# ========== دیتابیس ==========
DATA_FILE = 'group_bot_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': [],
        'admins': [],
        'banned_users': [],
        'muted_users': {},
        'warnings': {},
        'scheduled_messages': [],
        'welcome_gif': None,
        'welcome_text': "به گروه خوش آمدی {name} عزیز! 🌟\nامیدوارم لحظات خوبی رو اینجا داشته باشی."
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== تنظیمات ==========
ADMIN_ID = 8481909076  # ایدی خودت رو اینجا بذار!
HAMADAN_CITY = "Hamedan"

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in load_data().get('admins', [])

def is_banned(user_id):
    return user_id in load_data().get('banned_users', [])

def is_muted(user_id, chat_id):
    data = load_data()
    muted = data['muted_users'].get(str(chat_id), {})
    if str(user_id) in muted:
        if datetime.now() < datetime.fromisoformat(muted[str(user_id)]):
            return True
        else:
            del muted[str(user_id)]
            save_data(data)
    return False

# ========== کیبورد اصلی ادمین ==========
def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("👑 پنل مدیریت"),
        KeyboardButton("📚 جزوات"),
        KeyboardButton("🎵 پخش آهنگ"),
        KeyboardButton("📅 کلاس‌ها")
    )
    return keyboard

def get_management_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔇 سکوت", callback_data="mute"),
        InlineKeyboardButton("🔊 رفع سکوت", callback_data="unmute"),
        InlineKeyboardButton("🚫 بن", callback_data="ban"),
        InlineKeyboardButton("✅ آنبن", callback_data="unban"),
        InlineKeyboardButton("⚠️ اخطار", callback_data="warn"),
        InlineKeyboardButton("🗑 پاکسازی", callback_data="purge"),
        InlineKeyboardButton("📝 پیام زمان‌دار", callback_data="schedule"),
        InlineKeyboardButton("🎉 تنظیم خوش‌آمدگویی", callback_data="set_welcome"),
        InlineKeyboardButton("📢 ارسال به کانال", callback_data="forward_channel"),
        InlineKeyboardButton("📊 آمار", callback_data="stats")
    )
    return keyboard

# ========== استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    data = load_data()
    if user_id not in data['users']:
        data['users'].append(user_id)
        save_data(data)
    
    bot.send_message(
        message.chat.id,
        f"🎉 سلام {message.from_user.first_name}!\n\n"
        f"به ربات مدیریت گروه خوش اومدی!\n\n"
        f"✨ **قابلیت‌ها:**\n"
        f"• 🔇 سکوت با ثانیه\n"
        f"• 🗑 پاکسازی پیام با تعداد دلخواه\n"
        f"• 📝 ارسال پیام زمان‌دار به گروه/کانال\n"
        f"• 🎉 خوش‌آمدگویی با گیف و اسم کاربر\n"
        f"• 📚 جزوه و فایل\n"
        f"• 🎵 پخش آهنگ\n"
        f"• 📅 یادآوری کلاس\n"
        f"• 🌤 آب و هوای همدان\n\n"
        f"برای دیدن منوی مدیریت، در گروه `/panel` رو بزن.",
        reply_markup=get_admin_keyboard() if is_admin(user_id) else None
    )

# ========== پنل مدیریت ==========
@bot.message_handler(commands=['panel'])
def panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین دسترسی داره!")
        return
    
    bot.send_message(
        message.chat.id,
        "👑 **پنل مدیریت گروه**\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=get_management_keyboard(),
        parse_mode='Markdown'
    )

# ========== 1. سکوت (با ثانیه) ==========
@bot.callback_query_handler(func=lambda call: call.data == "mute")
def mute_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🔇 **سکوت کاربر**\n\n"
        "فرمت مورد نظر:\n"
        "`@username ثانیه`\n"
        "یا\n"
        "`آیدی عددی ثانیه`\n\n"
        "مثال: `@ali 60` (یعنی 60 ثانیه)\n"
        "مثال: `123456789 120` (یعنی 2 دقیقه)\n\n"
        "برای لغو /cancel",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_mute)

def process_mute(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        
        target = parts[0]
        seconds = int(parts[1])
        
        # پیدا کردن user_id
        if target.startswith('@'):
            username = target[1:]
            try:
                user = bot.get_chat(username)
                user_id = user.id
            except:
                bot.reply_to(message, "❌ کاربر پیدا نشد!")
                return
        else:
            user_id = int(target)
        
        # ذخیره در دیتابیس
        data = load_data()
        chat_id = message.chat.id
        if str(chat_id) not in data['muted_users']:
            data['muted_users'][str(chat_id)] = {}
        data['muted_users'][str(chat_id)][str(user_id)] = (datetime.now() + timedelta(seconds=seconds)).isoformat()
        save_data(data)
        
        # اعمال محدودیت در گروه
        until_date = datetime.now() + timedelta(seconds=seconds)
        bot.restrict_chat_member(chat_id, user_id, until_date=until_date)
        
        bot.reply_to(
            message,
            f"✅ کاربر {target} برای {seconds} ثانیه سکوت شد!"
        )
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `@username 60`")

@bot.callback_query_handler(func=lambda call: call.data == "unmute")
def unmute_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🔊 **رفع سکوت کاربر**\n\n"
        "آیدی یا یوزرنیم کاربر رو بفرست:\n"
        "مثال: `@ali` یا `123456789`"
    )
    bot.register_next_step_handler(msg, process_unmute)

def process_unmute(message):
    try:
        target = message.text
        
        if target.startswith('@'):
            username = target[1:]
            user = bot.get_chat(username)
            user_id = user.id
        else:
            user_id = int(target)
        
        chat_id = message.chat.id
        bot.restrict_chat_member(chat_id, user_id, can_send_messages=True, can_send_media_messages=True)
        
        data = load_data()
        if str(chat_id) in data['muted_users'] and str(user_id) in data['muted_users'][str(chat_id)]:
            del data['muted_users'][str(chat_id)][str(user_id)]
        save_data(data)
        
        bot.reply_to(message, f"✅ سکوت کاربر {target} برداشته شد!")
    except:
        bot.reply_to(message, "❌ کاربر پیدا نشد!")

# ========== 2. بن ==========
@bot.callback_query_handler(func=lambda call: call.data == "ban")
def ban_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🚫 **بن کاربر**\n\n"
        "آیدی یا یوزرنیم کاربر رو بفرست:\n"
        "مثال: `@ali` یا `123456789`"
    )
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    try:
        target = message.text
        
        if target.startswith('@'):
            username = target[1:]
            user = bot.get_chat(username)
            user_id = user.id
        else:
            user_id = int(target)
        
        chat_id = message.chat.id
        bot.ban_chat_member(chat_id, user_id)
        
        data = load_data()
        if user_id not in data['banned_users']:
            data['banned_users'].append(user_id)
        save_data(data)
        
        bot.reply_to(message, f"✅ کاربر {target} بن شد!")
    except:
        bot.reply_to(message, "❌ کاربر پیدا نشد!")

@bot.callback_query_handler(func=lambda call: call.data == "unban")
def unban_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "✅ **آنبن کاربر**\n\n"
        "آیدی کاربر رو بفرست:\n"
        "مثال: `123456789`"
    )
    bot.register_next_step_handler(msg, process_unban)

def process_unban(message):
    try:
        user_id = int(message.text)
        chat_id = message.chat.id
        bot.unban_chat_member(chat_id, user_id)
        
        data = load_data()
        if user_id in data['banned_users']:
            data['banned_users'].remove(user_id)
        save_data(data)
        
        bot.reply_to(message, f"✅ کاربر {user_id} آنبن شد!")
    except:
        bot.reply_to(message, "❌ ایدی نامعتبر!")

# ========== 3. اخطار ==========
@bot.callback_query_handler(func=lambda call: call.data == "warn")
def warn_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "⚠️ **اخطار به کاربر**\n\n"
        "فرمت: `@username دلیل`\n"
        "مثال: `@ali اسپم`"
    )
    bot.register_next_step_handler(msg, process_warn)

def process_warn(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            raise ValueError
        
        target = parts[0]
        reason = parts[1]
        
        if target.startswith('@'):
            username = target[1:]
            user = bot.get_chat(username)
            user_id = user.id
        else:
            user_id = int(target)
        
        data = load_data()
        if str(user_id) not in data['warnings']:
            data['warnings'][str(user_id)] = []
        data['warnings'][str(user_id)].append({
            'reason': reason,
            'date': str(datetime.now()),
            'admin': message.from_user.first_name
        })
        
        warn_count = len(data['warnings'][str(user_id)])
        save_data(data)
        
        if warn_count >= 3:
            bot.ban_chat_member(message.chat.id, user_id)
            bot.reply_to(
                message,
                f"⚠️ کاربر {target} بعد از {warn_count} اخطار بن شد!\n"
                f"آخرین دلیل: {reason}"
            )
        else:
            bot.reply_to(
                message,
                f"⚠️ اخطار {warn_count}/3 به {target}\n"
                f"دلیل: {reason}"
            )
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `@username دلیل`")

# ========== 4. پاکسازی پیام ==========
@bot.callback_query_handler(func=lambda call: call.data == "purge")
def purge_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🗑 **پاکسازی پیام**\n\n"
        "تعداد پیام‌هایی که می‌خوای پاک بشه رو بفرست:\n"
        "مثال: `50` (یعنی 50 پیام آخر)\n\n"
        "حداکثر 100 پیام"
    )
    bot.register_next_step_handler(msg, process_purge)

def process_purge(message):
    try:
        count = int(message.text)
        if count > 100:
            count = 100
        
        chat_id = message.chat.id
        message_id = message.message_id
        
        deleted = 0
        for i in range(count):
            try:
                bot.delete_message(chat_id, message_id - i)
                deleted += 1
            except:
                pass
            time.sleep(0.1)
        
        bot.reply_to(message, f"✅ {deleted} پیام پاک شد!")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کن!")

# ========== 5. پیام زمان‌دار (به گروه/کانال) ==========
@bot.callback_query_handler(func=lambda call: call.data == "schedule")
def schedule_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 گروه فعلی", callback_data="schedule_group"),
        InlineKeyboardButton("📣 کانال", callback_data="schedule_channel")
    )
    bot.send_message(call.message.chat.id, "پیام زمان‌دار برای کجا ارسال بشه؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["schedule_group", "schedule_channel"])
def schedule_destination(call):
    dest = "group" if call.data == "schedule_group" else "channel"
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id,
        "📝 **پیام زمان‌دار**\n\n"
        "اول متن پیام رو بفرست.\n"
        "بعد از اون، زمان (به دقیقه) رو بفرست."
    )
    bot.register_next_step_handler(msg, get_schedule_text, dest)

def get_schedule_text(message, dest):
    text = message.text
    msg = bot.reply_to(message, "⏰ چند دقیقه بعد ارسال بشه؟ (عدد وارد کن)")
    bot.register_next_step_handler(msg, get_schedule_time, dest, text)

def get_schedule_time(message, dest, text):
    try:
        minutes = int(message.text)
        send_time = datetime.now() + timedelta(minutes=minutes)
        
        data = load_data()
        data['scheduled_messages'].append({
            'text': text,
            'dest': dest,
            'dest_id': message.chat.id if dest == 'group' else None,
            'time': send_time.isoformat()
        })
        save_data(data)
        
        bot.reply_to(
            message,
            f"✅ پیام در {minutes} دقیقه دیگه ارسال میشه!\n"
            f"مقصد: {'گروه فعلی' if dest == 'group' else 'کانال'}"
        )
        
        # تنظیم تایمر
        threading.Timer(minutes * 60, send_scheduled_message, args=[text, dest, message.chat.id]).start()
    except:
        bot.reply_to(message, "❌ زمان نامعتبر!")

def send_scheduled_message(text, dest, chat_id):
    if dest == 'group':
        bot.send_message(chat_id, f"📢 **پیام زمان‌دار:**\n\n{text}", parse_mode='Markdown')
    else:
        # برای کانال، باید channel_id رو ذخیره کنی
        bot.send_message(chat_id, f"📣 **ارسال به کانال:**\n\n{text}", parse_mode='Markdown')

# ========== 6. خوش‌آمدگویی با گیف و اسم ==========
@bot.callback_query_handler(func=lambda call: call.data == "set_welcome")
def set_welcome_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📝 متن خوش‌آمدگویی", callback_data="set_welcome_text"),
        InlineKeyboardButton("🎬 گیف خوش‌آمدگویی", callback_data="set_welcome_gif"),
        InlineKeyboardButton("❌ غیرفعال", callback_data="disable_welcome")
    )
    bot.send_message(call.message.chat.id, "🎉 **تنظیمات خوش‌آمدگویی**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_text")
def set_welcome_text_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📝 متن خوش‌آمدگویی رو وارد کن.\n\n"
        "از `{name}` برای اسم کاربر استفاده کن.\n"
        "مثال: `به گروه خوش اومدی {name} جان!`"
    )
    bot.register_next_step_handler(msg, save_welcome_text)

def save_welcome_text(message):
    data = load_data()
    data['welcome_text'] = message.text
    save_data(data)
    bot.reply_to(message, "✅ متن خوش‌آمدگویی ذخیره شد!")

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_gif")
def set_welcome_gif_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🎬 گیف خوش‌آمدگویی رو بفرست.\n\n"
        "یک فایل GIF بفرست."
    )
    bot.register_next_step_handler(msg, save_welcome_gif)

def save_welcome_gif(message):
    if message.animation:
        file_id = message.animation.file_id
        data = load_data()
        data['welcome_gif'] = file_id
        save_data(data)
        bot.reply_to(message, "✅ گیف خوش‌آمدگویی ذخیره شد!")
    else:
        bot.reply_to(message, "❌ لطفا یک فایل GIF بفرست!")

@bot.callback_query_handler(func=lambda call: call.data == "disable_welcome")
def disable_welcome(call):
    bot.answer_callback_query(call.id)
    data = load_data()
    data['welcome_gif'] = None
    data['welcome_text'] = None
    save_data(data)
    bot.reply_to(call.message, "❌ خوش‌آمدگویی غیرفعال شد!")

# عضو جدید به گروه اضافه شد
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    data = load_data()
    welcome_text = data.get('welcome_text')
    welcome_gif = data.get('welcome_gif')
    
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            continue
        
        name = new_member.first_name
        if new_member.last_name:
            name += " " + new_member.last_name
        
        if welcome_gif:
            try:
                bot.send_animation(
                    message.chat.id,
                    welcome_gif,
                    caption=welcome_text.format(name=name) if welcome_text else None
                )
            except:
                pass
        elif welcome_text:
            bot.send_message(
                message.chat.id,
                welcome_text.format(name=name)
            )

# ========== 7. ارسال به کانال ==========
@bot.callback_query_handler(func=lambda call: call.data == "forward_channel")
def forward_to_channel_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📢 **ارسال به کانال**\n\n"
        "آیدی کانال رو بفرست (مثل `@my_channel`)\n"
        "بعد از اون، پیام رو بفرست.\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, get_channel_id_for_forward)

def get_channel_id_for_forward(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    channel_id = message.text
    msg = bot.reply_to(message, f"📝 پیام مورد نظر رو برای ارسال به {channel_id} بفرست:")
    bot.register_next_step_handler(msg, send_to_channel, channel_id)

def send_to_channel(message, channel_id):
    try:
        if message.text:
            bot.send_message(channel_id, message.text)
        elif message.photo:
            bot.send_photo(channel_id, message.photo[-1].file_id, caption=message.caption)
        elif message.document:
            bot.send_document(channel_id, message.document.file_id, caption=message.caption)
        elif message.animation:
            bot.send_animation(channel_id, message.animation.file_id, caption=message.caption)
        
        bot.reply_to(message, f"✅ پیام به {channel_id} ارسال شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در ارسال: ربات رو ادمین کانال کن!")

# ========== 8. آب و هوای همدان ==========
@bot.message_handler(commands=['weather'])
def weather_hamadan(message):
    try:
        # استفاده از API رایگان wttr.in
        response = requests.get(f"https://wttr.in/{HAMADAN_CITY}?format=%C+%t+%w+%h")
        weather_data = response.text.strip()
        
        if weather_data:
            bot.reply_to(
                message,
                f"🌤 **آب و هوای همدان**\n\n"
                f"{weather_data}\n\n"
                f"📅 {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
        else:
            bot.reply_to(message, "❌ دریافت آب و هوا انجام نشد!")
    except:
        bot.reply_to(message, "❌ خطا در دریافت اطلاعات!")

# ========== 9. کلاس و یادآوری ==========
@bot.message_handler(commands=['addclass'])
def add_class(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    msg = bot.reply_to(
        message,
        "📅 **افزودن کلاس جدید**\n\n"
        "فرمت:\n"
        "`اسم کلاس|ساعت|دقیقه|تکرار`\n\n"
        "مثال: `ریاضی|14|30|شنبه`\n"
        "مثال: `فیزیک|10|0|یکشنبه,سه‌شنبه`"
    )
    bot.register_next_step_handler(msg, save_class)

def save_class(message):
    try:
        parts = message.text.split('|')
        if len(parts) >= 3:
            class_name = parts[0]
            hour = int(parts[1])
            minute = int(parts[2])
            repeat = parts[3] if len(parts) > 3 else "یکبار"
            
            data = load_data()
            if 'classes' not in data:
                data['classes'] = []
            data['classes'].append({
                'name': class_name,
                'hour': hour,
                'minute': minute,
                'repeat': repeat,
                'chat_id': message.chat.id
            })
            save_data(data)
            
            bot.reply_to(
                message,
                f"✅ کلاس «{class_name}» ذخیره شد!\n"
                f"⏰ ساعت {hour}:{minute:02d}\n"
                f"📅 تکرار: {repeat}"
            )
            
            # تنظیم یادآوری برای امروز
            now = datetime.now()
            class_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if class_time > now:
                seconds = (class_time - now).seconds
                threading.Timer(seconds, send_class_reminder, args=[message.chat.id, class_name]).start()
        else:
            raise ValueError
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `ریاضی|14|30|شنبه`")

@bot.message_handler(commands=['classes'])
def show_classes(message):
    data = load_data()
    classes = data.get('classes', [])
    
    if not classes:
        bot.reply_to(message, "📅 کلاسی ثبت نشده!")
        return
    
    text = "📅 **کلاس‌های ثبت شده:**\n\n"
    for i, c in enumerate(classes, 1):
        text += f"{i}. {c['name']} - {c['hour']}:{c['minute']:02d} ({c['repeat']})\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

def send_class_reminder(chat_id, class_name):
    bot.send_message(
        chat_id,
        f"⏰ **یادآوری کلاس!**\n\n"
        f"کلاس {class_name} در ۵ دقیقه دیگه شروع میشه!\n"
        f"آماده باش 📚"
    )

# ========== 10. حذف پیام خاص ==========
@bot.message_handler(commands=['del'])
def delete_specific_message(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استفاده: `/del message_id`")
        return
    
    try:
        msg_id = int(parts[1])
        bot.delete_message(message.chat.id, msg_id)
        bot.reply_to(message, f"✅ پیام {msg_id} حذف شد!")
    except:
        bot.reply_to(message, "❌ خطا در حذف پیام!")

# ========== 11. آمار ==========
@bot.callback_query_handler(func=lambda call: call.data == "stats")
def show_stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    data = load_data()
    
    stats = (
        f"📊 **آمار گروه**\n\n"
        f"👥 کاربران: {len(data.get('users', []))}\n"
        f"🚫 بن شده: {len(data.get('banned_users', []))}\n"
        f"⚠️ اخطارها: {sum(len(v) for v in data.get('warnings', {}).values())}\n"
        f"📅 کلاس‌ها: {len(data.get('classes', []))}\n"
        f"📝 پیام‌های زمان‌دار: {len(data.get('scheduled_messages', []))}"
    )
    bot.send_message(call.message.chat.id, stats, parse_mode='Markdown')

# ========== 12. دکمه بستن پنل ==========
@bot.message_handler(commands=['close'])
def close_panel(message):
    bot.reply_to(message, "✅ پنل بسته شد. برای باز کردن /panel")

# ========== 13. فیلتر پیام‌های اسپم ==========
@bot.message_handler(func=lambda message: True)
def filter_messages(message):
    # حذف پیام‌های لینک از کاربران عادی (اختیاری)
    if not is_admin(message.from_user.id):
        if 'http://' in message.text or 'https://' in message.text or 't.me/' in message.text:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message.chat.id, f"⛔ {message.from_user.first_name} لینک زدن ممنوع!", delete_in_sec=5)

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات مدیریت گروه روشن شد!")
    print("✅ قابلیت‌ها: سکوت با ثانیه | پاکسازی | پیام زماندار | خوش‌آمدگویی | آب و هوا | کلاس")
    bot.infinity_polling(timeout=80)
