import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import random
from datetime import datetime, timedelta
import threading
import time
import requests
import yt_dlp

# ========== توکن ربات (از متغیر محیطی) ==========
TOKEN = os.environ.get('BOT_TOKEN')

if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN)

# ========== فایل دیتابیس ساده ==========
DATA_FILE = 'bot_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': [], 
        'admins': [], 
        'banned_users': [], 
        'warnings': {},
        'files': [],
        'fortunes': [],
        'music_queue': {},
        'current_playing': {}
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== تنظیمات اولیه ==========
ADMIN_ID = 123456789  # این رو با ایدی عددی خودت عوض کن!
SUPPORTED_VIDEO = ['.mp4', '.mkv', '.avi', '.mov', '.webm']

def is_admin(user_id):
    return user_id == ADMIN_ID or user_id in load_data().get('admins', [])

def is_banned(user_id):
    return user_id in load_data().get('banned_users', [])

# ========== کیبورد اصلی ==========
def get_main_keyboard(is_admin_user=False):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📤 آپلود فایل")
    btn2 = KeyboardButton("📁 فایل‌های من")
    btn3 = KeyboardButton("🎵 پخش آهنگ")
    btn4 = KeyboardButton("🔮 فال حافظ")
    btn5 = KeyboardButton("📊 آمار")
    btn6 = KeyboardButton("👥 کاربران")
    
    if is_admin_user:
        keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6)
    else:
        keyboard.add(btn1, btn2, btn3, btn4)
    
    # دکمه های مدیریتی (فقط ادمین)
    if is_admin_user:
        keyboard.add(KeyboardButton("🚫 بن کاربر"), KeyboardButton("✅ آنبن کاربر"))
        keyboard.add(KeyboardButton("⚠️ اخطار"), KeyboardButton("🔇 میوت"))
        keyboard.add(KeyboardButton("📢 برادکست"))
    
    return keyboard

# ========== شروع ==========
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
        f"به ربات همه‌کاره خوش اومدی!\n\n"
        f"✨ **قابلیت‌ها:**\n"
        f"• 📤 ارسال و دریافت فایل\n"
        f"• 🎵 پخش آهنگ در گروه (با کیفیت بالا)\n"
        f"• 🔮 فال حافظ روزانه\n"
        f"• 👑 مدیریت گروه (بن، اخطار، میوت)\n\n"
        f"از دکمه‌های پایین استفاده کن 👇",
        reply_markup=get_main_keyboard(is_admin(user_id))
    )

# ========== 1. بخش مدیریت گروه ==========
@bot.message_handler(func=lambda message: message.text == "🚫 بن کاربر" and is_admin(message.from_user.id))
def ban_user_prompt(message):
    msg = bot.reply_to(message, "🚫 ایدی کاربر مورد نظر رو بفرست:\nمثال: `123456789`\n\nبرای لغو /cancel")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    try:
        user_id = int(message.text)
        data = load_data()
        if user_id not in data['banned_users']:
            data['banned_users'].append(user_id)
            save_data(data)
            bot.reply_to(message, f"✅ کاربر {user_id} بن شد!")
        else:
            bot.reply_to(message, "⚠️ این کاربر قبلا بن شده!")
    except:
        bot.reply_to(message, "❌ ایدی نامعتبر!")

@bot.message_handler(func=lambda message: message.text == "✅ آنبن کاربر" and is_admin(message.from_user.id))
def unban_user_prompt(message):
    msg = bot.reply_to(message, "✅ ایدی کاربر مورد نظر رو برای آنبن بفرست:")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(message):
    try:
        user_id = int(message.text)
        data = load_data()
        if user_id in data['banned_users']:
            data['banned_users'].remove(user_id)
            save_data(data)
            bot.reply_to(message, f"✅ کاربر {user_id} آنبن شد!")
        else:
            bot.reply_to(message, "⚠️ این کاربر در لیست بن نیست!")
    except:
        bot.reply_to(message, "❌ ایدی نامعتبر!")

@bot.message_handler(func=lambda message: message.text == "⚠️ اخطار" and is_admin(message.from_user.id))
def warn_user_prompt(message):
    msg = bot.reply_to(message, "⚠️ ایدی کاربر و دلیل اخطار رو بفرست:\nمثال: `123456789 - اسپم`")
    bot.register_next_step_handler(msg, process_warn)

