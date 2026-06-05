#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, random, yt_dlp, requests, asyncio, time, threading, re, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes


# ========== DATABASE ==========
class DB:
    def __init__(self):
        self.f = "music_data.json"
        self.d = json.load(open(self.f, 'r', encoding='utf-8')) if os.path.exists(self.f) else {
            'users': [], 'history': {}, 'favorites': {}, 'radio_songs': [], 'playlists': {}
        }
    def save(self): json.dump(self.d, open(self.f, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    def add_user(self, uid, name=None):
        if uid not in [u['id'] for u in self.d['users']]:
            self.d['users'].append({'id': uid, 'name': name, 'joined': str(datetime.now())[:19]}); self.save()
    def add_hist(self, cid, song):
        cid = str(cid)
        if cid not in self.d['history']: self.d['history'][cid] = []
        self.d['history'][cid].append({'song': song, 'time': str(datetime.now())[:19]})
        if len(self.d['history'][cid]) > 50: self.d['history'][cid] = self.d['history'][cid][-50:]
        self.save()
    def add_radio(self, song):
        if song not in self.d['radio_songs']: self.d['radio_songs'].append(song); self.save(); return True
        return False
    def get_radio(self): return self.d['radio_songs']
    def add_fav(self, uid, song):
        uid = str(uid)
        if uid not in self.d['favorites']: self.d['favorites'][uid] = []
        if song['id'] not in [s['id'] for s in self.d['favorites'][uid]]:
            self.d['favorites'][uid].append(song); self.save(); return True
        return False
    def get_fav(self, uid): return self.d['favorites'].get(str(uid), [])
    def get_stats(self):
        return {
            'users': len(self.d['users']),
            'radio': len(self.d['radio_songs']),
            'favs': sum(len(v) for v in self.d['favorites'].values()),
            'history': sum(len(v) for v in self.d['history'].values())
        }

db = DB()

# ========== DOWNLOADER ==========
class DL:
    def __init__(self):
        self.cache = {}
    
    def search(self, q, n=10):
        results = []
        # YouTube
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as y:
                res = y.extract_info(f"ytsearch{n}:{q}", download=False)
                for e in res.get('entries', []):
                    results.append({
                        'id': e.get('id', ''), 'title': e.get('title', 'بدون عنوان')[:100],
                        'duration': e.get('duration', 0), 'uploader': e.get('uploader', ''),
                        'url': f"https://youtube.com/watch?v={e.get('id', '')}", 'source': 'youtube',
                        'views': e.get('view_count', 0)
                    })
        except: pass
        
        # Aparat
        try:
            resp = requests.get(f"https://www.aparat.com/etc/api/videoBySearch/text/{q}/perpage/{n}", timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for v in root.findall('.//video'):
                    vid = v.findtext('uid', '')
                    results.append({
                        'id': vid, 'title': v.findtext('title', 'بدون عنوان')[:100],
                        'duration': int(v.findtext('duration', 0)), 'uploader': v.findtext('username', 'آپارات'),
                        'url': f"https://www.aparat.com/v/{vid}", 'source': 'aparat'
                    })
        except: pass
        return results
    
    def audio_url(self, url):
        if url in self.cache: return self.cache[url]
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestaudio/best'}) as y:
                info = y.extract_info(url, download=False)
                for f in info.get('formats', []):
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        self.cache[url] = f['url']; return f['url']
                self.cache[url] = info.get('url'); return info.get('url')
        except: return None
    
    def download_audio(self, url, filename):
        try:
            ydl_opts = {'quiet': True, 'format': 'bestaudio/best', 'outtmpl': filename, 'max_filesize': 50*1024*1024}
            with yt_dlp.YoutubeDL(ydl_opts) as y:
                y.download([url])
            return os.path.exists(filename)
        except: return False
    
    def randoms(self, n=10):
        qs = ["آهنگ جدید ایرانی", "موزیک شاد", "رپ فارسی", "پاپ ایرانی", "سنتی", "top music 2025", "turkish music", "arabic remix"]
        return self.search(random.choice(qs), n)

dl = DL()

# ========== PLAYER ==========
class Player:
    def __init__(self):
        self.q = {}; self.cur = {}; self.play = {}; self.loop = {}
    def add(self, c, t):
        if c not in self.q: self.q[c] = []
        self.q[c].append(t)
    def nxt(self, c):
        if self.loop.get(c) and self.cur.get(c): return self.cur[c]
        if c in self.q and self.q[c]: return self.q[c].pop(0)
        return None
    def clr(self, c): self.q[c] = []; self.cur[c] = None; self.play[c] = False

player = Player()

# ========== HELPERS ==========
def ok(chat_id): return chat_id in ALLOWED_CHATS or chat_id == OWNER_ID
def ft(s):
    if not s: return "∞"
    m, sec = divmod(int(s), 60); h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
def fn(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

# ========== KEYBOARDS ==========
def main_kb(c):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸", callback_data=f"ps_{c}"), InlineKeyboardButton("⏹", callback_data=f"st_{c}"), InlineKeyboardButton("⏭", callback_data=f"sk_{c}")],
        [InlineKeyboardButton("🔄", callback_data=f"lp_{c}"), InlineKeyboardButton("🎲", callback_data=f"sf_{c}"), InlineKeyboardButton("📋", callback_data=f"qu_{c}")],
        [InlineKeyboardButton("🔍 جستجو", callback_data="search"), InlineKeyboardButton("🎰 رندوم", callback_data="random")],
        [InlineKeyboardButton("🔥 محبوب", callback_data="trending"), InlineKeyboardButton("📻 رادیو", callback_data="radio"), InlineKeyboardButton("⭐ ذخیره", callback_data=f"fv_{c}")],
        [InlineKeyboardButton("📊 آمار", callback_data="stats"), InlineKeyboardButton("📜 تاریخچه", callback_data=f"hi_{c}")]
    ])

def search_kb(results, page=0, query=""):
    per = 5; s = page * per; e = s + per
    kb = InlineKeyboardMarkup(row_width=1)
    for t in results[s:e]:
        src = "🔴" if t.get('source') == 'youtube' else "🟢"
        kb.add(InlineKeyboardButton(f"{src} {t['title'][:40]} | {ft(t.get('duration',0))}", callback_data=f"sel_{t['id']}_{t.get('source','yt')}"))
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"sp_{page-1}_{query}"))
    if e < len(results): nav.append(InlineKeyboardButton("➡️", callback_data=f"sp_{page+1}_{query}"))
    if nav: kb.add(*nav)
    kb.add(InlineKeyboardButton("🔙 بستن", callback_data="close"))
    return kb

