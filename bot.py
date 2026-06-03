import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import random
import time
import threading
from datetime import datetime, timedelta
import requests

# ========== توکن ==========
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

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
        'muted': {},
        'warnings': {},
        'notes': {},
        'scores': {},
        'levels': {},
        'daily_streak': {},
        'referrals': {},
        'homeworks': [],
        'exams': [],
        'events': [],
        'reminders': [],
        'birthdays': {},
        'todo': {},
        'polls': [],
        'last_active': {},
        'welcome_text': "🎉 به {name} عزیز خوش اومدی! 🌟",
        'welcome_gif': None,
        'rules': "📜 **قوانین گروه دانشجویی:**\n\n1️⃣ احترام به همه اعضا\n2️⃣ اسپم و تبلیغ ممنوع\n3️⃣ جزوات رو در دسته مناسب آپلود کن\n4️⃣ از فحش و توهین خودداری کن\n5️⃣ همکاری در انجام تکالیف گروهی\n\n⚡ تخلف = اخطار → بن موقت → بن دائمی",
        'faq': {},
        'quiz_questions': [],
        'voice_messages': [],
        'study_sessions': {},
        'group_stats': {'messages': 0, 'notes': 0, 'homeworks': 0}
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== تنظیمات ==========
ADMIN_ID = 8481909076
ANONYMOUS_ID = 1087968824
HAMADAN_CITY = "Hamedan"

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id == ANONYMOUS_ID or user_id in load_data().get('admins', [])

def is_banned(user_id):
    return user_id in load_data().get('banned', [])

def is_muted(user_id, chat_id):
    data = load_data()
    muted = data.get('muted', {}).get(str(chat_id), {})
    if str(user_id) in muted:
        if datetime.now() < datetime.fromisoformat(muted[str(user_id)]):
            return True
        else:
            del muted[str(user_id)]
            save_data(data)
    return False

def add_score(user_id, points, reason=""):
    data = load_data()
    uid = str(user_id)
    data['scores'][uid] = data['scores'].get(uid, 0) + points
    
    # سیستم سطح‌بندی
    old_level = data['levels'].get(uid, 1)
    new_level = 1 + (data['scores'][uid] // 100)
    if new_level > old_level:
        data['levels'][uid] = new_level
        save_data(data)
        try:
            bot.send_message(user_id, f"🎉 **تبریک! سطح شما افزایش یافت!** 🎉\n\nسطح {old_level} → {new_level}\n🌟 امتیاز کل: {data['scores'][uid]}\n\nبه سطح {new_level} خوش اومدی! 🚀", parse_mode='Markdown')
        except:
            pass
    else:
        save_data(data)
    
    # استریک روزانه
    today = datetime.now().strftime('%Y%m%d')
    if data['daily_streak'].get(uid, {}).get('last_date') == today:
        data['daily_streak'][uid]['count'] = data['daily_streak'][uid].get('count', 0) + 1
        if data['daily_streak'][uid]['count'] % 7 == 0:
            bonus = 50
            data['scores'][uid] = data['scores'].get(uid, 0) + bonus
            try:
                bot.send_message(user_id, f"🎁 **تبریک! {data['daily_streak'][uid]['count']} روز پیاپی فعال بودی!**\n🌟 +{bonus} امتیاز جایزه!", parse_mode='Markdown')
            except:
                pass
    else:
        data['daily_streak'][uid] = {'count': 1, 'last_date': today}
    
    save_data(data)
    return data['scores'][uid]

def get_rank(user_id):
    data = load_data()
    scores = data['scores']
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for i, (uid, _) in enumerate(sorted_scores):
        if uid == str(user_id):
            return i + 1
    return None

# ========== کیبورد اصلی ==========
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("📚 کتابخانه جزوه"), KeyboardButton("📤 آپلود جزوه"),
        KeyboardButton("🔍 جستجوی جزوه"), KeyboardButton("⭐ جزوه‌های محبوب")
    )
    keyboard.add(
        KeyboardButton("🏆 کارنامه من"), KeyboardButton("📊 لیگ برتر"),
        KeyboardButton("🎮 بازی و سرگرمی"), KeyboardButton("🔮 فال حافظ")
    )
    keyboard.add(
        KeyboardButton("📝 ثبت تکلیف"), KeyboardButton("✅ تکالیف من"),
        KeyboardButton("📅 تقویم تحصیلی"), KeyboardButton("⏰ یادآوری کلاس")
    )
    keyboard.add(
        KeyboardButton("🌤 آب و هوا"), KeyboardButton("❓ سوال بپرس"),
        KeyboardButton("📜 قوانین"), KeyboardButton("📢 اعلان‌ها")
    )
    if is_admin(user_id):
        keyboard.add(KeyboardButton("👑 پنل ادمین"))
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        InlineKeyboardButton("📚 مدیریت جزوات", callback_data="admin_notes"),
        InlineKeyboardButton("📢 اعلان همگانی", callback_data="admin_broadcast"),
        InlineKeyboardButton("🚫 مدیریت بن", callback_data="admin_ban_menu"),
        InlineKeyboardButton("⚠️ مدیریت اخطار", callback_data="admin_warn_menu"),
        InlineKeyboardButton("🎉 تنظیم خوش‌آمدگویی", callback_data="admin_welcome"),
        InlineKeyboardButton("📜 ویرایش قوانین", callback_data="admin_rules"),
        InlineKeyboardButton("🗑 پاکسازی پیام", callback_data="admin_purge"),
        InlineKeyboardButton("📅 مدیریت رویدادها", callback_data="admin_events"),
        InlineKeyboardButton("🎁 هدیه روزانه", callback_data="admin_daily"),
        InlineKeyboardButton("📝 نظرسنجی", callback_data="admin_poll"),
        InlineKeyboardButton("📤 پشتیبان", callback_data="admin_backup"),
        InlineKeyboardButton("🔙 بستن", callback_data="admin_close")
    )
    return keyboard