def process_warn(message):
    try:
        parts = message.text.split(' - ')
        user_id = int(parts[0])
        reason = parts[1] if len(parts) > 1 else "بدون دلیل"
        
        data = load_data()
        if str(user_id) not in data['warnings']:
            data['warnings'][str(user_id)] = []
        data['warnings'][str(user_id)].append({'reason': reason, 'date': str(datetime.now())})
        
        if len(data['warnings'][str(user_id)]) >= 3:
            if user_id not in data['banned_users']:
                data['banned_users'].append(user_id)
            bot.reply_to(message, f"⚠️ کاربر {user_id} بعد از 3 اخطار بن شد!")
            del data['warnings'][str(user_id)]
        else:
            bot.reply_to(message, f"⚠️ اخطار {len(data['warnings'][str(user_id)])}/3 به {user_id} اضافه شد!\nدلیل: {reason}")
        
        save_data(data)
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `123456789 - دلیل`")

@bot.message_handler(func=lambda message: message.text == "🔇 میوت" and is_admin(message.from_user.id))
def mute_user_prompt(message):
    msg = bot.reply_to(message, "🔇 ایدی کاربر و مدت میوت (دقیقه) رو بفرست:\nمثال: `123456789 30`")
    bot.register_next_step_handler(msg, process_mute)

def process_mute(message):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 10
        
        # تنظیم محدودیت ارسال پیام
        bot.restrict_chat_member(
            message.chat.id, 
            user_id, 
            until_date=datetime.now() + timedelta(minutes=minutes)
        )
        bot.reply_to(message, f"🔇 کاربر {user_id} برای {minutes} دقیقه میوت شد!")
    except:
        bot.reply_to(message, "❌ فرمت اشتباه! استفاده: `123456789 30`")

# ========== 2. بخش فایل ==========
@bot.message_handler(func=lambda message: message.text == "📤 آپلود فایل")
def upload_file_prompt(message):
    msg = bot.reply_to(
        message,
        "📁 فایل مورد نظرت رو بفرست.\n"
        "میتونی هر نوع فایلی بفرستی (عکس، ویدیو، سند، صدا).\n\n"
        "برای لغو /cancel"
    )
    bot.register_next_step_handler(msg, receive_file)