# ========== COMMANDS ==========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user.id, update.effective_user.first_name)
    await update.message.reply_text(
        "🎵 **ربات موزیک پیشرفته** 🎵\n\n"
        "✨ **یوتیوب + آپارات**\n\n"
        "📋 **دستورات:**\n"
        "• /play نام آهنگ - جستجو و پخش\n"
        "• /play لینک - پخش با لینک\n"
        "• /random - پخش تصادفی\n"
        "• /search نام - جستجو\n"
        "• /trending - آهنگ‌های محبوب\n"
        "• /radio - ذخیره در رادیو\n"
        "• /skip - آهنگ بعدی\n"
        "• /stop - توقف\n"
        "• /queue - صف پخش\n"
        "• /fav - ذخیره مورد علاقه\n"
        "• /stats - آمار ربات\n\n"
        "🎤 **برای پخش در Voice Chat:**\n"
        "• ربات رو ادمین کن\n"
        "• ویس چت استارت کن\n"
        "• /play آهنگ رو بفرست\n"
        "• ربات فایل صوتی رو میفرسته - پخش کن!"
    )

async def cmd_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    if not ok(c): return
    
    q = update.message.text.replace("/play", "").strip()
    if not q:
        return await update.message.reply_text("🎵 `/play نام آهنگ یا لینک`")
    
    s = await update.message.reply_text("⏳ **در حال جستجو...**")
    
    # URL
    if q.startswith("http"):
        t = {'id': 'url', 'title': 'لینک مستقیم', 'url': q, 'uploader': '', 'duration': 0, 'source': 'link'}
        audio = dl.audio_url(q)
        if audio:
            player.add(c, t)
            db.add_hist(c, t)
            if not player.play.get(c):
                player.cur[c] = t; player.play[c] = True
                await s.edit_text(f"🎵 **{t['title']}**\n🔗 [دانلود صدا]({audio})\n\n💡 فایل رو دانلود کن و تو ویس چت پخش کن!", reply_markup=main_kb(c))
            else:
                await s.edit_text(f"✅ به صف اضافه شد!", reply_markup=main_kb(c))
        else:
            await s.edit_text("❌ خطا!")
        return
    
    # Search
    results = dl.search(q, 3)
    if not results:
        return await s.edit_text("❌ یافت نشد!")
    
    t = results[0]
    audio = dl.audio_url(t['url'])
    if not audio:
        return await s.edit_text("❌ خطا!")
    
    player.add(c, t)
    db.add_hist(c, t)
    src = "یوتیوب" if t.get('source') == 'youtube' else "آپارات"
    
    if not player.play.get(c):
        player.cur[c] = t; player.play[c] = True
    
    # Download and send audio file
    await s.edit_text("📥 **در حال دانلود...**")
    filename = f"/tmp/music_{int(time.time())}.mp3"
    
    if dl.download_audio(t['url'], filename):
        await s.edit_text("📤 **در حال ارسال فایل...**")
        try:
            with open(filename, 'rb') as f:
                await update.message.reply_audio(
                    audio=f,
                    title=t['title'][:64],
                    performer=t['uploader'],
                    duration=t.get('duration', 0),
                    caption=f"🎵 **{t['title']}**\n👤 {t['uploader']}\n📀 {src}\n⏱ {ft(t.get('duration',0))}",
                    reply_markup=main_kb(c)
                )
            await s.delete()
        except Exception as e:
            await s.edit_text(f"🎵 **{t['title']}**\n👤 {t['uploader']}\n📀 {src}\n⏱ {ft(t.get('duration',0))}\n\n🔗 [دانلود صدا]({audio})", reply_markup=main_kb(c))
        os.remove(filename)
    else:
        await s.edit_text(f"🎵 **{t['title']}**\n👤 {t['uploader']}\n📀 {src}\n⏱ {ft(t.get('duration',0))}\n\n🔗 [دانلود صدا]({audio})\n\n💡 فایل رو دانلود کن و تو ویس چت پخش کن!", reply_markup=main_kb(c))

