import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import random
from datetime import datetime, timedelta
import threading
import time
import requests
import hashlib
import string

# ========== توکن ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN)

# ========== دیتابیس ==========
DATA_FILE = 'advanced_bot_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': [],
        'admins': [8481909076],
        'banned_users': [],
        'muted_users': {},
        'warnings': {},
        'notes': {},  # جزوات دسته‌بندی شده
        'note_categories': ['ریاضی', 'فیزیک', 'شیمی', 'برنامه‌نویسی', 'عمومی', 'زبان'],
        'files': [],
        'welcome_text': "به گروه خوش آمدی {name} عزیز! 🎉",
        'welcome_gif': None,
        'rules': "📜 قوانین گروه:\n1️⃣ احترام به همه\n2️⃣ اسپم ممنوع\n3️⃣ جزوات رو در دسته مناسب آپلود کن",
        'questions': {},
        'polls': [],
        'events': [],
        'birthdays': {},
        'todo': {},
        'voice_messages': [],
        'links': {},
        'scores': {},
        'levels': {},
        'daily_messages': {},
        'study_time': {},
        'homeworks': [],
        'exams': [],
        'reminders': [],
        'music_queue': [],
        'scheduled_messages': []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== تنظیمات ==========
ADMIN_ID = 8481909076
ANONYMOUS_ADMIN_ID = 1087968824

def is_admin(user_id):
    data = load_data()
    return user_id == ADMIN_ID or user_id == ANONYMOUS_ADMIN_ID or user_id in data.get('admins', [])

def is_banned(user_id):
    return user_id in load_data().get('banned_users', [])

# ========== کیبورد اصلی ==========
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    # ردیف اول - جزوات
    keyboard.add(KeyboardButton("📚 کتابخانه جزوات"), KeyboardButton("📤 آپلود جزوه"))
    keyboard.add(KeyboardButton("🔍 جستجوی جزوه"), KeyboardButton("⭐ جزوه‌های محبوب"))
    
    # ردیف دوم - مدیریت و اطلاع‌رسانی
    keyboard.add(KeyboardButton("📢 اعلان‌ها"), KeyboardButton("📅 تقویم تحصیلی"))
    keyboard.add(KeyboardButton("✅ تکالیف من"), KeyboardButton("📝 ثبت تکلیف"))
    
    # ردیف سوم - سرگرمی و رفاهی
    keyboard.add(KeyboardButton("🎵 پخش موزیک"), KeyboardButton("🎮 بازی و سرگرمی"))
    keyboard.add(KeyboardButton("🔮 فال حافظ"), KeyboardButton("🌤 آب و هوا"))
    
    # ردیف چهارم - کاربردی
    keyboard.add(KeyboardButton("📊 کارنامه من"), KeyboardButton("🏆 لیگ برتر"))
    keyboard.add(KeyboardButton("❓ سوال بپرس"), KeyboardButton("📜 قوانین"))
    
    if is_admin(user_id):
        keyboard.add(KeyboardButton("👑 پنل ادمین"))
    
    return keyboard

def get_notes_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    data = load_data()
    for cat in data['note_categories']:
        count = len(data['notes'].get(cat, []))
        keyboard.add(InlineKeyboardButton(f"📁 {cat} ({count})", callback_data=f"cat_{cat}"))
    keyboard.add(InlineKeyboardButton("➕ دسته جدید", callback_data="new_category"))
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        InlineKeyboardButton("📚 مدیریت جزوات", callback_data="admin_notes"),
        InlineKeyboardButton("📢 اعلان همگانی", callback_data="admin_broadcast"),
        InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        InlineKeyboardButton("🎉 تنظیم خوش‌آمدگویی", callback_data="admin_welcome"),
        InlineKeyboardButton("📜 ویرایش قوانین", callback_data="admin_rules"),
        InlineKeyboardButton("🗑 پاکسازی گروه", callback_data="admin_purge"),
        InlineKeyboardButton("📅 مدیریت رویدادها", callback_data="admin_events"),
        InlineKeyboardButton("🎁 هدیه روزانه", callback_data="admin_daily"),
        InlineKeyboardButton("🔧 تنظیمات", callback_data="admin_settings")
    )
    return keyboard