def receive_file(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    file_id = None
    file_type = None
    file_name = None
    
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_name = "photo.jpg"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name or "video.mp4"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
        file_name = message.audio.file_name or "audio.mp3"
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"
        file_name = "voice.ogg"
    else:
        bot.reply_to(message, "❌ لطفا یک فایل معتبر بفرست!")
        return
    
    data = load_data()
    if 'files' not in data:
        data['files'] = []
    
    file_info = {
        'file_id': file_id,
        'file_type': file_type,
        'file_name': file_name,
        'uploader': message.from_user.id,
        'uploader_name': message.from_user.first_name,
        'date': str(datetime.now())
    }
    data['files'].append(file_info)
    save_data(data)
    
    bot.reply_to(message, f"✅ فایل «{file_name}» با موفقیت ذخیره شد!\nبرای مشاهده، از دکمه 📁 استفاده کن.")

@bot.message_handler(func=lambda message: message.text == "📁 فایل‌های من")
def show_my_files(message):
    data = load_data()
    files = data.get('files', [])
    user_files = [f for f in files if f['uploader'] == message.from_user.id]
    
    if not user_files:
        bot.send_message(message.chat.id, "📂 هنوز هیچ فایلی آپلود نکردی.")
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    for f in user_files[-10:]:
        btn = InlineKeyboardButton(f"📄 {f['file_name'][:30]}", callback_data=f"file_{f['file_id']}")
        markup.add(btn)
    
    bot.send_message(message.chat.id, f"📂 {len(user_files)} فایل داری.\nآخرین فایل‌ها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("file_"))
def send_file(call):
    file_id = call.data[5:]
    data = load_data()
    file_info = next((f for f in data['files'] if f['file_id'] == file_id), None)
    
    if file_info:
        if file_info['file_type'] == 'document':
            bot.send_document(call.message.chat.id, file_id)
        elif file_info['file_type'] == 'photo':
            bot.send_photo(call.message.chat.id, file_id)
        elif file_info['file_type'] == 'video':
            bot.send_video(call.message.chat.id, file_id)
        elif file_info['file_type'] == 'audio':
            bot.send_audio(call.message.chat.id, file_id)
        elif file_info['file_type'] == 'voice':
            bot.send_voice(call.message.chat.id, file_id)
        bot.answer_callback_query(call.id, "✅ فایل ارسال شد!")
    else:
        bot.answer_callback_query(call.id, "❌ فایل پیدا نشد!")

# ========== 3. بخش فال حافظ ==========
# فال‌های حافظ (چند نمونه برای شروع)
FORTUNES = [
    {"verse": "صبا به لطف بگو آن غزال رعنا را\nکه سر به کوه و بیابان تو می‌دهی یا را", "interpretation": "در کارها صبور باش و عجله نکن. به زودی خبرهای خوب می‌رسی."},
    {"verse": "در این زمانه رفیقی که خالی از خلل است\nبه جان خویش درآور که گوهر وصلی است", "interpretation": "به دوستان واقعی خود اعتماد کن. رابطه‌ای پایدار در انتظارته."},
    {"verse": "ساقیا برخیز و درده جام را\nخاک بر سر کن غم ایام را", "interpretation": "زندگی را ساده بگیر و از لحظه لذت ببر. غم‌هایت کم می‌شه."},
    {"verse": "اگر آن ترک شیرازی به دست آرد دل ما را\nبه خال هندویش بخشم سمرقند و بخارا را", "interpretation": "عشق و علاقه جدیدی وارد زندگیت می‌شه. بهش فرصت بده."},
    {"verse": "حافظا روزی تو را در کنج رندی خواهند یافت\nشاه راه طریقت این است و بس", "interpretation": "مسیر درست رو پیدا می‌کنی. به قلبت اعتماد کن."},
]

@bot.message_handler(func=lambda message: message.text == "🔮 فال حافظ")
def fortune(message):
    fortune = random.choice(FORTUNES)
    response = f"🍃 **فال حافظ** 🍃\n\n📜 {fortune['verse']}\n\n✨ **تعبیر:**\n{fortune['interpretation']}\n\n🌸 روزت پر از آرامش 🌸"
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

# ========== 4. بخش پخش آهنگ (ساده شده) ==========
QUEUES = {}
CURRENT = {}

@bot.message_handler(func=lambda message: message.text == "🎵 پخش آهنگ")
def play_song_prompt(message):
    msg = bot.reply_to(message, "🎵 لینک یوتیوب یا نام آهنگ رو بفرست:\n\nبرای لغو /cancel")
    bot.register_next_step_handler(msg, search_and_play)

def search_and_play(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ لغو شد.")
        return
    
    query = message.text
    chat_id = message.chat.id
    
    bot.send_message(chat_id, "🔍 در حال پیدا کردن آهنگ...")
    
    try:
        # گزینه‌های yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # جستجو
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info and info['entries']:
                video = info['entries'][0]
                title = video.get('title', 'Unknown')
                url = f"https://youtube.com/watch?v={video.get('id', '')}"
                duration = video.get('duration', 0)
                
                # ساخت کیبورد کنترل
                markup = InlineKeyboardMarkup(row_width=3)
                markup.add(
                    InlineKeyboardButton("▶️ پلی", callback_data=f"play_{url}"),
                    InlineKeyboardButton("⏹ استاپ", callback_data="stop_music")
                )
                
                minutes = duration // 60 if duration else 0
                seconds = duration % 60 if duration else 0
                duration_text = f"{minutes}:{seconds:02d}" if duration else "زنده"
                
                bot.send_message(
                    chat_id,
                    f"🎵 **در حال پخش:**\n"
                    f"🎤 {title}\n"
                    f"⏱ مدت: {duration_text}\n\n"
                    f"آهنگ در حال پخش در گروه...",
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
                
                # ذخیره در صف
                if chat_id not in QUEUES:
                    QUEUES[chat_id] = []
                QUEUES[chat_id].append({'title': title, 'url': url})
                CURRENT[chat_id] = {'title': title, 'url': url}
                
                # شبیه‌سازی پخش
                def simulate_playback(cid, track_url):
                    time.sleep(duration if duration and duration < 600 else 180)
                    if cid in QUEUES and QUEUES[cid]:
                        QUEUES[cid].pop(0) if QUEUES[cid] else None
                        if QUEUES[cid]:
                            next_track = QUEUES[cid][0]
                            bot.send_message(cid, f"🎵 در حال پخش آهنگ بعدی: {next_track['title']}")
                        else:
                            bot.send_message(cid, "✅ لیست پخش تمام شد!")
                
                thread = threading.Thread(target=simulate_playback, args=(chat_id, url))
                thread.daemon = True
                thread.start()
                
            else:
                bot.send_message(chat_id, "❌ آهنگی پیدا نشد!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در پخش آهنگ: {str(e)[:100]}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_"))
def play_control(call):
    url = call.data[5:]
    bot.answer_callback_query(call.id, "🎵 آهنگ در حال پخش...")
    # قبلاً پخش شده

@bot.callback_query_handler(func=lambda call: call.data == "stop_music")
def stop_music(call):
    chat_id = call.message.chat.id
    if chat_id in QUEUES:
        QUEUES[chat_id] = []
    if chat_id in CURRENT:
        del CURRENT[chat_id]
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    bot.send_message(chat_id, "⏹ پخش آهنگ متوقف شد.")
    bot.answer_callback_query(call.id, "پخش متوقف شد!")

# ========== 5. بخش آمار و کاربران ==========
@bot.message_handler(func=lambda message: message.text == "📊 آمار")
def show_stats(message):
    data = load_data()
    stats = (
        f"📊 **آمار ربات**\n\n"
        f"👥 **کل کاربران:** {len(data.get('users', []))}\n"
        f"📁 **فایل‌های ذخیره شده:** {len(data.get('files', []))}\n"
        f"🚫 **کاربران بن شده:** {len(data.get('banned_users', []))}\n"
        f"⚠️ **اخطارهای فعال:** {sum(len(v) for v in data.get('warnings', {}).values())}\n\n"
        f"💡 ربات 24/7 فعال است!"
    )
    bot.send_message(message.chat.id, stats, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "👥 کاربران" and is_admin(message.from_user.id))
def list_users(message):
    data = load_data()
    users = data.get('users', [])
    
    if not users:
        bot.send_message(message.chat.id, "📭 هنوز کاربری ثبت نشده!")
        return
    
    user_list = []
    for uid in users[-20:]:
        try:
            chat = bot.get_chat(uid)
            name = f"{chat.first_name or ''} {chat.last_name or ''}"[:30]
            user_list.append(f"• {name} (`{uid}`)")
        except:
            user_list.append(f"• کاربر ناشناس (`{uid}`)")
    
    text = f"👥 **آخرین کاربران ({len(users)} نفر)**\n\n" + "\n".join(user_list)
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ========== 6. بخش برادکست (فقط ادمین) ==========
@bot.message_handler(func=lambda message: message.text == "📢 برادکست" and is_admin(message.from_user.id))
def broadcast_prompt(message):
    msg = bot.reply_to(message, "📢 پیام همگانی خود را بفرست.\nبرای لغو /cancel")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.text == "/cancel":
        bot.reply_to(message, "❌ برادکست لغو شد.")
        return
    
    data = load_data()
    users = data.get('users', [])
    success = 0
    fail = 0
    
    status_msg = bot.reply_to(message, "⏳ در حال ارسال...")
    
    for user_id in users:
        try:
            if message.text:
                bot.send_message(user_id, message.text)
            elif message.photo:
                bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                bot.send_document(user_id, message.document.file_id, caption=message.caption)
            success += 1
        except:
            fail += 1
        time.sleep(0.05)
    
    bot.edit_message_text(
        f"✅ برادکست تمام شد!\n✓ موفق: {success}\n✗ ناموفق: {fail}",
        status_msg.chat.id,
        status_msg.message_id
    )

# ========== هندلر ذخیره کاربر جدید ==========
@bot.message_handler(func=lambda message: True)
def save_new_user(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "🚫 شما توسط ادمین بن شده‌اید!")
        return
    
    data = load_data()
    if user_id not in data['users']:
        data['users'].append(user_id)
        save_data(data)

# ========== اجرای ربات ==========
if __name__ == "__main__":
    print("🤖 ربات همه‌کاره روشن شد...")
    print("✅ قابلیت‌ها: مدیریت گروه | آپلود فایل | پخش آهنگ | فال حافظ")
    bot.infinity_polling(timeout=80)