async def cmd_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    if not ok(c): return
    s = await update.message.reply_text("🎰 **دریافت تصادفی...**")
    
    radio = db.get_radio()
    if radio:
        t = random.choice(radio)
        audio = dl.audio_url(t['url'])
        if audio:
            player.add(c, t)
            filename = f"/tmp/music_{int(time.time())}.mp3"
            if dl.download_audio(t['url'], filename):
                with open(filename, 'rb') as f:
                    await update.message.reply_audio(audio=f, title=t['title'][:64], performer=t['uploader'], caption=f"📻 رادیو: {t['title']}", reply_markup=main_kb(c))
                os.remove(filename); await s.delete()
            else:
                await s.edit_text(f"📻 **رادیو:** {t['title'][:80]}\n🔗 [دانلود]({audio})", reply_markup=main_kb(c))
            return
    
    r = dl.randoms(10)
    if r:
        t = random.choice(r)
        audio = dl.audio_url(t['url'])
        if audio:
            player.add(c, t)
            await s.edit_text(f"🎰 **تصادفی:** {t['title'][:80]}\n👤 {t['uploader']}\n🔗 [دانلود]({audio})", reply_markup=main_kb(c))
            return
    await s.edit_text("❌ خطا!")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.replace("/search", "").strip()
    if not q: return
    r = dl.search(q, 15)
    if not r: return await update.message.reply_text("❌ یافت نشد!")
    await update.message.reply_text(f"🔍 **نتایج: {q}**\n🔴 یوتیوب | 🟢 آپارات\n{len(r)} آهنگ پیدا شد.", reply_markup=search_kb(r, 0, q))