# ========== استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    data = load_data()
    
    if user_id not in data['users']:
        data['users'].append(user_id)
        data['scores'][str(user_id)] = 0
        data['levels'][str(user_id)] = 1
        data['daily_messages'][str(user_id)] = 0
        save_data(data)
        
        # خوش‌آمدگویی خصوصی
        bot.send_message(
            user_id,
            f"🎉 سلام {message.from_user.first_name} عزیز!\n\n"
            f"به ربات پیشرفته گروه دانشجویی خوش اومدی! 🤖\n\n"
            f"✨ **امکانات ویژه:**\n"
            f"• 📚 کتابخانه جزوات با دسته‌بندی هوشمند\n"
            f"• 🎵 پخش موزیک در گروه\n"
            f"• 📅 برنامه‌ریزی درسی و تکالیف\n"
            f"• 🏆 سیستم امتیازدهی و سطح‌بندی\n"
            f"• ❓ پرسش و پاسخ هوشمند\n"
            f"• 🎮 بازی‌های گروهی\n\n"
            f"🌟 **امتیاز شروع:** 0\n"
            f"📊 **سطح:** 1\n\n"
            f"برای شروع از دکمه‌های پایین استفاده کن! 👇"
        )
    
    bot.send_message(
        message.chat.id,
        f"به گروه خوش اومدی {message.from_user.first_name}! 🎉",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== 1. بخش جزوات پیشرفته ==========
@bot.message_handler(func=lambda message: message.text == "📚 کتابخانه جزوات")
def show_library(message):
    keyboard = get_notes_keyboard()
    bot.send_message(
        message.chat.id,
        "📚 **کتابخانه جزوات دانشجویی**\n\n"
        "یک دسته رو انتخاب کن:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def show_category_notes(call):
    category = call.data.replace("cat_", "")
    data = load_data()
    notes = data['notes'].get(category, [])
    
    if not notes:
        bot.answer_callback_query(call.id, f"هیچ جزوه‌ای در {category} وجود ندارد!")
        return
    
    bot.answer_callback_query(call.id)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, note in enumerate(notes[-15:]):  # آخرین 15 جزوه
        keyboard.add(InlineKeyboardButton(
            f"📄 {note['name'][:40]} (❤️ {note.get('likes', 0)})", 
            callback_data=f"view_{category}_{i}"
        ))
    
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_categories"))
    
    bot.send_message(
        call.message.chat.id,
        f"📁 **دسته: {category}**\n📊 تعداد جزوات: {len(notes)}\n\n",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

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
    
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("📥 دانلود", callback_data=f"download_{category}_{index}"),
        InlineKeyboardButton(f"❤️ {note.get('likes', 0)}", callback_data=f"like_{category}_{index}"),
        InlineKeyboardButton("📤 اشتراک", callback_data=f"share_{category}_{index}")
    )
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"cat_{category}"))
    
    bot.send_message(
        call.message.chat.id,
        f"📄 **{note['name']}**\n\n"
        f"📁 دسته: {category}\n"
        f"👤 آپلودکننده: {note.get('uploader_name', 'ناشناس')}\n"
        f"📅 تاریخ: {note.get('date', 'نامشخص')}\n"
        f"❤️ امتیاز: {note.get('likes', 0)}\n"
        f"📥 دانلود: {note.get('downloads', 0)} بار",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

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
    
    # افزایش آمار دانلود
    note['downloads'] = note.get('downloads', 0) + 1
    save_data(data)
    
    # افزایش امتیاز کاربر
    add_score(call.from_user.id, 2, "دانلود جزوه")
    
    bot.send_document(call.message.chat.id, note['file_id'])
    bot.answer_callback_query(call.id, "✅ جزوه ارسال شد! +2 امتیاز")

@bot.callback_query_handler(func=lambda call: call.data.startswith("like_"))
def like_note(call):
    parts = call.data.split("_")
    category = parts[1]
    index = int(parts[2])
    
    data = load_data()
    notes = data['notes'].get(category, [])
    
    if index >= len(notes):
        bot.answer_callback_query(call.id, "جزوه یافت نشد!")
        return
    
    note = notes[-(index + 1)]
    note['likes'] = note.get('likes', 0) + 1
    save_data(data)
    
    add_score(call.from_user.id, 1, "امتیاز دادن به جزوه")
    
    bot.answer_callback_query(call.id, f"❤️ امتیاز شما ثبت شد! +1 امتیاز")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def back_to_categories(call):
    bot.edit_message_text(
        "📚 **کتابخانه جزوات دانشجویی**\n\nیک دسته رو انتخاب کن:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_notes_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "📤 آپلود جزوه")
def upload_note(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 شما بن هستید!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    data = load_data()
    for cat in data['note_categories']:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"upload_cat_{cat}"))
    keyboard.add(InlineKeyboardButton("➕ دسته جدید", callback_data="upload_new_cat"))
    
    msg = bot.send_message(
        message.chat.id,
        "📤 **آپلود جزوه جدید**\n\n"
        "اول دسته رو انتخاب کن، بعد فایل رو بفرست:",
        reply_markup=keyboard
    )
    bot.register_next_step_handler(msg, lambda m: None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("upload_cat_"))
def get_upload_category(call):
    category = call.data.replace("upload_cat_", "")
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📤 دسته **{category}** انتخاب شد.\n\n"
        f"حالا فایل جزوه رو بفرست.\n"
        f"میتونی PDF، عکس، ورد یا هر فایل دیگه‌ای بفرستی.\n\n"
        f"برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, save_uploaded_note, category)

def save_uploaded_note(message, category):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ آپلود لغو شد.")
        return
    
    if not (message.document or message.photo):
        bot.reply_to(message, "❌ لطفا یک فایل معتبر بفرست!")
        return
    
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    file_name = message.document.file_name if message.document else f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    
    data = load_data()
    if category not in data['notes']:
        data['notes'][category] = []
    
    data['notes'][category].append({
        'file_id': file_id,
        'name': file_name,
        'uploader': message.from_user.id,
        'uploader_name': message.from_user.first_name,
        'date': str(datetime.now()),
        'likes': 0,
        'downloads': 0
    })
    save_data(data)
    
    # افزایش امتیاز برای آپلود جزوه
    add_score(message.from_user.id, 10, "آپلود جزوه")
    
    bot.reply_to(
        message,
        f"✅ جزوه «{file_name}» با موفقیت در دسته {category} ذخیره شد!\n"
        f"🌟 +10 امتیاز دریافت کردی!"
    )

@bot.message_handler(func=lambda message: message.text == "🔍 جستجوی جزوه")
def search_note_prompt(message):
    msg = bot.reply_to(
        message,
        "🔍 **جستجوی جزوه**\n\n"
        "نام درس یا کلمه کلیدی رو وارد کن:"
    )
    bot.register_next_step_handler(msg, search_note)

def search_note(message):
    keyword = message.text.lower()
    data = load_data()
    results = []
    
    for category, notes in data['notes'].items():
        for note in notes:
            if keyword in note['name'].lower() or keyword in category.lower():
                results.append((category, note))
    
    if not results:
        bot.reply_to(message, f"❌ هیچ نتیجه‌ای برای «{keyword}» پیدا نشد!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for category, note in results[:10]:
        keyboard.add(InlineKeyboardButton(
            f"📚 {category} - {note['name'][:35]}", 
            callback_data=f"search_result_{category}_{note['file_id']}"
        ))
    
    bot.send_message(
        message.chat.id,
        f"🔍 **نتایج جستجو برای «{keyword}»:**\n\n"
        f"{len(results)} جزوه پیدا شد.",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("search_result_"))
def open_search_result(call):
    parts = call.data.replace("search_result_", "").split("_", 1)
    category = parts[0]
    file_id = parts[1]
    
    data = load_data()
    notes = data['notes'].get(category, [])
    note = next((n for n in notes if n['file_id'] == file_id), None)
    
    if note:
        bot.send_document(call.message.chat.id, file_id)
        add_score(call.from_user.id, 2, "دانلود جزوه")
        bot.answer_callback_query(call.id, "✅ جزوه ارسال شد! +2 امتیاز")
    else:
        bot.answer_callback_query(call.id, "جزوه یافت نشد!")

# ========== 2. سیستم امتیازدهی و سطح ==========
def add_score(user_id, points, reason=""):
    data = load_data()
    uid = str(user_id)
    data['scores'][uid] = data['scores'].get(uid, 0) + points
    data['daily_messages'][uid] = data['daily_messages'].get(uid, 0) + 1
    
    # بررسی افزایش سطح
    old_level = data['levels'].get(uid, 1)
    new_level = 1 + (data['scores'][uid] // 100)
    
    if new_level > old_level:
        data['levels'][uid] = new_level
        save_data(data)
        
        # پیام تبریک برای افزایش سطح
        try:
            bot.send_message(
                user_id,
                f"🎉 **تبریک! سطح شما افزایش یافت!** 🎉\n\n"
                f"سطح {old_level} → {new_level}\n"
                f"🌟 امتیاز کل: {data['scores'][uid]}\n\n"
                f"به سطح {new_level} خوش اومدی! 🚀"
            )
        except:
            pass
    else:
        save_data(data)
    
    return points

@bot.message_handler(func=lambda message: message.text == "📊 کارنامه من")
def show_my_stats(message):
    data = load_data()
    uid = str(message.from_user.id)
    
    score = data['scores'].get(uid, 0)
    level = data['levels'].get(uid, 1)
    daily = data['daily_messages'].get(uid, 0)
    
    # محاسبه امتیاز تا سطح بعدی
    next_level_score = level * 100
    remain = next_level_score - score
    progress = int((score / next_level_score) * 100) if next_level_score > 0 else 0
    
    progress_bar = "█" * (progress // 5) + "░" * (20 - (progress // 5))
    
    # آمار مشارکت
    total_notes = sum(len(n) for n in data['notes'].values())
    user_notes = sum(1 for cat in data['notes'].values() for n in cat if n.get('uploader') == message.from_user.id)
    
    bot.send_message(
        message.chat.id,
        f"📊 **کارنامه تحصیلی**\n\n"
        f"👤 کاربر: {message.from_user.first_name}\n\n"
        f"🌟 **امتیاز کل:** {score}\n"
        f"📊 **سطح:** {level}\n"
        f"📈 **پیشرفت به سطح بعد:**\n"
        f"`{progress_bar}` {progress}%\n"
        f"🔜 امتیاز نیاز: {remain}\n\n"
        f"📚 **جزوه‌های آپلود شده:** {user_notes}\n"
        f"💬 **پیام‌های امروز:** {daily}\n"
        f"📥 **کل جزوات گروه:** {total_notes}\n\n"
        f"✨ با فعالیت بیشتر، امتیاز بیشتری دریافت کن!",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "🏆 لیگ برتر")
def show_leaderboard(message):
    data = load_data()
    scores = data['scores']
    
    if not scores:
        bot.reply_to(message, "📊 هنوز امتیازی ثبت نشده!")
        return
    
    # مرتب‌سازی بر اساس امتیاز
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    
    leaderboard = "🏆 **لیگ برتر دانشجویان** 🏆\n\n"
    
    for i, (uid, score) in enumerate(sorted_scores, 1):
        level = data['levels'].get(uid, 1)
        # دریافت نام کاربر (اگر در گروه نباشه، آیدی نشون داده میشه)
        name = f"کاربر {uid[:6]}"
        try:
            chat = bot.get_chat(int(uid))
            name = chat.first_name or f"کاربر {uid[:6]}"
        except:
            pass
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        leaderboard += f"{medal} **{i}.** {name[:20]}\n"
        leaderboard += f"   🌟 {score} امتیاز | 📊 سطح {level}\n\n"
    
    # امتیاز خود کاربر
    uid = str(message.from_user.id)
    user_score = scores.get(uid, 0)
    user_rank = sorted([(k, v) for k, v in scores.items()], key=lambda x: x[1], reverse=True)
    rank = next((i+1 for i, (k, v) in enumerate(user_rank) if k == uid), None)
    
    if rank:
        leaderboard += f"\n🎯 **رتبه شما:** {rank} از {len(scores)} نفر\n"
        leaderboard += f"🌟 **امتیاز شما:** {user_score}\n"
    
    bot.send_message(message.chat.id, leaderboard, parse_mode='Markdown')

# ========== 3. بخش پرسش و پاسخ هوشمند ==========
@bot.message_handler(func=lambda message: message.text == "❓ سوال بپرس")
def ask_question_prompt(message):
    msg = bot.reply_to(
        message,
        "❓ **پرسش و پاسخ هوشمند**\n\n"
        "سوال خودت رو بپرس.\n\n"
        "مثال:\n"
        "• `آزمون ریاضی کی هست؟`\n"
        "• `جزوه فیزیک کجاست؟`\n"
        "• `تکلیف برنامه‌نویسی چیه؟`\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, answer_question)

def answer_question(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    question = message.text.lower()
    data = load_data()
    
    # پاسخ‌های هوشمند
    responses = {
        'امتحان': "📅 لیست امتحانات رو با دکمه 📅 تقویم تحصیلی می‌تونی ببینی!",
        'جزوه': "📚 جزوه‌ها توی کتابخانه جزوات هستن. از دکمه 📚 کتابخانه جزوات استفاده کن!",
        'تکلیف': "✅ تکالیف خودت رو می‌تونی با دکمه 📝 ثبت تکلیف اضافه کنی و با ✅ تکالیف من ببینی!",
        'کلاس': "📅 برای مشاهده و ثبت کلاس‌ها از بخش 📅 تقویم تحصیلی استفاده کن!",
        'امتیاز': "🌟 امتیاز خودت رو با دکمه 📊 کارنامه من می‌تونی ببینی!",
        'لول': "📊 سطح و امتیازت توی 📊 کارنامه من هست!",
        'فال': "🔮 برای فال حافظ از دکمه 🔮 فال حافظ استفاده کن!",
        'موزیک': "🎵 برای پخش موزیک از دکمه 🎵 پخش موزیک استفاده کن!"
    }
    
    # پیدا کردن پاسخ مناسب
    answer = None
    for key, resp in responses.items():
        if key in question:
            answer = resp
            break
    
    if not answer:
        answer = "❓ سوال خوبی پرسیدی!\n\n"
        answer += "💡 **پیشنهادات:**\n"
        answer += "• سوال خودت رو دقیق‌تر بپرس\n"
        answer += "• از ادمین گروه بپرس\n"
        answer += "• توی گروه مطرح کن تا بقیه کمک کنن\n\n"
        answer += "🔍 همچنین می‌تونی با دکمه 🔍 جستجوی جزوه، جزوه مورد نظرتو پیدا کنی!"
    
    bot.reply_to(message, answer)
    add_score(message.from_user.id, 1, "پرسش سوال")

# ========== 4. بخش تکالیف و برنامه ریزی ==========
@bot.message_handler(func=lambda message: message.text == "📝 ثبت تکلیف")
def add_homework_prompt(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 شما بن هستید!")
        return
    
    msg = bot.reply_to(
        message,
        "📝 **ثبت تکلیف جدید**\n\n"
        "فرمت ارسال:\n"
        "`نام درس|توضیح تکلیف|ددلاین`\n\n"
        "مثال:\n"
        "`ریاضی|حل تمرین‌های صفحه ۲۰|1403/04/15`\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, save_homework)

def save_homework(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    try:
        parts = message.text.split('|')
        if len(parts) >= 2:
            subject = parts[0]
            description = parts[1]
            deadline = parts[2] if len(parts) > 2 else "نامشخص"
            
            data = load_data()
            data['homeworks'].append({
                'user_id': message.from_user.id,
                'subject': subject,
                'description': description,
                'deadline': deadline,
                'date': str(datetime.now()),
                'status': 'pending'
            })
            save_data(data)
            
            add_score(message.from_user.id, 3, "ثبت تکلیف")
            
            bot.reply_to(
                message,
                f"✅ تکلیف ثبت شد!\n\n"
                f"📚 درس: {subject}\n"
                f"📝 توضیح: {description}\n"
                f"⏰ ددلاین: {deadline}\n\n"
                f"🌟 +3 امتیاز!"
            )
        else:
            raise ValueError
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `درس|توضیح|ددلاین`")

@bot.message_handler(func=lambda message: message.text == "✅ تکالیف من")
def show_homeworks(message):
    data = load_data()
    user_homeworks = [h for h in data['homeworks'] if h['user_id'] == message.from_user.id]
    
    if not user_homeworks:
        bot.reply_to(message, "✅ هیچ تکلیفی ثبت نکردی!\nاز دکمه 📝 ثبت تکلیف استفاده کن.")
        return
    
    text = "✅ **لیست تکالیف شما**\n\n"
    for i, h in enumerate(reversed(user_homeworks[-10:]), 1):
        status = "✅ انجام شده" if h.get('status') == 'done' else "⏳ در حال انجام"
        text += f"{i}. **{h['subject']}**\n"
        text += f"   📝 {h['description'][:50]}\n"
        text += f"   ⏰ ددلاین: {h['deadline']}\n"
        text += f"   📊 وضعیت: {status}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "📅 تقویم تحصیلی")
def show_calendar(message):
    data = load_data()
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 تکالیف همه", callback_data="all_homeworks"),
        InlineKeyboardButton("📆 امتحانات", callback_data="all_exams"),
        InlineKeyboardButton("🎉 رویدادها", callback_data="all_events"),
        InlineKeyboardButton("➕ اضافه کردن", callback_data="add_calendar")
    )
    
    bot.send_message(
        message.chat.id,
        "📅 **تقویم تحصیلی گروه**\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "all_homeworks")
def show_all_homeworks(call):
    data = load_data()
    homeworks = data['homeworks']
    
    if not homeworks:
        bot.answer_callback_query(call.id, "هیچ تکلیفی ثبت نشده!")
        return
    
    text = "📝 **تکالیف ثبت شده گروه**\n\n"
    for i, h in enumerate(reversed(homeworks[-15:]), 1):
        text += f"{i}. **{h['subject']}** - {h['description'][:40]}\n"
        text += f"   ⏰ {h['deadline']}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "all_exams")
def show_all_exams(call):
    data = load_data()
    exams = data.get('exams', [])
    
    if not exams:
        bot.send_message(call.message.chat.id, "📆 هیچ امتحانی ثبت نشده!")
        bot.answer_callback_query(call.id)
        return
    
    text = "📆 **تقویم امتحانات**\n\n"
    for i, e in enumerate(reversed(exams[-15:]), 1):
        text += f"{i}. {e['subject']}\n"
        text += f"   📅 {e['date']}\n"
        text += f"   📝 {e.get('description', '')}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# ========== 5. بخش سرگرمی ==========
@bot.message_handler(func=lambda message: message.text == "🎮 بازی و سرگرمی")
def games_menu(message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎲 تاس بینداز", callback_data="game_dice"),
        InlineKeyboardButton("🎯 حدس عدد", callback_data="game_number"),
        InlineKeyboardButton("📝 مسابقه", callback_data="game_quiz"),
        InlineKeyboardButton("🎰 ماشین شانس", callback_data="game_slot")
    )
    
    bot.send_message(
        message.chat.id,
        "🎮 **بازی و سرگرمی**\n\n"
        "یک بازی رو انتخاب کن و امتیاز جمع کن! 🎁",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    dice = random.randint(1, 6)
    points = dice * 2
    add_score(call.from_user.id, points, "بازی تاس")
    
    bot.send_dice(call.message.chat.id, emoji="🎲")
    bot.send_message(
        call.message.chat.id,
        f"🎲 عدد {dice} اومد!\n🌟 {points} امتیاز گرفتی!",
        reply_to_message_id=call.message.message_id + 1
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_number")
def play_number_game(call):
    number = random.randint(1, 100)
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id,
        f"🎯 **حدس عدد بین 1 تا 100**\n\n"
        f"من یه عدد انتخاب کردم، حدس بزن!\n"
        f"(۳ تا شانس داری)\n\n"
        f"عددت رو بفرست:"
    )
    bot.register_next_step_handler(msg, check_number_guess, number, 3)

def check_number_guess(message, target, attempts):
    try:
        guess = int(message.text)
        
        if guess == target:
            points = 20
            add_score(message.from_user.id, points, "برنده بازی حدس عدد")
            bot.reply_to(message, f"🎉 تبریک! درست حدس زدی! عدد {target} بود.\n🌟 {points} امتیاز گرفتی!")
        elif attempts > 1:
            hint = "بزرگ‌تر" if guess < target else "کوچک‌تر"
            bot.reply_to(message, f"❌ نه! عدد {hint} از {guess} هست.\n🔁 {attempts-1} شانس دیگه داری!")
            msg = bot.send_message(message.chat.id, "عدد بعدی رو بفرست:")
            bot.register_next_step_handler(msg, check_number_guess, target, attempts-1)
        else:
            bot.reply_to(message, f"😔 بازی تموم شد! عدد {target} بود.\n💪 دفعه بعد حتما میبری!")
    except:
        bot.reply_to(message, "❌ لطفا یه عدد معتبر بفرست!")

@bot.callback_query_handler(func=lambda call: call.data == "game_quiz")
def play_quiz(call):
    quizzes = [
        {"q": "Python کی ساخته شد؟", "a": "1991", "options": ["1989", "1991", "1995", "2000"]},
        {"q": "تلگرام چند کاربر فعال دارد؟", "a": "800M", "options": ["500M", "700M", "800M", "1B"]},
        {"q": "کدام زبان برای AI بهتر است؟", "a": "Python", "options": ["Java", "C++", "Python", "JavaScript"]}
    ]
    
    quiz = random.choice(quizzes)
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in quiz['options']:
        keyboard.add(InlineKeyboardButton(opt, callback_data=f"quiz_{quiz['q']}_{opt}_{quiz['a']}"))
    
    bot.send_message(call.message.chat.id, f"❓ {quiz['q']}", reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_"))
def check_quiz(call):
    parts = call.data.split("_")
    answer = parts[-1]
    correct = parts[-2]
    
    if answer == correct:
        points = 15
        add_score(call.from_user.id, points, "برنده مسابقه")
        bot.edit_message_text(
            f"✅ پاسخ صحیح! +{points} امتیاز",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.edit_message_text(
            f"❌ پاسخ اشتباه! پاسخ صحیح: {correct}",
            call.message.chat.id,
            call.message.message_id
        )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    slots = ["🍒", "🍊", "🍋", "🍉", "⭐", "7️⃣"]
    result = [random.choice(slots) for _ in range(3)]
    
    points = 0
    if result[0] == result[1] == result[2]:
        points = 50
        msg = "🎉 **جکپات!** 🎉"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        points = 10
        msg = "🎈 بردی!"
    else:
        msg = "😔 بازنده شدی!"
    
    add_score(call.from_user.id, points, "بازی ماشین شانس")
    
    bot.send_message(
        call.message.chat.id,
        f"🎰 **ماشین شانس**\n\n"
        f"`{result[0]} | {result[1]} | {result[2]}`\n\n"
        f"{msg} 🌟 +{points} امتیاز"
    )
    bot.answer_callback_query(call.id)

# ========== 6. پخش موزیک ساده ==========
@bot.message_handler(func=lambda message: message.text == "🎵 پخش موزیک")
def play_music_simple(message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎵 آرامش بخش", callback_data="play_relax"),
        InlineKeyboardButton("🎸 پرانرژی", callback_data="play_energy"),
        InlineKeyboardButton("🎹 کلاسیک", callback_data="play_classic"),
        InlineKeyboardButton("⏹ توقف", callback_data="stop_music")
    )
    
    bot.send_message(
        message.chat.id,
        "🎵 **پخش موزیک در گروه**\n\n"
        "یک سبک رو انتخاب کن:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_"))
def play_music(call):
    style = call.data.replace("play_", "")
    music_files = {
        "relax": "CQACAgQAAxkBAA...",  # آیدی فایل موزیک رو اینجا بذار
        "energy": "CQACAgQAAxkBAA...",
        "classic": "CQACAgQAAxkBAA..."
    }
    
    bot.answer_callback_query(call.id, f"🎵 در حال پخش موزیک {style}...")
    # برای پخش واقعی نیاز به file_id موزیک داری
    bot.send_message(call.message.chat.id, f"🎵 موزیک {style} در حال پخش... (برای توقف دکمه رو بزن)")

@bot.callback_query_handler(func=lambda call: call.data == "stop_music")
def stop_music(call):
    bot.answer_callback_query(call.id, "⏹ پخش متوقف شد!")
    bot.send_message(call.message.chat.id, "⏹ پخش موزیک متوقف شد.")

# ========== 7. فال حافظ ==========
@bot.message_handler(func=lambda message: message.text == "🔮 فال حافظ")
def fortune(message):
    fortunes = [
        {"verse": "صبا به لطف بگو آن غزال رعنا را", "meaning": "به زودی خبرهای خوبی می‌رسی. صبور باش."},
        {"verse": "در این زمانه رفیقی که خالی از خلل است", "meaning": "به دوستان واقعی خود اعتماد کن."},
        {"verse": "ساقیا برخیز و درده جام را", "meaning": "زندگی رو ساده بگیر و از لحظه لذت ببر."},
        {"verse": "اگر آن ترک شیرازی به دست آرد دل ما را", "meaning": "عشق و علاقه جدیدی وارد زندگیت می‌شه."},
        {"verse": "حافظا روزی تو را در کنج رندی خواهند یافت", "meaning": "مسیر درست رو پیدا می‌کنی."}
    ]
    
    fortune = random.choice(fortunes)
    text = f"🍃 **فال حافظ** 🍃\n\n"
    text += f"📜 {fortune['verse']}\n\n"
    text += f"✨ **تعبیر:**\n{fortune['meaning']}\n\n"
    text += f"🌸 روزت پر از آرامش 🌸"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')
    add_score(message.from_user.id, 1, "فال حافظ")

# ========== 8. آب و هوا ==========
@bot.message_handler(func=lambda message: message.text == "🌤 آب و هوا")
def weather(message):
    cities = {
        "همدان": "Hamedan",
        "تهران": "Tehran",
        "اصفهان": "Esfahan",
        "مشهد": "Mashhad"
    }
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    for city in cities.keys():
        keyboard.add(InlineKeyboardButton(city, callback_data=f"weather_{cities[city]}"))
    
    bot.send_message(message.chat.id, "🌤 آب و هوای کدوم شهر رو می‌خوای؟", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("weather_"))
def send_weather(call):
    city = call.data.replace("weather_", "")
    
    try:
        response = requests.get(f"https://wttr.in/{city}?format=%C+%t+%w+%h&lang=fa")
        weather_data = response.text.strip()
        
        bot.send_message(
            call.message.chat.id,
            f"🌤 **آب و هوای {city}**\n\n{weather_data}\n\n📅 {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        )
        add_score(call.from_user.id, 1, "استعلام آب و هوا")
    except:
        bot.send_message(call.message.chat.id, f"❌ خطا در دریافت آب و هوای {city}!")
    
    bot.answer_callback_query(call.id)

# ========== 9. قوانین ==========
@bot.message_handler(func=lambda message: message.text == "📜 قوانین")
def show_rules(message):
    data = load_data()
    rules = data.get('rules', "📜 قوانین گروه:\n1️⃣ احترام به همه\n2️⃣ اسپم ممنوع")
    
    keyboard = InlineKeyboardMarkup()
    if is_admin(message.from_user.id):
        keyboard.add(InlineKeyboardButton("✏️ ویرایش قوانین", callback_data="edit_rules"))
    
    bot.send_message(message.chat.id, rules, reply_markup=keyboard)

# ========== 10. اعلان‌ها ==========
@bot.message_handler(func=lambda message: message.text == "📢 اعلان‌ها")
def show_announcements(message):
    data = load_data()
    events = data.get('events', [])
    
    if not events:
        bot.reply_to(message, "📢 هیچ اعلان جدیدی وجود ندارد!")
        return
    
    text = "📢 **آخرین اعلان‌ها**\n\n"
    for event in reversed(events[-5:]):
        text += f"• {event['title']}\n"
        text += f"  📅 {event['date']}\n"
        text += f"  📝 {event['description'][:100]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ========== 11. پنل ادمین ==========
@bot.message_handler(func=lambda message: message.text == "👑 پنل ادمین")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین دسترسی داره!")
        return
    
    bot.send_message(
        message.chat.id,
        "👑 **پنل مدیریت پیشرفته**\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=get_admin_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    data = load_data()
    total_notes = sum(len(n) for n in data['notes'].values())
    total_scores = sum(data['scores'].values())
    
    stats = (
        f"📊 **آمار پیشرفته گروه**\n\n"
        f"👥 کاربران: {len(data['users'])}\n"
        f"📚 جزوات: {total_notes}\n"
        f"📝 تکالیف: {len(data['homeworks'])}\n"
        f"🎯 امتیاز کل: {total_scores}\n"
        f"🏆 میانگین امتیاز: {total_scores // max(1, len(data['users']))}\n"
        f"🚫 کاربران بن: {len(data['banned_users'])}\n"
        f"⚠️ اخطارها: {sum(len(v) for v in data['warnings'].values())}"
    )
    
    bot.send_message(call.message.chat.id, stats, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def broadcast_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📢 **ارسال اعلان همگانی**\n\n"
        "متن پیام رو بفرست.\n"
        "میتونی متن، عکس یا فایل بفرستی.\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    data = load_data()
    users = data.get('users', [])
    success = 0
    
    status = bot.reply_to(message, "⏳ در حال ارسال...")
    
    for user_id in users:
        try:
            if message.text:
                bot.send_message(user_id, f"📢 **اعلان همگانی:**\n\n{message.text}")
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success += 1
        except:
            pass
        time.sleep(0.05)
    
    bot.edit_message_text(f"✅ اعلان به {success} نفر ارسال شد!", status.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_welcome")
def admin_welcome(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📝 متن خوش‌آمدگویی", callback_data="set_welcome_text"),
        InlineKeyboardButton("🎬 گیف خوش‌آمدگویی", callback_data="set_welcome_gif"),
        InlineKeyboardButton("❌ غیرفعال", callback_data="disable_welcome")
    )
    
    bot.send_message(call.message.chat.id, "🎉 **تنظیمات خوش‌آمدگویی**", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_text")
def set_welcome_text_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📝 متن خوش‌آمدگویی رو وارد کن.\n\n"
        "از `{name}` برای اسم کاربر استفاده کن.\n"
        "مثال: `به گروه خوش اومدی {name} جان! 🎉`"
    )
    bot.register_next_step_handler(msg, save_welcome_text)

def save_welcome_text(message):
    data = load_data()
    data['welcome_text'] = message.text
    save_data(data)
    bot.reply_to(message, "✅ متن خوش‌آمدگویی ذخیره شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_rules")
def edit_rules_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📜 **ویرایش قوانین گروه**\n\n"
        "قوانین جدید رو وارد کن.\n\n"
        "مثال:\n"
        "1️⃣ احترام به همه\n"
        "2️⃣ اسپم ممنوع\n"
        "3️⃣ جزوات رو در دسته مناسب آپلود کن"
    )
    bot.register_next_step_handler(msg, save_rules)

def save_rules(message):
    data = load_data()
    data['rules'] = message.text
    save_data(data)
    bot.reply_to(message, "✅ قوانین گروه به‌روزرسانی شد!")

# ========== اخطار ==========
@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ استفاده: `/warn @username دلیل`")
        return
    
    target = parts[0].replace('/warn', '').strip()
    reason = parts[1]
    
    if target.startswith('@'):
        try:
            user = bot.get_chat(target)
            user_id = user.id
        except:
            bot.reply_to(message, "❌ کاربر پیدا نشد!")
            return
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
        bot.reply_to(message, f"⚠️ کاربر {target} بعد از {warn_count} اخطار بن شد!\nدلیل: {reason}")
    else:
        bot.reply_to(message, f"⚠️ اخطار {warn_count}/3 به {target}\nدلیل: {reason}")

# ========== خوش‌آمدگویی خودکار ==========
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
        
        add_score(new_member.id, 5, "عضو جدید گروه")

# ========== پاکسازی ==========
@bot.message_handler(commands=['purge'])
def purge_messages(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ استفاده: `/purge تعداد`\nمثال: `/purge 50`")
        return
    
    try:
        count = min(int(parts[1]), 100)
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

# ========== هندلر پیام‌های عادی ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if is_banned(message.from_user.id):
        bot.delete_message(message.chat.id, message.message_id)
        return
    
    # افزایش امتیاز برای فعالیت روزانه
    data = load_data()
    uid = str(message.from_user.id)
    
    # محدودیت امتیاز روزانه
    last_msg = data.get('last_message_time', {}).get(uid, 0)
    now = time.time()
    
    if now - last_msg > 60:  # هر 1 دقیقه یک بار امتیاز
        add_score(message.from_user.id, 1, "فعالیت در گروه")
        if 'last_message_time' not in data:
            data['last_message_time'] = {}
        data['last_message_time'][uid] = now
        save_data(data)

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات فوق پیشرفته روشن شد!")
    print("✅ قابلیت‌ها: جزوه | امتیاز | بازی | تکلیف | موزیک | فال | آب و هوا")
    bot.infinity_polling(timeout=80)