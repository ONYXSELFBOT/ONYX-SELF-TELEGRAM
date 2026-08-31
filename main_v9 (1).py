#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╭──────────────────────────────────────────────────╮
│         💎 ONYX SELF V7 PRO'S                      │
│   سلف‌بات حرفه‌ای تلگرام — فایل یکپارچه         │
│   کتابخانه: Telethon + SQLite (WAL)              │
│   پلتفرم: Termux / Linux                         │
│   سازنده: @Reyvoxe                               │
╰──────────────────────────────────────────────────╯

راه‌اندازی:
    python main.py

تنظیم در config.ini یا متغیر محیطی:
    ONYX_API_ID     = your_api_id
    ONYX_API_HASH   = your_api_hash
    ONYX_SESSION    = onyx_v7  (اختیاری)
"""

# ══════════════════════════════════════════════════════
#  ═══  CORE  ═══
# ══════════════════════════════════════════════════════

import asyncio
import base64
import configparser
import datetime
import importlib
import importlib.util
import json
import logging
import math
import os
import random
import re
import shutil
import sqlite3
import string
import sys
import threading
import time as _time
import time
import traceback
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest
from telethon.tl.types import UserStatusOnline, UserStatusOffline, UserStatusRecently

# ══════════════════════════════════════════════
#  واترمارک و ثوابت
# ══════════════════════════════════════════════
WATERMARK = "💎 ONYX SELF V7 PRO'S | سازنده: @Reyvoxe"
VERSION   = "7.0.0"
PROJECT   = "ONYX SELF V7 PRO'S"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR  = os.path.join(BASE_DIR, "logs")
DL_DIR   = os.path.join(BASE_DIR, "downloads")
BK_DIR   = os.path.join(BASE_DIR, "backups")
VLT_DIR  = os.path.join(BASE_DIR, "vault")
PLG_DIR  = os.path.join(BASE_DIR, "plugins")
DB_PATH  = os.path.join(BASE_DIR, "onyx_v7.db")

for _d in (LOG_DIR, DL_DIR, BK_DIR, VLT_DIR, PLG_DIR):
    os.makedirs(_d, exist_ok=True)

# ══════════════════════════════════════════════
#  سیستم لاگ حرفه‌ای
# ══════════════════════════════════════════════
def setup_logger(name: str = "onyx") -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    log.addHandler(ch)
    # Rotating file handler
    try:
        fh = RotatingFileHandler(
            os.path.join(LOG_DIR, "onyx.log"),
            maxBytes=2 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
        # Error-only file
        eh = RotatingFileHandler(
            os.path.join(LOG_DIR, "errors.log"),
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(fmt)
        log.addHandler(eh)
    except Exception:
        pass
    return log

logger = setup_logger("onyx")

# ══════════════════════════════════════════════
#  دیتابیس SQLite
# ══════════════════════════════════════════════
_db_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_conn)
        _v7_init_schema(_conn)
    return _conn

def _init_schema(conn: sqlite3.Connection) -> None:
    """ساخت همه جداول اگر وجود نداشته باشند"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS contacts (
            uid       INTEGER PRIMARY KEY,
            name      TEXT    DEFAULT '',
            username  TEXT    DEFAULT '',
            bio       TEXT    DEFAULT '',
            note      TEXT    DEFAULT '',
            score     INTEGER DEFAULT 0,
            status    TEXT    DEFAULT 'normal',
            color     TEXT    DEFAULT '',
            phone     TEXT    DEFAULT '',
            birthday  TEXT    DEFAULT '',
            address   TEXT    DEFAULT '',
            job       TEXT    DEFAULT '',
            tags      TEXT    DEFAULT '[]',
            first_seen TEXT   DEFAULT '',
            last_msg  TEXT    DEFAULT '',
            msg_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
        CREATE TABLE IF NOT EXISTS contact_tags (
            id  INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            tag TEXT    NOT NULL,
            UNIQUE(uid, tag)
        );
        CREATE TABLE IF NOT EXISTS contact_history (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            uid     INTEGER NOT NULL,
            field   TEXT    NOT NULL,
            old_val TEXT    DEFAULT '',
            new_val TEXT    DEFAULT '',
            ts      TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ch_uid ON contact_history(uid);
        CREATE TABLE IF NOT EXISTS contact_notes (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            uid   INTEGER NOT NULL,
            note  TEXT    NOT NULL,
            ts    TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            uid     INTEGER NOT NULL,
            text    TEXT    NOT NULL,
            ts      TEXT    NOT NULL,
            done    INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_rem_uid ON reminders(uid);
        CREATE TABLE IF NOT EXISTS pins (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            msg_id  INTEGER NOT NULL,
            text    TEXT    DEFAULT '',
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS macros (
            name    TEXT PRIMARY KEY,
            value   TEXT NOT NULL,
            ts      TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS templates (
            name    TEXT PRIMARY KEY,
            value   TEXT NOT NULL,
            ts      TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vault (
            key_name TEXT PRIMARY KEY,
            value    TEXT NOT NULL,
            ts       TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_files (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT    DEFAULT 'عمومی',
            filename TEXT    NOT NULL,
            filepath TEXT    NOT NULL,
            size     INTEGER DEFAULT 0,
            ts       TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_messages (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            msg_id  INTEGER NOT NULL,
            text    TEXT    DEFAULT '',
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS achievements (
            id      TEXT    PRIMARY KEY,
            title   TEXT    NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cmd_history (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd   TEXT    NOT NULL,
            ts    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cmdh_ts ON cmd_history(ts);
        CREATE TABLE IF NOT EXISTS onyx_profile (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '0'
        );
        CREATE TABLE IF NOT EXISTS aliases (
            alias  TEXT PRIMARY KEY,
            target TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS todos (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            text  TEXT    NOT NULL,
            done  INTEGER DEFAULT 0,
            ts    TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorites (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            type    TEXT    DEFAULT 'message',
            text    TEXT    DEFAULT '',
            chat_id INTEGER NOT NULL,
            msg_id  INTEGER NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bookmarks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            text    TEXT    DEFAULT '',
            chat_id INTEGER NOT NULL,
            msg_id  INTEGER NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS calendar (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            type    TEXT    NOT NULL,
            date    TEXT    NOT NULL,
            title   TEXT    NOT NULL,
            added   TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cal_date ON calendar(date);
        CREATE TABLE IF NOT EXISTS expenses (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT    NOT NULL,
            amount  INTEGER NOT NULL,
            cat     TEXT    DEFAULT 'عمومی',
            date    TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_exp_date ON expenses(date);
        CREATE TABLE IF NOT EXISTS full_locks (
            lock_type TEXT PRIMARY KEY,
            active    INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS word_lists (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            list  TEXT    NOT NULL,
            word  TEXT    NOT NULL,
            UNIQUE(list, word)
        );
        CREATE TABLE IF NOT EXISTS backups (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT    NOT NULL,
            size     INTEGER DEFAULT 0,
            ts       TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plugins (
            name    TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            meta    TEXT    DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS workflows (
            name     TEXT PRIMARY KEY,
            steps    TEXT    NOT NULL,
            run_cnt  INTEGER DEFAULT 0,
            last_run TEXT    DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS online_log (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            uid     INTEGER NOT NULL,
            status  TEXT    NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ol_uid ON online_log(uid);
        CREATE TABLE IF NOT EXISTS online_watch (
            uid     INTEGER PRIMARY KEY,
            active  INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS daily_stats (
            date      TEXT    PRIMARY KEY,
            msgs_sent INTEGER DEFAULT 0,
            msgs_recv INTEGER DEFAULT 0,
            cmds      INTEGER DEFAULT 0,
            errors    INTEGER DEFAULT 0,
            dls       INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS dl_history (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            url     TEXT    NOT NULL,
            title   TEXT    DEFAULT '',
            size    INTEGER DEFAULT 0,
            status  TEXT    DEFAULT 'ok',
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ad_groups (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            gid   TEXT    NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS auto_replies (
            keyword TEXT PRIMARY KEY,
            reply   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rules (
            keyword TEXT PRIMARY KEY,
            reply   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chat_memory (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id  INTEGER NOT NULL,
            uid      INTEGER NOT NULL,
            sender   TEXT    DEFAULT '',
            text     TEXT    DEFAULT '',
            outgoing INTEGER DEFAULT 0,
            ts       TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cm_chat ON chat_memory(chat_id);
        CREATE INDEX IF NOT EXISTS idx_cm_ts ON chat_memory(ts);
        CREATE TABLE IF NOT EXISTS spam_log (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            count   INTEGER DEFAULT 0,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notebooks (
            uid     INTEGER PRIMARY KEY,
            phone   TEXT    DEFAULT '',
            extra   TEXT    DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS smart_queue (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            target  TEXT    NOT NULL,
            text    TEXT    NOT NULL,
            send_at TEXT    NOT NULL,
            done    INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS goals (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    NOT NULL,
            target    INTEGER NOT NULL,
            current   INTEGER DEFAULT 0,
            unit      TEXT    DEFAULT '',
            deadline  TEXT    DEFAULT '',
            done      INTEGER DEFAULT 0,
            ts        TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS time_capsules (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            open_date TEXT    NOT NULL,
            opened    INTEGER DEFAULT 0,
            ts        TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS habits (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    NOT NULL,
            streak    INTEGER DEFAULT 0,
            last_done TEXT    DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS chat_states (
            chat_id INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            value   TEXT    DEFAULT '',
            PRIMARY KEY(chat_id, key)
        );
        CREATE TABLE IF NOT EXISTS preferences (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS intent_rules (
            keywords TEXT PRIMARY KEY,
            intent   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comment_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS raid_alerts (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            type  TEXT NOT NULL,
            chat  TEXT NOT NULL,
            ts    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS snapshots (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            uid     INTEGER NOT NULL,
            data    TEXT    NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clone_data (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            text    TEXT    NOT NULL,
            chat_id INTEGER NOT NULL,
            ts      TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS file_vault (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT    DEFAULT 'عمومی',
            filename TEXT    NOT NULL,
            filepath TEXT    NOT NULL,
            size     INTEGER DEFAULT 0,
            ts       TEXT    NOT NULL
        );

    -- ══ Shadow Profile ══
    CREATE TABLE IF NOT EXISTS shadow_profiles (
        uid      INTEGER PRIMARY KEY,
        data     TEXT    DEFAULT '{}',
        updated  TEXT    DEFAULT ''
    );

    -- ══ Memory Book ══
    CREATE TABLE IF NOT EXISTS memory_book (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        memory  TEXT    NOT NULL,
        context TEXT    DEFAULT '',
        ts      TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_mb_uid ON memory_book(uid);

    -- ══ On This Day ══
    CREATE TABLE IF NOT EXISTS on_this_day (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        date_md TEXT    NOT NULL,
        text    TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );

    -- ══ Smart Reminders ══
    CREATE TABLE IF NOT EXISTS smart_reminders (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        text    TEXT    NOT NULL,
        target  TEXT    DEFAULT 'me',
        fire_at TEXT    NOT NULL,
        done    INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );

    -- ══ Favorite Contacts ══
    CREATE TABLE IF NOT EXISTS fav_contacts (
        uid     INTEGER PRIMARY KEY,
        note    TEXT    DEFAULT '',
        added   TEXT    NOT NULL
    );

    -- ══ Ignore List ══
    CREATE TABLE IF NOT EXISTS ignore_list (
        uid     INTEGER PRIMARY KEY,
        reason  TEXT    DEFAULT '',
        added   TEXT    NOT NULL
    );

    -- ══ Auto Nickname ══
    CREATE TABLE IF NOT EXISTS auto_nicknames (
        uid      INTEGER PRIMARY KEY,
        nickname TEXT    NOT NULL
    );

    -- ══ Waiting Tracker ══
    CREATE TABLE IF NOT EXISTS waiting_tracker (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        context TEXT    NOT NULL,
        started TEXT    NOT NULL,
        done    INTEGER DEFAULT 0
    );

    -- ══ Profile Timeline ══
    CREATE TABLE IF NOT EXISTS profile_timeline (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        field   TEXT    NOT NULL,
        value   TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );

    -- ══ Quick Replies ══
    CREATE TABLE IF NOT EXISTS quick_replies (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        shortcut TEXT   NOT NULL UNIQUE,
        text    TEXT    NOT NULL,
        used    INTEGER DEFAULT 0
    );

    -- ══ Draft Manager ══
    CREATE TABLE IF NOT EXISTS drafts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT    NOT NULL,
        content TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );

    -- ══ Password Manager ══
    CREATE TABLE IF NOT EXISTS passwords (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        site     TEXT    NOT NULL,
        username TEXT    DEFAULT '',
        password TEXT    NOT NULL,
        note     TEXT    DEFAULT '',
        ts       TEXT    NOT NULL
    );

    -- ══ Command Scheduler ══
    CREATE TABLE IF NOT EXISTS cmd_scheduler (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT    NOT NULL,
        cmd      TEXT    NOT NULL,
        run_at   TEXT    NOT NULL,
        repeat   TEXT    DEFAULT 'once',
        last_run TEXT    DEFAULT '',
        active   INTEGER DEFAULT 1
    );

    -- ══ Mention Alerts ══
    CREATE TABLE IF NOT EXISTS mention_alerts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT    NOT NULL,
        chat_id INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );

    -- ══ Collector System ══
    CREATE TABLE IF NOT EXISTS collections (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT    NOT NULL,
        title    TEXT    NOT NULL,
        content  TEXT    DEFAULT '',
        tags     TEXT    DEFAULT '[]',
        ts       TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_col_cat ON collections(category);

    -- ══ Streak System ══
    CREATE TABLE IF NOT EXISTS streaks (
        key      TEXT PRIMARY KEY,
        current  INTEGER DEFAULT 0,
        best     INTEGER DEFAULT 0,
        last_day TEXT    DEFAULT ''
    );

    -- ══ Activity Graph ══
    CREATE TABLE IF NOT EXISTS activity_log (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        type    TEXT    NOT NULL,
        value   INTEGER DEFAULT 1,
        ts      TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_act_ts ON activity_log(ts);

    -- ══ VPN Config Manager ══
    CREATE TABLE IF NOT EXISTS vpn_configs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT    NOT NULL,
        content   TEXT    NOT NULL,
        server    TEXT    DEFAULT '',
        protocol  TEXT    DEFAULT '',
        tags      TEXT    DEFAULT '[]',
        favorite  INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        last_used TEXT    DEFAULT '',
        latency   INTEGER DEFAULT 0,
        fingerprint TEXT  DEFAULT '',
        ts        TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vpn_config_lab (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        config_id INTEGER NOT NULL,
        action   TEXT    NOT NULL,
        result   TEXT    DEFAULT '',
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vpn_rotation (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        config_id INTEGER NOT NULL,
        ts       TEXT    NOT NULL
    );

    -- ══ Auto Config Store ══
    CREATE TABLE IF NOT EXISTS store_products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        category    TEXT    DEFAULT 'عمومی',
        price       INTEGER DEFAULT 0,
        description TEXT    DEFAULT '',
        stock       INTEGER DEFAULT 0,
        active      INTEGER DEFAULT 1,
        ts          TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_configs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        content    TEXT    NOT NULL,
        sold       INTEGER DEFAULT 0,
        order_id   INTEGER DEFAULT 0,
        ts         TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        order_uid   TEXT    NOT NULL UNIQUE,
        uid         INTEGER NOT NULL,
        username    TEXT    DEFAULT '',
        name        TEXT    DEFAULT '',
        product_id  INTEGER NOT NULL,
        product_name TEXT   DEFAULT '',
        price       INTEGER DEFAULT 0,
        status      TEXT    DEFAULT 'pending',
        receipt_file TEXT   DEFAULT '',
        config_id   INTEGER DEFAULT 0,
        coupon      TEXT    DEFAULT '',
        ts          TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_so_uid ON store_orders(uid);
    CREATE INDEX IF NOT EXISTS idx_so_status ON store_orders(status);
    CREATE TABLE IF NOT EXISTS store_coupons (
        code     TEXT PRIMARY KEY,
        discount INTEGER DEFAULT 0,
        uses     INTEGER DEFAULT 0,
        max_uses INTEGER DEFAULT 100,
        active   INTEGER DEFAULT 1,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS waiting_list (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        uid        INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        ts         TEXT    NOT NULL
    );

    -- ══ CRM ══
    CREATE TABLE IF NOT EXISTS crm_customers (
        uid            INTEGER PRIMARY KEY,
        name           TEXT    DEFAULT '',
        username       TEXT    DEFAULT '',
        total_spent    INTEGER DEFAULT 0,
        purchase_count INTEGER DEFAULT 0,
        vip_level      INTEGER DEFAULT 0,
        first_purchase TEXT    DEFAULT '',
        last_purchase  TEXT    DEFAULT '',
        renewal_date   TEXT    DEFAULT '',
        country        TEXT    DEFAULT '',
        notes          TEXT    DEFAULT '',
        blacklisted    INTEGER DEFAULT 0,
        whitelisted    INTEGER DEFAULT 0,
        coupons        TEXT    DEFAULT '[]'
    );
    CREATE TABLE IF NOT EXISTS crm_campaigns (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT    NOT NULL,
        template  TEXT    NOT NULL,
        target    TEXT    DEFAULT 'all',
        status    TEXT    DEFAULT 'draft',
        sent      INTEGER DEFAULT 0,
        scheduled TEXT    DEFAULT '',
        ts        TEXT    NOT NULL
    );

    -- ══ Support / Ticket System ══
    CREATE TABLE IF NOT EXISTS support_tickets (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        uid        INTEGER NOT NULL,
        username   TEXT    DEFAULT '',
        name       TEXT    DEFAULT '',
        subject    TEXT    NOT NULL,
        status     TEXT    DEFAULT 'open',
        priority   TEXT    DEFAULT 'normal',
        ts         TEXT    NOT NULL,
        closed_ts  TEXT    DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        uid       INTEGER NOT NULL,
        text      TEXT    NOT NULL,
        is_admin  INTEGER DEFAULT 0,
        ts        TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_tm_ticket ON ticket_messages(ticket_id);

    -- ══ Economy / Coin System ══
    CREATE TABLE IF NOT EXISTS economy (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT '0'
    );
    CREATE TABLE IF NOT EXISTS shop_items (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT    NOT NULL,
        price    INTEGER NOT NULL,
        effect   TEXT    DEFAULT '',
        category TEXT    DEFAULT 'عمومی',
        active   INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS inventory (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id  INTEGER NOT NULL,
        qty      INTEGER DEFAULT 1,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS coin_txns (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        amount  INTEGER NOT NULL,
        reason  TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );

    -- ══ Virtual Pet ══
    CREATE TABLE IF NOT EXISTS virtual_pet (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );

    -- ══ Virtual House ══
    CREATE TABLE IF NOT EXISTS virtual_house (
        room  TEXT PRIMARY KEY,
        items TEXT DEFAULT '[]',
        level INTEGER DEFAULT 1
    );

    -- ══ Skill Tree ══
    CREATE TABLE IF NOT EXISTS skill_tree (
        skill    TEXT PRIMARY KEY,
        level    INTEGER DEFAULT 0,
        max_level INTEGER DEFAULT 5,
        xp       INTEGER DEFAULT 0
    );

    -- ══ Quest System ══
    CREATE TABLE IF NOT EXISTS quests (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        title     TEXT    NOT NULL,
        target    INTEGER NOT NULL,
        current   INTEGER DEFAULT 0,
        reward    INTEGER DEFAULT 50,
        active    INTEGER DEFAULT 1,
        done      INTEGER DEFAULT 0,
        ts        TEXT    NOT NULL
    );

    -- ══ Badge Collection ══
    CREATE TABLE IF NOT EXISTS badges (
        id    TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        emoji TEXT DEFAULT '🏅',
        ts    TEXT NOT NULL
    );

    -- ══ Boss Fight ══
    CREATE TABLE IF NOT EXISTS boss_fight (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );

    -- ══ Mystery Box ══
    CREATE TABLE IF NOT EXISTS mystery_boxes (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        opened  INTEGER DEFAULT 0,
        reward  TEXT    DEFAULT '',
        ts      TEXT    NOT NULL
    );

    -- ══ Lab / Laboratory ══
    CREATE TABLE IF NOT EXISTS lab_experiments (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT    NOT NULL,
        input   TEXT    NOT NULL,
        output  TEXT    DEFAULT '',
        status  TEXT    DEFAULT 'pending',
        ts      TEXT    NOT NULL
    );

    -- ══ Leaderboard ══
    CREATE TABLE IF NOT EXISTS leaderboard (
        uid    INTEGER PRIMARY KEY,
        name   TEXT    DEFAULT '',
        score  INTEGER DEFAULT 0,
        updated TEXT   DEFAULT ''
    );

    -- ══ Smart Search ══
    CREATE TABLE IF NOT EXISTS search_history (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        query   TEXT    NOT NULL,
        results INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );

    -- ══ Archive Mode ══
    CREATE TABLE IF NOT EXISTS archives (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT    DEFAULT 'عمومی',
        title    TEXT    NOT NULL,
        content  TEXT    NOT NULL,
        ts       TEXT    NOT NULL
    );

    -- ══ Daily Reward ══
    CREATE TABLE IF NOT EXISTS daily_reward (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );

    -- ══ Mission Log ══
    CREATE TABLE IF NOT EXISTS mission_log (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        mission TEXT    NOT NULL,
        result  TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );

    -- ══ V9: Product Knowledge / Context ══
    CREATE TABLE IF NOT EXISTS product_knowledge (
        product_id   INTEGER PRIMARY KEY,
        product_name TEXT    DEFAULT '',
        product_type TEXT    DEFAULT 'عمومی',
        description  TEXT    DEFAULT '',
        features     TEXT    DEFAULT '',
        benefits     TEXT    DEFAULT '',
        rules        TEXT    DEFAULT '',
        faq          TEXT    DEFAULT '',
        sales_text   TEXT    DEFAULT '',
        delivery_text TEXT   DEFAULT '',
        restrictions TEXT    DEFAULT '',
        keywords     TEXT    DEFAULT '',
        ai_context   TEXT    DEFAULT '',
        updated      TEXT    DEFAULT ''
    );

    -- ══ V9: Black Box Recorder ══
    CREATE TABLE IF NOT EXISTS black_box (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        event   TEXT    NOT NULL,
        detail  TEXT    DEFAULT '',
        level   TEXT    DEFAULT 'info',
        ts      TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_bb_ts ON black_box(ts);

    -- ══ V9: Blacklist Intelligence ══
    CREATE TABLE IF NOT EXISTS blacklist_intel (
        uid     INTEGER PRIMARY KEY,
        level   TEXT    DEFAULT 'normal',
        reason  TEXT    DEFAULT '',
        score   INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );

    -- ══ V9: Custom Commands (Command Studio) ══
    CREATE TABLE IF NOT EXISTS custom_commands (
        name       TEXT    PRIMARY KEY,
        alias      TEXT    DEFAULT '',
        trigger    TEXT    NOT NULL,
        action     TEXT    NOT NULL,
        params     TEXT    DEFAULT '{}',
        active     INTEGER DEFAULT 1,
        run_count  INTEGER DEFAULT 0,
        ts         TEXT    NOT NULL
    );

    -- ══ V9: Event Replay Log ══
    CREATE TABLE IF NOT EXISTS event_replay (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT    NOT NULL,
        event     TEXT    NOT NULL,
        data      TEXT    DEFAULT '',
        ts        TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_er_entity ON event_replay(entity_id);

    -- ══ V9: Watermark Registry ══
    CREATE TABLE IF NOT EXISTS watermark_registry (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_uid  TEXT    NOT NULL,
        uid        INTEGER NOT NULL,
        fingerprint TEXT   NOT NULL,
        ts         TEXT    NOT NULL
    );

    -- ══ V9: Smart Negotiation Log ══
    CREATE TABLE IF NOT EXISTS negotiation_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        uid        INTEGER NOT NULL,
        product_id INTEGER DEFAULT 0,
        offer      INTEGER DEFAULT 0,
        counter    INTEGER DEFAULT 0,
        outcome    TEXT    DEFAULT '',
        ts         TEXT    NOT NULL
    );

    -- ══ V9: Personal Radar Events ══
    CREATE TABLE IF NOT EXISTS radar_events (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        type    TEXT    NOT NULL,
        summary TEXT    NOT NULL,
        score   INTEGER DEFAULT 0,
        seen    INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );

    -- ══ V9: Airlock Mode ══
    CREATE TABLE IF NOT EXISTS airlock_log (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        reason TEXT   NOT NULL,
        ts     TEXT   NOT NULL
    );

    -- ══ V9: Context Switcher ══
    CREATE TABLE IF NOT EXISTS context_sessions (
        key     TEXT    PRIMARY KEY,
        type    TEXT    NOT NULL,
        data    TEXT    DEFAULT '{}',
        updated TEXT    DEFAULT ''
    );

    -- ══ V9: Export Jobs ══
    CREATE TABLE IF NOT EXISTS export_jobs (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        format   TEXT    NOT NULL,
        data_key TEXT    NOT NULL,
        filepath TEXT    DEFAULT '',
        status   TEXT    DEFAULT 'pending',
        ts       TEXT    NOT NULL
    );

    -- ══ V9: Universal Capture Log ══
    CREATE TABLE IF NOT EXISTS capture_log (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        type     TEXT    NOT NULL,
        content  TEXT    DEFAULT '',
        chat_id  INTEGER DEFAULT 0,
        ts       TEXT    NOT NULL
    );
    """)
    conn.commit()

# ── helpers ──────────────────────────────────

def db_get(table: str, key: str, default: str = "") -> str:
    with _db_lock:
        conn = get_conn()
        row = conn.execute(
            f"SELECT value FROM {table} WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row else default

def db_set(table: str, key: str, value: str) -> None:
    with _db_lock:
        conn = get_conn()
        conn.execute(
            f"INSERT INTO {table}(key,value) VALUES(?,?) "
            f"ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()

def setting(key: str, default: str = "") -> str:
    return db_get("settings", key, default)

def set_setting(key: str, value: str) -> None:
    db_set("settings", key, value)

def profile_val(key: str, default: int = 0) -> int:
    v = db_get("onyx_profile", key, str(default))
    try:
        return int(v)
    except Exception:
        return default

def profile_incr(key: str, by: int = 1) -> int:
    val = profile_val(key) + by
    db_set("onyx_profile", key, str(val))
    return val

# ══════════════════════════════════════════════
#  ابزارهای تاریخ ایران — نسخه اصلاح‌شده V9
# ══════════════════════════════════════════════
try:
    import jdatetime as _jdt
    _HAS_JDATETIME = True
except ImportError:
    _HAS_JDATETIME = False

# ── تبدیل دقیق گرگوری به شمسی (بدون نیاز به jdatetime) ──
def _gregorian_to_jalali(gy: int, gm: int, gd: int):
    """تبدیل تاریخ میلادی به شمسی — الگوریتم دقیق"""
    g_d_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for i in range(gm - 1):
        g_d_no += [31,28 + (1 if (gy%4==0 and gy%100!=0) or gy%400==0 else 0),
                   31,30,31,30,31,31,30,31,30,31][i]
    g_d_no += gd - 1
    j_d_no = g_d_no - 79
    j_np = j_d_no // 12053
    j_d_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_d_no // 1461)
    j_d_no %= 1461
    if j_d_no >= 366:
        jy += (j_d_no - 1) // 365
        j_d_no = (j_d_no - 1) % 365
    for i, v in enumerate([31,31,31,31,31,31,30,30,30,30,30,29]):
        if j_d_no >= v:
            j_d_no -= v
        else:
            jm = i + 1
            jd = j_d_no + 1
            break
    else:
        jm = 12; jd = j_d_no + 1
    return jy, jm, jd

def iran_now() -> datetime.datetime:
    """زمان فعلی ایران (UTC+3:30)"""
    tz = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
    return datetime.datetime.now(tz=tz)

def jalali(dt: Optional[datetime.datetime] = None) -> str:
    """تبدیل datetime به تاریخ شمسی YYYY/MM/DD"""
    if dt is None:
        dt = iran_now()
    try:
        if _HAS_JDATETIME:
            # اگر dt دارای timezone است، naive می‌شود
            if dt.tzinfo is not None:
                dt_naive = dt.replace(tzinfo=None)
            else:
                dt_naive = dt
            j = _jdt.datetime.fromgregorian(datetime=dt_naive)
            return j.strftime("%Y/%m/%d")
    except Exception:
        pass
    # استفاده از الگوریتم داخلی (دقیق‌تر از year-621)
    try:
        jy, jm, jd = _gregorian_to_jalali(dt.year, dt.month, dt.day)
        return f"{jy}/{jm:02d}/{jd:02d}"
    except Exception:
        return f"{dt.year - 621}/{dt.month:02d}/{dt.day:02d}"

def jalali_weekday(dt: Optional[datetime.datetime] = None) -> str:
    """روز هفته به فارسی"""
    if dt is None:
        dt = iran_now()
    days = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]
    return days[dt.weekday()]

def now_str() -> str:
    """زمان فعلی به صورت رشته: تاریخ شمسی ساعت:دقیقه"""
    n = iran_now()
    return f"{jalali(n)} {n.strftime('%H:%M')}"

# ══════════════════════════════════════════════
#  ابزار UI
# ══════════════════════════════════════════════
def box(title: str, rows: list, footer: str = "") -> str:
    sep = "──────────────────────"
    lines = [f"╭─ {title}"]
    for r in rows:
        if r == "---":
            lines.append(f"├─ {sep[:20]}")
        else:
            lines.append(f"│ {r}")
    if footer:
        lines.append(f"├─ {sep[:20]}")
        lines.append(f"│ {footer}")
    lines.append("╰─" + sep[:20])
    return "\n".join(lines)

def cmd_pattern(p: str) -> str:
    return rf"^{p}"

async def safe_edit(event, text: str) -> None:
    try:
        await event.edit(text)
    except Exception as e:
        logger.debug(f"safe_edit: {e}")

# ══════════════════════════════════════════════
#  ثبت دستور و آمار
# ══════════════════════════════════════════════
def record_cmd(cmd: str) -> None:
    ts = now_str()
    with _db_lock:
        conn = get_conn()
        conn.execute("INSERT INTO cmd_history(cmd,ts) VALUES(?,?)", (cmd[:80], ts))
        # روزانه
        today = jalali()
        conn.execute(
            "INSERT INTO daily_stats(date,cmds) VALUES(?,1) "
            "ON CONFLICT(date) DO UPDATE SET cmds=cmds+1",
            (today,)
        )
        conn.commit()
    # XP
    xp  = profile_val("xp") + 1
    lvl = profile_val("level") or 1
    if xp >= lvl * 100:
        xp -= lvl * 100
        lvl += 1
        db_set("onyx_profile", "level", str(lvl))
        logger.info(f"🌟 ONYX Level Up! → {lvl}")
    db_set("onyx_profile", "xp", str(xp))
    db_set("onyx_profile", "cmds_executed", str(profile_val("cmds_executed") + 1))
    # روز فعال
    today = jalali()
    last_day = db_get("onyx_profile", "last_active_date", "")
    if last_day != today:
        db_set("onyx_profile", "last_active_date", today)
        db_set("onyx_profile", "active_days", str(profile_val("active_days") + 1))

def record_error(msg: str) -> None:
    today = jalali()
    with _db_lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO daily_stats(date,errors) VALUES(?,1) "
            "ON CONFLICT(date) DO UPDATE SET errors=errors+1",
            (today,)
        )
        conn.commit()

# ══════════════════════════════════════════════
#  رمزگذاری
# ══════════════════════════════════════════════
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    _AES_AVAIL = True
except ImportError:
    _AES_AVAIL = False

def _vault_key() -> bytes:
    raw = setting("vault_key", "")
    if not raw:
        return b"ONYX_DEFAULT_KEY" + b"\x00" * 16
    return (raw.encode()[:32]).ljust(32, b"\x00")

def vault_encrypt(text: str) -> str:
    if not _AES_AVAIL:
        return base64.b64encode(text.encode()).decode()
    key  = _vault_key()
    iv   = os.urandom(16)
    c    = AES.new(key, AES.MODE_CBC, iv)
    enc  = c.encrypt(pad(text.encode(), AES.block_size))
    return base64.b64encode(iv + enc).decode()

def vault_decrypt(data: str) -> str:
    if not _AES_AVAIL:
        return base64.b64decode(data.encode()).decode()
    key = _vault_key()
    raw = base64.b64decode(data.encode())
    iv  = raw[:16]; enc = raw[16:]
    c   = AES.new(key, AES.MODE_CBC, iv)
    return unpad(c.decrypt(enc), AES.block_size).decode()


# ══════════════════════════════════════════════════════
#  ═══  FONTS  ═══
# ══════════════════════════════════════════════════════
from typing import Dict, Optional

FONTS: Dict[str, Optional[dict]] = {
    "bold": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    ),
    "italic": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    ),
    "bold_italic": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕"
    ),
    "mono": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    ),
    "script": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"
    ),
    "fraktur": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"
    ),
    "double": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
    ),
    "bubble": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ⓪①②③④⑤⑥⑦⑧⑨"
    ),
    "small": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    ),
    "wide": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９"
    ),
    "sans": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"
    ),
    "sans_bold": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    ),
    "sans_italic": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    ),
    "old_english": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"
    ),
    "negative": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩🅐🅑🅒🅓🅔🅕🅖🅗🅘🅙🅚🅛🅜🅝🅞🅟🅠🅡🅢🅣🅤🅥🅦🅧🅨🅩⓿❶❷❸❹❺❻❼❽❾"
    ),
    "curly": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
    ),
    "square": str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
    ),
    "strikethrough": None,
    "underline": None,
}

CLOCK_FONTS = {
    # ── کلاسیک ──
    "normal":      lambda t: t,
    "bold":        lambda t: t.translate(FONTS["bold"]),
    "bubble":      lambda t: t.translate(FONTS["bubble"]),
    "mono":        lambda t: t.translate(FONTS["mono"]),
    "script":      lambda t: t.translate(FONTS["script"]),
    # ── جدید V9 ──
    "double":      lambda t: t.translate(FONTS["double"]),
    "wide":        lambda t: t.translate(FONTS["wide"]),
    "sans_bold":   lambda t: t.translate(FONTS["sans_bold"]),
    "fraktur":     lambda t: t.translate(FONTS["fraktur"]),
    "curly":       lambda t: t.translate(FONTS["curly"]),
    "negative":    lambda t: t.translate(FONTS["negative"]),
    "square":      lambda t: t.translate(FONTS["square"]),
    "small":       lambda t: t.translate(FONTS["small"]),
    # ── دکوراتیو ──
    "stars":       lambda t: "⭐" + t + "⭐",
    "diamond":     lambda t: "💎" + t + "💎",
    "fire":        lambda t: "🔥" + t + "🔥",
    "lightning":   lambda t: "⚡" + t + "⚡",
    "moon":        lambda t: "🌙" + t + "🌙",
    "clock_emoji": lambda t: "🕐 " + t,
    "brackets":    lambda t: "【" + t + "】",
    "double_brackets": lambda t: "《" + t + "》",
    "arrows":      lambda t: "→ " + t + " ←",
    "wave":        lambda t: "〜" + t + "〜",
}

_current_font: str = "none"

def get_font() -> str:
    return _current_font

def set_font(name: str) -> None:
    _current_font = name

def apply_font(text: str, mode: Optional[str] = None) -> str:
    m = mode or _current_font
    if m == "none" or m not in FONTS or FONTS[m] is None:
        if m == "strikethrough":
            return "".join(c + "\u0336" for c in text)
        if m == "underline":
            return "".join(c + "\u0332" for c in text)
        return text
    return text.translate(FONTS[m])

def apply_clock_font(text: str, font_name: str = "normal") -> str:
    fn = CLOCK_FONTS.get(font_name, CLOCK_FONTS["normal"])
    return fn(text)

FONT_SAMPLES = {
    "bold":        "𝗛𝗲𝗹𝗹𝗼",
    "italic":      "𝘏𝘦𝘭𝘭𝘰",
    "bold_italic": "𝙃𝙚𝙡𝙡𝙤",
    "mono":        "𝙷𝚎𝚕𝚕𝚘",
    "script":      "𝓗𝓮𝓵𝓵𝓸",
    "fraktur":     "𝔥𝔢𝔩𝔩𝔬",
    "double":      "𝕙𝕖𝕝𝕝𝕠",
    "bubble":      "ⓗⓔⓛⓛⓞ",
    "small":       "ʜᴇʟʟᴏ",
    "wide":        "ｈｅｌｌｏ",
    "sans":        "𝗁𝖾𝗅𝗅𝗈",
    "sans_bold":   "𝗵𝗲𝗹𝗹𝗼",
    "negative":    "🅗🅔🅛🅛🅞",
    "curly":       "𝒽𝑒𝓁𝓁𝑜",
    "square":      "🄷🄴🄻🄻🄾",
    "strikethrough": "H̶e̶l̶l̶o̶",
    "underline":   "H̲e̲l̲l̲o̲",
}


# ══════════════════════════════════════════════════════
#  ═══  HELP MENU DATA  ═══
# ══════════════════════════════════════════════════════
from telethon import events

# ══════════════════════════════════════════════
#  دیکشنری کامل منو
# ══════════════════════════════════════════════

MENU_CATEGORIES = {
    "اصلی":          "🏠",
    "پروفایل":       "👤",
    "مخاطبان":       "👥",
    "ساعت_فونت":     "⏰",
    "تحلیل":         "📊",
    "جستجو":         "🔍",
    "اتوماسیون":     "🤖",
    "ابزار_هوشمند":  "🧠",
    "پیام":          "💬",
    "رسانه":         "📥",
    "فایل":          "📁",
    "امنیت":         "🔐",
    "پایش":          "👁",
    "ابزار":         "🔧",
    "کارها":         "📋",
    "تقویم":         "📅",
    "هزینه":         "💰",
    "داشبورد":       "📈",
    "پلاگین":        "🧩",
    "بکاپ":          "💾",
    "بازی":          "🎮",
    "انیمیشن":       "✨",
    "راهنما":        "❓",
}

FULL_MENU: dict = {

    "🏠 اصلی / سیستم": [
        ("پینگ",             "پینگ و وضعیت سیستم",            "پینگ",                     "پینگ"),
        ("نسخه",             "نسخه ONYX",                      "نسخه",                     "نسخه"),
        ("درباره",           "درباره ONYX SELF V7 PRO'S",            "درباره",                   "درباره"),
        ("داشبورد",          "داشبورد کامل کنترل",             "داشبورد",                  "داشبورد"),
        ("آمار_روزانه",      "آمار امروز",                     "آمار_روزانه",              "آمار_روزانه"),
        ("آمار_ماهانه",      "آمار ماه جاری",                  "آمار_ماهانه",              "آمار_ماهانه"),
        ("بهینه‌سازی_دیتابیس","VACUUM + بهینه‌سازی DB",        "بهینه‌سازی_دیتابیس",       "بهینه‌سازی_دیتابیس"),
        ("تنظیمات",          "نمایش تنظیمات",                  "تنظیمات",                  "تنظیمات"),
        ("تنظیم",            "ذخیره تنظیم",                    "تنظیم [کلید]|[مقدار]",    "تنظیم نام|مقدار"),
        ("حذف_تنظیم",        "حذف تنظیم",                      "حذف_تنظیم [کلید]",         "حذف_تنظیم نام"),
        ("تنظیمات",          "نمایش تمام تنظیمات",             "تنظیمات",                  "تنظیمات"),
        ("داشبورد",          "داشبورد کنترل مرکزی",            "داشبورد",                  "داشبورد"),
        ("درباره",           "درباره ONYX SELF V7 PRO'S",       "درباره",                   "درباره"),
        ("وضعیت_کامل",       "وضعیت کامل سیستم",               "وضعیت_کامل",               "وضعیت_کامل"),
        ("گزارش_کامل",       "گزارش هفتگی جامع",               "گزارش_کامل",               "گزارش_کامل"),
        ("v7",               "راهنمای سریع V7",                "v7",                       "v7"),
        ("منو_v7",           "منوی کامل V7",                   "منو_v7",                   "منو_v7"),
        ("همه_v7",           "آمار دستورات V7",                "همه_v7",                   "همه_v7"),
        ("راهنما_کامل",      "راهنمای همه دستورات",            "راهنما_کامل",              "راهنما_کامل"),
        ("آمار_v7",          "آمار سیستم‌های V7",              "آمار_v7",                  "آمار_v7"),
    ],

    "👤 پروفایل": [
        ("پروفایل",          "پروفایل کاربر / ریپلای",         "پروفایل",                  "پروفایل"),
        ("پروفایل_onyx",     "پروفایل ONYX با XP و سطح",       "پروفایل_onyx",             "پروفایل_onyx"),
        ("نام_من",           "تغییر نام پروفایل",              "نام_من [نام]",             "نام_من علی احمدی"),
        ("بیو_من",           "تغییر بیو پروفایل",              "بیو_من [بیو]",             "بیو_من کد زندگیمه"),
        ("آیدی",             "آیدی کاربر",                     "آیدی",                     "آیدی (ریپلای)"),
        ("کپی_اسم",          "کپی نام کاربر",                  "کپی_اسم",                  "کپی_اسم (ریپلای)"),
        ("کپی_بیو",          "کپی بیو کاربر",                  "کپی_بیو",                  "کپی_بیو (ریپلای)"),
        ("کپی_یوزر",         "کپی یوزرنیم",                    "کپی_یوزر",                 "کپی_یوزر (ریپلای)"),
        ("کپی_آیدی",         "کپی آیدی عددی",                  "کپی_آیدی",                 "کپی_آیدی (ریپلای)"),
        ("بنر",              "بنر ASCII از متن",               "بنر [متن]",                "بنر ONYX"),
        ("qr",               "ساخت QR Code",                   "qr [متن/لینک]",            "qr https://t.me"),
        ("qrتلگرام",         "QR تلگرام یوزر",                 "qrتلگرام [@user]",         "qrتلگرام @me"),
    ],

    "👥 مخاطبان": [
        ("پروفایل_کامل",     "پروفایل کامل با دیتابیس",       "پروفایل_کامل [@user]",     "پروفایل_کامل @ali"),
        ("وضعیت_مخاطب",     "تنظیم وضعیت",                   "وضعیت_مخاطب [@] [نوع]",   "وضعیت_مخاطب @ali vip"),
        ("برچسب_مخاطب",     "تنظیم برچسب",                   "برچسب_مخاطب [@] [برچسب]", "برچسب_مخاطب @ali friend"),
        ("یادداشت_مخاطب",   "یادداشت برای مخاطب",            "یادداشت_مخاطب [@]|[یادداشت]","یادداشت_مخاطب @ali|دوست قدیمی"),
        ("امتیاز_مخاطب",    "امتیاز مخاطب",                  "امتیاز_مخاطب [@] [±n]",   "امتیاز_مخاطب @ali +10"),
        ("تگ_مخاطب",        "تگ مخاطب",                      "تگ_مخاطب [@]|[تگ]",        "تگ_مخاطب @ali|صمیمی"),
        ("تاریخچه_مخاطب",   "تاریخچه تغییرات",               "تاریخچه_مخاطب [@user]",    "تاریخچه_مخاطب @ali"),
        ("یادآوری",          "یادآوری برای مخاطب",            "یادآوری [@] [متن]",         "یادآوری @ali تماس بگیر"),
        ("یادآوری‌ها",       "لیست یادآوری‌ها",               "یادآوری‌ها",               "یادآوری‌ها"),
        ("پیدا",             "جستجو مخاطب",                   "پیدا [نام/تگ]",             "پیدا دوست"),
        ("نقشه_رابطه",      "نقشه رابطه مخاطبان",            "نقشه_رابطه",               "نقشه_رابطه"),
        ("آمار_مخاطبان",    "آمار کلی مخاطبان",               "آمار_مخاطبان",             "آمار_مخاطبان"),
        ("سنجاق",            "سنجاق پیام",                     "سنجاق (ریپلای)",           "سنجاق"),
        ("سنجاق‌ها",         "لیست سنجاق‌ها",                 "سنجاق‌ها",                 "سنجاق‌ها"),
        ("دفترچه",           "دفترچه مخاطب",                  "دفترچه [@]|[کلید=مقدار]", "دفترچه @ali|تلفن=09..."),
        ("دفترچه_نمایش",    "نمایش دفترچه",                  "دفترچه_نمایش [@]",         "دفترچه_نمایش @ali"),
        ("بلاک",             "بلاک کردن",                     "بلاک (ریپلای)",            "بلاک"),
        ("آنبلاک",           "آنبلاک کردن",                   "آنبلاک (ریپلای)",          "آنبلاک"),
        ("سکوت",             "ساکت کردن کاربر",               "سکوت (ریپلای)",            "سکوت"),
        ("حذف_سکوت",         "برداشتن سکوت",                  "حذف_سکوت (ریپلای)",        "حذف_سکوت"),
        ("دشمن",             "اضافه به دشمنان",               "دشمن (ریپلای)",            "دشمن"),
        ("حذف_دشمن",         "حذف از دشمنان",                 "حذف_دشمن (ریپلای)",        "حذف_دشمن"),
        ("عشق",              "اضافه به لیست عشق",             "عشق (ریپلای)",             "عشق"),
        ("حذف_عشق",          "حذف از لیست عشق",               "حذف_عشق (ریپلای)",         "حذف_عشق"),
    ],

    "⏰ ساعت و فونت": [
        ("ساعت_فعال",        "شروع ساعت ایران",               "ساعت_فعال",                "ساعت_فعال"),
        ("ساعت_خاموش",       "خاموش کردن ساعت",               "ساعت_خاموش",               "ساعت_خاموش"),
        ("وضعیت_ساعت",       "وضعیت ساعت",                    "وضعیت_ساعت",               "وضعیت_ساعت"),
        ("فونت_ساعت",        "لیست فونت ساعت",                "فونت_ساعت",                "فونت_ساعت"),
        ("فونت_ساعت_ست",     "تغییر فونت ساعت",               "فونت_ساعت_ست [نام]",       "فونت_ساعت_ست bold"),
        ("لیست_فونت",        "لیست فونت‌های متن",             "لیست_فونت",                "لیست_فونت"),
        ("فونت",             "تغییر فونت پیام‌ها",            "فونت [نام]",               "فونت bold"),
        ("متن_عادی",         "فونت عادی",                     "متن_عادی",                 "متن_عادی"),
        ("متن_پررنگ",        "فونت پررنگ",                    "متن_پررنگ",                "متن_پررنگ"),
        ("متن_کج",           "فونت کج",                       "متن_کج",                   "متن_کج"),
        ("متن_کد",           "فونت کد/تایپ‌رایتر",           "متن_کد",                   "متن_کد"),
        ("حذف_فونت",         "غیرفعال‌کردن فونت",             "حذف_فونت",                 "حذف_فونت"),
    ],

    "📊 تحلیل و آمار": [
        ("تاریخچه",          "تاریخچه چت",                    "تاریخچه [تعداد]",          "تاریخچه 20"),
        ("جستجو_پیام",       "جستجو در حافظه چت",             "جستجو_پیام [متن]",         "جستجو_پیام سلام"),
        ("ماشین_زمان",       "پیام‌های X روز پیش",            "ماشین_زمان [روز]",         "ماشین_زمان 7"),
        ("پخش_مجدد",         "پخش مجدد گفتگو",                "پخش_مجدد [تعداد]",         "پخش_مجدد 10"),
        ("آمار_من",          "تحلیل شخصی",                    "آمار_من",                  "آمار_من"),
        ("هیت_مپ",           "نقشه حرارتی ارسال",             "هیت_مپ",                   "هیت_مپ"),
        ("DNA_چت",           "DNA تحلیل چت",                  "DNA_چت [@user]",           "DNA_چت @ali"),
        ("خوانندگان_پنهان",  "تشخیص خوانندگان پنهان",         "خوانندگان_پنهان",          "خوانندگان_پنهان"),
        ("پیش‌بینی_فعالیت",  "پیش‌بینی فعالیت",              "پیش‌بینی_فعالیت",          "پیش‌بینی_فعالیت"),
        ("تحول_امتیاز",      "امتیاز کلی تحول",               "تحول_امتیاز",              "تحول_امتیاز"),
        ("آمار_آنلاین",      "آمار آنلاین مخاطب",             "آمار_آنلاین [@user]",      "آمار_آنلاین @ali"),
    ],

    "🤖 اتوماسیون": [
        ("منشی_فعال",        "فعال‌کردن منشی خودکار",         "منشی_فعال",                "منشی_فعال"),
        ("منشی_خاموش",       "خاموش‌کردن منشی",               "منشی_خاموش",               "منشی_خاموش"),
        ("تنظیم_منشی",       "پیام منشی",                     "تنظیم_منشی [متن]",         "تنظیم_منشی الان نیستم"),
        ("مشاهده_منشی",      "وضعیت منشی",                    "مشاهده_منشی",              "مشاهده_منشی"),
        ("جواب",             "جواب خودکار",                   "جواب [کلید]|[پاسخ]",       "جواب سلام|سلام عزیزم"),
        ("حذف_جواب",         "حذف جواب",                      "حذف_جواب [کلید]",          "حذف_جواب سلام"),
        ("لیست_جواب‌ها",     "لیست جواب‌ها",                  "لیست_جواب‌ها",             "لیست_جواب‌ها"),
        ("قانون",            "قانون هوشمند",                  "قانون [کلید]|[پاسخ]",      "قانون سلام|درود"),
        ("قوانین",           "لیست قوانین",                   "قوانین",                   "قوانین"),
        ("حذف_قانون",        "حذف قانون",                     "حذف_قانون [کلید]",         "حذف_قانون سلام"),
        ("ماکرو",            "ذخیره ماکرو",                   "ماکرو [نام]=[متن]",         "ماکرو hi=سلام همه!"),
        ("ماکروها",          "لیست ماکروها",                  "ماکروها",                  "ماکروها"),
        ("حذف_ماکرو",        "حذف ماکرو",                     "حذف_ماکرو [نام]",          "حذف_ماکرو hi"),
        ("قالب",             "ذخیره قالب",                    "قالب [نام]|[متن]",          "قالب خوشامد|سلام {name}"),
        ("قالب‌ها",          "لیست قالب‌ها",                  "قالب‌ها",                  "قالب‌ها"),
        ("تبلیغ",            "تنظیم متن تبلیغ",               "تبلیغ [متن]",              "تبلیغ کانال ما را فالو کن"),
        ("گروه",             "اضافه‌کردن گروه",               "گروه [@id]",               "گروه @mygroup"),
        ("حذف_گروه",         "حذف گروه",                      "حذف_گروه [@id]",           "حذف_گروه @mygroup"),
        ("گروه‌ها",          "لیست گروه‌ها",                  "گروه‌ها",                  "گروه‌ها"),
        ("زمان",             "فاصله ارسال تبلیغ",             "زمان [ثانیه]",             "زمان 60"),
        ("شروع",             "شروع تبلیغات",                  "شروع",                     "شروع"),
        ("توقف",             "توقف تبلیغات",                  "توقف",                     "توقف"),
        ("بفرست",            "فوروارد به همه",                "بفرست [گپ|کانال|پیوی|همه]","بفرست گپ (ریپلای)"),
        ("اسپم",             "ارسال چندباره",                 "اسپم [تعداد] [متن]",        "اسپم 5 سلام"),
        ("حذف",              "حذف پیام‌های ارسالی",           "حذف [تعداد]",              "حذف 10"),
        ("حالت_خواب",        "حالت خواب",                     "حالت_خواب [روشن|خاموش]",  "حالت_خواب روشن"),
        ("حالت_اضطراری",     "حالت اضطراری — توقف همه",       "حالت_اضطراری [روشن|خاموش]","حالت_اضطراری روشن"),
        ("صف",               "صف هوشمند ارسال",               "صف [@/id] [متن] [ثانیه]",  "صف @ali سلام 30"),
        ("لیست_صف",          "لیست صف انتظار",                "لیست_صف",                  "لیست_صف"),
        ("وظیفه",            "ورک‌فلو جدید",                  "وظیفه [نام]|[گام‌ها]",     "وظیفه test|msg:سلام|wait:5"),
        ("وظیفه_لیست",       "لیست ورک‌فلوها",                "وظیفه_لیست",               "وظیفه_لیست"),
        ("وظیفه_اجرا",       "اجرای ورک‌فلو",                 "وظیفه_اجرا [نام]",         "وظیفه_اجرا test"),
        ("وظیفه_حذف",        "حذف ورک‌فلو",                   "وظیفه_حذف [نام]",          "وظیفه_حذف test"),
        ("وظیفه_آمار",       "آمار ورک‌فلو",                  "وظیفه_آمار",               "وظیفه_آمار"),
        ("کامنت_متن",        "تنظیم متن کامنت",               "کامنت_متن [متن||متن2]",    "کامنت_متن عالی||👍"),
        ("کامنت_کانال",      "کانال کامنت‌گذار",              "کامنت_کانال [@ch]",        "کامنت_کانال @news"),
        ("کامنت_شروع",       "شروع کامنت‌گذار",               "کامنت_شروع",               "کامنت_شروع"),
        ("کامنت_توقف",       "توقف کامنت‌گذار",               "کامنت_توقف",               "کامنت_توقف"),
        ("کامنت_آمار",       "آمار کامنت‌گذار",               "کامنت_آمار",               "کامنت_آمار"),
    ],

    "🧠 ویژگی‌های هوشمند": [
        ("ai",               "هوش مصنوعی آفلاین",             "ai [سوال]",                "ai تلگرام چیست؟"),
        ("کلون_شروع",        "شروع ضبط رفتار",                "کلون_شروع",                "کلون_شروع"),
        ("کلون_توقف",        "توقف ضبط و تحلیل",              "کلون_توقف",                "کلون_توقف"),
        ("کلون_اجرا",        "فعال/غیرفعال Clone",            "کلون_اجرا [روشن|خاموش]",  "کلون_اجرا روشن"),
        ("کلون_آمار",        "آمار Clone",                    "کلون_آمار",                "کلون_آمار"),
        ("کلون_پاک",         "پاک‌کردن داده Clone",           "کلون_پاک",                 "کلون_پاک"),
        ("میمیک",            "حالت میمیک (تقلید)",            "میمیک [روشن|خاموش]",       "میمیک روشن"),
        ("داستان",           "تولید داستان تصادفی",           "داستان",                   "داستان"),
        ("پیش‌بینی_پاسخ",    "پیش‌بینی پاسخ",                "پیش‌بینی_پاسخ [متن]",      "پیش‌بینی_پاسخ سلام"),
        ("زمینه_یاد",        "آموزش Context",                 "زمینه_یاد [متن]",          "زمینه_یاد من علیم"),
        ("زمینه_خودکار",     "Context خودکار",                "زمینه_خودکار [روشن|خاموش]","زمینه_خودکار روشن"),
        ("زمینه_آمار",       "آمار Context",                  "زمینه_آمار",               "زمینه_آمار"),
        ("زمینه_پاک",        "پاک‌کردن Context",              "زمینه_پاک",                "زمینه_پاک"),
        ("قانون_هدف",        "قانون Intent",                  "قانون_هدف [کلید]|[intent]","قانون_هدف خرید|commerce"),
        ("هدف_تشخیص",        "تشخیص Intent",                  "هدف_تشخیص [متن]",          "هدف_تشخیص چه قیمتی"),
        ("وضعیت_ست",         "تنظیم وضعیت چت",               "وضعیت_ست [کلید]|[مقدار]", "وضعیت_ست mood|happy"),
        ("وضعیت_نمایش",      "نمایش وضعیت چت",               "وضعیت_نمایش",             "وضعیت_نمایش"),
        ("وضعیت_پاک",        "پاک‌کردن وضعیت",               "وضعیت_پاک",               "وضعیت_پاک"),
        ("هدف",              "ثبت هدف شخصی",                  "هدف [عنوان]|[مقدار] [واحد]","هدف دویدن|30 روز"),
        ("هدف_پیشرفت",       "پیشرفت هدف",                   "هدف_پیشرفت [id] [مقدار]",  "هدف_پیشرفت 1 5"),
        ("هدف‌ها",           "لیست اهداف",                    "هدف‌ها",                   "هدف‌ها"),
        ("عادت",             "ثبت عادت",                      "عادت [عنوان]",             "عادت ورزش صبحانه"),
        ("عادت_انجام",       "علامت‌گذاری عادت",              "عادت_انجام [id]",          "عادت_انجام 1"),
        ("عادت‌ها",          "لیست عادت‌ها",                  "عادت‌ها",                  "عادت‌ها"),
        ("کپسول",            "کپسول زمانی",                   "کپسول [عنوان]|[محتوا]|[تاریخ]","کپسول آینده|سلام|1405/01/01"),
        ("کپسول‌ها",         "لیست کپسول‌ها",                 "کپسول‌ها",                 "کپسول‌ها"),
        ("کپسول_باز",        "باز کردن کپسول",                "کپسول_باز [id]",           "کپسول_باز 1"),
        ("دستاوردها",        "لیست دستاوردها",                "دستاوردها",                "دستاوردها"),
        ("دستاوردها_ریست",   "ریست دستاوردها",                "دستاوردها_ریست",           "دستاوردها_ریست"),
    ],

    "📥 رسانه و دانلود": [
        (".dl",              "دانلود ویدیو",                  ".dl [URL]",                ".dl https://youtube.com/..."),
        (".mp3",             "دانلود صدا MP3",                ".mp3 [URL]",               ".mp3 https://youtube.com/..."),
        (".info",            "اطلاعات ویدیو",                  ".info [URL]",              ".info https://youtube.com/..."),
        ("تاریخچه_دانلود",  "تاریخچه دانلودها",               "تاریخچه_دانلود",           "تاریخچه_دانلود"),
        ("پاک_کش_دانلود",   "پاک کردن کش دانلود",            "پاک_کش_دانلود",            "پاک_کش_دانلود"),
        ("مسیر_دانلود",     "تنظیم مسیر دانلود",              "مسیر_دانلود [مسیر]",       "مسیر_دانلود /sdcard/دانلود"),
        ("کیفیت_دانلود",    "کیفیت ویدیو",                   "کیفیت_دانلود [کیفیت]",     "کیفیت_دانلود 720p"),
    ],

    "📁 مدیریت فایل": [
        ("فایل_ذخیره",       "ذخیره فایل از ریپلای",          "فایل_ذخیره (ریپلای)",      "فایل_ذخیره"),
        ("فایل_لیست",        "لیست فایل‌های ذخیره‌شده",       "فایل_لیست",                "فایل_لیست"),
        ("فایل_ارسال",       "ارسال فایل ذخیره",              "فایل_ارسال [شماره] [@dest]","فایل_ارسال 1"),
        ("فایل_حذف",         "حذف فایل ذخیره",                "فایل_حذف [شماره]",         "فایل_حذف 1"),
        ("فایل_نهان",        "صندوق فایل (نهان)",             "فایل_نهان [دسته] (ریپلای)", "فایل_نهان مدارک"),
        ("فایل_نهان_لیست",   "لیست صندوق فایل",               "فایل_نهان_لیست [دسته]",    "فایل_نهان_لیست"),
        ("سیو",              "سیو پیام",                      "سیو (ریپلای)",             "سیو"),
        ("سیو_100",          "سیو ۱۰۰ پیام اخیر",             "سیو_100",                  "سیو_100"),
        ("لیست_سیو",         "لیست سیوها",                    "لیست_سیو",                 "لیست_سیو"),
        ("پاکسازی",          "پاکسازی هوشمند",                "پاکسازی [نوع]",            "پاکسازی لینک"),
    ],

    "🔐 امنیت": [
        ("صندوق_کلید",       "کلید رمزگذاری صندوق",           "صندوق_کلید [کلید]",        "صندوق_کلید Myp@ss123"),
        ("صندوق_ذخیره",      "ذخیره رمزگذاری‌شده",            "صندوق_ذخیره [نام]|[مقدار]","صندوق_ذخیره ایمیل|test@test.com"),
        ("صندوق_نمایش",      "رمزگشایی و نمایش",              "صندوق_نمایش [نام]",        "صندوق_نمایش ایمیل"),
        ("صندوق_لیست",       "لیست صندوق",                    "صندوق_لیست",               "صندوق_لیست"),
        ("صندوق_حذف",        "حذف از صندوق",                  "صندوق_حذف [نام]",          "صندوق_حذف ایمیل"),
        ("صندوق_وضعیت",      "وضعیت صندوق",                   "صندوق_وضعیت",              "صندوق_وضعیت"),
        ("قفل_کامل",         "قفل نوع محتوا",                 "قفل_کامل [نوع] [روشن|خاموش]","قفل_کامل لینک روشن"),
        ("وضعیت_قفل_کامل",   "وضعیت قفل‌ها",                  "وضعیت_قفل_کامل",          "وضعیت_قفل_کامل"),
        ("لیست_سفید_کلمه",   "لیست سفید کلمات",               "لیست_سفید_کلمه [کلمه]",   "لیست_سفید_کلمه ممنون"),
        ("لیست_سیاه_کلمه",   "لیست سیاه کلمات",               "لیست_سیاه_کلمه [کلمه]",   "لیست_سیاه_کلمه اسپم"),
        ("ریِد_روشن",         "فعال‌کردن Raid Detector",       "ریِد_روشن",                "ریِد_روشن"),
        ("ریِد_خاموش",        "خاموش‌کردن Raid Detector",      "ریِد_خاموش",               "ریِد_خاموش"),
        ("ریِد_تنظیم",        "حساسیت Raid",                   "ریِد_تنظیم [1-10]",         "ریِد_تنظیم 7"),
        ("ریِد_آمار",         "آمار حملات",                    "ریِد_آمار",                "ریِد_آمار"),
        ("ریِد_سفید",         "لیست سفید Raid",                "ریِد_سفید [@user]",        "ریِد_سفید @ali"),
        ("پنهان",            "پنهان‌کردن متن",                "پنهان [روکش]|[راز]",       "پنهان سلام|رمز: ۱۲۳"),
        ("آشکار",            "آشکار کردن متن پنهان",           "آشکار (ریپلای)",           "آشکار"),
        ("رمز_تولید",        "تولید رمز عبور",                "رمز_تولید [طول] [حالت]",   "رمز_تولید 20 قوی"),
    ],

    "👁 پایش و مانیتورینگ": [
        ("واچ",              "واچ آنلاین کاربر",              "واچ [@user]",              "واچ @ali"),
        ("واچ_حذف",          "حذف واچ",                       "واچ_حذف [@user]",          "واچ_حذف @ali"),
        ("لیست_واچ",         "لیست واچ‌ها",                   "لیست_واچ",                 "لیست_واچ"),
        ("اسنپ",             "اسنپ‌شات پروفایل",              "اسنپ [@user]",             "اسنپ @ali"),
        ("اسنپ_مقایسه",      "مقایسه دو اسنپ",                "اسنپ_مقایسه [@user]",      "اسنپ_مقایسه @ali"),
    ],

    "🔧 ابزارها": [
        ("حساب",             "ماشین حساب",                    "حساب [عبارت]",             "حساب 15*3+sin(0)"),
        ("تبدیل",            "مبدّل واحد",                    "تبدیل [عدد] [از] [به]",    "تبدیل 100 km mi"),
        ("تایمر",            "تایمر",                         "تایمر [ثانیه] [نام]",       "تایمر 60 یادآوری"),
        ("ترجمه",            "ترجمه آنلاین (Google)",          "ترجمه [متن]",              "ترجمه hello world"),
        ("ترجمه_به",         "ترجمه به زبان دلخواه",           "ترجمه_به [زبان] [متن]",    "ترجمه_به en سلام دنیا"),
        ("شمار",             "شمارش کلمات",                   "شمار (ریپلای)",            "شمار"),
        ("تصادفی",           "عدد تصادفی",                    "تصادفی [min] [max]",        "تصادفی 1 100"),
        ("انتخاب",           "انتخاب تصادفی",                 "انتخاب [گ۱,گ۲,...]",       "انتخاب پیتزا,برگر,ساندویچ"),
        ("نقل_قول",          "نقل قول تصادفی",                "نقل_قول",                  "نقل_قول"),
        ("شعر",              "شعر فارسی",                     "شعر",                      "شعر"),
        ("میم",              "میم تصادفی",                    "میم",                      "میم"),
        ("ابزارها",          "لیست ابزارها",                  "ابزارها",                  "ابزارها"),
        ("بهینه‌سازی_دیتابیس","بهینه‌سازی DB",                "بهینه‌سازی_دیتابیس",       "بهینه‌سازی_دیتابیس"),
    ],

    "📋 مدیریت کارها": [
        ("کار",              "ثبت کار جدید",                  "کار [توضیح]",              "کار خرید بازار"),
        ("کارها",            "لیست کارهای باز",               "کارها",                    "کارها"),
        ("کار_انجام",        "علامت انجام",                   "کار_انجام [شماره]",         "کار_انجام 1"),
        ("کار_حذف",          "حذف کار",                       "کار_حذف [شماره]",          "کار_حذف 1"),
        ("کارهای_انجام‌شده", "لیست کارهای انجام‌شده",         "کارهای_انجام‌شده",         "کارهای_انجام‌شده"),
        ("پاک_انجام‌شده",    "پاک کارهای انجام‌شده",          "پاک_انجام‌شده",            "پاک_انجام‌شده"),
        ("بوکمارک",          "بوکمارک پیام",                  "بوکمارک (ریپلای)",         "بوکمارک"),
        ("بوکمارک‌ها",       "لیست بوکمارک‌ها",              "بوکمارک‌ها",               "بوکمارک‌ها"),
        ("بوکمارک_حذف",      "حذف بوکمارک",                   "بوکمارک_حذف [id]",         "بوکمارک_حذف 1"),
        ("لایک",             "ذخیره علاقه‌مند",               "لایک (ریپلای)",            "لایک"),
        ("علاقه‌مندی‌ها",   "لیست علاقه‌مندی‌ها",            "علاقه‌مندی‌ها",           "علاقه‌مندی‌ها"),
        ("تاریخچه_جستجو",   "تاریخچه جستجوها",               "تاریخچه_جستجو",            "تاریخچه_جستجو"),
        ("ابزارها",          "منوی ابزارها",                  "ابزارها",                  "ابزارها"),
    ],

    "📅 تقویم": [
        ("تولد",             "ثبت تولد",                      "تولد [نام] [YYYY/MM/DD]",  "تولد علی 1370/05/15"),
        ("رویداد",           "ثبت رویداد",                    "رویداد [عنوان] [YYYY/MM/DD]","رویداد جلسه 1404/01/15"),
        ("تقویم",            "نمایش تقویم",                   "تقویم",                    "تقویم"),
        ("تقویم_امروز",      "رویداد امروز",                  "تقویم_امروز",              "تقویم_امروز"),
        ("تقویم_حذف",        "حذف رویداد",                    "تقویم_حذف [id]",           "تقویم_حذف 1"),
        ("تقویم_ماه",        "رویداد ماه جاری",               "تقویم_ماه",                "تقویم_ماه"),
    ],

    "💰 مدیریت هزینه": [
        ("هزینه",            "ثبت هزینه",                     "هزینه [عنوان] [مبلغ] [دسته]","هزینه غذا 50000 خوراک"),
        ("هزینه‌ها",         "لیست هزینه‌ها",                 "هزینه‌ها",                 "هزینه‌ها"),
        ("هزینه_ماه",        "هزینه ماه جاری",                "هزینه_ماه",                "هزینه_ماه"),
        ("هزینه_حذف",        "حذف هزینه",                     "هزینه_حذف [id]",           "هزینه_حذف 1"),
        ("هزینه_دسته",       "هزینه به دسته‌بندی",            "هزینه_دسته",               "هزینه_دسته"),
    ],

    "💾 بکاپ و ریستور": [
        ("بکاپ",             "بکاپ دیتابیس",                  "بکاپ",                     "بکاپ"),
        ("لیست_بکاپ",        "لیست بکاپ‌ها",                  "لیست_بکاپ",                "لیست_بکاپ"),
        ("ریستور",           "ریستور از بکاپ",                "ریستور [نام_فایل]",         "ریستور onyx_backup_...db"),
    ],

    "🧩 پلاگین": [
        ("افزونه‌ها",        "لیست پلاگین‌ها",                "افزونه‌ها",                "افزونه‌ها"),
        ("افزونه فعال",      "فعال‌کردن پلاگین",              "افزونه فعال [نام]",         "افزونه فعال myplugin"),
        ("افزونه غیرفعال",   "غیرفعال‌کردن پلاگین",           "افزونه غیرفعال [نام]",      "افزونه غیرفعال myplugin"),
    ],

    "✨ انیمیشن": [
        ("موشک",  "انیمیشن موشک",     "موشک",  "موشک"),
        ("قلب",   "انیمیشن قلب",      "قلب",   "قلب"),
        ("لودینگ","انیمیشن لودینگ",   "لودینگ","لودینگ"),
        ("ماتریکس","انیمیشن ماتریکس", "ماتریکس","ماتریکس"),
        ("آتش",   "انیمیشن آتش",      "آتش",   "آتش"),
        ("مسجد",  "انیمیشن مسجد",     "مسجد",  "مسجد"),
        ("عقاب",  "انیمیشن عقاب",     "عقاب",  "عقاب"),
        ("گل",    "انیمیشن گل",       "گل",    "گل"),
        ("مار",   "انیمیشن مار",      "مار",   "مار"),
        ("تصادف", "انیمیشن تصادف",    "تصادف", "تصادف"),
        ("دوچرخه","انیمیشن دوچرخه",  "دوچرخه","دوچرخه"),
        ("خواب",  "انیمیشن خواب",     "خواب",  "خواب"),
    ],

    "🎮 بازی‌ها": [
        ("مین_گیم تاس",  "بازی تاس",   "مین_گیم تاس",  "مین_گیم تاس"),
        ("مین_گیم ورق",  "بازی ورق",   "مین_گیم ورق",  "مین_گیم ورق"),
    ],
}

# ══════════════════════════════════════════════
#  هندلرهای منو
# ══════════════════════════════════════════════


# ── CONTACTS GLOBALS ──

CONTACT_STATUSES = {
    "love":    "❤️ عشق",
    "enemy":   "⚔️ دشمن",
    "silent":  "🤫 ساکت",
    "blocked": "🚫 بلاک",
    "normal":  "👤 عادی",
    "vip":     "⭐ VIP",
    "work":    "💼 کاری",
}
CONTACT_LABELS = {
    "family":   "🟢 خانواده",
    "friend":   "🔵 دوست",
    "customer": "🟠 مشتری",
    "annoying": "🔴 مزاحم",
    "blocked":  "⚫ بلاک",
    "colleague":"🟡 همکار",
}

# ── CRUD helpers ──────────────────────────────

def get_contact(uid: int) -> dict:
    with _db_lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM contacts WHERE uid=?", (uid,)
        ).fetchone()
    if row:
        d = dict(row)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except Exception:
            d["tags"] = []
        return d
    return {
        "uid": uid, "name": "", "username": "", "bio": "",
        "note": "", "score": 0, "status": "normal", "color": "",
        "phone": "", "birthday": "", "address": "", "job": "",
        "tags": [], "first_seen": jalali(), "last_msg": "", "msg_count": 0,
    }

def save_contact(data: dict) -> None:
    tags = json.dumps(data.get("tags", []), ensure_ascii=False)
    with _db_lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO contacts(uid,name,username,bio,note,score,status,color,
                phone,birthday,address,job,tags,first_seen,last_msg,msg_count)
            VALUES(:uid,:name,:username,:bio,:note,:score,:status,:color,
                :phone,:birthday,:address,:job,:tags,:first_seen,:last_msg,:msg_count)
            ON CONFLICT(uid) DO UPDATE SET
                name=excluded.name, username=excluded.username, bio=excluded.bio,
                note=excluded.note, score=excluded.score, status=excluded.status,
                color=excluded.color, phone=excluded.phone, birthday=excluded.birthday,
                address=excluded.address, job=excluded.job, tags=excluded.tags,
                first_seen=excluded.first_seen, last_msg=excluded.last_msg,
                msg_count=excluded.msg_count
        """, {**data, "tags": tags})
        conn.commit()

def log_contact_change(uid: int, field: str, old_val: str, new_val: str) -> None:
    with _db_lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO contact_history(uid,field,old_val,new_val,ts) VALUES(?,?,?,?,?)",
            (uid, field, old_val, new_val, now_str())
        )
        conn.commit()

def incr_msg_count(uid: int, name: str = "", username: str = "") -> None:
    with _db_lock:
        conn = get_conn()
        existing = conn.execute("SELECT * FROM contacts WHERE uid=?", (uid,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE contacts SET msg_count=msg_count+1, last_msg=? WHERE uid=?",
                (now_str(), uid)
            )
        else:
            conn.execute(
                "INSERT INTO contacts(uid,name,username,first_seen,last_msg,msg_count) "
                "VALUES(?,?,?,?,?,1)",
                (uid, name[:60], username[:60], jalali(), now_str())
            )
        conn.commit()

async def resolve_user(client, event, arg: str = None):
    try:
        if arg:
            return await client.get_entity(arg.lstrip("@"))
        reply = await event.get_reply_message()
        if reply:
            return await reply.get_sender()
    except Exception as e:
        logger.debug(f"resolve_user: {e}")
    return None

# ── Handler factory ───────────────────────────


# ── AUTOMATION GLOBALS ──
from collections import defaultdict

# ── حالت‌های سراسری ──────────────────────────
_busy_replied: set = set()
_busy_active: bool = False
_busy_text: str = "🤖 الان مشغولم، بعداً پیام بده!"

_ads_running: bool = False
_ads_task: Optional[asyncio.Task] = None

_spam_running: bool = False
_spam_task: Optional[asyncio.Task] = None

_comment_running: bool = False
_comment_task: Optional[asyncio.Task] = None

_sleep_mode: bool = False
_panic_mode: bool = False

# ── Smart Queue ───────────────────────────────
_queue_task: Optional[asyncio.Task] = None

# ── Private helpers ───────────────────────────

def _get_busy_text() -> str:
    with _db_lock:
        conn = get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key='busy_text'").fetchone()
    return row["value"] if row else "🤖 الان مشغولم، بعداً پیام بده!"

async def _broadcast_loop(client, ad_text: str, groups: list, interval: int) -> None:
    while _ads_running:
        for g in groups:
            if not _ads_running:
                break
            try:
                await client.send_message(g, ad_text)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.warning(f"📢 {g}: {e}")
            await asyncio.sleep(3)
        await asyncio.sleep(interval)

def _parse_steps(raw: str) -> list:
    steps = []
    for part in raw.split("|"):
        part = part.strip()
        if ":" in part:
            t, v = part.split(":", 1)
            steps.append({"type": t.strip().lower(), "value": v.strip()})
        else:
            steps.append({"type": "msg", "value": part})
    return steps

async def _execute_workflow(client, steps: list, chat_id: int) -> None:
    for i, step in enumerate(steps):
        try:
            st = step.get("type", "")
            sv = step.get("value", "")
            if st == "msg":
                await client.send_message(chat_id, sv)
            elif st == "send":
                parts = sv.split(":", 1)
                if len(parts) == 2:
                    await client.send_message(parts[0].strip(), parts[1].strip())
            elif st == "wait":
                await asyncio.sleep(float(sv) if sv else 5)
            elif st == "name":
                await client(UpdateProfileRequest(first_name=sv))
            elif st == "bio":
                await client(UpdateProfileRequest(about=sv))
            elif st == "log":
                logger.info(f"🔄 [LOG] {sv}")
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning(f"🔄 گام {i+1}: {e}")

async def _comment_loop(client, channel: str, texts: list) -> None:
    with _db_lock:
        conn = get_conn()
        cnt_row = conn.execute("SELECT value FROM comment_config WHERE key='count'").fetchone()
        cnt = int(cnt_row["value"]) if cnt_row else 0
    last_id = 0
    while _comment_running:
        try:
            async for msg in client.iter_messages(channel, limit=5):
                if msg.id > last_id and msg.replies:
                    last_id = msg.id
                    text = random.choice(texts)
                    await client.send_message(channel, text, comment_to=msg.id)
                    cnt += 1
                    with _db_lock:
                        conn = get_conn()
                        conn.execute("INSERT INTO comment_config(key,value) VALUES('count',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(cnt),))
                        conn.commit()
                    await asyncio.sleep(random.randint(10, 30))
        except Exception as e:
            logger.debug(f"Comment loop: {e}")
        await asyncio.sleep(60)

async def smart_queue_runner(client) -> None:
    """Task پردازش صف هوشمند"""
    while True:
        try:
            now_s = iran_now().strftime("%Y/%m/%d %H:%M:%S")
            with _db_lock:
                conn = get_conn()
                rows = conn.execute(
                    "SELECT * FROM smart_queue WHERE done=0 AND send_at<=? LIMIT 10",
                    (now_s,)
                ).fetchall()
            for r in rows:
                try:
                    await client.send_message(r["target"], r["text"])
                except Exception as e:
                    logger.warning(f"Queue send: {e}")
                with _db_lock:
                    conn = get_conn()
                    conn.execute("UPDATE smart_queue SET done=1 WHERE id=?", (r["id"],))
                    conn.commit()
        except Exception as e:
            logger.debug(f"Queue runner: {e}")
        await asyncio.sleep(30)


# ── ANALYTICS GLOBALS ──

# ── state ─────────────────────────────────────
_context_active: bool = False
_context_data: dict = defaultdict(list)  # chat_id → list of msgs


# ── SECURITY GLOBALS ──
from typing import Dict, Set

# ── ریِد دتکتور ───────────────────────────────
_raid_active: bool = False
_raid_sensitivity: int = 5
_raid_msg_window: Dict[int, list] = defaultdict(list)
_raid_user_window: Dict[int, Set[int]] = defaultdict(set)
_raid_whitelist: Set[int] = set()

# ── قفل‌های کامل ──────────────────────────────
_LOCK_TYPES = {
    "لینک":     "link",
    "فوروارد":  "forward",
    "رسانه":    "media",
    "فایل":     "file",
    "صدا":      "voice",
    "استیکر":   "sticker",
    "گیف":      "gif",
}

def _lock_active(lock_type: str) -> bool:
    with _db_lock:
        conn = get_conn()
        row = conn.execute("SELECT active FROM full_locks WHERE lock_type=?", (lock_type,)).fetchone()
    return bool(row and row["active"])

def _raid_thresholds() -> tuple:
    return max(3, 15 - _raid_sensitivity), max(2, 8 - _raid_sensitivity // 2)


# ── PROFILE GLOBALS ──
from typing import Optional

# ── ساعت — اصلاح‌شده V9 ──────────────────────
_clock_task: Optional[asyncio.Task] = None

def _clock_is_active() -> bool:
    """بررسی وضعیت ساعت از دیتابیس"""
    return setting("clock_active", "0") == "1"

def _clock_set_active(val: bool) -> None:
    """ذخیره وضعیت ساعت در دیتابیس"""
    set_setting("clock_active", "1" if val else "0")

# ── async loop ────────────────────────────────
async def _clock_loop(client) -> None:
    """حلقه اصلی ساعت — با persistence و error recovery"""
    logger.info("⏰ ساعت ایران شروع شد")
    _clock_set_active(True)
    consecutive_errors = 0
    while True:
        try:
            now = iran_now()
            time_str = now.strftime("%H:%M")
            secs_str = now.strftime("%H:%M:%S")
            date_str = jalali(now)
            weekday  = jalali_weekday(now)
            with _db_lock:
                conn = get_conn()
                row = conn.execute("SELECT value FROM settings WHERE key='clock_font'").fetchone()
            fn = row["value"] if row else "normal"
            # اعتبارسنجی فونت
            if fn not in CLOCK_FONTS:
                fn = "normal"
            display = apply_clock_font(time_str, fn)
            with _db_lock:
                conn = get_conn()
                suffix_row = conn.execute("SELECT value FROM settings WHERE key='clock_suffix'").fetchone()
            suffix = suffix_row["value"] if suffix_row else ""
            await client(UpdateProfileRequest(
                first_name=f"⏰ {display}{suffix}",
                about=f"📅 {date_str} | {weekday}\n🕐 {secs_str}\n{WATERMARK}"
            ))
            consecutive_errors = 0
        except FloodWaitError as e:
            await asyncio.sleep(min(e.seconds, 300))
        except asyncio.CancelledError:
            break
        except Exception as e:
            consecutive_errors += 1
            logger.warning(f"⏰ خطای ساعت ({consecutive_errors}): {e}")
            if consecutive_errors >= 5:
                logger.error("⏰ ساعت به دلیل خطاهای متوالی متوقف شد")
                break
            await asyncio.sleep(min(60 * consecutive_errors, 300))
            continue
        await asyncio.sleep(60)
    _clock_set_active(False)
    logger.info("⏰ ساعت متوقف شد")



# ── MEDIA GLOBALS ──
import tempfile
import subprocess
import io

# ── state ─────────────────────────────────────
_active_downloads: dict = {}   # task_id → task

# ── Private helpers ───────────────────────────
async def _do_download(event, url: str, mode: str) -> None:
    # already imported globally _db_lock, DL_DIR, now_str, profile_incr
    with _db_lock:
        conn = get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key='dl_quality'").fetchone()
    quality = row["value"] if row else "best"
    with _db_lock:
        conn = get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key='dl_path'").fetchone()
    out_dir = row["value"] if row else DL_DIR

    try:
        if mode == "audio":
            fmt = "bestaudio/best"
            ext_opts = ["-x", "--audio-format", "mp3"]
        else:
            if quality == "best":
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            elif quality == "1080p":
                fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]"
            elif quality == "720p":
                fmt = "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]"
            elif quality == "480p":
                fmt = "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]"
            else:
                fmt = "best"
            ext_opts = []

        output = os.path.join(out_dir, "%(title).50s.%(ext)s")
        cmd = ["yt-dlp", "-f", fmt, "-o", output] + ext_opts + ["--no-playlist", url]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            await safe_edit(event, "❌ زمان دانلود تمام شد!")
            return

        if proc.returncode == 0:
            # پیدا کردن فایل دانلود شده
            files = sorted(
                [f for f in os.listdir(out_dir) if os.path.getmtime(os.path.join(out_dir, f)) > (asyncio.get_event_loop().time() - 400)],
                key=lambda f: os.path.getmtime(os.path.join(out_dir, f)),
                reverse=True
            )
            if files:
                fpath = os.path.join(out_dir, files[0])
                fsize = os.path.getsize(fpath)
                with _db_lock:
                    conn = get_conn()
                    conn.execute("INSERT INTO dl_history(url,title,size,status,ts) VALUES(?,?,?,?,?)",
                                 (url[:200], files[0][:100], fsize, "ok", now_str()))
                    conn.commit()
                profile_incr("downloads")
                await safe_edit(event, box("✅ دانلود موفق", [
                    f"فایل: {files[0][:40]}",
                    f"حجم: {fsize//1024}KB",
                    f"مسیر: {fpath[:50]}",
                ]))
                # ارسال به تلگرام اگر کوچکتر از 50MB
                if fsize < 50 * 1024 * 1024:
                    try:
                        await client.send_file(event.chat_id, fpath,
                                               caption=f"💎 ONYX | {files[0][:40]}")
                    except Exception as e:
                        logger.warning(f"DL send: {e}")
            else:
                await safe_edit(event, "⚠️ فایل دانلود شد اما پیدا نشد.")
        else:
            err_text = err.decode(errors="ignore")[-300:]
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO dl_history(url,title,size,status,ts) VALUES(?,?,?,?,?)",
                             (url[:200], "خطا", 0, "fail", now_str()))
                conn.commit()
            await safe_edit(event, f"❌ خطای دانلود:\n{err_text}")

    except FileNotFoundError:
        await safe_edit(event, "❌ yt-dlp نصب نیست!\nنصب: pip install yt-dlp")
    except Exception as e:
        logger.error(f"Download: {e}")
        await safe_edit(event, f"❌ {e}")


# ── SMART GLOBALS ──
from typing import Dict, List, Optional

# ══ Clone ════════════════════════════════════
_clone_recording: bool = False
_clone_active: bool    = False
_clone_stats: dict = {
    "avg_delay": 2.5, "emoji_rate": 0.3, "avg_length": 20,
    "active_hours": [], "common_words": [],
    "greeting_style": "سلام", "farewell_style": "خداحافظ",
}
_FA_EMOJIS = ["❤️","😊","🙏","👍","🌹","✨","💪","🔥","😂","🤣"]

# ══ Context ══════════════════════════════════
_context_auto: bool = False
_context_window: Dict[int, list] = defaultdict(list)

# ══ AI ═══════════════════════════════════════
AI_RESPONSES: Dict[str, list] = {
    "سلام":["سلام! چطور می‌تونم کمکت کنم؟ 😊","هی! خوبی؟ 👋","درود! 🌟"],
    "خوبی":["ممنون، خوبم! تو چطوری؟ 😊","عالی! چطور کمکت کنم؟","سرحالم! 😄"],
    "ممنون":["خواهش می‌کنم! 🙏","خوشحالم کمک کردم ❤️","وظیفه‌ام بود 💫"],
    "برنامه":["برنامه‌نویسی علم فوق‌العاده‌ایه! 💻","Python برای شروع عالیه 🐍"],
    "python":["Python یکی از محبوب‌ترین زبان‌هاست! 🐍","با Python هر کاری می‌شه کرد!"],
    "هوش مصنوعی":["AI آینده تکنولوژیه! 🤖","دنیای AI هر روز پیشرفت می‌کنه ✨"],
    "عشق":["عشق یه احساس قشنگه ❤️","عشق واقعی نادره، قدرش رو بدون 🌹"],
    "زندگی":["زندگی کوتاهه، هر لحظه‌ش رو قدر بدون 🌟","هر روز یه صفحه جدیده ✍️"],
    "موسیقی":["موسیقی روح رو تغذیه می‌کنه 🎵","هر ژانری دنیای خودش رو داره 🎸"],
    "ورزش":["ورزش = سلامتی + شادی 💪","هر روز یه کم ورزش کن! 🏃"],
    "غذا":["غذای خوب = روز خوب 🍽️","هیچ مشکلی نیست که یه غذای خوب حلش نکنه 😋"],
    "تلگرام":["تلگرام بهترین پیام‌رسانه! ✈️","Telethon API قدرتمندی داره 🚀"],
    "default":["سوال جالبیه! 🤔","این موضوع پیچیده‌ست 🧠","جالبه! 💡",
               "می‌تونی بیشتر توضیح بدی؟ 💬","پاسخ به دیدگاه آدم بستگی داره 🎭"],
}

_INTENT_RULES: Dict[str, str] = {}

def _detect_intent(text: str) -> tuple:
    tl = text.lower()
    scores = defaultdict(float)
    for kws, intent in _INTENT_RULES.items():
        for kw in kws.split("|"):
            if kw.strip() in tl:
                scores[intent] += 1.0 / max(1, len(kws.split("|")))
    built_in = {
        "greeting": ["سلام","درود","هلو","صبح","شب","خوبی"],
        "farewell":  ["خداحافظ","بای","شب بخیر","خوش"],
        "question":  ["چطور","چرا","کجا","چی","کی","آیا","؟"],
        "positive":  ["ممنون","عالی","خوب","آفرین","مرسی"],
        "negative":  ["بد","مشکل","خطا","اشتباه","نه","نمی"],
    }
    for intent, keywords in built_in.items():
        for kw in keywords:
            if kw in tl:
                scores[intent] += 0.5
    if not scores:
        return "unknown", 0.0
    best = max(scores, key=scores.get)
    return best, min(1.0, scores[best])

def _ai_respond(text: str) -> str:
    tl = text.lower()
    for kw, resps in AI_RESPONSES.items():
        if kw in tl:
            return random.choice(resps)
    return random.choice(AI_RESPONSES["default"])

def _analyze_clone_data(data: list) -> None:
    if not data:
        return
    delays, ec, tc, hours, all_words = [], 0, 0, [], []
    for i, entry in enumerate(data):
        text = entry.get("text", "")
        tc  += len(text)
        if sum(1 for c in text if ord(c) > 0x1F300) > 0:
            ec += 1
        if "ts" in entry:
            try:
                dt = datetime.datetime.fromisoformat(entry["ts"])
                hours.append(dt.hour)
                if i > 0 and "ts" in data[i-1]:
                    dt2 = datetime.datetime.fromisoformat(data[i-1]["ts"])
                    d = (dt - dt2).total_seconds()
                    if 0 < d < 3600:
                        delays.append(d)
            except Exception:
                pass
        all_words.extend(text.split())
    if delays:
        _clone_stats["avg_delay"] = sum(delays) / len(delays)
    if data:
        _clone_stats["emoji_rate"] = ec / len(data)
        _clone_stats["avg_length"] = tc / max(len(data), 1)
    stop = {"که","در","به","از","با","این","آن","را","می","است","بود","یک","هم"}
    wf = defaultdict(int)
    for w in all_words:
        if len(w) > 2 and w not in stop:
            wf[w] += 1
    _clone_stats["common_words"] = sorted(wf, key=wf.get, reverse=True)[:15]

def _gen_clone_resp(text: str) -> str:
    greets = ["سلام","درود","هلو","خوبی","hi","hello"]
    farews = ["خداحافظ","بای","شب بخیر","bye"]
    tl = text.lower()
    if any(g in tl for g in greets):
        base = _clone_stats["greeting_style"]
    elif any(f in tl for f in farews):
        base = _clone_stats["farewell_style"]
    elif _clone_stats["common_words"]:
        base = " ".join(random.sample(_clone_stats["common_words"],
                                      min(3, len(_clone_stats["common_words"]))))
    else:
        base = random.choice(["باشه","اوکی","متوجه","درسته","آره","ممنون"])
    if random.random() < _clone_stats["emoji_rate"]:
        base += f" {random.choice(_FA_EMOJIS)}"
    return base


async def achievement_checker_loop(client) -> None:
    """loop بررسی دستاوردها"""
    while True:
        try:
            with _db_lock:
                conn = get_conn()
                unlocked = {r["id"] for r in conn.execute("SELECT id FROM achievements").fetchall()}
            new_unlocks = []
            for aid, ach in {
                "first_cmd": ("🏆 اولین دستور", lambda: profile_val("cmds_executed") >= 1),
                "cmd_10":    ("🥈 ۱۰ دستور",    lambda: profile_val("cmds_executed") >= 10),
                "cmd_100":   ("🥇 ۱۰۰ دستور",   lambda: profile_val("cmds_executed") >= 100),
                "level_5":   ("⭐ سطح ۵",        lambda: profile_val("level") >= 5),
                "level_10":  ("🌟 سطح ۱۰",       lambda: profile_val("level") >= 10),
                "active_7":  ("📅 ۷ روز فعال",   lambda: profile_val("active_days") >= 7),
                "downloader":("📥 اولین دانلود", lambda: profile_val("downloads") >= 1),
            }.items():
                title_fn = ach
                if aid not in unlocked and title_fn[1]():
                    with _db_lock:
                        conn = get_conn()
                        conn.execute("INSERT OR IGNORE INTO achievements(id,title,ts) VALUES(?,?,?)",
                                     (aid, title_fn[0], now_str()))
                        conn.commit()
                    new_unlocks.append(title_fn[0])
            if new_unlocks:
                me = await client.get_me()
                for title in new_unlocks:
                    await client.send_message(me.id, f"🏆 دستاورد جدید!\n{title}")
        except Exception as e:
            logger.debug(f"Achievements: {e}")
        await asyncio.sleep(300)


# ── MONITORING GLOBALS ──
from typing import Optional, Set

async def online_notifier_loop(client) -> None:
    """loop بررسی دوره‌ای وضعیت کاربران واچ"""
    while True:
        try:
            with _db_lock:
                conn = get_conn()
                rows = conn.execute("SELECT uid FROM online_watch WHERE active=1").fetchall()
            for row in rows:
                try:
                    u = await client.get_entity(row["uid"])
                    status = type(u.status).__name__ if hasattr(u, "status") else "unknown"
                    with _db_lock:
                        conn = get_conn()
                        last = conn.execute(
                            "SELECT status FROM online_log WHERE uid=? ORDER BY id DESC LIMIT 1",
                            (u.id,)
                        ).fetchone()
                    if not last or last["status"] != status:
                        with _db_lock:
                            conn = get_conn()
                            conn.execute("INSERT INTO online_log(uid,status,ts) VALUES(?,?,?)",
                                         (u.id, status, now_str()))
                            conn.commit()
                except Exception:
                    pass
            await asyncio.sleep(60)
        except Exception as e:
            logger.debug(f"Online notifier: {e}")
            await asyncio.sleep(120)


# ── TOOLS GLOBALS ──



# ══════════════════════════════════════════════════════
#  ═══  REGISTER ALL HANDLERS  ═══
# ══════════════════════════════════════════════════════


# ══ V7 Globals & Helpers ══
"""
══════════════════════════════════════════════
 💎 ONYX SELF V7 PRO'S — HANDLERS PART 1
 🧠 Intelligence | 📊 Analytics | 👥 Contacts | 💬 Messaging
══════════════════════════════════════════════
"""

# ════════════════════════════════════════════════
#  V7 Global States
# ════════════════════════════════════════════════
_guess_game: dict = {}          # chat_id → {number, min, max, tries}
_blackjack_game: dict = {}      # chat_id → {hand, dealer, bet, deck}
_typing_challenge: dict = {}    # chat_id → {text, started}
_daily_puzzle_cache: dict = {}  # date → puzzle

_v7_mention_keywords: list = []  # loaded from DB on start

_V7_SCHEMA = """
    CREATE TABLE IF NOT EXISTS shadow_profiles (
        uid      INTEGER PRIMARY KEY,
        data     TEXT    DEFAULT '{}',
        updated  TEXT    DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS memory_book (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        memory  TEXT    NOT NULL,
        context TEXT    DEFAULT '',
        ts      TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_mb_uid ON memory_book(uid);
    CREATE TABLE IF NOT EXISTS on_this_day (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        date_md TEXT    NOT NULL,
        text    TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS smart_reminders (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        text    TEXT    NOT NULL,
        target  TEXT    DEFAULT 'me',
        fire_at TEXT    NOT NULL,
        done    INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS fav_contacts (
        uid     INTEGER PRIMARY KEY,
        note    TEXT    DEFAULT '',
        added   TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ignore_list (
        uid     INTEGER PRIMARY KEY,
        reason  TEXT    DEFAULT '',
        added   TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS auto_nicknames (
        uid      INTEGER PRIMARY KEY,
        nickname TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS waiting_tracker (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        context TEXT    NOT NULL,
        started TEXT    NOT NULL,
        done    INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS profile_timeline (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        uid     INTEGER NOT NULL,
        field   TEXT    NOT NULL,
        value   TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS quick_replies (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        shortcut TEXT   NOT NULL UNIQUE,
        text    TEXT    NOT NULL,
        used    INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS drafts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        title   TEXT    NOT NULL,
        content TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS passwords (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        site     TEXT    NOT NULL,
        username TEXT    DEFAULT '',
        password TEXT    NOT NULL,
        note     TEXT    DEFAULT '',
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS cmd_scheduler (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT    NOT NULL,
        cmd      TEXT    NOT NULL,
        run_at   TEXT    NOT NULL,
        repeat   TEXT    DEFAULT 'once',
        last_run TEXT    DEFAULT '',
        active   INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS mention_alerts (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT    NOT NULL,
        chat_id INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS collections (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT    NOT NULL,
        title    TEXT    NOT NULL,
        content  TEXT    DEFAULT '',
        tags     TEXT    DEFAULT '[]',
        ts       TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_col_cat ON collections(category);
    CREATE TABLE IF NOT EXISTS streaks (
        key      TEXT PRIMARY KEY,
        current  INTEGER DEFAULT 0,
        best     INTEGER DEFAULT 0,
        last_day TEXT    DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS activity_log (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        type    TEXT    NOT NULL,
        value   INTEGER DEFAULT 1,
        ts      TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_act_ts ON activity_log(ts);
    CREATE TABLE IF NOT EXISTS vpn_configs (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT    NOT NULL,
        content   TEXT    NOT NULL,
        server    TEXT    DEFAULT '',
        protocol  TEXT    DEFAULT '',
        tags      TEXT    DEFAULT '[]',
        favorite  INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        last_used TEXT    DEFAULT '',
        latency   INTEGER DEFAULT 0,
        fingerprint TEXT  DEFAULT '',
        ts        TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vpn_config_lab (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        config_id INTEGER NOT NULL,
        action   TEXT    NOT NULL,
        result   TEXT    DEFAULT '',
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS vpn_rotation (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        config_id INTEGER NOT NULL,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        category    TEXT    DEFAULT 'عمومی',
        price       INTEGER DEFAULT 0,
        description TEXT    DEFAULT '',
        stock       INTEGER DEFAULT 0,
        active      INTEGER DEFAULT 1,
        ts          TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_configs (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        content    TEXT    NOT NULL,
        sold       INTEGER DEFAULT 0,
        order_id   INTEGER DEFAULT 0,
        ts         TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_orders (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        order_uid   TEXT    NOT NULL UNIQUE,
        uid         INTEGER NOT NULL,
        username    TEXT    DEFAULT '',
        name        TEXT    DEFAULT '',
        product_id  INTEGER NOT NULL,
        product_name TEXT   DEFAULT '',
        price       INTEGER DEFAULT 0,
        status      TEXT    DEFAULT 'pending',
        receipt_file TEXT   DEFAULT '',
        config_id   INTEGER DEFAULT 0,
        coupon      TEXT    DEFAULT '',
        ts          TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_so_uid ON store_orders(uid);
    CREATE INDEX IF NOT EXISTS idx_so_status ON store_orders(status);
    CREATE TABLE IF NOT EXISTS store_coupons (
        code     TEXT PRIMARY KEY,
        discount INTEGER DEFAULT 0,
        uses     INTEGER DEFAULT 0,
        max_uses INTEGER DEFAULT 100,
        active   INTEGER DEFAULT 1,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS waiting_list (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        uid        INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        ts         TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS store_settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS store_order_history (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        order_uid TEXT    NOT NULL,
        action    TEXT    NOT NULL,
        note      TEXT    DEFAULT '',
        ts        TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_soh_order ON store_order_history(order_uid);
    CREATE TABLE IF NOT EXISTS customer_states (
        uid        INTEGER PRIMARY KEY,
        state      TEXT    DEFAULT 'idle',
        product_id INTEGER DEFAULT 0,
        order_uid  TEXT    DEFAULT '',
        data       TEXT    DEFAULT '{}',
        updated    TEXT    DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS store_triggers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        word       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        product_id INTEGER DEFAULT 0,
        action     TEXT    DEFAULT 'browse',
        active     INTEGER DEFAULT 1,
        ts         TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS crm_customers (
        uid            INTEGER PRIMARY KEY,
        name           TEXT    DEFAULT '',
        username       TEXT    DEFAULT '',
        total_spent    INTEGER DEFAULT 0,
        purchase_count INTEGER DEFAULT 0,
        vip_level      INTEGER DEFAULT 0,
        first_purchase TEXT    DEFAULT '',
        last_purchase  TEXT    DEFAULT '',
        renewal_date   TEXT    DEFAULT '',
        country        TEXT    DEFAULT '',
        notes          TEXT    DEFAULT '',
        blacklisted    INTEGER DEFAULT 0,
        whitelisted    INTEGER DEFAULT 0,
        coupons        TEXT    DEFAULT '[]',
        tags           TEXT    DEFAULT '[]',
        warnings       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS crm_campaigns (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT    NOT NULL,
        template  TEXT    NOT NULL,
        target    TEXT    DEFAULT 'all',
        status    TEXT    DEFAULT 'draft',
        sent      INTEGER DEFAULT 0,
        scheduled TEXT    DEFAULT '',
        ts        TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS campaign_history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        uid         INTEGER NOT NULL,
        status      TEXT    DEFAULT 'sent',
        ts          TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS support_tickets (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        uid        INTEGER NOT NULL,
        username   TEXT    DEFAULT '',
        name       TEXT    DEFAULT '',
        subject    TEXT    NOT NULL,
        status     TEXT    DEFAULT 'open',
        priority   TEXT    DEFAULT 'normal',
        assigned   TEXT    DEFAULT '',
        ts         TEXT    NOT NULL,
        closed_ts  TEXT    DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        uid       INTEGER NOT NULL,
        text      TEXT    NOT NULL,
        is_admin  INTEGER DEFAULT 0,
        ts        TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_tm_ticket ON ticket_messages(ticket_id);
    CREATE TABLE IF NOT EXISTS economy (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT '0'
    );
    CREATE TABLE IF NOT EXISTS shop_items (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT    NOT NULL,
        price    INTEGER NOT NULL,
        effect   TEXT    DEFAULT '',
        category TEXT    DEFAULT 'عمومی',
        active   INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS inventory (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id  INTEGER NOT NULL,
        qty      INTEGER DEFAULT 1,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS coin_txns (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        amount  INTEGER NOT NULL,
        reason  TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS virtual_pet (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS virtual_house (
        room  TEXT PRIMARY KEY,
        items TEXT DEFAULT '[]',
        level INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS skill_tree (
        skill    TEXT PRIMARY KEY,
        level    INTEGER DEFAULT 0,
        max_level INTEGER DEFAULT 5,
        xp       INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS quests (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        title     TEXT    NOT NULL,
        target    INTEGER NOT NULL,
        current   INTEGER DEFAULT 0,
        reward    INTEGER DEFAULT 50,
        active    INTEGER DEFAULT 1,
        done      INTEGER DEFAULT 0,
        ts        TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS badges (
        id    TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        emoji TEXT DEFAULT '🏅',
        ts    TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS boss_fight (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS mystery_boxes (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        opened  INTEGER DEFAULT 0,
        reward  TEXT    DEFAULT '',
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS lab_experiments (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT    NOT NULL,
        input   TEXT    NOT NULL,
        output  TEXT    DEFAULT '',
        status  TEXT    DEFAULT 'pending',
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS leaderboard (
        uid    INTEGER PRIMARY KEY,
        name   TEXT    DEFAULT '',
        score  INTEGER DEFAULT 0,
        updated TEXT   DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS search_history (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        query   TEXT    NOT NULL,
        results INTEGER DEFAULT 0,
        ts      TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS archives (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT    DEFAULT 'عمومی',
        title    TEXT    NOT NULL,
        content  TEXT    NOT NULL,
        ts       TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS daily_reward (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS mission_log (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        mission TEXT    NOT NULL,
        result  TEXT    NOT NULL,
        ts      TEXT    NOT NULL
    );
"""

def _v7_init_schema(conn):
    """اجرای schema جدول‌های V7"""
    conn.executescript(_V7_SCHEMA)
    conn.commit()


# ── Store helper functions ──────────────────────────────

def _store_setting(key: str, default: str = "") -> str:
    """دریافت تنظیم فروشگاه"""
    with _db_lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT value FROM store_settings WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row else default

def _store_set(key: str, value: str) -> None:
    """ذخیره تنظیم فروشگاه"""
    with _db_lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO store_settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()

def _gen_order_id() -> str:
    """تولید شناسه یکتا برای سفارش"""
    ts = iran_now().strftime("%y%m%d%H%M%S")
    rnd = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{ts}-{rnd}"

def _crm_update(uid: int, amount: int, product_name: str) -> None:
    """به‌روزرسانی CRM پس از تایید سفارش"""
    with _db_lock:
        conn = get_conn()
        existing = conn.execute(
            "SELECT * FROM crm_customers WHERE uid=?", (uid,)
        ).fetchone()
        now = now_str()
        if existing:
            conn.execute(
                "UPDATE crm_customers SET "
                "total_spent=total_spent+?, "
                "purchase_count=purchase_count+1, "
                "last_purchase=? "
                "WHERE uid=?",
                (amount, now, uid)
            )
        else:
            conn.execute(
                "INSERT INTO crm_customers(uid,total_spent,purchase_count,first_purchase,last_purchase) "
                "VALUES(?,?,1,?,?)",
                (uid, amount, now, now)
            )
        # به‌روزرسانی سطح VIP
        row = conn.execute("SELECT purchase_count, total_spent FROM crm_customers WHERE uid=?", (uid,)).fetchone()
        if row:
            pc = row["purchase_count"]
            ts = row["total_spent"]
            vip = 0
            if pc >= 10 or ts >= 5000000:
                vip = 3  # الماس
            elif pc >= 5 or ts >= 2000000:
                vip = 2  # طلا
            elif pc >= 2 or ts >= 500000:
                vip = 1  # نقره
            conn.execute("UPDATE crm_customers SET vip_level=? WHERE uid=?", (vip, uid))
        conn.commit()

# ── VPN Config helper functions ──────────────────────────

def _config_fingerprint(content: str) -> str:
    """تولید اثرانگشت یکتا برای کانفیگ"""
    import hashlib
    normalized = content.strip().lower()
    return hashlib.md5(normalized.encode("utf-8", errors="ignore")).hexdigest()[:16]

def _detect_protocol(content: str) -> str:
    """تشخیص پروتکل کانفیگ"""
    cl = content.lower()
    if "vmess://" in cl:
        return "VMess"
    elif "vless://" in cl:
        return "VLess"
    elif "trojan://" in cl:
        return "Trojan"
    elif "ss://" in cl:
        return "Shadowsocks"
    elif "ssr://" in cl:
        return "ShadowsocksR"
    elif "hysteria" in cl:
        return "Hysteria"
    elif "tuic://" in cl:
        return "TUIC"
    elif "wireguard" in cl or "[interface]" in cl:
        return "WireGuard"
    elif "[peer]" in cl:
        return "WireGuard"
    elif "socks5://" in cl:
        return "SOCKS5"
    elif "http://" in cl or "https://" in cl:
        return "HTTP"
    else:
        return "نامشخص"

def _extract_server(content: str) -> str:
    """استخراج آدرس سرور از کانفیگ"""
    import re as _re
    # VMess/VLess/Trojan URL
    m = _re.search(r'@([a-zA-Z0-9.\-]+):', content)
    if m:
        return m.group(1)
    # IP:Port pattern
    m = _re.search(r'"add"\s*:\s*"([^"]+)"', content)
    if m:
        return m.group(1)
    m = _re.search(r'Endpoint\s*=\s*([a-zA-Z0-9.\-:]+)', content)
    if m:
        return m.group(1).split(":")[0]
    # Generic IP
    m = _re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', content)
    if m:
        return m.group(1)
    return "—"

def _get_coins() -> int:
    return int(db_get("economy", "coins", "0"))

def _add_coins(amount: int, reason: str = "") -> int:
    current = _get_coins()
    new_val = max(0, current + amount)
    db_set("economy", "coins", str(new_val))
    with _db_lock:
        conn = get_conn()
        conn.execute("INSERT INTO coin_txns(amount,reason,ts) VALUES(?,?,?)",
                     (amount, reason[:80], now_str()))
        conn.commit()
    return new_val

def _get_pet() -> dict:
    with _db_lock:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM virtual_pet").fetchall()
    d = {r["key"]: r["value"] for r in rows}
    return {
        "name":    d.get("name", "اونیکس"),
        "type":    d.get("type", "گربه"),
        "hunger":  int(d.get("hunger", "80")),
        "thirst":  int(d.get("thirst", "80")),
        "happy":   int(d.get("happy", "80")),
        "level":   int(d.get("level", "1")),
        "xp":      int(d.get("xp", "0")),
        "last_fed":d.get("last_fed", ""),
    }

def _save_pet(pet: dict):
    with _db_lock:
        conn = get_conn()
        for k, v in pet.items():
            conn.execute("INSERT INTO virtual_pet(key,value) VALUES(?,?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (k, str(v)))
        conn.commit()

def _card_deck() -> list:
    suits  = ["♠","♥","♦","♣"]
    values = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    deck = [(v, s) for s in suits for v in values]
    random.shuffle(deck)
    return deck

def _card_value(card) -> int:
    v = card[0]
    if v in ("J","Q","K"): return 10
    if v == "A": return 11
    return int(v)

def _hand_total(hand: list) -> int:
    total = sum(_card_value(c) for c in hand)
    aces  = sum(1 for c in hand if c[0] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def _card_str(hand: list) -> str:
    return " ".join(f"{c[0]}{c[1]}" for c in hand)

_MAGIC8_ANSWERS = [
    "✅ قطعاً بله!","✅ بدون شک!","✅ بله!","✅ امیدوارم که بله",
    "🤔 ممکن است","🤔 نامشخص","🤔 بعداً بپرس","🤔 پیش‌بینی نامشخص",
    "❌ بعید است","❌ خیر!","❌ قطعاً خیر","❌ چشم‌انداز خوب نیست",
]

_RIDDLES = [
    ("چه چیزی همیشه در مقابل شما است اما نمی‌توان آن را دید؟", "آینده"),
    ("هرچه بیشتر از آن می‌بری، بزرگ‌تر می‌شود. چیست؟", "حفره"),
    ("دارم صدا ولی دهان ندارم، دارم رودخانه ولی آب ندارم. چیستم؟", "نقشه"),
    ("یک نردبان دارم که به پایین می‌رود اما بالا نمی‌رود. چیست؟", "ریشه"),
    ("وقتی جوان است سفید است، وقتی پیر شد قرمز می‌شود. چیست؟", "آتش"),
    ("من چیزی ندارم اما همه چیز را در خودم دارم. چیستم؟", "تاریکی"),
]

_TYPING_SENTENCES = [
    "ONYX SELF V7 PRO'S سلف‌بات حرفه‌ای تلگرام",
    "Python is the best programming language in the world",
    "Telethon library powers this amazing selfbot",
    "سرعت تایپ خود را با این جمله آزمایش کن",
    "The quick brown fox jumps over the lazy dog",
]


def register_v7_handlers(client):
    """ثبت تمام هندلرهای V7 — همه در register_all ثبت می‌شوند"""
    pass  # handlers registered in register_all

    # ════════════════════════════════════════════
    #  🧠 هوش مصنوعی V7 — Shadow Profile
    # ════════════════════════════════════════════



# ══ V7 Menu ══
"""
══════════════════════════════════════════════
 💎 ONYX SELF V7 PRO'S — NEW MENU CATEGORIES
══════════════════════════════════════════════
This block gets merged into FULL_MENU after existing entries
"""

V7_MENU_ADDITIONS = {

    "🧠 هوش مصنوعی V7": [
        ("سایه",              "پروفایل سایه کاربر",             "سایه [@user]",              "سایه @ali"),
        ("خاطره_ثبت",         "ثبت خاطره از کاربر",             "خاطره_ثبت [@]|[متن]",       "خاطره_ثبت @ali|دوست قدیمی"),
        ("خاطره‌ها",          "لیست خاطرات",                    "خاطره‌ها [@user]",           "خاطره‌ها @ali"),
        ("خاطره_حذف",         "حذف خاطره",                      "خاطره_حذف [id]",             "خاطره_حذف 1"),
        ("امروز_در_تاریخ",    "رویداد این روز در تاریخ",        "امروز_در_تاریخ",             "امروز_در_تاریخ"),
        ("امروز_ثبت",         "ثبت رویداد امروز",               "امروز_ثبت [متن]",            "امروز_ثبت اولین پیام"),
        ("یادآور_هوشمند",     "یادآور از متن",                  "یادآور_هوشمند [متن]",        "یادآور_هوشمند جلسه فردا ۳ بعدازظهر"),
        ("یادآورهای_من",      "لیست یادآورهای هوشمند",          "یادآورهای_من",               "یادآورهای_من"),
        ("میمیک_چت",          "تقلید سبک نوشتار",               "میمیک_چت [@user]",           "میمیک_چت @ali"),
    ],

    "📊 آنالیتیکس V7": [
        ("گراف_فعالیت",       "گراف فعالیت ۷ روز",              "گراف_فعالیت",                "گراف_فعالیت"),
        ("زمان_پاسخ",         "میانگین زمان پاسخ",              "زمان_پاسخ [@user]",          "زمان_پاسخ @ali"),
        ("استریک",            "سیستم streak فعالیت",            "استریک",                     "استریک"),
        ("استریک_ثبت",        "ثبت فعالیت روزانه",              "استریک_ثبت [نوع]",           "استریک_ثبت ورزش"),
        ("خلاصه_روزانه",      "خلاصه امروز",                    "خلاصه_روزانه",               "خلاصه_روزانه"),
        ("گزارش_هفتگی",       "گزارش هفته جاری",                "گزارش_هفتگی",                "گزارش_هفتگی"),
    ],

    "👥 مخاطبان V7": [
        ("مورد_علاقه",        "مخاطب مورد علاقه",               "مورد_علاقه [@user]",         "مورد_علاقه @ali"),
        ("لیست_علاقه",        "لیست مورد علاقه‌ها",             "لیست_علاقه",                 "لیست_علاقه"),
        ("بی‌خیال",          "اضافه به لیست نادیده",           "بی‌خیال [@user] [دلیل]",    "بی‌خیال @ali مزاحم"),
        ("لیست_نادیده",       "لیست نادیده گرفته‌شده",          "لیست_نادیده",                "لیست_نادیده"),
        ("منتظر",             "ردیابی انتظار پاسخ",             "منتظر [@user] [موضوع]",      "منتظر @ali پروژه"),
        ("منتظرها",           "لیست انتظارها",                  "منتظرها",                    "منتظرها"),
        ("منتظر_انجام",       "انجام شد — حذف از انتظار",       "منتظر_انجام [id]",           "منتظر_انجام 1"),
        ("تایم‌لاین_پروفایل", "تایم‌لاین تغییرات پروفایل",     "تایم‌لاین_پروفایل [@user]",  "تایم‌لاین_پروفایل @ali"),
        ("نام_مستعار",        "تنظیم نام مستعار",               "نام_مستعار [@user] [نام]",   "نام_مستعار @ali داداش"),
        ("نام_مستعار_لیست",   "لیست نام‌های مستعار",            "نام_مستعار_لیست",            "نام_مستعار_لیست"),
    ],

    "💬 پیام‌رسانی V7": [
        ("پاسخ_سریع",         "ثبت پاسخ سریع",                 "پاسخ_سریع [کلید]|[متن]",    "پاسخ_سریع ok|باشه حتماً"),
        ("پاسخ_سریع_لیست",    "لیست پاسخ‌های سریع",            "پاسخ_سریع_لیست",             "پاسخ_سریع_لیست"),
        ("پاسخ_سریع_حذف",     "حذف پاسخ سریع",                  "پاسخ_سریع_حذف [کلید]",      "پاسخ_سریع_حذف ok"),
        ("پیش‌نویس",          "ذخیره پیش‌نویس",                 "پیش‌نویس [عنوان]|[متن]",    "پیش‌نویس ایده|ایده جدید"),
        ("پیش‌نویس_لیست",     "لیست پیش‌نویس‌ها",              "پیش‌نویس_لیست",              "پیش‌نویس_لیست"),
        ("پیش‌نویس_ارسال",    "ارسال پیش‌نویس",                 "پیش‌نویس_ارسال [id]",        "پیش‌نویس_ارسال 1"),
        ("پیش‌نویس_حذف",      "حذف پیش‌نویس",                   "پیش‌نویس_حذف [id]",          "پیش‌نویس_حذف 1"),
        ("بمب_پیام",          "ارسال چندباره — Message Bomb",   "بمب_پیام [تعداد] [متن]",     "بمب_پیام 3 سلام"),
    ],

    "🔐 امنیت V7": [
        ("رمز_ذخیره",         "ذخیره رمز عبور",                 "رمز_ذخیره [سایت]|[user]|[pass]","رمز_ذخیره gmail|ali|Pass123"),
        ("رمز_نمایش",         "نمایش رمز عبور",                 "رمز_نمایش [سایت]",           "رمز_نمایش gmail"),
        ("رمز_لیست",          "لیست رمزها",                     "رمز_لیست",                   "رمز_لیست"),
        ("رمز_حذف",           "حذف رمز",                        "رمز_حذف [id]",               "رمز_حذف 1"),
        ("رمز_تولید_v7",      "تولید رمز قوی",                  "رمز_تولید_v7 [طول]",         "رمز_تولید_v7 16"),
    ],

    "⚙️ اتوماسیون V7": [
        ("زمان‌بند",          "زمان‌بند دستور",                  "زمان‌بند [نام]|[دستور]|[زمان]","زمان‌بند صبح|پینگ|08:00"),
        ("زمان‌بند_لیست",     "لیست زمان‌بندها",                "زمان‌بند_لیست",              "زمان‌بند_لیست"),
        ("زمان‌بند_حذف",      "حذف زمان‌بند",                   "زمان‌بند_حذف [id]",          "زمان‌بند_حذف 1"),
        ("هشدار_منشن",        "هشدار هنگام منشن",               "هشدار_منشن [کلیدواژه]",      "هشدار_منشن ONYX"),
        ("هشدار_منشن_لیست",   "لیست هشدارهای منشن",             "هشدار_منشن_لیست",            "هشدار_منشن_لیست"),
        ("ری‌استارت",         "ری‌استارت سلف‌بات",               "ری‌استارت",                  "ری‌استارت"),
        ("پاکسازی_هوشمند",    "پاکسازی داده‌های قدیمی",         "پاکسازی_هوشمند [روز]",       "پاکسازی_هوشمند 30"),
        ("آرشیو_ثبت",         "آرشیو محتوا",                    "آرشیو_ثبت [دسته]|[عنوان]|[متن]","آرشیو_ثبت کد|sort|[کد...]"),
        ("آرشیو_لیست",        "لیست آرشیو",                     "آرشیو_لیست [دسته]",           "آرشیو_لیست کد"),
        ("آرشیو_نمایش",       "نمایش آرشیو",                    "آرشیو_نمایش [id]",            "آرشیو_نمایش 1"),
    ],

    "📂 کالکشن V7": [
        ("کالکشن_ثبت",        "ثبت آیتم کالکشن",                "کالکشن_ثبت [دسته]|[عنوان]|[محتوا]","کالکشن_ثبت موسیقی|درامه|لینک"),
        ("کالکشن_لیست",       "لیست کالکشن",                    "کالکشن_لیست [دسته]",          "کالکشن_لیست موسیقی"),
        ("کالکشن_جستجو",      "جستجو در کالکشن",                "کالکشن_جستجو [متن]",          "کالکشن_جستجو درام"),
        ("کالکشن_حذف",        "حذف آیتم",                       "کالکشن_حذف [id]",             "کالکشن_حذف 1"),
        ("کالکشن_دسته‌ها",    "لیست دسته‌ها",                   "کالکشن_دسته‌ها",              "کالکشن_دسته‌ها"),
        ("کالکشن_تگ",         "افزودن تگ به کالکشن",            "کالکشن_تگ [id] [تگ]",         "کالکشن_تگ 1 موسیقی"),
    ],

    "🔎 ابزار هوشمند V7": [
        ("جستجو_هوشمند",      "جستجو در همه دیتابیس",           "جستجو_هوشمند [متن]",          "جستجو_هوشمند علی"),
        ("داشبورد_زنده",      "داشبورد زنده سیستم",             "داشبورد_زنده",                "داشبورد_زنده"),
        ("منابع",             "مانیتور RAM/CPU",                "منابع",                       "منابع"),
        ("بررسی_وابستگی",     "بررسی پکیج‌های نصب‌شده",        "بررسی_وابستگی",               "بررسی_وابستگی"),
    ],

    "🎰 بازی V7": [
        ("اسلات",             "اسلات ماشین",                    "اسلات [شرط]",                 "اسلات 10"),
        ("تاس_نبرد",          "نبرد تاس",                       "تاس_نبرد [@user]",            "تاس_نبرد @ali"),
        ("چرخ",               "چرخ گردون",                      "چرخ [گ۱,گ۲,...]",            "چرخ کار,استراحت,بازی"),
        ("سکه",               "پرتاب سکه",                      "سکه",                         "سکه"),
        ("سنگ_کاغذ_قیچی",    "بازی سنگ کاغذ قیچی",            "سنگ_کاغذ_قیچی [انتخاب]",     "سنگ_کاغذ_قیچی سنگ"),
        ("بیست_یک",           "بازی بیست‌ویک (Blackjack)",      "بیست_یک [شرط]",               "بیست_یک 20"),
        ("بیست_یک_کارت",      "دریافت کارت جدید",               "بیست_یک_کارت",                "بیست_یک_کارت"),
        ("ورق_تصادفی",        "ورق تصادفی از دسته",             "ورق_تصادفی",                  "ورق_تصادفی"),
        ("جادو_هشت",          "Magic 8-Ball",                   "جادو_هشت [سوال]",             "جادو_هشت آیا موفق می‌شوم؟"),
        ("حدس_عدد",           "بازی حدس عدد",                   "حدس_عدد [min] [max]",         "حدس_عدد 1 100"),
        ("حدس_من",            "پاسخ حدس عدد",                   "حدس_من [عدد]",                "حدس_من 47"),
        ("معما_روز",          "معما روزانه",                    "معما_روز",                    "معما_روز"),
        ("تایپ_چالش",         "چالش تایپ",                      "تایپ_چالش",                   "تایپ_چالش"),
        ("تایپ_پاسخ",         "پاسخ چالش تایپ",                 "تایپ_پاسخ [متن]",             "تایپ_پاسخ hello"),
        ("ماموریت_آمار",      "آمار ماموریت‌ها",                "ماموریت_آمار",                "ماموریت_آمار"),
    ],

    "💰 اقتصاد V7": [
        ("موجودی",            "موجودی سکه",                     "موجودی",                      "موجودی"),
        ("انتقال_سکه",        "انتقال سکه",                     "انتقال_سکه [@user] [مقدار]",  "انتقال_سکه @ali 100"),
        ("فروشگاه",           "فروشگاه آیتم",                   "فروشگاه",                     "فروشگاه"),
        ("خرید",              "خرید آیتم",                      "خرید [id]",                   "خرید 1"),
        ("کوله‌پشتی",         "کوله‌پشتی — آیتم‌های من",        "کوله‌پشتی",                   "کوله‌پشتی"),
        ("جدول_امتیاز",       "جدول امتیاز",                    "جدول_امتیاز",                 "جدول_امتیاز"),
        ("جایزه_روزانه",      "جایزه روزانه",                   "جایزه_روزانه",                "جایزه_روزانه"),
        ("ماموریت‌ها",        "ماموریت‌های فعال",               "ماموریت‌ها",                  "ماموریت‌ها"),
        ("ماموریت_انجام",     "پیشرفت ماموریت",                 "ماموریت_انجام [id]",           "ماموریت_انجام 1"),
        ("مجموعه_نشان",       "مجموعه نشان‌ها",                 "مجموعه_نشان",                 "مجموعه_نشان"),
        ("درخت_مهارت",        "درخت مهارت",                     "درخت_مهارت",                  "درخت_مهارت"),
        ("ارتقاء_مهارت",      "ارتقاء مهارت",                   "ارتقاء_مهارت [مهارت]",        "ارتقاء_مهارت منطق"),
        ("جعبه_رمز",          "جعبه مرموز",                     "جعبه_رمز",                    "جعبه_رمز"),
        ("نبرد_باس",          "نبرد با باس",                    "نبرد_باس",                    "نبرد_باس"),
        ("حیوان_خانگی",       "حیوان خانگی مجازی",              "حیوان_خانگی",                 "حیوان_خانگی"),
        ("مراقبت",            "مراقبت از حیوان خانگی",          "مراقبت [غذا|آب|بازی]",       "مراقبت غذا"),
        ("خانه",              "خانه مجازی",                     "خانه",                        "خانه"),
        ("مبل_بخر",           "خرید مبلمان",                    "مبل_بخر [اتاق] [آیتم]",       "مبل_بخر نشیمن کاناپه"),
        ("آزمایشگاه",         "آزمایشگاه ONYX",                 "آزمایشگاه",                   "آزمایشگاه"),
        ("آزمایش",            "شروع آزمایش",                    "آزمایش [نام]|[ورودی]",        "آزمایش ترکیب|آتش+آب"),
        ("آزمایشگاه_لیست",   "لیست آزمایشگاه",                 "آزمایشگاه_لیست",              "آزمایشگاه_لیست"),
        ("انتقال_سکه",        "انتقال سکه به کاربر",            "انتقال_سکه [@] [مقدار]",      "انتقال_سکه @ali 100"),
        ("همه_استریک",        "همه streak‌ها",                  "همه_استریک",                  "همه_استریک"),
        ("حیوان_آمار",        "آمار حیوان خانگی",               "حیوان_آمار",                  "حیوان_آمار"),
        ("نشان_ثبت",          "ثبت نشان",                       "نشان_ثبت [id]|[عنوان]|[emoji]","نشان_ثبت pro|حرفه‌ای|🏆"),
        ("درخت_مهارت",        "درخت مهارت",                     "درخت_مهارت",                  "درخت_مهارت"),
        ("اتاق‌ها",           "اتاق‌های خانه مجازی",            "اتاق‌ها",                     "اتاق‌ها"),
        ("لاگ_فعالیت",        "لاگ فعالیت‌ها",                 "لاگ_فعالیت [تعداد]",          "لاگ_فعالیت 20"),
    ],

    "🛡️ VPN Config V7": [
        ("کانفیگ_ثبت",        "ثبت کانفیگ جدید",                "کانفیگ_ثبت [نام]|[محتوا]",   "کانفیگ_ثبت ir1|vmess://..."),
        ("کانفیگ_لیست",       "لیست کانفیگ‌ها",                 "کانفیگ_لیست",                 "کانفیگ_لیست"),
        ("کانفیگ_نمایش",      "نمایش کانفیگ",                   "کانفیگ_نمایش [id]",           "کانفیگ_نمایش 1"),
        ("کانفیگ_حذف",        "حذف کانفیگ",                     "کانفیگ_حذف [id]",             "کانفیگ_حذف 1"),
        ("کانفیگ_علاقه",      "علاقه‌مند کردن کانفیگ",          "کانفیگ_علاقه [id]",           "کانفیگ_علاقه 1"),
        ("کانفیگ_تگ",         "افزودن تگ",                      "کانفیگ_تگ [id] [تگ]",        "کانفیگ_تگ 1 ایران"),
        ("کانفیگ_آمار",       "آمار کانفیگ",                    "کانفیگ_آمار [id]",            "کانفیگ_آمار 1"),
        ("کانفیگ_چرخش",       "چرخش خودکار کانفیگ",            "کانفیگ_چرخش",                 "کانفیگ_چرخش"),
        ("کانفیگ_تکراری",     "تشخیص تکراری",                   "کانفیگ_تکراری",               "کانفیگ_تکراری"),
        ("کانفیگ_اشتراک",     "اشتراک‌گذاری کانفیگ",           "کانفیگ_اشتراک [id]",          "کانفیگ_اشتراک 1"),
        ("کانفیگ_آزمایشگاه",  "آزمایشگاه کانفیگ",               "کانفیگ_آزمایشگاه [id]",       "کانفیگ_آزمایشگاه 1"),
        ("سرور_رتبه",         "رتبه‌بندی سرورها",               "سرور_رتبه",                   "سرور_رتبه"),
        ("پینگ_سرور",         "پینگ لایو سرور",                 "پینگ_سرور [آدرس]",            "پینگ_سرور example.com"),
        ("تاریخچه_اتصال",     "تاریخچه اتصال‌ها",              "تاریخچه_اتصال",               "تاریخچه_اتصال"),
        ("آمار_vpn",          "آمار کامل VPN",                  "آمار_vpn",                    "آمار_vpn"),
        ("کانفیگ_خروجی",      "خروجی دسته‌جمعی کانفیگ",         "کانفیگ_خروجی [تگ]",            "کانفیگ_خروجی ایران"),
    ],

    "🏪 فروشگاه V7": [
        ("محصول_ثبت",         "ثبت محصول جدید",                 "محصول_ثبت [نام]|[قیمت]|[توضیح]","محصول_ثبت VPN ماهانه|50000|۳۰ روز"),
        ("محصول_لیست",        "لیست محصولات",                   "محصول_لیست",                  "محصول_لیست"),
        ("محصول_ویرایش",      "ویرایش محصول",                   "محصول_ویرایش [id] [فیلد]=[مقدار]","محصول_ویرایش 1 price=45000"),
        ("محصول_حذف",         "حذف محصول",                      "محصول_حذف [id]",              "محصول_حذف 1"),
        ("کانفیگ_اضافه",      "اضافه کانفیگ به محصول",          "کانفیگ_اضافه [product_id]|[محتوا]","کانفیگ_اضافه 1|vmess://..."),
        ("موجودی_محصول",      "نمایش موجودی",                   "موجودی_محصول [id]",           "موجودی_محصول 1"),
        ("سفارش_لیست",        "لیست سفارش‌ها",                  "سفارش_لیست [status]",         "سفارش_لیست pending"),
        ("سفارش_تایید",       "تایید سفارش و ارسال کانفیگ",     "سفارش_تایید [order_uid]",     "سفارش_تایید ORD-ABC123"),
        ("سفارش_رد",          "رد سفارش",                       "سفارش_رد [order_uid] [دلیل]", "سفارش_رد ORD-ABC123 پرداخت نشد"),
        ("سفارش_جستجو",       "جستجو در سفارش‌ها",              "سفارش_جستجو [متن]",           "سفارش_جستجو ali"),
        ("کوپن_ثبت",          "ثبت کوپن تخفیف",                 "کوپن_ثبت [کد]|[درصد]",       "کوپن_ثبت SAVE20|20"),
        ("کوپن_لیست",         "لیست کوپن‌ها",                   "کوپن_لیست",                   "کوپن_لیست"),
        ("کوپن_استفاده",      "بررسی و استفاده از کوپن",        "کوپن_استفاده [کد]",           "کوپن_استفاده SAVE20"),
        ("کوپن_غیرفعال",      "غیرفعال کردن کوپن",             "کوپن_غیرفعال [کد]",           "کوپن_غیرفعال SAVE20"),
        ("vip_قیمت",          "قیمت ویژه VIP",                  "vip_قیمت [product_id]|[قیمت]","vip_قیمت 1|40000"),
        ("کانفیگ_جایگزین",   "جایگزینی کانفیگ سفارش",         "کانفیگ_جایگزین [order_id]",  "کانفیگ_جایگزین 5"),
        ("تمدید_یادآور",      "ارسال یادآوری تمدید",           "تمدید_یادآور [روز]",         "تمدید_یادآور 3"),
        ("لیست_انتظار_فروش",  "لیست انتظار محصول",              "لیست_انتظار_فروش [id]",       "لیست_انتظار_فروش 1"),
        ("تنظیم_فروشگاه",     "تنظیم کانال/ادمین",              "تنظیم_فروشگاه [کلید]|[مقدار]","تنظیم_فروشگاه admin_id|123456"),
        ("آمار_فروشگاه",     "آمار کامل فروشگاه",              "آمار_فروشگاه",                "آمار_فروشگاه"),
        ("تاریخچه_سفارش",    "تاریخچه سفارشات مشتری",          "تاریخچه_سفارش [@user]",       "تاریخچه_سفارش @ali"),
        ("آمار_اشتراک",      "آمار اشتراک‌ها و تمدیدها",       "آمار_اشتراک",                 "آمار_اشتراک"),
    ],

    "👔 CRM V7": [
        ("مشتری_پروفایل",     "پروفایل CRM مشتری",              "مشتری_پروفایل [@user]",       "مشتری_پروفایل @ali"),
        ("مشتری_یادداشت",     "یادداشت مشتری",                  "مشتری_یادداشت [@]|[یادداشت]","مشتری_یادداشت @ali|خرید کرده"),
        ("مشتری_vip",         "تغییر سطح VIP",                  "مشتری_vip [@] [سطح]",         "مشتری_vip @ali 2"),
        ("مشتری_بلاک",        "بلاک مشتری",                     "مشتری_بلاک [@] [دلیل]",       "مشتری_بلاک @ali تقلب"),
        ("مشتری_جستجو",       "جستجو مشتری",                    "مشتری_جستجو [متن]",           "مشتری_جستجو ali"),
        ("پخش_همه",           "پخش پیام به همه مشتریان",        "پخش_همه [پیام]",              "پخش_همه اطلاعیه مهم"),
        ("پخش_vip",           "پخش به VIPها",                   "پخش_vip [پیام]",              "پخش_vip تخفیف ویژه"),
        ("پخش_محصول",         "پخش به خریداران محصول",          "پخش_محصول [id] [پیام]",       "پخش_محصول 1 تمدید"),
        ("کمپین_ثبت",         "ثبت کمپین",                      "کمپین_ثبت [نام]|[قالب]",      "کمپین_ثبت تخفیف|سلام {name}"),
        ("کمپین_لیست",        "لیست کمپین‌ها",                  "کمپین_لیست",                  "کمپین_لیست"),
        ("کمپین_ارسال",       "ارسال کمپین",                    "کمپین_ارسال [id]",            "کمپین_ارسال 1"),
        ("مشتری_تگ",          "افزودن تگ به مشتری",            "مشتری_تگ [@]|[تگ]",           "مشتری_تگ @ali|VIP"),
        ("مشتری_هشدار",       "ثبت هشدار برای مشتری",          "مشتری_هشدار [@]",             "مشتری_هشدار @ali"),
        ("مشتری_وایت",        "وایت‌لیست مشتری",               "مشتری_وایت [@]",              "مشتری_وایت @ali"),
        ("مشتری_تمدید",       "ثبت تاریخ تمدید",               "مشتری_تمدید [@]|[تاریخ]",    "مشتری_تمدید @ali|2025-08-01"),
        ("پخش_منقضی",         "پخش به منقضی‌شوندگان",          "پخش_منقضی [پیام]",            "پخش_منقضی تمدید کنید"),
        ("پخش_غیرفعال",       "پخش به غیرفعال‌ها",             "پخش_غیرفعال [روز] [پیام]",   "پخش_غیرفعال 30 برگردید"),
        ("پخش_جدید",          "پخش به مشتریان جدید",           "پخش_جدید [روز] [پیام]",      "پخش_جدید 7 خوش آمدید"),
        ("پیشنهاد_هوش",       "پیشنهادهای هوشمند بازاریابی",  "پیشنهاد_هوش",                "پیشنهاد_هوش"),
        ("آمار_crm",          "آمار کامل CRM",                  "آمار_crm",                    "آمار_crm"),
        ("crm_کامل",          "آمار پیشرفته CRM",               "crm_کامل",                    "crm_کامل"),
        ("مشتری_کشور",        "ثبت کشور مشتری",                 "مشتری_کشور [@]|[کشور]",       "مشتری_کشور @ali|ایران"),
        ("پخش_کشور",          "پخش بر اساس کشور",               "پخش_کشور [کشور] [پیام]",      "پخش_کشور ایران سلام"),
        ("تاریخچه_کمپین",     "تاریخچه کمپین‌ها",              "تاریخچه_کمپین [id]",          "تاریخچه_کمپین 1"),
        ("گزارش_کمپین",       "گزارش کمپین",                   "گزارش_کمپین [id]",            "گزارش_کمپین 1"),
    ],

    "🎫 پشتیبانی V7": [
        ("تیکت_باز",          "باز کردن تیکت پشتیبانی",         "تیکت_باز [موضوع]",            "تیکت_باز مشکل اتصال"),
        ("تیکت_لیست",         "لیست تیکت‌ها",                   "تیکت_لیست [status]",          "تیکت_لیست open"),
        ("تیکت_پاسخ",         "پاسخ به تیکت",                   "تیکت_پاسخ [id] [متن]",        "تیکت_پاسخ 1 مشکل حل شد"),
        ("تیکت_بستن",         "بستن تیکت",                      "تیکت_بستن [id]",              "تیکت_بستن 1"),
        ("تیکت_جستجو",        "جستجو تیکت",                     "تیکت_جستجو [متن]",            "تیکت_جستجو اتصال"),
        ("تیکت_آمار",         "آمار تیکت‌ها",                   "تیکت_آمار",                   "تیکت_آمار"),
    ],
    "🗂️ مدیریت پیشرفته V7": [
        ("آرشیو_جستجو",       "جستجو در آرشیو",                 "آرشیو_جستجو [متن]",            "آرشیو_جستجو کد"),
        ("آرشیو_حذف",         "حذف از آرشیو",                   "آرشیو_حذف [id]",               "آرشیو_حذف 1"),
        ("کالکشن_تگ",         "افزودن تگ به کالکشن",            "کالکشن_تگ [id] [تگ]",         "کالکشن_تگ 1 موسیقی"),
        ("وضعیت_پلاگین",      "وضعیت پلاگین‌ها",               "وضعیت_پلاگین",                "وضعیت_پلاگین"),
        ("تاریخچه_جستجو",     "تاریخچه جستجوها",               "تاریخچه_جستجو",               "تاریخچه_جستجو"),
        ("لیست_بکاپ",         "لیست بکاپ‌ها",                  "لیست_بکاپ",                   "لیست_بکاپ"),
        ("سایه_جستجو",        "جستجو سایه",                     "سایه_جستجو [متن]",             "سایه_جستجو علی"),
        ("پیش‌نویس_ارسال_به", "ارسال پیش‌نویس به کاربر",        "پیش‌نویس_ارسال_به [id] [@]",  "پیش‌نویس_ارسال_به 1 @ali"),
        ("تیکت_نمایش",        "نمایش تیکت کامل",                "تیکت_نمایش [id]",              "تیکت_نمایش 1"),
        ("تیکت_اولویت",       "تغییر اولویت تیکت",              "تیکت_اولویت [id] [اولویت]",   "تیکت_اولویت 1 high"),
        ("تیکت_ارسال",        "ارسال پاسخ به مشتری",            "تیکت_ارسال [id] [متن]",        "تیکت_ارسال 1 مشکل حل شد"),
        ("ارسال_همه",         "ارسال به همه مخاطبان",           "ارسال_همه [پیام]",             "ارسال_همه سلام"),
        ("آمار_v7",           "آمار سیستم‌های V7",              "آمار_v7",                     "آمار_v7"),
        ("لاگ_فعالیت",        "لاگ فعالیت‌ها",                 "لاگ_فعالیت [تعداد]",          "لاگ_فعالیت 20"),
        ("اتاق‌ها",           "اتاق‌های خانه مجازی",            "اتاق‌ها",                     "اتاق‌ها"),
        ("حیوان_آمار",        "آمار حیوان خانگی",               "حیوان_آمار",                  "حیوان_آمار"),
        ("نشان_ثبت",          "ثبت نشان",                       "نشان_ثبت [id]|[عنوان]|[emoji]","نشان_ثبت pro|حرفه‌ای|🏆"),
        ("ماموریت_آمار",      "آمار ماموریت‌ها",                "ماموریت_آمار",                "ماموریت_آمار"),
        ("همه_استریک",        "همه streak‌ها",                  "همه_استریک",                  "همه_استریک"),
        ("آمار_vpn",          "آمار کامل VPN",                  "آمار_vpn",                    "آمار_vpn"),
        ("کانفیگ_خروجی",      "خروجی دسته‌جمعی کانفیگ",         "کانفیگ_خروجی [تگ]",            "کانفیگ_خروجی ایران"),
        ("آزمایشگاه_لیست",   "لیست آزمایشگاه",                 "آزمایشگاه_لیست",              "آزمایشگاه_لیست"),
        ("انتقال_سکه",        "انتقال سکه",                     "انتقال_سکه [@] [مقدار]",      "انتقال_سکه @ali 100"),
        ("تاریخچه_کمپین",     "تاریخچه کمپین‌ها",              "تاریخچه_کمپین [id]",          "تاریخچه_کمپین 1"),
        ("گزارش_کمپین",       "گزارش کمپین",                   "گزارش_کمپین [id]",            "گزارش_کمپین 1"),
        ("مشتری_کشور",        "ثبت کشور مشتری",                 "مشتری_کشور [@]|[کشور]",       "مشتری_کشور @ali|ایران"),
        ("پخش_کشور",          "پخش بر اساس کشور",               "پخش_کشور [کشور] [پیام]",      "پخش_کشور ایران سلام"),
        ("آمار_اشتراک",       "آمار اشتراک‌ها",                "آمار_اشتراک",                 "آمار_اشتراک"),
        ("crm_کامل",          "آمار پیشرفته CRM",               "crm_کامل",                    "crm_کامل"),
        ("تاریخچه_سفارش",     "تاریخچه سفارشات مشتری",          "تاریخچه_سفارش [@]",            "تاریخچه_سفارش @ali"),
        ("آمار_فروشگاه",      "آمار کامل فروشگاه",              "آمار_فروشگاه",                "آمار_فروشگاه"),
        ("گزارش_کامل",        "گزارش هفتگی جامع",               "گزارش_کامل",                  "گزارش_کامل"),
        ("وضعیت_کامل",        "وضعیت کامل سیستم",               "وضعیت_کامل",                  "وضعیت_کامل"),
        ("داشبورد",           "داشبورد کنترل مرکزی",            "داشبورد",                     "داشبورد"),
        ("درباره",            "درباره ONYX",                    "درباره",                      "درباره"),
    ],

}


# ── Merge V7 menus into FULL_MENU so منو command exposes all features ──
FULL_MENU.update(V7_MENU_ADDITIONS)


def register_all(client):

    # ─── منو راهنما ───
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^منو$"))
    async def main_menu(event):
        record_cmd("منو")
        cats = list(FULL_MENU.keys())
        lines = []
        for i, cat in enumerate(cats):
            cnt = len(FULL_MENU[cat])
            lines.append(f"{i+1:2d}. {cat} ({cnt} دستور)")
        await safe_edit(event, box("💎 ONYX SELF V7 PRO'S — منوی اصلی", lines,
                                   "منو [شماره] برای جزئیات"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^منو (\d+)$"))
    async def category_menu(event):
        record_cmd("منو")
        idx = int(event.pattern_match.group(1)) - 1
        cats = list(FULL_MENU.keys())
        if idx < 0 or idx >= len(cats):
            await safe_edit(event, f"❌ شماره نامعتبر! (۱ تا {len(cats)})"); return
        cat  = cats[idx]
        cmds = FULL_MENU[cat]
        lines = [f"• {cmd} — {desc}" for cmd, desc, _, _ in cmds]
        await safe_edit(event, box(f"{cat}", lines, f"راهنما [دستور] برای جزئیات"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^راهنما (.+)$"))
    async def command_help(event):
        record_cmd("راهنما")
        query = event.pattern_match.group(1).strip().lstrip(".")
        # جستجو در همه دسته‌ها
        found = []
        for cat, cmds in FULL_MENU.items():
            for cmd, desc, usage, example in cmds:
                if query.lower() in cmd.lower() or query.lower() in desc.lower():
                    found.append((cat, cmd, desc, usage, example))
        if not found:
            await safe_edit(event, f"❌ دستوری برای «{query}» پیدا نشد!\nمنو را ببین: منو"); return
        # اگر تک نتیجه، نمایش کامل
        if len(found) == 1:
            cat, cmd, desc, usage, example = found[0]
            await safe_edit(event, box(f"❓ راهنما: {cmd}", [
                f"دسته: {cat}",
                f"توضیح: {desc}",
                f"استفاده: {usage}",
                f"مثال: {example}",
            ], WATERMARK))
        else:
            lines = [f"• {cmd} ({cat.split()[1]}): {desc}" for cat, cmd, desc, _, _ in found[:12]]
            await safe_edit(event, box(f"🔍 نتایج «{query}» ({len(found)})", lines,
                                       "راهنما [دستور دقیق] برای جزئیات"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستورات$"))
    async def all_commands(event):
        record_cmd("دستورات")
        total = sum(len(v) for v in FULL_MENU.values())
        cats  = len(FULL_MENU)
        lines = [
            f"کل دستورات: {total}",
            f"دسته‌بندی: {cats}",
            "──────────────────",
        ]
        for cat, cmds in FULL_MENU.items():
            lines.append(f"{cat}: {len(cmds)}")
        await safe_edit(event, box("📚 فهرست دستورات", lines, "منو → برای مشاهده"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:help|هلپ|کمک)$"))
    async def help_alias(event):
        record_cmd("help")
        await safe_edit(event, box("💎 ONYX SELF V7 PRO'S", [
            "منو — فهرست دسته‌بندی",
            "منو [شماره] — دستورات دسته",
            "راهنما [دستور] — جزئیات دستور",
            "دستورات — آمار کلی",
            "داشبورد — کنترل مرکزی",
            "پینگ — وضعیت سیستم",
        ], WATERMARK))
    

    # ─── contacts ───
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پروفایل_کامل(?: (.+))?$"))
    async def full_profile(event):
        record_cmd("پروفایل_کامل")
        arg = event.pattern_match.group(1)
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ ریپلای کن یا یوزرنیم بده:\nمثال: پروفایل_کامل @user")
            return
        try:
            fu = await client(GetFullUserRequest(u))
            bio = getattr(fu.full_user, "about", "") or "ندارد"
        except Exception:
            bio = "ندارد"
        c = get_contact(u.id)
        old_name = c["name"]
        c["name"]     = f"{getattr(u,'first_name','') or ''} {getattr(u,'last_name','') or ''}".strip()
        c["username"] = getattr(u, "username", "") or ""
        c["bio"]      = bio[:120]
        if old_name and old_name != c["name"]:
            log_contact_change(u.id, "name", old_name, c["name"])
        save_contact(c)
        s_label = CONTACT_STATUSES.get(c["status"], "👤 عادی")
        l_label = CONTACT_LABELS.get(c["color"], "—")
        tags_s  = " ".join(f"#{t}" for t in c["tags"]) or "—"
        await safe_edit(event, box("👤 پروفایل کامل", [
            f"نام: {c['name'][:30]}",
            f"یوزر: @{c['username'] or '—'}",
            f"آیدی: {u.id}",
            f"بیو: {c['bio'][:50]}",
            f"اولین دیدار: {c['first_seen']}",
            f"آخرین پیام: {c['last_msg'] or '—'}",
            f"تعداد پیام: {c['msg_count']}",
            f"یادداشت: {c['note'][:35] or '—'}",
            f"امتیاز: {c['score']} ⭐",
            f"تگ‌ها: {tags_s[:40]}",
            f"وضعیت: {s_label}",
            f"برچسب: {l_label}",
            f"تلفن: {c['phone'] or '—'}",
            f"شغل: {c['job'] or '—'}",
        ], WATERMARK))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_مخاطب (.+) (love|enemy|silent|blocked|normal|vip|work)$"))
    async def set_status(event):
        record_cmd("وضعیت_مخاطب")
        arg, status = event.pattern_match.group(1).strip(), event.pattern_match.group(2)
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        c = get_contact(u.id)
        old = c["status"]; c["status"] = status
        save_contact(c)
        log_contact_change(u.id, "status", old, status)
        label = CONTACT_STATUSES.get(status, status)
        await safe_edit(event, f"✅ وضعیت {getattr(u,'first_name','کاربر')}: {label}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^برچسب_مخاطب (.+) (family|friend|customer|annoying|blocked|colleague)$"))
    async def set_label(event):
        record_cmd("برچسب_مخاطب")
        arg, color = event.pattern_match.group(1).strip(), event.pattern_match.group(2)
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        c = get_contact(u.id); c["color"] = color; save_contact(c)
        await safe_edit(event, f"✅ برچسب {getattr(u,'first_name','کاربر')}: {CONTACT_LABELS.get(color,color)}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^یادداشت_مخاطب (.+)\|(.+)$"))
    async def set_note(event):
        record_cmd("یادداشت_مخاطب")
        arg = event.pattern_match.group(1).strip()
        note = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        c = get_contact(u.id); c["note"] = note[:300]; save_contact(c)
        # ذخیره در جدول notes هم
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO contact_notes(uid,note,ts) VALUES(?,?,?)",
                         (u.id, note[:300], now_str()))
            conn.commit()
        await safe_edit(event, f"✅ یادداشت برای {getattr(u,'first_name','کاربر')} ثبت شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^امتیاز_مخاطب (.+) ([+-]?\d+)$"))
    async def set_score(event):
        record_cmd("امتیاز_مخاطب")
        arg = event.pattern_match.group(1).strip()
        delta = int(event.pattern_match.group(2))
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        c = get_contact(u.id); c["score"] = c["score"] + delta; save_contact(c)
        star = "⭐" * min(5, max(0, c["score"] // 10))
        await safe_edit(event, f"✅ امتیاز {getattr(u,'first_name','کاربر')}: {c['score']} {star}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تگ_مخاطب (.+)\|(.+)$"))
    async def add_tag(event):
        record_cmd("تگ_مخاطب")
        arg = event.pattern_match.group(1).strip()
        tag = event.pattern_match.group(2).strip().lstrip("#")
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        c = get_contact(u.id)
        if tag not in c["tags"]:
            c["tags"].append(tag)
        save_contact(c)
        await safe_edit(event, f"✅ تگ #{tag} به {getattr(u,'first_name','کاربر')} اضافه شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^یادآوری (.+) (.+)$"))
    async def add_reminder(event):
        record_cmd("یادآوری")
        arg = event.pattern_match.group(1).strip()
        text = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO reminders(uid,text,ts) VALUES(?,?,?)",
                         (u.id, text[:300], now_str()))
            conn.commit()
        await safe_edit(event, f"✅ یادآوری برای {getattr(u,'first_name','کاربر')} ثبت شد:\n{text[:60]}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^یادآوری‌ها$"))
    async def list_reminders(event):
        record_cmd("یادآوری‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT r.*,c.name FROM reminders r "
                "LEFT JOIN contacts c ON c.uid=r.uid "
                "WHERE r.done=0 ORDER BY r.id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 یادآوری‌ای ثبت نشده!"); return
        lines = [f"{'✅' if r['done'] else '⏳'} [{r['name'] or r['uid']}] {r['text'][:30]}" for r in rows]
        await safe_edit(event, box(f"⏰ یادآوری‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاریخچه_مخاطب (.+)$"))
    async def contact_history(event):
        record_cmd("تاریخچه_مخاطب")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM contact_history WHERE uid=? ORDER BY id DESC LIMIT 15",
                (u.id,)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"📭 تاریخچه‌ای برای {getattr(u,'first_name','کاربر')} نیست."); return
        lines = [f"• {r['ts']} | {r['field']}: {r['old_val'][:10]}→{r['new_val'][:10]}" for r in rows]
        await safe_edit(event, box(f"📋 تاریخچه {getattr(u,'first_name','?')}", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^سنجاق$"))
    async def pin_msg(event):
        record_cmd("سنجاق")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای روی پیام مورد نظر!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO pins(chat_id,msg_id,text,ts) VALUES(?,?,?,?)",
                (event.chat_id, reply.id, (reply.text or "")[:200], now_str())
            )
            conn.commit()
            cnt = conn.execute("SELECT COUNT(*) FROM pins WHERE chat_id=?", (event.chat_id,)).fetchone()[0]
        await safe_edit(event, f"📌 سنجاق شد! (کل در این چت: {cnt})")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^سنجاق‌ها$"))
    async def list_pins(event):
        record_cmd("سنجاق‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM pins ORDER BY id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 سنجاقی ثبت نشده!"); return
        lines = [f"📌 {r['ts'][:10]} | {(r['text'] or '[رسانه]')[:30]}" for r in rows]
        await safe_edit(event, box(f"📌 سنجاق‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دفترچه (.+)\|(.+)$"))
    async def notebook_set(event):
        record_cmd("دفترچه")
        arg = event.pattern_match.group(1).strip()
        data_str = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        # parse key=value pairs
        extra = {}
        phone = ""
        for part in data_str.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip(); v = v.strip()
                if k == "تلفن":
                    phone = v
                else:
                    extra[k] = v
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO notebooks(uid,phone,extra) VALUES(?,?,?) "
                "ON CONFLICT(uid) DO UPDATE SET phone=excluded.phone, extra=excluded.extra",
                (u.id, phone, json.dumps(extra, ensure_ascii=False))
            )
            conn.commit()
        await safe_edit(event, f"📔 دفترچه {getattr(u,'first_name','کاربر')} ذخیره شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دفترچه_نمایش (.+)$"))
    async def notebook_show(event):
        record_cmd("دفترچه_نمایش")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM notebooks WHERE uid=?", (u.id,)).fetchone()
        if not row:
            await safe_edit(event, f"📭 دفترچه‌ای برای {getattr(u,'first_name','کاربر')} نیست."); return
        extra = json.loads(row["extra"] or "{}")
        lines = [f"📞 تلفن: {row['phone'] or '—'}"]
        lines += [f"• {k}: {v}" for k, v in extra.items()]
        await safe_edit(event, box(f"📔 دفترچه {getattr(u,'first_name','?')}", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیدا (.+)$"))
    async def search_contacts(event):
        record_cmd("پیدا")
        q = event.pattern_match.group(1).strip().lower()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM contacts WHERE "
                "lower(name) LIKE ? OR lower(username) LIKE ? OR lower(tags) LIKE ? "
                "LIMIT 20",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            ).fetchall()
        if not rows:
            await safe_edit(event, f"❌ نتیجه‌ای برای «{q}» نیست."); return
        lines = [f"{'⭐' if r['score']>0 else '👤'} {r['name'] or '?'} @{r['username'] or '—'} | {CONTACT_STATUSES.get(r['status'],'👤')}"
                 for r in rows]
        await safe_edit(event, box(f"🔍 نتایج «{q}» ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^نقشه_رابطه$"))
    async def relationship_map(event):
        record_cmd("نقشه_رابطه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM contacts GROUP BY status"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 مخاطبی ثبت نشده!"); return
        lines = [f"{CONTACT_STATUSES.get(r['status'],'👤 ?')}: {r['cnt']} نفر" for r in rows]
        with _db_lock:
            conn = get_conn()
            total = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        lines.append(f"── کل: {total} مخاطب")
        await safe_edit(event, box("🗺️ نقشه رابطه", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_مخاطبان$"))
    async def contacts_stats(event):
        record_cmd("آمار_مخاطبان")
        with _db_lock:
            conn = get_conn()
            total  = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            scored = conn.execute("SELECT COUNT(*) FROM contacts WHERE score>0").fetchone()[0]
            noted  = conn.execute("SELECT COUNT(*) FROM contacts WHERE note!=''").fetchone()[0]
            tagged = conn.execute("SELECT COUNT(*) FROM contacts WHERE tags!='[]'").fetchone()[0]
            top    = conn.execute("SELECT name,msg_count FROM contacts ORDER BY msg_count DESC LIMIT 3").fetchall()
        lines = [
            f"کل مخاطبان: {total}",
            f"امتیازدار: {scored}",
            f"یادداشت‌دار: {noted}",
            f"تگ‌دار: {tagged}",
            "── پرپیام‌ترین ──",
        ] + [f"• {r['name'] or '?'}: {r['msg_count']}" for r in top]
        await safe_edit(event, box("📊 آمار مخاطبان", lines))
    
    @client.on(events.NewMessage(incoming=True))
    async def _track_contacts(event):
        """ردیابی خودکار پیام‌های دریافتی"""
        try:
            if event.sender_id and event.is_private:
                sender = await event.get_sender()
                incr_msg_count(
                    event.sender_id,
                    f"{getattr(sender,'first_name','') or ''} {getattr(sender,'last_name','') or ''}".strip(),
                    getattr(sender, "username", "") or ""
                )
        except Exception:
            pass
    

    # ─── automation ───
    
    # ══ منشی خودکار ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^منشی_فعال$"))
    async def busy_on(event):
        global _busy_active
        record_cmd("منشی_فعال")
        _busy_active = True
        t = _get_busy_text()
        await safe_edit(event, box("💼 منشی فعال", [f"پیام: {t[:50]}", "خاموش: منشی_خاموش"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^منشی_خاموش$"))
    async def busy_off(event):
        global _busy_active
        record_cmd("منشی_خاموش")
        _busy_active = False
        _busy_replied.clear()
        await safe_edit(event, "✅ منشی خاموش شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تنظیم_منشی (.+)$"))
    async def set_busy_text(event):
        record_cmd("تنظیم_منشی")
        t = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('busy_text',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (t,))
            conn.commit()
        await safe_edit(event, f"✅ پیام منشی:\n{t}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مشاهده_منشی$"))
    async def view_busy(event):
        record_cmd("مشاهده_منشی")
        t  = _get_busy_text()
        st = "🟢 فعال" if _busy_active else "🔴 خاموش"
        await safe_edit(event, box("💼 منشی", [f"وضعیت: {st}", f"پیام: {t[:50]}"]))
    
    @client.on(events.NewMessage(incoming=True))
    async def busy_handler(event):
        if not _busy_active or not event.is_private:
            return
        if _sleep_mode:
            return
        sid = event.sender_id
        if sid in _busy_replied:
            return
        _busy_replied.add(sid)
        await asyncio.sleep(0.5)
        try:
            await event.reply(_get_busy_text())
        except Exception:
            pass
    
    # ══ جواب خودکار ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:جواب|/جواب) (.+)\|(.+)$"))
    async def set_reply(event):
        record_cmd("جواب")
        k = event.pattern_match.group(1).strip()
        v = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO auto_replies(keyword,reply) VALUES(?,?) ON CONFLICT(keyword) DO UPDATE SET reply=excluded.reply", (k, v))
            conn.commit()
        await safe_edit(event, f"✅ جواب: {k} → {v[:30]}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_جواب (.+)$"))
    async def del_reply(event):
        record_cmd("حذف_جواب")
        k = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM auto_replies WHERE keyword=?", (k,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ جواب '{k}' حذف شد.")
        else:
            await safe_edit(event, f"❌ جواب '{k}' پیدا نشد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_جواب‌ها$"))
    async def list_replies(event):
        record_cmd("لیست_جواب‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM auto_replies LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ جوابی ثبت نشده!"); return
        lines = [f"• {r['keyword']}: {r['reply'][:30]}" for r in rows]
        await safe_edit(event, box(f"💬 جواب‌ها ({len(rows)})", lines))
    
    # ══ قوانین هوشمند ════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قانون (.+)\|(.+)$"))
    async def set_rule(event):
        record_cmd("قانون")
        k = event.pattern_match.group(1).strip()
        v = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO rules(keyword,reply) VALUES(?,?) ON CONFLICT(keyword) DO UPDATE SET reply=excluded.reply", (k, v))
            conn.commit()
        await safe_edit(event, f"✅ قانون: {k} → {v[:30]}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قوانین$"))
    async def list_rules(event):
        record_cmd("قوانین")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM rules LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 قانونی ثبت نشده!"); return
        lines = [f"• {r['keyword']}: {r['reply'][:30]}" for r in rows]
        await safe_edit(event, box(f"📋 قوانین ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_قانون (.+)$"))
    async def del_rule(event):
        record_cmd("حذف_قانون")
        k = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM rules WHERE keyword=?", (k,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ قانون '{k}' حذف شد.")
        else:
            await safe_edit(event, f"❌ قانون '{k}' پیدا نشد!")
    
    @client.on(events.NewMessage(incoming=True))
    async def auto_reply_handler(event):
        if not event.is_private or _sleep_mode:
            return
        text = (event.text or "").lower()
        with _db_lock:
            conn = get_conn()
            replies = conn.execute("SELECT * FROM auto_replies").fetchall()
            rules   = conn.execute("SELECT * FROM rules").fetchall()
        for r in replies:
            if r["keyword"].lower() in text:
                await asyncio.sleep(0.5)
                try:
                    await event.reply(r["reply"])
                except Exception:
                    pass
                return
        for r in rules:
            if any(w in text for w in r["keyword"].lower().split("|")):
                await asyncio.sleep(0.5)
                try:
                    await event.reply(r["reply"])
                except Exception:
                    pass
                return
    
    # ══ ماکرو ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماکرو (.+)=(.+)$"))
    async def set_macro(event):
        record_cmd("ماکرو")
        name = event.pattern_match.group(1).strip()
        val  = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO macros(name,value,ts) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value,ts=excluded.ts",
                         (name, val, now_str()))
            conn.commit()
        await safe_edit(event, f"✅ ماکرو «{name}» ذخیره شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^/([a-zA-Z\u0600-\u06FF_]+)$"))
    async def use_macro(event):
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT value FROM macros WHERE name=?", (name,)).fetchone()
        if row:
            await safe_edit(event, row["value"])
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماکروها$"))
    async def list_macros(event):
        record_cmd("ماکروها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM macros ORDER BY name LIMIT 30").fetchall()
        if not rows:
            await safe_edit(event, "📭 ماکرویی ثبت نشده!"); return
        lines = [f"• /{r['name']}: {r['value'][:30]}" for r in rows]
        await safe_edit(event, box(f"⚡ ماکروها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_ماکرو (.+)$"))
    async def del_macro(event):
        record_cmd("حذف_ماکرو")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM macros WHERE name=?", (name,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ ماکرو «{name}» حذف شد.")
        else:
            await safe_edit(event, f"❌ «{name}» پیدا نشد!")
    
    # ══ قالب ══════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قالب (.+)\|(.+)$"))
    async def set_template(event):
        record_cmd("قالب")
        name = event.pattern_match.group(1).strip()
        val  = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO templates(name,value,ts) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value,ts=excluded.ts",
                         (name, val, now_str()))
            conn.commit()
        await safe_edit(event, f"✅ قالب «{name}» ذخیره شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قالب (.+)$"))
    async def use_template(event):
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT value FROM templates WHERE name=?", (name,)).fetchone()
        if row:
            await safe_edit(event, row["value"])
        else:
            await safe_edit(event, f"❌ قالب «{name}» پیدا نشد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قالب‌ها$"))
    async def list_templates(event):
        record_cmd("قالب‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM templates ORDER BY name LIMIT 30").fetchall()
        if not rows:
            await safe_edit(event, "📭 قالبی ثبت نشده!"); return
        lines = [f"• {r['name']}: {r['value'][:30]}" for r in rows]
        await safe_edit(event, box(f"📄 قالب‌ها ({len(rows)})", lines))
    
    # ══ تبلیغات ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تبلیغ (.+)$"))
    async def set_ad(event):
        record_cmd("تبلیغ")
        text = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('ad_text',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (text,))
            conn.commit()
        await safe_edit(event, box("📢 متن تبلیغ", [f"متن: {text[:50]}", "شروع: شروع"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^گروه (.+)$"))
    async def add_group(event):
        record_cmd("گروه")
        gid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT OR IGNORE INTO ad_groups(gid) VALUES(?)", (gid,))
            conn.commit()
            cnt = conn.execute("SELECT COUNT(*) FROM ad_groups").fetchone()[0]
        await safe_edit(event, box("➕ گروه اضافه شد", [f"آیدی: {gid}", f"کل: {cnt}"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_گروه (.+)$"))
    async def del_group(event):
        record_cmd("حذف_گروه")
        gid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM ad_groups WHERE gid=?", (gid,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ گروه {gid} حذف شد.")
        else:
            await safe_edit(event, f"❌ {gid} در لیست نیست!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^گروه‌ها$"))
    async def list_groups(event):
        record_cmd("گروه‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM ad_groups LIMIT 30").fetchall()
        if not rows:
            await safe_edit(event, "📭 گروهی ثبت نشده!\nدستور: گروه @id"); return
        lines = [f"{i+1}. {r['gid']}" for i, r in enumerate(rows)]
        await safe_edit(event, box(f"📋 گروه‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمان (\d+)$"))
    async def set_interval(event):
        record_cmd("زمان")
        iv = int(event.pattern_match.group(1))
        if iv < 10:
            await safe_edit(event, "❌ حداقل ۱۰ ثانیه!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('ad_interval',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(iv),))
            conn.commit()
        await safe_edit(event, f"⏱ فاصله: {iv} ثانیه")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^شروع$"))
    async def start_ads(event):
        global _ads_running, _ads_task
        record_cmd("شروع_تبلیغ")
        with _db_lock:
            conn = get_conn()
            ad_text = (conn.execute("SELECT value FROM settings WHERE key='ad_text'").fetchone() or ("",))[0]
            groups  = [r["gid"] for r in conn.execute("SELECT gid FROM ad_groups").fetchall()]
            iv      = int((conn.execute("SELECT value FROM settings WHERE key='ad_interval'").fetchone() or (60,))[0])
        if not ad_text:
            await safe_edit(event, "❌ اول تبلیغ ثبت کن: تبلیغ [متن]"); return
        if not groups:
            await safe_edit(event, "❌ گروهی نداری: گروه @id"); return
        _ads_running = True
        _ads_task = asyncio.create_task(_broadcast_loop(client, ad_text, groups, iv))
        await safe_edit(event, box("🚀 تبلیغات شروع شد", [
            f"گروه‌ها: {len(groups)}", f"فاصله: {iv}s", "توقف: توقف"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^توقف$"))
    async def stop_ads(event):
        global _ads_running, _ads_task
        record_cmd("توقف_تبلیغ")
        _ads_running = False
        if _ads_task:
            _ads_task.cancel()
            _ads_task = None
        await safe_edit(event, "⏹ تبلیغات متوقف شد.")
    
    # ══ اسپم ══════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:اسپم|\.اسپم) (\d+) (.+)$"))
    async def spam_handler(event):
        global _spam_running
        record_cmd("اسپم")
        count = min(int(event.pattern_match.group(1)), 100)
        text  = event.pattern_match.group(2).strip()
        _spam_running = True
        await safe_edit(event, f"✨ ارسال {count} پیام...")
        try:
            for i in range(count):
                if not _spam_running:
                    break
                await client.send_message(event.chat_id, text)
                await asyncio.sleep(0.5)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.warning(f"اسپم: {e}")
        _spam_running = False
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:حذف|\.حذف)(?: (\d+))?$"))
    async def delete_msgs(event):
        record_cmd("حذف")
        m = event.pattern_match.group(1)
        count = int(m) if m else 10
        deleted = 0
        async for msg in client.iter_messages(event.chat_id, limit=count+5):
            if msg.out:
                try:
                    await msg.delete()
                    deleted += 1
                    if deleted >= count:
                        pass
                except Exception:
                    pass
                await asyncio.sleep(0.1)
        await client.send_message(event.chat_id, f"✅ {deleted} پیام حذف شد.", silent=True)
        await asyncio.sleep(1)
        async for m in client.iter_messages(event.chat_id, limit=1):
            try:
                await m.delete()
            except Exception:
                pass
    
    # ══ بفرست ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بفرست (گپ|کانال|پیوی|همه)$"))
    async def send_to_all(event):
        record_cmd("بفرست")
        target_type = event.pattern_match.group(1).strip()
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ روی پیام ریپلای کن!"); return
        await safe_edit(event, "⏳ در حال ارسال...")
        sent = err = 0
        async for d in client.iter_dialogs():
            t = type(d.entity).__name__
            ok = (
                (target_type == "گپ"     and (t == "Chat" or (t == "Channel" and getattr(d.entity,"megagroup",False))))
                or (target_type == "کانال"  and t == "Channel" and getattr(d.entity,"broadcast",False))
                or (target_type == "پیوی"   and t == "User")
                or (target_type == "همه")
            )
            if not ok: continue
            try:
                await client.forward_messages(d.entity, reply)
                sent += 1
            except Exception:
                err += 1
            await asyncio.sleep(2)
        await safe_edit(event, box("📤 ارسال", [f"✅ موفق: {sent}", f"❌ خطا: {err}"]))
    
    # ══ Sleep Mode / Panic Mode ════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حالت_خواب (روشن|خاموش)$"))
    async def sleep_mode(event):
        global _sleep_mode
        record_cmd("حالت_خواب")
        _sleep_mode = event.pattern_match.group(1) == "روشن"
        icon = "😴" if _sleep_mode else "☀️"
        await safe_edit(event, f"{icon} حالت خواب: {'فعال' if _sleep_mode else 'غیرفعال'}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حالت_اضطراری (روشن|خاموش)$"))
    async def panic_mode(event):
        global _panic_mode, _ads_running, _busy_active, _comment_running
        record_cmd("حالت_اضطراری")
        _panic_mode = event.pattern_match.group(1) == "روشن"
        if _panic_mode:
            _ads_running = False
            _busy_active = False
            _comment_running = False
            await safe_edit(event, "🚨 حالت اضطراری! همه اتوماسیون‌ها متوقف شدند.")
        else:
            await safe_edit(event, "✅ حالت اضطراری خاموش شد.")
    
    # ══ Smart Queue ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صف (.+) (.+) (\d+)$"))
    async def add_to_queue(event):
        record_cmd("صف")
        target = event.pattern_match.group(1).strip()
        text   = event.pattern_match.group(2).strip()
        delay  = int(event.pattern_match.group(3))
        send_at = (iran_now() + datetime.timedelta(seconds=delay)).strftime("%Y/%m/%d %H:%M:%S")
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO smart_queue(target,text,send_at) VALUES(?,?,?)",
                         (target, text[:500], send_at))
            conn.commit()
        await safe_edit(event, box("📨 صف اضافه شد", [
            f"مقصد: {target}", f"متن: {text[:30]}", f"ارسال: {delay}s دیگر"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_صف$"))
    async def list_queue(event):
        record_cmd("لیست_صف")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM smart_queue WHERE done=0 ORDER BY send_at LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 صف خالی است!"); return
        lines = [f"⏰ {r['send_at']} → {r['target']}: {r['text'][:20]}" for r in rows]
        await safe_edit(event, box(f"📨 صف ارسال ({len(rows)})", lines))
    
    # ══ ورک‌فلو ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وظیفه (.+?)\|(.+)$"))
    async def workflow_create(event):
        record_cmd("وظیفه")
        name  = event.pattern_match.group(1).strip()
        steps_raw = event.pattern_match.group(2).strip()
        steps = _parse_steps(steps_raw)
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO workflows(name,steps) VALUES(?,?) "
                "ON CONFLICT(name) DO UPDATE SET steps=excluded.steps",
                (name, json.dumps(steps, ensure_ascii=False))
            )
            conn.commit()
        await safe_edit(event, box("🔄 ورک‌فلو ایجاد شد", [f"نام: {name}", f"گام‌ها: {len(steps)}"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وظیفه_لیست$"))
    async def workflow_list(event):
        record_cmd("وظیفه_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM workflows ORDER BY name LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 ورک‌فلویی نیست!"); return
        lines = [f"⚙️ {r['name']} | {len(json.loads(r['steps']))} گام | {r['run_cnt']}x" for r in rows]
        await safe_edit(event, box(f"🔄 ورک‌فلوها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وظیفه_اجرا (.+)$"))
    async def workflow_run(event):
        record_cmd("وظیفه_اجرا")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT steps FROM workflows WHERE name=?", (name,)).fetchone()
        if not row:
            await safe_edit(event, f"❌ '{name}' پیدا نشد!"); return
        steps = json.loads(row["steps"])
        await safe_edit(event, f"⚙️ اجرا: {name}")
        await _execute_workflow(client, steps, event.chat_id)
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE workflows SET run_cnt=run_cnt+1, last_run=? WHERE name=?",
                         (now_str(), name))
            conn.commit()
        await client.send_message(event.chat_id, f"✅ '{name}' اجرا شد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وظیفه_حذف (.+)$"))
    async def workflow_delete(event):
        record_cmd("وظیفه_حذف")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM workflows WHERE name=?", (name,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ '{name}' حذف شد.")
        else:
            await safe_edit(event, f"❌ '{name}' نیست!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وظیفه_آمار$"))
    async def workflow_stats(event):
        record_cmd("وظیفه_آمار")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT name,run_cnt,last_run FROM workflows ORDER BY run_cnt DESC LIMIT 5").fetchall()
        if not rows:
            await safe_edit(event, "📭 ورک‌فلویی نیست!"); return
        lines = [f"• {r['name']}: {r['run_cnt']}x | {r['last_run'] or 'هرگز'}" for r in rows]
        await safe_edit(event, box("📊 آمار ورک‌فلو", lines))
    
    # ══ کامنت‌گذار ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کامنت_متن (.+)$"))
    async def comment_text(event):
        record_cmd("کامنت_متن")
        text = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO comment_config(key,value) VALUES('texts',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (text,))
            conn.commit()
        await safe_edit(event, f"✅ متن کامنت: {text[:40]}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کامنت_کانال (.+)$"))
    async def comment_channel(event):
        record_cmd("کامنت_کانال")
        ch = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO comment_config(key,value) VALUES('channel',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (ch,))
            conn.commit()
        await safe_edit(event, f"✅ کانال کامنت: {ch}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کامنت_شروع$"))
    async def comment_start(event):
        global _comment_running, _comment_task
        record_cmd("کامنت_شروع")
        with _db_lock:
            conn = get_conn()
            ch_row = conn.execute("SELECT value FROM comment_config WHERE key='channel'").fetchone()
            txt_row = conn.execute("SELECT value FROM comment_config WHERE key='texts'").fetchone()
        if not ch_row or not txt_row:
            await safe_edit(event, "❌ اول کامنت_کانال و کامنت_متن تنظیم کن!"); return
        _comment_running = True
        _comment_task = asyncio.create_task(
            _comment_loop(client, ch_row["value"], txt_row["value"].split("||"))
        )
        await safe_edit(event, box("💬 کامنت‌گذار شروع شد", [
            f"کانال: {ch_row['value']}", "توقف: کامنت_توقف"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کامنت_توقف$"))
    async def comment_stop(event):
        global _comment_running, _comment_task
        record_cmd("کامنت_توقف")
        _comment_running = False
        if _comment_task:
            _comment_task.cancel()
            _comment_task = None
        await safe_edit(event, "⏹ کامنت‌گذار متوقف شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کامنت_آمار$"))
    async def comment_stats(event):
        record_cmd("کامنت_آمار")
        with _db_lock:
            conn = get_conn()
            cnt_row = conn.execute("SELECT value FROM comment_config WHERE key='count'").fetchone()
        cnt = int(cnt_row["value"]) if cnt_row else 0
        st  = "🟢 فعال" if _comment_running else "🔴 متوقف"
        await safe_edit(event, box("💬 آمار کامنت‌گذار", [f"وضعیت: {st}", f"کل کامنت: {cnt}"]))
    

    # ─── analytics ───
    
    # ══ تاریخچه چت ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاریخچه(?: (\d+))?$"))
    async def history(event):
        record_cmd("تاریخچه")
        m = event.pattern_match.group(1)
        limit = min(int(m) if m else 10, 30)
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM chat_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (event.chat_id, limit)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 تاریخچه‌ای ثبت نشده!"); return
        rows = list(reversed(rows))
        lines = [
            f"{'←' if r['outgoing'] else '→'} [{r['ts'][11:16]}] {r['sender'][:8]}: {r['text'][:25]}"
            for r in rows[-10:]
        ]
        await safe_edit(event, box(f"📜 تاریخچه ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^جستجو_پیام (.+)$"))
    async def search_messages(event):
        record_cmd("جستجو_پیام")
        q = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM chat_memory WHERE text LIKE ? ORDER BY id DESC LIMIT 15",
                (f"%{q}%",)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"🔍 نتیجه‌ای برای «{q}» نیست."); return
        lines = [f"• [{r['ts'][:10]}] {r['sender'][:8]}: {r['text'][:30]}" for r in rows]
        await safe_edit(event, box(f"🔍 جستجو «{q}» ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماشین_زمان (\d+)$"))
    async def time_machine(event):
        record_cmd("ماشین_زمان")
        days = int(event.pattern_match.group(1))
        target = (iran_now() - timedelta(days=days)).strftime("%Y/%m/%d")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM chat_memory WHERE ts LIKE ? AND chat_id=? ORDER BY id LIMIT 10",
                (f"{target}%", event.chat_id)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"📭 پیامی برای {days} روز پیش ({target}) نیست."); return
        lines = [f"{'←' if r['outgoing'] else '→'} {r['ts'][11:16]} {r['sender'][:8]}: {r['text'][:25]}"
                 for r in rows]
        await safe_edit(event, box(f"⏰ ماشین زمان — {target}", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پخش_مجدد(?: (\d+))?$"))
    async def replay_conversation(event):
        record_cmd("پخش_مجدد")
        m = event.pattern_match.group(1)
        limit = min(int(m) if m else 10, 20)
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM chat_memory WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (event.chat_id, limit)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 پیامی برای پخش نیست."); return
        rows = list(reversed(rows))
        replay = "\n".join(
            f"{'👤' if r['outgoing'] else '💬'} {r['sender'][:10]}: {r['text'][:50]}"
            for r in rows
        )
        await safe_edit(event, f"🎬 پخش مجدد گفتگو:\n\n{replay}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_من$"))
    async def personal_analytics(event):
        record_cmd("آمار_من")
        with _db_lock:
            conn = get_conn()
            total_sent = conn.execute("SELECT COUNT(*) FROM chat_memory WHERE outgoing=1").fetchone()[0]
            total_recv = conn.execute("SELECT COUNT(*) FROM chat_memory WHERE outgoing=0").fetchone()[0]
            today = jalali()
            today_sent = conn.execute("SELECT COUNT(*) FROM chat_memory WHERE outgoing=1 AND ts LIKE ?", (f"{today}%",)).fetchone()[0]
            top_chats  = conn.execute(
                "SELECT chat_id, COUNT(*) as cnt FROM chat_memory WHERE outgoing=1 "
                "GROUP BY chat_id ORDER BY cnt DESC LIMIT 3"
            ).fetchall()
            cmds_today = conn.execute("SELECT COUNT(*) FROM cmd_history WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
        level = profile_val("level")
        xp    = profile_val("xp")
        await safe_edit(event, box("📊 تحلیل شخصی من", [
            f"ارسال کل: {total_sent}",
            f"دریافت کل: {total_recv}",
            f"ارسال امروز: {today_sent}",
            f"دستور امروز: {cmds_today}",
            f"سطح ONYX: {level} | XP: {xp}",
            "── فعال‌ترین چت‌ها ──",
        ] + [f"• {r['chat_id']}: {r['cnt']} پیام" for r in top_chats]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هیت_مپ$"))
    async def chat_heatmap(event):
        record_cmd("هیت_مپ")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT substr(ts,12,2) as hour, COUNT(*) as cnt FROM chat_memory "
                "WHERE outgoing=1 GROUP BY hour ORDER BY hour"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده‌ای برای هیت‌مپ نیست!"); return
        bars = "▁▂▃▄▅▆▇█"
        maxcnt = max(r["cnt"] for r in rows) or 1
        hours  = {r["hour"]: r["cnt"] for r in rows}
        grid = []
        for h in range(0, 24, 4):
            seg = "".join(
                bars[int((hours.get(f"{hh:02d}", 0) / maxcnt) * 7)]
                for hh in range(h, h+4)
            )
            grid.append(f"{h:02d}–{h+3:02d}: {seg}")
        await safe_edit(event, box("🗺️ هیت‌مپ ارسال", grid, "ساعت‌های فعال‌تر = نوار بلندتر"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^DNA_چت (.+)$"))
    async def dna_chat(event):
        record_cmd("DNA_چت")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
        except Exception:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT text FROM chat_memory WHERE chat_id=? LIMIT 200",
                (u.id,)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده‌ای برای تحلیل نیست!"); return
        words_all = " ".join(r["text"] for r in rows).split()
        stop = {"که","در","به","از","با","این","آن","را","می","است","بود","یک","هم","و","تو","من"}
        wf = defaultdict(int)
        for w in words_all:
            if len(w) > 2 and w not in stop:
                wf[w] += 1
        top = sorted(wf, key=wf.get, reverse=True)[:10]
        emoji_count = sum(1 for w in words_all if any(ord(c) > 0x1F300 for c in w))
        await safe_edit(event, box(f"🧬 DNA چت با {getattr(u,'first_name','?')}", [
            f"کل پیام: {len(rows)}",
            f"واژگان منحصر: {len(wf)}",
            f"اموجی: {emoji_count}",
            "── پرتکرارترین ──",
        ] + [f"• {w}: {wf[w]}" for w in top[:5]]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^خوانندگان_پنهان$"))
    async def ghost_readers(event):
        record_cmd("خوانندگان_پنهان")
        await safe_edit(event, "⏳ در حال بررسی...")
        result = []
        async for d in client.iter_dialogs(limit=50):
            if not d.is_group:
                break
            try:
                unread = d.unread_count or 0
                if unread == 0:
                    result.append(f"• {d.name[:25]}: خوانده شده ✅")
            except Exception:
                pass
        if not result:
            await safe_edit(event, "📭 اطلاعاتی نیست!"); return
        await safe_edit(event, box("👻 خوانندگان پنهان", result[:10], "گروه‌هایی که پیام‌ها خوانده شده"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌بینی_فعالیت$"))
    async def activity_forecast(event):
        record_cmd("پیش‌بینی_فعالیت")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT substr(ts,12,2) as hour, COUNT(*) as cnt FROM chat_memory "
                "WHERE outgoing=1 GROUP BY hour ORDER BY cnt DESC LIMIT 5"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده کافی نیست!"); return
        lines = [f"• ساعت {r['hour']}:00 — {r['cnt']} پیام" for r in rows]
        await safe_edit(event, box("🔮 پیش‌بینی فعالیت", lines, "ساعت‌هایی که معمولاً فعال‌تری"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تحول_امتیاز$"))
    async def evolution_score(event):
        record_cmd("تحول_امتیاز")
        level = profile_val("level")
        xp    = profile_val("xp")
        cmds  = profile_val("cmds_executed")
        days  = profile_val("active_days")
        dls   = profile_val("downloads")
        score = level * 500 + cmds * 2 + days * 50 + dls * 10
        stars = "⭐" * min(5, level)
        await safe_edit(event, box("🏆 امتیاز تحول", [
            f"{stars}",
            f"سطح: {level}",
            f"XP: {xp}/{level*100}",
            f"دستورات: {cmds}",
            f"روزهای فعال: {days}",
            f"دانلودها: {dls}",
            f"── امتیاز کل: {score} ──",
        ], WATERMARK))
    
    # ── Tracking handlers ────────────────────
    @client.on(events.NewMessage())
    async def _track_all_messages(event):
        """ذخیره همه پیام‌ها در حافظه چت"""
        try:
            text = event.text or ""
            if not text:
                return
            sender = await event.get_sender()
            name = ""
            if sender:
                name = f"{getattr(sender,'first_name','') or ''} {getattr(sender,'last_name','') or ''}".strip()
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO chat_memory(chat_id,uid,sender,text,outgoing,ts) VALUES(?,?,?,?,?,?)",
                    (event.chat_id, event.sender_id or 0, name[:60], text[:500],
                     1 if event.out else 0, now_str())
                )
                # نگه داشتن فقط آخرین 2000 پیام
                conn.execute(
                    "DELETE FROM chat_memory WHERE id NOT IN "
                    "(SELECT id FROM chat_memory ORDER BY id DESC LIMIT 2000)"
                )
                conn.commit()
        except Exception:
            pass
    

    # ─── security ───
    
    # ══ صندوق رمز ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_کلید (.+)$"))
    async def vault_setkey(event):
        record_cmd("صندوق_کلید")
        key = event.pattern_match.group(1).strip()
        if len(key) < 6:
            await safe_edit(event, "❌ کلید باید حداقل ۶ کاراکتر باشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('vault_key',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,))
            conn.commit()
        await safe_edit(event, "✅ کلید صندوق رمز تنظیم شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_ذخیره (.+)\|(.+)$"))
    async def vault_save(event):
        record_cmd("صندوق_ذخیره")
        key_name = event.pattern_match.group(1).strip()
        value    = event.pattern_match.group(2).strip()
        encrypted = vault_encrypt(value)
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO vault(key_name,value,ts) VALUES(?,?,?) "
                "ON CONFLICT(key_name) DO UPDATE SET value=excluded.value,ts=excluded.ts",
                (key_name, encrypted, now_str())
            )
            conn.commit()
        await safe_edit(event, f"🔐 «{key_name}» رمزگذاری و ذخیره شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_نمایش (.+)$"))
    async def vault_show(event):
        record_cmd("صندوق_نمایش")
        key_name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM vault WHERE key_name=?", (key_name,)).fetchone()
        if not row:
            await safe_edit(event, f"❌ «{key_name}» در صندوق نیست!"); return
        try:
            decrypted = vault_decrypt(row["value"])
            await safe_edit(event, box(f"🔐 صندوق: {key_name}", [
                f"مقدار: {decrypted[:60]}",
                f"ذخیره: {row['ts']}"
            ], "پیام رمزگذاری است"))
        except Exception:
            await safe_edit(event, "❌ خطا در رمزگشایی! کلید اشتباه است؟")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_لیست$"))
    async def vault_list(event):
        record_cmd("صندوق_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT key_name,ts FROM vault ORDER BY key_name LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 صندوق خالی است!"); return
        lines = [f"🔐 {r['key_name']} | {r['ts'][:10]}" for r in rows]
        await safe_edit(event, box(f"🔐 صندوق رمز ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_حذف (.+)$"))
    async def vault_delete(event):
        record_cmd("صندوق_حذف")
        key_name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM vault WHERE key_name=?", (key_name,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ «{key_name}» حذف شد.")
        else:
            await safe_edit(event, f"❌ «{key_name}» پیدا نشد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^صندوق_وضعیت$"))
    async def vault_status(event):
        record_cmd("صندوق_وضعیت")
        with _db_lock:
            conn = get_conn()
            cnt = conn.execute("SELECT COUNT(*) FROM vault").fetchone()[0]
            has_key = bool(conn.execute("SELECT value FROM settings WHERE key='vault_key'").fetchone())
        await safe_edit(event, box("🔐 وضعیت صندوق", [
            f"تعداد: {cnt} آیتم",
            f"کلید: {'✅ تنظیم شده' if has_key else '❌ تنظیم نشده'}",
            f"AES: {'✅ فعال' if _AES_AVAIL else '⚠️ Base64 (pip install pycryptodome)'}",
        ]))
    
    # ══ قفل کامل ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قفل_کامل (.+) (روشن|خاموش)$"))
    async def full_lock(event):
        record_cmd("قفل_کامل")
        lt_fa = event.pattern_match.group(1).strip()
        mode  = event.pattern_match.group(2)
        lt    = _LOCK_TYPES.get(lt_fa)
        if not lt:
            await safe_edit(event, f"❌ نوع قفل نامعتبر!\nنوع‌ها: {', '.join(_LOCK_TYPES)}"); return
        active = (mode == "روشن")
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO full_locks(lock_type,active) VALUES(?,?) "
                "ON CONFLICT(lock_type) DO UPDATE SET active=excluded.active",
                (lt, 1 if active else 0)
            )
            conn.commit()
        icon = "🔒" if active else "🔓"
        await safe_edit(event, f"{icon} قفل {lt_fa}: {mode}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_قفل_کامل$"))
    async def lock_status(event):
        record_cmd("وضعیت_قفل_کامل")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM full_locks").fetchall()
        lock_map = {r["lock_type"]: r["active"] for r in rows}
        lines = []
        for fa, en in _LOCK_TYPES.items():
            st = "🔒 قفل" if lock_map.get(en) else "🔓 باز"
            lines.append(f"• {fa}: {st}")
        await safe_edit(event, box("🔒 وضعیت قفل‌ها", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_سفید_کلمه(?: (.+))?$"))
    async def white_word(event):
        record_cmd("لیست_سفید_کلمه")
        word = (event.pattern_match.group(1) or "").strip()
        if word:
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT OR IGNORE INTO word_lists(list,word) VALUES('white',?)", (word,))
                conn.commit()
            await safe_edit(event, f"✅ «{word}» به لیست سفید اضافه شد.")
        else:
            with _db_lock:
                conn = get_conn()
                rows = conn.execute("SELECT word FROM word_lists WHERE list='white'").fetchall()
            words = [r["word"] for r in rows]
            await safe_edit(event, box("⬜ لیست سفید کلمات", words or ["(خالی)"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_سیاه_کلمه(?: (.+))?$"))
    async def black_word(event):
        record_cmd("لیست_سیاه_کلمه")
        word = (event.pattern_match.group(1) or "").strip()
        if word:
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT OR IGNORE INTO word_lists(list,word) VALUES('black',?)", (word,))
                conn.commit()
            await safe_edit(event, f"✅ «{word}» به لیست سیاه اضافه شد.")
        else:
            with _db_lock:
                conn = get_conn()
                rows = conn.execute("SELECT word FROM word_lists WHERE list='black'").fetchall()
            words = [r["word"] for r in rows]
            await safe_edit(event, box("⬛ لیست سیاه کلمات", words or ["(خالی)"]))
    
    @client.on(events.NewMessage(incoming=True))
    async def full_lock_guard(event):
        """نگهبان قفل کامل"""
        try:
            msg = event.message
            text = msg.text or ""
            # لینک
            if _lock_active("link") and ("http" in text or "t.me/" in text):
                await msg.delete()
                return
            # فوروارد
            if _lock_active("forward") and msg.forward:
                await msg.delete()
                return
            # رسانه
            if _lock_active("media") and msg.photo:
                await msg.delete()
                return
            # فایل
            if _lock_active("file") and msg.document and not msg.sticker and not msg.gif and not msg.voice:
                await msg.delete()
                return
            # صدا
            if _lock_active("voice") and msg.voice:
                await msg.delete()
                return
            # استیکر
            if _lock_active("sticker") and msg.sticker:
                await msg.delete()
                return
            # گیف
            if _lock_active("gif") and msg.gif:
                await msg.delete()
                return
            # لیست سیاه کلمات
            if text:
                with _db_lock:
                    conn = get_conn()
                    black = [r["word"] for r in conn.execute("SELECT word FROM word_lists WHERE list='black'").fetchall()]
                if any(w.lower() in text.lower() for w in black):
                    await msg.delete()
        except Exception:
            pass
    
    # ══ ریِد دتکتور ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریِد_روشن$"))
    async def raid_on(event):
        global _raid_active
        record_cmd("ریِد_روشن")
        _raid_active = True
        mt, ut = _raid_thresholds()
        await safe_edit(event, box("🚨 Raid Detector فعال", [
            f"حساسیت: {_raid_sensitivity}/10",
            f"پیام: {mt}/10s  کاربر: {ut}/30s",
            "خاموش: ریِد_خاموش",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریِد_خاموش$"))
    async def raid_off(event):
        global _raid_active
        record_cmd("ریِد_خاموش")
        _raid_active = False
        await safe_edit(event, "🔕 Raid Detector خاموش شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریِد_تنظیم (\d+)$"))
    async def raid_sensitivity(event):
        global _raid_sensitivity
        record_cmd("ریِد_تنظیم")
        v = int(event.pattern_match.group(1))
        if not 1 <= v <= 10:
            await safe_edit(event, "❌ بین ۱ تا ۱۰!"); return
        _raid_sensitivity = v
        lv = "🔴 بسیار حساس" if v >= 8 else ("🟠 حساس" if v >= 5 else "🟢 معمولی")
        await safe_edit(event, f"✅ حساسیت: {v}/10  {lv}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریِد_آمار$"))
    async def raid_stats(event):
        record_cmd("ریِد_آمار")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM raid_alerts ORDER BY id DESC LIMIT 5").fetchall()
            total = conn.execute("SELECT COUNT(*) FROM raid_alerts").fetchone()[0]
        st = "🟢" if _raid_active else "🔴"
        lines = [f"وضعیت: {st}  حساسیت: {_raid_sensitivity}",
                 f"کل حملات: {total}"]
        lines += [f"🚨 {r['ts']} | {r['type'][:20]}" for r in rows] or ["هیچ حمله‌ای ثبت نشده"]
        await safe_edit(event, box("🚨 آمار Raid", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریِد_سفید (.+)$"))
    async def raid_whitelist(event):
        record_cmd("ریِد_سفید")
        un = event.pattern_match.group(1).strip().lstrip("@")
        try:
            u = await client.get_entity(un)
            _raid_whitelist.add(u.id)
            await safe_edit(event, f"✅ @{un} به لیست سفید ریِد اضافه شد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(incoming=True))
    async def raid_monitor(event):
        if not _raid_active:
            return
        cid = event.chat_id
        sid = event.sender_id
        if not sid or sid in _raid_whitelist:
            return
        now = datetime.datetime.now()
        mt, ut = _raid_thresholds()
        _raid_msg_window[cid].append(now)
        c10 = now - datetime.timedelta(seconds=10)
        c30 = now - datetime.timedelta(seconds=30)
        _raid_msg_window[cid] = [t for t in _raid_msg_window[cid] if t > c30]
        _raid_user_window[cid].add(sid)
        rm = [t for t in _raid_msg_window[cid] if t > c10]
        rtype = ""
        if len(rm) >= mt:
            rtype = f"📨 سیل ({len(rm)}/10s)"
        elif len(_raid_user_window[cid]) >= ut:
            rtype = f"👥 انبوه ({len(_raid_user_window[cid])})"
        text = event.text or ""
        if text.count("http") >= 3 or text.count("t.me") >= 2:
            rtype = "🔗 اسپم لینک"
        if rtype:
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO raid_alerts(type,chat,ts) VALUES(?,?,?)",
                             (rtype, str(cid), now.strftime("%H:%M:%S")))
                conn.commit()
            _raid_user_window[cid] = set()
            try:
                me = await client.get_me()
                await client.send_message(me.id,
                    f"🚨 Raid!\nنوع: {rtype}\nچت: {cid}\nزمان: {now.strftime('%H:%M:%S')}")
            except Exception:
                pass
    
    # ══ بلاک / آنبلاک ════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بلاک$"))
    async def block_user(event):
        record_cmd("بلاک")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        try:
            await client(BlockRequest(sender))
            await safe_edit(event, f"🚫 {getattr(sender,'first_name','کاربر')} بلاک شد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آنبلاک$"))
    async def unblock_user(event):
        record_cmd("آنبلاک")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        try:
            await client(UnblockRequest(sender))
            await safe_edit(event, f"✅ {getattr(sender,'first_name','کاربر')} آنبلاک شد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    # ══ سکوت / دشمن / عشق ════════════════════
    _silenced: set = set()
    _enemies:  set = set()
    _loves:    set = set()
    ENEMY_MSGS = ["برو گم شو 🖕","حرف نزن 😤","با تو نیستم 😒","برو پی کارت 🙄"]
    LOVE_MSGS  = ["سلام عزیزم ❤️","دوستت دارم 🌹","خوشحالم پیام دادی 💕","جانم! 🥰"]
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^سکوت$"))
    async def silence(event):
        global _silenced
        record_cmd("سکوت")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _silenced.add(reply.sender_id)
        s = await reply.get_sender()
        await safe_edit(event, f"🔇 {getattr(s,'first_name','کاربر')} ساکت شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_سکوت$"))
    async def unsilence(event):
        global _silenced
        record_cmd("حذف_سکوت")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _silenced.discard(reply.sender_id)
        await safe_edit(event, "🔈 سکوت برداشته شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دشمن$"))
    async def add_enemy(event):
        global _enemies
        record_cmd("دشمن")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _enemies.add(reply.sender_id)
        s = await reply.get_sender()
        await safe_edit(event, f"👿 {getattr(s,'first_name','کاربر')} دشمن شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_دشمن$"))
    async def remove_enemy(event):
        global _enemies
        record_cmd("حذف_دشمن")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _enemies.discard(reply.sender_id)
        await safe_edit(event, "✅ از لیست دشمنان حذف شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^عشق$"))
    async def add_love(event):
        global _loves
        record_cmd("عشق")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _loves.add(reply.sender_id)
        s = await reply.get_sender()
        await safe_edit(event, f"❤️ {getattr(s,'first_name','کاربر')} به لیست عشق اضافه شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_عشق$"))
    async def remove_love(event):
        global _loves
        record_cmd("حذف_عشق")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        _loves.discard(reply.sender_id)
        await safe_edit(event, "✅ از لیست عشق حذف شد.")
    
    @client.on(events.NewMessage(incoming=True))
    async def social_handler(event):
        if not event.is_private:
            return
        sid = event.sender_id
        if sid in _silenced:
            try:
                await event.message.delete()
            except Exception:
                pass
        elif sid in _enemies:
            try:
                await event.reply(random.choice(ENEMY_MSGS))
            except Exception:
                pass
        elif sid in _loves:
            try:
                await event.reply(random.choice(LOVE_MSGS))
            except Exception:
                pass
    

    # ─── profile ───
    
    # ══ ساعت ایران — اصلاح‌شده V9 ════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ساعت_فعال$"))
    async def clock_on(event):
        global _clock_task
        record_cmd("ساعت_فعال")
        # بستن task قبلی در صورت وجود
        if _clock_task and not _clock_task.done():
            _clock_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(_clock_task), timeout=2)
            except Exception:
                pass
            _clock_task = None
        _clock_task = asyncio.create_task(_clock_loop(client))
        fn = setting("clock_font", "normal")
        now = iran_now()
        await safe_edit(event, box("⏰ ساعت فعال شد", [
            f"زمان فعلی: {jalali(now)} | {now.strftime('%H:%M')}",
            f"فونت: {fn}",
            "نام پروفایل به‌روز می‌شود",
            "خاموش: ساعت_خاموش",
            "وضعیت: وضعیت_ساعت",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ساعت_خاموش$"))
    async def clock_off(event):
        global _clock_task
        record_cmd("ساعت_خاموش")
        _clock_set_active(False)
        if _clock_task and not _clock_task.done():
            _clock_task.cancel()
            _clock_task = None
            await safe_edit(event, "✅ ساعت خاموش شد.")
        else:
            _clock_task = None
            await safe_edit(event, "ℹ️ ساعت از قبل خاموش بود.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فونت_ساعت$"))
    async def clock_font_list(event):
        record_cmd("فونت_ساعت")
        now = iran_now()
        t = now.strftime("%H:%M")
        lines = []
        for name, fn_func in CLOCK_FONTS.items():
            try:
                preview = fn_func(t)
            except Exception:
                preview = t
            lines.append(f"• {name:<15} → {preview}")
        lines.append("──────────────────────")
        lines.append("تغییر: فونت_ساعت_ست [نام]")
        await safe_edit(event, box(f"🔤 فونت‌های ساعت ({len(CLOCK_FONTS)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فونت_ساعت_ست (.+)$"))
    async def set_clock_font(event):
        record_cmd("فونت_ساعت_ست")
        name = event.pattern_match.group(1).strip()
        if name not in CLOCK_FONTS:
            opts = ", ".join(CLOCK_FONTS.keys())
            await safe_edit(event, f"❌ فونت نامعتبر!\nگزینه‌ها: {opts}"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('clock_font',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (name,))
            conn.commit()
        now = iran_now()
        preview = CLOCK_FONTS[name](now.strftime("%H:%M"))
        await safe_edit(event, box(f"✅ فونت ساعت تغییر کرد", [
            f"فونت: {name}",
            f"پیش‌نمایش: {preview}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_ساعت$"))
    async def clock_status(event):
        record_cmd("وضعیت_ساعت")
        is_running = bool(_clock_task and not _clock_task.done())
        is_saved   = _clock_is_active()
        st = "🟢 فعال" if is_running else "🔴 خاموش"
        fn = setting("clock_font", "normal")
        now = iran_now()
        date_fa = jalali(now)
        time_now = now.strftime("%H:%M:%S")
        try:
            preview = CLOCK_FONTS.get(fn, CLOCK_FONTS["normal"])(now.strftime("%H:%M"))
        except Exception:
            preview = now.strftime("%H:%M")
        await safe_edit(event, box("⏰ وضعیت ساعت", [
            f"وضعیت: {st}",
            f"فونت: {fn}",
            f"تاریخ: {date_fa}",
            f"ساعت: {time_now}",
            f"پیش‌نمایش: {preview}",
            f"ذخیره در DB: {'بله' if is_saved else 'خیر'}",
        ]))
    
    # ══ فونت متن ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_فونت$"))
    async def font_list(event):
        lines = [f"{name}: {sample}" for name, sample in FONT_SAMPLES.items()]
        await safe_edit(event, box("🖌 فونت‌ها", lines, "تغییر: فونت [نام] | حذف: حذف_فونت"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فونت (.+)$"))
    async def set_font_handler(event):
        record_cmd("فونت")
        name = event.pattern_match.group(1).strip()
        if name not in FONTS:
            await safe_edit(event, f"❌ فونت نامعتبر! از لیست_فونت ببین."); return
        set_font(name)
        sample = apply_font("Hello World", name)
        await safe_edit(event, f"✅ فونت: {name}\nنمونه: {sample}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^متن_عادی$"))
    async def font_normal(event):
        set_font("none")
        await safe_edit(event, "✅ فونت عادی فعال شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^متن_پررنگ$"))
    async def font_bold(event):
        set_font("bold")
        await safe_edit(event, "✅ فونت پررنگ: 𝗛𝗲𝗹𝗹𝗼")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^متن_کج$"))
    async def font_italic(event):
        set_font("italic")
        await safe_edit(event, "✅ فونت کج: 𝘏𝘦𝘭𝘭𝘰")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^متن_کد$"))
    async def font_mono(event):
        set_font("mono")
        await safe_edit(event, "✅ فونت کد: 𝙷𝚎𝚕𝚕𝚘")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_فونت$"))
    async def remove_font(event):
        set_font("none")
        await safe_edit(event, "✅ فونت غیرفعال شد.")
    
    @client.on(events.NewMessage(outgoing=True))
    async def font_applier(event):
        """اعمال فونت به پیام‌های خروجی"""
        try:
            mode = get_font()
            if mode == "none" or not event.text:
                return
            skip = ["منو","راهنما","فونت","متن_","حذف_","ساعت","پینگ","نسخه","درباره"]
            if any(event.text.startswith(s) for s in skip):
                return
            transformed = apply_font(event.text, mode)
            if transformed != event.text:
                await event.edit(transformed)
        except Exception:
            pass
    
    # ══ پروفایل کاربر ═════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پروفایل$"))
    async def profile_self(event):
        record_cmd("پروفایل")
        reply = await event.get_reply_message()
        try:
            if reply:
                u = await reply.get_sender()
            else:
                u = await client.get_me()
            fu = await client(GetFullUserRequest(u))
            bio = getattr(fu.full_user, "about", "") or "ندارد"
        except Exception as e:
            await safe_edit(event, f"❌ {e}"); return
        name = f"{getattr(u,'first_name','') or ''} {getattr(u,'last_name','') or ''}".strip()
        await safe_edit(event, box("👤 پروفایل", [
            f"نام: {name[:30]}",
            f"یوزر: @{getattr(u,'username','—') or '—'}",
            f"آیدی: {u.id}",
            f"بیو: {bio[:60]}",
            f"ربات: {'✅' if getattr(u,'bot',False) else '❌'}",
        ], WATERMARK))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپی_اسم$"))
    async def copy_name(event):
        record_cmd("کپی_اسم")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        name = f"{getattr(sender,'first_name','') or ''} {getattr(sender,'last_name','') or ''}".strip()
        await safe_edit(event, name or "بدون نام")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپی_بیو$"))
    async def copy_bio(event):
        record_cmd("کپی_بیو")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        try:
            fu = await client(GetFullUserRequest(sender))
            bio = getattr(fu.full_user, "about", "") or "بدون بیو"
        except Exception:
            bio = "بدون بیو"
        await safe_edit(event, bio)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپی_یوزر$"))
    async def copy_username(event):
        record_cmd("کپی_یوزر")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        un = getattr(sender, "username", "") or "بدون یوزرنیم"
        await safe_edit(event, f"@{un}" if un != "بدون یوزرنیم" else un)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپی_آیدی$"))
    async def copy_id(event):
        record_cmd("کپی_آیدی")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        sender = await reply.get_sender()
        await safe_edit(event, str(sender.id))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آیدی$"))
    async def show_id(event):
        record_cmd("آیدی")
        reply = await event.get_reply_message()
        if reply:
            sender = await reply.get_sender()
            await safe_edit(event, box("🆔 آیدی", [
                f"کاربر: {getattr(sender,'first_name','?')}",
                f"آیدی: {sender.id}",
                f"یوزر: @{getattr(sender,'username','—') or '—'}",
            ]))
        else:
            me = await client.get_me()
            await safe_edit(event, box("🆔 آیدی من", [f"آیدی: {me.id}"]))
    
    # ══ تغییر نام و بیو ═══════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^نام_من (.+)$"))
    async def set_my_name(event):
        record_cmd("نام_من")
        name = event.pattern_match.group(1).strip()
        parts = name.split(" ", 1)
        fn = parts[0]
        ln = parts[1] if len(parts) > 1 else ""
        try:
            await client(UpdateProfileRequest(first_name=fn, last_name=ln))
            await safe_edit(event, f"✅ نام تغییر کرد: {name}")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بیو_من (.+)$"))
    async def set_my_bio(event):
        record_cmd("بیو_من")
        bio = event.pattern_match.group(1).strip()
        try:
            await client(UpdateProfileRequest(about=bio[:70]))
            await safe_edit(event, f"✅ بیو تغییر کرد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    # ══ پینگ و اطلاعات سیستم ══════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پینگ$"))
    async def ping(event):
        record_cmd("پینگ")
        start = time.time()
        await safe_edit(event, "⏳")
        elapsed = (time.time() - start) * 1000
        conn_q = "🟢 عالی" if elapsed < 150 else ("🟡 متوسط" if elapsed < 400 else "🔴 ضعیف")
    
        cpu_u = ram_u = up_str = net_s = disk_s = "؟"
        try:
            cpu_u = f"{psutil.cpu_percent(interval=0.1):.1f}%"
            ram = psutil.virtual_memory()
            ram_u = f"{ram.percent:.0f}% ({ram.used//1024//1024}MB/{ram.total//1024//1024}MB)"
            secs = int(time.time() - psutil.boot_time())
            h, r = divmod(secs, 3600); m, s = divmod(r, 60)
            up_str = f"{h}h {m}m {s}s"
            n = psutil.net_io_counters()
            net_s = f"↑{n.bytes_sent//1024//1024}MB ↓{n.bytes_recv//1024//1024}MB"
            d = psutil.disk_usage("/")
            disk_s = f"{d.percent:.0f}% ({d.used//1024//1024//1024}G/{d.total//1024//1024//1024}G)"
        except Exception:
            pass
    
        ip_addr = ip_loc = "؟"
        try:
            loop = asyncio.get_event_loop()
            geo = await loop.run_in_executor(None, lambda: json.loads(
                urllib.request.urlopen(
                    "http://ip-api.com/json/?fields=status,country,city,query", timeout=4
                ).read().decode()
            ))
            if geo.get("status") == "success":
                ip_addr = geo.get("query", "؟")
                ip_loc  = f"{geo.get('city','')}, {geo.get('country','')}"
        except Exception:
            pass
    
        me = await client.get_me()
        now = iran_now()
        try:
            tel_v = tv.__version__
        except Exception:
            tel_v = "؟"
    
        db_size = 0
        try:
                db_size = os.path.getsize(DB_PATH) // 1024
        except Exception:
            pass
    
        await safe_edit(event, box("🏓 پینگ", [
            f"⚡ پینگ: {elapsed:.0f}ms  {conn_q}",
            f"🧠 CPU: {cpu_u}",
            f"💾 RAM: {ram_u}",
            f"💿 دیسک: {disk_s}",
            f"📡 شبکه: {net_s}",
            f"⏱ آپتایم: {up_str}",
            f"🌍 IP: {ip_addr}",
            f"📍 مکان: {ip_loc}",
            f"👤 {me.first_name} | {jalali(now)} {now.strftime('%H:%M')}",
            f"🐍 Python {sys.version_info.major}.{sys.version_info.minor} | Telethon {tel_v}",
            f"🗄️ دیتابیس: {db_size}KB",
        ], WATERMARK))
    
    # ══ نسخه / درباره ═════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^نسخه$"))
    async def version(event):
        record_cmd("نسخه")
        await safe_edit(event, box(f"💎 ONYX SELF", [
            f"نسخه: v{VERSION}",
            f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "پلتفرم: Termux / Linux",
            "کتابخانه: Telethon + SQLite",
        ], "سازنده: @Reyvoxe"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^qr (.+)$"))
    async def qr_code(event):
        record_cmd("qr")
        text = event.pattern_match.group(1).strip()
        encoded = urllib.parse.quote(text)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded}&size=300x300"
        await safe_edit(event, box("📷 QR Code", [
            f"متن: {text[:40]}",
            f"لینک: {qr_url[:60]}",
            "با مرورگر باز کنید",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^qrتلگرام(?: (.+))?$"))
    async def qr_telegram(event):
        record_cmd("qrتلگرام")
        arg = event.pattern_match.group(1)
        if arg:
            un = arg.strip().lstrip("@")
        else:
            me = await client.get_me()
            un = me.username or str(me.id)
        url = f"https://t.me/{un}"
        encoded = urllib.parse.quote(url)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded}&size=300x300"
        await safe_edit(event, box("📷 QR تلگرام", [
            f"@{un}",
            f"لینک: {url}",
            f"QR: {qr_url[:60]}",
        ]))
    
    # ══ بنر ASCII ═════════════════════════════
    _BANNER_CHARS = {
        'A':'▄▀▄\n█▀█\n█ █','B':'█▀▄\n█▀▄\n█▄▀','C':'▄▀▀\n█  \n▀▄▄',
        'D':'█▀▄\n█ █\n█▄▀','E':'█▀▀\n█▀ \n█▄▄','F':'█▀▀\n█▀ \n█  ',
        'G':'▄▀▀\n█▀▄\n▀▄▄','H':'█ █\n█▀█\n█ █','I':'▀█▀\n █ \n▀█▀',
        'O':'▄▀▄\n█ █\n▀▄▀','N':'█▄ █\n█ ▀█\n█  █','X':'▀▄▀\n ▄ \n▀▄▀',
        'Y':'▀▄▀\n █ \n █ ','Z':'▀▀▄\n▄▀ \n▄▄▄',
    }
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بنر (.+)$"))
    async def banner(event):
        record_cmd("بنر")
        text = event.pattern_match.group(1).strip().upper()[:8]
        lines = ["", "", ""]
        for ch in text:
            if ch in _BANNER_CHARS:
                parts = _BANNER_CHARS[ch].split("\n")
                while len(parts) < 3:
                    parts.append("   ")
                for i in range(3):
                    lines[i] += parts[i] + "  "
            elif ch == " ":
                for i in range(3):
                    lines[i] += "    "
        result = "\n".join(lines).rstrip()
        if not result.strip():
            await safe_edit(event, f"```\n{text}\n```"); return
        await safe_edit(event, f"```\n{result}\n```")
    
    # ══ پروفایل ONYX ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پروفایل_onyx$"))
    async def onyx_profile(event):
        record_cmd("پروفایل_onyx")
        level = profile_val("level")
        xp    = profile_val("xp")
        cmds  = profile_val("cmds_executed")
        msgs  = profile_val("msgs_sent")
        days  = profile_val("active_days")
        dls   = profile_val("downloads")
        start = profile_val("start_time")
        if start:
            uptime = int(time.time() - start)
            h, r = divmod(uptime, 3600)
            m, s = divmod(r, 60)
            up_str = f"{h}h {m}m"
        else:
            up_str = "؟"
        stars = "⭐" * min(10, level)
        bar_len = min(20, int(xp / max(level * 100, 1) * 20))
        bar = "█" * bar_len + "░" * (20 - bar_len)
        await safe_edit(event, box("💎 پروفایل ONYX", [
            f"سطح: {level}  {stars}",
            f"XP: [{bar}] {xp}/{level*100}",
            f"دستورات: {cmds}",
            f"پیام‌های ارسالی: {msgs}",
            f"دانلودها: {dls}",
            f"روزهای فعال: {days}",
            f"آپتایم: {up_str}",
        ], WATERMARK))
    
    @client.on(events.NewMessage(outgoing=True))
    async def track_outgoing(event):
        profile_incr("msgs_sent")
    
    

    # ─── media ───
    
    # ══ دانلود رسانه ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.dl (.+)$"))
    async def download_video(event):
        record_cmd(".dl")
        url = event.pattern_match.group(1).strip()
        await safe_edit(event, "📥 شروع دانلود ویدیو...")
        await _do_download(event, url, "video")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.mp3 (.+)$"))
    async def download_audio(event):
        record_cmd(".mp3")
        url = event.pattern_match.group(1).strip()
        await safe_edit(event, "🎵 شروع دانلود صدا...")
        await _do_download(event, url, "audio")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.info (.+)$"))
    async def video_info(event):
        record_cmd(".info")
        url = event.pattern_match.group(1).strip()
        await safe_edit(event, "⏳ دریافت اطلاعات...")
        try:
            cmd = ["yt-dlp", "--no-download", "--print",
                   "%(title)s||%(uploader)s||%(duration_string)s||%(view_count)s||%(like_count)s",
                   url]
            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, err = await asyncio.wait_for(result.communicate(), timeout=30)
            if result.returncode == 0:
                parts = out.decode(errors="ignore").strip().split("||")
                title  = parts[0] if len(parts) > 0 else "?"
                uploader = parts[1] if len(parts) > 1 else "?"
                dur    = parts[2] if len(parts) > 2 else "?"
                views  = parts[3] if len(parts) > 3 else "?"
                likes  = parts[4] if len(parts) > 4 else "?"
                await safe_edit(event, box("ℹ️ اطلاعات ویدیو", [
                    f"عنوان: {title[:50]}",
                    f"کانال: {uploader[:30]}",
                    f"مدت: {dur}",
                    f"بازدید: {views}",
                    f"لایک: {likes}",
                ]))
            else:
                await safe_edit(event, f"❌ خطا:\n{err.decode(errors='ignore')[:200]}")
        except FileNotFoundError:
            await safe_edit(event, "❌ yt-dlp نصب نیست!\nنصب: pip install yt-dlp")
        except asyncio.TimeoutError:
            await safe_edit(event, "❌ زمان درخواست تمام شد!")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاریخچه_دانلود$"))
    async def dl_history(event):
        record_cmd("تاریخچه_دانلود")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM dl_history ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 تاریخچه دانلودی نیست!"); return
        lines = [f"{'✅' if r['status']=='ok' else '❌'} {r['ts'][:10]} | {r['title'][:25]}" for r in rows]
        await safe_edit(event, box(f"📥 تاریخچه دانلود ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاک_کش_دانلود$"))
    async def clear_dl_cache(event):
        record_cmd("پاک_کش_دانلود")
        removed = 0
        for f in os.listdir(DL_DIR):
            try:
                os.remove(os.path.join(DL_DIR, f))
                removed += 1
            except Exception:
                pass
        await safe_edit(event, f"🧹 {removed} فایل از کش دانلود حذف شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مسیر_دانلود (.+)$"))
    async def set_dl_path(event):
        record_cmd("مسیر_دانلود")
        path = event.pattern_match.group(1).strip()
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                await safe_edit(event, f"❌ مسیر نامعتبر: {e}"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('dl_path',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (path,))
            conn.commit()
        await safe_edit(event, f"✅ مسیر دانلود: {path}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کیفیت_دانلود (.+)$"))
    async def set_dl_quality(event):
        record_cmd("کیفیت_دانلود")
        q = event.pattern_match.group(1).strip()
        valid = ["best", "1080p", "720p", "480p", "360p", "worst"]
        if q not in valid:
            await safe_edit(event, f"❌ کیفیت نامعتبر!\nگزینه‌ها: {', '.join(valid)}"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('dl_quality',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (q,))
            conn.commit()
        await safe_edit(event, f"✅ کیفیت دانلود: {q}")
    
    # ══ ذخیره فایل ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_ذخیره$"))
    async def save_file(event):
        record_cmd("فایل_ذخیره")
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await safe_edit(event, "❌ ریپلای روی یک فایل کن!"); return
        await safe_edit(event, "⏳ در حال ذخیره...")
        try:
            path = await reply.download_media(file=DL_DIR)
            fname = os.path.basename(path)
            size = os.path.getsize(path)
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO saved_files(category,filename,filepath,size,ts) VALUES(?,?,?,?,?)",
                             ("عمومی", fname, path, size, now_str()))
                conn.commit()
            await safe_edit(event, box("✅ فایل ذخیره شد", [
                f"نام: {fname[:40]}",
                f"حجم: {size//1024}KB",
                f"مسیر: {path[:50]}",
            ]))
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_لیست$"))
    async def list_files(event):
        record_cmd("فایل_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM saved_files ORDER BY id DESC LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 فایلی ذخیره نشده!"); return
        lines = [f"{i+1}. {r['filename'][:25]} ({r['size']//1024}KB)" for i, r in enumerate(rows)]
        await safe_edit(event, box(f"📁 فایل‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_ارسال (\d+)(?: (.+))?$"))
    async def send_file(event):
        record_cmd("فایل_ارسال")
        idx = int(event.pattern_match.group(1)) - 1
        target = event.pattern_match.group(2)
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM saved_files ORDER BY id DESC LIMIT 50").fetchall()
        if idx < 0 or idx >= len(rows):
            await safe_edit(event, "❌ شماره نادرست!"); return
        row = rows[idx]
        if not os.path.exists(row["filepath"]):
            await safe_edit(event, "❌ فایل پیدا نشد!"); return
        dest = target or event.chat_id
        try:
            await client.send_file(dest, row["filepath"], caption=f"📁 {row['filename'][:30]}")
            await safe_edit(event, f"✅ فایل ارسال شد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_حذف (\d+)$"))
    async def delete_file(event):
        record_cmd("فایل_حذف")
        idx = int(event.pattern_match.group(1)) - 1
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM saved_files ORDER BY id DESC LIMIT 50").fetchall()
        if idx < 0 or idx >= len(rows):
            await safe_edit(event, "❌ شماره نادرست!"); return
        row = rows[idx]
        try:
            os.remove(row["filepath"])
        except Exception:
            pass
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM saved_files WHERE id=?", (row["id"],))
            conn.commit()
        await safe_edit(event, f"✅ فایل «{row['filename'][:30]}» حذف شد.")
    
    # ══ فایل نهان ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_نهان(?: (.+))?$"))
    async def file_vault_save(event):
        record_cmd("فایل_نهان")
        cat = (event.pattern_match.group(1) or "عمومی").strip()
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await safe_edit(event, "❌ ریپلای روی یک فایل کن!"); return
        await safe_edit(event, "⏳ در حال ذخیره در صندوق فایل...")
        try:
            path = await reply.download_media(file=DL_DIR)
            fname = os.path.basename(path)
            size = os.path.getsize(path)
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO file_vault(category,filename,filepath,size,ts) VALUES(?,?,?,?,?)",
                             (cat, fname, path, size, now_str()))
                conn.commit()
            await safe_edit(event, f"🗄️ فایل در دسته «{cat}» ذخیره شد: {fname[:30]}")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^فایل_نهان_لیست(?: (.+))?$"))
    async def file_vault_list(event):
        record_cmd("فایل_نهان_لیست")
        cat = (event.pattern_match.group(1) or "").strip()
        with _db_lock:
            conn = get_conn()
            if cat:
                rows = conn.execute("SELECT * FROM file_vault WHERE category=? ORDER BY id DESC LIMIT 20", (cat,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM file_vault ORDER BY id DESC LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 فایلی در صندوق نیست!"); return
        lines = [f"• [{r['category']}] {r['filename'][:25]} ({r['size']//1024}KB)" for r in rows]
        await safe_edit(event, box(f"🗄️ صندوق فایل ({len(rows)})", lines))
    
    # ══ سیو پیام ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^سیو$"))
    async def save_msg(event):
        record_cmd("سیو")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای روی پیام مورد نظر!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO saved_messages(chat_id,msg_id,text,ts) VALUES(?,?,?,?)",
                         (event.chat_id, reply.id, (reply.text or "")[:500], now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM saved_messages").fetchone()[0]
            conn.commit()
        await safe_edit(event, f"📌 پیام سیو شد! (کل: {cnt})")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^سیو_100$"))
    async def save_100(event):
        record_cmd("سیو_100")
        await safe_edit(event, "⏳ سیو ۱۰۰ پیام اخیر...")
        saved = 0
        async for msg in client.iter_messages(event.chat_id, limit=100):
            if msg.text:
                with _db_lock:
                    conn = get_conn()
                    conn.execute("INSERT OR IGNORE INTO saved_messages(chat_id,msg_id,text,ts) VALUES(?,?,?,?)",
                                 (event.chat_id, msg.id, msg.text[:500], now_str()))
                    conn.commit()
                saved += 1
        await safe_edit(event, f"✅ {saved} پیام سیو شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_سیو$"))
    async def list_saved(event):
        record_cmd("لیست_سیو")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM saved_messages ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 پیامی سیو نشده!"); return
        lines = [f"• {r['ts'][:10]} | {r['text'][:30]}" for r in rows]
        await safe_edit(event, box(f"📥 سیوها ({len(rows)})", lines))
    
    # ══ پاکسازی هوشمند ════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاکسازی (لینک|عکس|فایل|گیف|استیکر)$"))
    async def smart_clean(event):
        record_cmd("پاکسازی")
        ctype = event.pattern_match.group(1)
        await safe_edit(event, f"🧹 پاکسازی {ctype}...")
        deleted = 0
        async for msg in client.iter_messages(event.chat_id, limit=200):
            to_del = False
            text = msg.text or ""
            if ctype == "لینک"    and ("http" in text or "t.me/" in text):
                to_del = True
            elif ctype == "عکس"   and msg.photo:
                to_del = True
            elif ctype == "فایل"  and msg.document and not msg.sticker and not msg.gif:
                to_del = True
            elif ctype == "گیف"   and msg.gif:
                to_del = True
            elif ctype == "استیکر" and msg.sticker:
                to_del = True
            if to_del:
                try:
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
        await client.send_message(event.chat_id, f"🧹 {deleted} {ctype} حذف شد.", silent=True)
        await asyncio.sleep(1)
        async for m in client.iter_messages(event.chat_id, limit=1):
            try: await m.delete()
            except Exception: pass
    
    # ══ انیمیشن‌ها ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^موشک$"))
    async def anim_rocket(event):
        record_cmd("موشک")
        frames = ["🌍", "🌍🚀", "  🚀💨", "    🚀✨", "      🚀🌟", "        🚀⭐", "          🌠"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قلب$"))
    async def anim_heart(event):
        record_cmd("قلب")
        frames = ["🖤","💔","❤️","💕","💞","💖","💝","💗","💓","💖✨"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.3)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لودینگ$"))
    async def anim_loading(event):
        record_cmd("لودینگ")
        frames = ["⏳","⌛","⏳","⌛","⏳ لود...","⌛ لود...","✅ آماده!"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماتریکس$"))
    async def anim_matrix(event):
        record_cmd("ماتریکس")
        chars = "01アイウエオカキクケコ"
        for _ in range(6):
            line = "".join(r.choice(chars) for _ in range(20))
            await safe_edit(event, f"`{line}`")
            await asyncio.sleep(0.3)
        await safe_edit(event, "💊 Wake up...")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آتش$"))
    async def anim_fire(event):
        record_cmd("آتش")
        frames = ["🔥","🔥🔥","🔥🔥🔥","🔥🔥🔥🔥","🌋🔥🔥🔥🔥","💥🌋🔥🔥🔥🔥","💥💥🌋🔥🔥"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.3)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مسجد$"))
    async def anim_mosque(event):
        record_cmd("مسجد")
        frames = ["🕌","🕌✨","🕌🌙","🕌🌙⭐","🕌🌙⭐✨","🌙🕌🌙","✨🕌✨"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^عقاب$"))
    async def anim_eagle(event):
        record_cmd("عقاب")
        frames = ["🦅","🦅 ","  🦅 "," 🦅  ","  🦅  🌤","   🦅✨"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^گل$"))
    async def anim_flower(event):
        record_cmd("گل")
        frames = ["🌱","🌿","🌺","🌸","🌸✨","🌸🌸","🌸🌸🌸💐"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مار$"))
    async def anim_snake(event):
        record_cmd("مار")
        frames = ["🐍","🐍➡️","➡️🐍","⬅️🐍","🐍⬆️","🐍✨","🎉"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تصادف$"))
    async def anim_crash(event):
        record_cmd("تصادف")
        frames = ["🚗","🚗💨","🚗💨🚕","💥","💥💥","🔥💥🔥","🚒🚑🚔"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دوچرخه$"))
    async def anim_bike(event):
        record_cmd("دوچرخه")
        frames = ["🚲","🚲💨"," 🚲💨","  🚲💨","   🚲💨","    🚲✨"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^خواب$"))
    async def anim_sleep(event):
        record_cmd("خواب")
        frames = ["😐","😴","😴💤","😴💤💤","😴💤💤💤 z","😴💤💤 Zz","😪🌙"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
    
    # ══ بازی‌های سریع ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مین_گیم تاس$"))
    async def dice_game(event):
        record_cmd("مین_گیم تاس")
        die = random.randint(1, 6)
        faces = ["⚀","⚁","⚂","⚃","⚄","⚅"]
        for _ in range(3):
            await safe_edit(event, f"🎲 {faces[random.randint(0,5)]}")
            await asyncio.sleep(0.3)
        await safe_edit(event, box("🎲 تاس", [f"نتیجه: {faces[die-1]} ({die})"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^مین_گیم ورق$"))
    async def card_game(event):
        record_cmd("مین_گیم ورق")
        suits  = ["♠️","♥️","♦️","♣️"]
        values = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
        card = f"{random.choice(values)}{random.choice(suits)}"
        await safe_edit(event, box("🃏 ورق", [f"کارت شما: {card}"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^میم$"))
    async def random_meme(event):
        record_cmd("میم")
        memes = [
            "وقتی بالاخره باگ رو پیدا می‌کنی 🐛➡️🗑️",
            "من: کدم کامله!\nکامپایلر: 47 خطا 😂",
            "وقتی ۳ ساعت روی باگ کار می‌کنی بعد یادت میاد ذخیره نکردی 💀",
            "Git commit -m 'fix' نه اولین نه آخرین 😅",
            "Stack Overflow منجی برنامه‌نویسان 🙏",
        ]
        await safe_edit(event, f"😂 {random.choice(memes)}")
    
    

    # ─── smart ───
    
    # ══ AI هوش مصنوعی ════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:ai|/ai) (.+)$"))
    async def ai_handler(event):
        record_cmd("ai")
        question = event.pattern_match.group(1).strip()
        await safe_edit(event, "🤖 پردازش...")
        await asyncio.sleep(0.6)
        answer = _ai_respond(question)
        await safe_edit(event, box("🤖 هوش مصنوعی", [
            f"❓ {question[:50]}",
            f"💡 {answer}",
        ], "ONYX AI | آفلاین و سریع"))
    
    # ══ Behavioral Clone ══════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کلون_شروع$"))
    async def clone_start(event):
        global _clone_recording
        record_cmd("کلون_شروع")
        _clone_recording = True
        await safe_edit(event, box("🧬 ضبط رفتار شروع شد", [
            "پیام‌های ارسالی ثبت می‌شوند",
            "توقف: کلون_توقف",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کلون_توقف$"))
    async def clone_stop(event):
        global _clone_recording
        record_cmd("کلون_توقف")
        _clone_recording = False
        with _db_lock:
            conn = get_conn()
            cnt = conn.execute("SELECT COUNT(*) FROM clone_data").fetchone()[0]
        rows = []
        with _db_lock:
            conn = get_conn()
            rows = [dict(r) for r in conn.execute("SELECT text,ts FROM clone_data ORDER BY id").fetchall()]
        _analyze_clone_data([{"text": r["text"], "ts": r["ts"]} for r in rows])
        await safe_edit(event, box("⏹ ضبط متوقف", [
            f"پیام‌ها: {cnt}",
            f"تأخیر: {_clone_stats['avg_delay']:.1f}s",
            f"کلمات: {', '.join(_clone_stats['common_words'][:5])}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کلون_اجرا (روشن|خاموش)$"))
    async def clone_run(event):
        global _clone_active
        record_cmd("کلون_اجرا")
        mode = event.pattern_match.group(1)
        _clone_active = (mode == "روشن")
        if _clone_active:
            with _db_lock:
                conn = get_conn()
                cnt = conn.execute("SELECT COUNT(*) FROM clone_data").fetchone()[0]
            if cnt < 5:
                await safe_edit(event, "⚠️ داده کافی نیست! اول کلون_شروع"); return
            rows = [dict(r) for r in conn.execute("SELECT text,ts FROM clone_data").fetchall()]
            _analyze_clone_data(rows)
        icon = "🟢" if _clone_active else "🔴"
        await safe_edit(event, f"🧬 کلون: {icon} {mode}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کلون_آمار$"))
    async def clone_stats(event):
        record_cmd("کلون_آمار")
        with _db_lock:
            conn = get_conn()
            cnt = conn.execute("SELECT COUNT(*) FROM clone_data").fetchone()[0]
        rs = "🟢" if _clone_recording else "🔴"
        ra = "🟢" if _clone_active else "🔴"
        cw = ", ".join(_clone_stats["common_words"][:5]) or "ندارد"
        await safe_edit(event, box("🧬 آمار Clone", [
            f"ضبط: {rs}  اجرا: {ra}",
            f"پیام‌ها: {cnt}",
            f"تأخیر: {_clone_stats['avg_delay']:.1f}s",
            f"اموجی: {_clone_stats['emoji_rate']:.0%}",
            f"کلمات پرکار: {cw[:40]}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کلون_پاک$"))
    async def clone_clear(event):
        global _clone_active, _clone_recording
        record_cmd("کلون_پاک")
        _clone_active = _clone_recording = False
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM clone_data")
            conn.commit()
        _clone_stats.update({"avg_delay":2.5,"emoji_rate":0.3,"avg_length":20,
                              "active_hours":[],"common_words":[]})
        await safe_edit(event, "✅ داده‌های کلون پاک شد.")
    
    @client.on(events.NewMessage(outgoing=True))
    async def clone_recorder(event):
        skip = ["کلون","منو","راهنما","ai ","وظیفه","اسپم","حذف"]
        if _clone_recording and event.text and not any(event.text.startswith(s) for s in skip):
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO clone_data(text,chat_id,ts) VALUES(?,?,?)",
                             (event.text[:500], event.chat_id, iran_now().isoformat()))
                conn.commit()
    
    @client.on(events.NewMessage(incoming=True))
    async def clone_auto_reply(event):
        if not _clone_active or not event.is_private:
            return
        text = event.text or ""
        if len(text) < 2:
            return
        delay = max(1.0, random.gauss(_clone_stats["avg_delay"], 1.0))
        await asyncio.sleep(delay)
        resp = _gen_clone_resp(text)
        if resp:
            try:
                await event.reply(resp)
            except Exception:
                pass
    
    # ══ Context / Smart Context ═══════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمینه_یاد (.+)$"))
    async def context_learn(event):
        record_cmd("زمینه_یاد")
        text = event.pattern_match.group(1).strip()
        _context_window[event.chat_id].append(text)
        if len(_context_window[event.chat_id]) > 50:
            _context_window[event.chat_id].pop(0)
        await safe_edit(event, f"🧠 ثبت شد (کل: {len(_context_window[event.chat_id])})")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمینه_خودکار (روشن|خاموش)$"))
    async def context_auto(event):
        global _context_auto
        record_cmd("زمینه_خودکار")
        _context_auto = event.pattern_match.group(1) == "روشن"
        icon = "🟢" if _context_auto else "🔴"
        await safe_edit(event, f"🧠 زمینه خودکار: {icon}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمینه_آمار$"))
    async def context_stats(event):
        record_cmd("زمینه_آمار")
        total = sum(len(v) for v in _context_window.values())
        await safe_edit(event, box("🧠 آمار Context", [
            f"زمینه‌ها: {len(_context_window)}",
            f"کل آیتم: {total}",
            f"خودکار: {'🟢' if _context_auto else '🔴'}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمینه_پاک$"))
    async def context_clear(event):
        record_cmd("زمینه_پاک")
        _context_window[event.chat_id].clear()
        await safe_edit(event, "🧹 زمینه پاک شد.")
    
    # ══ Intent ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^قانون_هدف (.+)\|(.+)$"))
    async def add_intent_rule(event):
        record_cmd("قانون_هدف")
        kws = event.pattern_match.group(1).strip()
        intent = event.pattern_match.group(2).strip()
        _INTENT_RULES[kws] = intent
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO intent_rules(keywords,intent) VALUES(?,?) ON CONFLICT(keywords) DO UPDATE SET intent=excluded.intent",
                         (kws, intent))
            conn.commit()
        await safe_edit(event, box("⚙️ Intent ثبت شد", [
            f"کلید: {kws[:30]}", f"Intent: {intent}", f"کل: {len(_INTENT_RULES)}"]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هدف_تشخیص (.+)$"))
    async def detect_intent_cmd(event):
        record_cmd("هدف_تشخیص")
        text = event.pattern_match.group(1).strip()
        intent, score = _detect_intent(text)
        conf = "🔴 ضعیف" if score < 0.3 else ("🟡 متوسط" if score < 0.7 else "🟢 قوی")
        await safe_edit(event, box("🎯 تشخیص Intent", [
            f"متن: {text[:40]}",
            f"Intent: {intent}",
            f"{conf} {score:.1%}",
        ]))
    
    # ══ وضعیت چت ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_ست (.+)\|(.+)$"))
    async def set_state(event):
        record_cmd("وضعیت_ست")
        k = event.pattern_match.group(1).strip()
        v = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO chat_states(chat_id,key,value) VALUES(?,?,?) ON CONFLICT(chat_id,key) DO UPDATE SET value=excluded.value",
                         (event.chat_id, k, v))
            conn.commit()
        await safe_edit(event, f"✅ {k} = {v}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_نمایش$"))
    async def show_state(event):
        record_cmd("وضعیت_نمایش")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM chat_states WHERE chat_id=?", (event.chat_id,)).fetchall()
        if not rows:
            await safe_edit(event, "📭 وضعیتی نیست!"); return
        lines = [f"• {r['key']}: {r['value']}" for r in rows]
        await safe_edit(event, box("📋 وضعیت چت", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_پاک$"))
    async def clear_state(event):
        record_cmd("وضعیت_پاک")
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM chat_states WHERE chat_id=?", (event.chat_id,))
            conn.commit()
        await safe_edit(event, "🧹 وضعیت پاک شد.")
    
    # ══ هدف‌ها ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هدف (.+)\|(\d+)(?: (.+))?$"))
    async def add_goal(event):
        record_cmd("هدف")
        title  = event.pattern_match.group(1).strip()
        target = int(event.pattern_match.group(2))
        unit   = (event.pattern_match.group(3) or "").strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO goals(title,target,unit,ts) VALUES(?,?,?,?)",
                         (title[:100], target, unit, now_str()))
            conn.commit()
        await safe_edit(event, f"🎯 هدف «{title[:30]}» ثبت شد: {target} {unit}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هدف_پیشرفت (\d+) (\d+)$"))
    async def goal_progress(event):
        record_cmd("هدف_پیشرفت")
        gid = int(event.pattern_match.group(1))
        val = int(event.pattern_match.group(2))
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE goals SET current=MIN(target, current+?) WHERE id=?", (val, gid))
            row = conn.execute("SELECT * FROM goals WHERE id=?", (gid,)).fetchone()
            conn.commit()
        if not row:
            await safe_edit(event, "❌ هدف پیدا نشد!"); return
        pct = row["current"] * 100 // max(row["target"], 1)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        done = row["current"] >= row["target"]
        if done:
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE goals SET done=1 WHERE id=?", (gid,))
                conn.commit()
        await safe_edit(event, box(f"🎯 {row['title'][:30]}", [
            f"[{bar}] {pct}%",
            f"{row['current']}/{row['target']} {row['unit']}",
            "✅ هدف محقق شد! 🎉" if done else "",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هدف‌ها$"))
    async def list_goals(event):
        record_cmd("هدف‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM goals ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 هدفی ثبت نشده!"); return
        lines = [
            f"{'✅' if r['done'] else '🎯'} {r['id']}. {r['title'][:25]} | {r['current']}/{r['target']} {r['unit']}"
            for r in rows
        ]
        await safe_edit(event, box(f"🎯 اهداف ({len(rows)})", lines))
    
    # ══ عادت ══════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^عادت (.+)$"))
    async def add_habit(event):
        record_cmd("عادت")
        title = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO habits(title) VALUES(?)", (title[:80],))
            conn.commit()
        await safe_edit(event, f"✅ عادت «{title[:30]}» ثبت شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^عادت_انجام (\d+)$"))
    async def habit_done(event):
        record_cmd("عادت_انجام")
        hid = int(event.pattern_match.group(1))
        today = jalali()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM habits WHERE id=?", (hid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ عادت پیدا نشد!"); return
        last = row["last_done"]
        streak = row["streak"]
        if last == today:
            await safe_edit(event, f"⚠️ «{row['title'][:25]}» قبلاً امروز انجام داده شده!"); return
        streak += 1
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE habits SET streak=?, last_done=? WHERE id=?", (streak, today, hid))
            conn.commit()
        await safe_edit(event, box(f"✅ {row['title'][:30]}", [
            f"🔥 streak: {streak} روز متوالی",
            f"آخرین: {today}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^عادت‌ها$"))
    async def list_habits(event):
        record_cmd("عادت‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM habits ORDER BY streak DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 عادتی ثبت نشده!"); return
        lines = [f"🔥 {r['id']}. {r['title'][:25]} | streak: {r['streak']}" for r in rows]
        await safe_edit(event, box(f"🔄 عادت‌ها ({len(rows)})", lines))
    
    # ══ کپسول زمان ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپسول (.+)\|(.+)\|(.+)$"))
    async def add_capsule(event):
        record_cmd("کپسول")
        title   = event.pattern_match.group(1).strip()
        content = event.pattern_match.group(2).strip()
        open_dt = event.pattern_match.group(3).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO time_capsules(title,content,open_date,ts) VALUES(?,?,?,?)",
                         (title[:100], content[:1000], open_dt, now_str()))
            conn.commit()
        await safe_edit(event, box("⏳ کپسول زمان ثبت شد", [
            f"عنوان: {title[:30]}",
            f"باز شدن: {open_dt}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپسول‌ها$"))
    async def list_capsules(event):
        record_cmd("کپسول‌ها")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM time_capsules ORDER BY open_date LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 کپسولی ثبت نشده!"); return
        lines = [
            f"{'✅' if r['open_date'] <= today else '⏳'} {r['id']}. {r['title'][:25]} | {r['open_date']}"
            for r in rows
        ]
        await safe_edit(event, box(f"⏳ کپسول‌های زمانی ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپسول_باز (\d+)$"))
    async def open_capsule(event):
        record_cmd("کپسول_باز")
        cid = int(event.pattern_match.group(1))
        today = jalali()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM time_capsules WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ کپسول پیدا نشد!"); return
        if row["open_date"] > today:
            await safe_edit(event, f"⏰ هنوز موقع باز کردن نرسیده!\nباز می‌شه: {row['open_date']}"); return
        await safe_edit(event, box(f"📬 کپسول: {row['title'][:30]}", [
            f"ثبت شد: {row['ts'][:10]}",
            f"محتوا: {row['content'][:200]}",
        ]))
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE time_capsules SET opened=1 WHERE id=?", (cid,))
            conn.commit()
    
    # ══ دستاوردها ══════════════════════════════
    ACHIEVEMENTS_DEF = {
        "first_cmd":      {"title":"🏆 اولین دستور", "check": lambda: profile_val("cmds_executed") >= 1},
        "cmd_10":         {"title":"🥈 ۱۰ دستور",    "check": lambda: profile_val("cmds_executed") >= 10},
        "cmd_100":        {"title":"🥇 ۱۰۰ دستور",   "check": lambda: profile_val("cmds_executed") >= 100},
        "cmd_1000":       {"title":"💎 هزار دستور",   "check": lambda: profile_val("cmds_executed") >= 1000},
        "level_5":        {"title":"⭐ سطح ۵",        "check": lambda: profile_val("level") >= 5},
        "level_10":       {"title":"🌟 سطح ۱۰",       "check": lambda: profile_val("level") >= 10},
        "active_7":       {"title":"📅 ۷ روز فعال",   "check": lambda: profile_val("active_days") >= 7},
        "active_30":      {"title":"🗓️ ۳۰ روز فعال", "check": lambda: profile_val("active_days") >= 30},
        "downloader":     {"title":"📥 اولین دانلود", "check": lambda: profile_val("downloads") >= 1},
        "dl_master":      {"title":"📦 ۱۰ دانلود",    "check": lambda: profile_val("downloads") >= 10},
    }
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستاوردها$"))
    async def achievements(event):
        record_cmd("دستاوردها")
        with _db_lock:
            conn = get_conn()
            unlocked = {r["id"] for r in conn.execute("SELECT id FROM achievements").fetchall()}
        lines = []
        for aid, ach in ACHIEVEMENTS_DEF.items():
            status = "✅" if aid in unlocked else "🔒"
            lines.append(f"{status} {ach['title']}")
        pct = len(unlocked) * 100 // max(len(ACHIEVEMENTS_DEF), 1)
        await safe_edit(event, box(f"🏆 دستاوردها ({len(unlocked)}/{len(ACHIEVEMENTS_DEF)})", lines,
                                   f"پیشرفت: {pct}%"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستاوردها_ریست$"))
    async def achievements_reset(event):
        record_cmd("دستاوردها_ریست")
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM achievements")
            conn.commit()
        await safe_edit(event, "✅ دستاوردها ریست شد.")
    
    # ══ Mimic Mode ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^میمیک (روشن|خاموش)$"))
    async def mimic_mode(event):
        record_cmd("میمیک")
        mode = event.pattern_match.group(1)
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES('mimic',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (mode,))
            conn.commit()
        await safe_edit(event, f"🪞 Mimic Mode: {mode}")
    
    @client.on(events.NewMessage(incoming=True))
    async def mimic_handler(event):
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT value FROM settings WHERE key='mimic'").fetchone()
        if not row or row["value"] != "روشن":
            return
        if not event.is_private or not event.text:
            return
        await asyncio.sleep(0.5)
        try:
            await event.reply(event.text)
        except Exception:
            pass
    
    # ══ Story Generator ════════════════════════
    _STORY_PARTS = {
        "شروع": ["یک روز","ناگهان","در شهری دور","زمانی بود که"],
        "شخص": ["یک جوان","یک دانشمند","یک مسافر","یک قهرمان"],
        "عمل": ["تصمیم گرفت","به جستجو رفت","پیدا کرد","دریافت کرد"],
        "موضوع": ["گنجی پنهان","راز بزرگ","دوستی عمیق","قدرتی عجیب"],
        "پایان": ["و زندگی‌اش برای همیشه تغییر کرد.","و این آغاز ماجرایی شگفت‌انگیز بود.","و همه چیز روشن شد."],
    }
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^داستان$"))
    async def story_generator(event):
        record_cmd("داستان")
        story = (
            f"{random.choice(_STORY_PARTS['شروع'])} "
            f"{random.choice(_STORY_PARTS['شخص'])} "
            f"{random.choice(_STORY_PARTS['عمل'])} "
            f"{random.choice(_STORY_PARTS['موضوع'])}. "
            f"{random.choice(_STORY_PARTS['پایان'])}"
        )
        await safe_edit(event, box("📖 داستان تصادفی", [story]))
    
    # ══ Predict Reply ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌بینی_پاسخ (.+)$"))
    async def predict_reply(event):
        record_cmd("پیش‌بینی_پاسخ")
        text = event.pattern_match.group(1).strip()
        intent, score = _detect_intent(text)
        if intent == "greeting":
            pred = ["سلام!", "چطوری؟", "درود!"]
        elif intent == "farewell":
            pred = ["خداحافظ!", "بای!", "موفق باشی!"]
        elif intent == "question":
            pred = ["نمی‌دونم...", "ببینم...", "فکر می‌کنم..."]
        elif intent == "positive":
            pred = ["ممنونم!", "خوشحالم!", "مرسی!"]
        else:
            pred = ["باشه", "اوکی", "درسته", "آره"]
        await safe_edit(event, box("🔮 پیش‌بینی پاسخ", [
            f"متن: {text[:40]}",
            f"Intent: {intent} ({score:.0%})",
            "پیش‌بینی‌ها:",
        ] + [f"• {p}" for p in pred]))
    
    

    # ─── monitoring ───
    
    # ══ داشبورد ONYX ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^واچ (.+)$"))
    async def add_watch(event):
        record_cmd("واچ")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO online_watch(uid,active) VALUES(?,1) ON CONFLICT(uid) DO UPDATE SET active=1", (u.id,))
                cnt = conn.execute("SELECT COUNT(*) FROM online_watch WHERE active=1").fetchone()[0]
                conn.commit()
            await safe_edit(event, box("👁 واچ فعال شد", [
                f"کاربر: {getattr(u,'first_name','?')}",
                f"آیدی: {u.id}",
                f"کل واچ: {cnt}",
            ]))
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^واچ_حذف (.+)$"))
    async def remove_watch(event):
        record_cmd("واچ_حذف")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE online_watch SET active=0 WHERE uid=?", (u.id,))
                conn.commit()
            await safe_edit(event, f"✅ واچ {getattr(u,'first_name','?')} حذف شد.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_واچ$"))
    async def list_watch(event):
        record_cmd("لیست_واچ")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT w.uid, c.name FROM online_watch w LEFT JOIN contacts c ON c.uid=w.uid WHERE w.active=1"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ کاربری واچ نشده!"); return
        lines = [f"👁 {r['name'] or r['uid']}" for r in rows]
        await safe_edit(event, box(f"👁 واچ‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_آنلاین (.+)$"))
    async def online_stats(event):
        record_cmd("آمار_آنلاین")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
        except Exception as e:
            await safe_edit(event, f"❌ {e}"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM online_log WHERE uid=? ORDER BY id DESC LIMIT 20",
                (u.id,)
            ).fetchall()
            total_online = conn.execute(
                "SELECT COUNT(*) FROM online_log WHERE uid=? AND status='online'", (u.id,)
            ).fetchone()[0]
        if not rows:
            await safe_edit(event, f"📭 لاگ آنلاینی برای {getattr(u,'first_name','?')} نیست."); return
        last5 = [f"• {r['ts']} | {r['status']}" for r in rows[:5]]
        await safe_edit(event, box(f"📊 آمار آنلاین {getattr(u,'first_name','?')}", [
            f"کل آنلاین: {total_online} بار",
            "── آخرین ──",
        ] + last5))
    
    # ══ اسنپ‌شات ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^اسنپ (.+)$"))
    async def snapshot(event):
        record_cmd("اسنپ")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
            fu = await client(GetFullUserRequest(u))
            data = {
                "first_name": getattr(u, "first_name", ""),
                "last_name":  getattr(u, "last_name", ""),
                "username":   getattr(u, "username", ""),
                "bio":        getattr(fu.full_user, "about", "") or "",
            }
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO snapshots(uid,data,ts) VALUES(?,?,?)",
                             (u.id, json.dumps(data, ensure_ascii=False), now_str()))
                conn.commit()
            await safe_edit(event, box(f"📸 اسنپ‌شات {getattr(u,'first_name','?')}", [
                f"نام: {data['first_name']} {data['last_name']}",
                f"یوزر: @{data['username'] or '—'}",
                f"بیو: {data['bio'][:40] or '—'}",
            ]))
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^اسنپ_مقایسه (.+)$"))
    async def snapshot_compare(event):
        record_cmd("اسنپ_مقایسه")
        arg = event.pattern_match.group(1).strip()
        try:
            u = await client.get_entity(arg.lstrip("@"))
            with _db_lock:
                conn = get_conn()
                rows = conn.execute(
                    "SELECT * FROM snapshots WHERE uid=? ORDER BY id DESC LIMIT 2",
                    (u.id,)
                ).fetchall()
            if len(rows) < 2:
                await safe_edit(event, "❌ حداقل ۲ اسنپ برای مقایسه نیاز است!"); return
            new_s = json.loads(rows[0]["data"])
            old_s = json.loads(rows[1]["data"])
            changes = []
            for key in new_s:
                if new_s[key] != old_s.get(key, ""):
                    changes.append(f"• {key}: «{old_s.get(key,'—')[:20]}» ← «{new_s[key][:20]}»")
            if not changes:
                await safe_edit(event, "✅ تغییری بین دو اسنپ نیست."); return
            await safe_edit(event, box(f"🔍 مقایسه اسنپ {getattr(u,'first_name','?')}", changes))
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    # ══ بکاپ و ریستور ════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بکاپ$"))
    async def backup(event):
        record_cmd("بکاپ")
        await safe_edit(event, "⏳ در حال بکاپ‌گیری...")
        ts = iran_now().strftime("%Y%m%d_%H%M%S")
        bk_file = os.path.join(BK_DIR, f"onyx_backup_{ts}.db")
        try:
            shutil.copy2(DB_PATH, bk_file)
            size = os.path.getsize(bk_file)
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO backups(filename,size,ts) VALUES(?,?,?)",
                             (os.path.basename(bk_file), size, now_str()))
                conn.commit()
            await safe_edit(event, box("✅ بکاپ گرفته شد", [
                f"فایل: onyx_backup_{ts}.db",
                f"حجم: {size//1024}KB",
                f"مسیر: {BK_DIR}",
            ]))
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریستور (.+)$"))
    async def restore(event):
        record_cmd("ریستور")
        fname = event.pattern_match.group(1).strip()
        bk_path = os.path.join(BK_DIR, fname)
        if not os.path.exists(bk_path):
            await safe_edit(event, f"❌ فایل پیدا نشد: {fname}"); return
        await safe_edit(event, "⚠️ ریستور اجرا می‌شود. بعد از ریستور بات را راه‌اندازی مجدد کنید.")
        try:
            shutil.copy2(bk_path, DB_PATH)
            await safe_edit(event, f"✅ ریستور از «{fname}» موفق.\n🔄 لطفاً بات را ری‌استارت کنید.")
        except Exception as e:
            await safe_edit(event, f"❌ {e}")
    
    # ══ پلاگین مانیجر ═════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^افزونه‌ها$"))
    async def list_plugins(event):
        record_cmd("افزونه‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM plugins ORDER BY name").fetchall()
        if not rows:
            await safe_edit(event, box("🧩 پلاگین‌ها", ["هیچ پلاگینی نصب نشده!",
                                                         "فایل‌های .py را در پوشه plugins/ بگذار"])); return
        lines = [f"{'🟢' if r['enabled'] else '🔴'} {r['name']}" for r in rows]
        await safe_edit(event, box(f"🧩 پلاگین‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^افزونه فعال (.+)$"))
    async def plugin_enable(event):
        record_cmd("افزونه فعال")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO plugins(name,enabled) VALUES(?,1) ON CONFLICT(name) DO UPDATE SET enabled=1", (name,))
            conn.commit()
        await safe_edit(event, f"🟢 پلاگین «{name}» فعال شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^افزونه غیرفعال (.+)$"))
    async def plugin_disable(event):
        record_cmd("افزونه غیرفعال")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO plugins(name,enabled) VALUES(?,0) ON CONFLICT(name) DO UPDATE SET enabled=0", (name,))
            conn.commit()
        await safe_edit(event, f"🔴 پلاگین «{name}» غیرفعال شد.")
    
    # ══ آمار روزانه ═══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_روزانه$"))
    async def daily_stats(event):
        record_cmd("آمار_روزانه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM daily_stats ORDER BY date DESC LIMIT 7"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 آماری ثبت نشده!"); return
        lines = [f"• {r['date']} | ارسال:{r['msgs_sent']} | دستور:{r['cmds']} | خطا:{r['errors']}"
                 for r in rows]
        await safe_edit(event, box("📈 آمار ۷ روز اخیر", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_ماهانه$"))
    async def monthly_stats(event):
        record_cmd("آمار_ماهانه")
        month = jalali()[:7]
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT SUM(msgs_sent) ms, SUM(msgs_recv) mr, SUM(cmds) c, SUM(errors) e "
                "FROM daily_stats WHERE date LIKE ?",
                (f"{month}%",)
            ).fetchone()
        await safe_edit(event, box(f"📊 آمار {month}", [
            f"ارسال: {rows['ms'] or 0}",
            f"دریافت: {rows['mr'] or 0}",
            f"دستورات: {rows['c'] or 0}",
            f"خطاها: {rows['e'] or 0}",
        ]))
    
    # ══ لاگ آنلاین واچ ════════════════════════
    @client.on(events.UserUpdate())
    async def user_update_handler(event):
        try:
            uid = event.user_id
            if not uid:
                return
            with _db_lock:
                conn = get_conn()
                row = conn.execute("SELECT uid FROM online_watch WHERE uid=? AND active=1", (uid,)).fetchone()
            if not row:
                return
            status = "unknown"
            if isinstance(event.status, UserStatusOnline):
                status = "online"
            elif isinstance(event.status, UserStatusOffline):
                status = "offline"
            elif isinstance(event.status, UserStatusRecently):
                status = "recently"
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO online_log(uid,status,ts) VALUES(?,?,?)",
                             (uid, status, now_str()))
                conn.commit()
            if status == "online":
                try:
                    me = await client.get_me()
                    with _db_lock:
                        conn2 = get_conn()
                        c_row = conn2.execute("SELECT name FROM contacts WHERE uid=?", (uid,)).fetchone()
                    name = (c_row["name"] if c_row else None) or str(uid)
                    await client.send_message(me.id, f"🟢 {name} آنلاین شد | {now_str()}")
                except Exception:
                    pass
        except Exception:
            pass
    
    

    # ─── tools ───
    
    # ══ Todo / کارها ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کار (.+)$"))
    async def add_todo(event):
        record_cmd("کار")
        text = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO todos(text,ts) VALUES(?,?)", (text[:200], now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM todos WHERE done=0").fetchone()[0]
            conn.commit()
        await safe_edit(event, f"✅ کار اضافه شد! ({cnt} کار باز)")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کارها$"))
    async def list_todos(event):
        record_cmd("کارها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM todos WHERE done=0 ORDER BY id LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ کاری نداری! 🎉"); return
        lines = [f"{r['id']}. {r['text'][:40]}" for r in rows]
        await safe_edit(event, box(f"📋 کارها ({len(rows)})", lines, "انجام: کار_انجام [شماره]"))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کار_انجام (\d+)$"))
    async def done_todo(event):
        record_cmd("کار_انجام")
        tid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT text FROM todos WHERE id=?", (tid,)).fetchone()
            if not row:
                await safe_edit(event, "❌ کار پیدا نشد!"); return
            conn.execute("UPDATE todos SET done=1 WHERE id=?", (tid,))
            conn.commit()
        await safe_edit(event, f"✅ «{row['text'][:40]}» انجام شد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کار_حذف (\d+)$"))
    async def del_todo(event):
        record_cmd("کار_حذف")
        tid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM todos WHERE id=?", (tid,))
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"✅ کار {tid} حذف شد.")
        else:
            await safe_edit(event, "❌ پیدا نشد!")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^کارهای_انجام‌شده$"))
    async def done_todos(event):
        record_cmd("کارهای_انجام‌شده")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM todos WHERE done=1 ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 کاری انجام نشده!"); return
        lines = [f"✅ {r['id']}. {r['text'][:35]}" for r in rows]
        await safe_edit(event, box(f"✅ انجام‌شده‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاک_انجام‌شده$"))
    async def clear_done(event):
        record_cmd("پاک_انجام‌شده")
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM todos WHERE done=1")
            conn.commit()
        await safe_edit(event, f"🧹 {c.rowcount} کار انجام‌شده پاک شد.")
    
    # ══ تقویم ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تولد (.+) (\d{4}/\d{2}/\d{2})$"))
    async def add_birthday(event):
        record_cmd("تولد")
        name = event.pattern_match.group(1).strip()
        date = event.pattern_match.group(2)
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO calendar(type,date,title,added) VALUES(?,?,?,?)",
                         ("تولد", date, name, now_str()))
            conn.commit()
        await safe_edit(event, f"🎂 تولد {name} در {date} ثبت شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^رویداد (.+) (\d{4}/\d{2}/\d{2})$"))
    async def add_event(event):
        record_cmd("رویداد")
        title = event.pattern_match.group(1).strip()
        date  = event.pattern_match.group(2)
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO calendar(type,date,title,added) VALUES(?,?,?,?)",
                         ("رویداد", date, title, now_str()))
            conn.commit()
        await safe_edit(event, f"📅 رویداد «{title}» در {date} ثبت شد.")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تقویم$"))
    async def show_calendar(event):
        record_cmd("تقویم")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM calendar ORDER BY date LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ رویدادی ثبت نشده!"); return
        lines = []
        for r in rows:
            past = r["date"] < today
            icon = "✅" if past else ("🔜" if r["date"] == today else "📅")
            tp   = "🎂" if r["type"] == "تولد" else "📌"
            lines.append(f"{icon}{tp} {r['date']} | {r['title'][:25]}")
        await safe_edit(event, box(f"📅 تقویم ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تقویم_امروز$"))
    async def calendar_today(event):
        record_cmd("تقویم_امروز")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM calendar WHERE date=?", (today,)).fetchall()
        if not rows:
            await safe_edit(event, f"📭 هیچ رویدادی برای امروز ({today}) نیست!"); return
        lines = [f"{'🎂' if r['type']=='تولد' else '📌'} {r['title'][:30]}" for r in rows]
        await safe_edit(event, box(f"🎉 رویدادهای امروز", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تقویم_حذف (\d+)$"))
    async def del_calendar(event):
        record_cmd("تقویم_حذف")
        eid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM calendar WHERE id=?", (eid,))
            conn.commit()
        await safe_edit(event, f"✅ رویداد {eid} حذف شد." if c.rowcount else "❌ پیدا نشد!")
    
    # ══ هزینه‌یاب ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هزینه (.+) (\d+)(?: (.+))?$"))
    async def add_expense(event):
        record_cmd("هزینه")
        title = event.pattern_match.group(1).strip()
        amount = int(event.pattern_match.group(2))
        cat = (event.pattern_match.group(3) or "عمومی").strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO expenses(title,amount,cat,date) VALUES(?,?,?,?)",
                         (title[:100], amount, cat, jalali()))
            conn.commit()
        await safe_edit(event, f"💸 هزینه «{title[:25]}»: {amount:,} ریال در دسته «{cat}»")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هزینه‌ها$"))
    async def list_expenses(event):
        record_cmd("هزینه‌ها")
        with _db_lock:
            conn = get_conn()
            rows  = conn.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 15").fetchall()
            total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        if not rows:
            await safe_edit(event, "📭 هزینه‌ای ثبت نشده!"); return
        lines = [f"• {r['date']} [{r['cat']}] {r['title'][:20]}: {r['amount']:,}" for r in rows[:10]]
        lines.append(f"── کل: {total:,} ریال")
        await safe_edit(event, box(f"💰 هزینه‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هزینه_ماه$"))
    async def expense_month(event):
        record_cmd("هزینه_ماه")
        month = jalali()[:7]
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT cat, SUM(amount) total FROM expenses WHERE date LIKE ? GROUP BY cat ORDER BY total DESC",
                (f"{month}%",)
            ).fetchall()
            month_total = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date LIKE ?", (f"{month}%",)
            ).fetchone()[0]
        if not rows:
            await safe_edit(event, f"📭 هزینه‌ای در {month} نیست!"); return
        lines = [f"• {r['cat']}: {r['total']:,}" for r in rows]
        lines.append(f"── کل: {month_total:,} ریال")
        await safe_edit(event, box(f"💰 هزینه‌ها {month}", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^هزینه_حذف (\d+)$"))
    async def del_expense(event):
        record_cmd("هزینه_حذف")
        eid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
            conn.commit()
        await safe_edit(event, f"✅ هزینه {eid} حذف شد." if c.rowcount else "❌ پیدا نشد!")
    
    # ══ بوکمارک ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بوکمارک$"))
    async def add_bookmark(event):
        record_cmd("بوکمارک")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای روی پیام مورد نظر!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO bookmarks(text,chat_id,msg_id,ts) VALUES(?,?,?,?)",
                         ((reply.text or "")[:300], event.chat_id, reply.id, now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
            conn.commit()
        await safe_edit(event, f"🔖 بوکمارک شد! (کل: {cnt})")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بوکمارک‌ها$"))
    async def list_bookmarks(event):
        record_cmd("بوکمارک‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM bookmarks ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 بوکمارکی نیست!"); return
        lines = [f"• {r['ts'][:10]} | {r['text'][:35] or '[رسانه]'}" for r in rows]
        await safe_edit(event, box(f"🔖 بوکمارک‌ها ({len(rows)})", lines))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بوکمارک_حذف (\d+)$"))
    async def del_bookmark(event):
        record_cmd("بوکمارک_حذف")
        bid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM bookmarks WHERE id=?", (bid,))
            conn.commit()
        await safe_edit(event, f"✅ بوکمارک {bid} حذف شد." if c.rowcount else "❌ پیدا نشد!")
    
    # ══ علاقه‌مندی ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^لایک$"))
    async def add_favorite(event):
        record_cmd("لایک")
        reply = await event.get_reply_message()
        if not reply:
            await safe_edit(event, "❌ ریپلای کن!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO favorites(type,text,chat_id,msg_id,ts) VALUES(?,?,?,?,?)",
                         ("message", (reply.text or "")[:300], event.chat_id, reply.id, now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
            conn.commit()
        await safe_edit(event, f"❤️ به علاقه‌مندی‌ها اضافه شد! (کل: {cnt})")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^علاقه‌مندی‌ها$"))
    async def list_favorites(event):
        record_cmd("علاقه‌مندی‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM favorites ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 علاقه‌مندی‌ای نیست!"); return
        lines = [f"❤️ {r['ts'][:10]} | {r['text'][:35] or '[رسانه]'}" for r in rows]
        await safe_edit(event, box(f"❤️ علاقه‌مندی‌ها ({len(rows)})", lines))
    
    # ══ ماشین حساب ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?:حساب|calc) (.+)$"))
    async def calculator(event):
        record_cmd("حساب")
        expr = event.pattern_match.group(1).strip()
        safe_expr = re.sub(r"[^0-9+\-*/().^%e πsin cos tan sqrt log ]", "", expr)
        safe_expr = safe_expr.replace("^", "**").replace("π", str(math.pi))
        # تبدیل توابع ریاضی
        allowed = {
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
            "abs": abs, "pi": math.pi, "e": math.e, "ceil": math.ceil,
            "floor": math.floor, "round": round,
        }
        try:
            result = eval(safe_expr, {"__builtins__": {}}, allowed)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            await safe_edit(event, box("🔢 ماشین حساب", [
                f"ورودی: {expr[:50]}",
                f"نتیجه: {result:,}",
            ]))
        except ZeroDivisionError:
            await safe_edit(event, "❌ تقسیم بر صفر!")
        except Exception:
            await safe_edit(event, f"❌ عبارت نامعتبر: {expr[:40]}")
    
    # ══ مبدّل واحد ════════════════════════════
    UNIT_MAP = {
        "km_mi":  (1, 0.621371, "کیلومتر", "مایل"),
        "mi_km":  (1, 1.60934,  "مایل",    "کیلومتر"),
        "kg_lb":  (1, 2.20462,  "کیلوگرم", "پوند"),
        "lb_kg":  (1, 0.453592, "پوند",    "کیلوگرم"),
        "c_f":    (None, None,  "سلسیوس",  "فارنهایت"),
        "f_c":    (None, None,  "فارنهایت","سلسیوس"),
        "m_ft":   (1, 3.28084,  "متر",     "فوت"),
        "ft_m":   (1, 0.3048,   "فوت",     "متر"),
        "usd_irr":(1, 680000,   "دلار",    "ریال"),
    }
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تبدیل (.+) (.+) (.+)$"))
    async def convert(event):
        record_cmd("تبدیل")
        try:
            val   = float(event.pattern_match.group(1).replace(",", ""))
            from_ = event.pattern_match.group(2).lower()
            to_   = event.pattern_match.group(3).lower()
            key   = f"{from_}_{to_}"
        except Exception:
            await safe_edit(event, "❌ فرمت: تبدیل [عدد] [واحد_مبدا] [واحد_مقصد]"); return
        if key not in UNIT_MAP:
            await safe_edit(event, f"❌ تبدیل «{from_}» به «{to_}» پشتیبانی نمی‌شود!\nمثال: تبدیل 100 km mi"); return
        u = UNIT_MAP[key]
        if key == "c_f":
            result = val * 9/5 + 32
        elif key == "f_c":
            result = (val - 32) * 5/9
        else:
            result = val * u[1]
        if isinstance(result, float) and abs(result) > 1000:
            await safe_edit(event, box("🔄 تبدیل واحد", [
                f"ورودی: {val:,} {u[2]}",
                f"نتیجه: {result:,.2f} {u[3]}",
            ]))
        else:
            await safe_edit(event, box("🔄 تبدیل واحد", [
                f"ورودی: {val} {u[2]}",
                f"نتیجه: {result:.4f} {u[3]}",
            ]))
    
    # ══ زمان‌سنج ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تایمر (\d+)(?: (.+))?$"))
    async def timer(event):
        record_cmd("تایمر")
        secs = int(event.pattern_match.group(1))
        label = (event.pattern_match.group(2) or "تایمر").strip()
        if secs > 3600:
            await safe_edit(event, "❌ حداکثر ۳۶۰۰ ثانیه!"); return
        await safe_edit(event, f"⏱ {label}: {secs}s شروع شد...")
        await asyncio.sleep(secs)
        try:
            await event.edit(box(f"⏰ {label}", [
                f"✅ {secs} ثانیه گذشت!",
                f"زمان: {now_str()}",
            ]))
            me = await client.get_me()
            await client.send_message(me.id, f"⏰ تایمر «{label}» تموم شد! ({secs}s)")
        except Exception:
            pass
    
    # ══ ترجمه آنلاین ════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ترجمه (.+)$"))
    async def translate(event):
        record_cmd("ترجمه")
        text = event.pattern_match.group(1).strip()
        await safe_edit(event, "🌐 در حال ترجمه...")
        try:
            from deep_translator import GoogleTranslator
            # تشخیص خودکار زبان و ترجمه به فارسی
            # اگر متن فارسی بود → انگلیسی، وگرنه → فارسی
            fa_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            if fa_chars > len(text) * 0.3:
                dest = "en"
                dest_name = "انگلیسی"
            else:
                dest = "fa"
                dest_name = "فارسی"
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: GoogleTranslator(source="auto", target=dest).translate(text)
            )
            await safe_edit(event, box("🌐 ترجمه آنلاین", [
                f"متن: {text[:60]}",
                f"زبان مقصد: {dest_name}",
                f"ترجمه: {result}",
            ], "Google Translate | deep-translator"))
        except ImportError:
            await safe_edit(event, box("❌ کتابخانه نصب نیست", [
                "دستور نصب:",
                "pip install deep-translator",
            ]))
        except Exception as e:
            await safe_edit(event, f"❌ خطا در ترجمه: {e}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ترجمه_به (.+?) (.+)$"))
    async def translate_to(event):
        record_cmd("ترجمه_به")
        lang = event.pattern_match.group(1).strip().lower()
        text = event.pattern_match.group(2).strip()
        await safe_edit(event, "🌐 در حال ترجمه...")
        lang_map = {
            "فا": "fa", "fa": "fa", "فارسی": "fa",
            "en": "en", "انگلیسی": "en",
            "ar": "ar", "عربی": "ar",
            "tr": "tr", "ترکی": "tr",
            "de": "de", "آلمانی": "de",
            "fr": "fr", "فرانسوی": "fr",
            "es": "es", "اسپانیایی": "es",
            "ru": "ru", "روسی": "ru",
            "zh": "zh-CN", "چینی": "zh-CN",
            "ja": "ja", "ژاپنی": "ja",
            "ko": "ko", "کره‌ای": "ko",
            "it": "it", "ایتالیایی": "it",
        }
        dest = lang_map.get(lang, lang)
        try:
            from deep_translator import GoogleTranslator
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: GoogleTranslator(source="auto", target=dest).translate(text)
            )
            await safe_edit(event, box("🌐 ترجمه آنلاین", [
                f"متن: {text[:60]}",
                f"زبان: {lang} ({dest})",
                f"ترجمه: {result}",
            ], "Google Translate | deep-translator"))
        except ImportError:
            await safe_edit(event, "❌ نصب کن: pip install deep-translator")
        except Exception as e:
            await safe_edit(event, f"❌ خطا: {e}")


    
    # ══ رمز عبور ══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_تولید(?: (\d+))?(?: (.+))?$"))
    async def gen_password(event):
        record_cmd("رمز_تولید")
        length = int(event.pattern_match.group(1) or 16)
        length = max(6, min(64, length))
        mode   = (event.pattern_match.group(2) or "قوی").strip()
        if mode == "ساده":
            chars = string.ascii_letters + string.digits
        elif mode == "عدد":
            chars = string.digits
        else:  # قوی
            chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pwd = "".join(random.choice(chars) for _ in range(length))
        await safe_edit(event, box("🔑 رمز تولید شد", [
            f"رمز: {pwd}",
            f"طول: {length}",
            f"حالت: {mode}",
            "⚠️ پیام را بعد از کپی حذف کن!",
        ]))
    
    # ══ متن پنهان ═════════════════════════════
    _ZWSP  = "\u200b"
    _ZWNJ  = "\u200c"
    _ZWJ   = "\u200d"
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^پنهان (.+)\|(.+)$"))
    async def hide_text(event):
        record_cmd("پنهان")
        cover  = event.pattern_match.group(1).strip()
        secret = event.pattern_match.group(2).strip()
        encoded = ""
        for ch in secret:
            b = bin(ord(ch))[2:].zfill(8)
            encoded += "".join(_ZWSP if bit == "0" else _ZWNJ for bit in b) + _ZWJ
        await safe_edit(event, cover + encoded)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^آشکار$"))
    async def reveal_text(event):
        record_cmd("آشکار")
        reply = await event.get_reply_message()
        if not reply or not reply.text:
            await safe_edit(event, "❌ ریپلای کن!"); return
        text = reply.text
        encoded_part = ""
        for ch in text:
            if ch in (_ZWSP, _ZWNJ, _ZWJ):
                encoded_part += ch
        if not encoded_part:
            await safe_edit(event, "❌ متن پنهانی پیدا نشد!"); return
        try:
            bits = ""
            for ch in encoded_part:
                if ch == _ZWSP:
                    bits += "0"
                elif ch == _ZWNJ:
                    bits += "1"
            chars = [chr(int(bits[i:i+8], 2)) for i in range(0, len(bits)-7, 8)]
            decoded = "".join(c for c in chars if c.isprintable())
            await safe_edit(event, box("🔍 متن آشکار شد", [f"پنهان: {decoded[:100]}"] if decoded else ["متن قابل خواندن نیست"]))
        except Exception:
            await safe_edit(event, "❌ رمزگشایی ناموفق!")
    
    # ══ شمار کلمات ════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^شمار$"))
    async def count_words(event):
        record_cmd("شمار")
        reply = await event.get_reply_message()
        if not reply or not reply.text:
            await safe_edit(event, "❌ ریپلای روی یک پیام متنی کن!"); return
        text = reply.text
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", "").replace("\n", ""))
        lines = text.count("\n") + 1
        await safe_edit(event, box("📊 شمارش", [
            f"کلمات: {words}",
            f"کاراکتر: {chars}",
            f"بدون فاصله: {chars_no_space}",
            f"خطوط: {lines}",
        ]))
    
    # ══ تصادفی ════════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تصادفی (\d+) (\d+)$"))
    async def random_num(event):
        record_cmd("تصادفی")
        lo = int(event.pattern_match.group(1))
        hi = int(event.pattern_match.group(2))
        if lo > hi:
            lo, hi = hi, lo
        result = random.randint(lo, hi)
        await safe_edit(event, box("🎲 عدد تصادفی", [
            f"بازه: {lo} تا {hi}",
            f"نتیجه: {result}",
        ]))
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^انتخاب (.+)$"))
    async def random_choice(event):
        record_cmd("انتخاب")
        items = [x.strip() for x in event.pattern_match.group(1).split(",") if x.strip()]
        if not items:
            await safe_edit(event, "❌ گزینه‌ها را با کاما جدا کن!"); return
        chosen = random.choice(items)
        await safe_edit(event, box("🎯 انتخاب تصادفی", [
            f"گزینه‌ها: {len(items)}",
            f"انتخاب: {chosen}",
        ]))
    
    # ══ نقل قول ══════════════════════════════
    _QUOTES = [
        "زندگی یعنی آنچه در حین برنامه‌ریزی برایت اتفاق می‌افتد — جان لنون",
        "موفقیت نهایی نیست، شکست کشنده نیست — چرچیل",
        "فردا هرگز نخواهد آمد؛ امروز را دریاب",
        "بهترین زمان برای کاشتن درخت بیست سال پیش بود. بهترین زمان دوم، همین الان است",
        "انسان به اندازه‌ای که می‌اندیشد بزرگ است — سقراط",
        "کوچکترین عمل بهتر از بزرگترین نیت است",
        "هر کسی که متوقف شد از یادگیری متوقف شد — هنری فورد",
        "خوشبختی داشتن چیزی نیست که نداری — زندگی با چیزی است که داری",
        "دشمن تو نه کسی است که به تو دروغ گفت؛ بلکه کسی است که آن دروغ را باور کردی",
        "از شکست‌هایت بیاموز؛ اما در آن‌ها غرق نشو",
    ]
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^نقل_قول$"))
    async def quote(event):
        record_cmd("نقل_قول")
        q = random.choice(_QUOTES)
        await safe_edit(event, f"💬 {q}")
    
    # ══ اشعار ═════════════════════════════════
    _POEMS = [
        "بنی‌آدم اعضای یکدیگرند\nکه در آفرینش ز یک گوهرند — سعدی",
        "ای دوست شکر بهتر یا آن که شکر سازد؟\nعقل بهتر یا آن که عقل و نظر سازد؟ — مولانا",
        "گر مرد رهی غم مخور از دوری و دیری\nدانی که رسیدن هنر خویش کند ذوقت — حافظ",
        "مرغ سحر با گل نو خاسته گفت:\nنازک و آسان شکستی و نمود — صائب",
        "هر که جز ماهی ز آبش سیر شد\nهر که بی‌روزی است روزش دیر شد — مولانا",
    ]
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^شعر$"))
    async def poem(event):
        record_cmd("شعر")
        p = random.choice(_POEMS)
        await safe_edit(event, f"📜 {p}")
    
    # ══ لیست ابزارها ══════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^بهینه‌سازی_دیتابیس$"))
    async def optimize_db(event):
        record_cmd("بهینه‌سازی_دیتابیس")
        await safe_edit(event, "⏳ در حال بهینه‌سازی...")
        with _db_lock:
            conn = get_conn()
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.commit()
        size = 0
        try:
            size = os.path.getsize(DB_PATH) // 1024
        except Exception:
            pass
        await safe_edit(event, box("✅ بهینه‌سازی انجام شد", [
            f"اندازه دیتابیس: {size}KB",
            "VACUUM + ANALYZE اجرا شد",
        ]))
    
    # ══ تنظیمات ═══════════════════════════════
    @client.on(events.NewMessage(outgoing=True, pattern=r"^تنظیم (.+)\|(.+)$"))
    async def set_setting_cmd(event):
        record_cmd("تنظیم")
        key = event.pattern_match.group(1).strip()
        val = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, val))
            conn.commit()
        await safe_edit(event, f"✅ {key} = {val}")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_تنظیم (.+)$"))
    async def del_setting(event):
        record_cmd("حذف_تنظیم")
        key = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM settings WHERE key=?", (key,))
            conn.commit()
        await safe_edit(event, f"✅ «{key}» حذف شد." if c.rowcount else f"❌ «{key}» نیست!")
    

    # ════════════════════════════════════════════
    #  💎 V7 PRO'S Handlers
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سایه(?: (.+))?$"))
    async def shadow_profile(event):
        record_cmd("سایه")
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM shadow_profiles WHERE uid=?", (u.id,)).fetchone()
            mem_cnt = conn.execute("SELECT COUNT(*) FROM memory_book WHERE uid=?", (u.id,)).fetchone()[0]
            msg_cnt = conn.execute("SELECT msg_count FROM contacts WHERE uid=?", (u.id,)).fetchone()
            last_msg = conn.execute(
                "SELECT text,ts FROM chat_memory WHERE uid=? ORDER BY id DESC LIMIT 1", (u.id,)
            ).fetchone()
        data = json.loads(row["data"]) if row else {}
        name = f"{getattr(u,'first_name','')} {getattr(u,'last_name','') or ''}".strip()
        username = getattr(u, "username", "") or "—"
        lines = [
            f"👤 نام: {name[:30]}",
            f"🔗 یوزر: @{username}",
            f"🆔 آیدی: {u.id}",
            f"💬 پیام‌ها: {msg_cnt['msg_count'] if msg_cnt else 0}",
            f"🧠 خاطرات: {mem_cnt}",
            f"📱 ربات: {'✅' if getattr(u,'bot',False) else '❌'}",
        ]
        if last_msg:
            lines.append(f"🕐 آخرین پیام: {last_msg['ts'][:10]}")
            lines.append(f"📝 متن: {last_msg['text'][:30]}")
        if data:
            for k, v in list(data.items())[:3]:
                lines.append(f"• {k}: {v}")
        await safe_edit(event, box(f"👥 پروفایل سایه — {name[:20]}", lines, WATERMARK))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خاطره_ثبت (.+)\|(.+)$"))
    async def memory_add(event):
        record_cmd("خاطره_ثبت")
        arg  = event.pattern_match.group(1).strip()
        text = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO memory_book(uid,memory,ts) VALUES(?,?,?)",
                         (u.id, text[:500], now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM memory_book WHERE uid=?", (u.id,)).fetchone()[0]
            conn.commit()
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, f"🧠 خاطره برای {name} ثبت شد. (کل: {cnt})")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خاطره‌ها(?: (.+))?$"))
    async def memory_list(event):
        record_cmd("خاطره‌ها")
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM memory_book WHERE uid=? ORDER BY id DESC LIMIT 15", (u.id,)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 خاطره‌ای ثبت نشده!"); return
        name = getattr(u, "first_name", str(u.id))
        lines = [f"• [{r['ts'][:10]}] {r['memory'][:50]}" for r in rows]
        await safe_edit(event, box(f"🧠 خاطرات {name} ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خاطره_حذف (\d+)$"))
    async def memory_delete(event):
        record_cmd("خاطره_حذف")
        mid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM memory_book WHERE id=?", (mid,))
            conn.commit()
        await safe_edit(event, f"✅ خاطره {mid} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^امروز_در_تاریخ$"))
    async def on_this_day(event):
        record_cmd("امروز_در_تاریخ")
        today = jalali()
        md = today[5:]
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM on_this_day WHERE date_md=? ORDER BY id DESC LIMIT 10", (md,)
            ).fetchall()
            cal_rows = conn.execute(
                "SELECT * FROM calendar WHERE substr(date,6)=?", (md,)
            ).fetchall()
        lines = []
        for r in rows:
            lines.append(f"📖 {r['text'][:50]}")
        for r in cal_rows:
            icon = "🎂" if r["type"] == "تولد" else "📌"
            lines.append(f"{icon} {r['title'][:30]} ({r['date'][:4]})")
        if not lines:
            await safe_edit(event, f"📭 هیچ رویدادی برای این روز ({md}) ثبت نشده!")
            return
        await safe_edit(event, box(f"📅 امروز در تاریخ — {today}", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^امروز_ثبت (.+)$"))
    async def on_this_day_add(event):
        record_cmd("امروز_ثبت")
        text = event.pattern_match.group(1).strip()
        md = jalali()[5:]
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO on_this_day(date_md,text,ts) VALUES(?,?,?)",
                         (md, text[:300], now_str()))
            conn.commit()
        await safe_edit(event, f"✅ رویداد برای این روز ({md}) ثبت شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^یادآور_هوشمند (.+)$"))
    async def smart_reminder_add(event):
        record_cmd("یادآور_هوشمند")
        text = event.pattern_match.group(1).strip()
        # Parse time from text using simple heuristics
        fire_at = ""
        hour = 9
        import re as _re
        h_match = _re.search(r"(\d{1,2})\s*(?:بعد|صبح|شب|ظهر|بعدازظهر|:)", text)
        if h_match:
            hour = int(h_match.group(1))
        tomorrow_words = ["فردا", "tomorrow", "بعد از فردا"]
        today_str = jalali()
        if any(w in text for w in tomorrow_words):
            parts = today_str.split("/")
            day   = int(parts[2]) + 1
            fire_at = f"{parts[0]}/{parts[1]}/{day:02d} {hour:02d}:00"
        else:
            fire_at = f"{today_str} {hour:02d}:00"
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO smart_reminders(text,fire_at,ts) VALUES(?,?,?)",
                         (text[:300], fire_at, now_str()))
            conn.commit()
        await safe_edit(event, box("⏰ یادآور هوشمند", [
            f"متن: {text[:50]}",
            f"زمان تخمینی: {fire_at}",
            "راهنما: یادآورهای_من",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^یادآورهای_من$"))
    async def smart_reminders_list(event):
        record_cmd("یادآورهای_من")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM smart_reminders WHERE done=0 ORDER BY fire_at LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 یادآوری فعالی نیست!"); return
        lines = [f"• [{r['fire_at'][:13]}] {r['text'][:40]}" for r in rows]
        await safe_edit(event, box(f"⏰ یادآورهای هوشمند ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^میمیک_چت(?: (.+))?$"))
    async def mimic_chat(event):
        record_cmd("میمیک_چت")
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT text FROM chat_memory WHERE uid=? AND outgoing=0 LIMIT 50", (u.id,)
            ).fetchall()
        if len(rows) < 5:
            await safe_edit(event, "📭 داده پیام کافی نیست (حداقل ۵ پیام)!"); return
        texts = [r["text"] for r in rows]
        stop = {"که","در","به","از","با","این","آن","را","می","است","بود","یک","هم","و"}
        wf = defaultdict(int)
        avg_len = 0
        for t in texts:
            avg_len += len(t)
            for w in t.split():
                if len(w) > 2 and w not in stop:
                    wf[w] += 1
        avg_len //= len(texts)
        top_words = sorted(wf, key=wf.get, reverse=True)[:8]
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, box(f"🎭 میمیک سبک {name}", [
            f"کل پیام تحلیل: {len(rows)}",
            f"میانگین طول: {avg_len} کاراکتر",
            f"پرکاربردترین واژگان: {', '.join(top_words[:5])}",
            "── نمونه سبک ──",
        ] + [f"💬 {t[:45]}" for t in random.sample(texts, min(3, len(texts)))]))

    # ════════════════════════════════════════════
    #  📊 آنالیتیکس V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^گراف_فعالیت$"))
    async def activity_graph(event):
        record_cmd("گراف_فعالیت")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT date, msgs_sent, cmds FROM daily_stats ORDER BY date DESC LIMIT 7"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده کافی نیست!"); return
        rows = list(reversed(rows))
        bars = "▁▂▃▄▅▆▇█"
        max_msg = max((r["msgs_sent"] or 0) for r in rows) or 1
        lines = []
        for r in rows:
            cnt = r["msgs_sent"] or 0
            bar = bars[int((cnt / max_msg) * 7)]
            lines.append(f"{r['date'][5:]} {bar * 3} {cnt} پیام | {r['cmds']} دستور")
        await safe_edit(event, box("📊 گراف فعالیت ۷ روز", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمان_پاسخ(?: (.+))?$"))
    async def avg_response_time(event):
        record_cmd("زمان_پاسخ")
        arg = (event.pattern_match.group(1) or "").strip()
        if arg:
            u = await resolve_user(client, event, arg)
            uid = u.id if u else None
            label = getattr(u, "first_name", arg) if u else arg
        else:
            uid = None
            label = "همه"
        with _db_lock:
            conn = get_conn()
            if uid:
                rows = conn.execute(
                    "SELECT ts, outgoing FROM chat_memory WHERE chat_id=? ORDER BY id LIMIT 200",
                    (uid,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT ts, outgoing FROM chat_memory ORDER BY id DESC LIMIT 200"
                ).fetchall()
        if len(rows) < 4:
            await safe_edit(event, "📭 داده کافی نیست!"); return
        delays = []
        for i in range(1, len(rows)):
            prev = rows[i - 1]
            curr = rows[i]
            if prev["outgoing"] == 0 and curr["outgoing"] == 1:
                try:
                    t1 = datetime.datetime.strptime(prev["ts"], "%Y/%m/%d %H:%M")
                    t2 = datetime.datetime.strptime(curr["ts"], "%Y/%m/%d %H:%M")
                    diff = (t2 - t1).total_seconds()
                    if 0 < diff < 7200:
                        delays.append(diff)
                except Exception:
                    pass
        if not delays:
            await safe_edit(event, "📭 نمی‌توان محاسبه کرد!"); return
        avg = sum(delays) / len(delays)
        mn  = min(delays)
        mx  = max(delays)
        def fmt(s):
            m, sec = divmod(int(s), 60)
            return f"{m}دقیقه {sec}ثانیه" if m else f"{sec}ثانیه"
        await safe_edit(event, box(f"⏱ زمان پاسخ — {label}", [
            f"میانگین: {fmt(avg)}",
            f"سریع‌ترین: {fmt(mn)}",
            f"کندترین: {fmt(mx)}",
            f"نمونه: {len(delays)} پیام",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^استریک$"))
    async def show_streaks(event):
        record_cmd("استریک")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM streaks ORDER BY current DESC LIMIT 10").fetchall()
        if not rows:
            await safe_edit(event, "📭 streak ثبت نشده!\nاستفاده: استریک_ثبت [نوع]"); return
        lines = [f"🔥 {r['key']}: {r['current']} روز (بهترین: {r['best']})" for r in rows]
        await safe_edit(event, box("🔥 Streak System", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^استریک_ثبت (.+)$"))
    async def streak_record(event):
        record_cmd("استریک_ثبت")
        key   = event.pattern_match.group(1).strip()
        today = jalali()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM streaks WHERE key=?", (key,)).fetchone()
        if row:
            last = row["last_day"]
            current = row["current"]
            best    = row["best"]
            if last == today:
                await safe_edit(event, f"⚠️ «{key}» قبلاً امروز ثبت شد!"); return
            parts_last = last.split("/") if last else []
            parts_today = today.split("/")
            is_consecutive = False
            if len(parts_last) == 3 and len(parts_today) == 3:
                try:
                    day_diff = int(parts_today[2]) - int(parts_last[2])
                    if day_diff == 1:
                        is_consecutive = True
                except Exception:
                    pass
            current = current + 1 if is_consecutive else 1
            best    = max(best, current)
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE streaks SET current=?,best=?,last_day=? WHERE key=?",
                             (current, best, today, key))
                conn.commit()
        else:
            current = 1
            best    = 1
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO streaks(key,current,best,last_day) VALUES(?,1,1,?)",
                             (key, today))
                conn.commit()
        fire = "🔥" * min(current, 7)
        await safe_edit(event, box(f"🔥 Streak: {key}", [
            f"{fire}",
            f"فعلی: {current} روز",
            f"بهترین: {best} روز",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خلاصه_روزانه$"))
    async def daily_summary(event):
        record_cmd("خلاصه_روزانه")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            ds = conn.execute("SELECT * FROM daily_stats WHERE date=?", (today,)).fetchone()
            todos_done = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE done=1 AND ts LIKE ?", (f"{today}%",)
            ).fetchone()[0]
            cmds_today = conn.execute(
                "SELECT COUNT(*) FROM cmd_history WHERE ts LIKE ?", (f"{today}%",)
            ).fetchone()[0]
            exp_today = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date=?", (today,)
            ).fetchone()[0]
            cal_rows = conn.execute("SELECT * FROM calendar WHERE date=?", (today,)).fetchall()
        lines = [
            f"📅 تاریخ: {today}",
            f"📤 پیام ارسالی: {ds['msgs_sent'] if ds else 0}",
            f"📥 پیام دریافتی: {ds['msgs_recv'] if ds else 0}",
            f"⚡ دستورات: {cmds_today}",
            f"✅ کارهای انجام‌شده: {todos_done}",
            f"💸 هزینه: {exp_today:,} ریال",
            f"📌 رویدادهای امروز: {len(cal_rows)}",
        ]
        if cal_rows:
            for r in cal_rows:
                lines.append(f"  {'🎂' if r['type']=='تولد' else '📅'} {r['title'][:25]}")
        level = profile_val("level")
        xp    = profile_val("xp")
        lines.append(f"⭐ سطح: {level} | XP: {xp}")
        await safe_edit(event, box("📋 خلاصه روزانه", lines, WATERMARK))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^گزارش_هفتگی$"))
    async def weekly_report(event):
        record_cmd("گزارش_هفتگی")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM daily_stats ORDER BY date DESC LIMIT 7"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده کافی نیست!"); return
        total_sent = sum(r["msgs_sent"] or 0 for r in rows)
        total_recv = sum(r["msgs_recv"] or 0 for r in rows)
        total_cmds = sum(r["cmds"]      or 0 for r in rows)
        total_err  = sum(r["errors"]    or 0 for r in rows)
        best_day   = max(rows, key=lambda r: r["msgs_sent"] or 0)
        lines = [
            f"📤 ارسال: {total_sent}",
            f"📥 دریافت: {total_recv}",
            f"⚡ دستور: {total_cmds}",
            f"❌ خطا: {total_err}",
            f"🏆 بهترین روز: {best_day['date']} ({best_day['msgs_sent'] or 0} پیام)",
            "── روز به روز ──",
        ]
        for r in reversed(rows):
            lines.append(f"• {r['date'][5:]}: {r['msgs_sent'] or 0}↑ {r['msgs_recv'] or 0}↓")
        await safe_edit(event, box("📊 گزارش هفتگی", lines, WATERMARK))

    # ════════════════════════════════════════════
    #  👥 مخاطبان V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مورد_علاقه(?: (.+))?$"))
    async def fav_contact_add(event):
        record_cmd("مورد_علاقه")
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO fav_contacts(uid,added) VALUES(?,?) "
                         "ON CONFLICT(uid) DO NOTHING", (u.id, now_str()))
            conn.commit()
            cnt = conn.execute("SELECT COUNT(*) FROM fav_contacts").fetchone()[0]
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, f"⭐ {name} به مورد علاقه‌ها اضافه شد! (کل: {cnt})")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_علاقه$"))
    async def fav_contact_list(event):
        record_cmd("لیست_علاقه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT f.*,c.name,c.username FROM fav_contacts f "
                "LEFT JOIN contacts c ON f.uid=c.uid ORDER BY f.added DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 کسی در لیست مورد علاقه نیست!"); return
        lines = [f"⭐ {r['name'] or r['uid']} | @{r['username'] or '—'}" for r in rows]
        await safe_edit(event, box(f"⭐ مورد علاقه‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بی‌خیال (.+?)(?:\s(.+))?$"))
    async def ignore_add(event):
        record_cmd("بی‌خیال")
        arg    = event.pattern_match.group(1).strip()
        reason = (event.pattern_match.group(2) or "").strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO ignore_list(uid,reason,added) VALUES(?,?,?) "
                         "ON CONFLICT(uid) DO UPDATE SET reason=excluded.reason",
                         (u.id, reason[:100], now_str()))
            conn.commit()
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, f"🚫 {name} به لیست نادیده اضافه شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_نادیده$"))
    async def ignore_list_cmd(event):
        record_cmd("لیست_نادیده")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT i.*,c.name,c.username FROM ignore_list i "
                "LEFT JOIN contacts c ON i.uid=c.uid ORDER BY i.added DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 لیست نادیده خالی است!"); return
        lines = [f"🚫 {r['name'] or r['uid']} | {r['reason'][:25] or '—'}" for r in rows]
        await safe_edit(event, box(f"🚫 نادیده گرفته‌شده‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^منتظر (.+?) (.+)$"))
    async def waiting_add(event):
        record_cmd("منتظر")
        arg     = event.pattern_match.group(1).strip()
        context = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO waiting_tracker(uid,context,started) VALUES(?,?,?)",
                         (u.id, context[:200], now_str()))
            conn.commit()
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, f"⏳ منتظر پاسخ {name} برای «{context[:30]}»")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^منتظرها$"))
    async def waiting_list_cmd(event):
        record_cmd("منتظرها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT w.*,c.name FROM waiting_tracker w "
                "LEFT JOIN contacts c ON w.uid=c.uid "
                "WHERE w.done=0 ORDER BY w.started DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "✅ منتظر هیچ پاسخی نیستی!"); return
        lines = [f"⏳ {r['id']}. {r['name'] or r['uid']} | {r['context'][:30]} | {r['started'][:10]}"
                 for r in rows]
        await safe_edit(event, box(f"⏳ در انتظار ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^منتظر_انجام (\d+)$"))
    async def waiting_done(event):
        record_cmd("منتظر_انجام")
        wid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("UPDATE waiting_tracker SET done=1 WHERE id=?", (wid,))
            conn.commit()
        await safe_edit(event, f"✅ آیتم {wid} انجام شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تایم‌لاین_پروفایل(?: (.+))?$"))
    async def profile_timeline(event):
        record_cmd("تایم‌لاین_پروفایل")
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM contact_history WHERE uid=? ORDER BY id DESC LIMIT 15", (u.id,)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 تاریخچه‌ای ثبت نشده!"); return
        name = getattr(u, "first_name", str(u.id))
        lines = [f"• [{r['ts'][:10]}] {r['field']}: {r['old_val'][:15]} ← {r['new_val'][:15]}"
                 for r in rows]
        await safe_edit(event, box(f"📅 تایم‌لاین {name}", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^نام_مستعار (.+?) (.+)$"))
    async def auto_nickname_set(event):
        record_cmd("نام_مستعار")
        arg  = event.pattern_match.group(1).strip()
        nick = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO auto_nicknames(uid,nickname) VALUES(?,?) "
                         "ON CONFLICT(uid) DO UPDATE SET nickname=excluded.nickname",
                         (u.id, nick[:50]))
            conn.commit()
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, f"✅ نام مستعار {name} → «{nick}» تنظیم شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^نام_مستعار_لیست$"))
    async def auto_nickname_list(event):
        record_cmd("نام_مستعار_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT n.*,c.name FROM auto_nicknames n "
                "LEFT JOIN contacts c ON n.uid=c.uid LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 نام مستعاری تنظیم نشده!"); return
        lines = [f"• {r['name'] or r['uid']} → «{r['nickname']}»" for r in rows]
        await safe_edit(event, box(f"🏷️ نام‌های مستعار ({len(rows)})", lines))

    # ════════════════════════════════════════════
    #  💬 پیام‌رسانی V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاسخ_سریع (.+)\|(.+)$"))
    async def quick_reply_add(event):
        record_cmd("پاسخ_سریع")
        key  = event.pattern_match.group(1).strip()
        text = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO quick_replies(shortcut,text) VALUES(?,?) "
                         "ON CONFLICT(shortcut) DO UPDATE SET text=excluded.text",
                         (key[:30], text[:500]))
            conn.commit()
        await safe_edit(event, f"✅ پاسخ سریع «{key}» ذخیره شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاسخ_سریع_لیست$"))
    async def quick_reply_list(event):
        record_cmd("پاسخ_سریع_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM quick_replies ORDER BY used DESC LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 پاسخ سریعی ثبت نشده!"); return
        lines = [f"• /{r['shortcut']}: {r['text'][:35]} (×{r['used']})" for r in rows]
        await safe_edit(event, box(f"⚡ پاسخ‌های سریع ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاسخ_سریع_حذف (.+)$"))
    async def quick_reply_del(event):
        record_cmd("پاسخ_سریع_حذف")
        key = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM quick_replies WHERE shortcut=?", (key,))
            conn.commit()
        await safe_edit(event, f"✅ پاسخ سریع «{key}» حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^/qr_(.+)$"))
    async def use_quick_reply(event):
        key = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM quick_replies WHERE shortcut=?", (key,)).fetchone()
        if row:
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE quick_replies SET used=used+1 WHERE shortcut=?", (key,))
                conn.commit()
            await safe_edit(event, row["text"])

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌نویس (.+)\|(.+)$"))
    async def draft_add(event):
        record_cmd("پیش‌نویس")
        title   = event.pattern_match.group(1).strip()
        content = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO drafts(title,content,ts) VALUES(?,?,?)",
                         (title[:80], content[:2000], now_str()))
            cnt = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
            conn.commit()
        await safe_edit(event, f"📝 پیش‌نویس «{title[:30]}» ذخیره شد. (کل: {cnt})")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌نویس_لیست$"))
    async def draft_list(event):
        record_cmd("پیش‌نویس_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM drafts ORDER BY id DESC LIMIT 15").fetchall()
        if not rows:
            await safe_edit(event, "📭 پیش‌نویسی نیست!"); return
        lines = [f"📝 {r['id']}. {r['title'][:30]} | {r['ts'][:10]}" for r in rows]
        await safe_edit(event, box(f"📝 پیش‌نویس‌ها ({len(rows)})", lines, "ارسال: پیش‌نویس_ارسال [id]"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌نویس_ارسال (\d+)$"))
    async def draft_send(event):
        record_cmd("پیش‌نویس_ارسال")
        did = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM drafts WHERE id=?", (did,)).fetchone()
        if not row:
            await safe_edit(event, "❌ پیش‌نویس پیدا نشد!"); return
        await safe_edit(event, row["content"])

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پیش‌نویس_حذف (\d+)$"))
    async def draft_delete(event):
        record_cmd("پیش‌نویس_حذف")
        did = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM drafts WHERE id=?", (did,))
            conn.commit()
        await safe_edit(event, f"✅ پیش‌نویس {did} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بمب_پیام (\d+) (.+)$"))
    async def message_bomb(event):
        record_cmd("بمب_پیام")
        count = min(int(event.pattern_match.group(1)), 20)
        text  = event.pattern_match.group(2).strip()
        await safe_edit(event, f"💣 ارسال {count} پیام...")
        for i in range(count):
            try:
                await client.send_message(event.chat_id, text)
                await asyncio.sleep(0.8)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as ex:
                logger.warning(f"bomb: {ex}")
                break
        try:
            await event.delete()
        except Exception:
            pass

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_ذخیره (.+)\|(.+)\|(.+)$"))
    async def password_save(event):
        record_cmd("رمز_ذخیره")
        site     = event.pattern_match.group(1).strip()
        username = event.pattern_match.group(2).strip()
        password = event.pattern_match.group(3).strip()
        encrypted = vault_encrypt(password)
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO passwords(site,username,password,ts) VALUES(?,?,?,?)",
                (site[:80], username[:80], encrypted, now_str())
            )
            conn.commit()
        await safe_edit(event, f"🔑 رمز «{site}» ذخیره شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_نمایش (.+)$"))
    async def password_show(event):
        record_cmd("رمز_نمایش")
        site = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute(
                "SELECT * FROM passwords WHERE site LIKE ? ORDER BY id DESC LIMIT 1",
                (f"%{site}%",)
            ).fetchone()
        if not row:
            await safe_edit(event, f"❌ رمزی برای «{site}» پیدا نشد!"); return
        try:
            decrypted = vault_decrypt(row["password"])
        except Exception:
            decrypted = "❌ خطا در رمزگشایی"
        await safe_edit(event, box(f"🔑 {row['site']}", [
            f"یوزرنیم: {row['username']}",
            f"رمز: {decrypted}",
            f"ذخیره: {row['ts'][:10]}",
        ], "⚠️ این پیام را حذف کنید!"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_لیست$"))
    async def password_list(event):
        record_cmd("رمز_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT id,site,username,ts FROM passwords ORDER BY id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 رمزی ذخیره نشده!"); return
        lines = [f"🔑 {r['id']}. {r['site']} | {r['username']}" for r in rows]
        await safe_edit(event, box(f"🔑 رمزهای ذخیره‌شده ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_حذف (\d+)$"))
    async def password_delete(event):
        record_cmd("رمز_حذف")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM passwords WHERE id=?", (pid,))
            conn.commit()
        await safe_edit(event, f"✅ رمز {pid} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رمز_تولید_v7(?: (\d+))?$"))
    async def password_gen_v7(event):
        record_cmd("رمز_تولید_v7")
        length = min(int(event.pattern_match.group(1) or 16), 64)
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        pwd   = "".join(random.choice(chars) for _ in range(length))
        strength = "💪 قوی" if length >= 16 else ("🟡 متوسط" if length >= 10 else "🔴 ضعیف")
        await safe_edit(event, box("🔐 رمز تولید شده", [
            f"رمز: `{pwd}`",
            f"طول: {length}",
            f"قدرت: {strength}",
        ], "رمز را ذخیره کنید!"))

    # ════════════════════════════════════════════
    #  ⚙️ اتوماسیون V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمان‌بند (.+)\|(.+)\|(.+)$"))
    async def scheduler_add(event):
        record_cmd("زمان‌بند")
        name   = event.pattern_match.group(1).strip()
        cmd    = event.pattern_match.group(2).strip()
        run_at = event.pattern_match.group(3).strip()
        today  = jalali()
        if ":" in run_at and "/" not in run_at:
            run_at = f"{today} {run_at}"
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO cmd_scheduler(name,cmd,run_at,active) VALUES(?,?,?,1)",
                (name[:50], cmd[:200], run_at)
            )
            conn.commit()
        await safe_edit(event, box("⏰ زمان‌بند ثبت شد", [
            f"نام: {name}",
            f"دستور: {cmd[:40]}",
            f"زمان: {run_at}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمان‌بند_لیست$"))
    async def scheduler_list(event):
        record_cmd("زمان‌بند_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM cmd_scheduler WHERE active=1 ORDER BY run_at LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 زمان‌بندی ثبت نشده!"); return
        lines = [f"⏰ {r['id']}. {r['name']} | {r['run_at'][:13]} | {r['cmd'][:25]}"
                 for r in rows]
        await safe_edit(event, box(f"⏰ زمان‌بندها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زمان‌بند_حذف (\d+)$"))
    async def scheduler_del(event):
        record_cmd("زمان‌بند_حذف")
        sid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("UPDATE cmd_scheduler SET active=0 WHERE id=?", (sid,))
            conn.commit()
        await safe_edit(event, f"✅ زمان‌بند {sid} غیرفعال شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^هشدار_منشن (.+)$"))
    async def mention_alert_add(event):
        record_cmd("هشدار_منشن")
        kw = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO mention_alerts(keyword,ts) VALUES(?,?)",
                         (kw[:80], now_str()))
            conn.commit()
        _v7_mention_keywords.append(kw.lower())
        await safe_edit(event, f"🔔 هشدار منشن «{kw}» ثبت شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^هشدار_منشن_لیست$"))
    async def mention_alert_list(event):
        record_cmd("هشدار_منشن_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM mention_alerts ORDER BY id DESC LIMIT 20").fetchall()
        if not rows:
            await safe_edit(event, "📭 هشداری ثبت نشده!"); return
        lines = [f"🔔 {r['keyword']}" for r in rows]
        await safe_edit(event, box(f"🔔 هشدارهای منشن ({len(rows)})", lines))

    @client.on(events.NewMessage(incoming=True))
    async def mention_watcher(event):
        try:
            if not _v7_mention_keywords:
                return
            text = (event.text or "").lower()
            for kw in _v7_mention_keywords:
                if kw in text:
                    me = await client.get_me()
                    sender = await event.get_sender()
                    sname = getattr(sender, "first_name", "?") if sender else "?"
                    await client.send_message(me.id,
                        f"🔔 منشن‌یاب:\nکلیدواژه: «{kw}»\nفرستنده: {sname}\nچت: {event.chat_id}\nمتن: {text[:100]}"
                    )
                    break
        except Exception:
            pass

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ری‌استارت$"))
    async def auto_restart(event):
        record_cmd("ری‌استارت")
        await safe_edit(event, "♻️ در حال ری‌استارت...")
        await asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاکسازی_هوشمند(?: (\d+))?$"))
    async def smart_cleaner(event):
        record_cmd("پاکسازی_هوشمند")
        days = int(event.pattern_match.group(1) or 30)
        cutoff = jalali()
        parts = cutoff.split("/")
        old_day = max(1, int(parts[2]) - days)
        cutoff_date = f"{parts[0]}/{parts[1]}/{old_day:02d}"
        with _db_lock:
            conn = get_conn()
            cm = conn.execute("DELETE FROM chat_memory WHERE ts < ?", (f"{cutoff_date} 00:00",)).rowcount
            cmdh = conn.execute("DELETE FROM cmd_history WHERE ts < ?", (f"{cutoff_date} 00:00",)).rowcount
            al = conn.execute("DELETE FROM activity_log WHERE ts < ?", (f"{cutoff_date} 00:00",)).rowcount
            conn.commit()
        await safe_edit(event, box("🧹 پاکسازی هوشمند", [
            f"مبنا: {days} روز قبل از امروز",
            f"پیام‌های چت: {cm} حذف",
            f"تاریخچه دستور: {cmdh} حذف",
            f"لاگ فعالیت: {al} حذف",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آرشیو_ثبت (.+)\|(.+)\|(.+)$"))
    async def archive_add(event):
        record_cmd("آرشیو_ثبت")
        category = event.pattern_match.group(1).strip()
        title    = event.pattern_match.group(2).strip()
        content  = event.pattern_match.group(3).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO archives(category,title,content,ts) VALUES(?,?,?,?)",
                (category[:50], title[:100], content[:5000], now_str())
            )
            conn.commit()
        await safe_edit(event, f"📂 آرشیو «{title[:30]}» در دسته «{category}» ذخیره شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آرشیو_لیست(?: (.+))?$"))
    async def archive_list(event):
        record_cmd("آرشیو_لیست")
        cat = (event.pattern_match.group(1) or "").strip()
        with _db_lock:
            conn = get_conn()
            if cat:
                rows = conn.execute(
                    "SELECT * FROM archives WHERE category LIKE ? ORDER BY id DESC LIMIT 15",
                    (f"%{cat}%",)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM archives ORDER BY id DESC LIMIT 15"
                ).fetchall()
        if not rows:
            await safe_edit(event, "📭 آرشیوی نیست!"); return
        lines = [f"📂 {r['id']}. [{r['category']}] {r['title'][:30]}" for r in rows]
        await safe_edit(event, box(f"📂 آرشیو ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آرشیو_نمایش (\d+)$"))
    async def archive_show(event):
        record_cmd("آرشیو_نمایش")
        aid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM archives WHERE id=?", (aid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ پیدا نشد!"); return
        await safe_edit(event, box(f"📂 {row['title']}", [
            f"دسته: {row['category']}",
            f"تاریخ: {row['ts'][:10]}",
            "── محتوا ──",
            row["content"][:800],
        ]))

    # ════════════════════════════════════════════
    #  📂 کالکشن V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کالکشن_ثبت (.+)\|(.+)\|(.+)$"))
    async def collection_add(event):
        record_cmd("کالکشن_ثبت")
        cat     = event.pattern_match.group(1).strip()
        title   = event.pattern_match.group(2).strip()
        content = event.pattern_match.group(3).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO collections(category,title,content,ts) VALUES(?,?,?,?)",
                (cat[:50], title[:100], content[:2000], now_str())
            )
            conn.commit()
        await safe_edit(event, f"📦 «{title[:30]}» در کالکشن «{cat}» اضافه شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کالکشن_لیست(?: (.+))?$"))
    async def collection_list(event):
        record_cmd("کالکشن_لیست")
        cat = (event.pattern_match.group(1) or "").strip()
        with _db_lock:
            conn = get_conn()
            if cat:
                rows = conn.execute(
                    "SELECT * FROM collections WHERE category LIKE ? ORDER BY id DESC LIMIT 20",
                    (f"%{cat}%",)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM collections ORDER BY id DESC LIMIT 20"
                ).fetchall()
        if not rows:
            await safe_edit(event, "📭 کالکشنی نیست!"); return
        lines = [f"📦 {r['id']}. [{r['category']}] {r['title'][:30]}" for r in rows]
        await safe_edit(event, box(f"📦 کالکشن ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کالکشن_جستجو (.+)$"))
    async def collection_search(event):
        record_cmd("کالکشن_جستجو")
        q = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM collections WHERE title LIKE ? OR content LIKE ? OR category LIKE ? LIMIT 15",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            ).fetchall()
        if not rows:
            await safe_edit(event, f"❌ نتیجه‌ای برای «{q}» نیست!"); return
        lines = [f"📦 {r['id']}. [{r['category']}] {r['title'][:30]}" for r in rows]
        await safe_edit(event, box(f"🔍 نتایج «{q}» ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کالکشن_حذف (\d+)$"))
    async def collection_del(event):
        record_cmd("کالکشن_حذف")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM collections WHERE id=?", (cid,))
            conn.commit()
        await safe_edit(event, f"✅ آیتم {cid} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کالکشن_دسته‌ها$"))
    async def collection_cats(event):
        record_cmd("کالکشن_دسته‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT category, COUNT(*) cnt FROM collections GROUP BY category ORDER BY cnt DESC"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 دسته‌ای نیست!"); return
        lines = [f"📁 {r['category']}: {r['cnt']} آیتم" for r in rows]
        await safe_edit(event, box("📁 دسته‌های کالکشن", lines))

    # ════════════════════════════════════════════
    #  🔎 ابزار هوشمند V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جستجو_هوشمند (.+)$"))
    async def smart_search(event):
        record_cmd("جستجو_هوشمند")
        q = event.pattern_match.group(1).strip()
        ql = f"%{q}%"
        with _db_lock:
            conn = get_conn()
            contacts = conn.execute(
                "SELECT name,username FROM contacts WHERE name LIKE ? OR username LIKE ? LIMIT 3", (ql, ql)
            ).fetchall()
            macros = conn.execute(
                "SELECT name,value FROM macros WHERE name LIKE ? OR value LIKE ? LIMIT 3", (ql, ql)
            ).fetchall()
            vault  = conn.execute(
                "SELECT key_name FROM vault WHERE key_name LIKE ? LIMIT 3", (ql,)
            ).fetchall()
            todos  = conn.execute(
                "SELECT text FROM todos WHERE text LIKE ? AND done=0 LIMIT 3", (ql,)
            ).fetchall()
            memos  = conn.execute(
                "SELECT memory FROM memory_book WHERE memory LIKE ? LIMIT 3", (ql,)
            ).fetchall()
            colls  = conn.execute(
                "SELECT title,category FROM collections WHERE title LIKE ? OR content LIKE ? LIMIT 3",
                (ql, ql)
            ).fetchall()
        lines = []
        if contacts:
            lines.append("👥 مخاطبان:")
            lines += [f"  • {r['name']} @{r['username'] or '—'}" for r in contacts]
        if macros:
            lines.append("⚡ ماکروها:")
            lines += [f"  • /{r['name']}: {r['value'][:25]}" for r in macros]
        if vault:
            lines.append("🔐 صندوق:")
            lines += [f"  • {r['key_name']}" for r in vault]
        if todos:
            lines.append("📋 کارها:")
            lines += [f"  • {r['text'][:30]}" for r in todos]
        if memos:
            lines.append("🧠 خاطرات:")
            lines += [f"  • {r['memory'][:30]}" for r in memos]
        if colls:
            lines.append("📦 کالکشن:")
            lines += [f"  • [{r['category']}] {r['title'][:25]}" for r in colls]
        if not lines:
            await safe_edit(event, f"❌ نتیجه‌ای برای «{q}» پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO search_history(query,results,ts) VALUES(?,?,?)",
                         (q[:100], len(lines), now_str()))
            conn.commit()
        await safe_edit(event, box(f"🔍 جستجوی هوشمند: «{q}»", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^داشبورد_زنده$"))
    async def live_dashboard(event):
        record_cmd("داشبورد_زنده")
        me = await client.get_me()
        today = jalali()
        with _db_lock:
            conn = get_conn()
            msg_today  = conn.execute("SELECT COUNT(*) FROM chat_memory WHERE outgoing=1 AND ts LIKE ?", (f"{today}%",)).fetchone()[0]
            cmd_today  = conn.execute("SELECT COUNT(*) FROM cmd_history WHERE ts LIKE ?", (f"{today}%",)).fetchone()[0]
            contacts_t = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            todos_open = conn.execute("SELECT COUNT(*) FROM todos WHERE done=0").fetchone()[0]
            orders_pen = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='pending'").fetchone()[0]
            tickets_o  = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'").fetchone()[0]
            coins      = _get_coins()
        level = profile_val("level")
        xp    = profile_val("xp")
        try:
            import psutil as _ps
            cpu = f"{_ps.cpu_percent(0.1):.1f}%"
            ram = _ps.virtual_memory()
            ram_s = f"{ram.percent:.0f}%"
        except Exception:
            cpu = ram_s = "؟"
        await safe_edit(event, box(f"📊 داشبورد زنده — {now_str()}", [
            f"👤 {me.first_name} | سطح {level} | XP {xp}",
            f"💬 پیام امروز: {msg_today}",
            f"⚡ دستور امروز: {cmd_today}",
            f"👥 مخاطبان: {contacts_t}",
            f"📋 کارهای باز: {todos_open}",
            f"🏪 سفارش‌های معلق: {orders_pen}",
            f"🎫 تیکت‌های باز: {tickets_o}",
            f"💰 موجودی: {coins} سکه",
            f"🧠 CPU: {cpu} | RAM: {ram_s}",
        ], WATERMARK))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^منابع$"))
    async def resource_monitor(event):
        record_cmd("منابع")
        try:
            import psutil as _ps
            cpu  = _ps.cpu_percent(interval=0.5)
            ram  = _ps.virtual_memory()
            disk = _ps.disk_usage("/")
            net  = _ps.net_io_counters()
            procs = len(list(_ps.process_iter()))
            await safe_edit(event, box("💻 مانیتور منابع", [
                f"CPU: {cpu:.1f}%",
                f"RAM: {ram.used//1024//1024}MB / {ram.total//1024//1024}MB ({ram.percent:.0f}%)",
                f"دیسک: {disk.used//1024//1024//1024}GB / {disk.total//1024//1024//1024}GB ({disk.percent:.0f}%)",
                f"شبکه ↑: {net.bytes_sent//1024//1024}MB",
                f"شبکه ↓: {net.bytes_recv//1024//1024}MB",
                f"پروسس‌ها: {procs}",
                f"پایتون: {sys.version_info.major}.{sys.version_info.minor}",
            ]))
        except ImportError:
            await safe_edit(event, "❌ psutil نصب نیست!\nنصب: pip install psutil")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بررسی_وابستگی$"))
    async def dependency_check(event):
        record_cmd("بررسی_وابستگی")
        pkgs = {
            "telethon": "Telethon — هسته اصلی",
            "psutil":   "psutil — مانیتور سیستم",
            "pycryptodome": "pycryptodome — رمزنگاری AES",
            "yt_dlp":   "yt-dlp — دانلود رسانه",
        }
        lines = []
        for pkg, desc in pkgs.items():
            try:
                importlib.import_module(pkg.replace("-", "_"))
                lines.append(f"✅ {desc}")
            except ImportError:
                lines.append(f"❌ {desc} — pip install {pkg}")
        await safe_edit(event, box("📦 بررسی وابستگی‌ها", lines))

    # ════════════════════════════════════════════
    #  🎰 بازی V7
    # ════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^اسلات(?: (\d+))?$"))
    async def slot_machine(event):
        record_cmd("اسلات")
        bet = int(event.pattern_match.group(1) or 10)
        coins = _get_coins()
        if coins < bet:
            await safe_edit(event, f"❌ موجودی کافی نیست! ({coins} سکه)"); return
        symbols = ["🍒","🍋","🍊","🍇","⭐","💎","7️⃣","🔔"]
        r1 = [random.choice(symbols) for _ in range(3)]
        await safe_edit(event, f"🎰 {' | '.join(r1)}")
        await asyncio.sleep(0.5)
        r2 = [random.choice(symbols) for _ in range(3)]
        await safe_edit(event, f"🎰 {' | '.join(r2)}")
        await asyncio.sleep(0.5)
        r3 = [random.choice(symbols) for _ in range(3)]
        await safe_edit(event, f"🎰 {' | '.join(r3)}")
        await asyncio.sleep(0.3)
        slots = [random.choice(symbols) for _ in range(3)]
        if slots[0] == slots[1] == slots[2]:
            mult = 10 if slots[0] == "💎" else (5 if slots[0] == "7️⃣" else 3)
            win  = bet * mult
            _add_coins(win - bet, "اسلات برنده")
            msg = f"🎉 بردی! {bet} × {mult} = {win} سکه!"
        elif slots[0] == slots[1] or slots[1] == slots[2]:
            _add_coins(0, "")
            msg = "🎵 دو تا یکی — سر به سر!"
        else:
            _add_coins(-bet, "اسلات باخت")
            msg = f"😢 باختی {bet} سکه!"
        final = " | ".join(slots)
        new_bal = _get_coins()
        await safe_edit(event, box("🎰 اسلات ماشین", [
            f"نتیجه: {final}",
            msg,
            f"موجودی: {new_bal} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاس_نبرد(?: (.+))?$"))
    async def dice_battle(event):
        record_cmd("تاس_نبرد")
        me_roll   = random.randint(1, 6)
        opp_roll  = random.randint(1, 6)
        me_emoji  = ["⚀","⚁","⚂","⚃","⚄","⚅"][me_roll - 1]
        opp_emoji = ["⚀","⚁","⚂","⚃","⚄","⚅"][opp_roll - 1]
        if me_roll > opp_roll:
            result = "🏆 تو بردی!"
            _add_coins(20, "تاس_نبرد")
        elif me_roll < opp_roll:
            result = "😢 باختی!"
            _add_coins(-10, "تاس_نبرد")
        else:
            result = "🤝 مساوی!"
        await safe_edit(event, box("🎲 نبرد تاس", [
            f"تو: {me_emoji} ({me_roll})",
            f"حریف: {opp_emoji} ({opp_roll})",
            result,
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^چرخ (.+)$"))
    async def spin_wheel(event):
        record_cmd("چرخ")
        raw     = event.pattern_match.group(1).strip()
        choices = [c.strip() for c in raw.split(",") if c.strip()]
        if not choices:
            await safe_edit(event, "❌ حداقل یک گزینه وارد کن!"); return
        frames = ["🌀", "🔄", "⚡", "🌪"]
        for f in frames:
            await safe_edit(event, f"{f} در حال چرخیدن...")
            await asyncio.sleep(0.4)
        winner = random.choice(choices)
        await safe_edit(event, box("🎡 چرخ گردون", [
            f"گزینه‌ها: {', '.join(choices[:8])}",
            f"🏆 برنده: {winner}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سکه$"))
    async def coin_flip(event):
        record_cmd("سکه")
        result = random.choice(["شیر 🦁", "خط ✏️"])
        await safe_edit(event, f"🪙 پرتاب سکه: **{result}**")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سنگ_کاغذ_قیچی (.+)$"))
    async def rock_paper_scissors(event):
        record_cmd("سنگ_کاغذ_قیچی")
        choices = {"سنگ": "🪨", "کاغذ": "📄", "قیچی": "✂️"}
        user_choice = event.pattern_match.group(1).strip()
        if user_choice not in choices:
            await safe_edit(event, f"❌ انتخاب نامعتبر! گزینه‌ها: {', '.join(choices)}"); return
        bot_choice = random.choice(list(choices.keys()))
        wins = {"سنگ": "قیچی", "قیچی": "کاغذ", "کاغذ": "سنگ"}
        if user_choice == bot_choice:
            result = "🤝 مساوی!"
        elif wins[user_choice] == bot_choice:
            result = "🏆 تو بردی!"
            _add_coins(15, "سنگ_کاغذ_قیچی")
        else:
            result = "🤖 ONYX برد!"
            _add_coins(-5, "سنگ_کاغذ_قیچی")
        await safe_edit(event, box("✂️ سنگ کاغذ قیچی", [
            f"تو: {choices[user_choice]} {user_choice}",
            f"ONYX: {choices[bot_choice]} {bot_choice}",
            result,
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بیست_یک(?: (\d+))?$"))
    async def blackjack_start(event):
        record_cmd("بیست_یک")
        bet = int(event.pattern_match.group(1) or 20)
        coins = _get_coins()
        if coins < bet:
            await safe_edit(event, f"❌ موجودی کم! ({coins} سکه)"); return
        deck   = _card_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        _blackjack_game[event.chat_id] = {
            "hand": player, "dealer": dealer, "bet": bet, "deck": deck
        }
        total = _hand_total(player)
        await safe_edit(event, box("🃏 بیست‌ویک", [
            f"دست تو: {_card_str(player)} = {total}",
            f"دیلر: {dealer[0][0]}{dealer[0][1]} 🂠",
            f"شرط: {bet} سکه",
            "بیست_یک_کارت — کارت بگیر | توقف — بایست",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بیست_یک_کارت$"))
    async def blackjack_hit(event):
        record_cmd("بیست_یک_کارت")
        game = _blackjack_game.get(event.chat_id)
        if not game:
            await safe_edit(event, "❌ بازی شروع نشده! بیست_یک [شرط]"); return
        card = game["deck"].pop()
        game["hand"].append(card)
        total = _hand_total(game["hand"])
        if total > 21:
            _add_coins(-game["bet"], "blackjack باخت")
            del _blackjack_game[event.chat_id]
            await safe_edit(event, box("🃏 BUST!", [
                f"دست: {_card_str(game['hand'])} = {total}",
                f"😢 باختی {game['bet']} سکه!",
            ]))
        elif total == 21:
            win = game["bet"] * 2
            _add_coins(win, "blackjack بیست‌ویک!")
            del _blackjack_game[event.chat_id]
            await safe_edit(event, box("🃏 بیست‌ویک! 🎉", [
                f"دست: {_card_str(game['hand'])} = {total}",
                f"🏆 بردی {win} سکه!",
            ]))
        else:
            await safe_edit(event, box("🃏 بیست‌ویک", [
                f"دست تو: {_card_str(game['hand'])} = {total}",
                f"دیلر: {game['dealer'][0][0]}{game['dealer'][0][1]} 🂠",
                "بیست_یک_کارت | توقف",
            ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ورق_تصادفی$"))
    async def random_card(event):
        record_cmd("ورق_تصادفی")
        deck = _card_deck()
        card = deck.pop()
        suit_names = {"♠": "پیک", "♥": "دل", "♦": "خشت", "♣": "گشنیز"}
        val_names  = {"A": "آس", "J": "جک", "Q": "ملکه", "K": "پادشاه"}
        val_fa = val_names.get(card[0], card[0])
        suit_fa = suit_names.get(card[1], card[1])
        await safe_edit(event, box("🃏 ورق تصادفی", [
            f"{card[0]}{card[1]}",
            f"نام: {val_fa} {suit_fa}",
            f"ارزش: {_card_value(card)}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جادو_هشت (.+)$"))
    async def magic_8ball(event):
        record_cmd("جادو_هشت")
        question = event.pattern_match.group(1).strip()
        answer   = random.choice(_MAGIC8_ANSWERS)
        await safe_edit(event, box("🎱 Magic 8-Ball", [
            f"سوال: {question[:50]}",
            f"جواب: {answer}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^حدس_عدد(?: (\d+))?(?: (\d+))?$"))
    async def guess_number_start(event):
        record_cmd("حدس_عدد")
        mn = int(event.pattern_match.group(1) or 1)
        mx = int(event.pattern_match.group(2) or 100)
        if mn >= mx:
            await safe_edit(event, "❌ min باید کمتر از max باشد!"); return
        number = random.randint(mn, mx)
        _guess_game[event.chat_id] = {"number": number, "min": mn, "max": mx, "tries": 0}
        await safe_edit(event, box("🎯 حدس عدد", [
            f"عددی بین {mn} و {mx} انتخاب کردم!",
            "دستور: حدس_من [عدد]",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^حدس_من (\d+)$"))
    async def guess_number_answer(event):
        record_cmd("حدس_من")
        game = _guess_game.get(event.chat_id)
        if not game:
            await safe_edit(event, "❌ بازی‌ای شروع نشده! حدس_عدد [min] [max]"); return
        guess = int(event.pattern_match.group(1))
        game["tries"] += 1
        n = game["number"]
        if guess == n:
            reward = max(10, 50 - game["tries"] * 5)
            _add_coins(reward, "حدس_عدد")
            del _guess_game[event.chat_id]
            await safe_edit(event, box("🎯 درست!", [
                f"عدد: {n}",
                f"تلاش: {game['tries']} بار",
                f"جایزه: {reward} سکه",
            ]))
        elif guess < n:
            await safe_edit(event, f"⬆️ بزرگتر! (تلاش {game['tries']})")
        else:
            await safe_edit(event, f"⬇️ کوچک‌تر! (تلاش {game['tries']})")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^معما_روز$"))
    async def daily_puzzle(event):
        record_cmd("معما_روز")
        today = jalali()
        riddle = _RIDDLES[sum(ord(c) for c in today) % len(_RIDDLES)]
        await safe_edit(event, box("🧩 معمای روز", [
            f"سوال: {riddle[0]}",
            "── برای دیدن جواب ──",
            "10 ثانیه صبر کن...",
        ]))
        await asyncio.sleep(10)
        _add_coins(5, "معما_روز")
        await safe_edit(event, box("🧩 معمای روز — جواب", [
            f"سوال: {riddle[0]}",
            f"جواب: {riddle[1]}",
            "✅ +5 سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تایپ_چالش$"))
    async def typing_challenge_start(event):
        record_cmd("تایپ_چالش")
        sentence = random.choice(_TYPING_SENTENCES)
        _typing_challenge[event.chat_id] = {
            "text": sentence,
            "started": _time.time()
        }
        await safe_edit(event, box("⌨️ چالش تایپ", [
            "این جمله را تایپ کن:",
            f"👇 {sentence}",
            "دستور: تایپ_پاسخ [متن]",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تایپ_پاسخ (.+)$"))
    async def typing_challenge_answer(event):
        record_cmd("تایپ_پاسخ")
        game = _typing_challenge.get(event.chat_id)
        if not game:
            await safe_edit(event, "❌ چالشی شروع نشده! تایپ_چالش"); return
        user_text  = event.pattern_match.group(1).strip()
        target     = game["text"]
        elapsed    = _time.time() - game["started"]
        words      = len(target.split())
        wpm        = int(words / (elapsed / 60)) if elapsed > 0 else 0
        correct    = sum(1 for a, b in zip(user_text, target) if a == b)
        accuracy   = int(correct / max(len(target), 1) * 100)
        del _typing_challenge[event.chat_id]
        reward = min(50, int(wpm / 5))
        _add_coins(reward, "تایپ_چالش")
        await safe_edit(event, box("⌨️ نتیجه تایپ", [
            f"⏱ زمان: {elapsed:.1f} ثانیه",
            f"🚀 سرعت: {wpm} کلمه/دقیقه",
            f"🎯 دقت: {accuracy}%",
            f"💰 جایزه: {reward} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^فروشگاه$"))
    async def ingame_shop(event):
        record_cmd("فروشگاه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM shop_items WHERE active=1 ORDER BY category, price"
            ).fetchall()
        if not rows:
            with _db_lock:
                conn = get_conn()
                defaults = [
                    ("بوستر XP", 100, "xp_x2", "بوستر"),
                    ("سپر محافظ", 200, "shield", "دفاع"),
                    ("کلید رمز", 150, "key", "ابزار"),
                    ("الیکسیر قدرت", 80, "power", "بوستر"),
                    ("نقشه گنج", 300, "treasure_map", "ماجرا"),
                ]
                for name, price, effect, cat in defaults:
                    conn.execute(
                        "INSERT OR IGNORE INTO shop_items(name,price,effect,category) VALUES(?,?,?,?)",
                        (name, price, effect, cat)
                    )
                conn.commit()
                rows = conn.execute("SELECT * FROM shop_items WHERE active=1").fetchall()
        coins = _get_coins()
        lines = [f"💰 موجودی: {coins} سکه", "──────────────────"]
        for r in rows:
            lines.append(f"🛒 {r['id']}. {r['name']} — {r['price']} سکه [{r['category']}]")
            if r["effect"]:
                lines.append(f"   ✨ {r['effect']}")
        lines.append("──────────────────")
        lines.append("خرید: خرید [id]")
        await safe_edit(event, box("🛍️ فروشگاه ONYX", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خرید (\d+)$"))
    async def buy_item(event):
        record_cmd("خرید")
        item_id = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            item = conn.execute("SELECT * FROM shop_items WHERE id=? AND active=1", (item_id,)).fetchone()
        if not item:
            await safe_edit(event, "❌ آیتم پیدا نشد!"); return
        coins = _get_coins()
        if coins < item["price"]:
            await safe_edit(event, f"❌ موجودی کافی نیست! ({coins}/{item['price']} سکه)"); return
        _add_coins(-item["price"], f"خرید {item['name']}")
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO inventory(item_id,qty,ts) VALUES(?,1,?)", (item_id, now_str()))
            conn.commit()
        await safe_edit(event, box("✅ خرید موفق", [
            f"آیتم: {item['name']}",
            f"قیمت: {item['price']} سکه",
            f"موجودی: {_get_coins()} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کوله‌پشتی$"))
    async def backpack_show(event):
        record_cmd("کوله‌پشتی")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT i.*,s.name,s.effect,s.category FROM inventory i "
                "JOIN shop_items s ON i.item_id=s.id ORDER BY i.id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📦 کوله‌پشتی خالی است!"); return
        lines = [f"🎒 {r['name']} ×{r['qty']} [{r['category']}]" for r in rows]
        await safe_edit(event, box(f"🎒 کوله‌پشتی ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جدول_امتیاز$"))
    async def leaderboard_show(event):
        record_cmd("جدول_امتیاز")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM leaderboard ORDER BY score DESC LIMIT 10"
            ).fetchall()
        if not rows:
            me = await client.get_me()
            score = int(profile_val("xp") or 0)
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO leaderboard(uid,name,score,updated) VALUES(?,?,?,?)",
                    (me.id, me.first_name, score, now_str())
                )
                conn.commit()
            await safe_edit(event, "📊 جدول ثبت شد! دوباره امتحان کن."); return
        medals = ["🥇","🥈","🥉"] + ["🏅"] * 7
        lines  = [f"{medals[i]} {r['name']}: {r['score']} XP" for i, r in enumerate(rows)]
        await safe_edit(event, box("🏆 جدول امتیازات", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جایزه_روزانه$"))
    async def daily_reward(event):
        record_cmd("جایزه_روزانه")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT value FROM daily_reward WHERE key='last_claim'").fetchone()
        last = row["value"] if row else ""
        if last == today:
            await safe_edit(event, "⏳ جایزه روزانه قبلاً دریافت شد!\nفردا دوباره بیا."); return
        base_reward = random.randint(30, 100)
        streak_row  = None
        with _db_lock:
            conn = get_conn()
            streak_row = conn.execute("SELECT * FROM streaks WHERE key='daily_login'").fetchone()
        streak  = 0
        if streak_row:
            parts_last  = (streak_row["last_day"] or "").split("/")
            parts_today = today.split("/")
            if len(parts_last) == 3 and len(parts_today) == 3:
                try:
                    diff = int(parts_today[2]) - int(parts_last[2])
                    streak = streak_row["current"] + 1 if diff == 1 else 1
                except Exception:
                    streak = 1
            else:
                streak = 1
            best = max(streak, streak_row["best"])
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE streaks SET current=?,best=?,last_day=? WHERE key='daily_login'",
                             (streak, best, today))
                conn.commit()
        else:
            streak = 1
            with _db_lock:
                conn = get_conn()
                conn.execute("INSERT INTO streaks(key,current,best,last_day) VALUES('daily_login',1,1,?)",
                             (today,))
                conn.commit()
        bonus   = streak * 5
        total   = base_reward + bonus
        _add_coins(total, "جایزه_روزانه")
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO daily_reward(key,value) VALUES('last_claim',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (today,)
            )
            conn.commit()
        fire = "🔥" * min(streak, 7)
        await safe_edit(event, box("🎁 جایزه روزانه", [
            f"جایزه پایه: {base_reward} سکه",
            f"{fire} استریک {streak} روز: +{bonus} سکه",
            f"مجموع: {total} سکه",
            f"موجودی: {_get_coins()} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماموریت‌ها$"))
    async def quests_list(event):
        record_cmd("ماموریت‌ها")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM quests WHERE active=1 AND done=0 LIMIT 10").fetchall()
        if not rows:
            with _db_lock:
                conn = get_conn()
                default_quests = [
                    ("۱۰ دستور اجرا کن", 10, 100),
                    ("۵ بار بازی کن", 5, 50),
                    ("۳ خاطره ثبت کن", 3, 75),
                    ("جایزه روزانه دریافت کن", 1, 30),
                    ("۲۰ سکه خرج کن", 20, 60),
                ]
                for title, target, reward in default_quests:
                    conn.execute(
                        "INSERT OR IGNORE INTO quests(title,target,reward,ts) VALUES(?,?,?,?)",
                        (title, target, reward, now_str())
                    )
                conn.commit()
                rows = conn.execute("SELECT * FROM quests WHERE active=1 AND done=0 LIMIT 10").fetchall()
        lines = []
        for r in rows:
            pct  = min(100, int(r["current"] / r["target"] * 100))
            bar  = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines.append(f"• {r['title']}")
            lines.append(f"  [{bar}] {r['current']}/{r['target']} | 🎁 {r['reward']} سکه")
        await safe_edit(event, box(f"🎯 ماموریت‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماموریت_انجام (\d+)$"))
    async def quest_progress(event):
        record_cmd("ماموریت_انجام")
        qid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM quests WHERE id=?", (qid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ ماموریت پیدا نشد!"); return
        new_val = row["current"] + 1
        if new_val >= row["target"]:
            _add_coins(row["reward"], f"ماموریت: {row['title']}")
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE quests SET done=1, current=? WHERE id=?", (new_val, qid))
                conn.commit()
            await safe_edit(event, box("🎯 ماموریت کامل!", [
                f"✅ {row['title']}",
                f"🎁 جایزه: {row['reward']} سکه",
                f"موجودی: {_get_coins()} سکه",
            ]))
        else:
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE quests SET current=? WHERE id=?", (new_val, qid))
                conn.commit()
            await safe_edit(event, f"📈 پیشرفت: {new_val}/{row['target']} — {row['title']}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مجموعه_نشان$"))
    async def badges_show(event):
        record_cmd("مجموعه_نشان")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM badges ORDER BY ts").fetchall()
        if not rows:
            await safe_edit(event, "📭 هنوز نشانی جمع‌آوری نکردی!\nنشان‌ها با بازی و دستورات کسب می‌شن."); return
        lines = [f"{r['emoji']} {r['title']} — {r['ts'][:10]}" for r in rows]
        await safe_edit(event, box(f"🏅 مجموعه نشان ({len(rows)})", lines))

    def _grant_badge(badge_id: str, title: str, emoji: str = "🏅"):
        try:
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT OR IGNORE INTO badges(id,title,emoji,ts) VALUES(?,?,?,?)",
                    (badge_id, title, emoji, now_str())
                )
                conn.commit()
        except Exception:
            pass

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ارتقاء_مهارت (.+)$"))
    async def skill_upgrade(event):
        record_cmd("ارتقاء_مهارت")
        skill = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM skill_tree WHERE skill=?", (skill,)).fetchone()
        if not row:
            await safe_edit(event, f"❌ مهارت «{skill}» پیدا نشد!"); return
        if row["level"] >= row["max_level"]:
            await safe_edit(event, f"✅ مهارت «{skill}» به حداکثر سطح رسیده!"); return
        cost = (row["level"] + 1) * 50
        if _get_coins() < cost:
            await safe_edit(event, f"❌ موجودی کافی نیست! ({cost} سکه لازم)"); return
        _add_coins(-cost, f"ارتقاء مهارت {skill}")
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE skill_tree SET level=level+1 WHERE skill=?", (skill,))
            conn.commit()
            new_level = conn.execute("SELECT level FROM skill_tree WHERE skill=?", (skill,)).fetchone()[0]
        await safe_edit(event, box(f"⬆️ مهارت ارتقاء یافت!", [
            f"مهارت: {skill}",
            f"سطح: {new_level}",
            f"هزینه: {cost} سکه",
            f"موجودی: {_get_coins()} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جعبه_رمز$"))
    async def mystery_box_open(event):
        record_cmd("جعبه_رمز")
        cost = 50
        if _get_coins() < cost:
            await safe_edit(event, f"❌ {cost} سکه لازم داری!"); return
        _add_coins(-cost, "جعبه رمز")
        prizes = [
            ("💰 سکه",      lambda: _add_coins(random.randint(10, 200), "جعبه رمز")),
            ("⭐ XP",       lambda: None),
            ("🏅 نشان",     lambda: _grant_badge(f"box_{now_str()[:10]}", "جعبه‌باز", "📦")),
            ("💎 جواهر",    lambda: _add_coins(500, "جعبه رمز - جواهر")),
            ("🎪 نتیجه‌ای ندارد", lambda: None),
        ]
        weights = [40, 25, 20, 5, 10]
        prize = random.choices(prizes, weights=weights, k=1)[0]
        prize[1]()
        frames = ["📦 🤔", "📦 ❓", "📦 ✨", "📦 🎁"]
        for f in frames:
            await safe_edit(event, f)
            await asyncio.sleep(0.4)
        await safe_edit(event, box("📦 جعبه مرموز", [
            f"جایزه: {prize[0]}",
            f"موجودی: {_get_coins()} سکه",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^نبرد_باس$"))
    async def boss_fight(event):
        record_cmd("نبرد_باس")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM boss_fight").fetchall()
        state = {r["key"]: r["value"] for r in rows}
        boss_hp    = int(state.get("hp", "100"))
        boss_name  = state.get("name", "اژدهای آتشین")
        player_atk = random.randint(10, 30)
        boss_atk   = random.randint(5, 20)
        player_hp  = int(state.get("player_hp", "100"))
        boss_hp   -= player_atk
        player_hp -= boss_atk
        player_hp  = max(0, player_hp)
        boss_hp    = max(0, boss_hp)
        def _boss_set(k, v):
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO boss_fight(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v))
                )
                conn.commit()
        if boss_hp <= 0:
            reward = random.randint(100, 300)
            _add_coins(reward, "نبرد باس")
            _grant_badge("boss_slayer", "باس‌کش", "🗡️")
            _boss_set("hp", "100")
            _boss_set("player_hp", "100")
            _boss_set("name", random.choice(["اژدهای آتشین","دیو سیاه","جادوگر ظلمت","غول کوه"]))
            await safe_edit(event, box(f"⚔️ {boss_name} شکست خورد!", [
                f"حمله تو: {player_atk}",
                f"🏆 پیروزی!",
                f"جایزه: {reward} سکه",
                f"نشان «باس‌کش» کسب کردی!",
            ]))
        elif player_hp <= 0:
            _boss_set("hp", "100")
            _boss_set("player_hp", "100")
            await safe_edit(event, box(f"⚔️ باختی به {boss_name}!", [
                f"حمله تو: {player_atk}",
                f"ضربه باس: {boss_atk}",
                "دوباره تلاش کن!",
            ]))
        else:
            _boss_set("hp", boss_hp)
            _boss_set("player_hp", player_hp)
            hp_bar  = "❤️" * (player_hp // 10) + "🖤" * (10 - player_hp // 10)
            bhp_bar = "💔" * (boss_hp // 10) + "❤️‍🔥" * (10 - boss_hp // 10)
            await safe_edit(event, box(f"⚔️ نبرد با {boss_name}", [
                f"HP باس: {bhp_bar} {boss_hp}",
                f"HP تو:  {hp_bar} {player_hp}",
                f"حمله تو: -{player_atk} | ضربه باس: -{boss_atk}",
                "نبرد_باس — ادامه بده!",
            ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^حیوان_خانگی$"))
    async def virtual_pet_show(event):
        record_cmd("حیوان_خانگی")
        pet = _get_pet()
        def bar(val):
            filled = val // 10
            return "🟩" * filled + "⬜" * (10 - filled)
        await safe_edit(event, box(f"🐾 {pet['name']} ({pet['type']})", [
            f"⭐ سطح {pet['level']} | XP {pet['xp']}",
            f"🍖 غذا:  {bar(pet['hunger'])} {pet['hunger']}%",
            f"💧 آب:   {bar(pet['thirst'])} {pet['thirst']}%",
            f"😊 شاد:  {bar(pet['happy'])} {pet['happy']}%",
            "──────────────────",
            "مراقبت غذا | مراقبت آب | مراقبت بازی",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مراقبت (.+)$"))
    async def pet_care(event):
        record_cmd("مراقبت")
        action = event.pattern_match.group(1).strip()
        pet = _get_pet()
        action_map = {
            "غذا":  ("hunger",  30, "🍖 غذا داد"),
            "آب":   ("thirst",  30, "💧 آب داد"),
            "بازی": ("happy",   20, "🎮 بازی کرد"),
        }
        if action not in action_map:
            await safe_edit(event, "❌ گزینه: غذا | آب | بازی"); return
        field, amount, msg = action_map[action]
        pet[field] = min(100, pet[field] + amount)
        xp_gained  = random.randint(2, 8)
        pet["xp"] += xp_gained
        if pet["xp"] >= pet["level"] * 50:
            pet["xp"]   = 0
            pet["level"] += 1
            _grant_badge(f"pet_lv{pet['level']}", f"حیوان سطح {pet['level']}", "🐾")
            await client.send_message(event.chat_id, f"🎉 {pet['name']} به سطح {pet['level']} رسید!")
        _save_pet(pet)
        await safe_edit(event, f"✅ {msg}! +{xp_gained} XP\nسطح {pet['level']} | XP {pet['xp']}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خانه$"))
    async def virtual_house(event):
        record_cmd("خانه")
        with _db_lock:
            conn = get_conn()
            rooms = conn.execute("SELECT * FROM virtual_house").fetchall()
        if not rooms:
            default_rooms = [("نشیمن", 1), ("اتاق‌خواب", 1), ("آشپزخانه", 1), ("باغ", 1)]
            with _db_lock:
                conn = get_conn()
                for room, level in default_rooms:
                    conn.execute(
                        "INSERT OR IGNORE INTO virtual_house(room,items,level) VALUES(?,?,?)",
                        (room, "[]", level)
                    )
                conn.commit()
                rooms = conn.execute("SELECT * FROM virtual_house").fetchall()
        lines = []
        for r in rooms:
            items = json.loads(r["items"] or "[]")
            lines.append(f"🏠 {r['room']} (Lv.{r['level']}) — {len(items)} آیتم")
        await safe_edit(event, box("🏡 خانه مجازی", lines, "مبل_بخر [اتاق] [آیتم]"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مبل_بخر (.+) (.+)$"))
    async def buy_furniture(event):
        record_cmd("مبل_بخر")
        room = event.pattern_match.group(1).strip()
        item = event.pattern_match.group(2).strip()
        cost = 80
        if _get_coins() < cost:
            await safe_edit(event, f"❌ {cost} سکه لازم!"); return
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM virtual_house WHERE room=?", (room,)).fetchone()
        if not row:
            await safe_edit(event, f"❌ اتاق «{room}» پیدا نشد!"); return
        items = json.loads(row["items"] or "[]")
        items.append(item)
        _add_coins(-cost, f"مبلمان: {item}")
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE virtual_house SET items=? WHERE room=?",
                         (json.dumps(items, ensure_ascii=False), room))
            conn.commit()
        await safe_edit(event, f"🛋️ «{item}» به {room} اضافه شد! ({cost} سکه)")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آزمایشگاه$"))
    async def lab_show(event):
        record_cmd("آزمایشگاه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM lab_experiments ORDER BY id DESC LIMIT 10"
            ).fetchall()
        await safe_edit(event, box("🔬 آزمایشگاه ONYX", [
            f"📋 آزمایش‌ها: {len(rows)}",
            "── فرمول‌ها ──",
            "آتش+آب = بخار 💨",
            "خاک+آب = گِل 🪨",
            "آتش+خاک = لاوا 🌋",
            "باد+آب =嵐 توفان ⛈",
            "آتش+باد = انفجار 💥",
            "── دستور ──",
            "آزمایش [نام]|[ورودی]",
        ] + [f"• {r['name']}: {r['output'][:25] or r['status']}" for r in rows[:5]]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آزمایش (.+)\|(.+)$"))
    async def lab_experiment(event):
        record_cmd("آزمایش")
        name  = event.pattern_match.group(1).strip()
        inp   = event.pattern_match.group(2).strip()
        formulas = {
            "آتش+آب":   ("بخار 💨",   20),
            "خاک+آب":   ("گِل 🪨",    15),
            "آتش+خاک":  ("لاوا 🌋",   50),
            "باد+آب":   ("توفان ⛈",   30),
            "آتش+باد":  ("انفجار 💥", 100),
            "خاک+باد":  ("غبار 🌪",   25),
            "آب+نور":   ("رنگین‌کمان 🌈", 40),
            "آتش+نور":  ("خورشید ☀️", 80),
        }
        key = inp.strip()
        result, reward = formulas.get(key, (None, 0))
        status = "success" if result else "failed"
        output = result or "❓ ترکیب ناشناخته"
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO lab_experiments(name,input,output,status,ts) VALUES(?,?,?,?,?)",
                (name[:50], inp[:100], output[:200], status, now_str())
            )
            conn.commit()
        if reward:
            _add_coins(reward, f"آزمایش: {name}")
        await safe_edit(event, box(f"🔬 نتیجه: {name}", [
            f"ورودی: {inp}",
            f"خروجی: {output}",
            f"{'✅ موفق!' if result else '❌ شکست خورد'}",
            f"جایزه: {reward} سکه" if reward else "",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_ثبت (.+)\|(.+)$"))
    async def vpn_config_add(event):
        record_cmd("کانفیگ_ثبت")
        name    = event.pattern_match.group(1).strip()
        content = event.pattern_match.group(2).strip()
        fp      = _config_fingerprint(content)
        proto   = _detect_protocol(content)
        server  = _extract_server(content)
        with _db_lock:
            conn = get_conn()
            dup = conn.execute(
                "SELECT id,name FROM vpn_configs WHERE fingerprint=?", (fp,)
            ).fetchone()
        if dup:
            await safe_edit(event, f"⚠️ این کانفیگ قبلاً با نام «{dup['name']}» ثبت شده! (id: {dup['id']})"); return
        with _db_lock:
            conn = get_conn()
            cid = conn.execute(
                "INSERT INTO vpn_configs(name,content,server,protocol,fingerprint,ts) VALUES(?,?,?,?,?,?)",
                (name[:80], content[:5000], server, proto, fp, now_str())
            ).lastrowid
            conn.commit()
        await safe_edit(event, box("✅ کانفیگ ثبت شد", [
            f"آیدی: {cid}",
            f"نام: {name}",
            f"پروتکل: {proto}",
            f"سرور: {server[:40]}",
            f"اثرانگشت: {fp}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_لیست$"))
    async def vpn_config_list(event):
        record_cmd("کانفیگ_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT id,name,protocol,server,favorite,used_count,latency FROM vpn_configs ORDER BY favorite DESC, used_count DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 کانفیگی ثبت نشده!\nکانفیگ_ثبت [نام]|[محتوا]"); return
        lines = []
        for r in rows:
            fav  = "⭐" if r["favorite"] else "  "
            ping = f"{r['latency']}ms" if r["latency"] else "—"
            lines.append(
                f"{fav} {r['id']}. {r['name'][:20]} | {r['protocol']} | {r['server'][:20]} | {ping}"
            )
        await safe_edit(event, box(f"🛡️ کانفیگ‌ها ({len(rows)})", lines, "نمایش: کانفیگ_نمایش [id]"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_نمایش (\d+)$"))
    async def vpn_config_show(event):
        record_cmd("کانفیگ_نمایش")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM vpn_configs WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ کانفیگ پیدا نشد!"); return
        tags = json.loads(row["tags"] or "[]")
        await safe_edit(event, box(f"🛡️ {row['name']}", [
            f"پروتکل: {row['protocol']}",
            f"سرور: {row['server'][:50]}",
            f"استفاده: {row['used_count']} بار",
            f"پینگ: {row['latency']}ms" if row["latency"] else "پینگ: —",
            f"تگ‌ها: {', '.join(tags) or '—'}",
            f"اثرانگشت: {row['fingerprint']}",
            f"ثبت: {row['ts'][:10]}",
            "── محتوا ──",
            row["content"][:300],
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_حذف (\d+)$"))
    async def vpn_config_del(event):
        record_cmd("کانفیگ_حذف")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM vpn_configs WHERE id=?", (cid,))
            conn.commit()
        await safe_edit(event, f"✅ کانفیگ {cid} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_علاقه (\d+)$"))
    async def vpn_config_fav(event):
        record_cmd("کانفیگ_علاقه")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT favorite FROM vpn_configs WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ پیدا نشد!"); return
        new_val = 0 if row["favorite"] else 1
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE vpn_configs SET favorite=? WHERE id=?", (new_val, cid))
            conn.commit()
        status = "⭐ به علاقه‌مندی اضافه شد" if new_val else "❌ از علاقه‌مندی حذف شد"
        await safe_edit(event, f"{status} (کانفیگ {cid})")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_تگ (\d+) (.+)$"))
    async def vpn_config_tag(event):
        record_cmd("کانفیگ_تگ")
        cid = int(event.pattern_match.group(1))
        tag = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT tags FROM vpn_configs WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ کانفیگ پیدا نشد!"); return
        tags = json.loads(row["tags"] or "[]")
        if tag not in tags:
            tags.append(tag[:20])
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE vpn_configs SET tags=? WHERE id=?",
                         (json.dumps(tags, ensure_ascii=False), cid))
            conn.commit()
        await safe_edit(event, f"🏷️ تگ «{tag}» به کانفیگ {cid} اضافه شد.\nتگ‌ها: {', '.join(tags)}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_آمار (\d+)$"))
    async def vpn_config_stats(event):
        record_cmd("کانفیگ_آمار")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row  = conn.execute("SELECT * FROM vpn_configs WHERE id=?", (cid,)).fetchone()
            labs = conn.execute(
                "SELECT * FROM vpn_config_lab WHERE config_id=? ORDER BY id DESC LIMIT 5", (cid,)
            ).fetchall()
            rots = conn.execute(
                "SELECT COUNT(*) FROM vpn_rotation WHERE config_id=?", (cid,)
            ).fetchone()[0]
        if not row:
            await safe_edit(event, "❌ پیدا نشد!"); return
        tags = json.loads(row["tags"] or "[]")
        lines = [
            f"نام: {row['name']}",
            f"پروتکل: {row['protocol']}",
            f"سرور: {row['server'][:40]}",
            f"استفاده: {row['used_count']} بار",
            f"آخرین استفاده: {row['last_used'][:10] or '—'}",
            f"پینگ: {row['latency']}ms" if row["latency"] else "پینگ: —",
            f"چرخش: {rots} بار",
            f"تگ‌ها: {', '.join(tags) or '—'}",
            f"علاقه‌مند: {'⭐' if row['favorite'] else '❌'}",
        ]
        if labs:
            lines.append("── آزمایشگاه ──")
            for l in labs:
                lines.append(f"  • {l['action']}: {l['result'][:30]}")
        await safe_edit(event, box(f"📊 آمار کانفیگ {cid}", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_چرخش$"))
    async def vpn_config_rotate(event):
        record_cmd("کانفیگ_چرخش")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT id,name FROM vpn_configs ORDER BY used_count ASC, RANDOM() LIMIT 1"
            ).fetchall()
        if not rows:
            await safe_edit(event, "❌ هیچ کانفیگی نیست!"); return
        chosen = rows[0]
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE vpn_configs SET used_count=used_count+1, last_used=? WHERE id=?",
                         (now_str(), chosen["id"]))
            conn.execute("INSERT INTO vpn_rotation(config_id,ts) VALUES(?,?)",
                         (chosen["id"], now_str()))
            conn.commit()
        await safe_edit(event, box("🔄 چرخش کانفیگ", [
            f"انتخاب‌شده: {chosen['name']}",
            f"آیدی: {chosen['id']}",
            "نمایش کامل: کانفیگ_نمایش " + str(chosen["id"]),
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_تکراری$"))
    async def vpn_config_dup_detect(event):
        record_cmd("کانفیگ_تکراری")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT fingerprint, COUNT(*) cnt, GROUP_CONCAT(id) ids, MIN(name) name "
                "FROM vpn_configs GROUP BY fingerprint HAVING cnt > 1"
            ).fetchall()
        if not rows:
            await safe_edit(event, "✅ هیچ کانفیگ تکراری پیدا نشد!"); return
        lines = [f"⚠️ {r['name']}: {r['cnt']} تکرار (id: {r['ids']})" for r in rows]
        await safe_edit(event, box(f"🔍 کانفیگ‌های تکراری ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_اشتراک (\d+)$"))
    async def vpn_config_share(event):
        record_cmd("کانفیگ_اشتراک")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM vpn_configs WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ پیدا نشد!"); return
        share_text = (
            f"🛡️ کانفیگ: {row['name']}\n"
            f"📡 پروتکل: {row['protocol']}\n"
            f"🌐 سرور: {row['server']}\n\n"
            f"`{row['content']}`"
        )
        await safe_edit(event, share_text)

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_آزمایشگاه (\d+)$"))
    async def vpn_config_lab_cmd(event):
        record_cmd("کانفیگ_آزمایشگاه")
        cid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM vpn_configs WHERE id=?", (cid,)).fetchone()
        if not row:
            await safe_edit(event, "❌ کانفیگ پیدا نشد!"); return
        results = []
        # بررسی طول
        length = len(row["content"])
        results.append(("طول محتوا", f"{length} کاراکتر"))
        # بررسی پروتکل
        results.append(("پروتکل", row["protocol"]))
        # بررسی سرور
        results.append(("سرور", row["server"] or "نامشخص"))
        # بررسی اثرانگشت
        results.append(("اثرانگشت", row["fingerprint"]))
        # بهینه‌سازی
        optimized = row["content"].strip()
        if "\r\n" in optimized:
            optimized = optimized.replace("\r\n", "\n")
            results.append(("بهینه‌سازی", "CRLF به LF تبدیل شد"))
        else:
            results.append(("بهینه‌سازی", "نیازی نیست"))
        with _db_lock:
            conn = get_conn()
            for action, res in results:
                conn.execute(
                    "INSERT INTO vpn_config_lab(config_id,action,result,ts) VALUES(?,?,?,?)",
                    (cid, action, res, now_str())
                )
            conn.commit()
        lines = [f"• {a}: {r}" for a, r in results]
        await safe_edit(event, box(f"🔬 آزمایشگاه کانفیگ {cid}", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سرور_رتبه$"))
    async def server_ranking(event):
        record_cmd("سرور_رتبه")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT server, COUNT(*) cnt, AVG(latency) avg_lat, SUM(used_count) usage "
                "FROM vpn_configs WHERE server != '' AND server != '—' "
                "GROUP BY server ORDER BY usage DESC, avg_lat ASC LIMIT 10"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 داده کافی نیست!"); return
        lines = []
        for i, r in enumerate(rows, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}."
            lat   = f"{r['avg_lat']:.0f}ms" if r["avg_lat"] else "—"
            lines.append(f"{medal} {r['server'][:25]} | استفاده: {r['usage'] or 0} | پینگ: {lat}")
        await safe_edit(event, box("🏆 رتبه‌بندی سرورها", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پینگ_سرور (.+)$"))
    async def ping_server(event):
        record_cmd("پینگ_سرور")
        host = event.pattern_match.group(1).strip()
        await safe_edit(event, f"⏳ در حال پینگ {host}...")
        try:
            import subprocess, re as _re
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "3", "-W", "2", host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=12)
            out = stdout.decode("utf-8", errors="ignore")
            m = _re.search(r"rtt.+?=\s*([\d.]+)/([\d.]+)/([\d.]+)", out)
            if m:
                mn, avg, mx = m.group(1), m.group(2), m.group(3)
                loss_m = _re.search(r"(\d+)%\s+packet loss", out)
                loss   = loss_m.group(1) if loss_m else "?"
                await safe_edit(event, box(f"📡 پینگ {host}", [
                    f"کمینه: {mn}ms",
                    f"میانگین: {avg}ms",
                    f"بیشینه: {mx}ms",
                    f"از دست رفته: {loss}%",
                ]))
                with _db_lock:
                    conn = get_conn()
                    conn.execute(
                        "UPDATE vpn_configs SET latency=? WHERE server LIKE ?",
                        (int(float(avg)), f"%{host}%")
                    )
                    conn.commit()
            else:
                await safe_edit(event, f"⚠️ سرور {host} پاسخ نداد یا پارس نشد.")
        except asyncio.TimeoutError:
            await safe_edit(event, f"⏰ تایم‌اوت! {host} پاسخ نمی‌دهد.")
        except FileNotFoundError:
            await safe_edit(event, "❌ دستور ping در دسترس نیست!")
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاریخچه_اتصال$"))
    async def connection_history(event):
        record_cmd("تاریخچه_اتصال")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT r.*,c.name FROM vpn_rotation r "
                "LEFT JOIN vpn_configs c ON r.config_id=c.id "
                "ORDER BY r.id DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 تاریخچه‌ای نیست!"); return
        lines = [f"• {r['ts'][:13]} | {r['name'] or r['config_id']}" for r in rows]
        await safe_edit(event, box(f"📅 تاریخچه اتصال ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تنظیم_فروشگاه (.+)\|(.+)$"))
    async def store_settings(event):
        record_cmd("تنظیم_فروشگاه")
        key = event.pattern_match.group(1).strip()
        val = event.pattern_match.group(2).strip()
        _store_set(key, val)
        await safe_edit(event, f"✅ تنظیم «{key}» = «{val}» ذخیره شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^محصول_ثبت (.+)\|(.+)\|(.+)$"))
    async def store_product_add(event):
        record_cmd("محصول_ثبت")
        name  = event.pattern_match.group(1).strip()
        price = event.pattern_match.group(2).strip()
        desc  = event.pattern_match.group(3).strip()
        try:
            price_int = int(price.replace(",","").replace("٬",""))
        except ValueError:
            await safe_edit(event, "❌ قیمت باید عدد باشد!"); return
        with _db_lock:
            conn = get_conn()
            pid = conn.execute(
                "INSERT INTO store_products(name,price,description,stock,ts) VALUES(?,?,?,0,?)",
                (name[:80], price_int, desc[:300], now_str())
            ).lastrowid
            conn.commit()
        await safe_edit(event, box("✅ محصول ثبت شد", [
            f"آیدی: {pid}",
            f"نام: {name}",
            f"قیمت: {price_int:,} تومان",
            f"توضیح: {desc[:50]}",
            f"موجودی: ۰ کانفیگ",
            "کانفیگ اضافه کن: کانفیگ_اضافه " + str(pid) + "|[محتوا]",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^محصول_لیست$"))
    async def store_product_list(event):
        record_cmd("محصول_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM store_products ORDER BY active DESC, id").fetchall()
        if not rows:
            await safe_edit(event, "📭 محصولی ثبت نشده!"); return
        lines = []
        for r in rows:
            with _db_lock:
                conn = get_conn()
                stock = conn.execute(
                    "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0", (r["id"],)
                ).fetchone()[0]
            status = "✅" if r["active"] and stock > 0 else ("⚠️ ناموجود" if stock == 0 else "🔴 غیرفعال")
            lines.append(f"{status} {r['id']}. {r['name'][:25]} — {r['price']:,} تومان | موجودی: {stock}")
        await safe_edit(event, box(f"🛍️ محصولات ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^محصول_ویرایش (\d+) (.+)=(.+)$"))
    async def store_product_edit(event):
        record_cmd("محصول_ویرایش")
        pid   = int(event.pattern_match.group(1))
        field = event.pattern_match.group(2).strip()
        val   = event.pattern_match.group(3).strip()
        allowed = {"name", "price", "description", "category", "active"}
        if field not in allowed:
            await safe_edit(event, f"❌ فیلد مجاز: {', '.join(allowed)}"); return
        if field == "price":
            try:
                val = str(int(val.replace(",","")))
            except ValueError:
                await safe_edit(event, "❌ قیمت باید عدد باشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(f"UPDATE store_products SET {field}=? WHERE id=?", (val, pid))
            conn.commit()
        await safe_edit(event, f"✅ محصول {pid}: {field} = {val}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^محصول_حذف (\d+)$"))
    async def store_product_del(event):
        record_cmd("محصول_حذف")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM store_products WHERE id=?", (pid,))
            conn.commit()
        await safe_edit(event, f"✅ محصول {pid} حذف شد." if c.rowcount else "❌ پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانفیگ_اضافه (\d+)\|(.+)$"))
    async def store_config_add(event):
        record_cmd("کانفیگ_اضافه")
        pid     = int(event.pattern_match.group(1))
        content = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            prod = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
        if not prod:
            await safe_edit(event, "❌ محصول پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            cid = conn.execute(
                "INSERT INTO store_configs(product_id,content,ts) VALUES(?,?,?)",
                (pid, content[:5000], now_str())
            ).lastrowid
            stock = conn.execute(
                "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0", (pid,)
            ).fetchone()[0]
            conn.commit()
        await safe_edit(event, box("✅ کانفیگ اضافه شد", [
            f"محصول: {prod['name']}",
            f"موجودی جدید: {stock}",
            f"کانفیگ id: {cid}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^موجودی_محصول (\d+)$"))
    async def store_stock_show(event):
        record_cmd("موجودی_محصول")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            prod  = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
            avail = conn.execute("SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0", (pid,)).fetchone()[0]
            sold  = conn.execute("SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=1", (pid,)).fetchone()[0]
        if not prod:
            await safe_edit(event, "❌ محصول پیدا نشد!"); return
        await safe_edit(event, box(f"📦 موجودی: {prod['name']}", [
            f"موجود: {avail} کانفیگ",
            f"فروخته‌شده: {sold}",
            f"مجموع: {avail + sold}",
            f"قیمت: {prod['price']:,} تومان",
            f"وضعیت: {'✅ موجود' if avail > 0 else '❌ ناموجود'}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سفارش_لیست(?: (.+))?$"))
    async def store_orders_list(event):
        record_cmd("سفارش_لیست")
        status = (event.pattern_match.group(1) or "").strip() or None
        with _db_lock:
            conn = get_conn()
            if status:
                rows = conn.execute(
                    "SELECT * FROM store_orders WHERE status=? ORDER BY id DESC LIMIT 20",
                    (status,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM store_orders ORDER BY id DESC LIMIT 20"
                ).fetchall()
        if not rows:
            await safe_edit(event, f"📭 سفارشی {'با وضعیت «'+status+'» ' if status else ''}وجود ندارد!"); return
        STATUS_EMOJI = {"pending":"⏳","approved":"✅","rejected":"❌","delivered":"📦"}
        lines = []
        for r in rows:
            emoji = STATUS_EMOJI.get(r["status"], "❓")
            lines.append(f"{emoji} {r['order_uid']} | {r['name'][:12]} | {r['product_name'][:15]} | {r['ts'][:10]}")
        await safe_edit(event, box(f"📋 سفارش‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^_سفارش_تایید_v1 (.+)$"))
    async def store_order_approve_v1(event):
        record_cmd("_سفارش_تایید_v1")
        oid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute("SELECT * FROM store_orders WHERE order_uid=?", (oid,)).fetchone()
        if not order:
            await safe_edit(event, f"❌ سفارش «{oid}» پیدا نشد!"); return
        if order["status"] != "pending":
            await safe_edit(event, f"⚠️ وضعیت سفارش: {order['status']}"); return
        with _db_lock:
            conn = get_conn()
            cfg = conn.execute(
                "SELECT * FROM store_configs WHERE product_id=? AND sold=0 LIMIT 1",
                (order["product_id"],)
            ).fetchone()
        if not cfg:
            await safe_edit(event, "❌ موجودی تمام شد! کانفیگ جدید اضافه کن."); return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE store_configs SET sold=1, order_id=? WHERE id=?",
                         (order["id"], cfg["id"]))
            conn.execute("UPDATE store_orders SET status='approved', config_id=? WHERE order_uid=?",
                         (cfg["id"], oid))
            conn.commit()
        # ارسال محصول/تحویل به مشتری — V9 Product Context Aware
        try:
            pid = order.get("product_id", 0)
            pk = _get_product_knowledge(pid) if pid else {}
            # متن تحویل اختصاصی از Knowledge یا پیش‌فرض
            delivery_text_custom = (pk.get("delivery_text") or "").strip()
            if delivery_text_custom:
                # متن تحویل کاملاً سفارشی از Knowledge
                delivery_msg = (
                    f"✅ سفارش شما تایید شد!\n\n"
                    f"📦 محصول: {order['product_name']}\n"
                    f"🆔 کد سفارش: {oid}\n\n"
                    f"{delivery_text_custom}"
                )
            elif cfg.get("content"):
                # محتوای store_configs وجود دارد — ممکن است کانفیگ، کد، لینک یا هر چیز دیگری باشد
                product_type = (pk.get("product_type") or "").lower()
                content_label = "محتوا"
                if "vpn" in product_type or "کانفیگ" in product_type or "اشتراک" in product_type:
                    content_label = "کانفیگ"
                elif "لایسنس" in product_type or "license" in product_type or "کد" in product_type:
                    content_label = "کد فعال‌سازی"
                elif "دوره" in product_type or "آموزش" in product_type:
                    content_label = "لینک دسترسی"
                elif "اکانت" in product_type or "account" in product_type:
                    content_label = "اطلاعات اکانت"
                delivery_msg = (
                    f"✅ سفارش شما تایید شد!\n\n"
                    f"📦 محصول: {order['product_name']}\n"
                    f"🆔 کد سفارش: {oid}\n\n"
                    f"🎁 {content_label}:\n`{cfg['content']}`"
                )
            else:
                # هیچ محتوایی نیست
                delivery_msg = (
                    f"✅ سفارش شما تایید شد!\n\n"
                    f"📦 محصول: {order['product_name']}\n"
                    f"🆔 کد سفارش: {oid}\n\n"
                    f"📩 اطلاعات تکمیلی به زودی ارسال می‌شود."
                )
            await client.send_message(order["uid"], delivery_msg)
        except Exception as ex:
            logger.warning(f"send delivery to customer: {ex}")
        _crm_update(order["uid"], order["price"], order["product_name"])
        _log_event_replay(oid, "delivery_sent", f"product: {order['product_name']}")
        await safe_edit(event, box("✅ سفارش تایید شد", [
            f"سفارش: {oid}",
            f"مشتری: {order['name']} ({order['uid']})",
            f"محصول: {order['product_name']}",
            "✅ تحویل ارسال شد",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^_سفارش_رد_v1 (.+?) (.+)$"))
    async def store_order_reject_v1(event):
        record_cmd("_سفارش_رد_v1")
        oid    = event.pattern_match.group(1).strip()
        reason = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute("SELECT * FROM store_orders WHERE order_uid=?", (oid,)).fetchone()
        if not order:
            await safe_edit(event, f"❌ سفارش پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE store_orders SET status='rejected' WHERE order_uid=?", (oid,))
            conn.commit()
        try:
            await client.send_message(order["uid"],
                f"❌ سفارش شما رد شد.\n"
                f"📦 محصول: {order['product_name']}\n"
                f"🆔 کد: {oid}\n"
                f"دلیل: {reason}"
            )
        except Exception as ex:
            logger.warning(f"reject notify: {ex}")
        await safe_edit(event, f"✅ سفارش {oid} رد شد.\nمشتری مطلع شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سفارش_جستجو (.+)$"))
    async def store_order_search(event):
        record_cmd("سفارش_جستجو")
        q = event.pattern_match.group(1).strip()
        ql = f"%{q}%"
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM store_orders WHERE order_uid LIKE ? OR name LIKE ? OR username LIKE ? OR product_name LIKE ? ORDER BY id DESC LIMIT 15",
                (ql, ql, ql, ql)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"❌ نتیجه‌ای برای «{q}» نیست!"); return
        lines = [f"• {r['order_uid']} | {r['name'][:12]} | {r['product_name'][:15]} | {r['status']}"
                 for r in rows]
        await safe_edit(event, box(f"🔍 سفارش‌های «{q}» ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کوپن_ثبت (.+)\|(\d+)$"))
    async def store_coupon_add(event):
        record_cmd("کوپن_ثبت")
        code    = event.pattern_match.group(1).strip().upper()
        discount = int(event.pattern_match.group(2))
        if not (1 <= discount <= 100):
            await safe_edit(event, "❌ تخفیف باید بین ۱ تا ۱۰۰ باشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO store_coupons(code,discount,ts) VALUES(?,?,?) "
                "ON CONFLICT(code) DO UPDATE SET discount=excluded.discount",
                (code, discount, now_str())
            )
            conn.commit()
        await safe_edit(event, f"🎟️ کوپن «{code}» با تخفیف {discount}٪ ثبت شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کوپن_لیست$"))
    async def store_coupon_list(event):
        record_cmd("کوپن_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute("SELECT * FROM store_coupons ORDER BY active DESC, discount DESC").fetchall()
        if not rows:
            await safe_edit(event, "📭 کوپنی ثبت نشده!"); return
        lines = [
            f"{'✅' if r['active'] else '❌'} {r['code']} — {r['discount']}٪ | {r['uses']}/{r['max_uses']} استفاده"
            for r in rows
        ]
        await safe_edit(event, box(f"🎟️ کوپن‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_انتظار_فروش (\d+)$"))
    async def store_waiting_list(event):
        record_cmd("لیست_انتظار_فروش")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            prod = conn.execute("SELECT name FROM store_products WHERE id=?", (pid,)).fetchone()
            rows = conn.execute(
                "SELECT w.*,c.name,c.username FROM waiting_list w "
                "LEFT JOIN contacts c ON w.uid=c.uid WHERE w.product_id=? ORDER BY w.ts",
                (pid,)
            ).fetchall()
        pname = prod["name"] if prod else f"محصول {pid}"
        if not rows:
            await safe_edit(event, f"📭 کسی در لیست انتظار «{pname}» نیست!"); return
        lines = [f"• {r['name'] or r['uid']} @{r['username'] or '—'} | {r['ts'][:10]}" for r in rows]
        await safe_edit(event, box(f"⏳ لیست انتظار: {pname} ({len(rows)})", lines))

    # ════════════════════════════════════════════════════════════
    #  🏪 COMPLETE PURCHASE FLOW — State Machine + Receipt Processor
    # ════════════════════════════════════════════════════════════

    # ── State Machine helpers ───────────────────────────────────
    def _cust_state(uid: int) -> dict:
        """دریافت وضعیت مشتری"""
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM customer_states WHERE uid=?", (uid,)).fetchone()
        if not row:
            return {"uid": uid, "state": "idle", "product_id": 0, "order_uid": "", "data": "{}"}
        return dict(row)

    def _set_cust_state(uid: int, state: str, product_id: int = 0,
                        order_uid: str = "", data: dict = None):
        """ذخیره وضعیت مشتری"""
        import json as _json
        data_str = _json.dumps(data or {}, ensure_ascii=False)
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO customer_states(uid,state,product_id,order_uid,data,updated) "
                "VALUES(?,?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET "
                "state=excluded.state, product_id=excluded.product_id, "
                "order_uid=excluded.order_uid, data=excluded.data, updated=excluded.updated",
                (uid, state, product_id, order_uid, data_str, now_str())
            )
            conn.commit()

    def _reset_cust_state(uid: int):
        """ریست وضعیت مشتری"""
        _set_cust_state(uid, "idle", 0, "", {})

    def _get_report_dest(me_id: int):
        """دریافت مقصد گزارش"""
        dest = _store_setting("report_dest", "")
        if not dest or dest == "saved":
            return me_id
        try:
            return int(dest)
        except Exception:
            return me_id

    def _log_order_history(order_uid: str, action: str, note: str = ""):
        """ثبت تاریخچه سفارش"""
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO store_order_history(order_uid,action,note,ts) VALUES(?,?,?,?)",
                (order_uid, action[:100], note[:500], now_str())
            )
            conn.commit()

    def _build_products_text() -> str:
        """ساخت متن نمایش محصولات"""
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT p.*, "
                "(SELECT COUNT(*) FROM store_configs c "
                " WHERE c.product_id=p.id AND c.sold=0) AS avail "
                "FROM store_products p WHERE p.active=1 ORDER BY p.id"
            ).fetchall()
        if not rows:
            return "\u274c \u0647\u06cc\u0686 \u0645\u062d\u0635\u0648\u0644\u06cc \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a."
        NL = "\n"
        SEP = "\u2501" * 17
        lines = ["\U0001f6d2 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0645\u0648\u062c\u0648\u062f:", SEP]
        for r in rows:
            avail = r["avail"] or 0
            stock_label = "\u2705 \u0645\u0648\u062c\u0648\u062f" if avail > 0 else "\u274c \u0646\u0627\u0645\u0648\u062c\u0648\u062f"
            lines.append(
                f"\U0001f539 {r['name']}" + NL
                + f"\U0001f4b0 \u0642\u06cc\u0645\u062a: {r['price']:,} \u062a\u0648\u0645\u0627\u0646" + NL
                + f"\U0001f4dd {r['description'] or '\u2014'}" + NL
                + f"\U0001f4e6 {stock_label} ({avail} \u0639\u062f\u062f)" + NL
                + f"\U0001f194 \u06a9\u062f \u0645\u062d\u0635\u0648\u0644: {r['id']}" + NL
                + SEP
            )
        lines.append("\U0001f4cc \u0628\u0631\u0627\u06cc \u062e\u0631\u06cc\u062f \u0628\u0646\u0648\u06cc\u0633: \u062e\u0631\u06cc\u062f [ID]")
        lines.append("\u0645\u062b\u0627\u0644: \u062e\u0631\u06cc\u062f 1")
        return NL.join(lines)

    def _build_payment_text(product: dict, order_uid: str) -> str:
        """ساخت متن اطلاعات پرداخت"""
        card_number  = _store_setting("card_number", "6037-XXXX-XXXX-XXXX")
        card_holder  = _store_setting("card_holder", "\u0646\u0627\u0645 \u0635\u0627\u062d\u0628 \u06a9\u0627\u0631\u062a")
        bank_name    = _store_setting("bank_name", "\u0628\u0627\u0646\u06a9")
        payment_note = _store_setting("payment_note", "")
        NL = "\n"
        SEP = "\u2501" * 17
        note_line = ("\U0001f4cc " + payment_note + NL) if payment_note else ""
        return (
            f"\U0001f4b3 \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u067e\u0631\u062f\u0627\u062e\u062a{NL}{SEP}{NL}"
            f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644: {product['name']}{NL}"
            f"\U0001f4b0 \u0645\u0628\u0644\u063a: {product['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}{SEP}{NL}"
            f"\U0001f3e6 \u0628\u0627\u0646\u06a9: {bank_name}{NL}"
            f"\U0001f4b3 \u0634\u0645\u0627\u0631\u0647 \u06a9\u0627\u0631\u062a:{NL}"
            f"<code>{card_number}</code>{NL}"
            f"\U0001f464 \u0635\u0627\u062d\u0628 \u06a9\u0627\u0631\u062a: {card_holder}{NL}{SEP}{NL}"
            f"\U0001f4cb \u0634\u0646\u0627\u0633\u0647 \u0633\u0641\u0627\u0631\u0634: <code>{order_uid}</code>{NL}{NL}"
            f"{note_line}"
            f"\u2705 \u067e\u0633 \u0627\u0632 \u0648\u0627\u0631\u06cc\u0632\u060c \u062a\u0635\u0648\u06cc\u0631 \u0641\u06cc\u0634 \u0631\u0627 \u0627\u06cc\u0646\u062c\u0627 \u0627\u0631\u0633\u0627\u0644 \u06a9\u0646\u06cc\u062f.{NL}"
            f"\u26a0\ufe0f \u0646\u0627\u0645 \u0635\u0627\u062d\u0628 \u06a9\u0627\u0631\u062a \u0648 \u0645\u0628\u0644\u063a \u0631\u0627 \u062f\u0642\u06cc\u0642\u0627\u064b \u0686\u06a9 \u06a9\u0646\u06cc\u062f."
        )

    async def _send_receipt_report(sender, order_uid: str, product_name: str,
                                    price: int, receipt_file: str, me):
        """ارسال گزارش فیش به مقصد تنظیم‌شده"""
        import json as _json
        sname = ((getattr(sender, "first_name", "") or "")
                 + " " + (getattr(sender, "last_name", "") or "")).strip() or str(sender.id)
        susername = getattr(sender, "username", "") or ""
        dest = _get_report_dest(me.id)
        NL = "\n"
        report_text = (
            f"\U0001f514 **\u0633\u0641\u0627\u0631\u0634 \u062c\u062f\u06cc\u062f \u2014 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u062a\u0627\u06cc\u06cc\u062f**{NL}{NL}"
            f"\U0001f464 \u0646\u0627\u0645: {sname}{NL}"
            f"\U0001f517 \u06cc\u0648\u0632\u0631\u0646\u06cc\u0645: @{susername or '\u2014'}{NL}"
            f"\U0001f194 \u0622\u06cc\u062f\u06cc: `{sender.id}`{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644: {product_name or '\u2014'}{NL}"
            f"\U0001f4b0 \u0645\u0628\u0644\u063a: {price:,} \u062a\u0648\u0645\u0627\u0646{NL}"
            f"\U0001f550 \u0632\u0645\u0627\u0646: {now_str()}{NL}"
            f"\U0001f194 \u06a9\u062f \u0633\u0641\u0627\u0631\u0634: `{order_uid}`{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u062f\u0633\u062a\u0648\u0631\u0627\u062a:{NL}"
            f"\u2022 `\u0633\u0641\u0627\u0631\u0634_\u062a\u0627\u06cc\u06cc\u062f {order_uid}`{NL}"
            f"\u2022 `\u0633\u0641\u0627\u0631\u0634_\u0631\u062f {order_uid} [\u062f\u0644\u06cc\u0644]`"
        )
        try:
            if receipt_file and os.path.exists(receipt_file):
                await client.send_file(dest, receipt_file, caption=report_text, parse_mode='md')
            else:
                await client.send_message(dest, report_text, parse_mode='md')
        except Exception as ex:
            logger.warning(f"send_receipt_report to {dest}: {ex}")
            try:
                if dest != me.id:
                    if receipt_file and os.path.exists(receipt_file):
                        await client.send_file(me.id, receipt_file, caption=report_text, parse_mode='md')
                    else:
                        await client.send_message(me.id, report_text, parse_mode='md')
            except Exception:
                pass

    # ─── Customer: مشتری: خرید / کانفیگ / اشتراک / محصولات ────
    @client.on(events.NewMessage(incoming=True,
        pattern=r"^(\u062e\u0631\u06cc\u062f|\u06a9\u0627\u0646\u0641\u06cc\u06af|\u0627\u0634\u062a\u0631\u0627\u06a9|\u0645\u062d\u0635\u0648\u0644\u0627\u062a|\u0644\u06cc\u0633\u062a_\u0645\u062d\u0635\u0648\u0644\u0627\u062a|shop|store)$"))
    async def customer_browse_trigger(event):
        """مشتری درخواست مشاهده محصولات"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            _set_cust_state(sender.id, "BROWSING_PRODUCTS")
            await event.reply(_build_products_text())
        except Exception as ex:
            logger.debug(f"customer_browse_trigger: {ex}")

    @client.on(events.NewMessage(incoming=True,
        pattern=r"^\u062e\u0631\u06cc\u062f\s+(\d+)$"))
    async def customer_select_product(event):
        """مشتری محصول انتخاب می‌کند"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            pid = int(event.pattern_match.group(1))
            with _db_lock:
                conn = get_conn()
                prod = conn.execute(
                    "SELECT * FROM store_products WHERE id=? AND active=1", (pid,)
                ).fetchone()
                avail = (conn.execute(
                    "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0", (pid,)
                ).fetchone() or [0])[0]
            if not prod:
                await event.reply(
                    "\u274c \u0645\u062d\u0635\u0648\u0644 \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!\n"
                    "\u0644\u06cc\u0633\u062a \u0645\u062d\u0635\u0648\u0644\u0627\u062a: \u0645\u062d\u0635\u0648\u0644\u0627\u062a"
                )
                return
            if avail == 0:
                with _db_lock:
                    conn = get_conn()
                    try:
                        conn.execute(
                            "INSERT INTO waiting_list(uid,product_id,ts) VALUES(?,?,?)",
                            (sender.id, pid, now_str())
                        )
                        conn.commit()
                    except Exception:
                        pass
                await event.reply(
                    f"\u274c \u0645\u062a\u0623\u0633\u0641\u0627\u0646\u0647 \u00ab{prod['name']}\u00bb \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a.\n"
                    "\u0634\u0645\u0627 \u0628\u0647 \u0644\u06cc\u0633\u062a \u0627\u0646\u062a\u0638\u0627\u0631 \u0627\u0636\u0627\u0641\u0647 \u0634\u062f\u06cc\u062f."
                )
                return
            order_uid = _gen_order_id()
            sname = ((getattr(sender, "first_name", "") or "")
                     + " " + (getattr(sender, "last_name", "") or "")).strip() or str(sender.id)
            susername = getattr(sender, "username", "") or ""
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO store_orders"
                    "(order_uid,uid,username,name,product_id,product_name,price,status,ts) "
                    "VALUES(?,?,?,?,?,?,?,'waiting_payment',?)",
                    (order_uid, sender.id, susername, sname,
                     pid, prod["name"], prod["price"], now_str())
                )
                conn.commit()
            _log_order_history(order_uid, "created", f"product: {prod['name']}")
            _set_cust_state(sender.id, "WAITING_PAYMENT", pid, order_uid,
                            {"product_name": prod["name"], "price": prod["price"]})
            await event.reply(
                _build_payment_text(dict(prod), order_uid),
                parse_mode='html'
            )
        except Exception as ex:
            logger.debug(f"customer_select_product: {ex}")

    @client.on(events.NewMessage(incoming=True,
        pattern=r"^(\u062a\u0645\u062f\u06cc\u062f|\u062a\u0645\u062f\u06cc\u062f_\u0627\u0634\u062a\u0631\u0627\u06a9)$"))
    async def customer_renewal_trigger(event):
        """مشتری درخواست تمدید"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            with _db_lock:
                conn = get_conn()
                last = conn.execute(
                    "SELECT * FROM store_orders WHERE uid=? AND status='approved'"
                    " ORDER BY id DESC LIMIT 1",
                    (sender.id,)
                ).fetchone()
            if not last:
                await event.reply(
                    "\u274c \u062e\u0631\u06cc\u062f\u06cc \u06cc\u0627\u0641\u062a \u0646\u0634\u062f.\n\n"
                    + _build_products_text()
                )
                return
            with _db_lock:
                conn = get_conn()
                prod = conn.execute(
                    "SELECT * FROM store_products WHERE id=? AND active=1",
                    (last["product_id"],)
                ).fetchone()
            if not prod:
                await event.reply(
                    "\U0001f4cc \u0645\u062d\u0635\u0648\u0644 \u0642\u0628\u0644\u06cc \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a.\n\n"
                    + _build_products_text()
                )
                return
            NL = "\n"
            await event.reply(
                f"\U0001f504 \u062a\u0645\u062f\u06cc\u062f \u0627\u0634\u062a\u0631\u0627\u06a9{NL}"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
                f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644: {prod['name']}{NL}"
                f"\U0001f4b0 \u0642\u06cc\u0645\u062a: {prod['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
                f"\u0628\u0631\u0627\u06cc \u062a\u0645\u062f\u06cc\u062f \u0628\u0646\u0648\u06cc\u0633:{NL}"
                f"\u062e\u0631\u06cc\u062f {prod['id']}"
            )
        except Exception as ex:
            logger.debug(f"customer_renewal_trigger: {ex}")

    @client.on(events.NewMessage(incoming=True,
        pattern=r"^(\u0644\u063a\u0648_\u0633\u0641\u0627\u0631\u0634|\u0627\u0646\u0635\u0631\u0627\u0641|cancel)$"))
    async def customer_cancel_order(event):
        """لغو سفارش فعال"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            cst = _cust_state(sender.id)
            if cst["state"] not in ("WAITING_PAYMENT", "WAITING_RECEIPT"):
                await event.reply(
                    "\u2139\ufe0f \u0633\u0641\u0627\u0631\u0634 \u0641\u0639\u0627\u0644\u06cc \u0628\u0631\u0627\u06cc \u0644\u063a\u0648 \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f."
                )
                return
            order_uid = cst["order_uid"]
            if order_uid:
                with _db_lock:
                    conn = get_conn()
                    conn.execute(
                        "UPDATE store_orders SET status='cancelled' "
                        "WHERE order_uid=? AND status IN ('waiting_payment','pending')",
                        (order_uid,)
                    )
                    conn.commit()
                _log_order_history(order_uid, "cancelled", "by customer")
            _reset_cust_state(sender.id)
            await event.reply(
                "\u2705 \u0633\u0641\u0627\u0631\u0634 \u0644\u063a\u0648 \u0634\u062f.\n"
                "\u0645\u062d\u0635\u0648\u0644\u0627\u062a"
            )
        except Exception as ex:
            logger.debug(f"customer_cancel_order: {ex}")

    @client.on(events.NewMessage(incoming=True,
        pattern=r"^(\u0648\u0636\u0639\u06cc\u062a_\u0633\u0641\u0627\u0631\u0634|\u0633\u0641\u0627\u0631\u0634_\u0645\u0646|\u0648\u0636\u0639\u06cc\u062a)$"))
    async def customer_order_status(event):
        """وضعیت آخرین سفارش"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            with _db_lock:
                conn = get_conn()
                orders = conn.execute(
                    "SELECT * FROM store_orders WHERE uid=? ORDER BY id DESC LIMIT 3",
                    (sender.id,)
                ).fetchall()
            if not orders:
                await event.reply(
                    "\U0001f4ed \u0647\u06cc\u0686 \u0633\u0641\u0627\u0631\u0634\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647.\n"
                    "\u0645\u062d\u0635\u0648\u0644\u0627\u062a"
                )
                return
            STATUS_FA = {
                "waiting_payment": "\u23f3 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u067e\u0631\u062f\u0627\u062e\u062a",
                "pending":         "\U0001f50d \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc",
                "approved":        "\u2705 \u062a\u0627\u06cc\u06cc\u062f \u2014 \u06a9\u0627\u0646\u0641\u06cc\u06af \u0627\u0631\u0633\u0627\u0644 \u0634\u062f",
                "rejected":        "\u274c \u0631\u062f \u0634\u062f\u0647",
                "delivered":       "\U0001f4e6 \u062a\u062d\u0648\u06cc\u0644 \u062f\u0627\u062f\u0647 \u0634\u062f\u0647",
                "cancelled":       "\U0001f6ab \u0644\u063a\u0648 \u0634\u062f\u0647",
            }
            NL = "\n"
            SEP = "\u2501" * 17
            lines = ["\U0001f4e6 \u0622\u062e\u0631\u06cc\u0646 \u0633\u0641\u0627\u0631\u0634\u0627\u062a:"]
            for o in orders:
                st = STATUS_FA.get(o["status"], o["status"])
                lines.append(
                    f"{SEP}{NL}\U0001f194 {o['order_uid']}{NL}"
                    f"\U0001f4e6 {o['product_name'] or '\u2014'}{NL}"
                    f"\U0001f4b0 {o['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}"
                    f"\U0001f4cc {st}{NL}"
                    f"\U0001f550 {o['ts'][:16]}"
                )
            await event.reply(NL.join(lines))
        except Exception as ex:
            logger.debug(f"customer_order_status: {ex}")

    # ─── State Machine: دریافت رسید با State Machine کامل ───────
    @client.on(events.NewMessage(incoming=True))
    async def store_receipt_listener(event):
        """دریافت رسید پرداخت با State Machine"""
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            if event.is_group or event.is_channel:
                return
            has_photo = bool(event.photo) or bool(event.media)
            text = event.text or ""
            cst = _cust_state(sender.id)
            import json as _json

            # ── حالت: در انتظار پرداخت و عکس ارسال شده ──────────
            if cst["state"] == "WAITING_PAYMENT" and has_photo:
                order_uid = cst["order_uid"]
                if not order_uid:
                    await event.reply(
                        "\u26a0\ufe0f \u0627\u0628\u062a\u062f\u0627 \u0645\u062d\u0635\u0648\u0644\u06cc \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646: \u0645\u062d\u0635\u0648\u0644\u0627\u062a"
                    )
                    return
                receipt_path = ""
                try:
                    dl_path = os.path.join(DL_DIR, f"receipt_{order_uid}.jpg")
                    await client.download_media(event.media, file=dl_path)
                    receipt_path = dl_path
                except Exception as dl_ex:
                    logger.debug(f"receipt_dl: {dl_ex}")
                with _db_lock:
                    conn = get_conn()
                    conn.execute(
                        "UPDATE store_orders SET status='pending', receipt_file=?"
                        " WHERE order_uid=?",
                        (receipt_path, order_uid)
                    )
                    conn.commit()
                _log_order_history(order_uid, "receipt_received", receipt_path)
                cst_data = _json.loads(cst.get("data", "{}") or "{}")
                _set_cust_state(sender.id, "WAITING_RECEIPT",
                                cst["product_id"], order_uid, cst_data)
                await event.reply(
                    f"\u2705 \u0631\u0633\u06cc\u062f \u0634\u0645\u0627 \u062f\u0631\u06cc\u0627\u0641\u062a \u0634\u062f!\n"
                    f"\U0001f194 \u06a9\u062f \u067e\u06cc\u06af\u06cc\u0631\u06cc: <code>{order_uid}</code>\n"
                    f"\u23f3 \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc...",
                    parse_mode='html'
                )
                await _send_receipt_report(
                    sender, order_uid,
                    cst_data.get("product_name", ""),
                    cst_data.get("price", 0),
                    receipt_path, me
                )
                return

            # ── حالت: رسید ارسال شده — در انتظار بررسی ──────────
            if cst["state"] == "WAITING_RECEIPT":
                order_uid = cst["order_uid"]
                await event.reply(
                    f"\u23f3 \u0633\u0641\u0627\u0631\u0634 (<code>{order_uid}</code>)"
                    f" \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0627\u0633\u062a.\n"
                    f"\u0644\u0637\u0641\u0627\u064b \u0645\u0646\u062a\u0638\u0631 \u0628\u0645\u0627\u0646\u06cc\u062f.",
                    parse_mode='html'
                )
                return

            # ── Trigger قدیمی: #فیش یا عکس بدون state ───────────
            trigger = _store_setting("receipt_trigger", "#\u0641\u06cc\u0634")
            if (trigger in text or has_photo) and cst["state"] == "idle":
                with _db_lock:
                    conn = get_conn()
                    pending_order = conn.execute(
                        "SELECT * FROM store_orders WHERE uid=?"
                        " AND status='waiting_payment' ORDER BY id DESC LIMIT 1",
                        (sender.id,)
                    ).fetchone()
                if pending_order:
                    order_uid = pending_order["order_uid"]
                    receipt_path = ""
                    if has_photo:
                        try:
                            dl_path = os.path.join(DL_DIR, f"receipt_{order_uid}.jpg")
                            await client.download_media(event.media, file=dl_path)
                            receipt_path = dl_path
                            with _db_lock:
                                conn = get_conn()
                                conn.execute(
                                    "UPDATE store_orders SET status='pending',receipt_file=?"
                                    " WHERE order_uid=?", (receipt_path, order_uid)
                                )
                                conn.commit()
                        except Exception:
                            pass
                        _log_order_history(order_uid, "receipt_received", "trigger")
                        _set_cust_state(
                            sender.id, "WAITING_RECEIPT",
                            pending_order["product_id"], order_uid,
                            {"product_name": pending_order["product_name"],
                             "price": pending_order["price"]}
                        )
                        await event.reply(
                            f"\u2705 \u0631\u0633\u06cc\u062f \u062f\u0631\u06cc\u0627\u0641\u062a \u0634\u062f!\n"
                            f"\U0001f194 \u06a9\u062f: <code>{order_uid}</code>\n"
                            f"\u23f3 \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc...",
                            parse_mode='html'
                        )
                        await _send_receipt_report(
                            sender, order_uid,
                            pending_order["product_name"],
                            pending_order["price"],
                            receipt_path, me
                        )
                    else:
                        await event.reply(
                            "\U0001f4ce \u0644\u0637\u0641\u0627\u064b \u062a\u0635\u0648\u06cc\u0631"
                            " \u0641\u06cc\u0634 \u067e\u0631\u062f\u0627\u062e\u062a \u0631\u0627"
                            " \u0627\u0631\u0633\u0627\u0644 \u06a9\u0646\u06cc\u062f."
                        )
                else:
                    if has_photo:
                        sname = ((getattr(sender,"first_name","") or "")
                                 + " " + (getattr(sender,"last_name","") or "")).strip() or str(sender.id)
                        susername = getattr(sender,"username","") or ""
                        order_uid = _gen_order_id()
                        import re as _re
                        pm = _re.search(r"#?\u0645\u062d\u0635\u0648\u0644[:\s]*(\d+)", text)
                        pid_match = int(pm.group(1)) if pm else 0
                        pname, pprice = "", 0
                        if pid_match:
                            with _db_lock:
                                conn = get_conn()
                                pr = conn.execute(
                                    "SELECT * FROM store_products WHERE id=?", (pid_match,)
                                ).fetchone()
                            if pr:
                                pname = pr["name"]
                                pprice = pr["price"]
                        with _db_lock:
                            conn = get_conn()
                            conn.execute(
                                "INSERT INTO store_orders"
                                "(order_uid,uid,username,name,product_id,product_name,price,status,ts)"
                                " VALUES(?,?,?,?,?,?,?,'pending',?)",
                                (order_uid, sender.id, susername, sname,
                                 pid_match, pname, pprice, now_str())
                            )
                            conn.commit()
                        receipt_path = ""
                        try:
                            dl_path = os.path.join(DL_DIR, f"receipt_{order_uid}.jpg")
                            await client.download_media(event.media, file=dl_path)
                            receipt_path = dl_path
                            with _db_lock:
                                conn = get_conn()
                                conn.execute(
                                    "UPDATE store_orders SET receipt_file=? WHERE order_uid=?",
                                    (receipt_path, order_uid)
                                )
                                conn.commit()
                        except Exception:
                            pass
                        _log_order_history(order_uid, "created+receipt", "trigger-new")
                        _set_cust_state(sender.id, "WAITING_RECEIPT",
                                        pid_match, order_uid,
                                        {"product_name": pname, "price": pprice})
                        await event.reply(
                            f"\u2705 \u0633\u0641\u0627\u0631\u0634 \u062b\u0628\u062a \u0634\u062f!\n"
                            f"\U0001f194 \u06a9\u062f: <code>{order_uid}</code>\n"
                            f"\u23f3 \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc...",
                            parse_mode='html'
                        )
                        await _send_receipt_report(
                            sender, order_uid, pname, pprice, receipt_path, me
                        )
        except Exception as ex:
            logger.debug(f"receipt_listener: {ex}")


    # ════════════════════════════════════════════════════════════
    #  🏪 Store — Enhanced Approve/Reject Flow with Full Updates
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0633\u0641\u0627\u0631\u0634_\u062a\u0627\u06cc\u06cc\u062f (.+)$"))
    async def store_order_approve_full(event):
        """تایید سفارش با به‌روزرسانی کامل"""
        record_cmd("\u0633\u0641\u0627\u0631\u0634_\u062a\u0627\u06cc\u06cc\u062f")
        import json as _json
        oid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute(
                "SELECT * FROM store_orders WHERE order_uid=?", (oid,)
            ).fetchone()
        if not order:
            await safe_edit(event, f"\u274c \u0633\u0641\u0627\u0631\u0634 \u00ab{oid}\u00bb \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        if order["status"] == "approved":
            await safe_edit(event, "\u26a0\ufe0f \u0633\u0641\u0627\u0631\u0634 \u0642\u0628\u0644\u0627\u064b \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f\u0647!")
            return
        if order["status"] not in ("pending", "waiting_payment"):
            await safe_edit(event,
                f"\u26a0\ufe0f \u0648\u0636\u0639\u06cc\u062a \u0641\u0639\u0644\u06cc: {order['status']}"
                f" \u2014 \u062a\u0627\u06cc\u06cc\u062f \u0645\u0645\u06a9\u0646 \u0646\u06cc\u0633\u062a."
            )
            return
        with _db_lock:
            conn = get_conn()
            cfg = conn.execute(
                "SELECT * FROM store_configs WHERE product_id=? AND sold=0 LIMIT 1",
                (order["product_id"],)
            ).fetchone()
        if not cfg:
            await safe_edit(event,
                "\u274c \u0645\u0648\u062c\u0648\u062f\u06cc \u062a\u0645\u0627\u0645 \u0634\u062f!"
                " \u06a9\u0627\u0646\u0641\u06cc\u06af \u062c\u062f\u06cc\u062f: \u06a9\u0627\u0646\u0641\u06cc\u06af_\u0627\u0636\u0627\u0641\u0647 [id]|[\u0645\u062d\u062a\u0648\u0627]"
            )
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE store_configs SET sold=1, order_id=? WHERE id=?",
                         (order["id"], cfg["id"]))
            conn.execute("UPDATE store_orders SET status='approved', config_id=? WHERE order_uid=?",
                         (cfg["id"], oid))
            conn.execute("UPDATE store_products SET stock=MAX(0,stock-1) WHERE id=?",
                         (order["product_id"],))
            conn.commit()
        _log_order_history(oid, "approved", f"config_id:{cfg['id']}")
        _crm_update(order["uid"], order["price"], order["product_name"])
        _set_cust_state(order["uid"], "DELIVERED", order["product_id"], oid,
                        {"product_name": order["product_name"]})
        with _db_lock:
            conn = get_conn()
            avail = conn.execute(
                "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0",
                (order["product_id"],)
            ).fetchone()[0]
            conn.execute("INSERT INTO activity_log(type,value,ts) VALUES('sale',?,?)",
                         (order["price"], now_str()))
            conn.commit()
        NL = "\n"
        try:
            await client.send_message(
                order["uid"],
                f"\u2705 **\u0633\u0641\u0627\u0631\u0634 \u0634\u0645\u0627 \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f!**{NL}{NL}"
                f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644: {order['product_name']}{NL}"
                f"\U0001f194 \u06a9\u062f \u0633\u0641\u0627\u0631\u0634: `{oid}`{NL}{NL}"
                f"\U0001f511 \u06a9\u0627\u0646\u0641\u06cc\u06af \u0634\u0645\u0627:{NL}"
                f"`{cfg['content']}`{NL}{NL}"
                f"\u0627\u0632 \u062e\u0631\u06cc\u062f \u0634\u0645\u0627 \u0645\u062a\u0634\u06a9\u0631\u06cc\u0645! \U0001f64f",
                parse_mode='md'
            )
        except Exception as ex:
            logger.warning(f"approve send config: {ex}")
        low_th = int(_store_setting("low_stock_threshold", "3"))
        low_msg = ""
        if avail <= low_th:
            low_msg = (
                f"\n\u26a0\ufe0f \u0647\u0634\u062f\u0627\u0631: \u0645\u0648\u062c\u0648\u062f\u06cc"
                f" \u00ab{order['product_name']}\u00bb = {avail} \u0639\u062f\u062f!"
            )
        await safe_edit(event, box("\u2705 \u0633\u0641\u0627\u0631\u0634 \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f", [
            f"\u0633\u0641\u0627\u0631\u0634: {oid}",
            f"\u0645\u0634\u062a\u0631\u06cc: {order['name']} ({order['uid']})",
            f"\u0645\u062d\u0635\u0648\u0644: {order['product_name']}",
            f"\u0645\u0628\u0644\u063a: {order['price']:,} \u062a\u0648\u0645\u0627\u0646",
            f"\u06a9\u0627\u0646\u0641\u06cc\u06af \u0627\u0631\u0633\u0627\u0644 \u0634\u062f \u2705",
            f"\u0645\u0648\u062c\u0648\u062f\u06cc: {avail}",
        ]) + low_msg)

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0633\u0641\u0627\u0631\u0634_\u0631\u062f (.+?) (.+)$"))
    async def store_order_reject_full(event):
        """رد سفارش با اطلاع‌رسانی"""
        record_cmd("\u0633\u0641\u0627\u0631\u0634_\u0631\u062f")
        oid    = event.pattern_match.group(1).strip()
        reason = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute(
                "SELECT * FROM store_orders WHERE order_uid=?", (oid,)
            ).fetchone()
        if not order:
            await safe_edit(event, f"\u274c \u0633\u0641\u0627\u0631\u0634 \u00ab{oid}\u00bb \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        if order["status"] == "rejected":
            await safe_edit(event, "\u26a0\ufe0f \u0633\u0641\u0627\u0631\u0634 \u0642\u0628\u0644\u0627\u064b \u0631\u062f \u0634\u062f\u0647!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "UPDATE store_orders SET status='rejected' WHERE order_uid=?", (oid,)
            )
            conn.commit()
        _log_order_history(oid, "rejected", reason)
        _set_cust_state(order["uid"], "REJECTED", order["product_id"], oid, {"reason": reason})
        NL = "\n"
        try:
            await client.send_message(
                order["uid"],
                f"\u274c **\u0633\u0641\u0627\u0631\u0634 \u0634\u0645\u0627 \u0631\u062f \u0634\u062f.**{NL}{NL}"
                f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644: {order['product_name']}{NL}"
                f"\U0001f194 \u06a9\u062f: `{oid}`{NL}"
                f"\U0001f4cc \u062f\u0644\u06cc\u0644: {reason}{NL}{NL}"
                f"\u0645\u062c\u062f\u062f\u0627\u064b \u0645\u06cc\u062a\u0648\u0627\u0646\u06cc\u062f \u0633\u0641\u0627\u0631\u0634 \u062f\u0647\u06cc\u062f:"
                f" \u0645\u062d\u0635\u0648\u0644\u0627\u062a",
                parse_mode='md'
            )
        except Exception as ex:
            logger.warning(f"reject notify: {ex}")
        await safe_edit(event,
            f"\u2705 \u0633\u0641\u0627\u0631\u0634 {oid} \u0631\u062f \u0634\u062f. \u0645\u0634\u062a\u0631\u06cc \u0645\u0637\u0644\u0639 \u0634\u062f."
        )

    # ════════════════════════════════════════════════════════════
    #  🔧 Report Router & Store Settings
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0645\u0642\u0635\u062f_\u06af\u0632\u0627\u0631\u0634(?: (.+))?$"))
    async def report_destination_cmd(event):
        """تنظیم مقصد گزارش"""
        record_cmd("\u0645\u0642\u0635\u062f_\u06af\u0632\u0627\u0631\u0634")
        arg = (event.pattern_match.group(1) or "").strip()
        if not arg:
            dest = _store_setting("report_dest", "saved")
            await safe_edit(event, box("\U0001f4cd \u0645\u0642\u0635\u062f \u06af\u0632\u0627\u0631\u0634\u0647\u0627", [
                f"\u0645\u0642\u0635\u062f \u0641\u0639\u0644\u06cc: {dest or 'saved'}",
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
                "\u06af\u0632\u06cc\u0646\u0647\u0647\u0627:",
                "\u2022 saved \u2014 \u067e\u06cc\u0627\u0645 \u0630\u062e\u06cc\u0631\u0647\u0634\u062f\u0647",
                "\u2022 [\u0622\u06cc\u062f\u06cc \u0639\u062f\u062f\u06cc] \u2014 \u06af\u0631\u0648\u0647 / \u06a9\u0627\u0646\u0627\u0644 / \u0686\u062a \u062e\u0635\u0648\u0635\u06cc",
                "\u0645\u062b\u0627\u0644: \u0645\u0642\u0635\u062f_\u06af\u0632\u0627\u0631\u0634 -100123456789",
            ]))
            return
        _store_set("report_dest", arg)
        label = "\u067e\u06cc\u0627\u0645 \u0630\u062e\u06cc\u0631\u0647\u0634\u062f\u0647" if arg == "saved" else f"\u0686\u062a {arg}"
        await safe_edit(event, f"\u2705 \u0645\u0642\u0635\u062f \u06af\u0632\u0627\u0631\u0634: {label}")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0686\u062a_\u0627\u062f\u0645\u06cc\u0646(?: (.+))?$"))
    async def admin_chat_cmd(event):
        """تنظیم آیدی ادمین"""
        record_cmd("\u0686\u062a_\u0627\u062f\u0645\u06cc\u0646")
        arg = (event.pattern_match.group(1) or "").strip()
        if not arg:
            cur = _store_setting("admin_id", "\u2014")
            await safe_edit(event,
                f"\U0001f464 \u0622\u06cc\u062f\u06cc \u0627\u062f\u0645\u06cc\u0646: {cur}\n"
                f"\u062a\u0646\u0638\u06cc\u0645: \u0686\u062a_\u0627\u062f\u0645\u06cc\u0646 [\u0622\u06cc\u062f\u06cc]"
            )
            return
        _store_set("admin_id", arg)
        await safe_edit(event, f"\u2705 \u0622\u06cc\u062f\u06cc \u0627\u062f\u0645\u06cc\u0646: {arg}")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0646\u0638\u06cc\u0645\u0627\u062a_\u0641\u0631\u0648\u0634\u06af\u0627\u0647$"))
    async def store_all_settings(event):
        """نمایش تمام تنظیمات فروشگاه"""
        record_cmd("\u062a\u0646\u0638\u06cc\u0645\u0627\u062a_\u0641\u0631\u0648\u0634\u06af\u0627\u0647")
        keys = [
            ("admin_id",           "\u0622\u06cc\u062f\u06cc \u0627\u062f\u0645\u06cc\u0646"),
            ("report_dest",        "\u0645\u0642\u0635\u062f \u06af\u0632\u0627\u0631\u0634"),
            ("card_number",        "\u0634\u0645\u0627\u0631\u0647 \u06a9\u0627\u0631\u062a"),
            ("card_holder",        "\u0635\u0627\u062d\u0628 \u06a9\u0627\u0631\u062a"),
            ("bank_name",          "\u0628\u0627\u0646\u06a9"),
            ("payment_note",       "\u062a\u0648\u0636\u06cc\u062d \u067e\u0631\u062f\u0627\u062e\u062a"),
            ("receipt_trigger",    "\u0646\u0634\u0627\u0646\u0647 \u0641\u06cc\u0634"),
            ("low_stock_threshold","\u0622\u0633\u062a\u0627\u0646\u0647 \u0645\u0648\u062c\u0648\u062f\u06cc \u06a9\u0645"),
            ("auto_reserve",       "\u0631\u0632\u0631\u0648 \u062e\u0648\u062f\u06a9\u0627\u0631"),
            ("reserve_timeout",    "\u062a\u0627\u06cc\u0645\u200c\u0627\u0648\u062a \u0631\u0632\u0631\u0648 (\u062f\u0642\u06cc\u0642\u0647)"),
            ("order_prefix",       "\u067e\u06cc\u0634\u0648\u0646\u062f \u06a9\u062f \u0633\u0641\u0627\u0631\u0634"),
        ]
        lines = [f"{label}: {(_store_setting(k,'—') or '—')[:40]}" for k, label in keys]
        await safe_edit(event, box(
            "\u2699\ufe0f \u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u0641\u0631\u0648\u0634\u06af\u0627\u0647",
            lines,
            "\u062a\u0646\u0638\u06cc\u0645_\u0641\u0631\u0648\u0634\u06af\u0627\u0647 [\u06a9\u0644\u06cc\u062f]|[\u0645\u0642\u062f\u0627\u0631]"
        ))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u06a9\u0627\u0631\u062a_\u067e\u0631\u062f\u0627\u062e\u062a (.+)\|(.+)\|(.+)$"))
    async def set_payment_card(event):
        """تنظیم اطلاعات کارت"""
        record_cmd("\u06a9\u0627\u0631\u062a_\u067e\u0631\u062f\u0627\u062e\u062a")
        number = event.pattern_match.group(1).strip()
        holder = event.pattern_match.group(2).strip()
        bank   = event.pattern_match.group(3).strip()
        _store_set("card_number", number)
        _store_set("card_holder", holder)
        _store_set("bank_name", bank)
        await safe_edit(event, box("\u2705 \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u06a9\u0627\u0631\u062a \u0630\u062e\u06cc\u0631\u0647 \u0634\u062f", [
            f"\u0634\u0645\u0627\u0631\u0647: {number}",
            f"\u0635\u0627\u062d\u0628: {holder}",
            f"\u0628\u0627\u0646\u06a9: {bank}",
        ]))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0645\u062a\u0646_\u067e\u0631\u062f\u0627\u062e\u062a (.+)$"))
    async def set_payment_note(event):
        """تنظیم متن توضیح پرداخت"""
        record_cmd("\u0645\u062a\u0646_\u067e\u0631\u062f\u0627\u062e\u062a")
        note = event.pattern_match.group(1).strip()[:300]
        _store_set("payment_note", note)
        await safe_edit(event, f"\u2705 \u0645\u062a\u0646 \u062a\u0648\u0636\u06cc\u062d \u0630\u062e\u06cc\u0631\u0647 \u0634\u062f.")

    # ════════════════════════════════════════════════════════════
    #  📦 Inventory Engine
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0645\u0648\u062c\u0648\u062f\u06cc_\u06a9\u0644$"))
    async def store_inventory_full(event):
        """نمایش کامل موجودی"""
        record_cmd("\u0645\u0648\u062c\u0648\u062f\u06cc_\u06a9\u0644")
        with _db_lock:
            conn = get_conn()
            products = conn.execute(
                "SELECT p.*, "
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=0) AS avail, "
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=1) AS sold_cnt "
                "FROM store_products p ORDER BY p.active DESC, p.id"
            ).fetchall()
        if not products:
            await safe_edit(event, "\U0001f4ed \u0647\u06cc\u0686 \u0645\u062d\u0635\u0648\u0644\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647!")
            return
        low_th = int(_store_setting("low_stock_threshold", "3"))
        lines = []
        for p in products:
            avail = p["avail"] or 0
            sold  = p["sold_cnt"] or 0
            act   = "\u2705" if p["active"] else "\u274c"
            flag  = "\u26a0\ufe0f" if 0 < avail <= low_th else ("\U0001f534" if avail == 0 else "\U0001f7e2")
            lines.append(
                f"{act}{flag} {p['id']}. {p['name'][:20]} | "
                f"\u0645\u0648\u062c\u0648\u062f: {avail} | \u0641\u0631\u0648\u0634: {sold} | {p['price']:,}"
            )
        total = sum(p["avail"] or 0 for p in products)
        await safe_edit(event, box(
            f"\U0001f4e6 \u0645\u0648\u062c\u0648\u062f\u06cc ({len(products)} \u0645\u062d\u0635\u0648\u0644)",
            lines,
            f"\u062c\u0645\u0639 \u06a9\u0627\u0646\u0641\u06cc\u06af: {total}"
        ))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc(?: (\d+))?$"))
    async def low_stock_alert(event):
        """هشدار موجودی کم"""
        record_cmd("\u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc")
        grp = event.pattern_match.group(1)
        threshold = int(grp) if grp else int(_store_setting("low_stock_threshold", "3"))
        _store_set("low_stock_threshold", str(threshold))
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT p.id, p.name, "
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=0) AS avail "
                "FROM store_products p WHERE p.active=1 "
                "HAVING avail <= ? ORDER BY avail",
                (threshold,)
            ).fetchall()
        if not rows:
            await safe_edit(event,
                f"\u2705 \u0647\u0645\u0647 \u0645\u062d\u0635\u0648\u0644\u0627\u062a"
                f" \u0645\u0648\u062c\u0648\u062f\u06cc \u0628\u06cc\u0634\u062a\u0631 \u0627\u0632 {threshold} \u062f\u0627\u0631\u0646\u062f!"
            )
            return
        lines = [
            f"{'🔴' if r['avail']==0 else '⚠️'} {r['id']}. {r['name'][:25]}: {r['avail']}"
            for r in rows
        ]
        await safe_edit(event, box(
            f"\u26a0\ufe0f \u0645\u0648\u062c\u0648\u062f\u06cc \u06a9\u0645 (\u2264{threshold})",
            lines,
            "\u06a9\u0627\u0646\u0641\u06cc\u06af_\u0627\u0636\u0627\u0641\u0647 [id]|[\u0645\u062d\u062a\u0648\u0627]"
        ))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u06a9\u0627\u0646\u0641\u06cc\u06af_\u062a\u06a9\u0631\u0627\u0631\u06cc_\u0641\u0631\u0648\u0634$"))
    async def store_dup_check(event):
        """تشخیص کانفیگ تکراری"""
        record_cmd("\u06a9\u0627\u0646\u0641\u06cc\u06af_\u062a\u06a9\u0631\u0627\u0631\u06cc_\u0641\u0631\u0648\u0634")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT content, COUNT(*) cnt FROM store_configs GROUP BY content HAVING cnt>1"
            ).fetchall()
        if not rows:
            await safe_edit(event, "\u2705 \u0647\u06cc\u0686 \u06a9\u0627\u0646\u0641\u06cc\u06af \u062a\u06a9\u0631\u0627\u0631\u06cc \u0646\u06cc\u0633\u062a!")
            return
        lines = [f"\u26a0\ufe0f {r['cnt']} \u062a\u06a9\u0631\u0627\u0631: {r['content'][:35]}..." for r in rows]
        await safe_edit(event, box(f"\U0001f50d \u062a\u06a9\u0631\u0627\u0631\u06cc ({len(rows)})", lines))

    # ════════════════════════════════════════════════════════════
    #  📋 Customer State Management
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc(?: (.+))?$"))
    async def customer_state_check(event):
        """بررسی وضعیت مشتری"""
        record_cmd("\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc")
        import json as _json
        arg = (event.pattern_match.group(1) or "").strip()
        u = await resolve_user(client, event, arg if arg else None)
        if not u:
            await safe_edit(event, "\u274c \u06a9\u0627\u0631\u0628\u0631 \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        cst = _cust_state(u.id)
        data = _json.loads(cst.get("data", "{}") or "{}")
        STATE_FA = {
            "idle":              "\U0001f535 \u0628\u062f\u0648\u0646 \u0633\u0641\u0627\u0631\u0634 \u0641\u0639\u0627\u0644",
            "BROWSING_PRODUCTS": "\U0001f440 \u0645\u0634\u0627\u0647\u062f\u0647 \u0645\u062d\u0635\u0648\u0644\u0627\u062a",
            "WAITING_PAYMENT":   "\U0001f4b3 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u067e\u0631\u062f\u0627\u062e\u062a",
            "WAITING_RECEIPT":   "\U0001f4ce \u0631\u0633\u06cc\u062f \u2014 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0628\u0631\u0631\u0633\u06cc",
            "APPROVED":          "\u2705 \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f\u0647",
            "REJECTED":          "\u274c \u0631\u062f \u0634\u062f\u0647",
            "DELIVERED":         "\U0001f4e6 \u062a\u062d\u0648\u06cc\u0644 \u0634\u062f\u0647",
            "CANCELLED":         "\U0001f6ab \u0644\u063a\u0648 \u0634\u062f\u0647",
        }
        name = getattr(u, "first_name", str(u.id))
        lines = [
            f"\U0001f464 {name} ({u.id})",
            f"\U0001f4cc {STATE_FA.get(cst['state'], cst['state'])}",
            f"\U0001f194 {cst['order_uid'] or '\u2014'}",
            f"\U0001f4e6 {data.get('product_name','\u2014')}",
            f"\u23f0 {(cst['updated'] or '')[:16]}",
        ]
        await safe_edit(event, box("\U0001f4cb \u0648\u0636\u0639\u06cc\u062a \u0645\u0634\u062a\u0631\u06cc", lines))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0631\u06cc\u0633\u062a_\u0645\u0634\u062a\u0631\u06cc (.+)$"))
    async def reset_customer_state(event):
        """ریست وضعیت مشتری"""
        record_cmd("\u0631\u06cc\u0633\u062a_\u0645\u0634\u062a\u0631\u06cc")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "\u274c \u06a9\u0627\u0631\u0628\u0631 \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        _reset_cust_state(u.id)
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event,
            f"\u2705 \u0648\u0636\u0639\u06cc\u062a {name} ({u.id}) \u0631\u06cc\u0633\u062a \u0634\u062f."
        )

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0644\u06cc\u0633\u062a_\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646$"))
    async def list_active_states(event):
        """لیست مشتریان با سفارش فعال"""
        record_cmd("\u0644\u06cc\u0633\u062a_\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT cs.*, c.name, c.username FROM customer_states cs "
                "LEFT JOIN contacts c ON cs.uid=c.uid "
                "WHERE cs.state NOT IN ('idle') ORDER BY cs.updated DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "\U0001f4ed \u0647\u06cc\u0686 \u0633\u0641\u0627\u0631\u0634 \u0641\u0639\u0627\u0644\u06cc \u0646\u06cc\u0633\u062a!")
            return
        lines = [
            f"\u2022 {r['name'] or r['uid']} | {r['state']} | {(r['order_uid'] or '')[:10]} | {(r['updated'] or '')[:10]}"
            for r in rows
        ]
        await safe_edit(event, box(
            f"\U0001f4cb \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u0641\u0639\u0627\u0644 ({len(rows)})",
            lines
        ))

    # ════════════════════════════════════════════════════════════
    #  📤 Bulk Messaging
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u067e\u062e\u0634_\u0645\u062d\u0635\u0648\u0644 (\d+) (.+)$"))
    async def broadcast_to_buyers(event):
        """ارسال پیام به خریداران یک محصول"""
        record_cmd("\u067e\u062e\u0634_\u0645\u062d\u0635\u0648\u0644")
        pid = int(event.pattern_match.group(1))
        msg = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            prod = conn.execute("SELECT name FROM store_products WHERE id=?", (pid,)).fetchone()
            uids = [r["uid"] for r in conn.execute(
                "SELECT DISTINCT uid FROM store_orders WHERE product_id=? AND status='approved'",
                (pid,)
            ).fetchall()]
        pname = prod["name"] if prod else str(pid)
        if not uids:
            await safe_edit(event, f"\u274c \u062e\u0631\u06cc\u062f\u0627\u0631\u06cc \u0628\u0631\u0627\u06cc \u00ab{pname}\u00bb \u0646\u06cc\u0633\u062a!")
            return
        await safe_edit(event, f"\U0001f4e4 \u0627\u0631\u0633\u0627\u0644 \u0628\u0647 {len(uids)} \u0646\u0641\u0631...")
        sent = 0
        for uid in uids:
            try:
                await client.send_message(uid, msg)
                sent += 1
                await asyncio.sleep(1.2)
            except Exception:
                pass
        await safe_edit(event,
            f"\u2705 \u067e\u062e\u0634 \u00ab{pname}\u00bb: {sent}/{len(uids)} \u0627\u0631\u0633\u0627\u0644 \u0634\u062f."
        )

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u067e\u06cc\u0627\u0645_\u0645\u0634\u062a\u0631\u06cc (.+?) (.+)$"))
    async def message_to_customer(event):
        """ارسال پیام مستقیم به مشتری"""
        record_cmd("\u067e\u06cc\u0627\u0645_\u0645\u0634\u062a\u0631\u06cc")
        arg = event.pattern_match.group(1).strip()
        msg = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "\u274c \u06a9\u0627\u0631\u0628\u0631 \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        try:
            await client.send_message(u.id, msg)
            name = getattr(u, "first_name", str(u.id))
            await safe_edit(event, f"\u2705 \u067e\u06cc\u0627\u0645 \u0628\u0647 {name} ({u.id}) \u0627\u0631\u0633\u0627\u0644 \u0634\u062f.")
        except Exception as ex:
            await safe_edit(event, f"\u274c \u062e\u0637\u0627: {ex}")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u067e\u062e\u0634_\u0647\u0645\u0647 (.+)$"))
    async def broadcast_all(event):
        """ارسال به همه مشتریان"""
        record_cmd("\u067e\u062e\u0634_\u0647\u0645\u0647")
        msg = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            uids = [r["uid"] for r in conn.execute(
                "SELECT uid FROM crm_customers WHERE blacklisted=0"
            ).fetchall()]
        if not uids:
            await safe_edit(event, "\u274c \u0645\u0634\u062a\u0631\u06cc CRM\u0627\u06cc \u0646\u06cc\u0633\u062a!")
            return
        await safe_edit(event, f"\U0001f4e4 \u0627\u0631\u0633\u0627\u0644 \u0628\u0647 {len(uids)} \u0645\u0634\u062a\u0631\u06cc...")
        sent = 0
        for uid in uids:
            try:
                await client.send_message(uid, msg)
                sent += 1
                await asyncio.sleep(1.2)
            except Exception:
                pass
        await safe_edit(event, f"\u2705 \u067e\u062e\u0634 \u0647\u0645\u0647: {sent}/{len(uids)} \u0627\u0631\u0633\u0627\u0644 \u0634\u062f.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u067e\u062e\u0634_vip (.+)$"))
    async def broadcast_vip(event):
        """ارسال به مشتریان VIP"""
        record_cmd("\u067e\u062e\u0634_vip")
        msg = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            uids = [r["uid"] for r in conn.execute(
                "SELECT uid FROM crm_customers WHERE vip_level>0 AND blacklisted=0"
            ).fetchall()]
        if not uids:
            await safe_edit(event, "\u274c \u0645\u0634\u062a\u0631\u06cc VIP\u0627\u06cc \u0646\u06cc\u0633\u062a!")
            return
        await safe_edit(event, f"\U0001f4e4 \u0627\u0631\u0633\u0627\u0644 \u0628\u0647 {len(uids)} VIP...")
        sent = 0
        for uid in uids:
            try:
                await client.send_message(uid, msg)
                sent += 1
                await asyncio.sleep(1.2)
            except Exception:
                pass
        await safe_edit(event, f"\u2705 \u067e\u062e\u0634 VIP: {sent}/{len(uids)} \u0627\u0631\u0633\u0627\u0644 \u0634\u062f.")

    # ════════════════════════════════════════════════════════════
    #  📊 Order History & Analytics
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0627\u0631\u06cc\u062e\u0686\u0647_\u0639\u0645\u0644\u06cc\u0627\u062a (.+)$"))
    async def order_op_history(event):
        """تاریخچه عملیات سفارش"""
        record_cmd("\u062a\u0627\u0631\u06cc\u062e\u0686\u0647_\u0639\u0645\u0644\u06cc\u0627\u062a")
        oid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM store_order_history WHERE order_uid=? ORDER BY id",
                (oid,)
            ).fetchall()
            order = conn.execute(
                "SELECT * FROM store_orders WHERE order_uid=?", (oid,)
            ).fetchone()
        if not rows and not order:
            await safe_edit(event, f"\u274c \u0633\u0641\u0627\u0631\u0634 \u00ab{oid}\u00bb \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")
            return
        lines = []
        if order:
            lines += [
                f"\U0001f4e6 {order['product_name'][:25]} | {order['status']}",
                f"\U0001f464 {order['name'][:20]} | {order['ts'][:10]}",
                "\u2500\u2500 \u062a\u0627\u0631\u06cc\u062e\u0686\u0647 \u2500\u2500"
            ]
        for r in rows:
            lines.append(
                f"\u2022 {r['ts'][:13]} | {r['action']}: {(r['note'] or '')[:30]}"
            )
        await safe_edit(event, box(f"\U0001f4cb {oid}", lines))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0633\u0641\u0627\u0631\u0634\u0627\u062a_\u0627\u0645\u0631\u0648\u0632$"))
    async def orders_today(event):
        """سفارشات امروز"""
        record_cmd("\u0633\u0641\u0627\u0631\u0634\u0627\u062a_\u0627\u0645\u0631\u0648\u0632")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM store_orders WHERE ts LIKE ? ORDER BY id DESC",
                (f"{today}%",)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"\U0001f4ed \u0633\u0641\u0627\u0631\u0634\u06cc \u0628\u0631\u0627\u06cc \u0627\u0645\u0631\u0648\u0632 ({today}) \u0646\u06cc\u0633\u062a!")
            return
        STATUS_E = {
            "waiting_payment": "\U0001f4b3",
            "pending": "\u23f3",
            "approved": "\u2705",
            "rejected": "\u274c",
            "delivered": "\U0001f4e6",
            "cancelled": "\U0001f6ab",
        }
        total = sum(r["price"] for r in rows if r["status"] == "approved")
        lines = [f"\u0627\u0645\u0631\u0648\u0632: {today} | \u062f\u0631\u0622\u0645\u062f: {total:,}", "\u2500\u2500"]
        for r in rows:
            e = STATUS_E.get(r["status"], "?")
            lines.append(
                f"{e} {r['order_uid'][-8:]} | {r['name'][:12]} | {r['product_name'][:15]}"
            )
        await safe_edit(event, box(
            f"\U0001f4c5 \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u0627\u0645\u0631\u0648\u0632 ({len(rows)})",
            lines
        ))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644(?: (\d+))?$"))
    async def product_sales_stats(event):
        """آمار فروش محصولات"""
        record_cmd("\u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644")
        grp = event.pattern_match.group(1)
        with _db_lock:
            conn = get_conn()
            if grp:
                rows = conn.execute(
                    "SELECT product_name, COUNT(*) cnt, SUM(price) rev FROM store_orders "
                    "WHERE product_id=? AND status='approved' GROUP BY product_id",
                    (int(grp),)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT product_name, COUNT(*) cnt, SUM(price) rev FROM store_orders "
                    "WHERE status='approved' GROUP BY product_id ORDER BY cnt DESC LIMIT 10"
                ).fetchall()
        if not rows:
            await safe_edit(event, "\U0001f4ed \u062f\u0627\u062f\u0647 \u0641\u0631\u0648\u0634\u06cc \u0646\u06cc\u0633\u062a!")
            return
        total = sum(r["rev"] or 0 for r in rows)
        lines = [
            f"\u2022 {r['product_name'][:25]}: {r['cnt']} \u0641\u0631\u0648\u0634 | {(r['rev'] or 0):,}"
            for r in rows
        ]
        await safe_edit(event, box("\U0001f4ca \u0622\u0645\u0627\u0631 \u0641\u0631\u0648\u0634", lines,
                                    f"\u062c\u0645\u0639: {total:,} \u062a\u0648\u0645\u0627\u0646"))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062f\u0631\u0622\u0645\u062f_\u0645\u0627\u0647$"))
    async def monthly_revenue(event):
        """درآمد ماه جاری"""
        record_cmd("\u062f\u0631\u0622\u0645\u062f_\u0645\u0627\u0647")
        month_prefix = jalali()[:7]
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT product_name, COUNT(*) cnt, SUM(price) rev FROM store_orders "
                "WHERE status='approved' AND ts LIKE ? "
                "GROUP BY product_name ORDER BY rev DESC",
                (f"{month_prefix}%",)
            ).fetchall()
            total_orders = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE ts LIKE ?",
                (f"{month_prefix}%",)
            ).fetchone()[0]
        if not rows:
            await safe_edit(event, f"\U0001f4ed \u0647\u06cc\u0686 \u0641\u0631\u0648\u0634\u06cc \u062f\u0631 {month_prefix} \u0646\u06cc\u0633\u062a!")
            return
        total = sum(r["rev"] or 0 for r in rows)
        lines = [f"\u0645\u0627\u0647: {month_prefix} | \u062c\u0645\u0639 \u0633\u0641\u0627\u0631\u0634: {total_orders}", "\u2500\u2500"]
        for r in rows:
            lines.append(f"\u2022 {r['product_name'][:25]}: {r['cnt']} | {(r['rev'] or 0):,}")
        await safe_edit(event, box("\U0001f4b0 \u062f\u0631\u0622\u0645\u062f \u0645\u0627\u0647", lines,
                                    f"\u062c\u0645\u0639: {total:,} \u062a\u0648\u0645\u0627\u0646"))

    # ════════════════════════════════════════════════════════════
    #  🏪 Store Dashboard
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0641\u0631\u0648\u0634\u06af\u0627\u0647$"))
    async def store_dashboard(event):
        """داشبورد اصلی فروشگاه"""
        record_cmd("\u0641\u0631\u0648\u0634\u06af\u0627\u0647")
        with _db_lock:
            conn = get_conn()
            prods   = conn.execute("SELECT COUNT(*) FROM store_products WHERE active=1").fetchone()[0]
            avail   = conn.execute("SELECT COUNT(*) FROM store_configs WHERE sold=0").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='pending'").fetchone()[0]
            approved= conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='approved'").fetchone()[0]
            revenue = conn.execute(
                "SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved'"
            ).fetchone()[0]
            custs   = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
            tickets = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'").fetchone()[0]
        dest = _store_setting("report_dest", "saved")
        card = _store_setting("card_number", "\u2014")
        await safe_edit(event, box("\U0001f3ea \u062f\u0627\u0634\u0628\u0648\u0631\u062f \u0641\u0631\u0648\u0634\u06af\u0627\u0647", [
            f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0641\u0639\u0627\u0644: {prods}",
            f"\U0001f511 \u06a9\u0627\u0646\u0641\u06cc\u06af \u0645\u0648\u062c\u0648\u062f: {avail}",
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"\u23f3 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0628\u0631\u0631\u0633\u06cc: {pending}",
            f"\u2705 \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f\u0647: {approved}",
            f"\U0001f4b0 \u062f\u0631\u0622\u0645\u062f \u06a9\u0644: {revenue:,} \u062a\u0648\u0645\u0627\u0646",
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"\U0001f454 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646: {custs}",
            f"\U0001f3ab \u062a\u06cc\u06a9\u062a \u0628\u0627\u0632: {tickets}",
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            f"\U0001f4b3 {card[:12] if card != '\u2014' else '\u2014'}...",
            f"\U0001f4cd \u0645\u0642\u0635\u062f: {dest or 'saved'}",
            "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
            "\u0631\u0627\u0647\u0646\u0645\u0627_\u0641\u0631\u0648\u0634\u06af\u0627\u0647_\u06a9\u0627\u0645\u0644",
        ], WATERMARK))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u0631\u0627\u0647\u0646\u0645\u0627_\u0641\u0631\u0648\u0634\u06af\u0627\u0647_\u06a9\u0627\u0645\u0644$"))
    async def store_help_full(event):
        """راهنمای کامل فروشگاه"""
        record_cmd("\u0631\u0627\u0647\u0646\u0645\u0627_\u0641\u0631\u0648\u0634\u06af\u0627\u0647_\u06a9\u0627\u0645\u0644")
        await safe_edit(event, box("\U0001f3ea \u0631\u0627\u0647\u0646\u0645\u0627\u06cc \u06a9\u0627\u0645\u0644 \u0641\u0631\u0648\u0634\u06af\u0627\u0647", [
            "\u2500\u2500 \u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u2500\u2500",
            "\u062a\u0646\u0638\u06cc\u0645\u0627\u062a_\u0641\u0631\u0648\u0634\u06af\u0627\u0647",
            "\u062a\u0646\u0638\u06cc\u0645_\u0641\u0631\u0648\u0634\u06af\u0627\u0647 [\u06a9\u0644\u06cc\u062f]|[\u0645\u0642\u062f\u0627\u0631]",
            "\u06a9\u0627\u0631\u062a_\u067e\u0631\u062f\u0627\u062e\u062a [\u0634\u0645\u0627\u0631\u0647]|[\u0635\u0627\u062d\u0628]|[\u0628\u0627\u0646\u06a9]",
            "\u0645\u062a\u0646_\u067e\u0631\u062f\u0627\u062e\u062a [\u062a\u0648\u0636\u06cc\u062d]",
            "\u0645\u0642\u0635\u062f_\u06af\u0632\u0627\u0631\u0634 [saved | \u0622\u06cc\u062f\u06cc]",
            "\u0686\u062a_\u0627\u062f\u0645\u06cc\u0646 [\u0622\u06cc\u062f\u06cc]",
            "\u2500\u2500 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u2500\u2500",
            "\u0645\u062d\u0635\u0648\u0644_\u062b\u0628\u062a [\u0646\u0627\u0645]|[\u0642\u06cc\u0645\u062a]|[\u062a\u0648\u0636\u06cc\u062d]",
            "\u0645\u062d\u0635\u0648\u0644_\u0644\u06cc\u0633\u062a",
            "\u0645\u062d\u0635\u0648\u0644_\u0648\u06cc\u0631\u0627\u06cc\u0634 [id] [\u0641\u06cc\u0644\u062f]=[\u0645\u0642\u062f\u0627\u0631]",
            "\u0645\u062d\u0635\u0648\u0644_\u062d\u0630\u0641 [id]",
            "\u06a9\u0627\u0646\u0641\u06cc\u06af_\u0627\u0636\u0627\u0641\u0647 [product_id]|[\u0645\u062d\u062a\u0648\u0627]",
            "\u0645\u0648\u062c\u0648\u062f\u06cc_\u0645\u062d\u0635\u0648\u0644 [id]",
            "\u0645\u0648\u062c\u0648\u062f\u06cc_\u06a9\u0644",
            "\u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc [\u0622\u0633\u062a\u0627\u0646\u0647]",
            "\u2500\u2500 \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u2500\u2500",
            "\u0633\u0641\u0627\u0631\u0634_\u0644\u06cc\u0633\u062a [\u0648\u0636\u0639\u06cc\u062a]",
            "\u0633\u0641\u0627\u0631\u0634_\u062a\u0627\u06cc\u06cc\u062f [order_uid]",
            "\u0633\u0641\u0627\u0631\u0634_\u0631\u062f [order_uid] [\u062f\u0644\u06cc\u0644]",
            "\u0633\u0641\u0627\u0631\u0634\u0627\u062a_\u0627\u0645\u0631\u0648\u0632",
            "\u062a\u0627\u0631\u06cc\u062e\u0686\u0647_\u0639\u0645\u0644\u06cc\u0627\u062a [order_uid]",
            "\u2500\u2500 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646 \u2500\u2500",
            "\u0645\u0634\u062a\u0631\u06cc_\u067e\u0631\u0648\u0641\u0627\u06cc\u0644 [@]",
            "\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc [@]",
            "\u0631\u06cc\u0633\u062a_\u0645\u0634\u062a\u0631\u06cc [@]",
            "\u0644\u06cc\u0633\u062a_\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646",
            "\u2500\u2500 \u0627\u0631\u0633\u0627\u0644 \u2500\u2500",
            "\u067e\u06cc\u0627\u0645_\u0645\u0634\u062a\u0631\u06cc [@] [\u067e\u06cc\u0627\u0645]",
            "\u067e\u062e\u0634_\u0647\u0645\u0647 [\u067e\u06cc\u0627\u0645]",
            "\u067e\u062e\u0634_vip [\u067e\u06cc\u0627\u0645]",
            "\u067e\u062e\u0634_\u0645\u062d\u0635\u0648\u0644 [id] [\u067e\u06cc\u0627\u0645]",
            "\u2500\u2500 \u0622\u0645\u0627\u0631 \u2500\u2500",
            "\u0641\u0631\u0648\u0634\u06af\u0627\u0647",
            "\u0622\u0645\u0627\u0631_\u0641\u0631\u0648\u0634\u06af\u0627\u0647",
            "\u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644 [id]",
            "\u062f\u0631\u0622\u0645\u062f_\u0645\u0627\u0647",
        ], WATERMARK))



    # ════════════════════════════════════════════════════════════
    #  🔥 DYNAMIC TRIGGER SYSTEM + INLINE ADMIN PANEL  (V8)
    # ════════════════════════════════════════════════════════════

    # ── Default triggers seeded on first run ────────────────────
    def _seed_default_triggers():
        """بارگذاری تریگرهای پیش‌فرض"""
        defaults = [
            ("\u062e\u0631\u06cc\u062f",     0, "browse"),
            ("\u06a9\u0627\u0646\u0641\u06cc\u06af", 0, "browse"),
            ("\u0627\u0634\u062a\u0631\u0627\u06a9", 0, "browse"),
            ("\u0633\u0631\u0648\u0631",     0, "browse"),
            ("\u067e\u0644\u0646",           0, "browse"),
            ("\u0645\u062d\u0635\u0648\u0644\u0627\u062a", 0, "browse"),
            ("\u0644\u06cc\u0633\u062a",     0, "browse"),
            ("shop",                          0, "browse"),
            ("store",                         0, "browse"),
        ]
        with _db_lock:
            conn = get_conn()
            for word, pid, action in defaults:
                conn.execute(
                    "INSERT OR IGNORE INTO store_triggers(word,product_id,action,ts)"
                    " VALUES(?,?,?,?)",
                    (word, pid, action, now_str())
                )
            conn.commit()

    # Seed on startup (called inside register_all scope)
    try:
        _seed_default_triggers()
    except Exception:
        pass

    def _get_triggers() -> list:
        """دریافت همه تریگرهای فعال"""
        with _db_lock:
            conn = get_conn()
            return conn.execute(
                "SELECT * FROM store_triggers WHERE active=1 ORDER BY id"
            ).fetchall()

    def _match_trigger(text: str):
        """بررسی آیا متن با تریگری match می‌کند"""
        text = text.strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute(
                "SELECT * FROM store_triggers WHERE active=1 AND LOWER(word)=LOWER(?)",
                (text,)
            ).fetchone()
        return row

    def _match_product_name(text: str):
        """بررسی آیا متن اسم یک محصول است"""
        text = text.strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute(
                "SELECT * FROM store_products"
                " WHERE active=1 AND LOWER(name)=LOWER(?)",
                (text,)
            ).fetchone()
        return row

    # ── Trigger Management Commands ──────────────────────────────

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0631\u06cc\u06af\u0631_\u0627\u0636\u0627\u0641\u0647 (.+?)(?:\|(\d+))?$"))
    async def trigger_add(event):
        """تریگر_اضافه [کلمه] یا تریگر_اضافه [کلمه]|[product_id]"""
        record_cmd("\u062a\u0631\u06cc\u06af\u0631_\u0627\u0636\u0627\u0641\u0647")
        word = event.pattern_match.group(1).strip()
        pid  = int(event.pattern_match.group(2) or 0)
        action = "product" if pid else "browse"
        with _db_lock:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT INTO store_triggers(word,product_id,action,active,ts)"
                    " VALUES(?,?,?,1,?)",
                    (word, pid, action, now_str())
                )
                conn.commit()
            except Exception:
                conn.execute(
                    "UPDATE store_triggers SET product_id=?,action=?,active=1 WHERE LOWER(word)=LOWER(?)",
                    (pid, action, word)
                )
                conn.commit()
        label = f"\u0645\u062d\u0635\u0648\u0644 {pid}" if pid else "\u0628\u0627\u0632 \u06a9\u0631\u062f\u0646 \u0641\u0631\u0648\u0634\u06af\u0627\u0647"
        await safe_edit(event,
            f"\u2705 \u062a\u0631\u06cc\u06af\u0631 \u00ab{word}\u00bb \u0627\u0636\u0627\u0641\u0647 \u0634\u062f \u2192 {label}"
        )

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0631\u06cc\u06af\u0631_\u062d\u0630\u0641 (.+)$"))
    async def trigger_remove(event):
        """تریگر_حذف [کلمه]"""
        record_cmd("\u062a\u0631\u06cc\u06af\u0631_\u062d\u0630\u0641")
        word = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute(
                "DELETE FROM store_triggers WHERE LOWER(word)=LOWER(?)", (word,)
            )
            conn.commit()
        if c.rowcount:
            await safe_edit(event, f"\u2705 \u062a\u0631\u06cc\u06af\u0631 \u00ab{word}\u00bb \u062d\u0630\u0641 \u0634\u062f.")
        else:
            await safe_edit(event, f"\u274c \u062a\u0631\u06cc\u06af\u0631 \u00ab{word}\u00bb \u067e\u06cc\u062f\u0627 \u0646\u0634\u062f!")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0631\u06cc\u06af\u0631_\u0644\u06cc\u0633\u062a$"))
    async def trigger_list(event):
        """لیست همه تریگرها"""
        record_cmd("\u062a\u0631\u06cc\u06af\u0631_\u0644\u06cc\u0633\u062a")
        rows = _get_triggers()
        if not rows:
            await safe_edit(event, "\U0001f4ed \u062a\u0631\u06cc\u06af\u0631\u06cc \u062a\u0639\u0631\u06cc\u0641 \u0646\u0634\u062f\u0647!")
            return
        lines = []
        for r in rows:
            if r["product_id"]:
                lines.append(f"\u2022 \u00ab{r['word']}\u00bb \u2192 \u0645\u062d\u0635\u0648\u0644 {r['product_id']}")
            else:
                lines.append(f"\u2022 \u00ab{r['word']}\u00bb \u2192 \u0641\u0631\u0648\u0634\u06af\u0627\u0647")
        await safe_edit(event, box(
            f"\U0001f3f7\ufe0f \u062a\u0631\u06cc\u06af\u0631\u0647\u0627 ({len(rows)})", lines,
            "\u062a\u0631\u06cc\u06af\u0631_\u0627\u0636\u0627\u0641\u0647 [\u06a9\u0644\u0645\u0647] | \u062a\u0631\u06cc\u06af\u0631_\u062d\u0630\u0641 [\u06a9\u0644\u0645\u0647]"
        ))

    # ════════════════════════════════════════════════════════════
    #  🤖 SMART INCOMING MESSAGE ENGINE
    #  این handler باید آخرین incoming=True handler باشد
    # ════════════════════════════════════════════════════════════

    @client.on(events.NewMessage(incoming=True))
    async def smart_message_engine(event):
        """
        موتور هوشمند پیام‌های ورودی:
        1. بررسی تریگرها
        2. بررسی اسم محصول
        3. بررسی حالت مشتری (state machine)
        4. رسید (عکس)
        """
        try:
            sender = await event.get_sender()
            if not sender:
                return
            me = await client.get_me()
            if sender.id == me.id:
                return
            if event.is_group or event.is_channel:
                return

            import json as _json

            text      = (event.text or "").strip()
            has_photo = bool(event.photo) or bool(event.media)
            cst       = _cust_state(sender.id)

            # ── 1) اگر state فعال دارد و عکس فرستاده: رسید ─────
            if has_photo and cst["state"] == "WAITING_PAYMENT":
                order_uid = cst["order_uid"]
                if not order_uid:
                    return
                receipt_path = ""
                try:
                    dl_path = os.path.join(DL_DIR, f"receipt_{order_uid}.jpg")
                    await client.download_media(event.media, file=dl_path)
                    receipt_path = dl_path
                except Exception as dl_ex:
                    logger.debug(f"dl: {dl_ex}")
                with _db_lock:
                    conn = get_conn()
                    conn.execute(
                        "UPDATE store_orders SET status='pending',receipt_file=?"
                        " WHERE order_uid=?", (receipt_path, order_uid)
                    )
                    conn.commit()
                _log_order_history(order_uid, "receipt_received", receipt_path)
                cst_data = _json.loads(cst.get("data", "{}") or "{}")
                _set_cust_state(sender.id, "WAITING_RECEIPT",
                                cst["product_id"], order_uid, cst_data)
                await event.reply(
                    f"\u2705 \u0631\u0633\u06cc\u062f \u062f\u0631\u06cc\u0627\u0641\u062a \u0634\u062f!\n"
                    f"\U0001f194 \u06a9\u062f \u067e\u06cc\u06af\u06cc\u0631\u06cc: "
                    f"<code>{order_uid}</code>\n"
                    f"\u23f3 \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc...",
                    parse_mode='html'
                )
                await _send_receipt_report(
                    sender, order_uid,
                    cst_data.get("product_name", ""),
                    cst_data.get("price", 0),
                    receipt_path, me
                )
                return

            # ── 2) اگر در انتظار بررسی است ──────────────────────
            if cst["state"] == "WAITING_RECEIPT":
                if has_photo:
                    order_uid = cst["order_uid"]
                    await event.reply(
                        f"\u23f3 \u0633\u0641\u0627\u0631\u0634 <code>{order_uid}</code>"
                        f" \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0627\u0633\u062a.\n"
                        f"\u0644\u0637\u0641\u0627\u064b \u0635\u0628\u0631 \u06a9\u0646\u06cc\u062f.",
                        parse_mode='html'
                    )
                return

            # ── 3) اگر پیام متنی است ─────────────────────────────
            if not text:
                return

            # ── 3a) تریگر مستقیم ─────────────────────────────────
            trig = _match_trigger(text)
            if trig:
                if trig["product_id"] and trig["action"] == "product":
                    # باز کردن مستقیم یک محصول
                    with _db_lock:
                        conn = get_conn()
                        prod = conn.execute(
                            "SELECT * FROM store_products WHERE id=? AND active=1",
                            (trig["product_id"],)
                        ).fetchone()
                    if prod:
                        avail = 0
                        with _db_lock:
                            conn = get_conn()
                            avail = conn.execute(
                                "SELECT COUNT(*) FROM store_configs"
                                " WHERE product_id=? AND sold=0",
                                (prod["id"],)
                            ).fetchone()[0]
                        NL = "\n"
                        SEP = "\u2501" * 17
                        stock_label = "\u2705 \u0645\u0648\u062c\u0648\u062f" if avail else "\u274c \u0646\u0627\u0645\u0648\u062c\u0648\u062f"
                        await event.reply(
                            f"\U0001f4e6 {prod['name']}{NL}{SEP}{NL}"
                            f"\U0001f4b0 \u0642\u06cc\u0645\u062a: {prod['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}"
                            f"\U0001f4dd {prod['description'] or '\u2014'}{NL}"
                            f"\U0001f4e6 {stock_label} ({avail} \u0639\u062f\u062f){NL}{SEP}{NL}"
                            f"\u0628\u0631\u0627\u06cc \u062e\u0631\u06cc\u062f \u0628\u0646\u0648\u06cc\u0633:{NL}"
                            f"\u062e\u0631\u06cc\u062f {prod['id']}"
                        )
                        _set_cust_state(sender.id, "BROWSING_PRODUCTS")
                    else:
                        await event.reply(_build_products_text())
                else:
                    # browse: نمایش همه محصولات
                    _set_cust_state(sender.id, "BROWSING_PRODUCTS")
                    await event.reply(_build_products_text())
                return

            # ── 3b) اسم محصول مستقیم ────────────────────────────
            prod_match = _match_product_name(text)
            if prod_match:
                with _db_lock:
                    conn = get_conn()
                    avail = conn.execute(
                        "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0",
                        (prod_match["id"],)
                    ).fetchone()[0]
                NL = "\n"
                SEP = "\u2501" * 17
                stock_label = "\u2705 \u0645\u0648\u062c\u0648\u062f" if avail else "\u274c \u0646\u0627\u0645\u0648\u062c\u0648\u062f"
                await event.reply(
                    f"\U0001f4e6 {prod_match['name']}{NL}{SEP}{NL}"
                    f"\U0001f4b0 \u0642\u06cc\u0645\u062a: {prod_match['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}"
                    f"\U0001f4dd {prod_match['description'] or '\u2014'}{NL}"
                    f"\U0001f4e6 {stock_label} ({avail} \u0639\u062f\u062f){NL}{SEP}{NL}"
                    f"\u0628\u0631\u0627\u06cc \u062e\u0631\u06cc\u062f \u0628\u0646\u0648\u06cc\u0633:{NL}"
                    f"\u062e\u0631\u06cc\u062f {prod_match['id']}"
                )
                _set_cust_state(sender.id, "BROWSING_PRODUCTS")
                return

            # ── 3c) دستورات ثابت مشتری ─────────────────────────
            CMD_FA = {
                "\u062e\u0631\u06cc\u062f \u06a9\u0646": "browse",
                "\u0644\u06cc\u0633\u062a \u0645\u062d\u0635\u0648\u0644": "browse",
                "\u0648\u0636\u0639\u06cc\u062a \u0633\u0641\u0627\u0631\u0634": "status",
                "\u0644\u063a\u0648 \u0633\u0641\u0627\u0631\u0634": "cancel",
                "\u06a9\u0645\u06a9": "help",
                "\u0631\u0627\u0647\u0646\u0645\u0627": "help",
                "help": "help",
                "start": "help",
            }
            action = CMD_FA.get(text.lower())
            if action == "browse":
                _set_cust_state(sender.id, "BROWSING_PRODUCTS")
                await event.reply(_build_products_text())
                return
            if action == "status":
                with _db_lock:
                    conn = get_conn()
                    orders = conn.execute(
                        "SELECT * FROM store_orders WHERE uid=? ORDER BY id DESC LIMIT 3",
                        (sender.id,)
                    ).fetchall()
                if not orders:
                    await event.reply(
                        "\U0001f4ed \u0633\u0641\u0627\u0631\u0634\u06cc \u062b\u0628\u062a \u0646\u0634\u062f\u0647.\n\u0645\u062d\u0635\u0648\u0644\u0627\u062a"
                    )
                    return
                STATUS_FA = {
                    "waiting_payment": "\u23f3 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u067e\u0631\u062f\u0627\u062e\u062a",
                    "pending": "\U0001f50d \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc",
                    "approved": "\u2705 \u062a\u0627\u06cc\u06cc\u062f \u2014 \u06a9\u0627\u0646\u0641\u06cc\u06af \u0627\u0631\u0633\u0627\u0644 \u0634\u062f",
                    "rejected": "\u274c \u0631\u062f \u0634\u062f\u0647",
                    "delivered": "\U0001f4e6 \u062a\u062d\u0648\u06cc\u0644",
                    "cancelled": "\U0001f6ab \u0644\u063a\u0648",
                }
                NL = "\n"
                SEP = "\u2501" * 17
                lines = ["\U0001f4e6 \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u0634\u0645\u0627:"]
                for o in orders:
                    st = STATUS_FA.get(o["status"], o["status"])
                    lines.append(
                        f"{SEP}{NL}\U0001f194 {o['order_uid']}{NL}"
                        f"\U0001f4e6 {o['product_name'] or '\u2014'}{NL}"
                        f"\U0001f4cc {st}{NL}"
                        f"\U0001f550 {o['ts'][:16]}"
                    )
                await event.reply(NL.join(lines))
                return
            if action == "cancel":
                if cst["state"] in ("WAITING_PAYMENT", "WAITING_RECEIPT"):
                    order_uid = cst["order_uid"]
                    if order_uid:
                        with _db_lock:
                            conn = get_conn()
                            conn.execute(
                                "UPDATE store_orders SET status='cancelled'"
                                " WHERE order_uid=? AND status IN ('waiting_payment','pending')",
                                (order_uid,)
                            )
                            conn.commit()
                        _log_order_history(order_uid, "cancelled", "customer request")
                    _reset_cust_state(sender.id)
                    await event.reply("\u2705 \u0633\u0641\u0627\u0631\u0634 \u0644\u063a\u0648 \u0634\u062f.")
                else:
                    await event.reply("\u2139\ufe0f \u0633\u0641\u0627\u0631\u0634 \u0641\u0639\u0627\u0644\u06cc \u0646\u062f\u0627\u0631\u06cc\u062f.")
                return
            if action == "help":
                await event.reply(
                    "\U0001f6d2 \u0628\u0647 \u0641\u0631\u0648\u0634\u06af\u0627\u0647 \u062e\u0648\u0634 \u0622\u0645\u062f\u06cc\u062f!\n\n"
                    "\u062f\u0633\u062a\u0648\u0631\u0627\u062a:\n"
                    "\u2022 \u062e\u0631\u06cc\u062f \u2014 \u0645\u0634\u0627\u0647\u062f\u0647 \u0645\u062d\u0635\u0648\u0644\u0627\u062a\n"
                    "\u2022 \u062e\u0631\u06cc\u062f [ID] \u2014 \u062e\u0631\u06cc\u062f \u0645\u062d\u0635\u0648\u0644\n"
                    "\u2022 \u062a\u0645\u062f\u06cc\u062f \u2014 \u062a\u0645\u062f\u06cc\u062f \u0627\u0634\u062a\u0631\u0627\u06a9\n"
                    "\u2022 \u0648\u0636\u0639\u06cc\u062a \u0633\u0641\u0627\u0631\u0634 \u2014 \u0628\u0631\u0631\u0633\u06cc \u0633\u0641\u0627\u0631\u0634\n"
                    "\u2022 \u0644\u063a\u0648 \u0633\u0641\u0627\u0631\u0634 \u2014 \u0644\u063a\u0648 \u0633\u0641\u0627\u0631\u0634 \u0641\u0639\u0644\u06cc"
                )
                return

            # ── 3d) خرید [شماره] ─────────────────────────────────
            import re as _re
            m_buy = _re.match(r"^\u062e\u0631\u06cc\u062f\s+(\d+)$", text)
            if m_buy:
                pid = int(m_buy.group(1))
                with _db_lock:
                    conn = get_conn()
                    prod = conn.execute(
                        "SELECT * FROM store_products WHERE id=? AND active=1", (pid,)
                    ).fetchone()
                    avail = (conn.execute(
                        "SELECT COUNT(*) FROM store_configs WHERE product_id=? AND sold=0",
                        (pid,)
                    ).fetchone() or [0])[0]
                if not prod:
                    await event.reply(_build_products_text())
                    return
                if avail == 0:
                    with _db_lock:
                        conn = get_conn()
                        try:
                            conn.execute(
                                "INSERT INTO waiting_list(uid,product_id,ts) VALUES(?,?,?)",
                                (sender.id, pid, now_str())
                            )
                            conn.commit()
                        except Exception:
                            pass
                    await event.reply(
                        f"\u274c \u00ab{prod['name']}\u00bb \u0645\u0648\u062c\u0648\u062f \u0646\u06cc\u0633\u062a.\n"
                        "\u0634\u0645\u0627 \u062f\u0631 \u0644\u06cc\u0633\u062a \u0627\u0646\u062a\u0638\u0627\u0631 \u062b\u0628\u062a \u0634\u062f\u06cc\u062f."
                    )
                    return
                order_uid = _gen_order_id()
                sname = ((getattr(sender, "first_name", "") or "")
                         + " " + (getattr(sender, "last_name", "") or "")).strip() or str(sender.id)
                susername = getattr(sender, "username", "") or ""
                with _db_lock:
                    conn = get_conn()
                    conn.execute(
                        "INSERT INTO store_orders"
                        "(order_uid,uid,username,name,product_id,product_name,price,status,ts)"
                        " VALUES(?,?,?,?,?,?,?,'waiting_payment',?)",
                        (order_uid, sender.id, susername, sname,
                         pid, prod["name"], prod["price"], now_str())
                    )
                    conn.commit()
                _log_order_history(order_uid, "created", f"product:{prod['name']}")
                _set_cust_state(sender.id, "WAITING_PAYMENT", pid, order_uid,
                                {"product_name": prod["name"], "price": prod["price"]})
                await event.reply(
                    _build_payment_text(dict(prod), order_uid),
                    parse_mode='html'
                )
                return

            # ── 3e) تمدید ────────────────────────────────────────
            if text in ("\u062a\u0645\u062f\u06cc\u062f", "\u062a\u0645\u062f\u06cc\u062f \u0627\u0634\u062a\u0631\u0627\u06a9"):
                with _db_lock:
                    conn = get_conn()
                    last = conn.execute(
                        "SELECT * FROM store_orders WHERE uid=? AND status='approved'"
                        " ORDER BY id DESC LIMIT 1",
                        (sender.id,)
                    ).fetchone()
                if not last:
                    await event.reply(
                        "\u274c \u062e\u0631\u06cc\u062f\u06cc \u06cc\u0627\u0641\u062a \u0646\u0634\u062f.\n\n"
                        + _build_products_text()
                    )
                    return
                with _db_lock:
                    conn = get_conn()
                    prod = conn.execute(
                        "SELECT * FROM store_products WHERE id=? AND active=1",
                        (last["product_id"],)
                    ).fetchone()
                if not prod:
                    await event.reply(_build_products_text())
                    return
                NL = "\n"
                await event.reply(
                    f"\U0001f504 \u062a\u0645\u062f\u06cc\u062f \u0627\u0634\u062a\u0631\u0627\u06a9{NL}"
                    f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
                    f"\U0001f4e6 {prod['name']}{NL}"
                    f"\U0001f4b0 {prod['price']:,} \u062a\u0648\u0645\u0627\u0646{NL}"
                    f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
                    f"\u0628\u0631\u0627\u06cc \u062a\u0645\u062f\u06cc\u062f: \u062e\u0631\u06cc\u062f {prod['id']}"
                )
                return

        except Exception as ex:
            logger.debug(f"smart_engine: {ex}")

    # ════════════════════════════════════════════════════════════
    #  📱 INLINE ADMIN PANEL
    # ════════════════════════════════════════════════════════════

    def _admin_main_menu():
        """منوی اصلی ادمین"""
        return [
            [Button.inline("\U0001f3ea \u0641\u0631\u0648\u0634\u06af\u0627\u0647", b"menu:store"),
             Button.inline("\U0001f4e6 \u0633\u0641\u0627\u0631\u0634\u0627\u062a", b"menu:orders")],
            [Button.inline("\U0001f464 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646", b"menu:customers"),
             Button.inline("\U0001f4ca \u0622\u0645\u0627\u0631", b"menu:stats")],
            [Button.inline("\u2699\ufe0f \u062a\u0646\u0638\u06cc\u0645\u0627\u062a", b"menu:settings"),
             Button.inline("\U0001f3f7\ufe0f \u062a\u0631\u06cc\u06af\u0631\u0647\u0627", b"menu:triggers")],
            [Button.inline("\U0001f4e2 \u067e\u062e\u0634 \u067e\u06cc\u0627\u0645", b"menu:broadcast"),
             Button.inline("\U0001f4e6 \u0645\u0648\u062c\u0648\u062f\u06cc", b"menu:inventory")],
        ]

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644$"))
    async def admin_panel(event):
        """پنل — منوی اصلی مدیریت"""
        record_cmd("\u067e\u0646\u0644")
        with _db_lock:
            conn = get_conn()
            pending  = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='pending'").fetchone()[0]
            avail    = conn.execute("SELECT COUNT(*) FROM store_configs WHERE sold=0").fetchone()[0]
            revenue  = conn.execute("SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved'").fetchone()[0]
            custs    = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
            tickets  = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'").fetchone()[0]
        NL = "\n"
        await safe_edit(event,
            f"\U0001f3ea **\u067e\u0646\u0644 \u0645\u062f\u06cc\u0631\u06cc\u062a ONYX**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u23f3 \u0633\u0641\u0627\u0631\u0634 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631: **{pending}** | "
            f"\U0001f511 \u06a9\u0627\u0646\u0641\u06cc\u06af: **{avail}** | "
            f"\U0001f454 \u0645\u0634\u062a\u0631\u06cc: **{custs}**{NL}"
            f"\U0001f4b0 \u062f\u0631\u0622\u0645\u062f: **{revenue:,}** \u062a \u2502 \U0001f3ab \u062a\u06cc\u06a9\u062a \u0628\u0627\u0632: **{tickets}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f3ea  \u067e\u0646\u0644_\u0641\u0631\u0648\u0634\u06af\u0627\u0647    \u2014 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0648 \u06a9\u0627\u0646\u0641\u06cc\u06af{NL}"
            f"\U0001f4e6  \u067e\u0646\u0644_\u0633\u0641\u0627\u0631\u0634\u0627\u062a    \u2014 \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u0648 \u062a\u0627\u06cc\u06cc\u062f/\u0631\u062f{NL}"
            f"\U0001f464  \u067e\u0646\u0644_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646     \u2014 CRM \u0648 \u0645\u062f\u06cc\u0631\u06cc\u062a \u0645\u0634\u062a\u0631\u06cc{NL}"
            f"\U0001f4ca  \u067e\u0646\u0644_\u0622\u0645\u0627\u0631          \u2014 \u062f\u0631\u0622\u0645\u062f \u0648 \u06af\u0632\u0627\u0631\u0634{NL}"
            f"\u2699\ufe0f  \u067e\u0646\u0644_\u062a\u0646\u0638\u06cc\u0645\u0627\u062a    \u2014 \u06a9\u0627\u0631\u062a\u060c \u0645\u0642\u0635\u062f\u060c \u062a\u0646\u0638\u06cc\u0645{NL}"
            f"\U0001f3f7\ufe0f  \u067e\u0646\u0644_\u062a\u0631\u06cc\u06af\u0631\u0647\u0627     \u2014 \u0645\u062f\u06cc\u0631\u06cc\u062a \u06a9\u0644\u0645\u0627\u062a \u062e\u0631\u06cc\u062f{NL}"
            f"\U0001f4e2  \u067e\u0646\u0644_\u067e\u062e\u0634          \u2014 \u0627\u0631\u0633\u0627\u0644 \u0628\u0647 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646{NL}"
            f"\U0001f4e6  \u067e\u0646\u0644_\u0645\u0648\u062c\u0648\u062f\u06cc       \u2014 \u0648\u0636\u0639\u06cc\u062a \u06a9\u0627\u0646\u0641\u06cc\u06af\u0647\u0627{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"{WATERMARK}"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u0641\u0631\u0648\u0634\u06af\u0627\u0647$"))
    async def panel_store(event):
        """پنل_فروشگاه — زیرمنوی فروشگاه"""
        record_cmd("\u067e\u0646\u0644_\u0641\u0631\u0648\u0634\u06af\u0627\u0647")
        with _db_lock:
            conn = get_conn()
            prods = conn.execute("SELECT COUNT(*) FROM store_products WHERE active=1").fetchone()[0]
            cfgs  = conn.execute("SELECT COUNT(*) FROM store_configs WHERE sold=0").fetchone()[0]
            sold  = conn.execute("SELECT COUNT(*) FROM store_configs WHERE sold=1").fetchone()[0]
        NL = "\n"
        await safe_edit(event,
            f"\U0001f3ea **\u0641\u0631\u0648\u0634\u06af\u0627\u0647**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4e6 \u0645\u062d\u0635\u0648\u0644\u0627\u062a \u0641\u0639\u0627\u0644: **{prods}** | "
            f"\U0001f511 \u0645\u0648\u062c\u0648\u062f: **{cfgs}** | \U0001f534 \u0641\u0631\u0648\u062e\u062a\u0647: **{sold}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4cb  \u0645\u062d\u0635\u0648\u0644_\u0644\u06cc\u0633\u062a{NL}"
            f"\u2795  \u0645\u062d\u0635\u0648\u0644_\u062b\u0628\u062a [\u0646\u0627\u0645]|[\u0642\u06cc\u0645\u062a]|[\u062a\u0648\u0636\u06cc\u062d]{NL}"
            f"\u270f\ufe0f  \u0645\u062d\u0635\u0648\u0644_\u0648\u06cc\u0631\u0627\u06cc\u0634 [id] [\u0641\u06cc\u0644\u062f]=[\u0645\u0642\u062f\u0627\u0631]{NL}"
            f"\U0001f5d1\ufe0f  \u0645\u062d\u0635\u0648\u0644_\u062d\u0630\u0641 [id]{NL}"
            f"\U0001f511  \u06a9\u0627\u0646\u0641\u06cc\u06af_\u0627\u0636\u0627\u0641\u0647 [product_id]|[\u0645\u062d\u062a\u0648\u0627]{NL}"
            f"\U0001f4e6  \u0645\u0648\u062c\u0648\u062f\u06cc_\u0645\u062d\u0635\u0648\u0644 [id]{NL}"
            f"\U0001f4e6  \u0645\u0648\u062c\u0648\u062f\u06cc_\u06a9\u0644{NL}"
            f"\u26a0\ufe0f  \u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc [\u0622\u0633\u062a\u0627\u0646\u0647]{NL}"
            f"\U0001f50d  \u06a9\u0627\u0646\u0641\u06cc\u06af_\u062a\u06a9\u0631\u0627\u0631\u06cc_\u0641\u0631\u0648\u0634{NL}"
            f"\U0001f4ca  \u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644 [id]{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u0633\u0641\u0627\u0631\u0634\u0627\u062a$"))
    async def panel_orders(event):
        """پنل_سفارشات — زیرمنوی سفارشات"""
        record_cmd("\u067e\u0646\u0644_\u0633\u0641\u0627\u0631\u0634\u0627\u062a")
        with _db_lock:
            conn = get_conn()
            pending  = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='pending'").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='approved'").fetchone()[0]
            rejected = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='rejected'").fetchone()[0]
            cancelled= conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='cancelled'").fetchone()[0]
            today_cnt= conn.execute("SELECT COUNT(*) FROM store_orders WHERE ts LIKE ?", (f"{jalali()}%",)).fetchone()[0]
        NL = "\n"
        await safe_edit(event,
            f"\U0001f4e6 **\u0633\u0641\u0627\u0631\u0634\u0627\u062a**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u23f3 \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631: **{pending}** | "
            f"\u2705 \u062a\u0627\u06cc\u06cc\u062f: **{approved}** | "
            f"\u274c \u0631\u062f: **{rejected}** | "
            f"\U0001f6ab \u0644\u063a\u0648: **{cancelled}** | "
            f"\U0001f4c5 \u0627\u0645\u0631\u0648\u0632: **{today_cnt}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4cb  \u0633\u0641\u0627\u0631\u0634_\u0644\u06cc\u0633\u062a pending   \u2014 \u0633\u0641\u0627\u0631\u0634\u0627\u062a \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631{NL}"
            f"\U0001f4cb  \u0633\u0641\u0627\u0631\u0634_\u0644\u06cc\u0633\u062a approved  \u2014 \u062a\u0627\u06cc\u06cc\u062f\u0634\u062f\u0647\u200c\u0647\u0627{NL}"
            f"\U0001f4cb  \u0633\u0641\u0627\u0631\u0634_\u0644\u06cc\u0633\u062a rejected  \u2014 \u0631\u062f\u0634\u062f\u0647\u200c\u0647\u0627{NL}"
            f"\U0001f4c5  \u0633\u0641\u0627\u0631\u0634\u0627\u062a_\u0627\u0645\u0631\u0648\u0632{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2705  \u0633\u0641\u0627\u0631\u0634_\u062a\u0627\u06cc\u06cc\u062f [order_uid]{NL}"
            f"\u274c  \u0633\u0641\u0627\u0631\u0634_\u0631\u062f [order_uid] [\u062f\u0644\u06cc\u0644]{NL}"
            f"\U0001f504  \u06a9\u0627\u0646\u0641\u06cc\u06af_\u062c\u0627\u06cc\u06af\u0632\u06cc\u0646 [order_id]{NL}"
            f"\U0001f50d  \u0633\u0641\u0627\u0631\u0634_\u062c\u0633\u062a\u062c\u0648 [\u0645\u062a\u0646]{NL}"
            f"\U0001f4cb  \u062a\u0627\u0631\u06cc\u062e\u0686\u0647_\u0639\u0645\u0644\u06cc\u0627\u062a [order_uid]{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646$"))
    async def panel_customers(event):
        """پنل_مشتریان — زیرمنوی مشتریان"""
        record_cmd("\u067e\u0646\u0644_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646")
        with _db_lock:
            conn = get_conn()
            total = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
            vips  = conn.execute("SELECT COUNT(*) FROM crm_customers WHERE vip_level>0").fetchone()[0]
            blk   = conn.execute("SELECT COUNT(*) FROM crm_customers WHERE blacklisted=1").fetchone()[0]
            active_states = conn.execute(
                "SELECT COUNT(*) FROM customer_states WHERE state NOT IN ('idle','DELIVERED','REJECTED','CANCELLED')"
            ).fetchone()[0]
        NL = "\n"
        await safe_edit(event,
            f"\U0001f464 **\u0645\u0634\u062a\u0631\u06cc\u0627\u0646**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f454 \u06a9\u0644: **{total}** | \u2b50 VIP: **{vips}** | "
            f"\u26d4 \u0628\u0644\u0627\u06a9: **{blk}** | \U0001f7e1 \u0641\u0639\u0627\u0644: **{active_states}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f50d  \u0645\u0634\u062a\u0631\u06cc_\u067e\u0631\u0648\u0641\u0627\u06cc\u0644 [@\u06cc\u0648\u0632\u0631 \u06cc\u0627 ID]{NL}"
            f"\U0001f4cb  \u0645\u0634\u062a\u0631\u06cc_\u0644\u06cc\u0633\u062a{NL}"
            f"\u2b50  \u0645\u0634\u062a\u0631\u06cc_vip [@] [0-3]{NL}"
            f"\u26d4  \u0645\u0634\u062a\u0631\u06cc_\u0628\u0644\u0627\u06a9 [@] [\u062f\u0644\u06cc\u0644]{NL}"
            f"\u2705  \u0645\u0634\u062a\u0631\u06cc_\u0627\u0646\u0628\u0644\u0627\u06a9 [@]{NL}"
            f"\U0001f4cb  \u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc [@]{NL}"
            f"\U0001f504  \u0631\u06cc\u0633\u062a_\u0645\u0634\u062a\u0631\u06cc [@]{NL}"
            f"\U0001f4cb  \u0644\u06cc\u0633\u062a_\u0648\u0636\u0639\u06cc\u062a_\u0645\u0634\u062a\u0631\u06cc\u0627\u0646{NL}"
            f"\U0001f4dd  \u0645\u0634\u062a\u0631\u06cc_\u06cc\u0627\u062f\u062f\u0627\u0634\u062a [@] [\u0645\u062a\u0646]{NL}"
            f"\U0001f4ca  \u0645\u0634\u062a\u0631\u06cc_\u0633\u0627\u0628\u0642\u0647 [@]{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u0622\u0645\u0627\u0631$"))
    async def panel_stats(event):
        """پنل_آمار — زیرمنوی آمار و گزارش"""
        record_cmd("\u067e\u0646\u0644_\u0622\u0645\u0627\u0631")
        with _db_lock:
            conn = get_conn()
            revenue   = conn.execute("SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved'").fetchone()[0]
            approved  = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='approved'").fetchone()[0]
            today_rev = conn.execute(
                "SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved' AND ts LIKE ?",
                (f"{jalali()}%",)
            ).fetchone()[0]
            month_rev = conn.execute(
                "SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved' AND ts LIKE ?",
                (f"{jalali()[:7]}%",)
            ).fetchone()[0]
        NL = "\n"
        await safe_edit(event,
            f"\U0001f4ca **\u0622\u0645\u0627\u0631**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4b0 \u0627\u0645\u0631\u0648\u0632: **{today_rev:,}** | "
            f"\U0001f4c5 \u0645\u0627\u0647: **{month_rev:,}** | "
            f"\U0001f4b8 \u06a9\u0644: **{revenue:,}** \u062a\u0648\u0645\u0627\u0646{NL}"
            f"\u2705 \u0633\u0641\u0627\u0631\u0634 \u062a\u0627\u06cc\u06cc\u062f: **{approved}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4ca  \u0622\u0645\u0627\u0631_\u0641\u0631\u0648\u0634\u06af\u0627\u0647{NL}"
            f"\U0001f4c5  \u0633\u0641\u0627\u0631\u0634\u0627\u062a_\u0627\u0645\u0631\u0648\u0632{NL}"
            f"\U0001f4b0  \u062f\u0631\u0622\u0645\u062f_\u0645\u0627\u0647{NL}"
            f"\U0001f4ca  \u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644{NL}"
            f"\U0001f4ca  \u0641\u0631\u0648\u0634_\u0645\u062d\u0635\u0648\u0644 [id] \u2014 \u0622\u0645\u0627\u0631 \u06cc\u06a9 \u0645\u062d\u0635\u0648\u0644{NL}"
            f"\U0001f4c8  \u0622\u0645\u0627\u0631_\u06a9\u0627\u0645\u0644{NL}"
            f"\U0001f4ca  \u06af\u0632\u0627\u0631\u0634_\u0641\u0631\u0648\u0634\u06af\u0627\u0647{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u062a\u0646\u0638\u06cc\u0645\u0627\u062a$"))
    async def panel_settings(event):
        """پنل_تنظیمات — زیرمنوی تنظیمات"""
        record_cmd("\u067e\u0646\u0644_\u062a\u0646\u0638\u06cc\u0645\u0627\u062a")
        card   = _store_setting("card_number", "\u2014")
        holder = _store_setting("card_holder", "\u2014")
        bank   = _store_setting("bank_name", "\u2014")
        dest   = _store_setting("report_dest", "saved")
        admin  = _store_setting("admin_id", "\u2014")
        note   = _store_setting("payment_note", "\u2014")
        low_th = _store_setting("low_stock_threshold", "3")
        NL = "\n"
        await safe_edit(event,
            f"\u2699\ufe0f **\u062a\u0646\u0638\u06cc\u0645\u0627\u062a \u0641\u0639\u0644\u06cc**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4b3 \u06a9\u0627\u0631\u062a: {card[:20] if card else '\u2014'}{NL}"
            f"\U0001f464 \u0635\u0627\u062d\u0628: {holder}{NL}"
            f"\U0001f3e6 \u0628\u0627\u0646\u06a9: {bank}{NL}"
            f"\U0001f4cd \u0645\u0642\u0635\u062f \u06af\u0632\u0627\u0631\u0634: {dest or 'saved'}{NL}"
            f"\U0001f464 \u0622\u06cc\u062f\u06cc \u0627\u062f\u0645\u06cc\u0646: {admin}{NL}"
            f"\u26a0\ufe0f \u0622\u0633\u062a\u0627\u0646\u0647 \u0645\u0648\u062c\u0648\u062f\u06cc: {low_th}{NL}"
            f"\U0001f4dd \u062a\u0648\u0636\u06cc\u062d: {note[:40] if note else '\u2014'}{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f4b3  \u06a9\u0627\u0631\u062a_\u067e\u0631\u062f\u0627\u062e\u062a [\u0634\u0645\u0627\u0631\u0647]|[\u0635\u0627\u062d\u0628]|[\u0628\u0627\u0646\u06a9]{NL}"
            f"\U0001f4dd  \u0645\u062a\u0646_\u067e\u0631\u062f\u0627\u062e\u062a [\u062a\u0648\u0636\u06cc\u062d]{NL}"
            f"\U0001f4cd  \u0645\u0642\u0635\u062f_\u06af\u0632\u0627\u0631\u0634 [saved | -100xxx]{NL}"
            f"\U0001f464  \u0686\u062a_\u0627\u062f\u0645\u06cc\u0646 [\u0622\u06cc\u062f\u06cc]{NL}"
            f"\u26a0\ufe0f  \u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc [\u0639\u062f\u062f]{NL}"
            f"\u2699\ufe0f  \u062a\u0646\u0638\u06cc\u0645_\u0641\u0631\u0648\u0634\u06af\u0627\u0647 [\u06a9\u0644\u06cc\u062f]|[\u0645\u0642\u062f\u0627\u0631]{NL}"
            f"\U0001f4cb  \u062a\u0646\u0638\u06cc\u0645\u0627\u062a_\u0641\u0631\u0648\u0634\u06af\u0627\u0647{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u062a\u0631\u06cc\u06af\u0631\u0647\u0627$"))
    async def panel_triggers(event):
        """پنل_تریگرها — مدیریت تریگرهای خرید"""
        record_cmd("\u067e\u0646\u0644_\u062a\u0631\u06cc\u06af\u0631\u0647\u0627")
        rows = _get_triggers()
        NL = "\n"
        lines = []
        for r in rows:
            dest = f"\u0645\u062d\u0635\u0648\u0644 {r['product_id']}" if r["product_id"] else "\u0641\u0631\u0648\u0634\u06af\u0627\u0647"
            lines.append(f"\u2022 **{r['word']}** \u2192 {dest}")
        trig_text = NL.join(lines) if lines else "\u2014"
        await safe_edit(event,
            f"\U0001f3f7\ufe0f **\u062a\u0631\u06cc\u06af\u0631\u0647\u0627 ({len(rows)})**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"{trig_text}{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2795  \u062a\u0631\u06cc\u06af\u0631_\u0627\u0636\u0627\u0641\u0647 [\u06a9\u0644\u0645\u0647]{NL}"
            f"\u2795  \u062a\u0631\u06cc\u06af\u0631_\u0627\u0636\u0627\u0641\u0647 [\u06a9\u0644\u0645\u0647]|[product_id] \u2014 \u0628\u0627\u0632 \u06a9\u0631\u062f\u0646 \u0645\u0633\u062a\u0642\u06cc\u0645 \u0645\u062d\u0635\u0648\u0644{NL}"
            f"\U0001f5d1\ufe0f  \u062a\u0631\u06cc\u06af\u0631_\u062d\u0630\u0641 [\u06a9\u0644\u0645\u0647]{NL}"
            f"\U0001f4cb  \u062a\u0631\u06cc\u06af\u0631_\u0644\u06cc\u0633\u062a{NL}"
            f"\U0001f504  \u062a\u0631\u06cc\u06af\u0631_\u067e\u06cc\u0634\u200c\u0641\u0631\u0636{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^\u062a\u0631\u06cc\u06af\u0631_\u067e\u06cc\u0634_\u0641\u0631\u0636$"))
    async def trigger_seed_cmd(event):
        """تریگر_پیش_فرض — بارگذاری تریگرهای پیش‌فرض"""
        record_cmd("\u062a\u0631\u06cc\u06af\u0631_\u067e\u06cc\u0634_\u0641\u0631\u0636")
        _seed_default_triggers()
        await safe_edit(event, "\u2705 \u062a\u0631\u06cc\u06af\u0631\u0647\u0627\u06cc \u067e\u06cc\u0634\u200c\u0641\u0631\u0636 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0634\u062f\u0646\u062f.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u067e\u062e\u0634$"))
    async def panel_broadcast(event):
        """پنل_پخش — ارسال پیام به مشتریان"""
        record_cmd("\u067e\u0646\u0644_\u067e\u062e\u0634")
        with _db_lock:
            conn = get_conn()
            total = conn.execute("SELECT COUNT(*) FROM crm_customers WHERE blacklisted=0").fetchone()[0]
            vips  = conn.execute("SELECT COUNT(*) FROM crm_customers WHERE vip_level>0 AND blacklisted=0").fetchone()[0]
            prods = conn.execute("SELECT id, name FROM store_products WHERE active=1 ORDER BY id").fetchall()
        NL = "\n"
        prod_lines = NL.join(
            f"\U0001f4e6  \u067e\u062e\u0634_\u0645\u062d\u0635\u0648\u0644 {p['id']} [\u067e\u06cc\u0627\u0645] \u2014 \u062e\u0631\u06cc\u062f\u0627\u0631\u0627\u0646 {p['name'][:20]}"
            for p in prods
        ) if prods else "\u2014"
        await safe_edit(event,
            f"\U0001f4e2 **\u067e\u062e\u0634 \u067e\u06cc\u0627\u0645**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f454 \u0647\u0645\u0647 \u0645\u0634\u062a\u0631\u06cc\u0627\u0646: **{total}** \u0646\u0641\u0631{NL}"
            f"\u2b50 VIP: **{vips}** \u0646\u0641\u0631{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f465  \u067e\u062e\u0634_\u0647\u0645\u0647 [\u067e\u06cc\u0627\u0645]{NL}"
            f"\u2b50  \u067e\u062e\u0634_vip [\u067e\u06cc\u0627\u0645]{NL}"
            f"\U0001f4e4  \u067e\u06cc\u0627\u0645_\u0645\u0634\u062a\u0631\u06cc [@\u06cc\u0627 ID] [\u067e\u06cc\u0627\u0645]{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u067e\u062e\u0634 \u0628\u0631 \u0627\u0633\u0627\u0633 \u0645\u062d\u0635\u0648\u0644:{NL}"
            f"{prod_lines}{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\u067e\u0646\u0644_\u0645\u0648\u062c\u0648\u062f\u06cc$"))
    async def panel_inventory(event):
        """پنل_موجودی — وضعیت موجودی کانفیگ‌ها"""
        record_cmd("\u067e\u0646\u0644_\u0645\u0648\u062c\u0648\u062f\u06cc")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT p.id, p.name, p.price, p.active,"
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=0) AS avail,"
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=1) AS sold_cnt "
                "FROM store_products p ORDER BY p.active DESC, avail ASC"
            ).fetchall()
        NL = "\n"
        low_th = int(_store_setting("low_stock_threshold", "3"))
        lines = []
        for r in rows:
            avail = r["avail"] or 0
            sold  = r["sold_cnt"] or 0
            act   = "\u2705" if r["active"] else "\u274c"
            icon  = "\U0001f534" if avail == 0 else ("\u26a0\ufe0f" if avail <= low_th else "\U0001f7e2")
            lines.append(
                f"{act}{icon} **{r['id']}. {r['name'][:18]}**  "
                f"\u0645\u0648\u062c\u0648\u062f:{avail} | \u0641\u0631\u0648\u062e\u062a\u0647:{sold} | {r['price']:,}\u062a"
            )
        total_avail = sum(r["avail"] or 0 for r in rows)
        await safe_edit(event,
            f"\U0001f4e6 **\u0645\u0648\u062c\u0648\u062f\u06cc ({len(rows)} \u0645\u062d\u0635\u0648\u0644)**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            + NL.join(lines) + NL
            + f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\U0001f7e2=OK \u26a0\ufe0f=\u06a9\u0645 \U0001f534=\u0635\u0641\u0631  |  \u062c\u0645\u0639 \u0645\u0648\u062c\u0648\u062f: **{total_avail}**{NL}"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{NL}"
            f"\u06a9\u0627\u0646\u0641\u06cc\u06af_\u0627\u0636\u0627\u0641\u0647 [product_id]|[\u0645\u062d\u062a\u0648\u0627]{NL}"
            f"\u0645\u0648\u062c\u0648\u062f\u06cc_\u06a9\u0644{NL}"
            f"\u0647\u0634\u062f\u0627\u0631_\u0645\u0648\u062c\u0648\u062f\u06cc{NL}"
            f"\u2B05\ufe0f \u067e\u0646\u0644"
        )


# ══════════════════════════════════════════════════════
#  ═══  ONYX SELF V8 PRO'S — ارتقاء  ═══
#  تمام قابلیت‌های جدید — تک‌فایلی — بدون تغییر ساختار
# ══════════════════════════════════════════════════════

VERSION = "8.0.0"

# ── جداول جدید V8 ──────────────────────────────────
def _v8_init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        -- Multi-type store delivery
        ALTER TABLE store_products ADD COLUMN product_type TEXT DEFAULT 'config';
        ALTER TABLE store_products ADD COLUMN file_path TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_text TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_pdf TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_video TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_image TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_link TEXT DEFAULT '';
        ALTER TABLE store_products ADD COLUMN tutorial_attachment TEXT DEFAULT '';

        -- Enhanced CRM
        ALTER TABLE crm_customers ADD COLUMN phone TEXT DEFAULT '';
        ALTER TABLE crm_customers ADD COLUMN email TEXT DEFAULT '';
        ALTER TABLE crm_customers ADD COLUMN city TEXT DEFAULT '';
        ALTER TABLE crm_customers ADD COLUMN tags TEXT DEFAULT '[]';
        ALTER TABLE crm_customers ADD COLUMN is_vip INTEGER DEFAULT 0;
        ALTER TABLE crm_customers ADD COLUMN score INTEGER DEFAULT 0;
        ALTER TABLE crm_customers ADD COLUMN join_date TEXT DEFAULT '';
        ALTER TABLE crm_customers ADD COLUMN admin_note TEXT DEFAULT '';
    """)
    conn.executescript("""
        -- Subscription / renewal
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT DEFAULT '',
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            auto_renew INTEGER DEFAULT 0,
            reminded INTEGER DEFAULT 0,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sub_uid ON subscriptions(uid);
        CREATE INDEX IF NOT EXISTS idx_sub_end ON subscriptions(end_date);

        -- Auto-save timed media
        CREATE TABLE IF NOT EXISTS timed_media_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            sender_name TEXT DEFAULT '',
            file_id TEXT DEFAULT '',
            media_type TEXT DEFAULT 'photo',
            caption TEXT DEFAULT '',
            duration INTEGER DEFAULT 0,
            saved_msg_id INTEGER DEFAULT 0,
            ts TEXT NOT NULL,
            UNIQUE(file_id, sender_id)
        );

        -- Timed media destinations
        CREATE TABLE IF NOT EXISTS timed_media_dests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dest TEXT NOT NULL UNIQUE,
            label TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            added TEXT NOT NULL
        );

        -- Self-Healing Engine
        CREATE TABLE IF NOT EXISTS health_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            fixed INTEGER DEFAULT 0,
            fix_note TEXT DEFAULT '',
            ts TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS black_box (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            detail TEXT DEFAULT '',
            extra TEXT DEFAULT '{}',
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_bb_ts ON black_box(ts);

        -- Command Studio
        CREATE TABLE IF NOT EXISTS custom_commands (
            name TEXT PRIMARY KEY,
            params TEXT DEFAULT '',
            condition TEXT DEFAULT '',
            action TEXT NOT NULL,
            reply TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            ts TEXT NOT NULL
        );

        -- Invisible Watermark
        CREATE TABLE IF NOT EXISTS watermark_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            file_hash TEXT NOT NULL,
            wm_code TEXT NOT NULL,
            file_type TEXT DEFAULT '',
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_wm_hash ON watermark_registry(file_hash);

        -- Honeytrap / identity verifier results
        CREATE TABLE IF NOT EXISTS identity_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            result TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            ts TEXT NOT NULL
        );

        -- Airlock log
        CREATE TABLE IF NOT EXISTS airlock_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger TEXT NOT NULL,
            detail TEXT DEFAULT '',
            ts TEXT NOT NULL
        );
    """)
    conn.commit()

# اجرای schema V8 در هنگام اتصال
_orig_get_conn = get_conn
def get_conn() -> sqlite3.Connection:
    global _conn
    conn = _orig_get_conn()
    # اگر V8 schema اجرا نشده باشد، اجرا می‌کنیم
    try:
        conn.execute("SELECT product_type FROM store_products LIMIT 1")
    except Exception:
        try:
            _v8_init_schema(conn)
        except Exception as _e:
            logger.debug(f"V8 schema init: {_e}")
    return conn

# ── متغیرهای Global V8 ──────────────────────────
_airlock_active: bool = False
_wm_active: bool = True
_timed_media_active: bool = True

def _bb_log(event_type: str, detail: str = "", extra: dict = None):
    """Black Box ثبت رویداد"""
    try:
        with _db_lock:
            conn = _orig_get_conn()
            conn.execute(
                "INSERT INTO black_box(event_type,detail,extra,ts) VALUES(?,?,?,?)",
                (event_type[:80], detail[:500],
                 json.dumps(extra or {}, ensure_ascii=False)[:500], now_str())
            )
            conn.commit()
    except Exception:
        pass

def _health_log(issue_type: str, detail: str = "", fixed: bool = False, fix_note: str = ""):
    """Health Engine ثبت مشکل"""
    try:
        with _db_lock:
            conn = _orig_get_conn()
            conn.execute(
                "INSERT INTO health_log(issue_type,detail,fixed,fix_note,ts) VALUES(?,?,?,?,?)",
                (issue_type[:80], detail[:500], 1 if fixed else 0, fix_note[:200], now_str())
            )
            conn.commit()
    except Exception:
        pass

def _gen_wm_code(uid: int, file_hash: str) -> str:
    """تولید کد واترمارک"""
    raw = f"ONYX-{uid}-{file_hash[:8]}-{int(_time.time())}"
    return base64.b64encode(raw.encode()).decode()[:24]

def _register_v8(client):
    """ثبت تمام هندلرهای V8"""

    # ════════════════════════════════
    #  📦 فروشگاه چند‌نوعی
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^محصول_نوع (\d+)\|(.+)$"))
    async def set_product_type(event):
        record_cmd("محصول_نوع")
        pid = int(event.pattern_match.group(1))
        ptype = event.pattern_match.group(2).strip()
        VALID = ["config","file","pdf","zip","image","video","course",
                 "subscription","license","account","service","digital",
                 "physical","template","app","encrypted"]
        if ptype not in VALID:
            await safe_edit(event, f"❌ نوع نامعتبر!\nمجاز: {', '.join(VALID)}"); return
        with _db_lock:
            conn = get_conn()
            c = conn.execute("UPDATE store_products SET product_type=? WHERE id=?", (ptype, pid))
            conn.commit()
        _bb_log("product_type_set", f"pid={pid} type={ptype}")
        await safe_edit(event, f"✅ نوع محصول {pid} به «{ptype}» تغییر یافت.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^محصول_فایل (\d+)$"))
    async def set_product_file(event):
        record_cmd("محصول_فایل")
        pid = int(event.pattern_match.group(1))
        reply = await event.get_reply_message()
        if not reply or not reply.media:
            await safe_edit(event, "❌ باید روی یک فایل ریپلای کنی!"); return
        try:
            dl_path = os.path.join(DL_DIR, f"product_{pid}_{now_str().replace('/','-').replace(' ','_')}")
            await client.download_media(reply.media, file=dl_path)
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE store_products SET file_path=? WHERE id=?", (dl_path, pid))
                conn.commit()
            await safe_edit(event, f"✅ فایل محصول {pid} ذخیره شد.")
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    # ════════════════════════════════
    #  📚 سیستم آموزش محصول
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^آموزش_محصول (\d+)\|(.+)$"))
    async def set_product_tutorial_text(event):
        record_cmd("آموزش_محصول")
        pid   = int(event.pattern_match.group(1))
        text  = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE store_products SET tutorial_text=? WHERE id=?", (text[:2000], pid))
            conn.commit()
        await safe_edit(event, f"✅ آموزش متنی محصول {pid} ثبت شد.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^آموزش_لینک (\d+)\|(.+)$"))
    async def set_product_tutorial_link(event):
        record_cmd("آموزش_لینک")
        pid  = int(event.pattern_match.group(1))
        link = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE store_products SET tutorial_link=? WHERE id=?", (link[:500], pid))
            conn.commit()
        await safe_edit(event, f"✅ لینک آموزشی محصول {pid} ثبت شد.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^آموزش_نمایش (\d+)$"))
    async def show_product_tutorial(event):
        record_cmd("آموزش_نمایش")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            prod = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
        if not prod:
            await safe_edit(event, "❌ محصول پیدا نشد!"); return
        lines = [
            f"📚 آموزش: {prod['name']}",
            "━"*17,
        ]
        if prod.get("tutorial_text"):
            lines.append(f"📝 متن: {prod['tutorial_text'][:200]}")
        if prod.get("tutorial_link"):
            lines.append(f"🔗 لینک: {prod['tutorial_link']}")
        if prod.get("tutorial_pdf"):
            lines.append(f"📄 PDF: موجود")
        if prod.get("tutorial_video"):
            lines.append(f"🎥 ویدیو: موجود")
        if prod.get("tutorial_image"):
            lines.append(f"🖼 تصویر: موجود")
        await safe_edit(event, "\n".join(lines))

    # ════════════════════════════════
    #  👥 CRM حرفه‌ای
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^crm_تلفن (.+)\|(.+)$"))
    async def crm_set_phone(event):
        record_cmd("crm_تلفن")
        arg   = event.pattern_match.group(1).strip()
        phone = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg if not arg.startswith("+") else None)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO crm_customers(uid,phone) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET phone=excluded.phone",
                (uid, phone[:30])
            )
            conn.commit()
        await safe_edit(event, f"✅ تلفن مشتری {uid} ثبت شد.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^crm_ایمیل (.+)\|(.+)$"))
    async def crm_set_email(event):
        record_cmd("crm_ایمیل")
        arg   = event.pattern_match.group(1).strip()
        email = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO crm_customers(uid,email) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET email=excluded.email",
                (uid, email[:100])
            )
            conn.commit()
        await safe_edit(event, f"✅ ایمیل مشتری {uid} ثبت شد.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^crm_یادداشت (.+)\|(.+)$"))
    async def crm_set_note(event):
        record_cmd("crm_یادداشت")
        arg  = event.pattern_match.group(1).strip()
        note = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO crm_customers(uid,admin_note) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET admin_note=excluded.admin_note",
                (uid, note[:500])
            )
            conn.commit()
        await safe_edit(event, f"✅ یادداشت مشتری {uid} ثبت شد.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^crm_vip (.+)$"))
    async def crm_set_vip(event):
        record_cmd("crm_vip")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO crm_customers(uid,is_vip,vip_level) VALUES(?,1,1) "
                "ON CONFLICT(uid) DO UPDATE SET is_vip=1, vip_level=MAX(1,vip_level)",
                (uid,)
            )
            conn.commit()
        await safe_edit(event, f"⭐ مشتری {uid} به VIP ارتقا یافت.")

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^crm_پروفایل (.+)$"))
    async def crm_profile_full(event):
        record_cmd("crm_پروفایل")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM crm_customers WHERE uid=?", (uid,)).fetchone()
            orders_cnt = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE uid=? AND status='approved'",
                (uid,)
            ).fetchone()[0]
        if not row:
            await safe_edit(event, f"❌ مشتری {uid} در CRM نیست!"); return
        lines = [
            f"👤 {row['name']} (@{row['username'] or '—'})",
            f"🆔 {uid}",
            f"📱 {row.get('phone','—') or '—'}",
            f"📧 {row.get('email','—') or '—'}",
            f"🏙 {row.get('city','—') or '—'} / {row.get('country','—') or '—'}",
            f"⭐ VIP: {'بله' if row.get('is_vip') else 'خیر'} | امتیاز: {row.get('score',0)}",
            f"💰 خرید کل: {row.get('total_spent',0):,} تومان",
            f"📦 سفارش‌ها: {orders_cnt} تایید‌شده",
            f"📅 آخرین خرید: {row.get('last_purchase','—') or '—'}",
            f"🗓 عضویت: {row.get('join_date','—') or '—'}",
            f"📝 یادداشت: {(row.get('admin_note','') or '')[:80] or '—'}",
        ]
        await safe_edit(event, box(f"👤 پروفایل کامل CRM", lines))

    # ════════════════════════════════
    #  🔄 سیستم اشتراک و تمدید
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^اشتراک_ثبت (\d+)\|(\d+)$"))
    async def subscription_add(event):
        record_cmd("اشتراک_ثبت")
        uid  = int(event.pattern_match.group(1))
        days = int(event.pattern_match.group(2))
        with _db_lock:
            conn = get_conn()
            last_order = conn.execute(
                "SELECT * FROM store_orders WHERE uid=? AND status='approved' ORDER BY id DESC LIMIT 1",
                (uid,)
            ).fetchone()
        pname = last_order["product_name"] if last_order else "اشتراک"
        pid   = last_order["product_id"]   if last_order else 0
        start = jalali()
        # محاسبه تاریخ پایان (ساده: جمع روزها)
        from datetime import date, timedelta
        try:
            parts = start.split("/")
            g_date = date(int(parts[0])+621, int(parts[1]), int(parts[2]))
            end_g  = g_date + timedelta(days=days)
            end    = f"{end_g.year-621:04d}/{end_g.month:02d}/{end_g.day:02d}"
        except Exception:
            end = start
        with _db_lock:
            conn = get_conn()
            sid = conn.execute(
                "INSERT INTO subscriptions(uid,product_id,product_name,start_date,end_date,ts) "
                "VALUES(?,?,?,?,?,?)",
                (uid, pid, pname, start, end, now_str())
            ).lastrowid
            conn.commit()
        await safe_edit(event, box("✅ اشتراک ثبت شد", [
            f"مشتری: {uid}",
            f"محصول: {pname}",
            f"شروع: {start}",
            f"پایان: {end}",
            f"مدت: {days} روز",
            f"ID اشتراک: {sid}",
        ]))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^اشتراک_لیست(?: (\d+))?$"))
    async def subscription_list(event):
        record_cmd("اشتراک_لیست")
        uid = event.pattern_match.group(1)
        with _db_lock:
            conn = get_conn()
            if uid:
                rows = conn.execute(
                    "SELECT * FROM subscriptions WHERE uid=? ORDER BY id DESC LIMIT 10",
                    (int(uid),)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM subscriptions ORDER BY end_date ASC LIMIT 20"
                ).fetchall()
        if not rows:
            await safe_edit(event, "📭 اشتراکی ثبت نشده!"); return
        today = jalali()
        lines = []
        for r in rows:
            status = "✅" if r["end_date"] >= today else "❌ منقضی"
            lines.append(f"{status} uid:{r['uid']} | {r['product_name'][:15]} | {r['end_date']}")
        await safe_edit(event, box(f"🔄 اشتراک‌ها ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^اشتراک_یادآوری$"))
    async def subscription_remind(event):
        record_cmd("اشتراک_یادآوری")
        today = jalali()
        # اشتراک‌هایی که تا ۷ روز دیگر منقضی می‌شوند
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM subscriptions WHERE reminded=0 AND end_date >= ? ORDER BY end_date",
                (today,)
            ).fetchall()
        expiring = []
        for r in rows:
            try:
                parts_e = r["end_date"].split("/")
                parts_t = today.split("/")
                diff = (int(parts_e[2]) - int(parts_t[2]))
                if diff <= 7:
                    expiring.append((r, diff))
            except Exception:
                pass
        if not expiring:
            await safe_edit(event, "✅ هیچ اشتراک رو به انقضایی نیست."); return
        me = await client.get_me()
        lines = []
        for r, diff in expiring:
            lines.append(f"⚠️ uid:{r['uid']} | {r['product_name'][:15]} | {diff} روز دیگر")
            # یادآوری به مشتری
            try:
                await client.send_message(r["uid"],
                    f"⚠️ اشتراک شما ({r['product_name']}) {diff} روز دیگر منقضی می‌شود.\n"
                    f"برای تمدید پیام «تمدید» ارسال کنید."
                )
                with _db_lock:
                    conn = get_conn()
                    conn.execute("UPDATE subscriptions SET reminded=1 WHERE id=?", (r["id"],))
                    conn.commit()
            except Exception as ex:
                lines.append(f"  ❌ خطا در ارسال: {ex}")
        await safe_edit(event, box(f"⚠️ یادآوری تمدید ({len(expiring)})", lines))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^اشتراک_تمدید (\d+)\|(\d+)$"))
    async def subscription_renew(event):
        record_cmd("اشتراک_تمدید")
        sid  = int(event.pattern_match.group(1))
        days = int(event.pattern_match.group(2))
        with _db_lock:
            conn = get_conn()
            sub = conn.execute("SELECT * FROM subscriptions WHERE id=?", (sid,)).fetchone()
        if not sub:
            await safe_edit(event, "❌ اشتراک پیدا نشد!"); return
        try:
            parts = sub["end_date"].split("/")
            from datetime import date, timedelta
            g_date = date(int(parts[0])+621, int(parts[1]), int(parts[2]))
            new_end_g = g_date + timedelta(days=days)
            new_end = f"{new_end_g.year-621:04d}/{new_end_g.month:02d}/{new_end_g.day:02d}"
        except Exception:
            new_end = sub["end_date"]
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE subscriptions SET end_date=?, reminded=0 WHERE id=?",
                         (new_end, sid))
            conn.commit()
        await safe_edit(event, f"✅ اشتراک {sid} به {new_end} تمدید شد (+{days} روز).")

    # ════════════════════════════════
    #  📸 ذخیره خودکار فایل زمان‌دار
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زماندار_روشن$"))
    async def timed_media_on(event):
        record_cmd("زماندار_روشن")
        global _timed_media_active
        _timed_media_active = True
        set_setting("timed_media_active", "1")
        await safe_edit(event, "✅ ذخیره خودکار فایل زمان‌دار فعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زماندار_خاموش$"))
    async def timed_media_off(event):
        record_cmd("زماندار_خاموش")
        global _timed_media_active
        _timed_media_active = False
        set_setting("timed_media_active", "0")
        await safe_edit(event, "⛔ ذخیره خودکار فایل زمان‌دار غیرفعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زماندار_مقصد (.+)$"))
    async def timed_media_add_dest(event):
        record_cmd("زماندار_مقصد")
        dest = event.pattern_match.group(1).strip()
        label = dest
        if dest == "me":
            label = "Saved Messages"
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO timed_media_dests(dest,label,added) VALUES(?,?,?) "
                "ON CONFLICT(dest) DO UPDATE SET active=1",
                (dest, label, now_str())
            )
            conn.commit()
        await safe_edit(event, f"✅ مقصد «{label}» اضافه شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زماندار_لیست$"))
    async def timed_media_list_dests(event):
        record_cmd("زماندار_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM timed_media_dests WHERE active=1"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 مقصدی ثبت نشده!\nزماندار_مقصد [مقصد]"); return
        lines = [f"📍 {r['label']} ({r['dest']})" for r in rows]
        await safe_edit(event, box(f"📍 مقصدهای زمان‌دار ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^زماندار_حذف_مقصد (.+)$"))
    async def timed_media_del_dest(event):
        record_cmd("زماندار_حذف_مقصد")
        dest = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE timed_media_dests SET active=0 WHERE dest=?", (dest,))
            conn.commit()
        await safe_edit(event, f"✅ مقصد «{dest}» حذف شد.")

    @client.on(events.NewMessage(incoming=True))
    async def auto_save_timed_media(event):
        """ذخیره خودکار فایل‌های زمان‌دار"""
        try:
            if not _timed_media_active:
                return
            if setting("timed_media_active", "1") == "0":
                return
            msg = event.message
            if not msg:
                return
            # بررسی اینکه آیا پیام زمان‌دار است
            is_timed = False
            media_type = ""
            duration = 0
            try:
                if hasattr(msg, 'ttl_period') and msg.ttl_period:
                    is_timed = True
                    duration = msg.ttl_period
                # بررسی MessageMediaPhoto یا MessageMediaDocument با ttl
                if hasattr(msg, 'media') and msg.media:
                    from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
                    if isinstance(msg.media, MessageMediaPhoto):
                        if hasattr(msg.media, 'ttl_seconds') and msg.media.ttl_seconds:
                            is_timed = True
                            duration = msg.media.ttl_seconds
                            media_type = "photo"
                    elif isinstance(msg.media, MessageMediaDocument):
                        if hasattr(msg.media, 'ttl_seconds') and msg.media.ttl_seconds:
                            is_timed = True
                            duration = msg.media.ttl_seconds
                            media_type = "video"
            except Exception:
                pass
            if not is_timed:
                return

            # دریافت اطلاعات فرستنده
            try:
                sender = await event.get_sender()
                sender_id   = getattr(sender, 'id', 0)
                sender_name = ((getattr(sender,'first_name','') or '') +
                               ' ' + (getattr(sender,'last_name','') or '')).strip()
            except Exception:
                sender_id, sender_name = 0, "ناشناس"

            caption = msg.text or msg.message or ""

            # فایل ID برای جلوگیری از تکرار
            file_id = ""
            try:
                if hasattr(msg.media, 'photo') and msg.media.photo:
                    file_id = str(msg.media.photo.id)
                elif hasattr(msg.media, 'document') and msg.media.document:
                    file_id = str(msg.media.document.id)
                else:
                    file_id = str(msg.id)
            except Exception:
                file_id = str(msg.id)

            # بررسی تکراری نبودن
            with _db_lock:
                conn = get_conn()
                existing = conn.execute(
                    "SELECT id FROM timed_media_log WHERE file_id=? AND sender_id=?",
                    (file_id, sender_id)
                ).fetchone()
            if existing:
                return  # قبلاً ذخیره شده

            # دانلود فایل
            try:
                dl_suffix = "jpg" if media_type == "photo" else "mp4"
                dl_path = os.path.join(DL_DIR, f"timed_{sender_id}_{file_id[:8]}.{dl_suffix}")
                await client.download_media(msg.media, file=dl_path)
            except Exception:
                dl_path = ""

            # پیام اطلاعات
            me = await client.get_me()
            info_text = (
                f"📸 **فایل زمان‌دار دریافت شد**\n\n"
                f"👤 فرستنده: {sender_name}\n"
                f"🆔 آیدی: {sender_id}\n"
                f"📅 تاریخ: {now_str()}\n"
                f"⏱ مدت: {duration} ثانیه\n"
                f"📝 کپشن: {caption[:100] or '—'}"
            )

            # ارسال به Saved Messages
            saved_msg_id = 0
            try:
                if dl_path and os.path.exists(dl_path):
                    sent = await client.send_file(me.id, dl_path, caption=info_text)
                else:
                    sent = await client.send_message(me.id, info_text)
                saved_msg_id = sent.id
            except Exception as ex:
                logger.debug(f"timed media save: {ex}")

            # ارسال به مقصدهای اضافی
            with _db_lock:
                conn = get_conn()
                dests = conn.execute(
                    "SELECT dest FROM timed_media_dests WHERE active=1"
                ).fetchall()
            for d in dests:
                dest_val = d["dest"]
                try:
                    if dest_val == "me":
                        target = me.id
                    else:
                        target = int(dest_val) if dest_val.lstrip("-").isdigit() else dest_val
                    if dl_path and os.path.exists(dl_path):
                        await client.send_file(target, dl_path, caption=info_text)
                    else:
                        await client.send_message(target, info_text)
                except Exception as ex:
                    logger.debug(f"timed media dest {dest_val}: {ex}")

            # ثبت در لاگ
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT OR IGNORE INTO timed_media_log"
                    "(sender_id,sender_name,file_id,media_type,caption,duration,saved_msg_id,ts)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (sender_id, sender_name, file_id, media_type,
                     caption[:200], duration, saved_msg_id, now_str())
                )
                conn.commit()
            _bb_log("timed_media_saved", f"from={sender_id} type={media_type}")

        except Exception as ex:
            logger.debug(f"auto_save_timed_media: {ex}")

    # ════════════════════════════════
    #  🛡️ Self-Healing Engine
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سلامت$"))
    async def health_check(event):
        record_cmd("سلامت")
        issues = []
        fixes  = []
        # بررسی جداول DB
        required_tables = [
            "settings","contacts","store_products","store_orders",
            "crm_customers","virtual_pet","quests","boss_fight"
        ]
        with _db_lock:
            conn = get_conn()
            for tbl in required_tables:
                try:
                    conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
                except Exception:
                    issues.append(f"❌ جدول «{tbl}» آسیب دیده")
        # بررسی فایل‌های ضروری
        for dpath in [LOG_DIR, DL_DIR, BK_DIR]:
            if not os.path.exists(dpath):
                issues.append(f"❌ پوشه «{dpath}» موجود نیست")
                try:
                    os.makedirs(dpath, exist_ok=True)
                    fixes.append(f"✅ پوشه «{dpath}» ساخته شد")
                except Exception:
                    pass
        # بررسی آخرین خطاها
        with _db_lock:
            conn = get_conn()
            recent_errors = conn.execute(
                "SELECT COUNT(*) FROM health_log WHERE ts >= ? AND fixed=0",
                (jalali(),)
            ).fetchone()[0]

        status = "🟢 سالم" if not issues else f"🔴 {len(issues)} مشکل"
        lines = [
            f"وضعیت: {status}",
            f"خطاهای امروز: {recent_errors}",
            "━"*17,
        ] + issues + (["━"*17] + fixes if fixes else [])
        _health_log("health_check", f"issues={len(issues)}", not issues, "auto")
        await safe_edit(event, box("🩺 گزارش سلامت سیستم", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خودترمیم$"))
    async def self_heal(event):
        record_cmd("خودترمیم")
        fixed = []
        # بازسازی پوشه‌ها
        for dpath in [LOG_DIR, DL_DIR, BK_DIR, VLT_DIR, PLG_DIR]:
            if not os.path.exists(dpath):
                os.makedirs(dpath, exist_ok=True)
                fixed.append(f"📁 پوشه بازسازی شد: {dpath}")
        # VACUUM دیتابیس
        try:
            with _db_lock:
                conn = get_conn()
                conn.execute("PRAGMA integrity_check")
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            fixed.append("🗄️ دیتابیس بهینه و تعمیر شد")
        except Exception as ex:
            fixed.append(f"⚠️ خطا در DB: {ex}")
        # پاکسازی لاگ‌های قدیمی
        try:
            with _db_lock:
                conn = get_conn()
                cnt = conn.execute(
                    "DELETE FROM black_box WHERE id IN "
                    "(SELECT id FROM black_box ORDER BY id DESC LIMIT -1 OFFSET 5000)"
                ).rowcount
                conn.commit()
            fixed.append(f"🧹 {cnt} رکورد قدیمی Black Box پاک شد")
        except Exception:
            pass
        _health_log("self_heal", f"fixed={len(fixed)}", True, "manual")
        _bb_log("self_heal", f"fixed_count={len(fixed)}")
        await safe_edit(event, box("🔧 خودترمیم انجام شد", fixed or ["✅ همه چیز سالم بود!"]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^گزارش_سلامت$"))
    async def health_report(event):
        record_cmd("گزارش_سلامت")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM health_log ORDER BY id DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 گزارش سلامتی ثبت نشده!"); return
        lines = [
            f"{'✅' if r['fixed'] else '❌'} {r['issue_type']} — {r['ts'][:13]}"
            for r in rows
        ]
        await safe_edit(event, box(f"📋 تاریخچه سلامت ({len(rows)})", lines))

    # ════════════════════════════════
    #  📦 Black Box Recorder
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جعبه_سیاه(?: (\d+))?$"))
    async def black_box_show(event):
        record_cmd("جعبه_سیاه")
        limit = int(event.pattern_match.group(1) or 20)
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM black_box ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ رویدادی در جعبه سیاه ثبت نشده!"); return
        lines = [f"• {r['event_type']} | {r['detail'][:40]} | {r['ts'][:13]}" for r in rows]
        await safe_edit(event, box(f"⬛ جعبه سیاه ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جعبه_پاک$"))
    async def black_box_clear(event):
        record_cmd("جعبه_پاک")
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM black_box").rowcount
            conn.commit()
        await safe_edit(event, f"✅ {c} رکورد از جعبه سیاه پاک شد.")

    # ════════════════════════════════
    #  🤝 Smart Negotiator
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مذاکره (.+)$"))
    async def smart_negotiator(event):
        record_cmd("مذاکره")
        text = event.pattern_match.group(1).strip()
        tl   = text.lower()

        # تحلیل پیام
        intent = "neutral"
        discount_offer = 0
        response_text = ""

        # تشخیص قصد
        if any(w in tl for w in ["چقدر","قیمت","چند","هزینه","مبلغ"]):
            intent = "price_inquiry"
        if any(w in tl for w in ["گرون","ارزون‌تر","تخفیف","چونه","کمتر"]):
            intent = "bargaining"
        if any(w in tl for w in ["بد","راضی نیستم","مشکل","شکایت","اعتراض"]):
            intent = "complaint"
        if any(w in tl for w in ["خریدم","تمدید","میخرم","بگیرم"]):
            intent = "purchase"

        # پیشنهاد بر اساس intent
        if intent == "bargaining":
            discount_offer = random.randint(5, 15)
            response_text = (
                f"✅ با توجه به درخواست شما، می‌توانیم {discount_offer}٪ تخفیف بدیم.\n"
                f"💬 پیشنهادی برای پاسخ: «{discount_offer}٪ تخفیف ویژه برای شما در نظر گرفتم.»"
            )
        elif intent == "complaint":
            response_text = (
                "🤝 پیشنهادی برای پاسخ:\n"
                "«متأسفم که مشکلی پیش آمده. چطور می‌تونم کمک کنم تا حل بشه?»"
            )
        elif intent == "price_inquiry":
            response_text = (
                "💬 پیشنهادی برای پاسخ:\n"
                "«قیمت محصول ما کاملاً منطقیه و کیفیت بالاست. اگر سوال دارید راهنماییتون می‌کنم.»"
            )
        elif intent == "purchase":
            response_text = (
                "💬 پیشنهادی برای پاسخ:\n"
                "«ممنون از اعتمادتون! کد سفارش رو بفرستید تا سریع پردازش کنم.»"
            )
        else:
            response_text = "💬 پیشنهاد: پاسخ دوستانه و حرفه‌ای بدید."

        # تحلیل احتمال خرید
        buy_prob = 0
        if intent == "purchase":   buy_prob = 85
        elif intent == "bargaining": buy_prob = 60
        elif intent == "price_inquiry": buy_prob = 45
        else: buy_prob = 20

        await safe_edit(event, box("🤝 تحلیل مذاکره", [
            f"متن: {text[:60]}",
            f"قصد: {intent}",
            f"احتمال خرید: {buy_prob}٪",
            f"پیشنهاد تخفیف: {discount_offer}٪" if discount_offer else "پیشنهاد تخفیف: —",
            "━"*17,
            response_text,
        ]))

    # ════════════════════════════════
    #  🔍 Identity Verifier
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تشخیص_هویت (.+)$"))
    async def identity_verifier(event):
        record_cmd("تشخیص_هویت")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        uid = u.id

        score = 0
        reasons = []

        # بررسی سابقه در contacts
        with _db_lock:
            conn = get_conn()
            contact = conn.execute("SELECT * FROM contacts WHERE uid=?", (uid,)).fetchone()
            msg_hist = conn.execute(
                "SELECT COUNT(*) FROM chat_memory WHERE uid=?", (uid,)
            ).fetchone()[0]
            orders = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE uid=?", (uid,)
            ).fetchone()[0]

        if contact:
            score += 20
            reasons.append(f"✅ در مخاطبین: {contact['name'] or 'بدون نام'}")
        if msg_hist > 0:
            score += min(msg_hist * 2, 30)
            reasons.append(f"✅ {msg_hist} پیام در تاریخچه")
        if orders > 0:
            score += 30
            reasons.append(f"✅ {orders} سفارش قبلی")

        # آنالیز username
        uname = getattr(u, 'username', '') or ''
        if not uname:
            score -= 10
            reasons.append("⚠️ بدون یوزرنیم")
        else:
            # اگر username شبیه اسپمرها باشد
            if re.search(r'\d{6,}', uname):
                score -= 15
                reasons.append("⚠️ یوزرنیم مشکوک (اعداد زیاد)")

        # بررسی phone (اگر قابل دسترسی باشد)
        phone = getattr(u, 'phone', None)
        if phone:
            score += 10
            reasons.append("✅ شماره تلفن موجود")

        score = max(0, min(100, score))
        verdict = "🟢 قابل اعتماد" if score >= 60 else ("🟡 متوسط" if score >= 30 else "🔴 مشکوک")

        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO identity_checks(uid,result,score,ts) VALUES(?,?,?,?)",
                (uid, verdict, score, now_str())
            )
            conn.commit()

        await safe_edit(event, box(f"🔍 تشخیص هویت: {getattr(u,'first_name','?')}", [
            f"آیدی: {uid}",
            f"امتیاز اعتماد: {score}٪",
            f"وضعیت: {verdict}",
            "━"*17,
        ] + reasons))

    # ════════════════════════════════
    #  🚫 Airlock Mode
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ایرلوک_روشن$"))
    async def airlock_on(event):
        record_cmd("ایرلوک_روشن")
        global _airlock_active
        _airlock_active = True
        set_setting("airlock_active", "1")
        _bb_log("airlock_on", "فعال شد")
        await safe_edit(event, "🚫 **Airlock Mode** فعال شد!\nاتوماسیون‌ها محدود هستند.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ایرلوک_خاموش$"))
    async def airlock_off(event):
        record_cmd("ایرلوک_خاموش")
        global _airlock_active
        _airlock_active = False
        set_setting("airlock_active", "0")
        _bb_log("airlock_off", "غیرفعال شد")
        await safe_edit(event, "✅ **Airlock Mode** غیرفعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_ایرلوک$"))
    async def airlock_status(event):
        record_cmd("وضعیت_ایرلوک")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM airlock_events ORDER BY id DESC LIMIT 10"
            ).fetchall()
        active = _airlock_active or setting("airlock_active", "0") == "1"
        lines = [
            f"وضعیت: {'🚫 فعال' if active else '✅ غیرفعال'}",
            f"رویدادهای اخیر: {len(rows)}",
            "━"*17,
        ] + [f"• {r['trigger']}: {r['detail'][:40]}" for r in rows]
        await safe_edit(event, box("🚫 وضعیت Airlock", lines))

    # ════════════════════════════════
    #  🍯 Honeytrap Detector
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خطرسنج (.+)$"))
    async def honeytrap_detector(event):
        record_cmd("خطرسنج")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return

        risk_score = 0
        reasons = []

        # بررسی پروفایل
        uname = getattr(u, 'username', '') or ''
        fname = getattr(u, 'first_name', '') or ''
        bot   = getattr(u, 'bot', False)

        if bot:
            risk_score += 40
            reasons.append("⚠️ ربات است")

        # یوزرنیم مشکوک (اعداد زیاد، الگوی عجیب)
        if uname and re.search(r'\d{5,}', uname):
            risk_score += 20
            reasons.append("⚠️ یوزرنیم با اعداد زیاد")

        # بررسی سابقه در DB
        uid = u.id
        with _db_lock:
            conn = get_conn()
            contact = conn.execute("SELECT * FROM contacts WHERE uid=?", (uid,)).fetchone()
            # بررسی spam_log
            spam_rows = conn.execute(
                "SELECT SUM(count) FROM spam_log WHERE chat_id=?", (uid,)
            ).fetchone()[0] or 0

        if not contact:
            risk_score += 10
            reasons.append("⚠️ ناشناس — در مخاطبین نیست")

        if spam_rows > 0:
            risk_score += min(spam_rows * 5, 30)
            reasons.append(f"⚠️ {spam_rows} اسپم در تاریخچه")

        # بررسی اینکه آیا قبلاً تایید شده
        with _db_lock:
            conn = get_conn()
            orders = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE uid=?", (uid,)
            ).fetchone()[0]
        if orders > 0:
            risk_score -= 20
            reasons.append(f"✅ {orders} سفارش قبلی — قابل اعتماد")

        # اگر بدون عکس پروفایل (نمی‌توانیم در Telethon تشخیص دهیم بدون API call سنگین)
        risk_score = max(0, min(100, risk_score))
        verdict = "🔴 ریسک بالا" if risk_score >= 60 else ("🟡 ریسک متوسط" if risk_score >= 30 else "🟢 ریسک کم")

        await safe_edit(event, box(f"🍯 آنالیز ریسک: {fname}", [
            f"آیدی: {uid}",
            f"ریسک: {risk_score}٪",
            f"وضعیت: {verdict}",
            "━"*17,
        ] + reasons + [
            "━"*17,
            "پیشنهاد: " + (
                "🚫 احتیاط کامل" if risk_score >= 60
                else ("⚠️ بررسی بیشتر" if risk_score >= 30
                      else "✅ مشکلی نیست")
            )
        ]))

    # ════════════════════════════════
    #  🎨 Command Studio
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^استودیو$"))
    async def command_studio_help(event):
        record_cmd("استودیو")
        with _db_lock:
            conn = get_conn()
            cnt = conn.execute("SELECT COUNT(*) FROM custom_commands WHERE active=1").fetchone()[0]
        await safe_edit(event, box("🎨 Command Studio", [
            f"دستورات سفارشی فعال: {cnt}",
            "━"*17,
            "دستور_جدید [نام]|[عملیات]|[پاسخ]",
            "ویرایش_دستور [نام]|[عملیات]|[پاسخ]",
            "حذف_دستور [نام]",
            "لیست_دستورات",
            "━"*17,
            "مثال:",
            "دستور_جدید سلام|echo|سلام خوش آمدی!",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستور_جدید (.+)\|(.+)\|(.+)$"))
    async def custom_cmd_add(event):
        record_cmd("دستور_جدید")
        name   = event.pattern_match.group(1).strip()
        action = event.pattern_match.group(2).strip()
        reply  = event.pattern_match.group(3).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO custom_commands(name,action,reply,ts) VALUES(?,?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET action=excluded.action, reply=excluded.reply",
                (name[:50], action[:200], reply[:500], now_str())
            )
            conn.commit()
        await safe_edit(event, f"✅ دستور «{name}» ثبت شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^لیست_دستورات$"))
    async def custom_cmd_list(event):
        record_cmd("لیست_دستورات")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM custom_commands WHERE active=1 ORDER BY name"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 دستور سفارشی ثبت نشده!\nدستور_جدید [نام]|[عملیات]|[پاسخ]"); return
        lines = [f"• {r['name']} → {r['reply'][:40]}" for r in rows]
        await safe_edit(event, box(f"🎨 دستورات سفارشی ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^حذف_دستور (.+)$"))
    async def custom_cmd_del(event):
        record_cmd("حذف_دستور")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("UPDATE custom_commands SET active=0 WHERE name=?", (name,))
            conn.commit()
        await safe_edit(event, f"✅ دستور «{name}» حذف شد." if c.rowcount else "❌ پیدا نشد!")

    # هندلر دستورات سفارشی
    @client.on(events.NewMessage(outgoing=True))
    async def custom_cmd_executor(event):
        """اجرای دستورات سفارشی از Command Studio"""
        try:
            text = (event.text or "").strip()
            if not text:
                return
            with _db_lock:
                conn = get_conn()
                cmd = conn.execute(
                    "SELECT * FROM custom_commands WHERE name=? AND active=1",
                    (text,)
                ).fetchone()
            if not cmd:
                return
            action = cmd["action"]
            reply  = cmd["reply"]
            if action == "echo":
                await safe_edit(event, reply)
            elif action == "delete":
                await event.delete()
            else:
                await safe_edit(event, reply)
            _bb_log("custom_cmd_exec", f"name={text}")
        except Exception:
            pass

    # ════════════════════════════════
    #  💧 Invisible Watermark Engine
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^واترمارک_روشن$"))
    async def wm_on(event):
        record_cmd("واترمارک_روشن")
        global _wm_active
        _wm_active = True
        set_setting("wm_active", "1")
        await safe_edit(event, "✅ واترمارک نامرئی فعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^واترمارک_خاموش$"))
    async def wm_off(event):
        record_cmd("واترمارک_خاموش")
        global _wm_active
        _wm_active = False
        set_setting("wm_active", "0")
        await safe_edit(event, "⛔ واترمارک نامرئی غیرفعال شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بررسی_واترمارک (.+)$"))
    async def wm_check(event):
        record_cmd("بررسی_واترمارک")
        wm_code = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            row = conn.execute(
                "SELECT * FROM watermark_registry WHERE wm_code=?", (wm_code,)
            ).fetchone()
        if not row:
            await safe_edit(event, f"❌ واترمارک «{wm_code}» شناسایی نشد!"); return
        await safe_edit(event, box("💧 واترمارک شناسایی شد", [
            f"آیدی دریافت‌کننده: {row['uid']}",
            f"نوع فایل: {row['file_type']}",
            f"تاریخ: {row['ts'][:16]}",
            f"هش فایل: {row['file_hash'][:20]}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^گزارش_واترمارک$"))
    async def wm_report(event):
        record_cmd("گزارش_واترمارک")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM watermark_registry ORDER BY id DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 واترمارکی ثبت نشده!"); return
        lines = [f"💧 uid:{r['uid']} | {r['file_type']} | {r['ts'][:13]}" for r in rows]
        await safe_edit(event, box(f"💧 واترمارک‌های ثبت‌شده ({len(rows)})", lines))

    # ════════════════════════════════
    #  📊 آمار اشتراک‌ها (بهبود)
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^آمار_اشتراک_v8$"))
    async def subscription_stats_v8(event):
        record_cmd("آمار_اشتراک_v8")
        today = jalali()
        with _db_lock:
            conn = get_conn()
            total   = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
            active  = conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE end_date >= ?", (today,)
            ).fetchone()[0]
            expired = total - active
            expiring_soon = conn.execute(
                "SELECT COUNT(*) FROM subscriptions WHERE end_date >= ? AND reminded=0",
                (today,)
            ).fetchone()[0]
        await safe_edit(event, box("📊 آمار اشتراک‌ها", [
            f"کل اشتراک‌ها: {total}",
            f"فعال: {active}",
            f"منقضی: {expired}",
            f"رو به انقضا (یادآوری نشده): {expiring_soon}",
        ]))

    # ════════════════════════════════
    #  🎮 بهبود بازی‌ها (Fix Buttons)
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بازی_حیوان$"))
    async def game_pet_fixed(event):
        record_cmd("بازی_حیوان")
        try:
            with _db_lock:
                conn = get_conn()
                pet_rows = conn.execute("SELECT key,value FROM virtual_pet").fetchall()
            pet = {r["key"]: r["value"] for r in pet_rows} if pet_rows else {}
            name  = pet.get("name", "حیوان")
            level = pet.get("level", "1")
            hp    = pet.get("hunger", "50")
            happy = pet.get("happy",  "50")
            await safe_edit(event, box(f"🐾 {name}", [
                f"سطح: {level}",
                f"گرسنگی: {hp}/100",
                f"شادی: {happy}/100",
                "━"*17,
                "مراقبت غذا — آب — بازی",
                "غذا_بده — آب_بده — باهاش_بازی_کن",
            ]))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^جعبه_راز$"))
    async def mystery_box_fixed(event):
        record_cmd("جعبه_راز")
        try:
            coins = 50
            rewards = [
                ("💰 ۱۰۰ سکه", 100),
                ("⭐ ۵۰ XP", 50),
                ("💎 آیتم نادر", 200),
                ("🎁 کوپن ۵٪", 0),
                ("🪙 ۲۵ سکه", 25),
            ]
            rw_name, rw_val = random.choice(rewards)
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO mystery_boxes(opened,reward,ts) VALUES(1,?,?)",
                    (rw_name, now_str())
                )
                conn.commit()
            if rw_val > 0:
                _add_coins(rw_val, f"جعبه راز: {rw_name}")
            _bb_log("mystery_box", f"reward={rw_name}")
            await safe_edit(event, box("🎁 جعبه راز باز شد!", [
                f"جایزه: {rw_name}",
                f"سکه دریافتی: {rw_val}" if rw_val > 0 else "",
            ]))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مبارزه_باس$"))
    async def boss_fight_fixed(event):
        record_cmd("مبارزه_باس")
        try:
            with _db_lock:
                conn = get_conn()
                boss_rows = conn.execute("SELECT key,value FROM boss_fight").fetchall()
            boss = {r["key"]: r["value"] for r in boss_rows}
            if not boss.get("name"):
                # ایجاد باس پیش‌فرض
                with _db_lock:
                    conn = get_conn()
                    for k, v in [("name","اژدها"),("hp","1000"),("max_hp","1000"),("level","1")]:
                        conn.execute(
                            "INSERT INTO boss_fight(key,value) VALUES(?,?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (k, v)
                        )
                    conn.commit()
                boss = {"name":"اژدها","hp":"1000","max_hp":"1000","level":"1"}
            dmg = random.randint(50, 150)
            hp  = max(0, int(boss.get("hp","1000")) - dmg)
            with _db_lock:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO boss_fight(key,value) VALUES('hp',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (str(hp),)
                )
                conn.commit()
            if hp <= 0:
                reward = 500
                _add_coins(reward, "باس کشته شد!")
                result = f"🏆 باس کشته شد! +{reward} سکه!"
                with _db_lock:
                    conn = get_conn()
                    conn.execute("INSERT INTO boss_fight(key,value) VALUES('hp','1000') "
                                 "ON CONFLICT(key) DO UPDATE SET value='1000'", ())
                    conn.commit()
            else:
                hp_pct = int(hp / int(boss.get("max_hp","1000")) * 100)
                bar = "█" * (hp_pct//10) + "░" * (10 - hp_pct//10)
                result = f"⚔️ {dmg} آسیب زدی!\n{bar} {hp_pct}٪"
            _bb_log("boss_fight", f"dmg={dmg} hp_left={hp}")
            await safe_edit(event, box(f"👹 مبارزه با {boss.get('name','باس')}", [
                result,
                f"HP باقی‌مانده: {hp}",
            ]))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^درخت_مهارت$"))
    async def skill_tree_fixed(event):
        record_cmd("درخت_مهارت")
        try:
            with _db_lock:
                conn = get_conn()
                skills = conn.execute("SELECT * FROM skill_tree ORDER BY level DESC").fetchall()
            if not skills:
                # مهارت‌های پیش‌فرض
                defaults = [
                    ("تجارت", 0, 5, 0),
                    ("جنگیدن", 0, 5, 0),
                    ("دانش", 0, 5, 0),
                    ("سرعت", 0, 5, 0),
                ]
                with _db_lock:
                    conn = get_conn()
                    for sk, lv, mx, xp in defaults:
                        conn.execute(
                            "INSERT OR IGNORE INTO skill_tree(skill,level,max_level,xp) VALUES(?,?,?,?)",
                            (sk, lv, mx, xp)
                        )
                    conn.commit()
                    skills = conn.execute("SELECT * FROM skill_tree").fetchall()
            lines = [
                f"{'⭐'*r['level']}{'○'*(r['max_level']-r['level'])} {r['skill']} Lv.{r['level']}/{r['max_level']}"
                for r in skills
            ]
            await safe_edit(event, box("🌳 درخت مهارت", lines, "مهارت_ارتقا [نام]"))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مهارت_ارتقا (.+)$"))
    async def skill_upgrade(event):
        record_cmd("مهارت_ارتقا")
        skill_name = event.pattern_match.group(1).strip()
        cost = 100
        try:
            if _get_coins() < cost:
                await safe_edit(event, f"❌ {cost} سکه لازم!"); return
            with _db_lock:
                conn = get_conn()
                sk = conn.execute(
                    "SELECT * FROM skill_tree WHERE skill=?", (skill_name,)
                ).fetchone()
            if not sk:
                await safe_edit(event, f"❌ مهارت «{skill_name}» پیدا نشد!"); return
            if sk["level"] >= sk["max_level"]:
                await safe_edit(event, f"⚠️ «{skill_name}» به حداکثر سطح رسیده!"); return
            new_level = sk["level"] + 1
            _add_coins(-cost, f"ارتقای مهارت: {skill_name}")
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE skill_tree SET level=? WHERE skill=?", (new_level, skill_name))
                conn.commit()
            await safe_edit(event, f"⭐ «{skill_name}» به سطح {new_level} ارتقا یافت! (-{cost} سکه)")
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماموریت_فعال$"))
    async def active_quests(event):
        record_cmd("ماموریت_فعال")
        try:
            with _db_lock:
                conn = get_conn()
                rows = conn.execute(
                    "SELECT * FROM quests WHERE active=1 AND done=0 ORDER BY id DESC LIMIT 10"
                ).fetchall()
            if not rows:
                await safe_edit(event, "📭 هیچ ماموریت فعالی نیست!\nماموریت_جدید [عنوان]|[هدف]|[جایزه]"); return
            lines = []
            for r in rows:
                pct = min(100, int(r["current"] / max(r["target"],1) * 100))
                bar = "█"*(pct//10) + "░"*(10-pct//10)
                lines.append(f"📋 {r['title']}\n   {bar} {pct}٪ ({r['current']}/{r['target']}) 🎁{r['reward']}")
            await safe_edit(event, box(f"📋 ماموریت‌های فعال ({len(rows)})", lines))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا: {ex}")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ماموریت_جدید (.+)\|(\d+)\|(\d+)$"))
    async def quest_new(event):
        record_cmd("ماموریت_جدید")
        title  = event.pattern_match.group(1).strip()
        target = int(event.pattern_match.group(2))
        reward = int(event.pattern_match.group(3))
        with _db_lock:
            conn = get_conn()
            qid = conn.execute(
                "INSERT INTO quests(title,target,reward,active,ts) VALUES(?,?,?,1,?)",
                (title[:100], target, reward, now_str())
            ).lastrowid
            conn.commit()
        await safe_edit(event, f"✅ ماموریت «{title}» ثبت شد (id:{qid}، هدف:{target}، جایزه:{reward})")

    # ════════════════════════════════
    #  🏪 تایید سفارش با ارسال آموزش
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^سفارش_تایید_v8 (.+)$"))
    async def store_order_approve_v8(event):
        """تایید سفارش V8 — با ارسال آموزش محصول"""
        record_cmd("سفارش_تایید_v8")
        oid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute("SELECT * FROM store_orders WHERE order_uid=?", (oid,)).fetchone()
        if not order:
            await safe_edit(event, f"❌ سفارش «{oid}» پیدا نشد!"); return
        if order["status"] == "approved":
            await safe_edit(event, "⚠️ سفارش قبلاً تایید شده!"); return

        # دریافت محصول و آموزش
        with _db_lock:
            conn = get_conn()
            prod = conn.execute(
                "SELECT * FROM store_products WHERE id=?", (order["product_id"],)
            ).fetchone()
            # دریافت محتوا (config یا file)
            cfg_item = conn.execute(
                "SELECT * FROM store_configs WHERE product_id=? AND sold=0 LIMIT 1",
                (order["product_id"],)
            ).fetchone()

        if not prod:
            await safe_edit(event, "❌ محصول پیدا نشد!"); return

        ptype = prod.get("product_type", "config") if prod else "config"

        # به‌روزرسانی وضعیت
        with _db_lock:
            conn = get_conn()
            if cfg_item:
                conn.execute("UPDATE store_configs SET sold=1, order_id=? WHERE id=?",
                             (order["id"], cfg_item["id"]))
            conn.execute("UPDATE store_orders SET status='approved', config_id=? WHERE order_uid=?",
                         (cfg_item["id"] if cfg_item else 0, oid))
            conn.commit()

        # ارسال محصول به مشتری
        try:
            main_text = (
                f"✅ سفارش شما تایید شد!\n\n"
                f"📦 محصول: {order['product_name']}\n"
                f"🆔 کد سفارش: {oid}\n"
            )
            if ptype == "config" and cfg_item:
                await client.send_message(order["uid"],
                    main_text + f"\n🔑 محتوا:\n`{cfg_item['content']}`")
            elif prod.get("file_path") and os.path.exists(prod["file_path"]):
                await client.send_file(order["uid"], prod["file_path"], caption=main_text)
            else:
                await client.send_message(order["uid"], main_text)

            # ارسال آموزش
            tutorial_text = prod.get("tutorial_text", "")
            tutorial_link = prod.get("tutorial_link", "")
            if tutorial_text or tutorial_link:
                tut_msg = "📚 **راهنمای استفاده:**\n\n"
                if tutorial_text:
                    tut_msg += tutorial_text[:1500] + "\n"
                if tutorial_link:
                    tut_msg += f"\n🔗 لینک آموزشی: {tutorial_link}"
                await client.send_message(order["uid"], tut_msg)

        except Exception as ex:
            logger.warning(f"V8 approve send: {ex}")

        # به‌روزرسانی CRM
        try:
            _crm_update(order["uid"], order["price"], order["product_name"])
        except Exception:
            pass

        _bb_log("order_approved_v8", f"oid={oid} uid={order['uid']}")
        await safe_edit(event, box("✅ سفارش V8 تایید شد", [
            f"سفارش: {oid}",
            f"مشتری: {order['name']} ({order['uid']})",
            f"محصول: {order['product_name']}",
            f"نوع: {ptype}",
            "آموزش ارسال شد ✅" if prod.get("tutorial_text") or prod.get("tutorial_link") else "آموزش: —",
        ]))

    # ════════════════════════════════
    #  📋 دستورات جدید CRM
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^crm_برچسب (.+)\|(.+)$"))
    async def crm_add_tag(event):
        record_cmd("crm_برچسب")
        arg = event.pattern_match.group(1).strip()
        tag = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT tags FROM crm_customers WHERE uid=?", (uid,)).fetchone()
            existing_tags = json.loads(row["tags"] if row and row["tags"] else "[]")
            if tag not in existing_tags:
                existing_tags.append(tag)
            conn.execute(
                "INSERT INTO crm_customers(uid,tags) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET tags=excluded.tags",
                (uid, json.dumps(existing_tags, ensure_ascii=False))
            )
            conn.commit()
        await safe_edit(event, f"✅ برچسب «{tag}» به مشتری {uid} اضافه شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^crm_شهر (.+)\|(.+)$"))
    async def crm_set_city(event):
        record_cmd("crm_شهر")
        arg  = event.pattern_match.group(1).strip()
        city = event.pattern_match.group(2).strip()
        u = await resolve_user(client, event, arg)
        uid = u.id if u else (int(arg) if arg.lstrip("-").isdigit() else None)
        if not uid:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO crm_customers(uid,city) VALUES(?,?) "
                "ON CONFLICT(uid) DO UPDATE SET city=excluded.city",
                (uid, city[:50])
            )
            conn.commit()
        await safe_edit(event, f"✅ شهر مشتری {uid} ثبت شد.")

    # ════════════════════════════════
    #  ℹ️ درباره V8
    # ════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^درباره_v8$"))
    async def about_v8(event):
        record_cmd("درباره_v8")
        await safe_edit(event, box("💎 ONYX SELF V8 PRO'S", [
            "نسخه: 8.0.0",
            "ساخته شده روی V7",
            "━"*17,
            "✅ فروشگاه چند‌نوعی",
            "✅ آموزش محصول",
            "✅ CRM حرفه‌ای",
            "✅ سیستم اشتراک و تمدید",
            "✅ ذخیره فایل زمان‌دار",
            "✅ Self-Healing Engine",
            "✅ Black Box Recorder",
            "✅ Smart Negotiator",
            "✅ Identity Verifier",
            "✅ Airlock Mode",
            "✅ Honeytrap Detector",
            "✅ Command Studio",
            "✅ Invisible Watermark",
            "━"*17,
            WATERMARK,
        ]))



# ══════════════════════════════════════════════════════
#  ═══  V9 CORE SYSTEMS  ═══
# ══════════════════════════════════════════════════════

# ── متغیرهای Global V9 ──────────────────────────
_airlock_v9: bool = False
_context_v9: dict = {}   # {entity_id: {type, data}}
_radar_score_cache: dict = {}

def _bb_log_v9(event: str, detail: str = "", level: str = "info") -> None:
    """Black Box V9 — ثبت رویداد"""
    try:
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO black_box(event,detail,level,ts) VALUES(?,?,?,?)",
                (event[:100], detail[:500], level, now_str())
            )
            conn.commit()
    except Exception:
        pass

def _get_product_knowledge(product_id: int) -> dict:
    """دریافت Context محصول"""
    with _db_lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM product_knowledge WHERE product_id=?", (product_id,)
        ).fetchone()
    if row:
        return dict(row)
    # اگر Knowledge نبود، از اطلاعات پایه محصول استفاده کن
    with _db_lock:
        conn = get_conn()
        prod = conn.execute(
            "SELECT * FROM store_products WHERE id=?", (product_id,)
        ).fetchone()
    if prod:
        return {
            "product_id": product_id,
            "product_name": prod["name"],
            "product_type": prod.get("product_type", "عمومی"),
            "description": prod["description"] or "",
            "features": "", "benefits": "", "rules": "", "faq": "",
            "sales_text": "", "delivery_text": "", "restrictions": "",
            "keywords": "", "ai_context": "",
        }
    return {}

def _set_product_knowledge(pid: int, data: dict) -> None:
    """ذخیره/به‌روزرسانی Context محصول"""
    with _db_lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO product_knowledge(
                product_id,product_name,product_type,description,features,benefits,
                rules,faq,sales_text,delivery_text,restrictions,keywords,ai_context,updated
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(product_id) DO UPDATE SET
                product_name=excluded.product_name,
                product_type=excluded.product_type,
                description=excluded.description,
                features=excluded.features,
                benefits=excluded.benefits,
                rules=excluded.rules,
                faq=excluded.faq,
                sales_text=excluded.sales_text,
                delivery_text=excluded.delivery_text,
                restrictions=excluded.restrictions,
                keywords=excluded.keywords,
                ai_context=excluded.ai_context,
                updated=excluded.updated
        """, (
            pid,
            data.get("product_name","")[:200],
            data.get("product_type","عمومی")[:50],
            data.get("description","")[:500],
            data.get("features","")[:500],
            data.get("benefits","")[:500],
            data.get("rules","")[:500],
            data.get("faq","")[:1000],
            data.get("sales_text","")[:500],
            data.get("delivery_text","")[:500],
            data.get("restrictions","")[:300],
            data.get("keywords","")[:200],
            data.get("ai_context","")[:1000],
            now_str()
        ))
        conn.commit()

def _build_product_context_prompt(product_id: int) -> str:
    """ساخت Prompt برای هوش مصنوعی بر اساس Context محصول"""
    pk = _get_product_knowledge(product_id)
    if not pk:
        return ""
    lines = [f"PRODUCT: {pk.get('product_name','')}"]
    if pk.get('product_type'):
        lines.append(f"TYPE: {pk['product_type']}")
    if pk.get('description'):
        lines.append(f"DESCRIPTION: {pk['description']}")
    if pk.get('features'):
        lines.append(f"FEATURES: {pk['features']}")
    if pk.get('benefits'):
        lines.append(f"BENEFITS: {pk['benefits']}")
    if pk.get('rules'):
        lines.append(f"RULES: {pk['rules']}")
    if pk.get('restrictions'):
        lines.append(f"RESTRICTIONS (never mention): {pk['restrictions']}")
    if pk.get('ai_context'):
        lines.append(f"AI_CONTEXT: {pk['ai_context']}")
    return "\n".join(lines)

def _get_blacklist_level(uid: int) -> str:
    """سطح ریسک کاربر"""
    with _db_lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT level FROM blacklist_intel WHERE uid=?", (uid,)
        ).fetchone()
    return row["level"] if row else "normal"

def _set_blacklist_level(uid: int, level: str, reason: str = "") -> None:
    """تنظیم سطح ریسک"""
    VALID_LEVELS = ["trusted","normal","suspicious","restricted","blocked"]
    if level not in VALID_LEVELS:
        return
    with _db_lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO blacklist_intel(uid,level,reason,score,ts) VALUES(?,?,?,0,?)
            ON CONFLICT(uid) DO UPDATE SET level=excluded.level,reason=excluded.reason,ts=excluded.ts
        """, (uid, level, reason[:200], now_str()))
        conn.commit()

def _log_event_replay(entity_id: str, event: str, data: str = "") -> None:
    """ثبت رویداد برای Event Replay"""
    with _db_lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO event_replay(entity_id,event,data,ts) VALUES(?,?,?,?)",
            (entity_id[:100], event[:100], data[:500], now_str())
        )
        conn.commit()

def _generate_wm_fingerprint(uid: int, order_uid: str) -> str:
    """تولید اثر انگشت واترمارک برای فایل/محتوا"""
    raw = f"WM-{uid}-{order_uid}-{int(_time.time())}"
    return base64.b64encode(raw.encode()).decode()[:32]


def _register_v9(client):
    """ثبت تمام هندلرهای V9 — قابلیت‌های جدید"""

    # ════════════════════════════════════════
    #  📚 Product Knowledge / Context System
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^دانش_محصول (\d+)$"))
    async def show_product_knowledge(event):
        """نمایش Context/Knowledge یک محصول"""
        record_cmd("دانش_محصول")
        pid = int(event.pattern_match.group(1))
        pk = _get_product_knowledge(pid)
        if not pk or not pk.get("product_name"):
            await safe_edit(event, f"❌ Context برای محصول {pid} تعریف نشده!\nاز دانش_ثبت استفاده کن.")
            return
        lines = [
            f"📦 نام: {pk.get('product_name','-')}",
            f"🏷 نوع: {pk.get('product_type','-')}",
            f"📝 توضیح: {(pk.get('description','') or '-')[:80]}",
            f"✨ ویژگی‌ها: {(pk.get('features','') or '-')[:80]}",
            f"🎯 مزایا: {(pk.get('benefits','') or '-')[:60]}",
            f"📋 قوانین: {(pk.get('rules','') or '-')[:60]}",
            f"❓ FAQ: {(pk.get('faq','') or '-')[:60]}",
            f"💬 متن فروش: {(pk.get('sales_text','') or '-')[:60]}",
            f"📤 متن تحویل: {(pk.get('delivery_text','') or '-')[:60]}",
            f"🚫 محدودیت: {(pk.get('restrictions','') or '-')[:60]}",
            f"🔑 کلیدواژه: {(pk.get('keywords','') or '-')[:60]}",
            f"🤖 AI Context: {(pk.get('ai_context','') or '-')[:80]}",
            f"🕐 به‌روز: {(pk.get('updated','') or '-')[:16]}",
        ]
        await safe_edit(event, box(f"📚 دانش محصول {pid}", lines))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^دانش_ثبت (\d+)\|(.+)\|(.+)$"))
    async def set_product_knowledge_cmd(event):
        """دانش_ثبت [id]|[فیلد]|[مقدار]"""
        record_cmd("دانش_ثبت")
        pid   = int(event.pattern_match.group(1))
        field = event.pattern_match.group(2).strip()
        value = event.pattern_match.group(3).strip()
        FIELDS = {
            "نام": "product_name", "نوع": "product_type", "توضیح": "description",
            "ویژگی": "features", "ویژگی‌ها": "features", "مزایا": "benefits",
            "قوانین": "rules", "faq": "faq", "FAQ": "faq",
            "متن_فروش": "sales_text", "متن_تحویل": "delivery_text",
            "محدودیت": "restrictions", "کلیدواژه": "keywords",
            "ai_context": "ai_context", "AI_CONTEXT": "ai_context",
        }
        db_field = FIELDS.get(field, field)
        pk = _get_product_knowledge(pid)
        if not pk:
            # جستجو از store_products
            with _db_lock:
                conn = get_conn()
                prod = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
            if prod:
                pk = {"product_id": pid, "product_name": prod["name"],
                      "product_type": "عمومی", "description": prod["description"] or ""}
            else:
                pk = {"product_id": pid, "product_name": f"محصول {pid}"}
        pk[db_field] = value
        pk["product_id"] = pid
        _set_product_knowledge(pid, pk)
        _bb_log_v9("product_knowledge_set", f"pid={pid} field={db_field}")
        await safe_edit(event, box("✅ دانش محصول به‌روز شد", [
            f"محصول: {pid}",
            f"فیلد: {field} ({db_field})",
            f"مقدار: {value[:60]}",
            "مشاهده: دانش_محصول [id]",
        ]))

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^دانش_کامل (\d+)$"))
    async def set_product_knowledge_full(event):
        """دانش_کامل [id] — نمایش فرمت کامل برای ویرایش"""
        record_cmd("دانش_کامل")
        pid = int(event.pattern_match.group(1))
        pk = _get_product_knowledge(pid)
        template = (
            f"─── Product Knowledge #{pid} ───\n"
            f"PRODUCT: {pk.get('product_name','نام محصول')}\n"
            f"TYPE: {pk.get('product_type','نوع محصول')}\n"
            f"DESCRIPTION: {pk.get('description','توضیح محصول')}\n"
            f"FEATURES: {pk.get('features','ویژگی‌ها')}\n"
            f"BENEFITS: {pk.get('benefits','مزایا')}\n"
            f"PRICE: [از دیتابیس]\n"
            f"RULES: {pk.get('rules','قوانین فروش')}\n"
            f"FAQ: {pk.get('faq','سوالات متداول')}\n"
            f"SALES_TEXT: {pk.get('sales_text','متن فروش')}\n"
            f"DELIVERY_TEXT: {pk.get('delivery_text','متن تحویل')}\n"
            f"RESTRICTIONS: {pk.get('restrictions','موارد ممنوع')}\n"
            f"KEYWORDS: {pk.get('keywords','کلیدواژه‌ها')}\n"
            f"AI_CONTEXT: {pk.get('ai_context','اطلاعات برای هوش مصنوعی')}"
        )
        await safe_edit(event, f"```\n{template}\n```\n\n"
                               f"برای ثبت هر فیلد:\n"
                               f"دانش_ثبت {pid}|[فیلد]|[مقدار]")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دانش_لیست$"))
    async def list_product_knowledge(event):
        """لیست همه محصولات با Knowledge"""
        record_cmd("دانش_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT pk.*, sp.name as sp_name FROM product_knowledge pk "
                "LEFT JOIN store_products sp ON pk.product_id=sp.id ORDER BY pk.product_id"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ Knowledge‌ای ثبت نشده!\nدانش_ثبت [id]|[فیلد]|[مقدار]")
            return
        lines = []
        for r in rows:
            name = r["product_name"] or r["sp_name"] or f"#{r['product_id']}"
            has_ai = "🤖" if r["ai_context"] else "  "
            has_res = "🚫" if r["restrictions"] else "  "
            lines.append(f"{has_ai}{has_res} {r['product_id']}. {name[:30]} | {r['product_type']}")
        await safe_edit(event, box(f"📚 Knowledge محصولات ({len(rows)})", lines,
                                   "مشاهده: دانش_محصول [id]"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دانش_حذف (\d+)$"))
    async def delete_product_knowledge(event):
        """حذف Knowledge یک محصول"""
        record_cmd("دانش_حذف")
        pid = int(event.pattern_match.group(1))
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM product_knowledge WHERE product_id=?", (pid,))
            conn.commit()
        msg = f"✅ Knowledge محصول {pid} حذف شد." if c.rowcount else f"❌ Knowledge برای {pid} نبود."
        await safe_edit(event, msg)

    # ════════════════════════════════════════
    #  🛡️ 1. Self-Healing Engine
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خودترمیم$"))
    async def self_healing_report(event):
        """نمایش گزارش Self-Healing"""
        record_cmd("خودترمیم")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM black_box ORDER BY id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "✅ هیچ خطای ثبت‌شده‌ای نیست!")
            return
        error_rows = [r for r in rows if r["level"] in ("error","critical")]
        info_rows  = [r for r in rows if r["level"] == "info"]
        lines = [
            f"❌ خطاها: {len(error_rows)}",
            f"ℹ️ رویدادها: {len(info_rows)}",
            "── آخرین ۱۰ رویداد ──",
        ]
        for r in rows[:10]:
            icon = "❌" if r["level"] == "error" else ("⚠️" if r["level"] == "warning" else "ℹ️")
            lines.append(f"{icon} {r['ts'][:13]} | {r['event'][:30]}")
        await safe_edit(event, box("🛡️ Self-Healing Report", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^خطاهای_سیستم$"))
    async def system_errors(event):
        """نمایش خطاهای اخیر از Black Box"""
        record_cmd("خطاهای_سیستم")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM black_box WHERE level IN ('error','critical','warning') "
                "ORDER BY id DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "✅ هیچ خطایی ثبت نشده!")
            return
        lines = [f"{'❌' if r['level']=='error' else '⚠️'} {r['ts'][:13]} | {r['event'][:30]}: {r['detail'][:40]}"
                 for r in rows]
        await safe_edit(event, box(f"❌ خطاهای سیستم ({len(rows)})", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^پاک_بلک‌باکس$"))
    async def clear_black_box(event):
        """پاک‌کردن Black Box"""
        record_cmd("پاک_بلک‌باکس")
        with _db_lock:
            conn = get_conn()
            cnt = conn.execute("SELECT COUNT(*) FROM black_box").fetchone()[0]
            conn.execute("DELETE FROM black_box")
            conn.commit()
        await safe_edit(event, f"✅ {cnt} رویداد از Black Box پاک شد.")

    # ════════════════════════════════════════
    #  💼 2. Smart Negotiator
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^مذاکره (\d+)(?: (.+))?$"))
    async def smart_negotiator(event):
        """مذاکره [product_id] [درصد_تخفیف_پیشنهادی]"""
        record_cmd("مذاکره")
        pid = int(event.pattern_match.group(1))
        discount_pct = 0
        if event.pattern_match.group(2):
            try:
                discount_pct = int(event.pattern_match.group(2))
            except Exception:
                pass
        with _db_lock:
            conn = get_conn()
            prod = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
        if not prod:
            await safe_edit(event, "❌ محصول پیدا نشد!"); return
        pk = _get_product_knowledge(pid)
        price = prod["price"]
        # محاسبه پیشنهاد هوشمند
        max_discount = 20  # حداکثر تخفیف پیش‌فرض
        try:
            rules_text = pk.get("rules","") or ""
            if "تخفیف" in rules_text:
                import re as _re
                m = _re.search(r"تخفیف[:\s]*(\d+)%", rules_text)
                if m:
                    max_discount = int(m.group(1))
        except Exception:
            pass
        if discount_pct > max_discount:
            recommended = max_discount
            verdict = "❌ بیش از حد مجاز"
        elif discount_pct > 0:
            recommended = discount_pct
            verdict = "✅ قابل قبول"
        else:
            recommended = 0
            verdict = "💰 بدون تخفیف"
        final_price = int(price * (1 - recommended/100))
        # ثبت در negotiation_log
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO negotiation_log(uid,product_id,offer,counter,outcome,ts) VALUES(?,?,?,?,?,?)",
                (0, pid, discount_pct, recommended, verdict, now_str())
            )
            conn.commit()
        _bb_log_v9("negotiation", f"pid={pid} disc={discount_pct}%→{recommended}%")
        await safe_edit(event, box("💼 Smart Negotiator", [
            f"محصول: {prod['name'][:40]}",
            f"نوع: {pk.get('product_type','عمومی')}",
            f"قیمت اصلی: {price:,} تومان",
            f"تخفیف پیشنهادی: {discount_pct}%",
            f"حداکثر مجاز: {max_discount}%",
            f"تخفیف توصیه‌شده: {recommended}%",
            f"قیمت نهایی: {final_price:,} تومان",
            f"حکم: {verdict}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تاریخچه_مذاکره(?: (\d+))?$"))
    async def negotiation_history(event):
        record_cmd("تاریخچه_مذاکره")
        pid_arg = event.pattern_match.group(1)
        with _db_lock:
            conn = get_conn()
            if pid_arg:
                rows = conn.execute(
                    "SELECT * FROM negotiation_log WHERE product_id=? ORDER BY id DESC LIMIT 10",
                    (int(pid_arg),)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM negotiation_log ORDER BY id DESC LIMIT 15"
                ).fetchall()
        if not rows:
            await safe_edit(event, "📭 تاریخچه مذاکره‌ای نیست!"); return
        lines = [f"• {r['ts'][:13]} | pid:{r['product_id']} | {r['offer']}%→{r['counter']}% | {r['outcome']}"
                 for r in rows]
        await safe_edit(event, box(f"💼 تاریخچه مذاکره ({len(rows)})", lines))

    # ════════════════════════════════════════
    #  🔍 3. Identity Verifier
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تایید_هویت (.+)$"))
    async def identity_verify(event):
        """بررسی احتمال جعل هویت یا اکانت مشکوک"""
        record_cmd("تایید_هویت")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        uid = u.id
        risk_score = 0
        risk_factors = []
        # بررسی‌های مختلف
        with _db_lock:
            conn = get_conn()
            # آیا قبلاً در سیستم بوده؟
            crm = conn.execute("SELECT * FROM crm_customers WHERE uid=?", (uid,)).fetchone()
            contact = conn.execute("SELECT * FROM contacts WHERE uid=?", (uid,)).fetchone()
            orders = conn.execute("SELECT COUNT(*) FROM store_orders WHERE uid=?", (uid,)).fetchone()[0]
            bl = conn.execute("SELECT * FROM blacklist_intel WHERE uid=?", (uid,)).fetchone()
        # سابقه
        if not crm and not contact:
            risk_score += 30
            risk_factors.append("🟡 کاربر جدید بدون سابقه")
        elif orders == 0:
            risk_score += 10
            risk_factors.append("🟡 بدون سابقه خرید")
        # username
        username = getattr(u, "username", "") or ""
        if not username:
            risk_score += 20
            risk_factors.append("🟡 بدون یوزرنیم")
        # وضعیت blacklist
        if bl:
            level_scores = {"trusted":-20,"normal":0,"suspicious":30,"restricted":50,"blocked":80}
            lev = bl["level"]
            risk_score += level_scores.get(lev, 0)
            risk_factors.append(f"{'🔴' if lev in ('restricted','blocked') else '🟡'} سطح: {lev}")
        # جمع‌بندی
        risk_score = max(0, min(100, risk_score))
        if risk_score >= 70:
            verdict = "🔴 ریسک بالا"
        elif risk_score >= 40:
            verdict = "🟡 ریسک متوسط"
        elif risk_score >= 20:
            verdict = "🟢 ریسک کم"
        else:
            verdict = "✅ قابل اعتماد"
        name = getattr(u, "first_name", str(uid))
        _bb_log_v9("identity_verify", f"uid={uid} risk={risk_score}")
        await safe_edit(event, box(f"🔍 تایید هویت — {name}", [
            f"آیدی: {uid}",
            f"یوزر: @{username or '—'}",
            f"امتیاز ریسک: {risk_score}/100",
            f"حکم: {verdict}",
            "── عوامل ──",
        ] + (risk_factors or ["✅ مشکلی شناسایی نشد"]),
            "⚠️ این نتیجه احتمالی است و قطعی نیست"))

    # ════════════════════════════════════════
    #  📦 4. Black Box Recorder
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بلک_باکس(?: (\d+))?$"))
    async def black_box_view(event):
        """مشاهده Black Box"""
        record_cmd("بلک_باکس")
        limit = int(event.pattern_match.group(1) or 20)
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM black_box ORDER BY id DESC LIMIT ?", (min(limit,50),)
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 Black Box خالی است.")
            return
        icons = {"info":"ℹ️","warning":"⚠️","error":"❌","critical":"🚨"}
        lines = [f"{icons.get(r['level'],'📌')} {r['ts'][:13]} | {r['event'][:25]} | {r['detail'][:30]}"
                 for r in rows]
        await safe_edit(event, box(f"📦 Black Box ({len(rows)})", lines,
                                   "پاک: پاک_بلک‌باکس"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بلک_باکس_خلاصه$"))
    async def black_box_summary(event):
        record_cmd("بلک_باکس_خلاصه")
        with _db_lock:
            conn = get_conn()
            total = conn.execute("SELECT COUNT(*) FROM black_box").fetchone()[0]
            errors = conn.execute("SELECT COUNT(*) FROM black_box WHERE level='error'").fetchone()[0]
            warnings = conn.execute("SELECT COUNT(*) FROM black_box WHERE level='warning'").fetchone()[0]
            last = conn.execute("SELECT * FROM black_box ORDER BY id DESC LIMIT 1").fetchone()
        lines = [
            f"کل رویداد: {total}",
            f"❌ خطا: {errors}",
            f"⚠️ هشدار: {warnings}",
            f"آخرین رویداد: {last['ts'][:16] if last else '—'}",
        ]
        if last:
            lines.append(f"آخرین: {last['event'][:40]}")
        await safe_edit(event, box("📦 خلاصه Black Box", lines))

    # ════════════════════════════════════════
    #  🔒 5. Airlock Mode
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ایرلاک (روشن|خاموش)$"))
    async def airlock_toggle(event):
        """حالت قرنطینه اضطراری"""
        global _airlock_v9
        record_cmd("ایرلاک")
        mode = event.pattern_match.group(1)
        _airlock_v9 = (mode == "روشن")
        set_setting("airlock_active", "1" if _airlock_v9 else "0")
        if _airlock_v9:
            _bb_log_v9("airlock_on", "Airlock Mode activated", "warning")
            await safe_edit(event, box("🔒 Airlock Mode فعال شد", [
                "⛔ ارسال انبوه متوقف شد",
                "⛔ Automation محدود شد",
                "⛔ پردازش‌های غیرضروری متوقف",
                "خاموش: ایرلاک خاموش",
            ]))
        else:
            _bb_log_v9("airlock_off", "Airlock Mode deactivated", "info")
            await safe_edit(event, "✅ Airlock Mode خاموش شد. عملیات‌ها آزاد هستند.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^وضعیت_ایرلاک$"))
    async def airlock_status(event):
        record_cmd("وضعیت_ایرلاک")
        active = _airlock_v9 or (setting("airlock_active", "0") == "1")
        with _db_lock:
            conn = get_conn()
            logs = conn.execute(
                "SELECT * FROM airlock_log ORDER BY id DESC LIMIT 5"
            ).fetchall()
        lines = [
            f"وضعیت: {'🔒 فعال' if active else '🔓 غیرفعال'}",
        ]
        if logs:
            lines += [f"📋 {r['ts'][:13]}: {r['reason'][:40]}" for r in logs]
        await safe_edit(event, box("🔒 Airlock Mode", lines))

    # ════════════════════════════════════════
    #  🍯 6. Honeytrap Detector
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^تله_بررسی (.+)$"))
    async def honeytrap_check(event):
        """تشخیص رفتار مشکوک/Scam"""
        record_cmd("تله_بررسی")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        uid = u.id
        risk = 0
        factors = []
        with _db_lock:
            conn = get_conn()
            crm = conn.execute("SELECT * FROM crm_customers WHERE uid=?", (uid,)).fetchone()
            bl = conn.execute("SELECT * FROM blacklist_intel WHERE uid=?", (uid,)).fetchone()
            orders = conn.execute("SELECT COUNT(*) FROM store_orders WHERE uid=?", (uid,)).fetchone()[0]
            cancelled = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE uid=? AND status='cancelled'", (uid,)
            ).fetchone()[0]
        username = getattr(u, "username", "") or ""
        first_name = getattr(u, "first_name", "") or ""
        if not username:
            risk += 25; factors.append("🟡 بدون یوزرنیم")
        if len(first_name) < 2:
            risk += 15; factors.append("🟡 نام خیلی کوتاه")
        if cancelled > 2:
            risk += 20; factors.append(f"🔴 {cancelled} سفارش لغو‌شده")
        if bl and bl["level"] in ("suspicious","restricted","blocked"):
            risk += 40; factors.append(f"🔴 در لیست ریسک: {bl['level']}")
        if crm and crm.get("blacklisted"):
            risk += 50; factors.append("🔴 بلاک‌شده در CRM")
        risk = min(100, risk)
        verdict = ("🔴 مشکوک" if risk >= 60 else ("🟡 بررسی نیاز" if risk >= 30 else "🟢 طبیعی"))
        _bb_log_v9("honeytrap_check", f"uid={uid} risk={risk}")
        await safe_edit(event, box(f"🍯 Honeytrap — {getattr(u,'first_name',uid)}", [
            f"آیدی: {uid}",
            f"خریدها: {orders} | لغو‌شده: {cancelled}",
            f"امتیاز ریسک: {risk}/100",
            f"حکم: {verdict}",
            "── عوامل ──",
        ] + (factors or ["✅ مشکلی نیست"]),
            "⚠️ نتیجه احتمالی است"))

    # ════════════════════════════════════════
    #  ⌨️ 7. Command Studio
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستور_جدید (.+)\|(.+)\|(.+)$"))
    async def command_studio_create(event):
        """دستور_جدید [نام]|[تریگر]|[اکشن]"""
        record_cmd("دستور_جدید")
        name    = event.pattern_match.group(1).strip()
        trigger = event.pattern_match.group(2).strip()
        action  = event.pattern_match.group(3).strip()
        if not name or not trigger or not action:
            await safe_edit(event, "❌ فرمت: دستور_جدید [نام]|[تریگر]|[اکشن]"); return
        with _db_lock:
            conn = get_conn()
            try:
                conn.execute(
                    "INSERT INTO custom_commands(name,trigger,action,ts) VALUES(?,?,?,?)",
                    (name[:50], trigger[:100], action[:500], now_str())
                )
                conn.commit()
            except Exception:
                conn.execute(
                    "UPDATE custom_commands SET trigger=?,action=?,active=1 WHERE name=?",
                    (trigger[:100], action[:500], name)
                )
                conn.commit()
        _bb_log_v9("custom_cmd_created", f"name={name}")
        await safe_edit(event, box("⌨️ دستور سفارشی ثبت شد", [
            f"نام: {name}",
            f"تریگر: {trigger}",
            f"اکشن: {action[:50]}",
            "لیست: دستور_لیست",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستور_لیست$"))
    async def command_studio_list(event):
        record_cmd("دستور_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM custom_commands WHERE active=1 ORDER BY run_count DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ دستور سفارشی ثبت نشده!\nدستور_جدید [نام]|[تریگر]|[اکشن]")
            return
        lines = [f"• {r['name']}: «{r['trigger'][:20]}» → {r['action'][:30]} ({r['run_count']} اجرا)"
                 for r in rows]
        await safe_edit(event, box(f"⌨️ دستورات سفارشی ({len(rows)})", lines,
                                   "حذف: دستور_حذف [نام]"))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^دستور_حذف (.+)$"))
    async def command_studio_delete(event):
        record_cmd("دستور_حذف")
        name = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            c = conn.execute("DELETE FROM custom_commands WHERE name=?", (name,))
            conn.commit()
        await safe_edit(event, f"✅ دستور «{name}» حذف شد." if c.rowcount else f"❌ دستور «{name}» پیدا نشد!")

    @client.on(events.NewMessage(outgoing=True))
    async def custom_command_runner(event):
        """اجرای دستورات سفارشی"""
        try:
            text = (event.text or "").strip()
            if not text:
                return
            with _db_lock:
                conn = get_conn()
                cmds = conn.execute(
                    "SELECT * FROM custom_commands WHERE active=1"
                ).fetchall()
            for cmd in cmds:
                trigger = cmd["trigger"]
                if text == trigger or text.startswith(trigger + " "):
                    action = cmd["action"]
                    # جایگزینی متغیرها
                    if "{arg}" in action:
                        arg = text[len(trigger):].strip()
                        action = action.replace("{arg}", arg)
                    action = action.replace("{time}", iran_now().strftime("%H:%M"))
                    action = action.replace("{date}", jalali())
                    await safe_edit(event, action)
                    with _db_lock:
                        conn = get_conn()
                        conn.execute(
                            "UPDATE custom_commands SET run_count=run_count+1 WHERE name=?",
                            (cmd["name"],)
                        )
                        conn.commit()
                    break
        except Exception:
            pass

    # ════════════════════════════════════════
    #  💧 8. Invisible Watermark Engine
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^واترمارک (\d+)\|(.+)$"))
    async def watermark_create(event):
        """واترمارک [order_uid_or_uid]|[نام_فایل/توضیح]"""
        record_cmd("واترمارک")
        uid_or_order = event.pattern_match.group(1).strip()
        desc = event.pattern_match.group(2).strip()
        try:
            uid = int(uid_or_order)
        except Exception:
            uid = 0
        fp = _generate_wm_fingerprint(uid, desc[:8])
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO watermark_registry(order_uid,uid,fingerprint,ts) VALUES(?,?,?,?)",
                (uid_or_order, uid, fp, now_str())
            )
            conn.commit()
        _bb_log_v9("watermark_created", f"uid={uid} fp={fp}")
        await safe_edit(event, box("💧 Watermark تولید شد", [
            f"UID: {uid}",
            f"توضیح: {desc[:40]}",
            f"اثر انگشت: `{fp}`",
            "این کد برای شناسایی منشأ فایل است",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^واترمارک_بررسی (.+)$"))
    async def watermark_check(event):
        """بررسی اثر انگشت"""
        record_cmd("واترمارک_بررسی")
        fp = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM watermark_registry WHERE fingerprint LIKE ?",
                (f"%{fp[:20]}%",)
            ).fetchall()
        if not rows:
            await safe_edit(event, "❌ اثر انگشتی با این کد پیدا نشد!")
            return
        lines = [f"• uid:{r['uid']} | سفارش:{r['order_uid']} | {r['ts'][:13]}" for r in rows]
        await safe_edit(event, box(f"💧 نتیجه بررسی Watermark", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^واترمارک_لیست$"))
    async def watermark_list(event):
        record_cmd("واترمارک_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM watermark_registry ORDER BY id DESC LIMIT 20"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 واترمارکی ثبت نشده!")
            return
        lines = [f"• {r['id']}. uid:{r['uid']} | {r['fingerprint'][:20]} | {r['ts'][:10]}"
                 for r in rows]
        await safe_edit(event, box(f"💧 لیست Watermarks ({len(rows)})", lines))

    # ════════════════════════════════════════
    #  🔗 9. Smart Link Intelligence
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^لینک_آنالیز (.+)$"))
    async def link_analyze(event):
        """تحلیل لینک"""
        record_cmd("لینک_آنالیز")
        url = event.pattern_match.group(1).strip()
        await safe_edit(event, "⏳ در حال تحلیل لینک...")
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc or "—"
            scheme = parsed.scheme or "—"
            path   = parsed.path[:50] or "/"
            query  = parsed.query[:50] or "—"
            # تشخیص نوع
            link_type = "عمومی"
            if "t.me" in domain or "telegram" in domain:
                link_type = "تلگرام"
            elif "youtube" in domain or "youtu.be" in domain:
                link_type = "یوتیوب"
            elif "instagram" in domain:
                link_type = "اینستاگرام"
            elif "github" in domain:
                link_type = "GitHub"
            elif any(d in domain for d in ["vpn","v2ray","clash","vmess","vless","trojan"]):
                link_type = "VPN/Proxy"
            elif domain.endswith(".ir") or ".ir/" in url:
                link_type = "سایت ایرانی"
            # بررسی امنیت
            security_flags = []
            if scheme != "https":
                security_flags.append("⚠️ بدون HTTPS")
            if len(url) > 200:
                security_flags.append("⚠️ URL خیلی بلند")
            if "bit.ly" in domain or "tinyurl" in domain or "goo.gl" in domain:
                security_flags.append("⚠️ لینک کوتاه‌شده")
            # Action پیشنهادی
            actions = []
            if link_type == "تلگرام":
                actions.append("✓ باز کن در تلگرام")
            elif link_type == "یوتیوب":
                actions.append("✓ دانلود با .dl")
            elif link_type == "VPN/Proxy":
                actions.append("✓ ثبت با کانفیگ_ثبت")
            else:
                actions.append("✓ باز در مرورگر")
            await safe_edit(event, box("🔗 Smart Link Intelligence", [
                f"دامنه: {domain}",
                f"پروتکل: {scheme.upper()}",
                f"مسیر: {path}",
                f"نوع: {link_type}",
            ] + ([f"🔒 امنیت: {', '.join(security_flags)}"] if security_flags else ["🔒 امنیت: OK"])
              + ["── اکشن پیشنهادی ──"] + actions))
        except Exception as ex:
            await safe_edit(event, f"❌ خطا در تحلیل: {ex}")

    # ════════════════════════════════════════
    #  📤 10. Universal Exporter
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^اکسپورت (contacts|orders|crm|products|settings|calendar|macros)(?: (json|csv|txt))?$"))
    async def universal_export(event):
        """اکسپورت داده‌های سلف"""
        record_cmd("اکسپورت")
        data_type = event.pattern_match.group(1)
        fmt = (event.pattern_match.group(2) or "json").lower()
        await safe_edit(event, f"⏳ اکسپورت {data_type} به {fmt.upper()}...")
        try:
            with _db_lock:
                conn = get_conn()
                query_map = {
                    "contacts": "SELECT * FROM contacts LIMIT 500",
                    "orders":   "SELECT * FROM store_orders ORDER BY id DESC LIMIT 500",
                    "crm":      "SELECT * FROM crm_customers LIMIT 500",
                    "products": "SELECT * FROM store_products",
                    "settings": "SELECT * FROM settings",
                    "calendar": "SELECT * FROM calendar ORDER BY date",
                    "macros":   "SELECT * FROM macros",
                }
                rows = conn.execute(query_map[data_type]).fetchall()
            if not rows:
                await safe_edit(event, f"📭 داده‌ای برای اکسپورت {data_type} نیست!")
                return
            ts_safe = iran_now().strftime("%Y%m%d_%H%M%S")
            filename = f"onyx_export_{data_type}_{ts_safe}.{fmt}"
            filepath = os.path.join(DL_DIR, filename)
            data_list = [dict(r) for r in rows]
            if fmt == "json":
                content = json.dumps(data_list, ensure_ascii=False, indent=2)
            elif fmt == "csv":
                import csv, io
                buf = io.StringIO()
                if data_list:
                    writer = csv.DictWriter(buf, fieldnames=data_list[0].keys())
                    writer.writeheader()
                    writer.writerows(data_list)
                content = buf.getvalue()
            else:  # txt
                lines_txt = []
                for i, d in enumerate(data_list, 1):
                    lines_txt.append(f"── {i} ──")
                    lines_txt.extend(f"{k}: {v}" for k, v in d.items())
                content = "\n".join(lines_txt)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            _bb_log_v9("export", f"type={data_type} fmt={fmt} rows={len(data_list)}")
            await safe_edit(event, box("📤 اکسپورت انجام شد", [
                f"نوع: {data_type}",
                f"فرمت: {fmt.upper()}",
                f"تعداد: {len(data_list)} رکورد",
                f"فایل: {filename}",
                f"مسیر: {filepath}",
            ]))
            # ارسال فایل به Saved Messages
            me = await client.get_me()
            await client.send_file(me.id, filepath, caption=f"📤 Export: {data_type} ({len(data_list)} records)")
        except Exception as ex:
            await safe_edit(event, f"❌ خطا در اکسپورت: {ex}")

    # ════════════════════════════════════════
    #  🎯 11. Universal Capture
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپچر$"))
    async def universal_capture_help(event):
        """راهنمای Universal Capture"""
        await safe_edit(event, box("🎯 Universal Capture", [
            "این سیستم محتوای ورودی را شناسایی می‌کند:",
            "• کپچر_لینک [URL] — تحلیل لینک",
            "• کپچر_متن [متن] — ذخیره متن",
            "• کپچر_عدد [شماره] — شناسایی شماره",
            "• کپچر_تاریخ [تاریخ] — ذخیره رویداد",
            "• کپچر_فایل — ذخیره فایل ریپلای",
            "یا فقط پیام بده و سیستم تشخیص می‌دهد!",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کپچر_متن (.+)$"))
    async def capture_text(event):
        record_cmd("کپچر_متن")
        text = event.pattern_match.group(1).strip()
        # تشخیص هوشمند نوع
        content_type = "text"
        if text.startswith("http"):
            content_type = "link"
        elif text.startswith("+98") or text.startswith("09"):
            content_type = "phone"
        elif re.match(r"\d{4}/\d{2}/\d{2}", text):
            content_type = "date"
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO capture_log(type,content,ts) VALUES(?,?,?)",
                (content_type, text[:500], now_str())
            )
            conn.commit()
        # هدایت هوشمند
        if content_type == "link":
            await safe_edit(event, f"🔗 لینک شناسایی شد!\nبرای تحلیل: لینک_آنالیز {text}")
        elif content_type == "phone":
            await safe_edit(event, f"📱 شماره تلفن شناسایی شد: {text}\nبرای ذخیره در CRM: crm_تلفن [@user]|{text}")
        elif content_type == "date":
            await safe_edit(event, f"📅 تاریخ شناسایی شد: {text}\nبرای ذخیره در تقویم: تقویم [نوع] {text} [عنوان]")
        else:
            await safe_edit(event, f"📝 متن ذخیره شد!\nبرای ذخیره: سیو | ماکرو [نام]={text}")

    # ════════════════════════════════════════
    #  📡 12. Personal Radar
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رادار$"))
    async def personal_radar(event):
        """گزارش Radar — رویدادهای مهم"""
        record_cmd("رادار")
        with _db_lock:
            conn = get_conn()
            # سفارشات pending
            pending_orders = conn.execute(
                "SELECT COUNT(*) FROM store_orders WHERE status='pending'"
            ).fetchone()[0]
            # مشتریان VIP بدون خرید اخیر
            vip_inactive = conn.execute(
                "SELECT COUNT(*) FROM crm_customers WHERE vip_level>0 AND blacklisted=0 AND "
                f"(last_purchase IS NULL OR last_purchase < '{jalali()[:7]}')"
            ).fetchone()[0]
            # موجودی کم
            low_stock = conn.execute(
                "SELECT COUNT(*) FROM store_products p WHERE p.active=1 AND "
                "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=0) <= 3"
            ).fetchone()[0]
            # خطاهای اخیر
            recent_errors = conn.execute(
                "SELECT COUNT(*) FROM black_box WHERE level='error' AND ts > ?",
                (f"{jalali()} 00:00",)
            ).fetchone()[0]
            # کوپن‌های منقضی‌نزدیک
            vip_count = conn.execute(
                "SELECT COUNT(*) FROM crm_customers WHERE vip_level>0"
            ).fetchone()[0]
        alerts = []
        if pending_orders > 0:
            alerts.append(f"📦 {pending_orders} سفارش در انتظار تایید ← سفارش_لیست pending")
        if low_stock > 0:
            alerts.append(f"⚠️ {low_stock} محصول موجودی کم ← هشدار_موجودی")
        if recent_errors > 0:
            alerts.append(f"❌ {recent_errors} خطای امروز ← بلک_باکس")
        if vip_inactive > 0:
            alerts.append(f"💎 {vip_inactive} VIP غیرفعال ← پخش_vip [پیام]")
        if not alerts:
            alerts = ["✅ همه چیز طبیعی است!"]
        await safe_edit(event, box(f"📡 Personal Radar — {now_str()}", [
            f"💎 VIP: {vip_count} | 📦 انتظار: {pending_orders} | ⚠️ موجودی کم: {low_stock}",
            "── هشدارها ──",
        ] + alerts))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رادار_تنظیم$"))
    async def radar_settings(event):
        await safe_edit(event, box("📡 تنظیمات Radar", [
            "رادار — گزارش کلی",
            "رادار_رویداد [نوع]|[خلاصه] — ثبت رویداد",
            "رادار_لیست — لیست رویدادها",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رادار_رویداد (.+)\|(.+)$"))
    async def radar_add_event(event):
        record_cmd("رادار_رویداد")
        etype   = event.pattern_match.group(1).strip()
        summary = event.pattern_match.group(2).strip()
        with _db_lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO radar_events(type,summary,score,ts) VALUES(?,?,0,?)",
                (etype[:50], summary[:200], now_str())
            )
            conn.commit()
        await safe_edit(event, f"📡 رویداد «{summary[:40]}» ثبت شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^رادار_لیست$"))
    async def radar_list(event):
        record_cmd("رادار_لیست")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM radar_events WHERE seen=0 ORDER BY id DESC LIMIT 15"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 رویداد جدیدی نیست!"); return
        lines = [f"• {r['ts'][:13]} | {r['type'][:15]}: {r['summary'][:40]}" for r in rows]
        await safe_edit(event, box(f"📡 رویدادهای Radar ({len(rows)})", lines))

    # ════════════════════════════════════════
    #  🏰 13. Personal Control Tower
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^برج_کنترل$"))
    async def control_tower(event):
        """مرکز کنترل واحد"""
        record_cmd("برج_کنترل")
        with _db_lock:
            conn = get_conn()
            pending_orders = conn.execute("SELECT COUNT(*) FROM store_orders WHERE status='pending'").fetchone()[0]
            total_customers = conn.execute("SELECT COUNT(*) FROM crm_customers").fetchone()[0]
            vip_count = conn.execute("SELECT COUNT(*) FROM crm_customers WHERE vip_level>0").fetchone()[0]
            open_tickets = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='open'").fetchone()[0]
            today_cmds = conn.execute("SELECT COUNT(*) FROM cmd_history WHERE ts LIKE ?",
                                      (f"{jalali()}%",)).fetchone()[0]
            errors_today = conn.execute("SELECT COUNT(*) FROM black_box WHERE level='error' AND ts LIKE ?",
                                        (f"{jalali()}%",)).fetchone()[0]
            products_active = conn.execute("SELECT COUNT(*) FROM store_products WHERE active=1").fetchone()[0]
            total_revenue = conn.execute(
                "SELECT COALESCE(SUM(price),0) FROM store_orders WHERE status='approved'"
            ).fetchone()[0]
        clock_st = "🟢" if (_clock_task and not _clock_task.done()) else "🔴"
        airlock_st = "🔒" if _airlock_v9 else "🔓"
        await safe_edit(event, box("🏰 Personal Control Tower", [
            f"📅 {jalali()} | {iran_now().strftime('%H:%M')}",
            "─────────────────────",
            f"⏰ ساعت: {clock_st} | 🔒 Airlock: {airlock_st}",
            "─────────────────────",
            f"📦 سفارش منتظر: {pending_orders}",
            f"👥 مشتری: {total_customers} | VIP: {vip_count}",
            f"🎫 تیکت باز: {open_tickets}",
            f"🛍 محصول فعال: {products_active}",
            f"💰 درآمد کل: {total_revenue:,}",
            "─────────────────────",
            f"⚡ دستور امروز: {today_cmds}",
            f"❌ خطای امروز: {errors_today}",
            "─────────────────────",
            "📡 رادار   | 📦 سفارش_لیست pending",
            "💼 پنل     | 📊 آمار_فروشگاه",
            "🔍 بلک_باکس| 🔒 ایرلاک روشن",
        ], WATERMARK))

    # ════════════════════════════════════════
    #  🚦 14. Personal Blacklist Intelligence
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True,
        pattern=r"^بلک_لیست_هوش (.+) (trusted|normal|suspicious|restricted|blocked)(?: (.+))?$"))
    async def blacklist_intel_set(event):
        """بلک_لیست_هوش [@user] [سطح] [دلیل]"""
        record_cmd("بلک_لیست_هوش")
        arg    = event.pattern_match.group(1).strip()
        level  = event.pattern_match.group(2).strip()
        reason = (event.pattern_match.group(3) or "").strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        _set_blacklist_level(u.id, level, reason)
        _bb_log_v9("blacklist_set", f"uid={u.id} level={level}")
        ICONS = {"trusted":"✅","normal":"⚪","suspicious":"🟡","restricted":"🟠","blocked":"🔴"}
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, box(f"🚦 Blacklist Intelligence", [
            f"کاربر: {name} ({u.id})",
            f"سطح: {ICONS.get(level,'')} {level}",
            f"دلیل: {reason or '—'}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بلک_لیست_هوش_نمایش (.+)$"))
    async def blacklist_intel_show(event):
        record_cmd("بلک_لیست_هوش_نمایش")
        arg = event.pattern_match.group(1).strip()
        u = await resolve_user(client, event, arg)
        if not u:
            await safe_edit(event, "❌ کاربر پیدا نشد!"); return
        level = _get_blacklist_level(u.id)
        with _db_lock:
            conn = get_conn()
            row = conn.execute("SELECT * FROM blacklist_intel WHERE uid=?", (u.id,)).fetchone()
        ICONS = {"trusted":"✅","normal":"⚪","suspicious":"🟡","restricted":"🟠","blocked":"🔴"}
        name = getattr(u, "first_name", str(u.id))
        await safe_edit(event, box(f"🚦 {name}", [
            f"سطح: {ICONS.get(level,'')} {level}",
            f"دلیل: {row['reason'] if row else '—'}",
            f"تاریخ: {row['ts'][:13] if row else '—'}",
        ]))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^بلک_لیست_هوش_کل$"))
    async def blacklist_intel_all(event):
        record_cmd("بلک_لیست_هوش_کل")
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT bi.*, c.name FROM blacklist_intel bi LEFT JOIN contacts c ON bi.uid=c.uid "
                "ORDER BY bi.uid DESC LIMIT 30"
            ).fetchall()
        if not rows:
            await safe_edit(event, "📭 هیچ سطح ریسکی ثبت نشده!")
            return
        ICONS = {"trusted":"✅","normal":"⚪","suspicious":"🟡","restricted":"🟠","blocked":"🔴"}
        lines = [f"{ICONS.get(r['level'],'')} {r['uid']} | {r['name'] or '—'} | {r['level']}"
                 for r in rows]
        await safe_edit(event, box(f"🚦 Blacklist Intelligence ({len(rows)})", lines))

    # ════════════════════════════════════════
    #  🎬 15. Event Replay
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریپلی_رویداد (.+)$"))
    async def event_replay_view(event):
        """بازسازی زنجیره رویدادهای یک موجودیت"""
        record_cmd("ریپلی_رویداد")
        entity_id = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM event_replay WHERE entity_id=? ORDER BY id",
                (entity_id,)
            ).fetchall()
        if not rows:
            await safe_edit(event, f"❌ رویدادی برای «{entity_id}» ثبت نشده!")
            return
        lines = []
        for i, r in enumerate(rows, 1):
            lines.append(f"{'┌' if i==1 else ('└' if i==len(rows) else '├')} "
                         f"[{r['ts'][5:16]}] {r['event'][:40]}")
            if r.get("data") and r["data"] != "{}":
                lines.append(f"  → {r['data'][:50]}")
        await safe_edit(event, box(f"🎬 Event Replay: {entity_id}", lines))

    @client.on(events.NewMessage(outgoing=True, pattern=r"^ریپلی_سفارش (.+)$"))
    async def order_replay(event):
        """بازسازی تاریخچه یک سفارش"""
        record_cmd("ریپلی_سفارش")
        order_uid = event.pattern_match.group(1).strip()
        with _db_lock:
            conn = get_conn()
            order = conn.execute(
                "SELECT * FROM store_orders WHERE order_uid=?", (order_uid,)
            ).fetchone()
            history = conn.execute(
                "SELECT * FROM order_history WHERE order_uid=? ORDER BY id",
                (order_uid,)
            ).fetchall()
        if not order:
            await safe_edit(event, f"❌ سفارش «{order_uid}» پیدا نشد!"); return
        lines = [
            f"👤 مشتری: {order['name']} ({order['uid']})",
            f"📦 محصول: {order['product_name']}",
            f"💰 قیمت: {order['price']:,}",
            f"📌 وضعیت فعلی: {order['status']}",
            "── تاریخچه ──",
        ]
        if history:
            for h in history:
                lines.append(f"→ [{h['ts'][5:16]}] {h['action']}: {(h.get('detail','') or '')[:40]}")
        else:
            lines.append("→ تاریخچه‌ای ثبت نشده")
        await safe_edit(event, box(f"🎬 Event Replay: سفارش {order_uid}", lines))

    # ════════════════════════════════════════
    #  🔄 16. Context Switcher
    # ════════════════════════════════════════

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانتکست (.+)$"))
    async def context_switch(event):
        """کانتکست [@user/order_uid/product_id] — سوییچ Context"""
        record_cmd("کانتکست")
        arg = event.pattern_match.group(1).strip()
        ctx_data = {}
        ctx_type = "unknown"
        # تشخیص نوع
        if arg.startswith("@") or (arg.lstrip("-").isdigit() and len(arg) > 5):
            ctx_type = "user"
            u = await resolve_user(client, event, arg)
            if u:
                uid = u.id
                with _db_lock:
                    conn = get_conn()
                    crm = conn.execute("SELECT * FROM crm_customers WHERE uid=?", (uid,)).fetchone()
                    orders = conn.execute(
                        "SELECT * FROM store_orders WHERE uid=? ORDER BY id DESC LIMIT 5", (uid,)
                    ).fetchall()
                    contact = conn.execute("SELECT * FROM contacts WHERE uid=?", (uid,)).fetchone()
                ctx_data = {
                    "uid": uid, "name": getattr(u,"first_name",""),
                    "vip": crm["vip_level"] if crm else 0,
                    "total_spent": crm["total_spent"] if crm else 0,
                    "orders": len(orders),
                    "last_purchase": crm["last_purchase"] if crm else "",
                    "note": contact["note"][:50] if contact and contact["note"] else "",
                }
                _context_v9["active"] = {"type": "user", "id": uid, "data": ctx_data}
                name = getattr(u, "first_name", str(uid))
                lines = [
                    f"👤 {name} ({uid})",
                    f"💎 VIP: {ctx_data['vip']}",
                    f"💰 خرید کل: {ctx_data['total_spent']:,}",
                    f"📦 سفارشات: {ctx_data['orders']}",
                    f"📝 یادداشت: {ctx_data['note'] or '—'}",
                    "── آخرین سفارشات ──",
                ] + [f"• {o['order_uid'][:10]} | {o['product_name'][:20]} | {o['status']}" for o in orders]
                await safe_edit(event, box(f"🔄 Context: {name}", lines,
                                           "کانتکست_پاک برای ریست"))
            else:
                await safe_edit(event, "❌ کاربر پیدا نشد!")
        elif arg.startswith("ORD-") or arg.startswith("ord-"):
            ctx_type = "order"
            with _db_lock:
                conn = get_conn()
                order = conn.execute("SELECT * FROM store_orders WHERE order_uid=?", (arg,)).fetchone()
            if order:
                _context_v9["active"] = {"type": "order", "id": arg, "data": dict(order)}
                await safe_edit(event, box(f"🔄 Context: سفارش {arg}", [
                    f"مشتری: {order['name']} ({order['uid']})",
                    f"محصول: {order['product_name']}",
                    f"قیمت: {order['price']:,}",
                    f"وضعیت: {order['status']}",
                    f"تاریخ: {order['ts'][:13]}",
                ]))
            else:
                await safe_edit(event, f"❌ سفارش «{arg}» پیدا نشد!")
        else:
            # تلاش برای محصول
            try:
                pid = int(arg)
                with _db_lock:
                    conn = get_conn()
                    prod = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
                if prod:
                    pk = _get_product_knowledge(pid)
                    _context_v9["active"] = {"type": "product", "id": pid, "data": dict(prod)}
                    await safe_edit(event, box(f"🔄 Context: محصول {prod['name']}", [
                        f"نوع: {pk.get('product_type','عمومی')}",
                        f"قیمت: {prod['price']:,}",
                        f"توضیح: {prod['description'][:50] or '—'}",
                        f"Knowledge: {'✅' if pk.get('ai_context') else '❌'}",
                    ]))
                else:
                    await safe_edit(event, f"❌ محصول {pid} پیدا نشد!")
            except Exception:
                await safe_edit(event, "❌ نوع Context شناسایی نشد!\nمثال: کانتکست @user | کانتکست ORD-xxx | کانتکست [product_id]")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانتکست_پاک$"))
    async def context_clear(event):
        record_cmd("کانتکست_پاک")
        _context_v9.clear()
        await safe_edit(event, "✅ Context پاک شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^کانتکست_نمایش$"))
    async def context_show(event):
        record_cmd("کانتکست_نمایش")
        active = _context_v9.get("active")
        if not active:
            await safe_edit(event, "📭 Context فعالی نیست!\nکانتکست [@user/order/product_id]")
            return
        lines = [
            f"نوع: {active['type']}",
            f"شناسه: {active['id']}",
        ]
        for k, v in (active.get("data") or {}).items():
            if str(v):
                lines.append(f"{k}: {str(v)[:50]}")
        await safe_edit(event, box(f"🔄 Context فعال: {active['type']}", lines[:15]))

    # ════════════════════════════════════════
    #  ⏰ ساعت — بازیابی پس از Restart
    # ════════════════════════════════════════
    # این تابع در startup فراخوانی می‌شود
    async def restore_clock_if_needed():
        """بازیابی ساعت پس از Restart"""
        global _clock_task
        if _clock_is_active() and (not _clock_task or _clock_task.done()):
            logger.info("⏰ بازیابی ساعت از دیتابیس...")
            _clock_task = asyncio.create_task(_clock_loop(client))

    # Expose for startup
    _register_v9._restore_clock = restore_clock_if_needed

    # ════════════════════════════════════════
    #  📊 V9 Menu entries (merged)
    # ════════════════════════════════════════
    V9_MENU = {
        "🆕 قابلیت‌های V9": [
            ("دانش_محصول",      "Context/دانش محصول",              "دانش_محصول [id]",            "دانش_محصول 1"),
            ("دانش_ثبت",        "ثبت فیلد دانش محصول",             "دانش_ثبت [id]|[فیلد]|[مقدار]","دانش_ثبت 1|نوع|دوره"),
            ("دانش_کامل",       "قالب کامل Knowledge",             "دانش_کامل [id]",             "دانش_کامل 1"),
            ("دانش_لیست",       "لیست دانش محصولات",               "دانش_لیست",                  "دانش_لیست"),
            ("مذاکره",          "Smart Negotiator",                "مذاکره [id] [درصد]",          "مذاکره 1 15"),
            ("تایید_هویت",      "Identity Verifier",               "تایید_هویت [@user]",          "تایید_هویت @ali"),
            ("تله_بررسی",       "Honeytrap Detector",              "تله_بررسی [@user]",           "تله_بررسی @ali"),
            ("خودترمیم",        "Self-Healing Report",             "خودترمیم",                   "خودترمیم"),
            ("بلک_باکس",        "Black Box Recorder",              "بلک_باکس [تعداد]",            "بلک_باکس 20"),
            ("بلک_باکس_خلاصه",  "خلاصه Black Box",                 "بلک_باکس_خلاصه",             "بلک_باکس_خلاصه"),
            ("پاک_بلک‌باکس",    "پاک‌کردن Black Box",              "پاک_بلک‌باکس",               "پاک_بلک‌باکس"),
            ("ایرلاک",          "Airlock Mode",                    "ایرلاک [روشن|خاموش]",         "ایرلاک روشن"),
            ("واترمارک",        "Invisible Watermark",             "واترمارک [uid]|[توضیح]",      "واترمارک 123|فایل"),
            ("لینک_آنالیز",     "Smart Link Intelligence",         "لینک_آنالیز [URL]",           "لینک_آنالیز https://..."),
            ("اکسپورت",         "Universal Exporter",              "اکسپورت [نوع] [فرمت]",        "اکسپورت orders json"),
            ("کپچر_متن",        "Universal Capture",               "کپچر_متن [متن]",              "کپچر_متن سلام"),
            ("رادار",           "Personal Radar",                  "رادار",                      "رادار"),
            ("برج_کنترل",       "Personal Control Tower",          "برج_کنترل",                  "برج_کنترل"),
            ("بلک_لیست_هوش",    "Blacklist Intelligence",          "بلک_لیست_هوش [@] [سطح]",     "بلک_لیست_هوش @ali suspicious"),
            ("ریپلی_رویداد",    "Event Replay",                    "ریپلی_رویداد [id]",           "ریپلی_رویداد ORD-xxx"),
            ("ریپلی_سفارش",     "Replay سفارش",                   "ریپلی_سفارش [order_uid]",     "ریپلی_سفارش ORD-abc"),
            ("کانتکست",         "Context Switcher",                "کانتکست [@/order/product]",   "کانتکست @ali"),
            ("دستور_جدید",      "Command Studio",                  "دستور_جدید [نام]|[تریگر]|[اکشن]","دستور_جدید test|سلام|درود!"),
            ("دستور_لیست",      "لیست دستورات سفارشی",             "دستور_لیست",                 "دستور_لیست"),
        ],
    }
    FULL_MENU.update(V9_MENU)

    _bb_log_v9("v9_registered", "All V9 handlers loaded")


# ── ثبت V8 و V9 در register_all ──────────────────────
_original_register_all = register_all

def register_all(client):
    _original_register_all(client)
    _register_v8(client)
    _register_v9(client)




# ══════════════════════════════════════════════════════
#  ═══  STARTUP  ═══
# ══════════════════════════════════════════════════════
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╭──────────────────────────────────────────────────╮
│         💎 ONYX SELF V7 PRO'S                      │
│   سلف‌بات حرفه‌ای تلگرام — معماری ماژولار        │
│   کتابخانه: Telethon + SQLite (WAL)              │
│   پلتفرم: Termux / Linux                         │
│   سازنده: @Reyvoxe                               │
╰──────────────────────────────────────────────────╯

راه‌اندازی اول:
    python main.py

تنظیم در config.ini یا متغیر محیطی:
    ONYX_API_ID     = your_api_id
    ONYX_API_HASH   = your_api_hash
    ONYX_SESSION    = onyx_v7  (اختیاری)
"""


# ── مسیرها ───────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── بارگذاری ماژول هسته ──────────────────────

# ── تنظیمات ──────────────────────────────────
CONFIG_FILE = BASE_DIR / "config.ini"

def load_config() -> dict:
    """بارگذاری تنظیمات از فایل یا متغیرهای محیطی"""
    cfg = {
        "api_id":   os.environ.get("ONYX_API_ID", ""),
        "api_hash": os.environ.get("ONYX_API_HASH", ""),
        "session":  os.environ.get("ONYX_SESSION", "onyx_v7"),
        "phone":    os.environ.get("ONYX_PHONE", ""),
    }
    if CONFIG_FILE.exists():
        parser = configparser.ConfigParser()
        parser.read(str(CONFIG_FILE))
        sec = parser["onyx"] if "onyx" in parser else {}
        cfg["api_id"]   = sec.get("api_id",   cfg["api_id"])
        cfg["api_hash"] = sec.get("api_hash",  cfg["api_hash"])
        cfg["session"]  = sec.get("session",   cfg["session"])
        cfg["phone"]    = sec.get("phone",     cfg["phone"])
    return cfg

def prompt_config() -> dict:
    """دریافت اطلاعات از کاربر در صورت نبود config"""
    print("\n" + "="*50)
    print("💎 ONYX SELF V7 PRO'S — راه‌اندازی اولیه")
    print("="*50)
    print("برای دریافت API ID و Hash: https://my.telegram.org")
    print()
    api_id   = input("🔑 API ID   : ").strip()
    api_hash = input("🔑 API HASH : ").strip()
    phone    = input("📱 شماره تلفن (مثال: +989...) : ").strip()
    session  = input("💾 نام سشن [onyx_v7]: ").strip() or "onyx_v7"
    cfg = {"api_id": api_id, "api_hash": api_hash,
           "session": session, "phone": phone}
    # ذخیره در config.ini
    parser = configparser.ConfigParser()
    parser["onyx"] = cfg
    with open(str(CONFIG_FILE), "w", encoding="utf-8") as f:
        parser.write(f)
    print(f"\n✅ تنظیمات در {CONFIG_FILE} ذخیره شد.")
    return cfg

# ── بارگذاری پلاگین‌های خارجی ─────────────────
def load_external_plugins(client) -> int:
    """بارگذاری پلاگین‌های پوشه plugins/"""
    loaded = 0
    plg_path = Path(PLG_DIR)
    if not plg_path.exists():
        return 0
    for fpath in sorted(plg_path.glob("*.py")):
        if fpath.name.startswith("_"):
            pass
        try:
            spec = importlib.util.spec_from_file_location(fpath.stem, str(fpath))
            if spec is None:
                pass
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(client)
                loaded += 1
                logger.info(f"🧩 پلاگین لود شد: {fpath.name}")
                # ثبت در دیتابیس
                conn = get_conn()
                conn.execute(
                    "INSERT INTO plugins(name,enabled) VALUES(?,1) "
                    "ON CONFLICT(name) DO UPDATE SET enabled=1",
                    (fpath.stem,)
                )
                conn.commit()
            else:
                logger.warning(f"🧩 {fpath.name}: تابع register() ندارد — رد شد")
        except Exception as e:
            logger.error(f"🧩 خطا در بارگذاری {fpath.name}: {e}")
    return loaded

# ── راه‌اندازی اصلی ───────────────────────────
async def main():

    # تنظیمات
    cfg = load_config()
    if not cfg["api_id"] or not cfg["api_hash"]:
        cfg = prompt_config()
    if not cfg["api_id"]:
        print("❌ API ID الزامی است!"); sys.exit(1)

    print(f"\n{'='*52}")
    print(f"  💎 ONYX SELF v{VERSION}")
    print(f"  Database : {DB_PATH}")
    print(f"  Session  : {cfg['session']}.session")
    print(f"{'='*52}\n")

    # ذخیره زمان شروع
    db_set("onyx_profile", "start_time", str(int(_time.time())))

    # ایجاد کلاینت
    client = TelegramClient(
        str(BASE_DIR / cfg["session"]),
        int(cfg["api_id"]),
        cfg["api_hash"],
        device_model  = "ONYX SELF V7 PRO'S",
        system_version = "Termux/Linux",
        app_version    = f"v{VERSION}",
        lang_code      = "fa",
        system_lang_code = "fa-IR",
    )

    # ── بارگذاری ماژول‌ها ───────────────────
    print("⏳ بارگذاری ماژول‌ها...")
    module_results = {}

    register_all(client)

    # ── پلاگین‌های خارجی ────────────────────
    plg_count = load_external_plugins(client)
    if plg_count:
        print(f"\n🧩 {plg_count} پلاگین خارجی لود شد.")

    # ── اتصال و لاگین ───────────────────────
    print("\n⏳ اتصال به تلگرام...")
    try:
        if cfg.get("phone"):
            await client.start(phone=cfg["phone"])
        else:
            await client.start()
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}")
        traceback.print_exc()
        sys.exit(1)

    me = await client.get_me()
    print(f"\n✅ وارد شدید: {me.first_name} (@{me.username or me.id})")

    # ── شروع task های پس‌زمینه ──────────────
    background_tasks = []

    async def smart_queue_runner(client_inner):
        while True:
            try:
                now_s = iran_now().strftime("%Y/%m/%d %H:%M:%S")
                with _db_lock:
                    conn = get_conn()
                    rows = conn.execute(
                        "SELECT * FROM smart_queue WHERE done=0 AND send_at<=? LIMIT 10", (now_s,)
                    ).fetchall()
                for r in rows:
                    try:
                        await client_inner.send_message(r["target"], r["text"])
                    except Exception as eq:
                        logger.warning(f"Queue: {eq}")
                    with _db_lock:
                        conn = get_conn()
                        conn.execute("UPDATE smart_queue SET done=1 WHERE id=?", (r["id"],))
                        conn.commit()
            except Exception as e:
                logger.debug(f"Queue runner: {e}")
            await asyncio.sleep(30)

    async def online_notifier_loop(client_inner):
        while True:
            try:
                with _db_lock:
                    conn = get_conn()
                    rows = conn.execute("SELECT uid FROM online_watch WHERE active=1").fetchall()
                for row in rows:
                    try:
                        u = await client_inner.get_entity(row["uid"])
                        status = type(u.status).__name__ if hasattr(u, "status") else "unknown"
                        with _db_lock:
                            conn = get_conn()
                            last = conn.execute(
                                "SELECT status FROM online_log WHERE uid=? ORDER BY id DESC LIMIT 1",
                                (u.id,)
                            ).fetchone()
                        if not last or last["status"] != status:
                            with _db_lock:
                                conn = get_conn()
                                conn.execute(
                                    "INSERT INTO online_log(uid,status,ts) VALUES(?,?,?)",
                                    (u.id, status, now_str())
                                )
                                conn.commit()
                    except Exception:
                        pass
                await asyncio.sleep(60)
            except Exception as e:
                logger.debug(f"Online notifier: {e}")
                await asyncio.sleep(120)

    async def achievement_checker_loop(client_inner):
        ACHV = {
            "first_cmd":  ("🏆 اولین دستور", lambda: profile_val("cmds_executed") >= 1),
            "cmd_10":     ("🥈 ۱۰ دستور",    lambda: profile_val("cmds_executed") >= 10),
            "cmd_100":    ("🥇 ۱۰۰ دستور",   lambda: profile_val("cmds_executed") >= 100),
            "cmd_1000":   ("💎 هزار دستور",   lambda: profile_val("cmds_executed") >= 1000),
            "level_5":    ("⭐ سطح ۵",        lambda: profile_val("level") >= 5),
            "level_10":   ("🌟 سطح ۱۰",       lambda: profile_val("level") >= 10),
            "active_7":   ("📅 ۷ روز فعال",   lambda: profile_val("active_days") >= 7),
            "active_30":  ("🗓️ ۳۰ روز فعال", lambda: profile_val("active_days") >= 30),
            "downloader": ("📥 اولین دانلود", lambda: profile_val("downloads") >= 1),
            "dl_master":  ("📦 ۱۰ دانلود",    lambda: profile_val("downloads") >= 10),
        }
        while True:
            try:
                with _db_lock:
                    conn = get_conn()
                    unlocked = {r["id"] for r in conn.execute("SELECT id FROM achievements").fetchall()}
                for aid, (title, check_fn) in ACHV.items():
                    if aid not in unlocked and check_fn():
                        with _db_lock:
                            conn = get_conn()
                            conn.execute(
                                "INSERT OR IGNORE INTO achievements(id,title,ts) VALUES(?,?,?)",
                                (aid, title, now_str())
                            )
                            conn.commit()
                        me_inner = await client_inner.get_me()
                        await client_inner.send_message(me_inner.id, f"🏆 دستاورد جدید!\n{title}")
            except Exception as e:
                logger.debug(f"Achievements: {e}")
            await asyncio.sleep(300)

    t = asyncio.create_task(smart_queue_runner(client))
    background_tasks.append(("smart_queue", t))

    t = asyncio.create_task(online_notifier_loop(client))
    background_tasks.append(("online_notifier", t))

    t = asyncio.create_task(achievement_checker_loop(client))
    background_tasks.append(("achievements", t))

    async def calendar_reminder_loop():
        while True:
            try:
                today = jalali()
                with _db_lock:
                    conn = get_conn()
                    rows = conn.execute("SELECT * FROM calendar WHERE date=?", (today,)).fetchall()
                for r in rows:
                    await client.send_message(me.id,
                        f"📅 یادآوری: {r['type']} — {r['title']}\nتاریخ: {today}")
            except Exception as e:
                logger.debug(f"Calendar: {e}")
            await asyncio.sleep(3600)

    t = asyncio.create_task(calendar_reminder_loop())
    background_tasks.append(("calendar", t))

    async def capsule_checker_loop():
        while True:
            try:
                today = jalali()
                with _db_lock:
                    conn = get_conn()
                    rows = conn.execute(
                        "SELECT * FROM time_capsules WHERE open_date<=? AND opened=0", (today,)
                    ).fetchall()
                for r in rows:
                    await client.send_message(me.id,
                        f"📬 کپسول زمانی باز شد!\nعنوان: {r['title']}\nمحتوا: {r['content'][:200]}")
                    with _db_lock:
                        conn = get_conn()
                        conn.execute("UPDATE time_capsules SET opened=1 WHERE id=?", (r["id"],))
                        conn.commit()
            except Exception as e:
                logger.debug(f"Capsule: {e}")
            await asyncio.sleep(3600)

    t = asyncio.create_task(capsule_checker_loop())
    background_tasks.append(("capsule", t))

    async def birthday_reminder_loop():
        while True:
            try:
                today = jalali()
                today_md = today[5:]
                with _db_lock:
                    conn = get_conn()
                    rows = conn.execute(
                        "SELECT * FROM calendar WHERE type='تولد' AND substr(date,6)=?", (today_md,)
                    ).fetchall()
                for r in rows:
                    await client.send_message(me.id,
                        f"🎂 امروز تولد {r['title']} است!\nتبریک بگو! 🎉")
            except Exception as e:
                logger.debug(f"Birthday: {e}")
            await asyncio.sleep(3600)

    t = asyncio.create_task(birthday_reminder_loop())
    background_tasks.append(("birthday", t))

    # ── V9: Personal Radar background loop ──
    async def radar_background_loop():
        """بررسی دوره‌ای برای رویدادهای مهم"""
        while True:
            try:
                with _db_lock:
                    conn = get_conn()
                    pending = conn.execute(
                        "SELECT COUNT(*) FROM store_orders WHERE status='pending'"
                    ).fetchone()[0]
                    low_stock = conn.execute(
                        "SELECT COUNT(*) FROM store_products p WHERE p.active=1 AND "
                        "(SELECT COUNT(*) FROM store_configs c WHERE c.product_id=p.id AND c.sold=0) = 0"
                    ).fetchone()[0]
                if pending > 5:
                    _bb_log_v9("radar_alert", f"{pending} سفارش pending", "warning")
                if low_stock > 0:
                    _bb_log_v9("radar_alert", f"{low_stock} محصول بدون موجودی", "warning")
            except Exception as e:
                logger.debug(f"RadarLoop: {e}")
            await asyncio.sleep(1800)

    t = asyncio.create_task(radar_background_loop())
    background_tasks.append(("radar_v9", t))

    # ── V9: ساعت — بازیابی خودکار پس از Restart ──
    try:
        if _clock_is_active():
            logger.info("⏰ V9: بازیابی خودکار ساعت از دیتابیس...")
            _clock_task = asyncio.create_task(_clock_loop(client))
            background_tasks.append(("clock_v9", _clock_task))
    except Exception as e:
        logger.warning(f"⏰ خطا در بازیابی ساعت: {e}")

    # ── V9: Self-Healing — بررسی دوره‌ای task های معیوب ──
    async def self_healing_loop():
        """بررسی و ترمیم task های پس‌زمینه"""
        await asyncio.sleep(60)   # صبر کن همه task ها شروع شوند
        while True:
            try:
                for i, (name, task) in enumerate(background_tasks):
                    if task.done() and not task.cancelled():
                        exc = task.exception() if not task.cancelled() else None
                        if exc:
                            _bb_log_v9("self_heal", f"Task '{name}' crashed: {exc}", "error")
                            logger.warning(f"🛡️ Self-Healing: Task '{name}' دچار خطا شد: {exc}")
            except Exception as e:
                logger.debug(f"SelfHeal: {e}")
            await asyncio.sleep(300)

    t = asyncio.create_task(self_healing_loop())
    background_tasks.append(("self_heal_v9", t))

    # ── پیام خوش‌آمد ────────────────────────
    total_cmds = sum(len(v) for v in FULL_MENU.values())
    clock_restored = "✅ ساعت بازیابی شد" if _clock_is_active() else ""
    await client.send_message(me.id, (
        f"💎 **ONYX SELF v{VERSION} — نسخه V9** آماده است!\n\n"
        f"👤 {me.first_name} | {now_str()}\n"
        f"📅 تاریخ شمسی: {jalali()}\n"
        f"📚 {total_cmds} دستور فعال\n"
        f"🧩 {plg_count} پلاگین خارجی\n"
        f"🗄️ دیتابیس: {DB_PATH}\n"
        + (f"⏰ {clock_restored}\n" if clock_restored else "")
        + f"\n✨ قابلیت‌های V9:\n"
        f"• دانش محصول (دانش_لیست)\n"
        f"• Black Box (بلک_باکس)\n"
        f"• Control Tower (برج_کنترل)\n"
        f"• Smart Negotiator (مذاکره)\n"
        f"• Event Replay (ریپلی_سفارش)\n"
        f"• +12 قابلیت جدید دیگر\n\n"
        f"راهنما: **منو** یا **برج_کنترل**\n"
        f"{WATERMARK}"
    ))

    print(f"\n🚀 ONYX SELF v{VERSION} آماده است!")
    print(f"📚 {total_cmds} دستور فعال")
    print("Ctrl+C برای خروج\n")

    # ── اجرای اصلی ──────────────────────────
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n\n👋 ONYX خاموش شد.")
    finally:
        for name, task in background_tasks:
            try:
                task.cancel()
                await asyncio.sleep(0.1)
            except Exception:
                pass
        await client.disconnect()
        print("✅ اتصال قطع شد.")




if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 خروج")
    except Exception as e:
        print(f"\n❌ خطای بحرانی: {e}")
        traceback.print_exc()
        sys.exit(1)