async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = dl.randoms(15)
    if r:
        kb = InlineKeyboardMarkup(row_width=1)
        for t in r[:10]:
            src = "🔴" if t.get('source') == 'youtube' else "🟢"
            kb.add(InlineKeyboardButton(f"{src} {t['title'][:40]}", callback_data=f"sel_{t['id']}_{t.get('source','yt')}"))
        kb.add(InlineKeyboardButton("🔙", callback_data="close"))
        await update.message.reply_text("🔥 **آهنگ‌های محبوب**", reply_markup=kb)

async def cmd_radio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = player.cur.get(update.effective_chat.id)
    if cur:
        if db.add_radio(cur): await update.message.reply_text(f"📻 **اضافه شد:** {cur['title'][:60]}")
        else: await update.message.reply_text("⚠️ قبلاً در رادیو هست!")
    else: await update.message.reply_text("❌ آهنگی پخش نیست!")

async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    if not ok(c): return
    t = player.nxt(c)
    if t:
        audio = dl.audio_url(t['url'])
        if audio:
            await update.message.reply_text(f"⏭ **آهنگ بعدی:**\n{t['title'][:80]}\n🔗 [دانلود]({audio})", reply_markup=main_kb(c))
    else:
        await update.message.reply_text("📭 صف خالی!")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    if not ok(c): return
    player.clr(c)
    await update.message.reply_text("⏹ **پایان پخش!**")

async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    q = player.q.get(c, [])
    cur = player.cur.get(c)
    txt = "📋 **صف پخش**\n\n"
    if cur: txt += f"🎵 **در حال پخش:** {cur['title'][:60]}\n⏱ {ft(cur.get('duration',0))}\n\n"
    if q:
        txt += f"📊 **{len(q)} آهنگ در صف:**\n"
        for i, t in enumerate(q[:15], 1): txt += f"{i}. {t['title'][:50]} | {ft(t.get('duration',0))}\n"
        if len(q) > 15: txt += f"\n... و {len(q)-15} آهنگ دیگر"
    else: txt += "📭 خالی!"
    await update.message.reply_text(txt)

async def cmd_fav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = player.cur.get(update.effective_chat.id)
    if cur:
        if db.add_fav(update.effective_user.id, cur):
            await update.message.reply_text("⭐ **ذخیره شد!**")
        else: await update.message.reply_text("⚠️ قبلاً ذخیره شده!")
    else: await update.message.reply_text("❌ آهنگی پخش نیست!")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = db.get_stats()
    c = update.effective_chat.id
    txt = f"📊 **آمار ربات**\n\n👥 کاربران: {s['users']}\n📻 رادیو: {s['radio']}\n⭐ علاقه‌مندی: {s['favs']}\n📜 تاریخچه: {s['history']}\n\n📋 صف فعلی: {len(player.q.get(c, []))} آهنگ"
    await update.message.reply_text(txt)

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = update.effective_chat.id
    h = db.d['history'].get(str(c), [])[-15:]
    if not h: return await update.message.reply_text("📜 تاریخچه خالی!")
    txt = "📜 **آخرین آهنگ‌ها**\n\n"
    for i, entry in enumerate(reversed(h), 1):
        s = entry['song']
        txt += f"{i}. {s['title'][:50]} | {entry['time']}\n"
    await update.message.reply_text(txt)