def get_notes_keyboard():
    data = load_data()
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in ['ریاضی', 'فیزیک', 'شیمی', 'برنامه‌نویسی', 'عمومی', 'زبان', 'سایر']:
        count = len(data['notes'].get(cat, []))
        keyboard.add(InlineKeyboardButton(f"📁 {cat} ({count})", callback_data=f"cat_{cat}"))
    keyboard.add(InlineKeyboardButton("➕ دسته جدید", callback_data="new_category"))
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
        save_data(data)
        
        # پیام خصوصی خوش‌آمدگویی
        try:
            bot.send_message(
                user_id,
                f"🎉 **سلام {message.from_user.first_name} عزیز!** 🎉\n\n"
                f"به ربات پیشرفته گروه دانشجویی خوش اومدی! 🤖\n\n"
                f"✨ **امکانات ویژه:**\n"
                f"• 📚 کتابخانه جزوات با دسته‌بندی هوشمند\n"
                f"• 🎵 پخش موزیک و سرگرمی\n"
                f"• 📅 برنامه‌ریزی درسی و تکالیف\n"
                f"• 🏆 سیستم امتیازدهی و سطح‌بندی\n"
                f"• 🎮 بازی‌های گروهی و فال حافظ\n"
                f"• 🌤 آب و هوای همدان\n\n"
                f"🌟 **امتیاز شروع:** 0\n"
                f"📊 **سطح:** 1\n"
                f"🏅 **رتبه:** در حال محاسبه\n\n"
                f"💡 برای شروع از دکمه‌های پایین استفاده کن! 👇",
                parse_mode='Markdown'
            )
        except:
            pass
    
    bot.send_message(
        message.chat.id,
        f"🎉 به {message.from_user.first_name} عزیز خوش اومدی!\n\nاز دکمه‌های زیر استفاده کن:",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== 1. بخش جزوات پیشرفته ==========
@bot.message_handler(func=lambda m: m.text == "📚 کتابخانه جزوه")
def show_library(message):
    keyboard = get_notes_keyboard()
    bot.send_message(message.chat.id, "📚 **کتابخانه جزوات دانشجویی**\n\nیک دسته رو انتخاب کن:", reply_markup=keyboard, parse_mode='Markdown')

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
    for i, note in enumerate(notes[-15:]):
        keyboard.add(InlineKeyboardButton(f"📄 {note['name'][:40]} (❤️ {note.get('likes', 0)})", callback_data=f"view_{category}_{i}"))
    keyboard.add(InlineKeyboardButton("🔙 برگشت", callback_data="back_to_categories"))
    
    bot.edit_message_text(
        f"📁 **دسته: {category}**\n📊 تعداد جزوات: {len(notes)}\n\n",
        call.message.chat.id,
        call.message.message_id,
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
    keyboard.add(InlineKeyboardButton("🔙 برگشت", callback_data=f"cat_{category}"))
    
    info = f"📄 **{note['name']}**\n\n"
    info += f"📁 دسته: {category}\n"
    info += f"👤 آپلودکننده: {note.get('uploader_name', 'ناشناس')}\n"
    info += f"📅 تاریخ: {note.get('date', 'نامشخص')}\n"
    info += f"❤️ امتیاز: {note.get('likes', 0)}\n"
    info += f"📥 دانلود: {note.get('downloads', 0)} بار"
    
    bot.send_message(call.message.chat.id, info, reply_markup=keyboard, parse_mode='Markdown')
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
    note['downloads'] = note.get('downloads', 0) + 1
    save_data(data)
    
    bot.send_document(call.message.chat.id, note['file_id'])
    score = add_score(call.from_user.id, 2, "دانلود جزوه")
    bot.answer_callback_query(call.id, f"✅ جزوه ارسال شد! +2 امتیاز (کل: {score})")

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
    
    score = add_score(call.from_user.id, 1, "امتیاز دادن به جزوه")
    bot.answer_callback_query(call.id, f"❤️ امتیاز شما ثبت شد! +1 امتیاز (کل: {score})")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_categories")
def back_to_categories(call):
    bot.edit_message_text(
        "📚 **کتابخانه جزوات دانشجویی**\n\nیک دسته رو انتخاب کن:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=get_notes_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "📤 آپلود جزوه")
def upload_note(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 شما بن هستید! نمی‌توانید جزوه آپلود کنید.")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in ['ریاضی', 'فیزیک', 'شیمی', 'برنامه‌نویسی', 'عمومی', 'زبان', 'سایر']:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"upload_cat_{cat}"))
    keyboard.add(InlineKeyboardButton("➕ دسته جدید", callback_data="upload_new_cat"))
    
    bot.send_message(message.chat.id, "📤 **آپلود جزوه جدید**\n\nاول دسته رو انتخاب کن، بعد فایل رو بفرست:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("upload_cat_"))
def get_upload_category(call):
    category = call.data.replace("upload_cat_", "")
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📤 دسته **{category}** انتخاب شد.\n\nحالا فایل جزوه رو بفرست.\nمیتونی PDF، عکس، ورد یا هر فایل دیگه‌ای بفرستی.\n\nبرای لغو /cancel"
    )
    bot.register_next_step_handler(msg, save_uploaded_note, category)

@bot.callback_query_handler(func=lambda call: call.data == "upload_new_cat")
def new_category_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📝 نام دسته جدید رو وارد کن:")
    bot.register_next_step_handler(msg, create_new_category)

def create_new_category(message):
    category = message.text.strip()
    msg = bot.reply_to(message, f"✅ دسته **{category}** ساخته شد.\n\nحالا فایل جزوه رو بفرست:")
    bot.register_next_step_handler(msg, save_uploaded_note, category)

def save_uploaded_note(message, category):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ آپلود لغو شد.")
        return
    
    if not (message.document or message.photo):
        bot.reply_to(message, "❌ لطفا یک فایل معتبر بفرست (PDF، عکس، ورد)!")
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
        'date': str(datetime.now()),
        'likes': 0,
        'downloads': 0
    })
    save_data(data)
    
    score = add_score(message.from_user.id, 10, "آپلود جزوه")
    bot.reply_to(
        message,
        f"✅ **جزوه با موفقیت آپلود شد!**\n\n"
        f"📄 نام: {file_name}\n"
        f"📁 دسته: {category}\n"
        f"🌟 +10 امتیاز\n"
        f"🏆 امتیاز کل شما: {score}"
    )

@bot.message_handler(func=lambda m: m.text == "🔍 جستجوی جزوه")
def search_note_prompt(message):
    msg = bot.reply_to(message, "🔍 **جستجوی جزوه**\n\nنام درس یا کلمه کلیدی رو وارد کن:")
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
        keyboard.add(InlineKeyboardButton(f"📚 {category} - {note['name'][:35]}", callback_data=f"search_result_{category}_{note['file_id']}"))
    
    bot.send_message(message.chat.id, f"🔍 **نتایج جستجو برای «{keyword}»:**\n\n{len(results)} جزوه پیدا شد.", reply_markup=keyboard)

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
        score = add_score(call.from_user.id, 2, "دانلود جزوه از جستجو")
        bot.answer_callback_query(call.id, f"✅ جزوه ارسال شد! +2 امتیاز")
    else:
        bot.answer_callback_query(call.id, "جزوه یافت نشد!")

@bot.message_handler(func=lambda m: m.text == "⭐ جزوه‌های محبوب")
def popular_notes(message):
    data = load_data()
    all_notes = []
    for category, notes in data['notes'].items():
        for note in notes:
            all_notes.append((category, note))
    
    all_notes.sort(key=lambda x: x[1].get('likes', 0), reverse=True)
    
    if not all_notes:
        bot.reply_to(message, "📭 هنوز جزوه‌ای آپلود نشده!")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for category, note in all_notes[:10]:
        keyboard.add(InlineKeyboardButton(f"⭐ {note['name'][:35]} (❤️ {note.get('likes', 0)})", callback_data=f"popular_{category}_{note['file_id']}"))
    
    bot.send_message(message.chat.id, "⭐ **محبوب‌ترین جزوه‌ها**\n\nبر اساس امتیاز کاربران:", reply_markup=keyboard)

# ========== 2. سیستم امتیازدهی و سطح ==========
@bot.message_handler(func=lambda m: m.text == "🏆 کارنامه من")
def my_profile(message):
    data = load_data()
    uid = str(message.from_user.id)
    
    score = data['scores'].get(uid, 0)
    level = data['levels'].get(uid, 1)
    streak = data['daily_streak'].get(uid, {}).get('count', 0)
    rank = get_rank(message.from_user.id)
    
    next_level_score = (level + 1) * 100
    remain = next_level_score - score
    progress = int((score / next_level_score) * 100) if next_level_score > 0 else 0
    progress_bar = "█" * (progress // 5) + "░" * (20 - (progress // 5))
    
    total_notes_uploaded = sum(1 for cat in data['notes'].values() for n in cat if n.get('uploader') == message.from_user.id)
    total_downloads = sum(n.get('downloads', 0) for cat in data['notes'].values() for n in cat if n.get('uploader') == message.from_user.id)
    
    msg = f"🏆 **کارنامه تحصیلی {message.from_user.first_name}** 🏆\n\n"
    msg += f"🌟 **امتیاز کل:** {score}\n"
    msg += f"📊 **سطح:** {level}\n"
    msg += f"🏅 **رتبه:** {rank if rank else 'در حال محاسبه'}\n"
    msg += f"🔥 **استریک روزانه:** {streak} روز\n\n"
    msg += f"📈 **پیشرفت به سطح بعد:**\n"
    msg += f"`{progress_bar}` {progress}%\n"
    msg += f"🔜 امتیاز نیاز: {remain}\n\n"
    msg += f"📚 **جزوه‌های آپلود شده:** {total_notes_uploaded}\n"
    msg += f"📥 **کل دانلود جزوات شما:** {total_downloads}\n"
    msg += f"📊 **کل کاربران:** {len(data['users'])}\n\n"
    msg += f"✨ با آپلود جزوه و فعالیت بیشتر امتیاز بگیر!"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 لیگ برتر")
def leaderboard(message):
    data = load_data()
    scores = data['scores']
    
    if not scores:
        bot.reply_to(message, "📊 هنوز امتیازی ثبت نشده!")
        return
    
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:15]
    
    msg = "🏆 **لیگ برتر دانشجویان** 🏆\n\n"
    
    for i, (uid, score) in enumerate(sorted_scores, 1):
        level = data['levels'].get(uid, 1)
        try:
            chat = bot.get_chat(int(uid))
            name = f"{chat.first_name or ''} {chat.last_name or ''}"[:25]
        except:
            name = f"کاربر {uid[:6]}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{medal} **{name}**\n"
        msg += f"   🌟 {score} امتیاز | 📊 سطح {level}\n\n"
    
    # امتیاز خود کاربر
    uid = str(message.from_user.id)
    user_score = scores.get(uid, 0)
    user_rank = get_rank(message.from_user.id)
    
    if user_rank:
        msg += f"\n🎯 **رتبه شما:** {user_rank} از {len(scores)}\n"
        msg += f"🌟 **امتیاز شما:** {user_score}\n"
        if user_rank <= 10:
            msg += f"🔥 در بین ۱۰ نفر برتر هستی! ادامه بده!"
        else:
            diff = sorted_scores[9][1] - user_score if len(sorted_scores) > 9 else 0
            msg += f"📈 تا ورود به لیگ برتر: {diff} امتیاز نیاز داری!"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# ========== 3. بازی‌ها و سرگرمی ==========
@bot.message_handler(func=lambda m: m.text == "🎮 بازی و سرگرمی")
def games_menu(message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎲 تاس", callback_data="game_dice"),
        InlineKeyboardButton("🎯 حدس عدد", callback_data="game_number"),
        InlineKeyboardButton("📝 مسابقه", callback_data="game_quiz"),
        InlineKeyboardButton("🎰 ماشین شانس", callback_data="game_slot"),
        InlineKeyboardButton("✂️ سنگ کاغذ قیچی", callback_data="game_rps"),
        InlineKeyboardButton("🎯 شانس", callback_data="game_luck")
    )
    bot.send_message(message.chat.id, "🎮 **بازی و سرگرمی**\n\nیک بازی رو انتخاب کن و امتیاز جمع کن! 🎁", reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def play_dice(call):
    dice = random.randint(1, 6)
    points = dice * 2
    add_score(call.from_user.id, points, "بازی تاس")
    bot.send_dice(call.message.chat.id, emoji="🎲")
    time.sleep(1)
    bot.send_message(call.message.chat.id, f"🎲 **عدد {dice} اومد!**\n🌟 +{points} امتیاز گرفتی!", parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_number")
def play_number(call):
    number = random.randint(1, 50)
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🎯 **حدس عدد بین 1 تا 50**\n\nیه عدد بفرست (۳ تا شانس داری):")
    bot.register_next_step_handler(msg, check_guess, number, 3)

def check_guess(message, target, attempts):
    try:
        guess = int(message.text)
        if guess == target:
            points = 15
            add_score(message.from_user.id, points, "برنده بازی حدس عدد")
            bot.reply_to(message, f"🎉 **تبریک! درست حدس زدی!**\nعدد {target} بود.\n🌟 +{points} امتیاز!", parse_mode='Markdown')
        elif attempts > 1:
            hint = "بزرگ‌تر" if guess < target else "کوچک‌تر"
            msg = bot.reply_to(message, f"❌ نه! عدد **{hint}** از {guess} هست.\n🔁 {attempts-1} شانس دیگه داری!")
            bot.register_next_step_handler(msg, check_guess, target, attempts-1)
        else:
            bot.reply_to(message, f"😔 بازی تموم شد! عدد {target} بود.\n💪 دفعه بعد حتما میبری!", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ لطفا یه عدد معتبر بفرست!")

@bot.callback_query_handler(func=lambda call: call.data == "game_quiz")
def play_quiz(call):
    quizzes = [
        {"q": "Python زبان برنامه‌نویسی در چه سالی ساخته شد؟", "a": "1991", "options": ["1989", "1991", "1995", "2000"]},
        {"q": "تلگرام در چه سالی ساخته شد؟", "a": "2013", "options": ["2011", "2012", "2013", "2014"]},
        {"q": "کدام یک از اینها زبان برنامه‌نویسی است؟", "a": "Python", "options": ["HTML", "CSS", "Python", "JSON"]},
        {"q": "گیت‌هاب برای چیست؟", "a": "ذخیره کد", "options": ["شبکه اجتماعی", "ذخیره کد", "پخش فیلم", "ایمیل"]},
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
        bot.edit_message_text(f"✅ **پاسخ صحیح!**\n🌟 +{points} امتیاز", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    else:
        bot.edit_message_text(f"❌ **پاسخ اشتباه!**\n✅ پاسخ صحیح: {correct}", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_slot")
def play_slot(call):
    slots = ["🍒", "🍊", "🍋", "🍉", "⭐", "7️⃣"]
    result = [random.choice(slots) for _ in range(3)]
    
    if result[0] == result[1] == result[2]:
        points = 50
        msg = "🎉 **جکپات!** 🎉"
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        points = 10
        msg = "🎈 **بردی!**"
    else:
        points = 0
        msg = "😔 **بازنده شدی!**"
    
    add_score(call.from_user.id, points, "بازی ماشین شانس")
    
    bot.send_message(
        call.message.chat.id,
        f"🎰 **ماشین شانس**\n\n"
        f"`{result[0]} | {result[1]} | {result[2]}`\n\n"
        f"{msg} 🌟 +{points} امتیاز",
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_rps")
def play_rps(call):
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("✊ سنگ", callback_data="rps_sang"),
        InlineKeyboardButton("✋ کاغذ", callback_data="rps_kaghaz"),
        InlineKeyboardButton("✌️ قیچی", callback_data="rps_gheychi")
    )
    bot.edit_message_text("✂️ **سنگ کاغذ قیچی**\n\nیکی رو انتخاب کن:", call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps_"))
def play_rps_result(call):
    user_choice = call.data.replace("rps_", "")
    choices = {"sang": "✊ سنگ", "kaghaz": "✋ کاغذ", "gheychi": "✌️ قیچی"}
    bot_choice = random.choice(["sang", "kaghaz", "gheychi"])
    
    rules = {
        ("sang", "gheychi"): "win",
        ("kaghaz", "sang"): "win",
        ("gheychi", "kaghaz"): "win"
    }
    
    if user_choice == bot_choice:
        points = 5
        result = "مساوی"
    elif rules.get((user_choice, bot_choice)) == "win":
        points = 15     
        result = "بردی"
    else:
        points = 0
        result = "باختی"
    
    add_score(call.from_user.id, points, f"بازی سنگ کاغذ قیچی - {result}")
    
    bot.edit_message_text(
        f"✂️ **سنگ کاغذ قیچی**\n\n"
        f"شما: {choices[user_choice]}\n"
        f"ربات: {choices[bot_choice]}\n\n"
        f"**{result}** 🌟 +{points} امتیاز",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "game_luck")
def play_luck(call):
    luck = random.randint(1, 100)
    if luck <= 10:
        points = 100
        msg = "🎉 **شانس فوق‌العاده!** 🎉"
    elif luck <= 30:
        points = 50
        msg = "🎈 **شانس خوب!** 🎈"
    elif luck <= 60:
        points = 20
        msg = "👍 **شانس معمولی**"
    elif luck <= 80:
        points = 5
        msg = "🙂 **شانس کم**"
    else:
        points = 0
        msg = "😔 **شانس نیاوردی**"
    
    add_score(call.from_user.id, points, "بازی شانس")
    
    bot.send_message(
        call.message.chat.id,
        f"🎯 **بازی شانس**\n\n"
        f"شانس شما: {luck}%\n"
        f"{msg} 🌟 +{points} امتیاز",
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

# ========== 4. فال حافظ ==========
@bot.message_handler(func=lambda m: m.text == "🔮 فال حافظ")
def fortune(message):
    fortunes = [
        {"verse": "صبا به لطف بگو آن غزال رعنا را", "meaning": "به زودی خبرهای خوبی بهت می‌رسه! صبور باش. ✨"},
        {"verse": "در این زمانه رفیقی که خالی از خلل است", "meaning": "به دوستان واقعی خود اعتماد کن. رابطه‌ای پایدار در انتظارته. 🤝"},
        {"verse": "ساقیا برخیز و درده جام را", "meaning": "زندگی رو ساده بگیر و از لحظه لذت ببر. غم‌هات کم میشه. 🍃"},
        {"verse": "حافظا روزی تو را در کنج رندی خواهند یافت", "meaning": "مسیر درست رو پیدا می‌کنی. به قلبت اعتماد کن. 🎯"},
        {"verse": "اگر آن ترک شیرازی به دست آرد دل ما را", "meaning": "عشق و علاقه جدیدی وارد زندگیت میشه. بهش فرصت بده. 💕"},
        {"verse": "به میخانه دوش از اهل صفا", "meaning": "امروز روز خوبی برای شروع کارهای جدید هست. 🚀"},
        {"verse": "دلا بسوز که سوز تو کارها بکند", "meaning": "با تلاش و پشتکار به همه چیز میرسی. 💪"},
    ]
    
    f = random.choice(fortunes)
    score = add_score(message.from_user.id, 2, "فال حافظ")
    
    msg = f"🍃 **فال حافظ** 🍃\n\n"
    msg += f"📜 {f['verse']}\n\n"
    msg += f"✨ **تعبیر:**\n{f['meaning']}\n\n"
    msg += f"🌸 +2 امتیاز | امتیاز کل: {score}"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# ========== 5. تکالیف و برنامه ریزی ==========
@bot.message_handler(func=lambda m: m.text == "📝 ثبت تکلیف")
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
            subject = parts[0].strip()
            description = parts[1].strip()
            deadline = parts[2].strip() if len(parts) > 2 else "نامشخص"
            
            data = load_data()
            data['homeworks'].append({
                'user_id': message.from_user.id,
                'user_name': message.from_user.first_name,
                'subject': subject,
                'description': description,
                'deadline': deadline,
                'date': str(datetime.now()),
                'status': 'pending'
            })
            save_data(data)
            
            score = add_score(message.from_user.id, 5, "ثبت تکلیف")
            
            bot.reply_to(
                message,
                f"✅ **تکلیف ثبت شد!**\n\n"
                f"📚 درس: {subject}\n"
                f"📝 توضیح: {description}\n"
                f"⏰ ددلاین: {deadline}\n\n"
                f"🌟 +5 امتیاز | کل: {score}"
            )
        else:
            raise ValueError
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `درس|توضیح|ددلاین`")

@bot.message_handler(func=lambda m: m.text == "✅ تکالیف من")
def show_homeworks(message):
    data = load_data()
    user_homeworks = [h for h in data['homeworks'] if h['user_id'] == message.from_user.id]
    
    if not user_homeworks:
        bot.reply_to(message, "✅ هیچ تکلیفی ثبت نکردی!\nاز دکمه 📝 ثبت تکلیف استفاده کن.")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, h in enumerate(reversed(user_homeworks[-10:])):
        status = "✅" if h.get('status') == 'done' else "⏳"
        keyboard.add(InlineKeyboardButton(f"{status} {h['subject']} - {h['deadline']}", callback_data=f"hw_{i}"))
    
    bot.send_message(message.chat.id, "✅ **لیست تکالیف شما**", reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == "📅 تقویم تحصیلی")
def show_calendar(message):
    data = load_data()
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 همه تکالیف", callback_data="all_homeworks"),
        InlineKeyboardButton("📆 امتحانات", callback_data="all_exams"),
        InlineKeyboardButton("🎉 رویدادها", callback_data="all_events"),
        InlineKeyboardButton("➕ ثبت امتحان", callback_data="add_exam"),
        InlineKeyboardButton("🎉 ثبت رویداد", callback_data="add_event")
    )
    
    bot.send_message(message.chat.id, "📅 **تقویم تحصیلی گروه**\n\nاز دکمه‌های زیر استفاده کن:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "all_homeworks")
def all_homeworks(call):
    data = load_data()
    homeworks = data['homeworks']
    
    if not homeworks:
        bot.send_message(call.message.chat.id, "📝 هیچ تکلیفی ثبت نشده!")
        bot.answer_callback_query(call.id)
        return
    
    msg = "📝 **تکالیف ثبت شده گروه**\n\n"
    for i, h in enumerate(reversed(homeworks[-15:]), 1):
        status = "✅ انجام شده" if h.get('status') == 'done' else "⏳ در حال انجام"
        msg += f"{i}. **{h['subject']}**\n"
        msg += f"   👤 {h['user_name']}\n"
        msg += f"   📝 {h['description'][:50]}\n"
        msg += f"   ⏰ {h['deadline']} | {status}\n\n"
    
    bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "add_exam")
def add_exam_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📆 **ثبت امتحان جدید**\n\nفرمت: `نام درس|تاریخ|توضیح`\nمثال: `ریاضی 2|1403/04/20|استاد احمدی`")
    bot.register_next_step_handler(msg, save_exam)

def save_exam(message):
    try:
        parts = message.text.split('|')
        subject = parts[0].strip()
        date = parts[1].strip() if len(parts) > 1 else "نامشخص"
        desc = parts[2].strip() if len(parts) > 2 else ""
        
        data = load_data()
        data['exams'].append({
            'subject': subject,
            'date': date,
            'description': desc,
            'added_by': message.from_user.first_name,
            'added_at': str(datetime.now())
        })
        save_data(data)
        
        bot.reply_to(message, f"✅ امتحان **{subject}** در تاریخ {date} ثبت شد!")
    except:
        bot.reply_to(message, "❌ فرمت اشتباه!")

@bot.callback_query_handler(func=lambda call: call.data == "all_exams")
def all_exams(call):
    data = load_data()
    exams = data.get('exams', [])
    
    if not exams:
        bot.send_message(call.message.chat.id, "📆 هیچ امتحانی ثبت نشده!")
        bot.answer_callback_query(call.id)
        return
    
    msg = "📆 **تقویم امتحانات**\n\n"
    for i, e in enumerate(reversed(exams[-15:]), 1):
        msg += f"{i}. **{e['subject']}**\n"
        msg += f"   📅 {e['date']}\n"
        if e.get('description'):
            msg += f"   📝 {e['description']}\n"
        msg += f"   👤 ثبت: {e['added_by']}\n\n"
    
    bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "⏰ یادآوری کلاس")
def add_class_reminder(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 شما بن هستید!")
        return
    
    msg = bot.reply_to(
        message,
        "⏰ **ثبت یادآوری کلاس**\n\n"
        "فرمت: `نام کلاس|ساعت|دقیقه|تکرار`\n"
        "مثال: `ریاضی|14|30|شنبه`\n"
        "مثال: `فیزیک|10|0|یکشنبه,سه‌شنبه`\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, save_class_reminder)

def save_class_reminder(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    try:
        parts = message.text.split('|')
        class_name = parts[0].strip()
        hour = int(parts[1])
        minute = int(parts[2])
        repeat = parts[3].strip() if len(parts) > 3 else "یکبار"
        
        data = load_data()
        data['reminders'].append({
            'user_id': message.from_user.id,
            'class_name': class_name,
            'hour': hour,
            'minute': minute,
            'repeat': repeat,
            'chat_id': message.chat.id
        })
        save_data(data)
        
        bot.reply_to(
            message,
            f"✅ **یادآوری کلاس ثبت شد!**\n\n"
            f"📚 کلاس: {class_name}\n"
            f"⏰ ساعت: {hour:02d}:{minute:02d}\n"
            f"📅 تکرار: {repeat}\n\n"
            f"⏰ ۵ دقیقه قبل از کلاس یادآوری می‌کنم!"
        )
        
        # تنظیم یادآوری برای امروز
        now = datetime.now()
        class_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if class_time > now:
            reminder_time = class_time - timedelta(minutes=5)
            if reminder_time > now:
                seconds = (reminder_time - now).seconds
                threading.Timer(seconds, send_class_reminder, args=[message.chat.id, class_name]).start()
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `ریاضی|14|30|شنبه`")

def send_class_reminder(chat_id, class_name):
    bot.send_message(chat_id, f"⏰ **یادآوری کلاس!**\n\n📚 کلاس {class_name} در ۵ دقیقه دیگه شروع میشه!\nآماده باش!", parse_mode='Markdown')

# ========== 6. آب و هوا (فقط همدان) ==========
@bot.message_handler(func=lambda m: m.text == "🌤 آب و هوا")
def weather_hamadan(message):
    status = bot.send_message(message.chat.id, "⏳ در حال دریافت اطلاعات آب و هوای همدان...")
    try:
        # استفاده از API رایگان wttr.in برای همدان
        response = requests.get(f"https://wttr.in/{HAMADAN_CITY}?format=%C+%t+%w+%h&lang=fa", timeout=10)
        weather_data = response.text.strip()
        
        if weather_data:
            # تبدیل درجه سانتی‌گراد
            weather_data = weather_data.replace('+', '').replace('°C', '°')
            
            msg = f"🌤 **آب و هوای همدان**\n\n"
            msg += f"📊 {weather_data}\n\n"
            msg += f"📅 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
            msg += f"💡 توصیه: "
            if "باران" in weather_data:
                msg += "چتر همراه داشته باش! ☔"
            elif "برف" in weather_data:
                msg += "لباس گرم بپوش! ❄️"
            elif "آفتابی" in weather_data:
                msg += "روز خوبی برای درس خوندنه! ☀️"
            else:
                msg += "روز خوبی داشته باش! 🌸"
            
            bot.edit_message_text(msg, status.chat.id, status.message_id, parse_mode='Markdown')
            add_score(message.from_user.id, 1, "دریافت آب و هوا")
        else:
            bot.edit_message_text("❌ دریافت اطلاعات آب و هوای همدان انجام نشد!", status.chat.id, status.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا در دریافت اطلاعات آب و هوا!\n{str(e)[:50]}", status.chat.id, status.message_id)

# ========== 7. سوال بپرس ==========
@bot.message_handler(func=lambda m: m.text == "❓ سوال بپرس")
def ask_question_prompt(message):
    msg = bot.reply_to(
        message,
        "❓ **پرسش و پاسخ هوشمند**\n\n"
        "سوال خودت رو بپرس.\n\n"
        "مثال:\n"
        "• `آزمون ریاضی کی هست؟`\n"
        "• `جزوه فیزیک کجاست؟`\n"
        "• `تکلیف برنامه‌نویسی چیه؟`\n"
        "• `قوانین گروه چیه؟`\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, answer_question)

def answer_question(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    question = message.text.lower()
    data = load_data()
    
    responses = {
        'امتحان': "📅 لیست امتحانات رو با دکمه 📅 تقویم تحصیلی می‌تونی ببینی!",
        'جزوه': "📚 جزوه‌ها توی کتابخانه جزوات هستن. از دکمه 📚 کتابخانه جزوه استفاده کن!",
        'تکلیف': "✅ تکالیف خودت رو می‌تونی با دکمه 📝 ثبت تکلیف اضافه کنی و با ✅ تکالیف من ببینی!",
        'کلاس': "⏰ برای ثبت یادآوری کلاس از دکمه ⏰ یادآوری کلاس استفاده کن!",
        'امتیاز': "🌟 امتیاز خودت رو با دکمه 🏆 کارنامه من می‌تونی ببینی!",
        'قوانین': "📜 قوانین گروه رو با دکمه 📜 قوانین می‌تونی ببینی!",
        'فال': "🔮 برای فال حافظ از دکمه 🔮 فال حافظ استفاده کن!",
        'بازی': "🎮 برای بازی‌ها از دکمه 🎮 بازی و سرگرمی استفاده کن!",
        'آب و هوا': "🌤 آب و هوای همدان رو با دکمه 🌤 آب و هوا می‌تونی ببینی!",
        'رتبه': "🏆 رتبه خودت رو توی 📊 لیگ برتر می‌تونی ببینی!",
    }
    
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

# ========== 8. قوانین ==========
@bot.message_handler(func=lambda m: m.text == "📜 قوانین")
def show_rules(message):
    data = load_data()
    rules = data.get('rules')
    
    keyboard = InlineKeyboardMarkup()
    if is_admin(message.from_user.id):
        keyboard.add(InlineKeyboardButton("✏️ ویرایش قوانین", callback_data="edit_rules"))
    
    bot.send_message(message.chat.id, rules, reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "edit_rules")
def edit_rules_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📜 **ویرایش قوانین گروه**\n\nقوانین جدید رو وارد کن:")
    bot.register_next_step_handler(msg, save_rules)

def save_rules(message):
    data = load_data()
    data['rules'] = message.text
    save_data(data)
    bot.reply_to(message, "✅ قوانین گروه به‌روزرسانی شد!")

# ========== 9. اعلان‌ها ==========
@bot.message_handler(func=lambda m: m.text == "📢 اعلان‌ها")
def show_announcements(message):
    data = load_data()
    events = data.get('events', [])
    
    if not events:
        bot.reply_to(message, "📢 هیچ اعلان جدیدی وجود ندارد!")
        return
    
    msg = "📢 **آخرین اعلان‌ها**\n\n"
    for event in reversed(events[-10:]):
        msg += f"📌 **{event['title']}**\n"
        msg += f"   📅 {event['date']}\n"
        msg += f"   📝 {event['description'][:100]}\n\n"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# ========== 10. پنل ادمین ==========
@bot.message_handler(func=lambda m: m.text == "👑 پنل ادمین")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین دسترسی داره!")
        return
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**\n\nاز دکمه‌های زیر استفاده کن:", reply_markup=get_admin_keyboard(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    data = load_data()
    total_notes = sum(len(n) for n in data['notes'].values())
    total_scores = sum(data['scores'].values())
    total_homeworks = len(data['homeworks'])
    
    msg = f"📊 **آمار پیشرفته گروه**\n\n"
    msg += f"👥 **کل کاربران:** {len(data['users'])}\n"
    msg += f"📚 **کل جزوات:** {total_notes}\n"
    msg += f"📝 **تکالیف ثبت شده:** {total_homeworks}\n"
    msg += f"🏆 **مجموع امتیاز:** {total_scores}\n"
    msg += f"📊 **میانگین امتیاز:** {total_scores // max(1, len(data['users']))}\n"
    msg += f"🚫 **کاربران بن:** {len(data['banned'])}\n"
    msg += f"⚠️ **اخطارها:** {sum(len(v) for v in data['warnings'].values())}\n"
    msg += f"📁 **دسته‌های جزوه:** {len(data['notes'])}\n"
    msg += f"📅 **امتحانات:** {len(data.get('exams', []))}\n"
    msg += f"🎉 **رویدادها:** {len(data.get('events', []))}\n"
    msg += f"🔥 **فعال‌ترین کاربر:** در حال محاسبه..."
    
    bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    data = load_data()
    users = data.get('users', [])
    
    if not users:
        bot.send_message(call.message.chat.id, "📭 هنوز کاربری ثبت نشده!")
        bot.answer_callback_query(call.id)
        return
    
    msg = "👥 **لیست کاربران گروه**\n\n"
    for i, uid in enumerate(users[-30:], 1):
        score = data['scores'].get(str(uid), 0)
        level = data['levels'].get(str(uid), 1)
        try:
            chat = bot.get_chat(uid)
            name = f"{chat.first_name or ''} {chat.last_name or ''}"[:25]
            msg += f"{i}. **{name}**\n"
            msg += f"   🆔 `{uid}` | 🌟 {score} | 📊 سطح {level}\n\n"
        except:
            msg += f"{i}. کاربر ناشناس\n   🆔 `{uid}` | 🌟 {score} | 📊 سطح {level}\n\n"
    
    bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban_menu")
def admin_ban_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🚫 بن کاربر", callback_data="admin_ban"),
        InlineKeyboardButton("✅ آنبن کاربر", callback_data="admin_unban"),
        InlineKeyboardButton("📜 لیست بن شده‌ها", callback_data="admin_banned_list"),
        InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")
    )
    bot.edit_message_text("🚫 **مدیریت بن کاربران**", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_ban")
def ban_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🚫 **بن کردن کاربر**\n\nآیدی عددی یا یوزرنیم کاربر رو بفرست:\nمثال: `@username` یا `123456789`")
    bot.register_next_step_handler(msg, ban_user)

def ban_user(message):
    try:
        target = message.text.strip()
        if target.startswith('@'):
            user = bot.get_chat(target)
            user_id = user.id
            name = user.first_name
        else:
            user_id = int(target)
            name = target
        
        data = load_data()
        if user_id not in data['banned']:
            data['banned'].append(user_id)
            save_data(data)
            bot.reply_to(message, f"✅ کاربر **{name}** با موفقیت بن شد!", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"⚠️ کاربر {name} قبلاً بن شده!", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: کاربر پیدا نشد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_unban")
def unban_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "✅ **آنبن کاربر**\n\nآیدی عددی کاربر رو بفرست:")
    bot.register_next_step_handler(msg, unban_user)

def unban_user(message):
    try:
        user_id = int(message.text.strip())
        data = load_data()
        if user_id in data['banned']:
            data['banned'].remove(user_id)
            save_data(data)
            bot.reply_to(message, f"✅ کاربر {user_id} آنبن شد!")
        else:
            bot.reply_to(message, f"⚠️ کاربر {user_id} در لیست بن نیست!")
    except:
        bot.reply_to(message, "❌ ایدی نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_banned_list")
def banned_list(call):
    data = load_data()
    banned = data.get('banned', [])
    
    if not banned:
        bot.send_message(call.message.chat.id, "📭 هیچ کاربر بن شده‌ای وجود ندارد!")
        bot.answer_callback_query(call.id)
        return
    
    msg = "🚫 **لیست کاربران بن شده**\n\n"
    for uid in banned[-20:]:
        try:
            chat = bot.get_chat(uid)
            name = f"{chat.first_name or ''} {chat.last_name or ''}"[:30]
            msg += f"• {name}\n  🆔 `{uid}`\n\n"
        except:
            msg += f"• کاربر ناشناس\n  🆔 `{uid}`\n\n"
    
    bot.send_message(call.message.chat.id, msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_warn_menu")
def admin_warn_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⚠️ اخطار", callback_data="admin_warn"),
        InlineKeyboardButton("📜 لیست اخطارها", callback_data="admin_warn_list"),
        InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")
    )
    bot.edit_message_text("⚠️ **مدیریت اخطارها**", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_warn")
def warn_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "⚠️ **اخطار به کاربر**\n\nفرمت: `@username دلیل`\nمثال: `@ali اسپم`")
    bot.register_next_step_handler(msg, process_warn)

def process_warn(message):
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            raise ValueError
        
        target = parts[0].strip()
        reason = parts[1].strip()
        
        if target.startswith('@'):
            user = bot.get_chat(target)
            user_id = user.id
            name = user.first_name
        else:
            user_id = int(target)
            name = target
        
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
            if user_id not in data['banned']:
                data['banned'].append(user_id)
                save_data(data)
            bot.reply_to(message, f"⚠️ کاربر {name} بعد از {warn_count} اخطار **بن شد!**\nآخرین دلیل: {reason}", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"⚠️ اخطار {warn_count}/3 به {name}\nدلیل: {reason}", parse_mode='Markdown')
            
            # ارسال اخطار به کاربر
            try:
                bot.send_message(user_id, f"⚠️ **شما در گروه اخطار دریافت کردید!**\n\nدلیل: {reason}\nاخطار {warn_count}/3\n\nلطفا قوانین گروه رو رعایت کن!", parse_mode='Markdown')
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: کاربر پیدا نشد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def broadcast_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📢 **ارسال اعلان همگانی**\n\nمتن پیام رو بفرست.\nمیتونی متن، عکس یا فایل بفرستی.\n\nبرای لغو /cancel")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    data = load_data()
    users = data.get('users', [])
    success = 0
    fail = 0
    
    status = bot.reply_to(message, "⏳ در حال ارسال اعلان به کاربران...")
    
    for user_id in users:
        try:
            if message.text:
                bot.send_message(user_id, f"📢 **اعلان گروهی:**\n\n{message.text}", parse_mode='Markdown')
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success += 1
        except:
            fail += 1
        time.sleep(0.03)
    
    bot.edit_message_text(
        f"✅ **اعلان ارسال شد!**\n\n✓ موفق: {success}\n✗ ناموفق: {fail}",
        status.chat.id,
        status.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_welcome")
def admin_welcome(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📝 متن خوش‌آمدگویی", callback_data="set_welcome_text"),
        InlineKeyboardButton("🎬 گیف خوش‌آمدگویی", callback_data="set_welcome_gif"),
        InlineKeyboardButton("❌ غیرفعال", callback_data="disable_welcome"),
        InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")
    )
    bot.edit_message_text("🎉 **تنظیمات خوش‌آمدگویی**", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_text")
def set_welcome_text_prompt(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📝 متن خوش‌آمدگویی رو وارد کن.\n\nاز `{name}` برای اسم کاربر استفاده کن.\nمثال: `به گروه خوش اومدی {name} جان! 🎉`")
    bot.register_next_step_handler(msg, save_welcome_text)

def save_welcome_text(message):
    data = load_data()
    data['welcome_text'] = message.text
    save_data(data)
    bot.reply_to(message, "✅ متن خوش‌آمدگویی ذخیره شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_purge")
def purge_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "🗑 **پاکسازی پیام‌ها**\n\nتعداد پیام‌هایی که می‌خوای پاک بشه رو بفرست (حداکثر 100):")
    bot.register_next_step_handler(msg, purge_messages)

def purge_messages(message):
    try:
        count = min(int(message.text), 100)
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
        
        bot.reply_to(message, f"✅ **{deleted} پیام** با موفقیت پاک شد!", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ لطفا یک عدد معتبر بفرست!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.edit_message_text("👑 **پنل مدیریت پیشرفته**\n\nاز دکمه‌های زیر استفاده کن:", call.message.chat.id, call.message.message_id, reply_markup=get_admin_keyboard(), parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_close")
def admin_close(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "پنل بسته شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ فقط ادمین!", show_alert=True)
        return
    
    data = load_data()
    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    bot.answer_callback_query(call.id, "در حال تهیه پشتیبان...")
    bot.send_document(call.message.chat.id, InputFile(DATA_FILE, filename=backup_file))
    bot.send_message(call.message.chat.id, "✅ **پشتیبان از دیتابیس گرفته شد!**", parse_mode='Markdown')

# ========== خوش‌آمدگویی عضو جدید ==========
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    data = load_data()
    welcome_text = data.get('welcome_text')
    welcome_gif = data.get('welcome_gif')
    
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            continue
        
        name = member.first_name
        add_score(member.id, 5, "عضویت در گروه")
        
        if welcome_gif:
            try:
                bot.send_animation(message.chat.id, welcome_gif, caption=welcome_text.format(name=name) if welcome_text else None)
            except:
                pass
        elif welcome_text:
            bot.send_message(message.chat.id, welcome_text.format(name=name))
        else:
            bot.send_message(message.chat.id, f"🎉 به {name} عزیز خوش اومدی! +5 امتیاز")

# ========== حذف پیام لینک از کاربران عادی ==========
@bot.message_handler(func=lambda m: True)
def filter_messages(message):
    # حذف پیام لینک از کاربران غیر ادمین
    if not is_admin(message.from_user.id) and not is_banned(message.from_user.id):
        if 'http://' in message.text or 'https://' in message.text or 't.me/' in message.text:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, f"⛔ {message.from_user.first_name} لینک زدن ممنوع!", delete_in_sec=3)
            except:
                pass
            return
    
    # فعالیت روزانه و امتیاز
    if not is_banned(message.from_user.id):
        data = load_data()
        uid = str(message.from_user.id)
        
        # افزایش آمار پیام گروه
        data['group_stats']['messages'] = data['group_stats'].get('messages', 0) + 1
        save_data(data)
        
        last = data.get('last_active', {}).get(uid, 0)
        if time.time() - last > 300:  # هر 5 دقیقه یک بار امتیاز
            add_score(message.from_user.id, 1, "فعالیت در گروه")
            if 'last_active' not in data:
                data['last_active'] = {}
            data['last_active'][uid] = time.time()
            save_data(data)

# ========== اجرا ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 **ربات فوق پیشرفته گروه دانشجویی**")
    print("=" * 50)
    print("📚 جزوات | 🏆 امتیاز | 🎮 بازی | 📝 تکلیف")
    print("🌤 آب و هوا | 🔮 فال | 📅 تقویم | 👑 مدیریت")
    print("=" * 50)
    print("✅ ربات با موفقیت روشن شد!")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"⚠️ خطا: {e}")
            time.sleep(5)
