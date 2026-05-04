import telebot
from telebot import types
import schedule, time, threading, random, os, sqlite3, re, json
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Thread

# ==================== CONFIG @KaroPlusbot V12 ====================
TOKEN = os.environ.get('BOT_TOKEN', '8720770282:AAEDA4gTXNNoc4EnExzZiEpjYZvYS3KJSoo')
BOT_USERNAME = '@KaroPlusbot'
CHANNEL_ID = -1003929479271
CHANNEL_LINK = 'https://t.me/karoplusjobs'
WEBAPP_URL = 'https://karo-plus-iraq.netlify.app'
LOGO_URL = 'https://i.imgur.com/8tG8ZqN.png'
ADMIN_IDS = [8720770282]

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
app = Flask(__name__)

# ==================== DATABASE V12 ====================
def init_db():
    conn = sqlite3.connect('karoplus.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
                  lang TEXT DEFAULT 'ku', join_date TEXT, last_active TEXT,
                  free_days INTEGER DEFAULT 7, refs INTEGER DEFAULT 0, ref_by INTEGER,
                  apps_sent INTEGER DEFAULT 0, profile_views INTEGER DEFAULT 0,
                  is_premium INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
                  phone TEXT, email TEXT, whatsapp TEXT, telegram TEXT,
                  bio TEXT, skills TEXT, location TEXT, salary_exp TEXT,
                  cv_url TEXT, video_cv_url TEXT, profile_pic TEXT,
                  is_company INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0,
                  followers INTEGER DEFAULT 0, following INTEGER DEFAULT 0,
                  rating REAL DEFAULT 0, reviews INTEGER DEFAULT 0,
                  total_earnings INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS companies
                 (company_id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER,
                  name TEXT, email TEXT, phone TEXT, whatsapp TEXT,
                  website TEXT, location TEXT, description TEXT, industry TEXT,
                  logo_url TEXT, verified INTEGER DEFAULT 0,
                  created_date TEXT, total_jobs INTEGER DEFAULT 0,
                  followers INTEGER DEFAULT 0, rating REAL DEFAULT 0,
                  subscription TEXT DEFAULT 'free', sub_expiry TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS jobs
                 (job_id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
                  posted_by INTEGER, title TEXT, company_name TEXT,
                  location TEXT, salary TEXT, salary_min INTEGER, salary_max INTEGER,
                  type TEXT, category TEXT, experience TEXT,
                  description TEXT, requirements TEXT, benefits TEXT,
                  email TEXT, phone TEXT, whatsapp TEXT, telegram TEXT,
                  posted_date TEXT, expiry_date TEXT,
                  is_vip INTEGER DEFAULT 0, is_featured INTEGER DEFAULT 0,
                  is_active INTEGER DEFAULT 1, is_approved INTEGER DEFAULT 0,
                  ai_score INTEGER DEFAULT 0, rejection_reason TEXT,
                  views INTEGER DEFAULT 0, apps INTEGER DEFAULT 0,
                  likes INTEGER DEFAULT 0, shares INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (app_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER,
                  user_id INTEGER, company_id INTEGER, apply_date TEXT,
                  status TEXT DEFAULT 'pending', cv_file TEXT, video_cv TEXT,
                  cover_letter TEXT, user_phone TEXT, user_email TEXT, user_whatsapp TEXT,
                  ai_match_score INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS follows
                 (follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  follower_id INTEGER, following_id INTEGER,
                  follow_date TEXT, is_company INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER, receiver_id INTEGER,
                  message TEXT, media_type TEXT, media_url TEXT,
                  sent_date TEXT, is_read INTEGER DEFAULT 0,
                  is_deleted INTEGER DEFAULT 0, reply_to INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (ref_id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER,
                  referred_id INTEGER, date TEXT, rewarded INTEGER DEFAULT 0)''')

    conn.commit()
    conn.close()

init_db()

# ==================== AI MODERATION V12 ====================
BAD_WORDS = ['sex', 'porn', 'drug', 'سێکس', 'مادە', 'قومار', 'cheat', 'hack', 'scam']
SCAM_PATTERNS = [r'پارە بنێرە', r'کلیک بکە.*بە دەوڵەمەند', r'١٠٠\$ لە ڕۆژێک', r'bitcoin', r'crypto']

def ai_moderate_job_v12(data):
    text = f"{data['title']} {data['desc']} {data['company']}".lower()
    score = 100
    issues = []

    for word in BAD_WORDS:
        if word in text:
            return False, 0, "ناوەڕۆکی نەشیاو", f"وشەی '{word}' لاببە"

    for pattern in SCAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            score -= 60
            issues.append("گومانی فێڵ")

    if len(data['desc']) < 50:
        score -= 25
        issues.append("وەسف کورتە - کەمترین 50 پیت")

    if not data.get('whatsapp') and not data.get('email'):
        score -= 20
        issues.append("واتساپ یان ئیمەیل زیاد بکە")

    if len(data['company']) < 3:
        score -= 15
        issues.append("ناوی کۆمپانیا ڕوونتر")

    approved = score >= 60
    reason = "پەسەندکرا" if approved else " | ".join(issues)
    advice = "کێشەکان چارە بکە" if not approved else ""
    return approved, score, reason, advice

# ==================== TEXTS ====================
TEXTS = {
    'ku': {
        'welcome': '<b>👑 بەخێربێیت بۆ KARO PLUS V12</b>\n\n<i>Your Career, Elevated</i>\n\n🎁 <b>7 ڕۆژ VIP</b> | 👥 <b>2 هاوڕێ = VIP هەتا هەتایە</b>\n\n💼 <b>کۆمپانیا؟</b> کار پۆست بکە\n👤 <b>کارخواز؟</b> هەزاران هەل\n💬 <b>چات + فۆڵۆ</b> هەیە\n\nزمان هەڵبژێرە:',
        'menu': '<b>👑 KARO PLUS V12</b>\n\n💎 <b>{status}</b> | ⏳ <b>{days}</b> ڕۆژ\n👥 فۆڵۆوەر: <b>{followers}</b> | فۆڵۆینگ: <b>{following}</b>\n📤 داواکاری: <b>{apps}</b> | 👁️ بینین: <b>{views}</b>\n🏆 ڕیزبەندی: <b>#{rank}</b>',
        'post_approved': '🎉 <b>پیرۆزە! کارەکەت پەسەند کرا</b>\n\n✅ <b>AI سکۆر:</b> {score}/100\n📊 <b>ID:</b> #{job_id}',
        'post_rejected': '❌ <b>کارەکەت ڕەتکرایەوە</b>\n\n<b>هۆکار:</b> {reason}\n<b>AI سکۆر:</b> {score}/100\n\n<b>چارەسەر:</b> {advice}',
    }
}

# ==================== DB FUNCTIONS ====================
def get_user(user_id):
    conn = sqlite3.connect('karoplus.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, join_date, last_active) VALUES (?,?,?)",
                 (user_id, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
    else:
        c.execute("UPDATE users SET last_active=? WHERE user_id=?",
                 (datetime.now().strftime("%Y-%m-%d %H:%M"), user_id))
        conn.commit()

    c.execute("SELECT COUNT(*) FROM follows WHERE following_id=?", (user_id,))
    followers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,))
    following = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE apps_sent >?", (row[10],))
    rank = c.fetchone()[0] + 1
    conn.close()

    return {
        'user_id': row[0], 'username': row[1] or '', 'first_name': row[2] or '',
        'lang': row[4], 'days': row[7], 'refs': row[8], 'apps': row[10],
        'views': row[11], 'is_premium': row[12],
        'status': 'VIP 👑' if row[7] > 0 or row[12] else 'Free',
        'rank': rank, 'followers': followers, 'following': following
    }

def update_user(user_id, **kwargs):
    conn = sqlite3.connect('karoplus.db', check_same_thread=False)
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE users SET {key}=? WHERE user_id=?", (val, user_id))
    conn.commit()
    conn.close()

def create_job_v12(data):
    conn = sqlite3.connect('karoplus.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''INSERT INTO jobs
                 (posted_by, title, company_name, location, salary, type, category,
                  description, requirements, email, phone, whatsapp,
                  posted_date, is_approved, ai_score, rejection_reason)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (data['user_id'], data['title'], data['company'], data['location'],
               data['salary'], data.get('type','fulltime'), data.get('category','Other'),
               data['desc'], data['req'], data['email'], data['phone'], data['whatsapp'],
               datetime.now().strftime("%Y-%m-%d"), data['approved'], data['ai_score'],
               data.get('rejection_reason', '')))
    job_id = c.lastrowid
    conn.commit()
    conn.close()
    return job_id

# ==================== HANDLERS ====================
user_states = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if len(message.text.split()) > 1 and message.text.split()[1].startswith('ref'):
        try:
            ref_id = int(message.text.split()[1][3:])
            if ref_id!= user_id:
                conn = sqlite3.connect('karoplus.db', check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT ref_by FROM users WHERE user_id=?", (user_id,))
                if not c.fetchone()[0]:
                    c.execute("UPDATE users SET ref_by=? WHERE user_id=?", (ref_id, user_id))
                    c.execute("UPDATE users SET refs = refs + 1 WHERE user_id=?", (ref_id,))
                    c.execute("SELECT refs FROM users WHERE user_id=?", (ref_id,))
                    if c.fetchone()[0] >= 2:
                        c.execute("UPDATE users SET is_premium=1, free_days=9999 WHERE user_id=?", (ref_id,))
                        bot.send_message(ref_id, "🎉 <b>پیرۆزە!</b> بوویت بە <b>VIP هەتا هەتایە</b>! 👑")
                    conn.commit()
                conn.close()
        except: pass

    user = get_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("کوردی 🦅", callback_data="lang_ku"),
        types.InlineKeyboardButton("العربية 👑", callback_data="lang_ar"),
        types.InlineKeyboardButton("English 💎", callback_data="lang_en")
    )
    bot.send_photo(message.chat.id, LOGO_URL, caption=TEXTS['ku']['welcome'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    lang = call.data.split('_')[1]
    update_user(call.from_user.id, lang=lang)
    user = get_user(call.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    web_app = types.WebAppInfo(WEBAPP_URL)
    markup.add(types.InlineKeyboardButton("🚀 کردنەوەی ئەپی شاهانە", web_app=web_app))
    markup.add(
        types.InlineKeyboardButton("📝 پۆستکردنی کار", callback_data="post_job"),
        types.InlineKeyboardButton("👤 پرۆفایلی من", callback_data="profile")
    )
    bot.edit_message_caption(TEXTS['ku']['menu'].format(**user), call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'post_job')
def post_job_start(call):
    user_states[call.from_user.id] = {'step': 'title', 'data': {'user_id': call.from_user.id}}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📝 <b>ناوی کار:</b>")

@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def handle_post_job(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    steps = ['title', 'company', 'location', 'salary', 'desc', 'req', 'whatsapp', 'email', 'phone']
    prompts = {
        'company': '🏢 <b>ناوی کۆمپانیا:</b>',
        'location': '📍 <b>شوێن:</b>',
        'salary': '💰 <b>مووچە:</b>',
        'desc': '📄 <b>وەسف:</b> (کەمترین 50 پیت)',
        'req': '✅ <b>مەرجەکان:</b>',
        'whatsapp': '📱 <b>واتساپ:</b>',
        'email': '📧 <b>ئیمەیل:</b>',
        'phone': '☎️ <b>تەلەفۆن:</b>'
    }

    current_idx = steps.index(state['step'])
    state['data'][state['step']] = message.text

    if current_idx < len(steps) - 1:
        state['step'] = steps[current_idx + 1]
        bot.send_message(message.chat.id, prompts[state['step']])
    else:
        bot.send_message(message.chat.id, "🤖 AI پشکنین دەکات...")
        approved, score, reason, advice = ai_moderate_job_v12(state['data'])
        state['data']['approved'] = 1 if approved else 0
        state['data']['ai_score'] = score
        state['data']['rejection_reason'] = reason
        job_id = create_job_v12(state['data'])
        del user_states[user_id]

        if approved:
            bot.send_message(message.chat.id, TEXTS['ku']['post_approved'].format(job_id=job_id, score=score))
            post_job_to_channel(state['data'], job_id)
        else:
            bot.send_message(message.chat.id, TEXTS['ku']['post_rejected'].format(reason=reason, score=score, advice=advice))

def post_job_to_channel(data, job_id):
    markup = types.InlineKeyboardMarkup()
    web_app = types.WebAppInfo(WEBAPP_URL)
    markup.add(types.InlineKeyboardButton("💎 داواکاری پێشکەش بکە", web_app=web_app))
    text = f"👑 <b>هەلی کاری نوێ</b>\n\n🏢 {data['company']}\n💼 {data['title']}\n📍 {data['location']}\n💰 {data['salary']}\n\n📱 {data['whatsapp']}\n📧 {data['email']}\n\n#KaroPlus #Job{job_id}"
    try:
        bot.send_photo(CHANNEL_ID, LOGO_URL, caption=text, reply_markup=markup)
    except Exception as e:
        print(f"Post Error: {e}")

# ==================== SCHEDULER ====================
AI_POSTS = [
    "🔥 <b>500+ هەلی کار</b> لە KARO PLUS!\n\n👑 ببە VIP بە 2 هاوڕێ\n💼 کاری خەونەکانت بدۆزەرەوە",
    "💎 <b>AI CV Builder</b> بە خۆڕایی!\n\n🤖 CV یەکی پرۆفیشناڵ دروست بکە\n📈 ATS Score 90+",
]

def ai_daily_post():
    post = random.choice(AI_POSTS)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 دەستپێبکە", url=f"https://t.me/{BOT_USERNAME[1:]}"))
    try:
        bot.send_photo(CHANNEL_ID, LOGO_URL, caption=post, reply_markup=markup)
    except:
        bot.send_message(CHANNEL_ID, post, reply_markup=markup)

schedule.every().day.at("10:00").do(ai_daily_post)
schedule.every().day.at("21:00").do(ai_daily_post)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

Thread(target=run_schedule, daemon=True).start()

# ==================== FLASK API ====================
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = sqlite3.connect('karoplus.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE is_active=1 AND is_approved=1 ORDER BY posted_date DESC LIMIT 100")
    jobs = c.fetchall()
    conn.close()
    return jsonify([{
        'id': j[0], 'title': j[4], 'company': j[5], 'location': j[6],
        'salary': j[7], 'desc': j[12], 'whatsapp': j[16], 'email': j[15],
        'views': j[26], 'posted_by': j[2]
    } for j in jobs])

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_api(user_id):
    return jsonify(get_user(user_id))

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

Thread(target=run_flask, daemon=True).start()

# ==================== MAIN ====================
print(f"✅ @KaroPlusbot V12 Running 👑")
if __name__ == "__main__":
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(15)