# ========== CALLBACKS ==========
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb = update.callback_query
    d = cb.data; c = cb.message.chat.id; uid = cb.from_user.id
    
    if d == "close": await cb.message.delete()
    elif d == "search": await cb.answer("با /search جستجو کن", show_alert=True)
    elif d == "random": await cb.answer(); await cmd_random(update, context)
    elif d == "trending": await cb.answer(); await cmd_trending(update, context)
    elif d == "radio": await cb.answer(); await cmd_radio(update, context)
    elif d == "stats":
        s = db.get_stats()
        await cb.answer(f"👥 {s['users']} | 📻 {s['radio']} | ⭐ {s['favs']}", show_alert=True)
    elif d.startswith("sel_"):
        _, vid, src = d.split("_", 2)
        url = f"https://youtube.com/watch?v={vid}" if src == "yt" else f"https://www.aparat.com/v/{vid}"
        t = {'id': vid, 'title': '...', 'url': url, 'source': src, 'uploader': '', 'duration': 0}
        audio = dl.audio_url(url)
        if audio:
            player.add(c, t)
            s = await cb.message.reply_text("📥 دانلود...")
            filename = f"/tmp/music_{int(time.time())}.mp3"
            if dl.download_audio(url, filename):
                with open(filename, 'rb') as f:
                    await cb.message.reply_audio(audio=f, title=t['title'][:64], caption=f"✅ از جستجو", reply_markup=main_kb(c))
                os.remove(filename); await s.delete()
            else:
                await s.edit_text(f"🎵 **{t['title']}**\n🔗 [دانلود]({audio})", reply_markup=main_kb(c))
        else: await cb.answer("❌ خطا!")
    elif d.startswith("sp_"):
        _, page, query = d.split("_", 2)
        r = dl.search(query, 15)
        await cb.message.edit_reply_markup(reply_markup=search_kb(r, int(page), query))
    elif d.startswith("ps_"): await cb.answer("⏸")
    elif d.startswith("st_"):
        player.clr(c); await cb.message.delete()
    elif d.startswith("sk_"):
        await cb.answer("⏭")
        t = player.nxt(c)
        if t:
            audio = dl.audio_url(t['url'])
            if audio:
                await cb.message.reply_text(f"⏭ {t['title'][:80]}\n🔗 [دانلود]({audio})", reply_markup=main_kb(c))
    elif d.startswith("lp_"):
        player.loop[c] = not player.loop.get(c)
        await cb.answer(f"🔄 {'ON' if player.loop[c] else 'OFF'}")
    elif d.startswith("sf_"):
        if player.q.get(c): random.shuffle(player.q[c])
        await cb.answer("🎲 صف بهم ریخت!")
    elif d.startswith("qu_"):
        q = player.q.get(c, []); cur = player.cur.get(c)
        txt = "📋\n"
        if cur: txt += f"🎵 {cur['title'][:40]}\n"
        for i, t in enumerate(q[:10], 1): txt += f"{i}. {t['title'][:35]}\n"
        await cb.answer(txt[:200] or "خالی", show_alert=True)
    elif d.startswith("fv_"):
        cur = player.cur.get(c)
        if cur and db.add_fav(uid, cur): await cb.answer("⭐ ذخیره شد!")
    elif d.startswith("hi_"):
        h = db.d['history'].get(str(c), [])[-5:]
        txt = "\n".join([f"{e['song']['title'][:40]}" for e in reversed(h)])
        await cb.answer(txt[:200] or "خالی", show_alert=True)

# ========== MAIN ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("play", cmd_play))
    app.add_handler(CommandHandler("random", cmd_random))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("trending", cmd_trending))
    app.add_handler(CommandHandler("radio", cmd_radio))
    app.add_handler(CommandHandler("skip", cmd_skip))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(CommandHandler("fav", cmd_fav))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CallbackQueryHandler(callback))
    
    print("🎵 Advanced Music Bot Started | YouTube + Aparat | File Download")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
