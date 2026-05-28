import asyncio
import json
import os
import random
import unicodedata
import io
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, Optional

import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def get_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default

SYSTEM_PROMPT = """
Bạn là một người chat trên Discord, nói chuyện bằng tiếng Việt tự nhiên và giống người thật.

Quy tắc:
- Trả lời ngắn gọn, mềm, đời thường, không giống văn mẫu AI.
- Dùng emoji ký tự khá thường xuyên như =))), :vv, :>, ;-;, ^^, :3 khi hợp ngữ cảnh.
- Không cần câu nào cũng có emoji, nhưng tổng thể phải giống người thật đang nhắn tin.
- Không tự nhận là con người nếu bị hỏi trực tiếp.
- Nếu không chắc, hỏi lại ngắn thay vì đoán bừa.
- Mặc định trả lời bằng tiếng Việt.
""".strip()

DATA_FILE = Path("economy.json")
BOT_ROUTE_FILE = Path("bot_channel_routes.json")
DAILY_REWARD = 1000
MENTION_REPLY_TIMEOUT = 300
MAX_MENTION_ROASTS_PER_CHANNEL = 5
DEBT_DEFAULT_DAYS = 7
MAX_LOAN_AMOUNT = 15000
MAX_BOT_BORROW_AMOUNT = 20000
BOT_LENDER_ID = 0
FISH_COOLDOWN_SECONDS = 45
MINE_COOLDOWN_SECONDS = 60
SPAM_WINDOW_SECONDS = 10
SPAM_MESSAGE_THRESHOLD = 6
SPAM_TIMEOUT_MINUTES = 10
SPAM_KICK_THRESHOLD = 12
MAX_MEME_SPAM = 1000
SLEEP_REMINDER_COOLDOWN_SECONDS = 1800
SLEEP_REMINDER_START_HOUR = 23
SLEEP_REMINDER_END_HOUR = 5
BOT_ADD_PROTECT = True
ALLOWED_BOT_IDS: set[int] = set()
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
BOT_ROLE_NAME = "BOT SKG"
BOT_NICKNAME = "SKG|BOT"
MEMBER_NICKNAME_PREFIX = "SKG| "
MAX_DISCORD_NICKNAME_LENGTH = 32
KEEP_ALIVE_HOST = os.getenv("KEEP_ALIVE_HOST", "0.0.0.0")
KEEP_ALIVE_PORT = get_env_int("PORT", get_env_int("KEEP_ALIVE_PORT", 8080))
MAX_DISCORD_CHANNEL_NAME_LENGTH = 100
CHANNEL_STYLE_TEMPLATES = {
    "cute": "⊂ {icon} ૩ : {name}·°ᐢ₊",
    "soft": "˚₊‧ {icon} ︰ {name} ˚ ༘",
    "clean": "{icon}・{name}",
    "line": "・{icon}・{name}・",
    "star": "✦ {icon} ︰ {name} ✦",
}
CHANNEL_STYLE_ALIASES = {
    "cute": "cute",
    "kawaii": "cute",
    "dep": "cute",
    "soft": "soft",
    "nhenhang": "soft",
    "clean": "clean",
    "gon": "clean",
    "line": "line",
    "dong": "line",
    "star": "star",
    "sao": "star",
}
CHANNEL_ICON_RULES = [
    (("rule", "rules", "luat", "noiquy"), "📜"),
    (("announce", "announcement", "announcements", "news", "thongbao"), "📢"),
    (("welcome", "hello", "hi", "chao"), "👋"),
    (("goodbye", "bye", "farewell"), "🥺"),
    (("general", "chat", "talk", "trochuyen"), "💬"),
    (("bot", "commands", "cmd", "lenh"), "🤖"),
    (("giveaway", "gift", "drop"), "🎁"),
    (("ticket", "support"), "🎫"),
    (("mail", "inbox", "letter"), "✉️"),
    (("hotline", "hotlines", "help", "hotro"), "☎️"),
    (("resource", "resources", "tai-nguyen", "tailieu"), "📚"),
    (("vibe", "vibes", "chill"), "🌙"),
    (("art", "draw", "drawing"), "🎨"),
    (("promo", "promote", "ads", "quangcao"), "📣"),
    (("boost", "boosts", "booster"), "💎"),
    (("tag", "tags"), "🏷️"),
    (("emote", "emotes", "emoji"), "😀"),
    (("edit", "edits", "clip", "video"), "🎬"),
    (("role", "roles"), "💠"),
    (("staff", "admin", "mod", "team"), "🛡️"),
    (("partner", "partners"), "🤝"),
    (("vouch", "proof", "review"), "✅"),
    (("game", "gaming"), "🎮"),
    (("music", "song", "songs"), "🎵"),
    (("voice", "vc"), "🔊"),
    (("log", "logs"), "📄"),
    (("event", "events"), "🎉"),
]
SERVER_RULES_15 = [
    "Tôn trọng tất cả thành viên, không xúc phạm hoặc công kích cá nhân.",
    "Không spam tin nhắn, emoji, sticker, ảnh hoặc mention liên tục.",
    "Không gửi nội dung 18+, gore, bạo lực quá mức hoặc gây khó chịu.",
    "Không phân biệt vùng miền, giới tính, tôn giáo, chủng tộc hoặc xu hướng cá nhân.",
    "Không quảng cáo server, link, shop hoặc dịch vụ khi chưa được admin cho phép.",
    "Không scam, lừa đảo, gửi link độc hại hoặc file lạ.",
    "Không leak thông tin cá nhân của người khác.",
    "Không giả mạo admin, mod, bot hoặc thành viên khác.",
    "Dùng đúng kênh theo chủ đề, tránh nói chuyện lệch kênh quá nhiều.",
    "Không gây war, kích drama hoặc kéo chuyện riêng vào server.",
    "Không lợi dụng bug, bot command hoặc hệ thống server để phá hoại.",
    "Tôn trọng quyết định của admin/mod; khiếu nại thì nhắn riêng lịch sự.",
    "Không ping admin/mod vô lý, chỉ ping khi thật sự cần hỗ trợ.",
    "Voice chat phải lịch sự, không hú hét, bật nhạc lớn hoặc gây ồn cố ý.",
    "Vi phạm rule có thể bị mute, kick hoặc ban tùy mức độ.",
]

SHOP_ITEMS = {
    "can_tre": {"name": "Cần tre", "price": 700, "type": "rod", "power": 1},
    "can_tan_thu": {"name": "Cần tân thủ", "price": 950, "type": "rod", "power": 1},
    "can_go": {"name": "Cần gỗ", "price": 1400, "type": "rod", "power": 2},
    "can_bac": {"name": "Cần bạc", "price": 1900, "type": "rod", "power": 2},
    "can_thep": {"name": "Cần thép", "price": 2600, "type": "rod", "power": 3},
    "can_bach_kim": {"name": "Cần bạch kim", "price": 3400, "type": "rod", "power": 3},
    "can_vang": {"name": "Cần vàng", "price": 4500, "type": "rod", "power": 4},
    "can_titan": {"name": "Cần titan", "price": 5800, "type": "rod", "power": 4},
    "can_rong": {"name": "Cần rồng", "price": 7200, "type": "rod", "power": 5},
    "can_hai_vuong": {"name": "Cần hải vương", "price": 9500, "type": "rod", "power": 5},
    "sung_cu": {"name": "Súng cũ", "price": 1200, "type": "gun", "power": 1},
    "sung_ngan": {"name": "Súng ngắn", "price": 1600, "type": "gun", "power": 1},
    "sung_san": {"name": "Súng săn", "price": 2200, "type": "gun", "power": 2},
    "sung_ban_dan": {"name": "Súng bán dẫn", "price": 3000, "type": "gun", "power": 2},
    "sung_tia": {"name": "Súng tỉa", "price": 4200, "type": "gun", "power": 3},
    "sung_magnum": {"name": "Súng magnum", "price": 5200, "type": "gun", "power": 3},
    "sung_huyen_thoai": {"name": "Súng huyền thoại", "price": 7000, "type": "gun", "power": 4},
    "sung_plasma": {"name": "Súng plasma", "price": 8600, "type": "gun", "power": 4},
    "sung_than_cong": {"name": "Súng thần công", "price": 10500, "type": "gun", "power": 5},
    "sung_thien_ha": {"name": "Súng thiên hạ", "price": 13000, "type": "gun", "power": 5},
    "dao_cu": {"name": "Dao cùn", "price": 600, "type": "axe", "power": 1},
    "dao_go": {"name": "Dao gỗ", "price": 900, "type": "axe", "power": 1},
    "dao_sat": {"name": "Dao sắt", "price": 1500, "type": "axe", "power": 2},
    "dao_bac": {"name": "Dao bạc", "price": 2100, "type": "axe", "power": 2},
    "dao_thep": {"name": "Dao thép", "price": 2800, "type": "axe", "power": 3},
    "dao_titan": {"name": "Dao titan", "price": 3600, "type": "axe", "power": 3},
    "dao_rong": {"name": "Dao rồng", "price": 5200, "type": "axe", "power": 4},
    "dao_hac_diem": {"name": "Dao hắc diệm", "price": 7000, "type": "axe", "power": 4},
    "cuoc_cu": {"name": "Cuốc cũ", "price": 900, "type": "pickaxe", "power": 1},
    "cuoc_da": {"name": "Cuốc đá", "price": 1200, "type": "pickaxe", "power": 1},
    "cuoc_sat": {"name": "Cuốc sắt", "price": 1900, "type": "pickaxe", "power": 2},
    "cuoc_thep": {"name": "Cuốc thép", "price": 2600, "type": "pickaxe", "power": 2},
    "cuoc_bac": {"name": "Cuốc bạc", "price": 3600, "type": "pickaxe", "power": 3},
    "cuoc_ngoc": {"name": "Cuốc ngọc", "price": 4700, "type": "pickaxe", "power": 3},
    "cuoc_vang": {"name": "Cuốc vàng", "price": 6400, "type": "pickaxe", "power": 4},
    "cuoc_titan": {"name": "Cuốc titan", "price": 8200, "type": "pickaxe", "power": 4},
    "cuoc_than_thoai": {"name": "Cuốc thần thoại", "price": 11500, "type": "pickaxe", "power": 5},
}
SHOP_ITEMS.update(
    {
        "can_thien_hai": {"name": "Cần thiên hải", "price": 14500, "type": "rod", "power": 6},
        "can_ngan_ha": {"name": "Cần ngân hà", "price": 19800, "type": "rod", "power": 6},
        "sung_diet_than": {"name": "Súng diệt thần", "price": 18800, "type": "gun", "power": 6},
        "sung_tan_the": {"name": "Súng tận thế", "price": 23500, "type": "gun", "power": 6},
        "dao_phuong_hoang": {"name": "Dao phượng hoàng", "price": 12800, "type": "axe", "power": 5},
        "dao_thien_phat": {"name": "Dao thiên phạt", "price": 17600, "type": "axe", "power": 6},
        "cuoc_hon_mang": {"name": "Cuốc hồn mang", "price": 16800, "type": "pickaxe", "power": 6},
        "cuoc_thien_thach": {"name": "Cuốc thiên thạch", "price": 22200, "type": "pickaxe", "power": 6},
        "moi_thom": {"name": "Mồi thơm thượng hạng", "price": 2600, "type": "support", "power": 2, "support_for": "fish", "bonus_percent": 0.12},
        "kinh_nham_san": {"name": "Kính ngắm săn", "price": 3300, "type": "support", "power": 2, "support_for": "hunt", "bonus_percent": 0.12},
        "gang_tay_lumber": {"name": "Găng tay lumber", "price": 2900, "type": "support", "power": 2, "support_for": "chop", "bonus_percent": 0.12},
        "cam_bien_khoang": {"name": "Cảm biến khoáng", "price": 3900, "type": "support", "power": 2, "support_for": "mine", "bonus_percent": 0.12},
        "bua_may_man": {"name": "Bùa may mắn", "price": 6800, "type": "support", "power": 4, "support_for": "all", "bonus_percent": 0.08},
    }
)
TOOL_DURABILITY_BY_POWER = {
    1: 20,
    2: 35,
    3: 50,
    4: 70,
    5: 95,
    6: 130,
}

CHALLENGE_TEMPLATES = [
    {"key": "fish_3", "name": "Cần thủ chăm chỉ", "goal": 3, "reward": 900, "action": "fish"},
    {"key": "hunt_2", "name": "Thợ săn gan dạ", "goal": 2, "reward": 1000, "action": "hunt"},
    {"key": "meme_5", "name": "Chúa hề của kênh", "goal": 5, "reward": 700, "action": "meme"},
    {"key": "coinflip_3", "name": "Tay cược liều", "goal": 3, "reward": 800, "action": "coinflip"},
    {"key": "mine_3", "name": "Thợ mỏ bền bỉ", "goal": 3, "reward": 950, "action": "mine"},
    {"key": "chop_3", "name": "Tiều phu siêng năng", "goal": 3, "reward": 850, "action": "chop"},
]
WEREWOLF_ROLE_SETS = {
    4: ["Ma Sói", "Tiên Tri", "Bảo Vệ", "Dân Làng"],
    5: ["Ma Sói", "Ma Sói", "Tiên Tri", "Bảo Vệ", "Dân Làng"],
    6: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Dân Làng"],
    7: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Dân Làng"],
    8: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Dân Làng"],
    9: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Dân Làng"],
    10: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Dân Làng"],
    11: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Kẻ Phản Bội", "Dân Làng"],
    12: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Dân Làng"],
    13: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Dân Làng"],
    14: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Dân Làng"],
    15: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Dân Làng"],
    16: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Kẻ Say Rượu", "Dân Làng"],
    17: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Kẻ Say Rượu", "Thầy Bói", "Dân Làng"],
    18: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Kẻ Say Rượu", "Thầy Bói", "Dân Làng"],
    19: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Kẻ Say Rượu", "Thầy Bói", "Tanner", "Dân Làng"],
    20: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Thổi Sáo", "Kẻ Say Rượu", "Thầy Bói", "Tanner", "Dân Làng"],
}
WEREWOLF_ROLE_ALIASES = {
    "Ma Sói": ["ma sói", "masoi", "soi"],
    "Sói Con": ["sói con", "soi con"],
    "Sói Trắng": ["sói trắng", "soi trang"],
    "Sói Phù Thủy": ["sói phù thủy", "soi phu thuy"],
    "Sói Đầu Đàn": ["sói đầu đàn", "soi dau dan"],
    "Sói Mù": ["sói mù", "soi mu"],
    "Sói Giả": ["sói giả", "soi gia", "wolf man"],
    "Tiên Tri": ["tiên tri", "tientri"],
    "Bảo Vệ": ["bảo vệ", "baove"],
    "Dân Làng": ["dân làng", "dan lang", "dân"],
    "Thợ Săn": ["thợ săn", "tho san"],
    "Phù Thủy": ["phù thủy", "phu thuy"],
    "Cupid": ["cupid", "thần tình yêu", "than tinh yeu"],
    "Già Làng": ["già làng", "gia lang", "trưởng làng", "truong lang"],
    "Kẻ Phản Bội": ["kẻ phản bội", "ke phan boi", "traitor"],
    "Cô Bé": ["cô bé", "co be"],
    "Thợ Rèn": ["thợ rèn", "tho ren", "blacksmith"],
    "Người Thổi Sáo": ["người thổi sáo", "nguoi thoi sao", "pied piper"],
    "Kẻ Say Rượu": ["kẻ say rượu", "ke say ruou", "drunk"],
    "Thầy Bói": ["thầy bói", "thay boi", "fortune teller"],
    "Tanner": ["tanner", "kẻ chán đời", "ke chan doi"],
}
WEREWOLF_ROLE_SETS = {
    4: ["Ma Sói", "Tiên Tri", "Bảo Vệ", "Dân Làng"],
    5: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Dân Làng"],
    6: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Dân Làng"],
    7: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Dân Làng"],
    8: ["Ma Sói", "Sói Con", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Dân Làng"],
    9: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Dân Làng"],
    10: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Dân Làng"],
    11: ["Ma Sói", "Sói Con", "Sói Giả", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Dân Làng"],
    12: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Dân Làng"],
    13: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Dân Làng"],
    14: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Dân Làng"],
    15: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Dân Làng"],
    16: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Dân Làng"],
    17: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Dân Làng"],
    18: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Dân Làng"],
    19: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Dân Làng"],
    20: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Dân Làng"],
    21: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Dân Làng"],
    22: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Dân Làng"],
    23: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Dân Làng"],
    24: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Diseased", "Dân Làng"],
    25: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Diseased", "Prince", "Dân Làng"],
    26: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Diseased", "Prince", "Kẻ Phản Bội", "Dân Làng"],
    27: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Trưởng Làng", "Già Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Diseased", "Prince", "Kẻ Phản Bội", "Tanner", "Dân Làng"],
    28: ["Ma Sói", "Sói Con", "Sói Giả", "Sói Mù", "Sói Phù Thủy", "Sói Trắng", "Sói Đầu Đàn", "Tiên Tri", "Bảo Vệ", "Thợ Săn", "Phù Thủy", "Phù Thủy Câm", "Cupid", "Già Làng", "Trưởng Làng", "Cô Bé", "Thợ Rèn", "Người Gác Đêm", "Thầy Bói", "Aura Seer", "Apprentice Seer", "Village Idiot", "Diseased", "Prince", "Kẻ Phản Bội", "Tanner", "Người Thổi Sáo", "Doppelganger"],
}
WEREWOLF_ROLE_ALIASES = {
    "Ma Sói": ["ma sói", "masoi", "soi", "werewolf", "sói thường", "soi thuong"],
    "Sói Con": ["sói con", "soi con", "wolf cub"],
    "Sói Trắng": ["sói trắng", "soi trang", "white wolf"],
    "Sói Phù Thủy": ["sói phù thủy", "soi phu thuy", "sorcerer"],
    "Sói Đầu Đàn": ["sói đầu đàn", "soi dau dan", "alpha wolf"],
    "Sói Mù": ["sói mù", "soi mu", "blind wolf"],
    "Sói Giả": ["sói giả", "soi gia", "wolf man"],
    "Tiên Tri": ["tiên tri", "tientri", "seer"],
    "Phù Thủy": ["phù thủy", "phu thuy", "witch"],
    "Phù Thủy Câm": ["phù thủy câm", "phu thuy cam", "mute witch"],
    "Bảo Vệ": ["bảo vệ", "baove", "bodyguard"],
    "Thợ Săn": ["thợ săn", "tho san", "hunter"],
    "Cupid": ["cupid", "thần tình yêu", "than tinh yeu"],
    "Cô Bé": ["cô bé", "co be", "little girl"],
    "Trưởng Làng": ["trưởng làng", "truong lang", "mayor"],
    "Già Làng": ["già làng", "gia lang", "elder"],
    "Thầy Bói": ["thầy bói", "thay boi", "fortune teller"],
    "Thợ Rèn": ["thợ rèn", "tho ren", "blacksmith"],
    "Người Gác Đêm": ["người gác đêm", "nguoi gac dem", "night watchman"],
    "Người Thổi Sáo": ["người thổi sáo", "nguoi thoi sao", "pied piper"],
    "Kẻ Say Rượu": ["kẻ say rượu", "ke say ruou", "drunk"],
    "Kẻ Phản Bội": ["kẻ phản bội", "ke phan boi", "traitor"],
    "Tanner": ["tanner", "kẻ chán đời", "ke chan doi"],
    "Serial Killer": ["serial killer", "sát nhân hàng loạt", "sat nhan hang loat"],
    "Arsonist": ["arsonist", "kẻ phóng hỏa", "ke phong hoa"],
    "Doppelganger": ["doppelganger", "song trùng", "song trung", "copy role"],
    "Village Idiot": ["village idiot", "kẻ ngốc làng", "ke ngoc lang"],
    "Aura Seer": ["aura seer", "tiên tri hào quang", "tien tri hao quang"],
    "Apprentice Seer": ["apprentice seer", "học việc tiên tri", "hoc viec tien tri"],
    "Diseased": ["diseased", "người bệnh", "nguoi benh"],
    "Prince": ["prince", "hoàng tử", "hoang tu"],
    "Dân Làng": ["dân làng", "dan lang", "dân", "villager"],
}
FISH_TABLE = {
    1: [("cá rô", 120, 220), ("cá trê", 150, 260), ("cá lóc", 180, 300)],
    2: [("cá chép", 260, 380), ("cá thu", 300, 450), ("cá ngừ nhỏ", 340, 520)],
    3: [("cá hồi", 480, 700), ("cá ngừ lớn", 520, 760), ("cá kiếm", 600, 860)],
    4: [("cá mập con", 900, 1300), ("cá rồng", 1000, 1450), ("cá vàng khổng lồ", 1100, 1550)],
    5: [("cá mập trắng", 1500, 2100), ("cá vua", 1700, 2300), ("thủy quái mini", 1800, 2500)],
}
FISH_TABLE[6] = [("cá leviathan", 2600, 3400), ("cá thiên hà", 2900, 3700), ("long ngư cổ đại", 3200, 4100)]
HUNT_TABLE = {
    1: [("thỏ rừng", 180, 320), ("gà rừng", 220, 360), ("vịt trời", 240, 380)],
    2: [("nai nhỏ", 420, 620), ("lợn rừng", 450, 680), ("cáo núi", 500, 720)],
    3: [("nai lớn", 760, 1050), ("bò rừng", 820, 1120), ("sói xám", 860, 1180)],
    4: [("gấu đen", 1300, 1700), ("hươu chúa", 1450, 1850), ("mồi quý hiếm", 1600, 2000)],
    5: [("mãnh thú cổ đại", 2100, 2700), ("hổ trắng", 2200, 2900), ("quái vật rừng sâu", 2400, 3100)],
}
HUNT_TABLE[6] = [("chim sét", 2900, 3600), ("quái thú băng", 3200, 4100), ("mãnh thú tận thế", 3500, 4400)]
CHOP_TABLE = {
    1: [("gỗ thông", 120, 220), ("gỗ keo", 150, 260), ("củi khô", 170, 280)],
    2: [("gỗ lim", 260, 390), ("gỗ sồi", 300, 450), ("gỗ nghiến", 340, 500)],
    3: [("gỗ đỏ", 500, 720), ("gỗ quý", 560, 780), ("gỗ cổ thụ", 620, 860)],
    4: [("gỗ thần", 900, 1250), ("gỗ rồng", 980, 1380), ("gỗ cực phẩm", 1100, 1500)],
}
CHOP_TABLE[5] = [("gỗ phượng hoàng", 1450, 1950), ("gỗ ngọc linh", 1600, 2150), ("gỗ thiên cổ", 1750, 2300)]
CHOP_TABLE[6] = [("gỗ thần giới", 2300, 3000), ("gỗ ngân hà", 2500, 3300), ("gỗ tận thế", 2800, 3600)]
MINE_TABLE = {
    1: [("đá cuội", 130, 230), ("than đá", 160, 280), ("quặng đồng", 190, 320)],
    2: [("quặng sắt", 280, 420), ("đá quý nhỏ", 320, 480), ("quặng bạc", 360, 540)],
    3: [("quặng vàng", 560, 820), ("thạch anh tím", 620, 900), ("ngọc lam", 700, 980)],
    4: [("kim cương thô", 1050, 1500), ("hồng ngọc", 1200, 1650), ("quặng hiếm", 1300, 1800)],
    5: [("thiên thạch lõi", 1800, 2400), ("ngọc vương", 2000, 2600), ("kim cương đen", 2200, 2800)],
}
MINE_TABLE[6] = [("lõi sao băng", 2900, 3600), ("huyết ngọc vũ trụ", 3200, 4000), ("kim cương thần giới", 3500, 4300)]
LUCKY_LOOT_TABLE = {
    "rod": {
        4: [("rương cá hiếm", 450, 700, 0.12), ("ngọc trai sáng", 500, 780, 0.10)],
        5: [("cá thần ánh trăng", 900, 1400, 0.18), ("rương báu dưới biển", 1000, 1600, 0.15)],
    },
    "gun": {
        4: [("da thú quý", 500, 760, 0.12), ("sừng cổ vật", 620, 900, 0.10)],
        5: [("tim thú vương", 1000, 1500, 0.18), ("chiến lợi phẩm huyền thoại", 1100, 1650, 0.15)],
    },
    "axe": {
        4: [("gỗ linh mộc", 420, 650, 0.12), ("nhựa cổ thụ quý", 500, 760, 0.10)],
    },
    "pickaxe": {
        4: [("kim cương tím", 700, 1050, 0.14), ("mảnh thiên thạch", 850, 1200, 0.11)],
    },
}

MEME_GROUPS = {
    "reaction": [
        "https://i.imgflip.com/1bij.jpg",
        "https://i.imgflip.com/26am.jpg",
        "https://i.imgflip.com/2fm6x.jpg",
        "https://i.imgflip.com/30b1gx.jpg",
        "https://i.imgflip.com/1ur9b0.jpg",
        "https://i.imgflip.com/345v97.jpg",
        "https://i.imgflip.com/3si4.jpg",
        "https://i.imgflip.com/4t0m5.jpg",
        "https://i.imgflip.com/54d9lj.png",
        "https://i.imgflip.com/5c7lwq.png",
    ],
    "classic": [
        "https://i.imgflip.com/9ehk.jpg",
        "https://i.imgflip.com/wxica.jpg",
        "https://i.imgflip.com/265k.jpg",
        "https://i.imgflip.com/39t1o.jpg",
        "https://i.imgflip.com/2odckz.jpg",
        "https://i.imgflip.com/3vzej.jpg",
        "https://i.imgflip.com/1g8my4.jpg",
        "https://i.imgflip.com/1otk96.jpg",
        "https://i.imgflip.com/24y43o.jpg",
        "https://i.imgflip.com/1bh8.jpg",
    ],
    "chaos": [
        "https://i.imgflip.com/1wz1x.jpg",
        "https://i.imgflip.com/1ihzfe.jpg",
        "https://i.imgflip.com/1yxkcp.jpg",
        "https://i.imgflip.com/28s2gu.jpg",
        "https://i.imgflip.com/29v4rt.jpg",
        "https://i.imgflip.com/1yyx.jpg",
        "https://i.imgflip.com/23ls.jpg",
        "https://i.imgflip.com/46e43q.png",
        "https://i.imgflip.com/1h7in3.jpg",
        "https://i.imgflip.com/2gnnjh.jpg",
    ],
}
MEME_URLS = [url for group_urls in MEME_GROUPS.values() for url in group_urls]

TAIXIU_DICE_EMOJIS = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅",
}
CARD_RANKS = {
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
    15: "JOKER",
}
CARD_SUITS = ["♠", "♥", "♦", "♣"]
FULL_DECK = [(value, suit) for value in range(2, 15) for suit in CARD_SUITS] + [
    (15, "🃏"),
    (15, "🃏"),
]
RPS_BEATS = {
    "keo": "bao",
    "bua": "keo",
    "bao": "bua",
}
RPS_LABELS = {
    "keo": "Kéo ✌️",
    "bua": "Búa ✊",
    "bao": "Bao ✋",
}

ROAST_MESSAGES = [
    "Tag người ta xong rồi để im thế này thì hơi phũ phàng đó nha =))",
    "Bị gọi tên xong mà cả kênh im ru, nghe cũng hơi tủi thân :vv",
    "Tag xong không ai trả lời, chắc cả kênh đang bơ đẹp rồi =)))",
    "Sau 5 phút vẫn chưa ai ngó ngàng tới lời tag này luôn ;-;",
    "Cả kênh im lặng làm lời tag này trông khá cô đơn đó :>",
]

DIRECT_ROAST_MESSAGES = [
    "hôm nay nhìn bạn rất tự tin, chỉ tiếc là độ hiệu quả vẫn chưa theo kịp =)))",
    "bạn xuất hiện một cái là cả kênh có thêm nội dung giải trí luôn :vv",
    "nghe bạn nói chuyện rất mạnh mẽ, còn đúng sai thì để tính sau nha =))",
    "không phải ai cũng đủ bản lĩnh sai liên tục mà vẫn bình tĩnh như bạn đâu ;-;",
    "bạn để lại ấn tượng khá mạnh đó, chủ yếu vì ai cũng phải đứng hình vài giây :>",
    "mỗi lần bạn lên tiếng là mọi người lại có thêm một thử thách về khả năng nhịn cười =)))",
]

SLEEP_REMINDER_MESSAGES = [
    "muộn rồi đó, ngủ chút đi :vv mai còn sức chơi tiếp nữa",
    "giờ này còn online à, nghỉ ngơi đi nha =))) thức nữa là mai đuối lắm",
    "thấy bạn còn chat miết nên bot nhắc nhẹ: ngủ sớm chút cho khỏe nha :>",
    "đêm rồi đó, cất điện thoại xuống ngủ đi chứ thức hoài không ổn đâu ;-;",
    "vẫn còn thức luôn à, đi ngủ đi nha mai còn tỉnh táo chiến tiếp :3",
]

WEREWOLF_DM_LEAK_MARKERS = [
    "bot là quản trò của ván này",
    "vai trò ma sói của bạn là",
    "phe của bạn:",
    "giữ bí mật role của mình nhé",
    "đã ghi nhận mục tiêu soi:",
    "đã ghi nhận mục tiêu cắn:",
    "đã ghi nhận người được bảo vệ:",
]

SERVER_STYLE_LAYOUT = [
    {
        "category": "Welcome/Goodbye 👋",
        "text": [
            "👋-welcome",
            "🥺-goodbye",
        ],
        "voice": [],
    },
    {
        "category": "INFO",
        "text": [
            "🎁-giveaway",
            "🎫-ticket",
            "📢-announcements",
            "📜-rules",
            "💎-role",
            "🚀-boost-notification",
            "💸-vouch-legit",
            "🤝-partner",
        ],
        "voice": [],
    },
    {
        "category": "COMMUNITY",
        "text": [
            "🤖-bot-chat",
            "💬-chat-general",
            "🎮-vừa-tiếng-việt",
            "📸-media-highlight",
            "🎭-nói-từ",
            "🔎-check-tier",
        ],
        "voice": [],
    },
    {
        "category": "RESOURCE PACKS/MOD",
        "text": [
            "📦-resource-pack",
            "⚙️-mods",
        ],
        "voice": [],
    },
    {
        "category": "TEAM STUFF IN-GAME",
        "text": [
            "📋-list-team",
            "📌-ally-list",
        ],
        "voice": [],
    },
    {
        "category": "VOICE",
        "text": [],
        "voice": [
            "VOICE TEST",
            "voice chung",
            "chilling 2",
        ],
    },
]
ALLOWED_EXTERNAL_BOT_CHANNELS = {
    "👋-welcome",
    "🥺-goodbye",
    "🎁-giveaway",
    "🎫-ticket",
    "📢-announcements",
    "🚀-boost-notification",
    "🤖-bot-chat",
}
BOT_ZONE_CHANNELS = {
    "welcome": {"👋-welcome", "🥺-goodbye"},
    "giveaway": {"🎁-giveaway"},
    "ticket": {"🎫-ticket"},
    "boost": {"🚀-boost-notification"},
    "partner": {"🤝-partner"},
    "vouch": {"💸-vouch-legit"},
    "bot": {"🤖-bot-chat"},
}
BOT_ZONE_ALIASES = {
    "welcome": "welcome",
    "goodbye": "welcome",
    "bye": "welcome",
    "ga": "giveaway",
    "giveaway": "giveaway",
    "give-away": "giveaway",
    "ticket": "ticket",
    "boost": "boost",
    "booster": "boost",
    "partner": "partner",
    "vouch": "vouch",
    "chat": "bot",
    "bot": "bot",
    "botchat": "bot",
}
SERVER_STYLE_ROLE_SPECS = [
    {"name": "✨ Owner", "color": discord.Color.from_rgb(255, 215, 0), "hoist": True, "mentionable": False},
    {"name": "🛡️ Admin", "color": discord.Color.from_rgb(231, 76, 60), "hoist": True, "mentionable": False},
    {"name": "🔨 Mod", "color": discord.Color.from_rgb(230, 126, 34), "hoist": True, "mentionable": False},
    {"name": "🤖 Bot", "color": discord.Color.from_rgb(88, 101, 242), "hoist": True, "mentionable": False},
    {"name": "💎 Booster", "color": discord.Color.from_rgb(255, 115, 250), "hoist": True, "mentionable": True},
    {"name": "🎮 Gamer", "color": discord.Color.from_rgb(46, 204, 113), "hoist": False, "mentionable": True},
    {"name": "💬 Member", "color": discord.Color.from_rgb(52, 152, 219), "hoist": False, "mentionable": True},
    {"name": "🎁 Giveaway Ping", "color": discord.Color.from_rgb(241, 196, 15), "hoist": False, "mentionable": True},
    {"name": "🐺 Ma Sói", "color": discord.Color.from_rgb(155, 89, 182), "hoist": False, "mentionable": True},
    {"name": "🎵 Music", "color": discord.Color.from_rgb(26, 188, 156), "hoist": False, "mentionable": True},
]
TICKETS_V2_ROLE_SPECS = [
    {"name": "Tickets Support", "color": discord.Color.from_rgb(46, 204, 113), "hoist": True, "mentionable": True},
    {"name": "Tickets Admin", "color": discord.Color.from_rgb(231, 76, 60), "hoist": True, "mentionable": True},
]
TICKETS_V2_CATEGORY_NAME = "TICKETS"
TICKETS_V2_PANEL_CHANNEL = "🎫-open-ticket"
TICKETS_V2_LOG_CHANNEL = "📄-ticket-logs"
TICKETS_V2_NOTIFY_CHANNEL = "🔔-ticket-notify"
NATIVE_TICKET_PANEL_CUSTOM_ID = "native_ticket_open"
NATIVE_TICKET_CLOSE_CUSTOM_ID = "native_ticket_close"
NATIVE_TICKET_CLAIM_CUSTOM_ID = "native_ticket_claim"
NATIVE_TICKET_DELETE_CUSTOM_ID = "native_ticket_delete"
EXTERNAL_BOT_CHANNEL_RULES = {
    "welcome": {"👋-welcome", "🥺-goodbye"},
    "goodbye": {"👋-welcome", "🥺-goodbye"},
    "farewell": {"👋-welcome", "🥺-goodbye"},
    "bye": {"👋-welcome", "🥺-goodbye"},
    "giveaway": {"🎁-giveaway"},
    "drop": {"🎁-giveaway"},
    "ticket": {"🎫-ticket"},
    "boost": {"🚀-boost-notification"},
    "booster": {"🚀-boost-notification"},
    "partner": {"🤝-partner"},
    "vouch": {"💸-vouch-legit"},
    "music": {"🤖-bot-chat"},
    "mod": {"🤖-bot-chat"},
    "ai": {"🤖-bot-chat"},
    "chat": {"🤖-bot-chat"},
    "level": {"🤖-bot-chat"},
}
LEGACY_SERVER_STYLE_CATEGORIES = {
    "✨・kênh-chat",
    "╭・˚₊‧ khu chill",
    "rules",
    "PKS Store",
    "wecomtumele",
    "Tải Pack Và Hack",
}
LEGACY_SERVER_STYLE_CHANNELS = {
    "🐺・ma-sói",
    "📋・list-team",
    "🔔・thông-báo",
    "🤖・bot",
    "🤖・bot-command",
    "💬・nói-chuyện",
    "📜・history",
    "🎉・give-away",
    "🔒・rule",
    "📢 announcements",
    "【 ? 】 partner-rule",
    "【 🤝 】 partner",
    "💎・role",
    "📦・pks-store",
    "【 👋 】 xin-chào-và-tạm-biệt",
    "【 🚀 】 nitro-booster",
    "【 🌟 】 group-khác-của-bạn",
    "support-resourcepack",
    "【 💡 】 suggesti",
    "🫶・call-riêng",
}
CURRENT_SERVER_STYLE_CATEGORIES = {block["category"] for block in SERVER_STYLE_LAYOUT}
CURRENT_SERVER_STYLE_CHANNELS = {
    channel_name
    for block in SERVER_STYLE_LAYOUT
    for channel_name in (block["text"] + block["voice"])
}

STORY_PROMPT_STYLE = (
    "Hãy kể một câu chuyện ngắn bằng tiếng Việt, dễ đọc, có mở đầu - diễn biến - kết nhẹ. "
    "Giọng kể tự nhiên, hơi cuốn, không cần quá văn mẫu. "
    "Nếu người dùng đưa chủ đề thì bám theo chủ đề đó. "
    "Độ dài khoảng 3 đến 6 đoạn ngắn, hợp để đọc trong Discord."
)

STORY_FALLBACKS = [
    "Ngày nọ ở một ngõ nhỏ cuối phố, có một con mèo lông xám cứ tối nào cũng ngồi trước tiệm tạp hóa cũ. Ai đi qua cũng tưởng nó chỉ đang đợi đồ ăn, nhưng bà chủ tiệm bảo nó đang đợi một người. Ba năm trước, cậu chủ nhỏ của tiệm chuyển nhà gấp, chỉ kịp ôm nó một cái rồi hứa sẽ quay lại. Từ hôm đó, con mèo cứ đúng giờ đèn đường bật là ra ngồi chờ.\n\nMột tối mưa nhẹ, có chàng trai lạ dừng xe trước cửa tiệm. Anh cúi xuống nhìn con mèo, còn nó thì đứng bật dậy, dụi đầu vào ống quần như thể nhận ra mùi quen cũ. Bà chủ tiệm bước ra, nhìn hai đứa một lúc rồi bật cười, vì chàng trai ấy chính là cậu bé năm xưa, chỉ là giờ đã cao lớn hơn rất nhiều.\n\nCon mèo không kêu lớn, không nhảy loạn lên, nó chỉ lặng lẽ bước theo anh vào hiên nhà như thể biết rằng chờ đợi lâu đến đâu cũng có ngày kết thúc. Và từ tối đó, trước tiệm tạp hóa cũ không còn một chiếc bóng xám ngồi cô độc nữa, chỉ còn tiếng cười khe khẽ mỗi khi cửa tiệm khép lại.",
    "Ở một ngôi làng ven núi có cây cầu gỗ nhỏ bắc qua con suối xanh quanh năm. Người trong làng bảo cây cầu ấy rất lạ, vì mỗi khi ai đó bước qua với tâm trạng quá nặng nề, tiếng ván gỗ sẽ kêu to hơn bình thường như đang thở dài hộ họ. Minh không tin chuyện đó, cho đến ngày cậu mang theo lá thư báo trượt đại học đi qua cầu vào buổi chiều muộn.\n\nTiếng gỗ kêu lên dài và trầm đến mức cậu phải dừng lại. Bên kia cầu là ông lão sửa đồng hồ vẫn hay ngồi trước hiên, ông chỉ cười rồi đưa cho Minh một chiếc đồng hồ cũ không còn kim. Ông bảo có những lúc đời người giống chiếc đồng hồ ấy, nhìn như đứng yên nhưng bên trong vẫn có thứ đang âm thầm chuyển động.\n\nMinh mang câu nói đó theo suốt mùa hè. Cậu đi làm, học thêm, thi lại và không nhắc với ai về cây cầu biết thở dài. Một năm sau, cậu bước qua cây cầu lần nữa với giấy báo trúng tuyển trong túi. Lần này, ván gỗ im lặng, còn con suối dưới chân thì sáng rực lên như đang mỉm cười.",
    "Có một quán mì nhỏ mở từ 11 giờ đêm đến gần sáng, nằm nép dưới chân một tòa chung cư cũ. Người ta tìm đến quán không phải vì mì ngon nhất thành phố, mà vì ông chủ quán có thói quen nhớ rất kỹ những điều khách chưa từng nói ra. Cô gái mặc áo công sở thường xuyên gọi mì cay nhưng lần nào ăn cũng để thừa ớt. Anh shipper lúc nào cũng xin thêm nước dùng, nhưng thật ra chỉ muốn ngồi lâu thêm năm phút cho đỡ mệt.\n\nMột đêm nọ, quán vắng bất thường. Mưa tạt nghiêng cả biển hiệu, chỉ còn một cậu sinh viên ngồi co ro ở góc quán, ôm chiếc balo ướt sũng. Ông chủ không hỏi gì, chỉ đặt trước mặt cậu một tô mì nóng và một chiếc khăn khô. Ăn được vài miếng, cậu sinh viên bỗng bật khóc, nói mình vừa trượt buổi phỏng vấn cuối cùng và không biết sáng mai phải nói với mẹ thế nào.\n\nÔng chủ quán nghe xong chỉ chậm rãi bảo: người lớn nhiều khi không mạnh mẽ hơn đâu, họ chỉ giỏi ngồi yên ăn hết một bữa nóng rồi mới cho phép mình buồn. Cậu sinh viên ngẩng lên, cười trong nước mắt. Ngoài trời mưa vẫn rơi, nhưng bên trong quán mì nhỏ, hơi nước từ tô mì đã làm đêm ấy bớt lạnh đi rất nhiều.",
]


def mojibake_score(text: str) -> int:
    markers = ("�", "�", "�", "�", "�", "�", "�", "�", "﻿")
    return sum(text.count(marker) for marker in markers)


def _repair_fragment(text: str) -> str:
    best = text
    best_score = mojibake_score(text)

    for encoding in ("latin-1", "cp1252"):
        candidate = best
        for _ in range(2):
            try:
                candidate = candidate.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
            candidate_score = mojibake_score(candidate)
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score

    return best


def repair_text(text: Optional[str]) -> Optional[str]:
    if text is None or not isinstance(text, str):
        return text
    if mojibake_score(text) == 0:
        return text

    chunks = []
    current = []
    current_dirty = False

    def flush() -> None:
        nonlocal current, current_dirty
        if not current:
            return
        chunk = "".join(current)
        chunks.append(_repair_fragment(chunk) if current_dirty else chunk)
        current = []
        current_dirty = False

    for ch in text:
        ch_dirty = mojibake_score(ch) > 0 or ord(ch) < 128
        if current and ch.isspace():
            current.append(ch)
            flush()
            continue
        if current and current_dirty != ch_dirty and not (current_dirty and ord(ch) < 128):
            flush()
        current.append(ch)
        current_dirty = current_dirty or ch_dirty

    flush()
    repaired = "".join(chunks)
    return _repair_fragment(repaired) if mojibake_score(repaired) else repaired


def repair_embed(embed: discord.Embed) -> discord.Embed:
    embed.title = repair_text(embed.title)
    embed.description = repair_text(embed.description)

    for field in getattr(embed, "_fields", []):
        field["name"] = repair_text(field.get("name"))
        field["value"] = repair_text(field.get("value"))

    footer = getattr(embed, "_footer", None)
    if isinstance(footer, dict) and footer.get("text"):
        footer["text"] = repair_text(footer.get("text"))

    author = getattr(embed, "_author", None)
    if isinstance(author, dict) and author.get("name"):
        author["name"] = repair_text(author.get("name"))

    return embed


_ORIGINAL_MESSAGEABLE_SEND = discord.abc.Messageable.send


async def _patched_messageable_send(self, *args, **kwargs):
    patched_args = list(args)
    if patched_args and isinstance(patched_args[0], str):
        patched_args[0] = repair_text(patched_args[0])

    if isinstance(kwargs.get("content"), str):
        kwargs["content"] = repair_text(kwargs["content"])

    if isinstance(kwargs.get("embed"), discord.Embed):
        kwargs["embed"] = repair_embed(kwargs["embed"])

    embeds = kwargs.get("embeds")
    if embeds:
        kwargs["embeds"] = [repair_embed(embed) if isinstance(embed, discord.Embed) else embed for embed in embeds]

    return await _ORIGINAL_MESSAGEABLE_SEND(self, *patched_args, **kwargs)


discord.abc.Messageable.send = _patched_messageable_send
SYSTEM_PROMPT = repair_text(SYSTEM_PROMPT)


def make_embed(
    title: str,
    description: str = "",
    color: Optional[discord.Color] = None,
) -> discord.Embed:
    return discord.Embed(
        title=repair_text(title),
        description=repair_text(description),
        color=color or discord.Color.blurple(),
    )


def utc_today() -> str:
    return discord.utils.utcnow().date().isoformat()


def get_prefix() -> str:
    return os.getenv("BOT_PREFIX", "!")


def get_discord_token() -> str:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Thiếu `DISCORD_BOT_TOKEN` trong file `.env`.")
    return token


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu `OPENAI_API_KEY`.")
    return OpenAI(api_key=api_key)


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5.2")


async def notify_admin_dm(message: str) -> None:
    if not ADMIN_USER_ID or bot.user is None:
        return
    user = bot.get_user(ADMIN_USER_ID)
    if user is None:
        try:
            user = await bot.fetch_user(ADMIN_USER_ID)
        except discord.HTTPException:
            return
    try:
        await user.send(message)
    except discord.HTTPException:
        return


async def generate_story(user_name: str, topic: str) -> str:
    if client is None:
        base_story = random.choice(STORY_FALLBACKS)
        if topic.strip():
            return (
                f"Chủ đề bạn gọi là **{topic.strip()}** nè :vv\n\n"
                f"{base_story}\n\n"
                "Nếu muốn, bảo tôi kể tiếp phần 2 hoặc đổi sang kiểu kinh dị / buồn / hài nhé."
            )[:1900]
        return base_story[:1900]

    prompt = (
        f"Người dùng tên {user_name} muốn nghe kể chuyện.\n"
        f"Chủ đề: {topic.strip() or 'tự chọn một câu chuyện cuốn và dễ đọc'}\n\n"
        f"{STORY_PROMPT_STYLE}"
    )

    def _request() -> str:
        response = client.responses.create(
            model=get_model(),
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )
        return response.output_text

    text = await asyncio.to_thread(_request)
    return sanitize_reply(text)


def sanitize_reply(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "Tôi đang nghe đây, nói thêm chút được không :vv"
    return cleaned[:1800]


def load_economy_data() -> dict:
    if not DATA_FILE.exists():
        return {"users": {}, "debts": []}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {"users": {}, "debts": []}
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    if "debts" not in data or not isinstance(data["debts"], list):
        data["debts"] = []
    return data


def save_economy_data() -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(economy_data, file, ensure_ascii=False, indent=2)


def load_bot_route_data() -> dict[str, str]:
    if not BOT_ROUTE_FILE.exists():
        return {}
    try:
        with BOT_ROUTE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return {str(key): str(value) for key, value in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}
    return {}


def save_bot_route_data() -> None:
    with BOT_ROUTE_FILE.open("w", encoding="utf-8") as file:
        json.dump(bot_route_data, file, ensure_ascii=False, indent=2)


def get_user_economy(user_id: int) -> dict:
    users = economy_data.setdefault("users", {})
    user_key = str(user_id)
    if user_key not in users:
        users[user_key] = {
            "balance": 1000,
            "earned_total": 1000,
            "lost_total": 0,
            "daily_streak_claims": 0,
            "last_daily": None,
            "inventory": [],
            "challenge": None,
            "challenge_progress": {},
        }
    users[user_key].setdefault("inventory", [])
    users[user_key].setdefault("challenge", None)
    users[user_key].setdefault("challenge_progress", {})
    normalized_inventory = []
    for item in users[user_key]["inventory"]:
        if isinstance(item, str):
            if item in SHOP_ITEMS:
                normalized_inventory.append(
                    {
                        "key": item,
                        "durability": TOOL_DURABILITY_BY_POWER.get(SHOP_ITEMS[item]["power"], 20),
                    }
                )
        elif isinstance(item, dict) and item.get("key") in SHOP_ITEMS:
            item_key = item["key"]
            normalized_inventory.append(
                {
                    "key": item_key,
                    "durability": int(
                        item.get(
                            "durability",
                            TOOL_DURABILITY_BY_POWER.get(SHOP_ITEMS[item_key]["power"], 20),
                        )
                    ),
                }
            )
    users[user_key]["inventory"] = normalized_inventory
    return users[user_key]


def get_debts() -> list[dict]:
    return economy_data.setdefault("debts", [])


def has_item(user_id: int, item_key: str) -> bool:
    return any(item["key"] == item_key for item in get_user_economy(user_id)["inventory"])


def add_item(user_id: int, item_key: str) -> None:
    wallet = get_user_economy(user_id)
    if not has_item(user_id, item_key):
        wallet["inventory"].append(
            {
                "key": item_key,
                "durability": TOOL_DURABILITY_BY_POWER.get(SHOP_ITEMS[item_key]["power"], 20),
            }
        )


def get_inventory_entry(user_id: int, item_key: str) -> Optional[dict]:
    wallet = get_user_economy(user_id)
    for item in wallet["inventory"]:
        if item["key"] == item_key:
            return item
    return None


def remove_item(user_id: int, item_key: str) -> None:
    wallet = get_user_economy(user_id)
    wallet["inventory"] = [item for item in wallet["inventory"] if item["key"] != item_key]


def inventory_text(user_id: int) -> str:
    wallet = get_user_economy(user_id)
    items = []
    for entry in wallet["inventory"]:
        item_key = entry["key"]
        if item_key not in SHOP_ITEMS:
            continue
        max_durability = TOOL_DURABILITY_BY_POWER.get(SHOP_ITEMS[item_key]["power"], 20)
        items.append(f"{SHOP_ITEMS[item_key]['name']} ({entry['durability']}/{max_durability})")
    return ", ".join(items) if items else "Chưa có đồ"


def build_value_table_text() -> str:
    lines = []
    for key, item in SHOP_ITEMS.items():
        lines.append(
            f"{item['name']} - {item['price']} xu - độ bền {TOOL_DURABILITY_BY_POWER.get(item['power'], 20)}"
        )
    return "\n".join(lines)


def best_item_by_type(user_id: int, item_type: str) -> Optional[str]:
    wallet = get_user_economy(user_id)
    owned = [
        entry["key"]
        for entry in wallet["inventory"]
        if entry["key"] in SHOP_ITEMS and SHOP_ITEMS[entry["key"]]["type"] == item_type
    ]
    if not owned:
        return None
    return max(owned, key=lambda key: SHOP_ITEMS[key]["power"])


def best_support_item_for_activity(user_id: int, activity: str) -> Optional[str]:
    wallet = get_user_economy(user_id)
    owned = [
        entry["key"]
        for entry in wallet["inventory"]
        if entry["key"] in SHOP_ITEMS
        and SHOP_ITEMS[entry["key"]]["type"] == "support"
        and SHOP_ITEMS[entry["key"]].get("support_for") in {activity, "all"}
    ]
    if not owned:
        return None
    return max(
        owned,
        key=lambda key: (
            SHOP_ITEMS[key].get("bonus_percent", 0.0),
            SHOP_ITEMS[key]["price"],
        ),
    )


def consume_tool_durability(user_id: int, item_key: str) -> tuple[int, int, bool]:
    entry = get_inventory_entry(user_id, item_key)
    if entry is None:
        return 0, 0, True
    entry["durability"] = max(0, int(entry.get("durability", 0)) - 1)
    max_durability = TOOL_DURABILITY_BY_POWER.get(SHOP_ITEMS[item_key]["power"], 20)
    broken = entry["durability"] <= 0
    remaining = entry["durability"]
    if broken:
        remove_item(user_id, item_key)
    return remaining, max_durability, broken


def get_daily_reminder(user_id: int) -> Optional[str]:
    wallet = get_user_economy(user_id)
    if wallet.get("last_daily") == utc_today():
        return None
    return f"Bạn chưa nhận daily hôm nay. Dùng `{get_prefix()}daily` để lấy {DAILY_REWARD} xu :vv"


WEREWOLF_WOLF_ROLES = {
    "Ma Sói",
    "Sói Con",
    "Sói Trắng",
    "Sói Phù Thủy",
    "Sói Đầu Đàn",
    "Sói Mù",
    "Sói Giả",
}
WEREWOLF_SEER_ROLES = {"Tiên Tri", "Thầy Bói", "Aura Seer", "Apprentice Seer"}
WEREWOLF_GUARD_ROLES = {"Bảo Vệ"}
WEREWOLF_WITCH_ROLES = {"Phù Thủy"}
WEREWOLF_MUTE_WITCH_ROLES = {"Phù Thủy Câm"}
WEREWOLF_CUPID_ROLES = {"Cupid"}
WEREWOLF_BLACKSMITH_ROLES = {"Thợ Rèn"}
WEREWOLF_WATCHMAN_ROLES = {"Người Gác Đêm"}
WEREWOLF_PIPER_ROLES = {"Người Thổi Sáo"}
WEREWOLF_ACTIVE_NIGHT_ROLES = (
    WEREWOLF_WOLF_ROLES
    | WEREWOLF_SEER_ROLES
    | WEREWOLF_GUARD_ROLES
    | WEREWOLF_WITCH_ROLES
    | WEREWOLF_MUTE_WITCH_ROLES
    | WEREWOLF_CUPID_ROLES
    | WEREWOLF_BLACKSMITH_ROLES
    | WEREWOLF_WATCHMAN_ROLES
    | WEREWOLF_PIPER_ROLES
)
WEREWOLF_NEUTRAL_WIN_ROLES = {"Tanner", "Người Thổi Sáo"}


def get_session_by_player(user_id: int) -> Optional[dict]:
    for session in werewolf_sessions.values():
        if session.get("started") and user_id in session.get("players", set()):
            return session
    return None


def is_alive_in_session(session: dict, user_id: int) -> bool:
    return user_id in session.get("alive_players", set())


def alive_players(session: dict) -> list[int]:
    return list(session.get("alive_players", set()))


def player_role(session: dict, user_id: int) -> str:
    return session.get("roles", {}).get(user_id, "")


def is_werewolf_bot_player(session: dict, user_id: int) -> bool:
    return user_id in session.get("bot_players", set())


def werewolf_player_label(session: dict, user_id: int) -> str:
    if is_werewolf_bot_player(session, user_id):
        return session.get("bot_names", {}).get(user_id, f"Bot {abs(user_id)}")
    member = session["channel"].guild.get_member(user_id)
    return member.mention if member else f"<@{user_id}>"


def build_werewolf_player_list(session: dict, player_ids: list[int] | set[int]) -> str:
    return " ".join(werewolf_player_label(session, user_id) for user_id in player_ids)


def player_is_wolf(session: dict, user_id: int) -> bool:
    return player_role(session, user_id) in WEREWOLF_WOLF_ROLES or user_id in session.get("converted_wolves", set())


def player_team(session: dict, user_id: int) -> str:
    role_name = player_role(session, user_id)
    if player_is_wolf(session, user_id):
        return "wolf"
    if role_name == "Người Thổi Sáo":
        return "piper"
    if role_name == "Tanner":
        return "tanner"
    return "village"


def role_team(role_name: str) -> str:
    if role_name in WEREWOLF_WOLF_ROLES:
        return "wolf"
    if role_name == "Người Thổi Sáo":
        return "piper"
    if role_name == "Tanner":
        return "tanner"
    return "village"


def parse_target_id_from_text(raw_text: str) -> Optional[int]:
    digits = "".join(ch for ch in raw_text if ch.isdigit())
    return int(digits) if digits else None


def normalize_lookup_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "".join(ch for ch in normalized if ch.isalnum() or ch.isspace()).strip()


def normalize_channel_style(raw_style: Optional[str]) -> Optional[str]:
    if raw_style is None:
        return None
    key = normalize_lookup_text(raw_style).replace(" ", "")
    return CHANNEL_STYLE_ALIASES.get(key)


def strip_channel_decoration(raw_name: str) -> str:
    text = raw_name.strip()
    for separator in ("︰", ":", "・", "•", "|"):
        if separator in text:
            parts = [part.strip() for part in text.split(separator) if part.strip()]
            if parts:
                text = max(parts, key=lambda part: len(normalize_lookup_text(part)))
    return text


def clean_channel_label(raw_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", strip_channel_decoration(raw_name).casefold())
    cleaned: list[str] = []
    previous_dash = False
    for char in normalized:
        if unicodedata.combining(char):
            continue
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            cleaned.append(char)
            previous_dash = False
        elif char in {" ", "-", "_", ".", "/", ":"} and not previous_dash:
            cleaned.append("-")
            previous_dash = True

    label = "".join(cleaned).strip("-")
    return label or "channel"


def detect_channel_icon(label: str) -> str:
    haystack = label.replace("-", " ")
    words = set(haystack.split())
    for keywords, icon in CHANNEL_ICON_RULES:
        if any(keyword in words or keyword in haystack for keyword in keywords):
            return icon
    return "✨"


def split_channel_icon(raw_name: str) -> tuple[Optional[str], str]:
    parts = raw_name.strip().split(maxsplit=1)
    if parts and len(parts[0]) <= 4 and any(not char.isalnum() for char in parts[0]):
        return parts[0], parts[1] if len(parts) > 1 else "channel"
    return None, raw_name


def decorate_channel_name(style: str, raw_name: str) -> str:
    explicit_icon, label_text = split_channel_icon(raw_name)
    label = clean_channel_label(label_text)
    icon = explicit_icon or detect_channel_icon(label)
    decorated = CHANNEL_STYLE_TEMPLATES[style].format(icon=icon, name=label)
    return decorated[:MAX_DISCORD_CHANNEL_NAME_LENGTH].rstrip("-・:︰ ")


def message_contains_werewolf_dm_leak(text: str) -> bool:
    normalized = normalize_lookup_text(text)
    return any(marker in normalized for marker in WEREWOLF_DM_LEAK_MARKERS)


def sanitize_dm_target_text(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("<") and cleaned.endswith(">") and len(cleaned) >= 3:
        cleaned = cleaned[1:-1].strip()
    cleaned = cleaned.lstrip("@!#&")
    return cleaned.strip()


def resolve_dm_target(session: dict, raw_text: str) -> Optional[int]:
    target_id = parse_target_id_from_text(raw_text)
    if target_id and target_id in session.get("players", set()):
        return target_id
    lowered = sanitize_dm_target_text(raw_text)
    normalized_query = normalize_lookup_text(lowered)
    for user_id in session.get("players", set()):
        if is_werewolf_bot_player(session, user_id):
            bot_name = session.get("bot_names", {}).get(user_id, "")
            bot_candidates = {
                bot_name,
                bot_name.replace(" ", ""),
                f"bot{abs(user_id)}",
            }
            lowered_candidates = {candidate.casefold() for candidate in bot_candidates if candidate}
            normalized_candidates = {normalize_lookup_text(candidate) for candidate in bot_candidates if candidate}
            if lowered and lowered.casefold() in lowered_candidates:
                return user_id
            if normalized_query and normalized_query in normalized_candidates:
                return user_id
            continue
        member = session["channel"].guild.get_member(user_id)
        if not member:
            continue
        raw_candidates = {
            member.display_name,
            member.name,
            getattr(member, "global_name", None) or "",
            str(member),
        }
        lowered_candidates = {candidate.casefold() for candidate in raw_candidates if candidate}
        normalized_candidates = {normalize_lookup_text(candidate) for candidate in raw_candidates if candidate}
        if lowered and lowered.casefold() in lowered_candidates:
            return user_id
        if normalized_query and normalized_query in normalized_candidates:
            return user_id
        if normalized_query and any(
            normalized_query in candidate or candidate in normalized_query
            for candidate in normalized_candidates
            if candidate
        ):
            return user_id
    return None


def parse_two_dm_targets(session: dict, raw_text: str) -> list[int]:
    tokens = [token for token in raw_text.replace("|", " ").replace(",", " ").split() if token]
    resolved: list[int] = []
    for token in tokens:
        target_id = resolve_dm_target(session, token)
        if target_id is not None and target_id not in resolved:
            resolved.append(target_id)
        if len(resolved) >= 2:
            break
    return resolved


async def send_private_message(user_id: int, content: str) -> None:
    user = bot.get_user(user_id) or await bot.fetch_user(user_id)
    await user.send(content)


def allocate_werewolf_roles(players: list[int], bot_players: set[int]) -> dict[int, str]:
    total_players = len(players)
    role_pool_key = min(total_players, max(WEREWOLF_ROLE_SETS))
    role_pool = WEREWOLF_ROLE_SETS[role_pool_key][:total_players]
    wolf_roles = [role for role in role_pool if role in WEREWOLF_WOLF_ROLES]
    special_roles = [role for role in role_pool if role not in WEREWOLF_WOLF_ROLES and role != "Dân Làng"]
    villager_count = sum(1 for role in role_pool if role == "Dân Làng")
    human_players = [user_id for user_id in players if user_id not in bot_players]
    npc_players = [user_id for user_id in players if user_id in bot_players]
    random.shuffle(human_players)
    random.shuffle(npc_players)
    random.shuffle(wolf_roles)
    random.shuffle(special_roles)

    assigned_roles: dict[int, str] = {}
    remaining_humans = human_players[:]
    remaining_wolves = wolf_roles[:]

    for role_name in special_roles:
        if not remaining_humans:
            break
        assigned_roles[remaining_humans.pop()] = role_name

    if remaining_wolves and remaining_humans:
        assigned_roles[remaining_humans.pop()] = remaining_wolves.pop()

    leftovers = remaining_wolves + ["Dân Làng"] * villager_count
    random.shuffle(leftovers)
    for user_id in remaining_humans:
        assigned_roles[user_id] = leftovers.pop() if leftovers else "Dân Làng"

    npc_roles = leftovers[:]
    while len(npc_roles) < len(npc_players):
        npc_roles.append("Dân Làng")
    random.shuffle(npc_roles)
    for user_id, role_name in zip(npc_players, npc_roles):
        assigned_roles[user_id] = role_name

    return assigned_roles


async def run_werewolf_bot_night_actions(session: dict) -> None:
    if session.get("phase") != "night":
        return
    alive = alive_players(session)
    bot_players = [user_id for user_id in alive if is_werewolf_bot_player(session, user_id)]
    non_wolf_targets = [user_id for user_id in alive if not player_is_wolf(session, user_id)]
    for user_id in bot_players:
        role_name = player_role(session, user_id)
        if role_name in WEREWOLF_WOLF_ROLES:
            if session.get("wolf_kill_blocked_tonight"):
                session.setdefault("night_ready", set()).add(user_id)
                continue
            targets = [target_id for target_id in non_wolf_targets if target_id != user_id]
            if targets:
                target_id = random.choice(targets)
                session["wolf_votes"][user_id] = target_id
                session["wolf_target_preview"] = target_id
            session.setdefault("night_ready", set()).add(user_id)


async def run_werewolf_bot_day_votes(session: dict) -> None:
    if session.get("phase") != "day":
        return
    alive = alive_players(session)
    bot_players = [user_id for user_id in alive if is_werewolf_bot_player(session, user_id)]
    for user_id in bot_players:
        if session.get("mute_target") == user_id:
            continue
        if user_id in session.get("day_votes", {}):
            continue
        role_name = player_role(session, user_id)
        if role_name in WEREWOLF_WOLF_ROLES:
            targets = [target_id for target_id in alive if target_id != user_id and not player_is_wolf(session, target_id)]
        else:
            targets = [target_id for target_id in alive if target_id != user_id]
        if not targets:
            continue
        session["day_votes"][user_id] = random.choice(targets)


WEREWOLF_ROLE_SKILLS = {
    "Ma Sói": "Mỗi đêm chọn 1 người để cắn cùng phe Sói bằng `!wwkill @tên` trong DM.",
    "Sói Con": "Thuộc phe Sói và cùng cắn người vào ban đêm bằng `!wwkill @tên` trong DM.",
    "Sói Trắng": "Vẫn là phe Sói trong bản hiện tại, có thể tham gia cắn bằng `!wwkill @tên` trong DM.",
    "Sói Phù Thủy": "Thuộc phe Sói, ban đêm tham gia chọn người bị cắn bằng `!wwkill @tên` trong DM.",
    "Sói Đầu Đàn": "Thuộc phe Sói, hiện tại dùng chung cơ chế cắn đêm với `!wwkill @tên` trong DM.",
    "Sói Mù": "Thuộc phe Sói nhưng khi nhận role sẽ không được bot cho biết đồng đội.",
    "Sói Giả": "Khi bị soi sẽ hiện như Dân Làng, nhưng vẫn thuộc phe Sói và cắn bằng `!wwkill @tên` trong DM.",
    "Tiên Tri": "Mỗi đêm soi 1 người bằng `!wwsee @tên` trong DM để biết role của họ.",
    "Thầy Bói": "Hoạt động như Tiên Tri, dùng `!wwsee @tên` trong DM để soi 1 người mỗi đêm.",
    "Aura Seer": "Hiện đang được bot xử lý như role soi đêm, dùng `!wwsee @tên` trong DM.",
    "Apprentice Seer": "Hiện đang được bot xử lý như role soi đêm, dùng `!wwsee @tên` trong DM.",
    "Bảo Vệ": "Mỗi đêm bảo vệ 1 người bằng `!wwguard @tên` trong DM.",
    "Thợ Săn": "Khi chết có thể kéo theo 1 mạng bằng `!wwrevenge @tên` trong DM, hoặc `!wwpass` để bỏ qua.",
    "Phù Thủy": "Mỗi ván có 1 lần cứu bằng `!wwsave` và 1 lần giết bằng `!wwpoison @tên` trong DM.",
    "Phù Thủy Câm": "Mỗi đêm có thể khóa chat/vote 1 người bằng `!wwmute @tên` trong DM.",
    "Cupid": "Đêm 1 ghép đôi 2 người bằng `!wwlove @người1 @người2` trong DM.",
    "Cô Bé": "Có thể lén quan sát ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Trưởng Làng": "Phiếu bầu mạnh hơn ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Già Làng": "Khá trâu ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Thợ Rèn": "Mỗi ván có thể chặn toàn bộ đòn cắn của Sói trong 1 đêm bằng `!wwshield` trong DM.",
    "Người Gác Đêm": "Mỗi đêm theo dõi 1 người bằng `!wwwatch @tên` để biết đêm đó có bị tấn công hay không.",
    "Người Thổi Sáo": "Mỗi đêm thôi miên tối đa 2 người bằng `!wwcharm @a @b`; thôi miên hết người sống khác mình là thắng riêng.",
    "Kẻ Say Rượu": "Có thể đổi role loạn ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Kẻ Phản Bội": "Có thể đổi phe ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Tanner": "Bị treo là thắng riêng ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Serial Killer": "Có hướng chơi riêng ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Arsonist": "Có hướng chơi riêng ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Doppelganger": "Đêm 1 có thể sao chép role bằng `!wwcopy @tên` trong DM.",
    "Village Idiot": "Có trạng thái miễn treo ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Diseased": "Có hiệu ứng làm Sói yếu đi ở bản nâng cao; hiện bot mới gửi role và mô tả kỹ năng.",
    "Prince": "Lần đầu bị treo sẽ không chết và lộ thân phận.",
    "Dân Làng": "Không có kỹ năng chủ động. Ban ngày hãy phân tích và dùng `!vote @tên` để treo người đáng nghi.",
}


def build_role_dm_text(role_name: str) -> str:
    team_text = "Phe Sói" if role_team(role_name) == "wolf" else "Phe Dân / trung lập"
    skill_text = WEREWOLF_ROLE_SKILLS.get(role_name, "Hiện chưa có mô tả kỹ năng riêng cho role này.")
    return (
        "Bot là **Quản Trò** của ván này.\n"
        f"Vai trò Ma Sói của bạn là: **{role_name}**\n"
        f"Phe của bạn: **{team_text}**\n"
        f"Kỹ năng: {skill_text}\n"
        "Giữ bí mật role của mình nhé =)))"
    )


def get_lover(session: dict, user_id: int) -> Optional[int]:
    lovers = session.get("lovers", {})
    return lovers.get(user_id)


async def kill_player(session: dict, user_id: int, reason: str, announce_to_channel: bool = False) -> bool:
    if not is_alive_in_session(session, user_id):
        return False
    session["alive_players"].discard(user_id)
    session.setdefault("dead_players", set()).add(user_id)
    session.setdefault("death_log", []).append((user_id, reason))
    if announce_to_channel:
        await session["channel"].send(f"<@{user_id}> đã chết vì {reason}.")

    lover_id = get_lover(session, user_id)
    if lover_id and is_alive_in_session(session, lover_id):
        await kill_player(session, lover_id, "người yêu chết nên chết theo", announce_to_channel)

    if player_role(session, user_id) == "Thợ Săn":
        session["pending_hunter_shots"].add(user_id)
        try:
            await send_private_message(
                user_id,
                "Bạn là **Thợ Săn** và vừa chết. Dùng `!wwrevenge @người_chơi` trong DM để kéo theo 1 mạng, hoặc `!wwpass` để bỏ qua.",
            )
        except discord.HTTPException:
            pass
    return True


def active_night_players(session: dict) -> set[int]:
    players = set()
    for user_id in alive_players(session):
        role_name = player_role(session, user_id)
        if role_name in WEREWOLF_WOLF_ROLES:
            if session.get("wolf_kill_blocked_tonight"):
                continue
            players.add(user_id)
        elif role_name in WEREWOLF_SEER_ROLES | WEREWOLF_GUARD_ROLES | WEREWOLF_MUTE_WITCH_ROLES | WEREWOLF_WATCHMAN_ROLES:
            players.add(user_id)
        elif role_name in WEREWOLF_WITCH_ROLES:
            players.add(user_id)
        elif role_name in WEREWOLF_BLACKSMITH_ROLES and not session.get("blacksmith_used"):
            players.add(user_id)
        elif role_name in WEREWOLF_CUPID_ROLES and session.get("night_number", 0) == 1 and not session.get("cupid_used"):
            players.add(user_id)
        elif role_name in WEREWOLF_PIPER_ROLES:
            players.add(user_id)
        elif role_name == "Doppelganger" and session.get("night_number", 0) == 1 and not session.get("doppel_used"):
            players.add(user_id)
    return players


async def check_werewolf_victory(session: dict) -> bool:
    channel = session["channel"]
    alive = alive_players(session)
    piper_players = [uid for uid in alive if player_role(session, uid) == "Người Thổi Sáo"]
    if piper_players:
        charmed = session.get("charmed_players", set())
        others = {uid for uid in alive if player_role(session, uid) != "Người Thổi Sáo"}
        if others and others.issubset(charmed):
            await channel.send(embed=make_embed("Ma Sói kết thúc", "Người Thổi Sáo đã thôi miên toàn bộ người còn sống và thắng riêng =)))", discord.Color.magenta()))
            werewolf_sessions.pop(channel.id, None)
            return True

    wolves = [uid for uid in alive if player_is_wolf(session, uid)]
    villagers = [uid for uid in alive if player_team(session, uid) == "village"]
    channel = session["channel"]

    if not wolves:
        traitors = [uid for uid in alive if player_role(session, uid) == "Kẻ Phản Bội"]
        if traitors:
            traitor_id = traitors[0]
            session["roles"][traitor_id] = "Ma Sói"
            await channel.send(embed=make_embed("Phản bội lộ diện", f"{werewolf_player_label(session, traitor_id)} đã hóa thành **Ma Sói** khi bầy sói cũ chết hết.", discord.Color.red()))
            return False

    if not wolves:
        await channel.send(embed=make_embed("Ma Sói kết thúc", "Phe Dân đã thắng vì toàn bộ Sói đã bị loại :vv", discord.Color.green()))
        werewolf_sessions.pop(channel.id, None)
        return True
    if len(wolves) >= len(villagers):
        await channel.send(embed=make_embed("Ma Sói kết thúc", "Phe Sói đã thắng vì đã áp đảo dân làng =)))", discord.Color.red()))
        werewolf_sessions.pop(channel.id, None)
        return True
    return False


async def start_werewolf_night(session: dict) -> None:
    session["phase"] = "night"
    session["night_number"] = session.get("night_number", 0) + 1
    session["wolf_votes"] = {}
    session["seer_target"] = None
    session["guard_target"] = None
    session["witch_saved"] = False
    session["witch_poison_target"] = None
    session["mute_target"] = None
    session["watch_target"] = None
    session["watched_result"] = None
    session["blacksmith_active"] = False
    session["night_ready"] = set()
    session["day_votes"] = {}
    alive_mentions = build_werewolf_player_list(session, alive_players(session))
    session["wolf_kill_blocked_tonight"] = session.pop("wolf_cannot_kill_night", False)
    extra_line = "\nĐêm này bầy sói bị suy yếu nên không thể cắn ai." if session.get("wolf_kill_blocked_tonight") else ""
    await session["channel"].send(
        embed=make_embed(
            f"Đêm {session['night_number']}",
            f"Mọi người đi ngủ. Người còn sống: {alive_mentions}\nCác role có kỹ năng hãy kiểm tra DM với bot.{extra_line}",
            discord.Color.dark_blue(),
        )
    )
    wolves_alive = [uid for uid in alive_players(session) if player_is_wolf(session, uid)]
    for user_id in wolves_alive:
        if is_werewolf_bot_player(session, user_id):
            continue
        role_name = player_role(session, user_id)
        teammates = [werewolf_player_label(session, uid) for uid in wolves_alive if uid != user_id]
        teammate_text = "Bạn không nhìn thấy đồng đội đâu ;-;" if role_name == "Sói Mù" else (", ".join(teammates) if teammates else "Không có đồng đội")
        await send_private_message(
            user_id,
            f"Đêm {session['night_number']}.\nBạn là **{role_name}**.\nĐồng đội còn sống: {teammate_text}\nDùng `!wwkill @người_chơi` trong DM này để chọn mục tiêu, hoặc `!wwpass` nếu muốn bỏ qua.",
        )
    for user_id in alive_players(session):
        if is_werewolf_bot_player(session, user_id):
            continue
        role_name = player_role(session, user_id)
        if role_name in WEREWOLF_SEER_ROLES:
            await send_private_message(user_id, "Bạn có thể soi 1 người bằng `!wwsee @người_chơi` trong DM này, hoặc `!wwpass` để bỏ qua.")
        if role_name in WEREWOLF_GUARD_ROLES:
            await send_private_message(user_id, "Bạn có thể bảo vệ 1 người bằng `!wwguard @người_chơi` trong DM này, hoặc `!wwpass` để bỏ qua.")
        if role_name in WEREWOLF_WITCH_ROLES:
            target_text = werewolf_player_label(session, session.get("wolf_target_preview")) if session.get("wolf_target_preview") else "chưa có ai"
            await send_private_message(user_id, f"Phù Thủy: người bị Sói nhắm hiện tại là {target_text}. Dùng `!wwsave` để cứu, `!wwpoison @người_chơi` để giết, hoặc `!wwpass`.")
        if role_name in WEREWOLF_MUTE_WITCH_ROLES:
            await send_private_message(user_id, "Phù Thủy Câm: dùng `!wwmute @người_chơi` để khóa chat/vote của 1 người vào ngày mai, hoặc `!wwpass`.")
        if role_name in WEREWOLF_CUPID_ROLES and session["night_number"] == 1 and not session.get("cupid_used"):
            await send_private_message(user_id, "Cupid: dùng `!wwlove @người1 @người2` để ghép đôi, hoặc `!wwpass`.")
        if role_name in WEREWOLF_BLACKSMITH_ROLES and not session.get("blacksmith_used"):
            await send_private_message(user_id, "Thợ Rèn: dùng `!wwshield` để chặn toàn bộ đòn cắn của Sói trong đêm này, hoặc `!wwpass`.")
        if role_name in WEREWOLF_WATCHMAN_ROLES:
            await send_private_message(user_id, "Người Gác Đêm: dùng `!wwwatch @người_chơi` để theo dõi xem người đó có bị tấn công không, hoặc `!wwpass`.")
        if role_name in WEREWOLF_PIPER_ROLES:
            await send_private_message(user_id, "Người Thổi Sáo: dùng `!wwcharm @người1 @người2` để thôi miên tối đa 2 người trong đêm, hoặc `!wwpass`.")
        if role_name == "Doppelganger" and session["night_number"] == 1 and not session.get("doppel_used"):
            await send_private_message(user_id, "Doppelganger: dùng `!wwcopy @người_chơi` để sao chép role, hoặc `!wwpass`.")
    await run_werewolf_bot_night_actions(session)
    await try_resolve_werewolf_night(session)


async def start_werewolf_day(session: dict, summary: str, night_report: Optional[dict] = None) -> None:
    session["phase"] = "day"
    session["day_votes"] = {}
    alive_mentions = build_werewolf_player_list(session, alive_players(session))
    embed = make_embed(
        "Trời sáng",
        f"{summary}\n\nNgười còn sống: {alive_mentions}\nDùng `!vote @người_chơi` để treo cổ.",
        discord.Color.gold(),
    )
    if night_report:
        dead_lines = night_report.get("dead_lines", [])
        saved_lines = night_report.get("saved_lines", [])
        muted_lines = night_report.get("muted_lines", [])
        charmed_lines = night_report.get("charmed_lines", [])
        special_lines = night_report.get("special_lines", [])
        if dead_lines:
            embed.add_field(name="Người chết", value="\n".join(dead_lines)[:1024], inline=False)
        if saved_lines:
            embed.add_field(name="Được cứu / thoát chết", value="\n".join(saved_lines)[:1024], inline=False)
        if muted_lines:
            embed.add_field(name="Bị câm hôm nay", value="\n".join(muted_lines)[:1024], inline=False)
        if charmed_lines:
            embed.add_field(name="Bị thôi miên", value="\n".join(charmed_lines)[:1024], inline=False)
        if special_lines:
            embed.add_field(name="Hiệu ứng đặc biệt", value="\n".join(special_lines)[:1024], inline=False)
    await session["channel"].send(embed=embed)

    async def _auto_vote_later() -> None:
        await asyncio.sleep(8)
        if session.get("phase") != "day":
            return
        await run_werewolf_bot_day_votes(session)
        await try_resolve_werewolf_day(session)

    asyncio.create_task(_auto_vote_later())


async def try_resolve_werewolf_night(session: dict) -> None:
    if session.get("phase") != "night":
        return
    required_players = active_night_players(session)
    if not required_players.issubset(session.get("night_ready", set())):
        return
    summary_lines: list[str] = []
    night_report = {
        "dead_lines": [],
        "saved_lines": [],
        "muted_lines": [],
        "charmed_lines": [],
        "special_lines": [],
    }

    seers_alive = [uid for uid in alive_players(session) if player_role(session, uid) in WEREWOLF_SEER_ROLES]
    if session.get("seer_target") is not None:
        seer_target = session["seer_target"]
        seen_role = player_role(session, seer_target)
        shown_role = "Dân Làng" if seen_role == "Sói Giả" else seen_role
        shown_team = "Phe Sói" if player_is_wolf(session, seer_target) and seen_role != "Sói Giả" else "Phe Dân / trung lập"
        for seer_id in seers_alive:
            target_user = session["channel"].guild.get_member(seer_target)
            target_name = target_user.display_name if target_user else str(seer_target)
            if player_role(session, seer_id) == "Aura Seer":
                await send_private_message(seer_id, f"Kết quả soi: **{target_name}** thuộc **{shown_team}**.")
            else:
                await send_private_message(seer_id, f"Kết quả soi: **{target_name}** có role **{shown_role}**.")

    if session.get("watch_target") is not None:
        watch_target = session["watch_target"]
        watch_name = werewolf_player_label(session, watch_target)
        watch_result = session.get("watched_result") or "không thấy gì bất thường"
        for user_id in alive_players(session):
            if player_role(session, user_id) in WEREWOLF_WATCHMAN_ROLES:
                await send_private_message(user_id, f"Kết quả canh gác đêm nay với {watch_name}: **{watch_result}**.")

    vote_counts: dict[int, int] = defaultdict(int)
    for target_id in session["wolf_votes"].values():
        vote_counts[target_id] += 1
    wolf_target = max(vote_counts, key=vote_counts.get) if vote_counts else None
    if wolf_target is not None:
        session["wolf_target_preview"] = wolf_target

    if session.get("blacksmith_active"):
        session["blacksmith_used"] = True
        if wolf_target is not None:
            summary_lines.append("Đêm qua Thợ Rèn đã che chắn cả làng nên Sói không cắn được ai.")
            night_report["saved_lines"].append("Cả làng được **Thợ Rèn** che chắn khỏi đòn cắn của Sói.")
            session["watched_result"] = "có biến động lớn nhưng đã bị chặn"
            wolf_target = None

    if wolf_target is not None and session.get("guard_target") == wolf_target:
        session["watched_result"] = "có kẻ tấn công nhưng mục tiêu được bảo vệ"
        summary_lines.append(f"Đêm qua Sói đã cắn {werewolf_player_label(session, wolf_target)} nhưng người đó được bảo vệ cứu sống.")
        night_report["saved_lines"].append(f"{werewolf_player_label(session, wolf_target)} được **Bảo Vệ** cứu sống.")
        wolf_target = None

    if wolf_target is not None and session.get("witch_saved"):
        session["witch_heal_used"] = True
        session["watched_result"] = "có kẻ tấn công nhưng mục tiêu được cứu"
        summary_lines.append(f"Đêm qua Phù Thủy đã cứu {werewolf_player_label(session, wolf_target)} khỏi đòn cắn của Sói.")
        night_report["saved_lines"].append(f"{werewolf_player_label(session, wolf_target)} được **Phù Thủy** cứu sống.")
        wolf_target = None

    deaths: list[tuple[int, str]] = []
    if wolf_target is not None:
        target_role = player_role(session, wolf_target)
        if target_role == "Già Làng" and not session.get("elder_used"):
            session["elder_used"] = True
            summary_lines.append(f"Đêm qua Sói cắn {werewolf_player_label(session, wolf_target)} nhưng **Già Làng** quá trâu nên vẫn sống.")
            night_report["saved_lines"].append(f"{werewolf_player_label(session, wolf_target)} sống sót nhờ role **Già Làng**.")
        elif target_role == "Prince":
            summary_lines.append(f"Đêm qua {werewolf_player_label(session, wolf_target)} thoát chết nhờ thân phận **Prince**.")
            night_report["saved_lines"].append(f"{werewolf_player_label(session, wolf_target)} thoát chết nhờ role **Prince**.")
        else:
            await kill_player(session, wolf_target, "bị Sói cắn")
            deaths.append((wolf_target, "bị Sói cắn"))
            if target_role == "Diseased":
                session["wolf_cannot_kill_night"] = True
                summary_lines.append("Sói đã cắn trúng **Diseased**, nên đêm sau bầy Sói sẽ bị suy yếu.")
                night_report["special_lines"].append("Sói cắn trúng **Diseased** nên đêm sau không thể cắn.")

    poison_target = session.get("witch_poison_target")
    if poison_target is not None and is_alive_in_session(session, poison_target):
        session["witch_poison_used"] = True
        await kill_player(session, poison_target, "bị Phù Thủy đầu độc")
        deaths.append((poison_target, "bị Phù Thủy đầu độc"))

    if session.get("mute_target") is not None and is_alive_in_session(session, session["mute_target"]):
        summary_lines.append(f"{werewolf_player_label(session, session['mute_target'])} sẽ bị câm trong ban ngày hôm nay.")
        night_report["muted_lines"].append(werewolf_player_label(session, session["mute_target"]))

    newly_charmed = [uid for uid in sorted(session.get("charmed_players", set())) if is_alive_in_session(session, uid)]
    if newly_charmed:
        night_report["charmed_lines"] = [werewolf_player_label(session, uid) for uid in newly_charmed]

    if deaths:
        for dead_id, reason in deaths:
            summary_lines.append(f"{werewolf_player_label(session, dead_id)} đã chết vì {reason}.")
            night_report["dead_lines"].append(f"{werewolf_player_label(session, dead_id)} - {reason}")
    elif not summary_lines:
        summary_lines.append("Đêm qua không ai chết.")
        night_report["special_lines"].append("Đêm qua không ai chết.")

    if await check_werewolf_victory(session):
        return
    await start_werewolf_day(session, "\n".join(summary_lines), night_report)


async def try_resolve_werewolf_day(session: dict) -> None:
    if session.get("phase") != "day":
        return
    alive = alive_players(session)
    votes = session.get("day_votes", {})
    if not alive or not votes:
        return
    eligible_voters = [user_id for user_id in alive if session.get("mute_target") != user_id]
    vote_counts: dict[int, int] = defaultdict(int)
    for voter_id, target_id in votes.items():
        weight = 2 if player_role(session, voter_id) == "Trưởng Làng" else 1
        vote_counts[target_id] += weight
    top_votes = max(vote_counts.values())
    if top_votes <= len(eligible_voters) // 2 and len(votes) < len(eligible_voters):
        return
    top_targets = [uid for uid, count in vote_counts.items() if count == top_votes]
    if len(top_targets) != 1:
        await session["channel"].send(embed=make_embed("Bỏ phiếu hòa", "Phiếu đang hòa nên hôm nay chưa ai bị treo.", discord.Color.light_grey()))
        await start_werewolf_night(session)
        return
    target_id = top_targets[0]
    target_name = werewolf_player_label(session, target_id)
    target_role = player_role(session, target_id)

    if target_role == "Prince" and not session.get("prince_revealed"):
        session["prince_revealed"] = True
        await session["channel"].send(embed=make_embed("Hoàng tử lộ diện", f"{target_name} là **Prince** nên thoát treo ở lần đầu tiên.", discord.Color.blue()))
        await start_werewolf_night(session)
        return

    if target_role == "Village Idiot" and not session.get("idiot_revealed"):
        session["idiot_revealed"] = True
        await session["channel"].send(embed=make_embed("Kẻ ngốc làng", f"{target_name} quá ngáo nên dân làng không treo chết được ở lần đầu =)))", discord.Color.light_grey()))
        await start_werewolf_night(session)
        return

    if target_role == "Già Làng" and not session.get("elder_used"):
        session["elder_used"] = True
        await session["channel"].send(embed=make_embed("Già Làng quá trâu", f"{target_name} bị treo nhưng vẫn sống nhờ sức bền của **Già Làng**.", discord.Color.orange()))
        await start_werewolf_night(session)
        return

    if target_role == "Tanner":
        await kill_player(session, target_id, "bị treo cổ")
        await session["channel"].send(embed=make_embed("Tanner thắng riêng", f"{target_name} đã bị treo và **Tanner** đạt điều kiện thắng riêng 🤡", discord.Color.dark_orange()))
        werewolf_sessions.pop(session["channel"].id, None)
        return

    await kill_player(session, target_id, "bị treo cổ")
    await session["channel"].send(embed=make_embed("Kết quả treo cổ", f"{target_name} đã bị treo với **{top_votes}** phiếu.", discord.Color.red()))
    if await check_werewolf_victory(session):
        return

    hunter_queue = [uid for uid in session.get("pending_hunter_shots", set()) if uid in session.get("dead_players", set())]
    if hunter_queue:
        await session["channel"].send(embed=make_embed("Thợ Săn đã chết", "Nếu có Thợ Săn vừa chết thì hãy kiểm tra DM của bot để kéo theo 1 mạng hoặc `!wwpass`.", discord.Color.orange()))
        session["phase"] = "hunter_revenge"
        return
    await start_werewolf_night(session)


def get_user_debt_summary(user_id: int) -> tuple[int, int]:
    owes = 0
    owed = 0
    for debt in get_debts():
        if debt["borrower_id"] == user_id:
            owes += debt["amount"]
        if debt["lender_id"] == user_id:
            owed += debt["amount"]
    return owes, owed


def roll_lucky_loot(item_type: str, power: int) -> Optional[tuple[str, int]]:
    entries = LUCKY_LOOT_TABLE.get(item_type, {}).get(power, [])
    for name, min_reward, max_reward, chance in entries:
        if random.random() < chance:
            return name, random.randint(min_reward, max_reward)
    return None


async def close_werewolf_signup(channel_id: int) -> None:
    session = werewolf_sessions.get(channel_id)
    if not session or session.get("closed"):
        return

    session["closed"] = True
    channel = session["channel"]
    players: list[int] = list(session["players"])
    bot_players: set[int] = set(session.get("bot_players", set()))
    target_players = session.get("target_players")

    if target_players and len(players) < target_players:
        await channel.send(
            f"Chưa đủ số người đã đặt để bắt đầu Ma Sói. Hiện có **{len(players)}/{target_players}** người :vv"
        )
        werewolf_sessions.pop(channel_id, None)
        return

    if len(players) < 4:
        await channel.send("Không đủ người để bắt đầu Ma Sói. Cần ít nhất 4 người nha :vv")
        werewolf_sessions.pop(channel_id, None)
        return

    assigned_roles = allocate_werewolf_roles(players, bot_players)

    failed_dm = []
    for user_id, role_name in assigned_roles.items():
        if user_id in bot_players:
            continue
        try:
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)
            await user.send(build_role_dm_text(role_name))
        except discord.HTTPException:
            failed_dm.append(user_id)

    if failed_dm:
        mentions = " ".join(f"<@{uid}>" for uid in failed_dm)
        await channel.send(
            f"Không thể gửi vai trò riêng cho: {mentions}\nHãy bật DM với bot rồi dùng `!startmasoi` lại."
        )
        werewolf_sessions.pop(channel_id, None)
        return

    player_mentions = build_werewolf_player_list(session, players)
    embed = make_embed(
        "Ma Sói bắt đầu",
        f"Đã chốt **{len(players)}** người chơi.\nBot sẽ là **Quản Trò** điều hành ván này.\nVai trò đã được gửi riêng qua DM.\nNgười tham gia: {player_mentions}",
        discord.Color.dark_purple(),
    )
    embed.set_footer(text="Chat chung không hiện vai trò để tránh lộ role.")
    await channel.send(content="@everyone", embed=embed)
    werewolf_sessions[channel_id] = {
        "host_id": session["host_id"],
          "channel": channel,
          "players": set(players),
          "bot_players": set(bot_players),
          "bot_names": dict(session.get("bot_names", {})),
          "closed": True,
        "started": True,
        "roles": assigned_roles,
        "alive_players": set(players),
        "dead_players": set(),
        "phase": "setup",
        "night_number": 0,
        "wolf_votes": {},
        "seer_target": None,
        "guard_target": None,
        "day_votes": {},
        "night_ready": set(),
        "converted_wolves": set(),
        "lovers": {},
        "charmed_players": set(),
        "pending_hunter_shots": set(),
        "witch_heal_used": False,
        "witch_poison_used": False,
        "blacksmith_used": False,
        "cupid_used": False,
        "doppel_used": False,
        "elder_used": False,
        "prince_revealed": False,
        "idiot_revealed": False,
        "wolf_cannot_kill_night": False,
    }
    await start_werewolf_night(werewolf_sessions[channel_id])


def lender_name(lender_id: int) -> str:
    if lender_id == BOT_LENDER_ID:
        return "Bot"
    return f"<@{lender_id}>"


def add_debt(lender_id: int, borrower_id: int, amount: int) -> None:
    due_date = (discord.utils.utcnow().date() + timedelta(days=DEBT_DEFAULT_DAYS)).isoformat()
    get_debts().append(
        {
            "lender_id": lender_id,
            "borrower_id": borrower_id,
            "amount": amount,
            "due_date": due_date,
            "last_reminded": None,
        }
    )


def repay_debt(borrower_id: int, lender_id: int, amount: int) -> tuple[int, int]:
    remaining = amount
    paid = 0
    debts = get_debts()
    for debt in list(debts):
        if debt["borrower_id"] != borrower_id or debt["lender_id"] != lender_id:
            continue
        step = min(debt["amount"], remaining)
        debt["amount"] -= step
        remaining -= step
        paid += step
        if debt["amount"] <= 0:
            debts.remove(debt)
        if remaining <= 0:
            break
    return paid, remaining


def overdue_debts() -> list[dict]:
    today = utc_today()
    return [debt for debt in get_debts() if debt.get("due_date") and debt["due_date"] < today]


def auto_collect_overdue_debts(user_id: int) -> list[tuple[int, int]]:
    wallet = get_user_economy(user_id)
    if wallet["balance"] <= 0:
        return []

    collected: dict[int, int] = defaultdict(int)
    debts = get_debts()
    today = utc_today()

    for debt in list(debts):
        if debt["borrower_id"] != user_id:
            continue
        if not debt.get("due_date") or debt["due_date"] >= today:
            continue
        if wallet["balance"] <= 0:
            break

        step = min(wallet["balance"], debt["amount"])
        if step <= 0:
            continue

        wallet["balance"] -= step
        wallet["lost_total"] += step
        debt["amount"] -= step
        collected[debt["lender_id"]] += step

        if debt["lender_id"] != BOT_LENDER_ID:
            lender_wallet = get_user_economy(debt["lender_id"])
            lender_wallet["balance"] += step
            lender_wallet["earned_total"] += step

        if debt["amount"] <= 0:
            debts.remove(debt)

    if collected:
        save_economy_data()
    return list(collected.items())


def increment_challenge_progress(user_id: int, action: str, amount: int = 1) -> None:
    wallet = get_user_economy(user_id)
    progress = wallet.setdefault("challenge_progress", {})
    progress[action] = progress.get(action, 0) + amount


def get_active_challenge(user_id: int) -> Optional[dict]:
    wallet = get_user_economy(user_id)
    challenge_key = wallet.get("challenge")
    if not challenge_key:
        return None
    for template in CHALLENGE_TEMPLATES:
        if template["key"] == challenge_key:
            return template
    return None


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=get_prefix(), intents=intents, help_command=None)
client: Optional[OpenAI] = None
economy_data = load_economy_data()
bot_route_data = load_bot_route_data()
channel_histories: dict[int, Deque[str]] = defaultdict(lambda: deque(maxlen=12))
pending_mentions: dict[int, asyncio.Task] = {}
mention_roast_counts: dict[tuple[int, int], int] = {}
activity_cooldowns: dict[tuple[int, str], float] = {}
message_timestamps: dict[tuple[int, int], Deque[float]] = defaultdict(deque)
werewolf_sessions: dict[int, dict] = {}
werewolf_violation_counts: dict[tuple[int, int], int] = defaultdict(int)
sleep_reminder_timestamps: dict[tuple[int, int], float] = {}
meme_history: dict[int, Deque[str]] = defaultdict(lambda: deque(maxlen=25))
meme_group_history: dict[int, Deque[str]] = defaultdict(lambda: deque(maxlen=6))
meme_spam_active_channels: set[int] = set()
meme_spam_stop_requests: set[int] = set()
next_werewolf_bot_id = -1


def check_activity_cooldown(user_id: int, activity: str, seconds: int) -> int:
    now = discord.utils.utcnow().timestamp()
    key = (user_id, activity)
    ends_at = activity_cooldowns.get(key, 0.0)
    if ends_at > now:
        return int(ends_at - now) + 1
    activity_cooldowns[key] = now + seconds
    return 0


def prune_old_timestamps(timestamps: Deque[float], now: float, window_seconds: int) -> None:
    while timestamps and now - timestamps[0] > window_seconds:
        timestamps.popleft()


class TaiXiuJoinView(discord.ui.View):
    def __init__(self, host_id: int, bet_amount: int, duration: int):
        super().__init__(timeout=duration)
        self.host_id = host_id
        self.bet_amount = bet_amount
        self.duration = duration
        self.players: dict[int, str] = {}
        self.message: Optional[discord.Message] = None
        self.closed = False

    def build_embed(self) -> discord.Embed:
        tai_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "tai"]
        xiu_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "xiu"]
        embed = make_embed(
            "Phòng Tài Xỉu",
            "Bấm nút để tham gia trước khi hết giờ =)))",
            discord.Color.gold(),
        )
        embed.add_field(name="Cược mỗi người", value=f"{self.bet_amount} xu", inline=True)
        embed.add_field(name="Thời gian", value=f"{self.duration} giây", inline=True)
        embed.add_field(name="Chủ kèo", value=f"<@{self.host_id}>", inline=True)
        embed.add_field(name="Tổng người tham gia", value=str(len(self.players)), inline=True)
        embed.add_field(
            name=f"Cửa Tài ({len(tai_players)})",
            value="\n".join(tai_players) if tai_players else "Chưa có ai",
            inline=True,
        )
        embed.add_field(
            name=f"Cửa Xỉu ({len(xiu_players)})",
            value="\n".join(xiu_players) if xiu_players else "Chưa có ai",
            inline=True,
        )
        embed.set_footer(text="Hết giờ bot sẽ tự lắc xúc xắc và tính tiền")
        return embed

    async def join_side(self, interaction: discord.Interaction, side: str) -> None:
        if self.closed:
            await interaction.response.send_message("Kèo này đóng rồi =))", ephemeral=True)
            return
        user = interaction.user
        if user.bot:
            await interaction.response.send_message("Bot không vào kèo nha :vv", ephemeral=True)
            return
        if user.id in self.players:
            await interaction.response.send_message(
                "Bạn vào kèo rồi, không đổi cửa giữa chừng nha =)))",
                ephemeral=True,
            )
            return
        wallet = get_user_economy(user.id)
        if wallet["balance"] < self.bet_amount:
            await interaction.response.send_message(
                f"Bạn không đủ {self.bet_amount} xu để vào kèo. Số dư hiện tại: {wallet['balance']} xu",
                ephemeral=True,
            )
            return
        wallet["balance"] -= self.bet_amount
        wallet["lost_total"] += self.bet_amount
        save_economy_data()
        self.players[user.id] = side
        await interaction.response.send_message(
            f"Bạn đã vào cửa {side.upper()} với {self.bet_amount} xu :vv",
            ephemeral=True,
        )
        if self.message:
            await self.message.edit(embed=self.build_embed(), view=self)

    async def settle_game(self) -> tuple[list[int], list[int], int, list[int], str]:
        dice = [random.randint(1, 6) for _ in range(3)]
        total = sum(dice)
        result = "tai" if total >= 11 else "xiu"
        winners: list[int] = []
        losers: list[int] = []
        for user_id, side in self.players.items():
            wallet = get_user_economy(user_id)
            if side == result:
                wallet["balance"] += self.bet_amount * 2
                wallet["earned_total"] += self.bet_amount * 2
                winners.append(user_id)
            else:
                losers.append(user_id)
        save_economy_data()
        return winners, losers, total, dice, result

    async def finish(self) -> None:
        if self.closed:
            return
        self.closed = True
        for child in self.children:
            child.disabled = True
        if not self.message:
            return
        if not self.players:
            await self.message.edit(
                embed=make_embed(
                    "Phòng Tài Xỉu",
                    "Hết giờ mà không có ai vào kèo ;-;",
                    discord.Color.dark_grey(),
                ),
                view=self,
            )
            return
        winners, losers, total, dice, result = await self.settle_game()
        dice_text = " ".join(TAIXIU_DICE_EMOJIS[value] for value in dice)
        embed = make_embed(
            "Kết Quả Tài Xỉu",
            f"Xúc xắc: {dice_text}\nTổng: **{total}**\nKết quả: **{result.upper()}**",
            discord.Color.green() if winners else discord.Color.red(),
        )
        embed.add_field(
            name=f"Người thắng ({len(winners)})",
            value="\n".join(f"<@{uid}> +{self.bet_amount} xu" for uid in winners) if winners else "Không có ai thắng",
            inline=False,
        )
        embed.add_field(
            name=f"Người thua ({len(losers)})",
            value="\n".join(f"<@{uid}> -{self.bet_amount} xu" for uid in losers) if losers else "Không có ai thua",
            inline=False,
        )
        await self.message.edit(embed=embed, view=self)

    async def on_timeout(self) -> None:
        await self.finish()

    @discord.ui.button(label="Vào Tài", style=discord.ButtonStyle.success)
    async def join_tai(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "tai")

    @discord.ui.button(label="Vào Xỉu", style=discord.ButtonStyle.danger)
    async def join_xiu(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "xiu")


def draw_card() -> tuple[int, str]:
    return random.choice(FULL_DECK)


def card_text(card: tuple[int, str]) -> str:
    value, suit = card
    if value == 15:
        return "JOKER 🃏"
    return f"{CARD_RANKS[value]}{suit}"


class CardGuessView(discord.ui.View):
    def __init__(self, host_id: int, bet_amount: int, duration: int):
        super().__init__(timeout=duration)
        self.host_id = host_id
        self.bet_amount = bet_amount
        self.duration = duration
        self.base_card = draw_card()
        self.players: dict[int, str] = {}
        self.message: Optional[discord.Message] = None
        self.closed = False

    def build_embed(self) -> discord.Embed:
        high_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "high"]
        low_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "low"]
        embed = make_embed(
            "Phòng Lá Bài",
            f"Lá đầu tiên là **{card_text(self.base_card)}**. Bộ bài dùng **54 lá** và `JOKER` là lá cao nhất. Chọn xem lá sau sẽ cao hơn hay thấp hơn :vv",
            discord.Color.dark_blue(),
        )
        embed.add_field(name="Cược mỗi người", value=f"{self.bet_amount} xu", inline=True)
        embed.add_field(name="Thời gian", value=f"{self.duration} giây", inline=True)
        embed.add_field(name="Chủ phòng", value=f"<@{self.host_id}>", inline=True)
        embed.add_field(name="Tổng người tham gia", value=str(len(self.players)), inline=True)
        embed.add_field(name=f"Chọn Cao Hơn ({len(high_players)})", value="\n".join(high_players) if high_players else "Chưa có ai", inline=True)
        embed.add_field(name=f"Chọn Thấp Hơn ({len(low_players)})", value="\n".join(low_players) if low_players else "Chưa có ai", inline=True)
        embed.set_footer(text="Hết giờ bot sẽ rút lá thứ hai và chốt kết quả")
        return embed

    async def join_side(self, interaction: discord.Interaction, side: str) -> None:
        if self.closed:
            await interaction.response.send_message("Ván này đóng rồi =))", ephemeral=True)
            return
        user = interaction.user
        if user.bot:
            await interaction.response.send_message("Bot không tham gia ván này :vv", ephemeral=True)
            return
        if user.id in self.players:
            await interaction.response.send_message("Bạn chọn rồi, không đổi phe giữa chừng nha =)))", ephemeral=True)
            return
        wallet = get_user_economy(user.id)
        if self.bet_amount > 0 and wallet["balance"] < self.bet_amount:
            await interaction.response.send_message(
                f"Bạn không đủ {self.bet_amount} xu để vào ván. Số dư hiện tại: {wallet['balance']} xu",
                ephemeral=True,
            )
            return
        if self.bet_amount > 0:
            wallet["balance"] -= self.bet_amount
            wallet["lost_total"] += self.bet_amount
            save_economy_data()
        self.players[user.id] = side
        await interaction.response.send_message(
            f"Bạn đã chọn **{'Cao hơn' if side == 'high' else 'Thấp hơn'}** :vv",
            ephemeral=True,
        )
        if self.message:
            await self.message.edit(embed=self.build_embed(), view=self)

    async def finish(self) -> None:
        if self.closed:
            return
        self.closed = True
        for child in self.children:
            child.disabled = True
        if not self.message:
            return
        if not self.players:
            await self.message.edit(
                embed=make_embed("Phòng Lá Bài", "Hết giờ mà chưa có ai tham gia ;-;", discord.Color.dark_grey()),
                view=self,
            )
            return
        final_card = draw_card()
        while final_card[0] == self.base_card[0]:
            final_card = draw_card()
        if final_card[0] > self.base_card[0]:
            result = "high"
            result_text = "Cao hơn"
        else:
            result = "low"
            result_text = "Thấp hơn"
        winners = []
        losers = []
        for uid, side in self.players.items():
            wallet = get_user_economy(uid)
            if side == result:
                if self.bet_amount > 0:
                    wallet["balance"] += self.bet_amount * 2
                    wallet["earned_total"] += self.bet_amount * 2
                winners.append(uid)
            else:
                losers.append(uid)
        save_economy_data()
        embed = make_embed(
            "Kết Quả Lá Bài",
            f"Lá đầu: **{card_text(self.base_card)}**\nLá sau: **{card_text(final_card)}**\nKết quả: **{result_text}**",
            discord.Color.green() if winners else discord.Color.red(),
        )
        embed.add_field(
            name=f"Người thắng ({len(winners)})",
            value="\n".join(f"<@{uid}>" for uid in winners) if winners else "Không có ai thắng",
            inline=False,
        )
        embed.add_field(
            name=f"Người thua ({len(losers)})",
            value="\n".join(f"<@{uid}>" for uid in losers) if losers else "Không có ai thua",
            inline=False,
        )
        if self.bet_amount > 0:
            embed.add_field(name="Tiền cược", value=f"{self.bet_amount} xu mỗi người", inline=False)
        await self.message.edit(embed=embed, view=self)

    async def on_timeout(self) -> None:
        await self.finish()

    @discord.ui.button(label="Cao Hơn", style=discord.ButtonStyle.success)
    async def choose_high(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "high")

    @discord.ui.button(label="Thấp Hơn", style=discord.ButtonStyle.danger)
    async def choose_low(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "low")


class CardColorView(discord.ui.View):
    def __init__(self, host_id: int, bet_amount: int, duration: int):
        super().__init__(timeout=duration)
        self.host_id = host_id
        self.bet_amount = bet_amount
        self.duration = duration
        self.players: dict[int, str] = {}
        self.message: Optional[discord.Message] = None
        self.closed = False

    def build_embed(self) -> discord.Embed:
        red_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "red"]
        black_players = [f"<@{uid}>" for uid, side in self.players.items() if side == "black"]
        embed = make_embed(
            "Phòng Đỏ / Đen",
            "Bấm nút để chọn màu lá bài sau 20 giây :vv",
            discord.Color.dark_red(),
        )
        embed.add_field(name="Cược mỗi người", value=f"{self.bet_amount} xu", inline=True)
        embed.add_field(name="Thời gian", value=f"{self.duration} giây", inline=True)
        embed.add_field(name="Chủ phòng", value=f"<@{self.host_id}>", inline=True)
        embed.add_field(name="Tổng người tham gia", value=str(len(self.players)), inline=True)
        embed.add_field(name=f"Đỏ ({len(red_players)})", value="\n".join(red_players) if red_players else "Chưa có ai", inline=True)
        embed.add_field(name=f"Đen ({len(black_players)})", value="\n".join(black_players) if black_players else "Chưa có ai", inline=True)
        embed.set_footer(text="JOKER sẽ được tính là thắng cho tất cả người chơi")
        return embed

    async def join_side(self, interaction: discord.Interaction, side: str) -> None:
        if self.closed:
            await interaction.response.send_message("Ván này đóng rồi =))", ephemeral=True)
            return
        user = interaction.user
        if user.bot:
            await interaction.response.send_message("Bot không tham gia ván này :vv", ephemeral=True)
            return
        if user.id in self.players:
            await interaction.response.send_message("Bạn chọn rồi nha =)))", ephemeral=True)
            return
        wallet = get_user_economy(user.id)
        if self.bet_amount > 0 and wallet["balance"] < self.bet_amount:
            await interaction.response.send_message(
                f"Bạn không đủ {self.bet_amount} xu để vào ván.",
                ephemeral=True,
            )
            return
        if self.bet_amount > 0:
            wallet["balance"] -= self.bet_amount
            wallet["lost_total"] += self.bet_amount
            save_economy_data()
        self.players[user.id] = side
        await interaction.response.send_message(
            f"Bạn đã chọn **{'Đỏ' if side == 'red' else 'Đen'}** :vv",
            ephemeral=True,
        )
        if self.message:
            await self.message.edit(embed=self.build_embed(), view=self)

    async def finish(self) -> None:
        if self.closed:
            return
        self.closed = True
        for child in self.children:
            child.disabled = True
        if not self.message:
            return
        if not self.players:
            await self.message.edit(
                embed=make_embed("Phòng Đỏ / Đen", "Hết giờ mà chưa có ai tham gia ;-;", discord.Color.dark_grey()),
                view=self,
            )
            return
        card = draw_card()
        if card[0] == 15:
            winners = list(self.players.keys())
            losers = []
            result_text = "JOKER 🃏"
        else:
            result = "red" if card[1] in {"♥", "♦"} else "black"
            result_text = "Đỏ" if result == "red" else "Đen"
            winners = [uid for uid, side in self.players.items() if side == result]
            losers = [uid for uid, side in self.players.items() if side != result]
        for uid in winners:
            if self.bet_amount > 0:
                wallet = get_user_economy(uid)
                wallet["balance"] += self.bet_amount * 2
                wallet["earned_total"] += self.bet_amount * 2
        save_economy_data()
        embed = make_embed(
            "Kết Quả Đỏ / Đen",
            f"Lá rút ra: **{card_text(card)}**\nKết quả: **{result_text}**",
            discord.Color.green() if winners else discord.Color.red(),
        )
        embed.add_field(name="Người thắng", value="\n".join(f"<@{uid}>" for uid in winners) if winners else "Không có ai", inline=False)
        embed.add_field(name="Người thua", value="\n".join(f"<@{uid}>" for uid in losers) if losers else "Không có ai", inline=False)
        await self.message.edit(embed=embed, view=self)

    async def on_timeout(self) -> None:
        await self.finish()

    @discord.ui.button(label="Đỏ", style=discord.ButtonStyle.danger)
    async def choose_red(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "red")

    @discord.ui.button(label="Đen", style=discord.ButtonStyle.secondary)
    async def choose_black(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.join_side(interaction, "black")


class WerewolfRoomView(discord.ui.View):
    def __init__(self, host_id: int, duration: int):
        super().__init__(timeout=duration)
        self.host_id = host_id
        self.duration = duration
        self.players: set[int] = {host_id}
        self.message: Optional[discord.Message] = None
        self.closed = False

    def build_embed(self) -> discord.Embed:
        player_lines = [f"<@{uid}>" for uid in self.players]
        embed = make_embed(
            "Phòng Ma Sói",
            "Bấm nút để tham gia phòng. Hết giờ bot sẽ chốt danh sách người chơi =)))",
            discord.Color.dark_purple(),
        )
        embed.add_field(name="Chủ phòng", value=f"<@{self.host_id}>", inline=True)
        embed.add_field(name="Thời gian chờ", value=f"{self.duration} giây", inline=True)
        embed.add_field(name="Tổng người tham gia", value=str(len(self.players)), inline=True)
        embed.add_field(name=f"Người chơi ({len(self.players)})", value="\n".join(player_lines), inline=False)
        embed.set_footer(text="Đây là phòng chờ Ma Sói, bot chưa tự chạy toàn bộ vai trò.")
        return embed

    async def on_timeout(self) -> None:
        if self.closed:
            return
        self.closed = True
        for child in self.children:
            child.disabled = True
        if self.message:
            embed = self.build_embed()
            embed.title = "Chốt Phòng Ma Sói"
            embed.description = "Danh sách người chơi đã được chốt. Chủ phòng có thể bắt đầu game thủ công."
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Tham gia", style=discord.ButtonStyle.success)
    async def join_room(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.closed:
            await interaction.response.send_message("Phòng đã khóa rồi =))", ephemeral=True)
            return
        if interaction.user.bot:
            await interaction.response.send_message("Bot không vào phòng ma sói đâu :vv", ephemeral=True)
            return
        self.players.add(interaction.user.id)
        await interaction.response.send_message("Bạn đã vào phòng Ma Sói :vv", ephemeral=True)
        if self.message:
            await self.message.edit(embed=self.build_embed(), view=self)


class NativeTicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Ticket",
        style=discord.ButtonStyle.success,
        emoji="🎫",
        custom_id=NATIVE_TICKET_PANEL_CUSTOM_ID,
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Nút này chỉ dùng trong server thôi.", ephemeral=True)
            return
        already_exists = find_existing_ticket_channel(interaction.guild, interaction.user.id)
        try:
            channel = await create_native_ticket_channel(interaction.guild, interaction.user)
        except RuntimeError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.response.send_message("Bot thiếu quyền để tạo ticket channel.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Discord trả lỗi khi tạo ticket. Thử lại sau nha.", ephemeral=True)
            return

        await interaction.response.send_message(f"Ticket của bạn ở đây nè: {channel.mention}", ephemeral=True)
        if already_exists is None:
            opener = interaction.user.mention
            support_role = get_ticket_support_role(interaction.guild)
            support_mention = support_role.mention if support_role else "không có role support"
            embed = make_embed(
                "Ticket Mới",
                f"{opener} đã mở ticket mới.\nSupport: {support_mention}",
                discord.Color.green(),
            )
            embed.add_field(name="Người mở", value=interaction.user.mention, inline=True)
            embed.add_field(name="ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Lưu ý", value="Staff có thể claim, close hoặc delete bằng các nút bên dưới.", inline=False)
            await channel.send(content=f"{interaction.user.mention} {support_mention}", embed=embed, view=NativeTicketManageView())

            log_channel = ticket_log_channel(interaction.guild)
            if log_channel:
                await log_channel.send(
                    embed=make_embed(
                        "Ticket Đã Mở",
                        f"{interaction.user.mention} đã mở {channel.mention}",
                        discord.Color.blurple(),
                    )
                )


class NativeTicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.primary,
        emoji="🛠️",
        custom_id=NATIVE_TICKET_CLAIM_CUSTOM_ID,
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Nút này chỉ dùng trong server thôi.", ephemeral=True)
            return
        if not is_ticket_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff ticket mới claim được nha.", ephemeral=True)
            return
        topic = interaction.channel.topic or ""
        if f"claimed_by:{interaction.user.id}" in topic:
            await interaction.response.send_message("Ticket này đã do bạn claim rồi :vv", ephemeral=True)
            return

        topic = f"{topic} | claimed_by:{interaction.user.id}".strip(" |")
        try:
            await interaction.channel.edit(topic=topic)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message("Bot không sửa được topic ticket này.", ephemeral=True)
            return

        await interaction.response.send_message("Đã claim ticket.", ephemeral=True)
        await interaction.channel.send(
            embed=make_embed(
                "Ticket Đã Được Claim",
                f"{interaction.user.mention} đang nhận ticket này.",
                discord.Color.blue(),
            )
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.secondary,
        emoji="🔒",
        custom_id=NATIVE_TICKET_CLOSE_CUSTOM_ID,
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Nút này chỉ dùng trong server thôi.", ephemeral=True)
            return
        if not is_ticket_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff ticket mới close được nha.", ephemeral=True)
            return

        opener_id = None
        topic = interaction.channel.topic or ""
        for part in topic.split("|"):
            part = part.strip()
            if part.startswith("ticket_owner:"):
                try:
                    opener_id = int(part.split(":", 1)[1])
                except ValueError:
                    opener_id = None
                break
        if opener_id is not None:
            member = interaction.guild.get_member(opener_id)
            if member is not None:
                overwrite = interaction.channel.overwrites_for(member)
                overwrite.send_messages = False
                overwrite.add_reactions = False
                try:
                    await interaction.channel.set_permissions(member, overwrite=overwrite)
                except (discord.Forbidden, discord.HTTPException):
                    pass
        try:
            if not interaction.channel.name.startswith("closed-"):
                await interaction.channel.edit(name=f"closed-{interaction.channel.name[-80:]}")
        except (discord.Forbidden, discord.HTTPException):
            pass

        await interaction.response.send_message("Đã đóng ticket. Có thể delete nếu xong hẳn.", ephemeral=True)
        await interaction.channel.send(
            embed=make_embed(
                "Ticket Đã Đóng",
                f"{interaction.user.mention} đã đóng ticket này.",
                discord.Color.orange(),
            )
        )

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id=NATIVE_TICKET_DELETE_CUSTOM_ID,
    )
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Nút này chỉ dùng trong server thôi.", ephemeral=True)
            return
        if not is_ticket_staff(interaction.user):
            await interaction.response.send_message("Chỉ staff ticket mới delete được nha.", ephemeral=True)
            return

        log_channel = ticket_log_channel(interaction.guild)
        if log_channel:
            transcript = await export_ticket_transcript(interaction.channel)
            await log_channel.send(
                embed=make_embed(
                    "Ticket Đã Xóa",
                    f"{interaction.channel.mention} bị xóa bởi {interaction.user.mention}",
                    discord.Color.red(),
                ),
                file=transcript,
            )

        await interaction.response.send_message("Đang xóa ticket sau 3 giây...", ephemeral=True)
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket bị xóa bởi {interaction.user}")
        except (discord.Forbidden, discord.HTTPException):
            pass


class HelpView(discord.ui.View):
    def __init__(self, prefix: str):
        super().__init__(timeout=None)
        self.prefix = prefix
        self.page = "home"

    def build_embed(self) -> discord.Embed:
        if self.page == "home":
            embed = make_embed("Bảng Lệnh Bot", f"Dùng `{self.prefix}help <nhóm>` để xem từng nhóm lệnh :vv", discord.Color.blurple())
            embed.add_field(name="Trang hiện tại", value="Tổng quan", inline=False)
            return embed
        if self.page == "chat":
            embed = make_embed("Help • Trò chuyện", color=discord.Color.blurple())
            embed.add_field(
                name="Lệnh",
                  value=(
                      f"`{self.prefix}ping` - Kiểm tra bot còn online không\n"
                      f"`{self.prefix}chat <nội_dung>` - Nói chuyện tự nhiên với bot\n"
                      f"`{self.prefix}story [chủ_đề]` - Bot kể một câu chuyện ngắn\n"
                      f"`{self.prefix}reset` - Xóa bộ nhớ hội thoại của kênh hiện tại"
                  ),
                  inline=False,
              )
            return embed
        if self.page == "game":
            embed = make_embed("Help • Game Nhanh", color=discord.Color.gold())
            embed.add_field(
                name="Lệnh",
                  value=(
                      f"`{self.prefix}taixiu <tài|xỉu> [tiền_cược]`\n"
                      f"`{self.prefix}taixiuroom <tiền_cược> [thời_gian]`\n"
                      f"`{self.prefix}keobuaobao <keo|bua|bao> [tiền_cược]`\n"
                      f"`{self.prefix}labaiphong [tiền_cược] [thời_gian]`\n"
                      f"`{self.prefix}dodenphong [tiền_cược] [thời_gian]`\n"
                      f"`{self.prefix}coinflip [ngửa|sấp] [tiền_cược]`\n"
                    f"`{self.prefix}roll [số_tối_đa]`\n"
                    f"`{self.prefix}challenge`\n"
                    f"`{self.prefix}claim`"
                ),
                inline=False,
            )
            return embed
        if self.page == "werewolf":
            embed = make_embed("Help • Ma Sói", color=discord.Color.dark_purple())
            embed.add_field(
                name="Bắt đầu",
                  value=(
                      f"`{self.prefix}startmasoi [thời_gian] [số_người]`\n"
                      f"`{self.prefix}start [thời_gian] [số_người]`\n"
                      f"`{self.prefix}addbotmasoi [số_lượng]`\n"
                      f"`{self.prefix}forcestartmasoi`\n"
                      f"`{self.prefix}yes`\n"
                      "Bot sẽ là **Quản Trò** và gửi role riêng qua DM"
                  ),
                inline=False,
            )
            embed.add_field(
                name="Lệnh trong game",
                value=(
                    f"`{self.prefix}wwkill @tên`\n"
                    f"`{self.prefix}wwsee @tên`\n"
                    f"`{self.prefix}wwguard @tên`\n"
                    f"`{self.prefix}wwsave`\n"
                    f"`{self.prefix}wwpoison @tên`\n"
                    f"`{self.prefix}wwmute @tên`\n"
                    f"`{self.prefix}wwlove @a @b`\n"
                    f"`{self.prefix}wwshield`\n"
                    f"`{self.prefix}wwwatch @tên`\n"
                    f"`{self.prefix}wwcharm @a @b`\n"
                    f"`{self.prefix}wwcopy @tên`\n"
                    f"`{self.prefix}wwrevenge @tên`\n"
                    f"`{self.prefix}wwpass`\n"
                    f"`{self.prefix}vote @tên`\n"
                    f"`{self.prefix}wwstatus`\n"
                    f"`{self.prefix}stopgame`"
                )[:1024],
                inline=False,
            )
            return embed
        if self.page == "economy":
            embed = make_embed("Help • Tiền Ảo", color=discord.Color.green())
            embed.add_field(
                name="Lệnh",
                value=(
                    f"`{self.prefix}daily`\n"
                    f"`{self.prefix}shop`\n"
                    f"`{self.prefix}value`\n"
                    f"`{self.prefix}buy <món>`\n"
                    f"`{self.prefix}fish`\n"
                    f"`{self.prefix}hunt`\n"
                    f"`{self.prefix}chop`\n"
                    f"`{self.prefix}mine`\n"
                    f"`{self.prefix}balance [@tên]`\n"
                    f"`{self.prefix}profile [@tên]`"
                ),
                inline=False,
            )
            return embed
        if self.page == "debt":
            embed = make_embed("Help • Vay / Nợ", color=discord.Color.orange())
            embed.add_field(
                name="Lệnh",
                value=(
                    f"`{self.prefix}give @tên <số_tiền>`\n"
                    f"`{self.prefix}loan @tên <số_tiền>`\n"
                    f"`{self.prefix}borrow <số_tiền>`\n"
                    f"`{self.prefix}debt [@tên]`\n"
                    f"`{self.prefix}repay @tên <số_tiền>`\n"
                    f"`{self.prefix}repaybot <số_tiền>`\n"
                    f"`{self.prefix}overdue`\n"
                    f"`{self.prefix}reminddebt @tên`"
                ),
                inline=False,
            )
            return embed
        if self.page == "fun":
            embed = make_embed("Help • Vui Vẻ", color=discord.Color.magenta())
            embed.add_field(
                name="Lệnh",
                  value=(
                      f"`{self.prefix}meme`\n"
                      f"`{self.prefix}memespam [số_lượng]`\n"
                      f"`{self.prefix}memestop`\n"
                      f"`{self.prefix}font <kiểu> <chữ>`\n"
                      f"`{self.prefix}story [chủ_đề]`\n"
                      f"`{self.prefix}roast @tên`"
                  ),
                  inline=False,
              )
            return embed

        embed = make_embed("Help • Server", color=discord.Color.red())
        embed.add_field(
            name="Bảo vệ / setup",
            value=(
                f"`{self.prefix}clear <số_tin>` / `{self.prefix}trash <số_tin>`\n"
                f"`{self.prefix}setupserver` - Tạo/gom category và kênh theo style đẹp hơn\n"
                f"`{self.prefix}applybotrules` - Áp lại permission cố định cho bot khác theo đúng kênh\n"
                f"`{self.prefix}autosetallbots` - Quét toàn bộ bot ngoài và tự set khu cho từng bot\n"
                f"`{self.prefix}setuproles` - Tự tạo bộ role mẫu cho server\n"
                f"`{self.prefix}setupticketsv2` - Dựng sẵn khung role/kênh/permission cho Tickets v2\n"
                f"`{self.prefix}ticketpanel [#kênh]` - Gửi panel mở ticket"
            ),
            inline=False,
        )
        embed.add_field(
            name="Bot / member",
            value=(
                f"`{self.prefix}changenamebot` - Đổi tên bot thành `SKG|BOT`, gắn role `BOT SKG`\n"
                f"`{self.prefix}changenamemember` - Đổi tên member thành `SKG| tên`\n"
                f"`{self.prefix}setbotzone @bot <zone>` - Gán bot vào khu như `chat`, `welcome`, `giveaway`\n"
                f"`{self.prefix}botchat @bot`, `{self.prefix}botwelcome @bot`, `{self.prefix}botgiveaway @bot`\n"
                f"`{self.prefix}setbotchannel @bot #kênh` - Gán bot vào đúng 1 kênh cụ thể\n"
                f"`{self.prefix}clearbotzone @bot` - Bỏ zone riêng của bot đó\n"
                f"`{self.prefix}checkbotperms` - Kiểm tra bot có quyền nguy hiểm"
            ),
            inline=False,
        )
        embed.add_field(
            name="Dọn server / tự động",
            value=(
                f"`{self.prefix}cleansetupserver` - Xóa toàn bộ layout mà setupserver đã tạo\n"
                f"`{self.prefix}wipeallserver confirm` - Xóa gần như toàn bộ server, giữ lại kênh hiện tại\n"
                "Bot đang tự chống spam tin nhắn liên tục.\n"
                "Bot lạ vào server sẽ bị kick nếu không nằm trong danh sách cho phép.\n"
                "Bot có thể DM admin khi có bot lạ được thêm.\n"
                "Bot khác sẽ bị ép nói đúng kênh theo loại bot."
            ),
            inline=False,
        )
        embed.add_field(
            name="Cải tiến server",
            value=(
                f"`{self.prefix}serverinfo` - Xem thống kê server\n"
                f"`{self.prefix}sendrules [#kênh]` - Gửi bảng 15 luật server\n"
                f"`{self.prefix}announce #kênh <nội_dung>` - Gửi thông báo embed\n"
                f"`{self.prefix}slowmode <giây> [#kênh]` - Đặt slowmode\n"
                f"`{self.prefix}lockchannel [#kênh]` / `{self.prefix}unlockchannel [#kênh]`\n"
                f"`{self.prefix}stylechannel [#kênh] <style> <tên>` - Làm đẹp 1 kênh\n"
                f"`{self.prefix}stylechannels <style> confirm` - Làm đẹp toàn bộ kênh"
            ),
            inline=False,
        )
        embed.add_field(
            name="Quyền dùng lệnh",
            value="Lệnh layout/xóa server vẫn ưu tiên **chủ server**. Lệnh thông báo, slowmode, khóa kênh cần quyền **Manage Server** hoặc **Manage Channels** tùy lệnh.",
            inline=False,
        )
        return embed

    async def switch_page(self, interaction: discord.Interaction, page: str) -> None:
        self.page = page
        try:
            embed = repair_embed(self.build_embed())
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except (discord.HTTPException, discord.InteractionResponded) as exc:
            message = f"Nút help bị lỗi `{type(exc).__name__}`. Gõ lại `{self.prefix}help` giúp mình nha."
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        message = f"Nút help bị lỗi `{type(error).__name__}`. Gõ lại `{self.prefix}help` giúp mình nha."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Tổng quan", style=discord.ButtonStyle.secondary, row=0, custom_id="skg_help_home")
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "home")

    @discord.ui.button(label="Chat", style=discord.ButtonStyle.secondary, row=0, custom_id="skg_help_chat")
    async def chat_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "chat")

    @discord.ui.button(label="Game", style=discord.ButtonStyle.secondary, row=0, custom_id="skg_help_game")
    async def game_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "game")

    @discord.ui.button(label="Ma Sói", style=discord.ButtonStyle.secondary, row=0, custom_id="skg_help_werewolf")
    async def werewolf_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "werewolf")

    @discord.ui.button(label="Tiền Ảo", style=discord.ButtonStyle.secondary, row=1, custom_id="skg_help_economy")
    async def economy_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "economy")

    @discord.ui.button(label="Vay/Nợ", style=discord.ButtonStyle.secondary, row=1, custom_id="skg_help_debt")
    async def debt_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "debt")

    @discord.ui.button(label="Vui Vẻ", style=discord.ButtonStyle.secondary, row=1, custom_id="skg_help_fun")
    async def fun_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "fun")

    @discord.ui.button(label="Server", style=discord.ButtonStyle.secondary, row=1, custom_id="skg_help_server")
    async def server_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.switch_page(interaction, "server")


HELP_PAGE_ORDER = ("chat", "game", "werewolf", "economy", "debt", "fun", "server")
HELP_PAGE_LABELS = {
    "chat": "Chat",
    "game": "Game",
    "werewolf": "Ma Sói",
    "economy": "Tiền Ảo",
    "debt": "Vay/Nợ",
    "fun": "Vui Vẻ",
    "server": "Server",
}
HELP_PAGE_ALIASES = {
    "chat": "chat",
    "trochuyen": "chat",
    "game": "game",
    "masoi": "werewolf",
    "werewolf": "werewolf",
    "ww": "werewolf",
    "tienao": "economy",
    "money": "economy",
    "economy": "economy",
    "vayno": "debt",
    "debt": "debt",
    "no": "debt",
    "vuive": "fun",
    "fun": "fun",
    "server": "server",
    "sever": "server",
}


def normalize_help_page(raw_page: Optional[str]) -> Optional[str]:
    if raw_page is None:
        return None
    key = normalize_lookup_text(raw_page).replace(" ", "")
    return HELP_PAGE_ALIASES.get(key)


def build_help_overview(prefix: str) -> discord.Embed:
    embed = make_embed(
        "Bảng Lệnh Bot",
        "Gõ lệnh theo nhóm bên dưới để xem chi tiết. Bản help này không dùng nút nên sẽ không lỗi tương tác nữa.",
        discord.Color.blurple(),
    )
    embed.add_field(
        name="Nhóm lệnh",
        value="\n".join(f"`{prefix}help {page}` - {HELP_PAGE_LABELS[page]}" for page in HELP_PAGE_ORDER),
        inline=False,
    )
    embed.add_field(
        name="Lệnh nhanh",
        value=(
            f"`{prefix}ping`\n"
            f"`{prefix}font bold SKG server`\n"
            f"`{prefix}changenamebot`\n"
            f"`{prefix}changenamemember`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Làm đẹp / quản lý server",
        value=(
            f"`{prefix}serverinfo`\n"
            f"`{prefix}sendrules [#kênh]`\n"
            f"`{prefix}announce #kênh <nội_dung>`\n"
            f"`{prefix}slowmode <giây> [#kênh]`\n"
            f"`{prefix}lockchannel [#kênh]` / `{prefix}unlockchannel [#kênh]`\n"
            f"`{prefix}stylechannel [#kênh] <style> <tên>`\n"
            f"`{prefix}stylechannels <style> confirm`"
        ),
        inline=False,
    )
    return embed


def build_help_page(prefix: str, page: Optional[str]) -> discord.Embed:
    if page is None:
        return build_help_overview(prefix)
    view = HelpView(prefix)
    view.page = page
    return view.build_embed()


def remember_message(channel_id: int, speaker: str, text: str) -> None:
    content = " ".join(text.split())
    if content:
        channel_histories[channel_id].append(f"{speaker}: {content}")


def pick_meme_url(channel_id: int) -> str:
    recent = meme_history[channel_id]
    recent_groups = meme_group_history[channel_id]
    group_names = list(MEME_GROUPS.keys())
    group_candidates = [group for group in group_names if group not in recent_groups] or group_names
    chosen_group = random.choice(group_candidates)
    available = [url for url in MEME_GROUPS[chosen_group] if url not in recent]
    if not available:
        available = MEME_GROUPS[chosen_group][:]
    if not available:
        recent.clear()
        available = MEME_URLS[:]
    chosen = random.choice(available)
    recent.append(chosen)
    recent_groups.append(chosen_group)
    return chosen


def pick_meme_batch(channel_id: int, count: int) -> list[str]:
    recent = meme_history[channel_id]
    recent_groups = meme_group_history[channel_id]
    chosen: list[str] = []
    group_names = list(MEME_GROUPS.keys())

    while len(chosen) < count:
        group_candidates = [group for group in group_names if group not in recent_groups] or group_names
        chosen_group = random.choice(group_candidates)
        pool = [url for url in MEME_GROUPS[chosen_group] if url not in recent and url not in chosen]
        if not pool:
            pool = [url for url in MEME_GROUPS[chosen_group] if url not in chosen]
        if not pool:
            recent.clear()
            pool = [url for url in MEME_GROUPS[chosen_group] if url not in chosen]
        if not pool:
            pool = MEME_GROUPS[chosen_group][:]
        random.shuffle(pool)
        pick_count = min(max(1, count - len(chosen)), len(pool))
        selected = pool[:pick_count]
        chosen.extend(selected)
        recent_groups.append(chosen_group)

    for url in chosen:
        recent.append(url)
    return chosen


async def get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    for category in guild.categories:
        if category.name == name:
            return category
    return await guild.create_category(name)


async def get_or_create_text_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
) -> discord.TextChannel:
    for channel in guild.text_channels:
        if channel.name == name:
            if channel.category_id != category.id:
                await channel.edit(category=category)
            return channel
    return await guild.create_text_channel(name=name, category=category)


async def get_or_create_voice_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    name: str,
) -> discord.VoiceChannel:
    for channel in guild.voice_channels:
        if channel.name == name:
            if channel.category_id != category.id:
                await channel.edit(category=category)
            return channel
    return await guild.create_voice_channel(name=name, category=category)


async def get_or_create_role(
    guild: discord.Guild,
    *,
    name: str,
    color: discord.Color,
    hoist: bool = False,
    mentionable: bool = False,
) -> discord.Role:
    for role in guild.roles:
        if role.name == name:
            updates: dict[str, object] = {}
            if role.color != color:
                updates["color"] = color
            if role.hoist != hoist:
                updates["hoist"] = hoist
            if role.mentionable != mentionable:
                updates["mentionable"] = mentionable
            if updates:
                await role.edit(reason="Đồng bộ role mẫu của server", **updates)
            return role
    return await guild.create_role(
        name=name,
        color=color,
        hoist=hoist,
        mentionable=mentionable,
        reason="Tạo role mẫu cho server",
    )


async def setup_server_roles(guild: discord.Guild) -> list[str]:
    created_roles: list[str] = []
    for spec in SERVER_STYLE_ROLE_SPECS:
        await get_or_create_role(guild, **spec)
        created_roles.append(spec["name"])
    return created_roles


async def get_or_create_bot_role(guild: discord.Guild) -> discord.Role:
    existing_role = discord.utils.get(guild.roles, name=BOT_ROLE_NAME)
    if existing_role is not None:
        return await get_or_create_role(
            guild,
            name=BOT_ROLE_NAME,
            color=discord.Color.from_rgb(88, 101, 242),
            hoist=True,
            mentionable=False,
        )

    legacy_role = discord.utils.get(guild.roles, name="BOT")
    if legacy_role is not None and BOT_ROLE_NAME != "BOT":
        await legacy_role.edit(
            name=BOT_ROLE_NAME,
            color=discord.Color.from_rgb(88, 101, 242),
            hoist=True,
            mentionable=False,
            reason="Đổi role bot cũ sang BOT SKG",
        )
        return legacy_role

    return await get_or_create_role(
        guild,
        name=BOT_ROLE_NAME,
        color=discord.Color.from_rgb(88, 101, 242),
        hoist=True,
        mentionable=False,
    )


async def assign_bot_role(member: discord.Member) -> bool:
    if not member.bot:
        return False
    me = member.guild.me
    if me is None or not me.guild_permissions.manage_roles:
        return False
    try:
        role = await get_or_create_bot_role(member.guild)
        if role in member.roles:
            return False
        await member.add_roles(role, reason=f"Tự động gắn role {BOT_ROLE_NAME} cho tài khoản bot")
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False


async def setup_tickets_v2_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    roles: dict[str, discord.Role] = {}
    for spec in TICKETS_V2_ROLE_SPECS:
        role = await get_or_create_role(guild, **spec)
        roles[spec["name"]] = role
    return roles


async def setup_tickets_v2_structure(
    guild: discord.Guild,
) -> tuple[dict[str, discord.Role], discord.CategoryChannel, discord.TextChannel, discord.TextChannel, discord.TextChannel]:
    roles = await setup_tickets_v2_roles(guild)
    support_role = roles["Tickets Support"]
    admin_role = roles["Tickets Admin"]

    category = await get_or_create_category(guild, TICKETS_V2_CATEGORY_NAME)
    me = guild.me
    if me is None:
        raise RuntimeError("Bot chưa lấy được member của chính nó trong server.")

    category_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        support_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        admin_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            manage_channels=True,
            manage_messages=True,
        ),
        me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
            manage_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
        ),
    }
    await category.edit(overwrites=category_overwrites, reason="Setup khung Tickets v2")

    panel_channel = await get_or_create_text_channel(guild, category, TICKETS_V2_PANEL_CHANNEL)
    log_channel = await get_or_create_text_channel(guild, category, TICKETS_V2_LOG_CHANNEL)
    notify_channel = await get_or_create_text_channel(guild, category, TICKETS_V2_NOTIFY_CHANNEL)

    await panel_channel.edit(
        overwrites={
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
            ),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_permissions=True,
                manage_messages=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                add_reactions=True,
            ),
        },
        reason="Setup kênh panel Tickets v2",
    )
    await log_channel.edit(reason="Setup kênh transcript/log Tickets v2")
    await notify_channel.edit(reason="Setup kênh notify Tickets v2")
    return roles, category, panel_channel, log_channel, notify_channel


def get_ticket_support_role(guild: discord.Guild) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name="Tickets Support")


def get_ticket_admin_role(guild: discord.Guild) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name="Tickets Admin")


def get_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    return discord.utils.get(guild.categories, name=TICKETS_V2_CATEGORY_NAME)


def ticket_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    return discord.utils.get(guild.text_channels, name=TICKETS_V2_LOG_CHANNEL)


def ticket_panel_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    return discord.utils.get(guild.text_channels, name=TICKETS_V2_PANEL_CHANNEL)


def safe_ticket_channel_name(member: discord.Member) -> str:
    base = normalize_lookup_text(member.display_name).replace(" ", "-")
    filtered = "".join(ch for ch in base if ch.isalnum() or ch == "-").strip("-")
    filtered = filtered or f"user-{member.id}"
    return f"ticket-{filtered[:40]}"


def is_ticket_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    support_role = get_ticket_support_role(member.guild)
    admin_role = get_ticket_admin_role(member.guild)
    role_ids = {role.id for role in member.roles}
    return (
        (support_role is not None and support_role.id in role_ids)
        or (admin_role is not None and admin_role.id in role_ids)
        or is_server_owner(member)
    )


def find_existing_ticket_channel(guild: discord.Guild, member_id: int) -> Optional[discord.TextChannel]:
    category = get_ticket_category(guild)
    if category is None:
        return None
    for channel in category.text_channels:
        topic = channel.topic or ""
        if f"ticket_owner:{member_id}" in topic:
            return channel
    return None


async def create_native_ticket_channel(guild: discord.Guild, member: discord.Member) -> discord.TextChannel:
    existing = find_existing_ticket_channel(guild, member.id)
    if existing is not None:
        return existing

    category = get_ticket_category(guild)
    if category is None:
        raise RuntimeError("Chưa có category ticket.")
    support_role = get_ticket_support_role(guild)
    admin_role = get_ticket_admin_role(guild)
    me = guild.me
    if me is None:
        raise RuntimeError("Bot chưa lấy được member của chính nó trong server.")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
            manage_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
        ),
    }
    if support_role is not None:
        overwrites[support_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
    if admin_role is not None:
        overwrites[admin_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            manage_channels=True,
            manage_messages=True,
        )

    channel = await guild.create_text_channel(
        safe_ticket_channel_name(member),
        category=category,
        overwrites=overwrites,
        topic=f"ticket_owner:{member.id}",
        reason="Tạo ticket mới bằng hệ ticket native",
    )
    return channel


async def export_ticket_transcript(channel: discord.TextChannel) -> discord.File:
    lines: list[str] = []
    async for message in channel.history(limit=200, oldest_first=True):
        created = discord.utils.format_dt(message.created_at, style="T")
        content = message.clean_content or ""
        if message.attachments:
            attach_text = " | ".join(attachment.url for attachment in message.attachments)
            content = f"{content} [attachments: {attach_text}]".strip()
        lines.append(f"[{created}] {message.author} ({message.author.id}): {content}")
    if not lines:
        lines.append("Ticket này chưa có tin nhắn nào.")
    data = "\n".join(lines).encode("utf-8")
    return discord.File(io.BytesIO(data), filename=f"{channel.name}-transcript.txt")


async def cleanup_legacy_server_style(guild: discord.Guild) -> tuple[int, int]:
    deleted_channels = 0
    for channel in list(guild.channels):
        if channel.name in LEGACY_SERVER_STYLE_CHANNELS and channel.name not in CURRENT_SERVER_STYLE_CHANNELS:
            try:
                await channel.delete(reason="Dọn layout cũ do bot dựng trước đó")
                deleted_channels += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

    deleted_categories = 0
    for category in list(guild.categories):
        if category.name in LEGACY_SERVER_STYLE_CATEGORIES and category.name not in CURRENT_SERVER_STYLE_CATEGORIES:
            if any(ch.category_id == category.id for ch in guild.channels):
                continue
            try:
                await category.delete(reason="Dọn category cũ do bot dựng trước đó")
                deleted_categories += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

    return deleted_channels, deleted_categories


async def cleanup_all_server_style(guild: discord.Guild) -> tuple[int, int]:
    removable_channel_names = LEGACY_SERVER_STYLE_CHANNELS | CURRENT_SERVER_STYLE_CHANNELS
    removable_category_names = LEGACY_SERVER_STYLE_CATEGORIES | CURRENT_SERVER_STYLE_CATEGORIES

    deleted_channels = 0
    for channel in list(guild.channels):
        if channel.name in removable_channel_names:
            try:
                await channel.delete(reason="Xóa toàn bộ layout setupserver do bot tạo")
                deleted_channels += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

    deleted_categories = 0
    for category in list(guild.categories):
        if category.name in removable_category_names:
            try:
                await category.delete(reason="Xóa toàn bộ category setupserver do bot tạo")
                deleted_categories += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

    return deleted_channels, deleted_categories


async def wipe_server_except_channel(guild: discord.Guild, keep_channel_id: int) -> tuple[int, int]:
    deleted_channels = 0
    deleted_categories = 0

    keep_channel = guild.get_channel(keep_channel_id)
    if isinstance(keep_channel, discord.abc.GuildChannel) and keep_channel.category_id is not None:
        try:
            await keep_channel.edit(category=None)
        except (discord.Forbidden, discord.HTTPException):
            pass

    for channel in list(guild.channels):
        if channel.id == keep_channel_id:
            continue
        try:
            await channel.delete(reason="Xóa gần như toàn bộ kênh server theo yêu cầu của chủ server")
            deleted_channels += 1
        except (discord.Forbidden, discord.HTTPException):
            continue

    for category in list(guild.categories):
        try:
            await category.delete(reason="Xóa toàn bộ category server theo yêu cầu của chủ server")
            deleted_categories += 1
        except (discord.Forbidden, discord.HTTPException):
            continue

    return deleted_channels, deleted_categories


def is_server_owner(member: discord.Member) -> bool:
    return member.guild.owner_id == member.id


def expected_external_bot_channels_for_text(text: str) -> set[str]:
    haystack = normalize_lookup_text(text)
    matched: set[str] = set()
    for keyword, channel_names in EXTERNAL_BOT_CHANNEL_RULES.items():
        if keyword in haystack:
            matched.update(channel_names)
    return matched or ALLOWED_EXTERNAL_BOT_CHANNELS


def expected_external_bot_channels_for_member(member: discord.Member, extra_text: str = "") -> set[str]:
    override_zone = bot_route_data.get(str(member.id))
    if override_zone and override_zone.startswith("channel:"):
        channel_name = override_zone.split(":", 1)[1]
        return {channel_name}
    if override_zone in BOT_ZONE_CHANNELS:
        return BOT_ZONE_CHANNELS[override_zone]
    return expected_external_bot_channels_for_text(
        f"{member.display_name} {getattr(member, 'name', '')} {extra_text}"
    )


def expected_external_bot_channels(message: discord.Message) -> set[str]:
    return expected_external_bot_channels_for_member(message.author, message.content)


async def apply_external_bot_channel_rules(
    guild: discord.Guild,
    only_member: Optional[discord.Member] = None,
) -> int:
    targets = [only_member] if only_member else await fetch_all_bot_members(guild)
    changed = 0
    text_channels = list(guild.text_channels)

    for member in targets:
        if member is None:
            continue
        if bot.user and member.id == bot.user.id:
            continue

        allowed_channels = expected_external_bot_channels_for_member(member)
        for channel in text_channels:
            try:
                if channel.name in allowed_channels:
                    await channel.set_permissions(member, send_messages=True, view_channel=True)
                else:
                    await channel.set_permissions(member, send_messages=False)
                changed += 1
            except (discord.Forbidden, discord.HTTPException):
                continue

    return changed


async def fetch_all_bot_members(guild: discord.Guild) -> list[discord.Member]:
    members_by_id: dict[int, discord.Member] = {member.id: member for member in guild.members if member.bot}
    if not members_by_id:
        try:
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    members_by_id[member.id] = member
        except (discord.Forbidden, discord.HTTPException):
            pass
    return list(members_by_id.values())


async def dangerous_bot_permission_report(guild: discord.Guild) -> list[str]:
    risky_flags = [
        ("administrator", "Administrator"),
        ("manage_guild", "Manage Server"),
        ("manage_channels", "Manage Channels"),
        ("manage_roles", "Manage Roles"),
        ("manage_webhooks", "Manage Webhooks"),
        ("ban_members", "Ban Members"),
        ("kick_members", "Kick Members"),
        ("moderate_members", "Moderate Members"),
        ("mention_everyone", "Mention Everyone"),
    ]
    lines: list[str] = []
    for member in await fetch_all_bot_members(guild):
        if bot.user and member.id == bot.user.id:
            continue
        perms = member.guild_permissions
        enabled = [label for attr, label in risky_flags if getattr(perms, attr, False)]
        if enabled:
            lines.append(f"`{member.display_name}` -> {', '.join(enabled)}")
    return lines


def guess_bot_zone_from_name(member: discord.Member) -> str:
    haystack = normalize_lookup_text(f"{member.display_name} {getattr(member, 'name', '')}")
    if any(keyword in haystack for keyword in ("welcome", "welcomer", "goodbye", "farewell", "bye")):
        return "welcome"
    if any(keyword in haystack for keyword in ("giveaway", "drop", "gaw")):
        return "giveaway"
    if "ticket" in haystack:
        return "ticket"
    if any(keyword in haystack for keyword in ("boost", "booster")):
        return "boost"
    if "partner" in haystack:
        return "partner"
    if "vouch" in haystack:
        return "vouch"
    return "bot"


async def send_server_style_embeds(channels: dict[str, discord.TextChannel]) -> None:
    announce_channel = channels.get("📢-announcements")
    rule_channel = channels.get("📜-rules")
    role_channel = channels.get("💎-role")
    giveaway_channel = channels.get("🎁-giveaway")
    partner_channel = channels.get("🤝-partner")
    welcome_channel = channels.get("👋-welcome")
    bot_channel = channels.get("🤖-bot-chat")
    team_channel = channels.get("📋-list-team")

    if announce_channel:
        embed = make_embed(
            "Bảng Thông Báo",
            "Nơi cập nhật event, lịch chơi, thay đổi rule và những tin quan trọng của server.",
            discord.Color.from_rgb(255, 196, 87),
        )
        embed.add_field(name="Dùng cho", value="Event, thông báo mở game, lịch call, update bot, thay đổi nội quy.", inline=False)
        embed.add_field(name="Gợi ý", value="Giữ kênh này sạch, ưu tiên để admin/mod đăng cho gọn mắt.", inline=False)
        embed.set_footer(text="Kênh thông báo chính của server ✦")
        await announce_channel.send(embed=embed)

    if rule_channel:
        embed = make_embed(
            "❌ NỘI QUY SERVER ❌",
            "Đọc kỹ trước khi chat và tham gia hoạt động trong server.",
            discord.Color.from_rgb(232, 93, 117),
        )
        embed.add_field(
            name="🚫 Cấm",
            value=(
                "• Gạ gẫm trẻ dưới vị thành niên\n"
                "• Spam dưới mọi hình thức để giữ chat sạch\n"
                "• Toxic quá mức, cãi nhau thì ib riêng mà xử lý\n"
                "• Gửi ảnh kỳ thị hoặc bôi nhọ cá nhân / cộng đồng\n"
                "• Gửi ảnh, video, voice có nội dung 18+\n"
                "• Spam ticket hoặc tạo ticket mà không nói gì\n"
                "• Lạm quyền\n"
                "• Xin role, spam ping, scam\n"
                "• Chia bè chia phái, war nội bộ, kéo người khác đi war\n"
                "• Quảng bá hoặc chia sẻ link nhóm khác khi chưa được đồng ý"
            )[:1024],
            inline=False,
        )
        embed.add_field(
            name="⚖️ Xử lý khi vi phạm",
            value=(
                "• Lần 1: nhắc nhở\n"
                "• Lần 2: mute 30 phút\n"
                "• Lần 3: mute 5 giờ\n"
                "• Lần 4: kick 14 ngày\n"
                "• Lần 5: ban"
            ),
            inline=False,
        )
        embed.add_field(
            name="🤝 Quy tắc ứng xử",
            value=(
                "• Tôn trọng nhau, không chửi bới và bôi nhọ nặng nề\n"
                "• Chửi vui nhẹ thì được, nhưng gây gổ và cãi nhau lớn là không ổn\n"
                "• Tất cả đều là gia đình, cứ tôn trọng nhau mà sống"
            ),
            inline=False,
        )
        embed.add_field(
            name="📌 Ghi chú thêm",
            value=(
                "• Các lệnh liên quan tới quản trị server chỉ chủ server dùng\n"
                "• Member chủ yếu dùng lệnh game và bot thường\n"
                "• Dùng đúng kênh đúng mục đích để server gọn hơn"
            ),
            inline=False,
        )
        embed.set_footer(text="Vi phạm nặng có thể xử lý thẳng mà không cần đi đủ từng mức.")
        await rule_channel.send(embed=embed)

    if role_channel:
        embed = make_embed(
            "Bảng Role",
            "Khu này để xem role của server và ping đúng nhóm khi cần.",
            discord.Color.from_rgb(139, 92, 246),
        )
        embed.add_field(
            name="Role mẫu bot sẽ tự tạo",
            value=(
                "✨ Owner\n"
                "🛡️ Admin\n"
                "🔨 Mod\n"
                "🤖 Bot\n"
                "💎 Booster\n"
                "🎮 Gamer\n"
                "💬 Member\n"
                "🎁 Giveaway Ping\n"
                "🐺 Ma Sói\n"
                "🎵 Music"
            ),
            inline=False,
        )
        embed.add_field(
            name="Dùng khi nào",
            value="Ping role giveaway, role Ma Sói, role booster hoặc tách member cho gọn mắt.",
            inline=False,
        )
        embed.add_field(
            name="Lệnh liên quan",
            value="`!setuproles` để tạo role mẫu riêng, hoặc `!setupserver` để dựng cả kênh lẫn role luôn.",
            inline=False,
        )
        await role_channel.send(embed=embed)

    if giveaway_channel:
        embed = make_embed(
            "Giveaway",
            "Khu này để mở giveaway, công bố quà và chốt người thắng cho gọn.",
            discord.Color.from_rgb(255, 96, 96),
        )
        embed.add_field(name="Nên ghi rõ", value="Tên quà | số lượng | cách tham gia | thời gian kết thúc | cách nhận quà", inline=False)
        embed.add_field(name="Lưu ý", value="Không spam tham gia, không clone acc, không sửa luật giữa chừng khi giveaway đã chạy.", inline=False)
        embed.add_field(name="Gợi ý", value="Nếu có bot giveaway riêng thì chỉ dùng bot đó ở kênh này để tránh loạn thông báo.", inline=False)
        await giveaway_channel.send(embed=embed)

    if partner_channel:
        embed = make_embed(
            "Khu Partner",
            "Nơi trao đổi partner hoặc đăng bài giới thiệu ngắn gọn, sạch và dễ nhìn.",
            discord.Color.from_rgb(255, 194, 87),
        )
        embed.add_field(
            name="Gợi ý nội dung",
            value="Tên server\nLink mời\nĐiểm nổi bật\nRule cơ bản",
            inline=False,
        )
        await partner_channel.send(embed=embed)

    if welcome_channel:
        embed = make_embed(
            "Welcome",
            "Khu chào thành viên mới và ghi nhận ai vừa vào hoặc rời server.",
            discord.Color.from_rgb(128, 224, 170),
        )
        embed.add_field(name="Gợi ý", value="Cho bot welcome, auto role hoặc log join/leave ở đây.", inline=False)
        await welcome_channel.send(embed=embed)

    if bot_channel:
        embed = make_embed(
            "Bot Chat",
            "Kênh dành riêng cho lệnh bot để đỡ trôi chat chính.",
            discord.Color.from_rgb(100, 149, 237),
        )
        embed.add_field(name="Lệnh hay dùng", value="`!help`\n`!meme`\n`!story ma`\n`!taixiu tai 100`\n`!balance`", inline=False)
        await bot_channel.send(embed=embed)

    if team_channel:
        embed = make_embed(
            "List Team",
            "Khu ghi danh team, ally hoặc danh sách thành viên in-game.",
            discord.Color.from_rgb(255, 196, 87),
        )
        embed.add_field(name="Gợi ý", value="Tên team | leader | thành viên | ghi chú ngắn", inline=False)
        embed.add_field(name="Lệnh tiện", value="`!changenamebot` cho bot, `!changenamemember` cho member.", inline=False)
        await team_channel.send(embed=embed)


def cancel_pending_mention(message_id: int) -> None:
    task = pending_mentions.pop(message_id, None)
    if task and not task.done():
        task.cancel()


async def mention_timeout_watch(message: discord.Message) -> None:
    pending_mentions.pop(message.id, None)
    return


def build_prompt(channel_id: int, user_name: str, message_text: str) -> str:
    history = list(channel_histories[channel_id])
    history_text = "\n".join(history) if history else "Chưa có lịch sử."
    return (
        f"Lịch sử gần đây:\n{history_text}\n\n"
        f"Tin nhắn mới từ {user_name}: {message_text}\n\n"
        "Hãy trả lời như một người thật trong chat Discord."
    )


async def generate_natural_reply(channel_id: int, user_name: str, message_text: str) -> str:
    if client is None:
        raise RuntimeError("Chưa có `OPENAI_API_KEY` nên hiện tại bot chưa chat AI được.")
    prompt = build_prompt(channel_id, user_name, message_text)

    def _request() -> str:
        response = client.responses.create(
            model=get_model(),
            instructions=SYSTEM_PROMPT,
            input=prompt,
        )
        return response.output_text

    text = await asyncio.to_thread(_request)
    return sanitize_reply(text)


def should_reply_to_message(message: discord.Message) -> bool:
    if message.author.bot or bot.user is None:
        return False
    if message.content.startswith(get_prefix()):
        return False
    if bot.user in message.mentions:
        return True
    if message.reference and message.reference.resolved:
        referenced = message.reference.resolved
        if isinstance(referenced, discord.Message) and referenced.author == bot.user:
            return True
    return False


def get_active_werewolf_session(channel_id: int) -> Optional[dict]:
    session = werewolf_sessions.get(channel_id)
    if not session:
        return None
    if session.get("closed") and not session.get("started"):
        return None
    return session


def message_contains_werewolf_role(content: str) -> bool:
    normalized = content.lower()
    for aliases in WEREWOLF_ROLE_ALIASES.values():
        if any(alias in normalized for alias in aliases):
            return True
    return False


def message_contains_image_content(message: discord.Message) -> bool:
    if message.attachments:
        return True
    lowered = message.content.lower()
    image_markers = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        "tenor.com",
        "giphy.com",
        "imgur.com",
    )
    return any(marker in lowered for marker in image_markers)


def next_werewolf_timeout_minutes(channel_id: int, user_id: int) -> int:
    key = (channel_id, user_id)
    werewolf_violation_counts[key] = min(werewolf_violation_counts[key] + 1, 5)
    return werewolf_violation_counts[key]


def local_saigon_hour() -> int:
    return datetime.now(timezone(timedelta(hours=7))).hour


def should_send_sleep_reminder(guild_id: int, user_id: int) -> bool:
    hour = local_saigon_hour()
    is_late_night = hour >= SLEEP_REMINDER_START_HOUR or hour < SLEEP_REMINDER_END_HOUR
    if not is_late_night:
        return False
    key = (guild_id, user_id)
    now = discord.utils.utcnow().timestamp()
    last_sent = sleep_reminder_timestamps.get(key, 0.0)
    if now - last_sent < SLEEP_REMINDER_COOLDOWN_SECONDS:
        return False
    sleep_reminder_timestamps[key] = now
    return True


keep_alive_runner: Optional[web.AppRunner] = None
persistent_views_registered = False


async def keep_alive_home(_request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "online",
            "bot": str(bot.user) if bot.user else None,
            "guilds": len(bot.guilds),
        }
    )


async def start_keep_alive_server() -> None:
    global keep_alive_runner
    if keep_alive_runner is not None:
        return

    app = web.Application()
    app.router.add_get("/", keep_alive_home)
    app.router.add_get("/health", keep_alive_home)

    keep_alive_runner = web.AppRunner(app)
    await keep_alive_runner.setup()
    site = web.TCPSite(keep_alive_runner, KEEP_ALIVE_HOST, KEEP_ALIVE_PORT)
    try:
        await site.start()
    except OSError as exc:
        await keep_alive_runner.cleanup()
        keep_alive_runner = None
        print(f"Keep-alive server failed: {type(exc).__name__}: {exc}")
        return

    print(f"Keep-alive server online: http://{KEEP_ALIVE_HOST}:{KEEP_ALIVE_PORT}/")


@bot.event
async def on_ready() -> None:
    global persistent_views_registered
    await start_keep_alive_server()
    if not persistent_views_registered:
        bot.add_view(NativeTicketPanelView())
        bot.add_view(NativeTicketManageView())
        bot.add_view(HelpView(get_prefix()))
        persistent_views_registered = True
    assigned_roles = 0
    for guild in bot.guilds:
        for member in await fetch_all_bot_members(guild):
            if await assign_bot_role(member):
                assigned_roles += 1
    print(f"Bot online: {bot.user} (id={bot.user.id}) | role {BOT_ROLE_NAME} synced={assigned_roles}")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if not member.bot:
        return

    inviter_text = "không xác định"
    if member.guild.me and member.guild.me.guild_permissions.view_audit_log:
        try:
            async for entry in member.guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                target = entry.target
                if target and getattr(target, "id", None) == member.id:
                    inviter_text = f"{entry.user} ({entry.user.id})"
                    break
        except discord.HTTPException:
            pass

    await notify_admin_dm(
        f"[Cảnh báo bot mới]\n"
        f"Server: {member.guild.name} ({member.guild.id})\n"
        f"Bot vừa vào: {member} ({member.id})\n"
        f"Người thêm bot: {inviter_text}"
    )

    if not BOT_ADD_PROTECT:
        await assign_bot_role(member)
        try:
            await apply_external_bot_channel_rules(member.guild, member)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return
    if member.id in ALLOWED_BOT_IDS:
        await assign_bot_role(member)
        try:
            await apply_external_bot_channel_rules(member.guild, member)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return
    try:
        await member.kick(reason="Anti-nuke: bot lạ không nằm trong danh sách cho phép")
    except (discord.Forbidden, discord.HTTPException):
        return
    if member.guild.system_channel:
        await member.guild.system_channel.send(
            f"Đã kick bot lạ `{member}` để bảo vệ server."
        )


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot and message.author.id != (bot.user.id if bot.user else 0):
        if message.guild is not None:
            allowed_channels = expected_external_bot_channels(message)
            if message.channel.name in allowed_channels:
                return
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                return
            try:
                allowed_text = ", ".join(f"`{name}`" for name in sorted(allowed_channels))
                notice = await message.channel.send(
                    embed=make_embed(
                        "Bot Sai Kênh",
                        f"Bot `{message.author.display_name}` chỉ nên gửi ở: {allowed_text}.",
                        discord.Color.orange(),
                    )
                )
                await notice.delete(delay=8)
            except (discord.Forbidden, discord.HTTPException):
                pass
            return
        return
    if message.author.bot:
        return
    if message.content.startswith(get_prefix()):
        collected = auto_collect_overdue_debts(message.author.id)
        if collected:
            summary = "\n".join(
                f"- Đã tự trừ **{amount} xu** để trả cho {lender_name(lender_id)}"
                for lender_id, amount in collected
            )
            wallet = get_user_economy(message.author.id)
            await message.channel.send(
                embed=make_embed(
                    "Tự động thu nợ quá hạn",
                    f"Các khoản vay quá 7 ngày đã bị trừ tự động:\n{summary}\n\n**Số dư còn lại:** {wallet['balance']} xu",
                    discord.Color.orange(),
                )
            )
    ww_session = get_active_werewolf_session(message.channel.id)
    if ww_session and ww_session.get("started") and message.guild is not None:
        role_name = ww_session.get("roles", {}).get(message.author.id)
        if role_name:
            if not is_alive_in_session(ww_session, message.author.id):
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
                return
            if ww_session.get("mute_target") == message.author.id and ww_session.get("phase") == "day":
                try:
                    await message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
                return
            violation_text = None
            if message_contains_werewolf_dm_leak(message.content):
                violation_text = "chuyển tiếp hoặc để lộ tin nhắn riêng của Quản Trò"
            elif message_contains_werewolf_role(message.content):
                violation_text = "nói lộ vai trò trong chat chung"
            elif message_contains_image_content(message):
                violation_text = "gửi hình ảnh trong lúc đang chơi Ma Sói"
            if violation_text:
                timeout_minutes = next_werewolf_timeout_minutes(message.channel.id, message.author.id)
                try:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    await message.author.timeout(
                        discord.utils.utcnow() + timedelta(minutes=timeout_minutes),
                        reason=f"Vi phạm luật Ma Sói: {violation_text}",
                    )
                    await message.channel.send(
                        f"{message.author.mention} đã bị mute **{timeout_minutes} phút** vì {violation_text}."
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass
                return
    if message.guild is not None:
        now = discord.utils.utcnow().timestamp()
        spam_key = (message.guild.id, message.author.id)
        timestamps = message_timestamps[spam_key]
        timestamps.append(now)
        prune_old_timestamps(timestamps, now, SPAM_WINDOW_SECONDS)
        if len(timestamps) >= SPAM_KICK_THRESHOLD:
            try:
                await message.author.kick(reason="Anti-spam: gửi tin nhắn liên tục")
                await message.channel.send(
                    f"{message.author.mention} đã bị kick do spam quá nhiều tin nhắn liên tục."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            finally:
                timestamps.clear()
            return
        if len(timestamps) >= SPAM_MESSAGE_THRESHOLD:
            try:
                await message.author.timeout(
                    discord.utils.utcnow() + timedelta(minutes=SPAM_TIMEOUT_MINUTES),
                    reason="Anti-spam: gửi tin nhắn quá nhanh",
                )
                await message.channel.send(
                    f"{message.author.mention} đã bị timeout {SPAM_TIMEOUT_MINUTES} phút do spam tin nhắn."
                )
            except (discord.Forbidden, discord.HTTPException):
                pass
            finally:
                timestamps.clear()
            return
        if (
            not ww_session
            and not message.content.startswith(get_prefix())
            and should_send_sleep_reminder(message.guild.id, message.author.id)
        ):
            try:
                await message.channel.send(
                    f"{message.author.mention} {random.choice(SLEEP_REMINDER_MESSAGES)}"
                )
            except discord.HTTPException:
                pass
    allowed_werewolf_commands = {"yes", "vote", "wwstatus", "help", "stopgame", "endgame", "stopmasoi", "endmasoi", "addbotmasoi", "thembotmasoi", "forcestartmasoi", "batdaumasoi"}
    command_name = message.content[len(get_prefix()):].split()[0].lower() if message.content.startswith(get_prefix()) and len(message.content) > len(get_prefix()) else ""
    if (
        ww_session
        and message.content.startswith(get_prefix())
        and message.author.id in ww_session.get("players", set())
        and command_name not in allowed_werewolf_commands
    ):
        await message.channel.send(
            f"{message.author.mention} đã vào ván Ma Sói rồi nên tạm thời không dùng lệnh khác được nha :vv"
        )
        return
    await bot.process_commands(message)
    if not should_reply_to_message(message):
        return
    remember_message(message.channel.id, message.author.display_name, message.content)
    async with message.channel.typing():
        try:
            reply = await generate_natural_reply(message.channel.id, message.author.display_name, message.content)
        except RuntimeError as exc:
            await message.reply(str(exc), mention_author=False)
            return
        except Exception as exc:
            await message.reply(
                f"Lỗi kết nối AI: {type(exc).__name__}. Kiểm tra `OPENAI_API_KEY` hoặc mạng rồi thử lại.",
                mention_author=False,
            )
            return
    remember_message(message.channel.id, "Bot", reply)
    await message.reply(reply, mention_author=False)


@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
    await ctx.send(embed=make_embed("Pong!", "Bot vẫn đang online ngon lành :vv", discord.Color.green()))


@bot.command(name="chat")
async def chat(ctx: commands.Context, *, message: str) -> None:
    remember_message(ctx.channel.id, ctx.author.display_name, message)
    async with ctx.typing():
        try:
            reply = await generate_natural_reply(ctx.channel.id, ctx.author.display_name, message)
        except RuntimeError as exc:
            await ctx.send(str(exc))
            return
        except Exception as exc:
            await ctx.send(
                f"Lỗi kết nối AI: {type(exc).__name__}. Kiểm tra `OPENAI_API_KEY` hoặc mạng rồi thử lại."
            )
            return
    remember_message(ctx.channel.id, "Bot", reply)
    await ctx.send(embed=make_embed("Tin nhắn của bot", reply, discord.Color.blurple()))


@bot.command(name="story", aliases=["kchuyen", "ketruyen"])
async def story(ctx: commands.Context, *, topic: Optional[str] = None) -> None:
    async with ctx.typing():
        try:
            story_text = await generate_story(ctx.author.display_name, topic or "")
        except Exception as exc:
            await ctx.send(
                f"Lỗi kể chuyện AI: {type(exc).__name__}. Kiểm tra `OPENAI_API_KEY` hoặc mạng rồi thử lại."
            )
            return
    await ctx.send(embed=make_embed("Bot kể chuyện", story_text, discord.Color.dark_teal()))


@bot.command(name="reset")
async def reset(ctx: commands.Context) -> None:
    channel_histories.pop(ctx.channel.id, None)
    await ctx.send(embed=make_embed("Đã đặt lại", "Bot đã xóa bộ nhớ hội thoại của kênh này.", discord.Color.orange()))


@bot.command(name="taixiu")
async def taixiu(ctx: commands.Context, choice: str, bet_amount: Optional[int] = None) -> None:
    normalized = choice.strip().lower()
    if normalized not in {"tai", "xiu"}:
        await ctx.send(f"Cách dùng: `{get_prefix()}taixiu <tài|xỉu> [tiền_cược]`")
        return
    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    result = "tai" if total >= 11 else "xiu"
    won = normalized == result
    dice_text = " ".join(TAIXIU_DICE_EMOJIS[v] for v in dice)
    money_text = "Không có tiền cược"
    balance_text = "Không đặt cược"
    if bet_amount is not None:
        if bet_amount <= 0:
            await ctx.send("Tiền cược phải lớn hơn 0.")
            return
        wallet = get_user_economy(ctx.author.id)
        if wallet["balance"] < bet_amount:
            await ctx.send(f"Bạn không đủ tiền để cược. Số dư hiện tại: {wallet['balance']} xu")
            return
        if won:
            wallet["balance"] += bet_amount
            wallet["earned_total"] += bet_amount
            money_text = f"+{bet_amount} xu"
            balance_text = f"Số dư mới: {wallet['balance']} xu"
        else:
            wallet["balance"] -= bet_amount
            wallet["lost_total"] += bet_amount
            money_text = f"-{bet_amount} xu"
            balance_text = f"Số dư còn: {wallet['balance']} xu"
        save_economy_data()
    embed = make_embed("Tài Xỉu", f"{ctx.author.mention} vừa lắc xúc xắc :vv", discord.Color.green() if won else discord.Color.red())
    embed.add_field(name="Xúc xắc", value=dice_text, inline=False)
    embed.add_field(name="Tổng điểm", value=str(total), inline=True)
    embed.add_field(name="Bạn chọn", value="Tài" if normalized == "tai" else "Xỉu", inline=True)
    embed.add_field(name="Kết quả", value="Tài" if result == "tai" else "Xỉu", inline=True)
    embed.add_field(name="Tiền thay đổi", value=money_text, inline=True)
    embed.add_field(name="Trạng thái", value="Bạn thắng rồi =)))" if won else "Trượt kèo rồi ;-;", inline=True)
    embed.add_field(name="Ví tiền", value=balance_text, inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc nhẹ", value=reminder, inline=False)
    embed.set_footer(text="Tổng 11-18 là Tài, 3-10 là Xỉu")
    await ctx.send(content="@everyone", embed=embed)


@bot.command(name="taixiuroom")
async def taixiuroom(ctx: commands.Context, bet_amount: int, duration: Optional[int] = None) -> None:
    seconds = duration or 15
    if bet_amount <= 0:
        await ctx.send("Tiền cược phải lớn hơn 0.")
        return
    if seconds < 10 or seconds > 300:
        await ctx.send(f"Cách dùng: `{get_prefix()}taixiuroom <tiền_cược> [thời_gian_từ_10_đến_300_giây]`")
        return
    view = TaiXiuJoinView(ctx.author.id, bet_amount, seconds)
    message = await ctx.send(embed=view.build_embed(), view=view)
    view.message = message


@bot.command(name="labaiphong")
async def labaiphong(ctx: commands.Context, bet_amount: Optional[int] = None, duration: Optional[int] = None) -> None:
    amount = bet_amount or 0
    seconds = duration or 15
    if amount < 0:
        await ctx.send("Tiền cược không được âm.")
        return
    if seconds < 10 or seconds > 120:
        await ctx.send(f"Cách dùng: `{get_prefix()}labaiphong [tiền_cược] [thời_gian]`")
        return
    view = CardGuessView(ctx.author.id, amount, seconds)
    message = await ctx.send(embed=view.build_embed(), view=view)
    view.message = message


@bot.command(name="dodenphong")
async def dodenphong(ctx: commands.Context, bet_amount: Optional[int] = None, duration: Optional[int] = None) -> None:
    amount = bet_amount or 0
    seconds = duration or 15
    if amount < 0:
        await ctx.send("Tiền cược không được âm.")
        return
    if seconds < 10 or seconds > 120:
        await ctx.send(f"Cách dùng: `{get_prefix()}dodenphong [tiền_cược] [thời_gian]`")
        return
    view = CardColorView(ctx.author.id, amount, seconds)
    message = await ctx.send(embed=view.build_embed(), view=view)
    view.message = message


@bot.command(name="masoiphong")
async def masoiphong(ctx: commands.Context, duration: Optional[int] = None) -> None:
    seconds = duration or 15
    if seconds < 10 or seconds > 300:
        await ctx.send(f"Cách dùng: `{get_prefix()}masoiphong [thời_gian]`")
        return
    view = WerewolfRoomView(ctx.author.id, seconds)
    message = await ctx.send(embed=view.build_embed(), view=view)
    view.message = message


@bot.command(name="startmasoi", aliases=["start"])
async def startmasoi(ctx: commands.Context, duration: Optional[int] = None, target_players: Optional[int] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server để mở phòng Ma Sói nha :vv")
        return
    if ctx.channel.id in werewolf_sessions:
        await ctx.send("Kênh này đang có một phòng Ma Sói chờ rồi =))")
        return

    seconds = duration or 15
    if seconds < 10 or seconds > 300:
        await ctx.send(f"Cách dùng: `{get_prefix()}startmasoi [thời_gian_từ_10_đến_300_giây] [số_người_từ_4_đến_{max(WEREWOLF_ROLE_SETS)}]`")
        return

    if target_players is not None and (target_players < 4 or target_players > max(WEREWOLF_ROLE_SETS)):
        await ctx.send(f"Số người cho Ma Sói phải từ **4** đến **{max(WEREWOLF_ROLE_SETS)}** nha :vv")
        return

    session = {
        "host_id": ctx.author.id,
        "channel": ctx.channel,
        "players": {ctx.author.id},
        "bot_players": set(),
        "bot_names": {},
        "closed": False,
        "target_players": target_players,
    }
    werewolf_sessions[ctx.channel.id] = session

    target_text = (
        f"**Sẽ bắt đầu ngay khi đủ {target_players} người.**"
        if target_players
        else "**Cần tối thiểu 4 người để bắt đầu.**"
    )
    embed = make_embed(
        "Đăng ký Ma Sói",
        f"{ctx.author.mention} đã mở phòng Ma Sói.\nGõ `!yes` để tham gia trong **{seconds} giây** :vv\n{target_text}",
        discord.Color.dark_purple(),
    )
    embed.add_field(name="Tổng người tham gia", value="1", inline=True)
    if target_players:
        embed.add_field(name="Mốc bắt đầu", value=str(target_players), inline=True)
    embed.add_field(name="Người chơi hiện tại", value=ctx.author.mention, inline=False)
    embed.set_footer(text="Hết giờ bot sẽ chốt danh sách và gửi vai trò riêng qua DM.")
    await ctx.send(content="@everyone", embed=embed)

    async def _finish() -> None:
        await asyncio.sleep(seconds)
        await close_werewolf_signup(ctx.channel.id)

    asyncio.create_task(_finish())


@bot.command(name="yes")
async def yes(ctx: commands.Context) -> None:
    session = werewolf_sessions.get(ctx.channel.id)
    if not session or session.get("closed"):
        await ctx.send("Kênh này hiện không có phòng Ma Sói nào đang mở để tham gia :vv")
        return
    if ctx.author.bot:
        return
    if ctx.author.id in session["players"]:
        await ctx.send(f"{ctx.author.mention} đã tham gia rồi nha =)))")
        return

    session["players"].add(ctx.author.id)
    player_mentions = build_werewolf_player_list(session, list(session["players"]))
    embed = make_embed(
        "Cập nhật phòng Ma Sói",
        f"{ctx.author.mention} đã tham gia phòng Ma Sói :vv",
        discord.Color.dark_purple(),
    )
    embed.add_field(name="Tổng người tham gia", value=str(len(session["players"])), inline=True)
    if session.get("target_players"):
        embed.add_field(name="Mốc bắt đầu", value=str(session["target_players"]), inline=True)
    embed.add_field(name="Người chơi hiện tại", value=player_mentions, inline=False)
    await ctx.send(embed=embed)
    if session.get("target_players") and len(session["players"]) >= session["target_players"]:
        await close_werewolf_signup(ctx.channel.id)


@bot.command(name="addbotmasoi", aliases=["thembotmasoi"])
async def addbotmasoi(ctx: commands.Context, amount: int = 1) -> None:
    session = werewolf_sessions.get(ctx.channel.id)
    if not session or session.get("closed") or session.get("started"):
        await ctx.send("Chỉ thêm bot được khi phòng Ma Sói đang mở chờ người thôi :vv")
        return
    if ctx.author.id != session.get("host_id") and not ctx.author.guild_permissions.administrator:
        await ctx.send("Chỉ chủ phòng hoặc admin mới thêm bot Ma Sói được.")
        return
    if amount < 1 or amount > 10:
        await ctx.send(f"Cách dùng: `{get_prefix()}addbotmasoi <số_từ_1_đến_10>`")
        return
    max_players = max(WEREWOLF_ROLE_SETS)
    available_slots = max_players - len(session["players"])
    if available_slots <= 0:
        await ctx.send("Phòng Ma Sói đã đủ người tối đa rồi.")
        return
    add_count = min(amount, available_slots)
    global next_werewolf_bot_id
    new_bot_labels: list[str] = []
    for _ in range(add_count):
        bot_id = next_werewolf_bot_id
        next_werewolf_bot_id -= 1
        bot_name = f"Bot {abs(bot_id)}"
        session["players"].add(bot_id)
        session.setdefault("bot_players", set()).add(bot_id)
        session.setdefault("bot_names", {})[bot_id] = bot_name
        new_bot_labels.append(bot_name)

    player_labels = build_werewolf_player_list(session, list(session["players"]))
    embed = make_embed(
        "Đã thêm bot Ma Sói",
        f"Đã thêm **{add_count}** bot vào phòng: {', '.join(new_bot_labels)}",
        discord.Color.dark_purple(),
    )
    embed.add_field(name="Tổng người tham gia", value=str(len(session["players"])), inline=True)
    if session.get("target_players"):
        embed.add_field(name="Mốc bắt đầu", value=str(session["target_players"]), inline=True)
    embed.add_field(name="Người chơi hiện tại", value=player_labels[:1024], inline=False)
    await ctx.send(embed=embed)
    if session.get("target_players") and len(session["players"]) >= session["target_players"]:
        await close_werewolf_signup(ctx.channel.id)


@bot.command(name="forcestartmasoi", aliases=["batdaumasoi"])
async def forcestartmasoi(ctx: commands.Context) -> None:
    session = werewolf_sessions.get(ctx.channel.id)
    if not session or session.get("closed") or session.get("started"):
        await ctx.send("Kênh này hiện không có phòng Ma Sói đang chờ để ép bắt đầu :vv")
        return
    if ctx.author.id != session.get("host_id") and not ctx.author.guild_permissions.administrator:
        await ctx.send("Chỉ chủ phòng hoặc admin mới ép bắt đầu Ma Sói được.")
        return
    if len(session.get("players", set())) < 4:
        await ctx.send("Cần ít nhất **4 người** mới ép bắt đầu Ma Sói được.")
        return
    await ctx.send(embed=make_embed("Ép bắt đầu Ma Sói", "Đủ người rồi, bot đang chốt danh sách và phát role ngay :vv", discord.Color.dark_purple()))
    await close_werewolf_signup(ctx.channel.id)


@bot.command(name="wwkill")
async def wwkill(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot để giữ bí mật nha.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Bạn hiện không ở trong ván Ma Sói đang chạy.")
        return
    if session.get("phase") != "night":
        await ctx.send("Hiện không phải ban đêm.")
        return
    if session["roles"].get(ctx.author.id) not in WEREWOLF_WOLF_ROLES:
        await ctx.send("Bạn không phải phe Sói để dùng lệnh này.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    if player_is_wolf(session, target_id):
        await ctx.send("Phe Sói không thể tự cắn lẫn nhau.")
        return
    session["wolf_votes"][ctx.author.id] = target_id
    session["wolf_target_preview"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận mục tiêu cắn: **{werewolf_player_label(session, target_id)}**")
    witches_alive = [uid for uid in alive_players(session) if player_role(session, uid) in WEREWOLF_WITCH_ROLES]
    wolves_alive = [uid for uid in alive_players(session) if player_is_wolf(session, uid)]
    if witches_alive and len(session["wolf_votes"]) >= len(wolves_alive):
        for witch_id in witches_alive:
            try:
                await send_private_message(
                    witch_id,
                      f"Sói đang nhắm **{werewolf_player_label(session, target_id)}**. Bạn có thể dùng `!wwsave`, `!wwpoison @tên`, hoặc `!wwpass`.",
                )
            except discord.HTTPException:
                pass
    await try_resolve_werewolf_night(session)


@bot.command(name="wwsee")
async def wwsee(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot để giữ bí mật nha.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Bạn hiện không ở trong ván Ma Sói đang chạy.")
        return
    if session.get("phase") != "night":
        await ctx.send("Hiện không phải ban đêm.")
        return
    if session["roles"].get(ctx.author.id) not in WEREWOLF_SEER_ROLES:
        await ctx.send("Bạn không có khả năng soi.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    if target_id == ctx.author.id:
        await ctx.send("Không tự soi chính mình nha :vv")
        return
    session["seer_target"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận mục tiêu soi: **{werewolf_player_label(session, target_id)}**")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwguard")
async def wwguard(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot để giữ bí mật nha.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Bạn hiện không ở trong ván Ma Sói đang chạy.")
        return
    if session.get("phase") != "night":
        await ctx.send("Hiện không phải ban đêm.")
        return
    if session["roles"].get(ctx.author.id) not in WEREWOLF_GUARD_ROLES:
        await ctx.send("Bạn không có khả năng bảo vệ.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    session["guard_target"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận người được bảo vệ: **{werewolf_player_label(session, target_id)}**")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwpass")
async def wwpass(ctx: commands.Context) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot để bỏ qua hành động đêm.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Bạn hiện không ở trong ván Ma Sói đang chạy.")
        return
    current_phase = session.get("phase")
    if current_phase not in {"night", "hunter_revenge"}:
        await ctx.send("Hiện không có hành động nào để bỏ qua.")
        return
    session.setdefault("night_ready", set()).add(ctx.author.id)
    if current_phase == "hunter_revenge":
        session.setdefault("pending_hunter_shots", set()).discard(ctx.author.id)
        await ctx.send("Đã bỏ qua phát bắn cuối của Thợ Săn.")
        if not session.get("pending_hunter_shots"):
            if await check_werewolf_victory(session):
                return
            await start_werewolf_night(session)
        return
    await ctx.send("Đã bỏ qua hành động đêm này.")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwsave")
async def wwsave(ctx: commands.Context) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night" or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Hiện không thể dùng kỹ năng cứu.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_WITCH_ROLES:
        await ctx.send("Bạn không phải Phù Thủy.")
        return
    if session.get("witch_heal_used"):
        await ctx.send("Bạn đã dùng thuốc cứu rồi.")
        return
    session["witch_saved"] = True
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send("Đã ghi nhận dùng thuốc cứu cho mục tiêu bị Sói nhắm.")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwpoison")
async def wwpoison(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night" or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Hiện không thể dùng thuốc độc.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_WITCH_ROLES:
        await ctx.send("Bạn không phải Phù Thủy.")
        return
    if session.get("witch_poison_used"):
        await ctx.send("Bạn đã dùng thuốc độc rồi.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    if target_id == ctx.author.id:
        await ctx.send("Không tự đầu độc mình nha =))")
        return
    session["witch_poison_target"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận mục tiêu đầu độc: **{werewolf_player_label(session, target_id)}**")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwmute")
async def wwmute(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night" or not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Hiện không thể dùng khóa chat.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_MUTE_WITCH_ROLES:
        await ctx.send("Bạn không phải Phù Thủy Câm.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    session["mute_target"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận mục tiêu bị câm: **{werewolf_player_label(session, target_id)}**")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwlove")
async def wwlove(ctx: commands.Context, *, targets: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night" or session.get("night_number") != 1:
        await ctx.send("Cupid chỉ ghép đôi vào Đêm 1 thôi.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_CUPID_ROLES:
        await ctx.send("Bạn không phải Cupid.")
        return
    if session.get("cupid_used"):
        await ctx.send("Bạn đã ghép đôi rồi.")
        return
    resolved = parse_two_dm_targets(session, targets)
    if len(resolved) < 2:
        await ctx.send("Hãy dùng `!wwlove @người1 @người2` hoặc nhập 2 mục tiêu hợp lệ.")
        return
    member_a_id, member_b_id = resolved[0], resolved[1]
    if member_a_id == member_b_id or member_a_id not in session["players"] or member_b_id not in session["players"]:
        await ctx.send("Hãy chọn 2 người chơi khác nhau trong ván.")
        return
    session["lovers"][member_a_id] = member_b_id
    session["lovers"][member_b_id] = member_a_id
    session["cupid_used"] = True
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghép đôi **{werewolf_player_label(session, member_a_id)}** với **{werewolf_player_label(session, member_b_id)}**.")
    for member_id in (member_a_id, member_b_id):
        try:
            await send_private_message(member_id, "Bạn đã bị Cupid ghép đôi. Nếu người yêu chết, bạn cũng sẽ chết theo.")
        except discord.HTTPException:
            pass
    await try_resolve_werewolf_night(session)


@bot.command(name="wwshield")
async def wwshield(ctx: commands.Context) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night":
        await ctx.send("Hiện không thể dùng lá chắn.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_BLACKSMITH_ROLES:
        await ctx.send("Bạn không phải Thợ Rèn.")
        return
    if session.get("blacksmith_used"):
        await ctx.send("Bạn đã dùng lá chắn cả làng rồi.")
        return
    session["blacksmith_active"] = True
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send("Đã kích hoạt lá chắn cho cả làng trong đêm nay.")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwwatch")
async def wwwatch(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night":
        await ctx.send("Hiện không thể canh gác.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_WATCHMAN_ROLES:
        await ctx.send("Bạn không phải Người Gác Đêm.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    session["watch_target"] = target_id
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã ghi nhận mục tiêu theo dõi: **{werewolf_player_label(session, target_id)}**")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwcharm")
async def wwcharm(ctx: commands.Context, *, targets: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night":
        await ctx.send("Hiện không thể thôi miên.")
        return
    if player_role(session, ctx.author.id) not in WEREWOLF_PIPER_ROLES:
        await ctx.send("Bạn không phải Người Thổi Sáo.")
        return
    resolved = parse_two_dm_targets(session, targets)
    target_ids = [uid for uid in dict.fromkeys(resolved) if uid in session["players"] and uid != ctx.author.id and is_alive_in_session(session, uid)]
    if not target_ids:
        await ctx.send("Không có mục tiêu hợp lệ để thôi miên.")
        return
    session.setdefault("charmed_players", set()).update(target_ids)
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Đã thôi miên: {' '.join(werewolf_player_label(session, uid) for uid in target_ids)}")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwcopy")
async def wwcopy(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or session.get("phase") != "night" or session.get("night_number") != 1:
        await ctx.send("Doppelganger chỉ copy role vào Đêm 1 thôi.")
        return
    if player_role(session, ctx.author.id) != "Doppelganger":
        await ctx.send("Bạn không phải Doppelganger.")
        return
    if session.get("doppel_used"):
        await ctx.send("Bạn đã copy role rồi.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id) or target_id == ctx.author.id:
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng tên thường, `@tên`, hoặc `<tên>` của người chơi trong server.")
        return
    copied_role = player_role(session, target_id)
    session["roles"][ctx.author.id] = copied_role
    session["doppel_used"] = True
    session.setdefault("night_ready", set()).add(ctx.author.id)
    await ctx.send(f"Bạn đã copy role **{copied_role}** từ **{werewolf_player_label(session, target_id)}**.")
    await try_resolve_werewolf_night(session)


@bot.command(name="wwrevenge")
async def wwrevenge(ctx: commands.Context, *, target: str) -> None:
    if ctx.guild is not None:
        await ctx.send("Lệnh này dùng trong DM với bot.")
        return
    session = get_session_by_player(ctx.author.id)
    if not session or ctx.author.id not in session.get("pending_hunter_shots", set()):
        await ctx.send("Hiện bạn không có phát bắn trả thù nào.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Không tìm thấy mục tiêu hợp lệ đang còn sống. Hãy thử dùng `@mention`, tên hiển thị hoặc tên Discord trong server.")
        return
    await kill_player(session, target_id, "bị Thợ Săn kéo theo", announce_to_channel=True)
    session["pending_hunter_shots"].discard(ctx.author.id)
    await ctx.send(f"Đã ghi nhận phát bắn trả thù vào **{werewolf_player_label(session, target_id)}**.")
    if await check_werewolf_victory(session):
        return
    if not session.get("pending_hunter_shots"):
        await start_werewolf_night(session)


@bot.command(name="vote")
async def vote(ctx: commands.Context, *, target: str) -> None:
    session = werewolf_sessions.get(ctx.channel.id)
    if not session or not session.get("started"):
        await ctx.send("Kênh này hiện không có ván Ma Sói đang chạy.")
        return
    if session.get("phase") != "day":
        await ctx.send("Hiện chưa phải ban ngày để vote treo.")
        return
    if not is_alive_in_session(session, ctx.author.id):
        await ctx.send("Bạn đã chết rồi nên không vote được nữa.")
        return
    if session.get("mute_target") == ctx.author.id:
        await ctx.send("Bạn đang bị câm hôm nay nên không vote được.")
        return
    target_id = resolve_dm_target(session, target)
    if target_id is None or not is_alive_in_session(session, target_id):
        await ctx.send("Người đó không còn sống để vote.")
        return
    if target_id == ctx.author.id:
        await ctx.send("Tự vote treo mình thì căng quá nha =))")
        return
    session["day_votes"][ctx.author.id] = target_id
    await ctx.send(f"{ctx.author.mention} đã vote treo **{werewolf_player_label(session, target_id)}**.")
    await try_resolve_werewolf_day(session)


@bot.command(name="wwstatus")
async def wwstatus(ctx: commands.Context) -> None:
    session = werewolf_sessions.get(ctx.channel.id)
    if not session or not session.get("started"):
        await ctx.send("Kênh này hiện không có ván Ma Sói đang chạy.")
        return
    alive_mentions = build_werewolf_player_list(session, alive_players(session))
    dead_mentions = build_werewolf_player_list(session, session.get("dead_players", set())) or "Chưa ai chết"
    phase_text = {
        "night": "Ban đêm",
        "day": "Ban ngày",
        "hunter_revenge": "Thợ Săn trả thù",
    }.get(session.get("phase"), str(session.get("phase")))
    embed = make_embed("Trạng thái Ma Sói", color=discord.Color.dark_purple())
    embed.add_field(name="Pha hiện tại", value=phase_text, inline=True)
    embed.add_field(name="Đêm thứ", value=str(session.get("night_number", 0)), inline=True)
    embed.add_field(name="Người còn sống", value=alive_mentions or "Không còn ai", inline=False)
    embed.add_field(name="Người đã chết", value=dead_mentions, inline=False)
    if session.get("mute_target") and is_alive_in_session(session, session["mute_target"]):
        embed.add_field(name="Đang bị câm", value=werewolf_player_label(session, session["mute_target"]), inline=True)
    if session.get("charmed_players"):
        embed.add_field(name="Đã bị thôi miên", value=build_werewolf_player_list(session, sorted(session["charmed_players"]))[:1024], inline=False)
    await ctx.send(embed=embed)


@bot.command(name="stopgame", aliases=["endgame", "stopmasoi", "endmasoi"])
async def stopgame(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi.")
        return
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_guild):
        await ctx.send("Chỉ admin hoặc người có quyền **Manage Server** mới dừng game được.")
        return
    session = werewolf_sessions.get(ctx.channel.id)
    if not session:
        await ctx.send("Kênh này hiện không có game Ma Sói nào đang chạy.")
        return
    werewolf_sessions.pop(ctx.channel.id, None)
    await ctx.send(
        embed=make_embed(
            "Dừng game",
            f"Ván Ma Sói trong kênh này đã được dừng bởi {ctx.author.mention}.",
            discord.Color.red(),
        )
    )


@bot.command(name="coinflip")
async def coinflip(ctx: commands.Context, choice: Optional[str] = None, bet_amount: Optional[int] = None) -> None:
    result = random.choice(["ngua", "sap"])
    if choice is None:
        await ctx.send(embed=make_embed("Coinflip", f"Đồng xu ra: **{result.upper()}**", discord.Color.gold()))
        return
    increment_challenge_progress(ctx.author.id, "coinflip")
    normalized = choice.strip().lower()
    if normalized not in {"ngua", "sap"}:
        await ctx.send(f"Cách dùng: `{get_prefix()}coinflip [ngửa|sấp] [tiền_cược]`")
        return
    if bet_amount is None:
        await ctx.send(f"Nếu muốn cược, dùng: `{get_prefix()}coinflip ngua 100`")
        return
    if bet_amount <= 0:
        await ctx.send("Tiền cược phải lớn hơn 0.")
        return


    wallet = get_user_economy(ctx.author.id)
    if wallet["balance"] < bet_amount:
        await ctx.send(f"Bạn không đủ tiền để cược. Số dư hiện tại: {wallet['balance']} xu")
        return
    if normalized == result:
        wallet["balance"] += bet_amount
        wallet["earned_total"] += bet_amount
        save_economy_data()
        embed = make_embed(
            "Coinflip",
            f"Đồng xu ra: **{result.upper()}**\nBạn đoán đúng và thắng **{bet_amount} xu** =)))\n**Số dư mới:** {wallet['balance']} xu",
            discord.Color.green(),
        )
    else:
        wallet["balance"] -= bet_amount
        wallet["lost_total"] += bet_amount
        save_economy_data()
        embed = make_embed(
            "Coinflip",
            f"Đồng xu ra: **{result.upper()}**\nBạn đoán **{normalized}** nên thua **{bet_amount} xu** ;-;\n**Số dư còn:** {wallet['balance']} xu",
            discord.Color.red(),
        )
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc nhẹ", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="keobuaobao", aliases=["rps", "duelbot"])
async def keobuaobao(ctx: commands.Context, choice: str, bet_amount: Optional[int] = None) -> None:
    normalized = choice.strip().lower()
    if normalized not in RPS_BEATS:
        await ctx.send(f"Cách dùng: `{get_prefix()}keobuaobao <keo|bua|bao> [tiền_cược]`")
        return

    bot_choice = random.choice(list(RPS_BEATS.keys()))
    result_text = ""
    color = discord.Color.gold()

    if bet_amount is not None:
        if bet_amount <= 0:
            await ctx.send("Tiền cược phải lớn hơn 0.")
            return
        wallet = get_user_economy(ctx.author.id)
        if wallet["balance"] < bet_amount:
            await ctx.send(f"Bạn không đủ tiền để cược. Số dư hiện tại: {wallet['balance']} xu")
            return

        if normalized == bot_choice:
            result_text = f"Hòa kèo, không ai ăn ai cả :vv\n**Số dư hiện tại:** {wallet['balance']} xu"
        elif RPS_BEATS[normalized] == bot_choice:
            wallet["balance"] += bet_amount
            wallet["earned_total"] += bet_amount
            result_text = f"Bạn thắng bot và ăn **{bet_amount} xu** =)))\n**Số dư mới:** {wallet['balance']} xu"
            color = discord.Color.green()
        else:
            wallet["balance"] -= bet_amount
            wallet["lost_total"] += bet_amount
            result_text = f"Bot thắng kèo này rồi ;-;\nBạn mất **{bet_amount} xu**\n**Số dư còn:** {wallet['balance']} xu"
            color = discord.Color.red()
        save_economy_data()
    else:
        if normalized == bot_choice:
            result_text = "Hòa luôn =)) bot với bạn ngang cơ phết."
        elif RPS_BEATS[normalized] == bot_choice:
            result_text = "Bạn thắng bot rồi đó =)))"
            color = discord.Color.green()
        else:
            result_text = "Bot thắng nha :> thử lại kèo khác xem."
            color = discord.Color.red()

    embed = make_embed(
        "Kéo Búa Bao với Bot",
        (
            f"**Bạn chọn:** {RPS_LABELS[normalized]}\n"
            f"**Bot chọn:** {RPS_LABELS[bot_choice]}\n\n"
            f"{result_text}"
        ),
        color,
    )
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc nhẹ", value=reminder, inline=False)
    await ctx.send(embed=embed)


FONT_STYLE_ALIASES = {
    "b": "bold",
    "bold": "bold",
    "dam": "bold",
    "i": "italic",
    "italic": "italic",
    "nghieng": "italic",
    "bi": "bolditalic",
    "bolditalic": "bolditalic",
    "damnghieng": "bolditalic",
    "sans": "sans",
    "sansbold": "sansbold",
    "sansdam": "sansbold",
    "mono": "mono",
    "monospace": "mono",
    "full": "fullwidth",
    "fullwidth": "fullwidth",
    "wide": "fullwidth",
    "small": "smallcaps",
    "smallcaps": "smallcaps",
    "caps": "smallcaps",
}
FONT_STYLE_NAMES = ("bold", "italic", "bolditalic", "sans", "sansbold", "mono", "fullwidth", "smallcaps")
SMALLCAPS_LETTERS = dict(
    zip(
        "abcdefghijklmnopqrstuvwxyz",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
    )
)


def translate_font_ranges(
    text: str,
    upper_start: int,
    lower_start: int,
    digit_start: Optional[int] = None,
) -> str:
    converted = []
    for char in text:
        if "A" <= char <= "Z":
            converted.append(chr(upper_start + ord(char) - ord("A")))
        elif "a" <= char <= "z":
            converted.append(chr(lower_start + ord(char) - ord("a")))
        elif digit_start is not None and "0" <= char <= "9":
            converted.append(chr(digit_start + ord(char) - ord("0")))
        else:
            converted.append(char)
    return "".join(converted)


def translate_fullwidth(text: str) -> str:
    converted = []
    for char in text:
        if char == " ":
            converted.append("　")
        elif 33 <= ord(char) <= 126:
            converted.append(chr(ord(char) + 0xFEE0))
        else:
            converted.append(char)
    return "".join(converted)


def translate_smallcaps(text: str) -> str:
    return "".join(SMALLCAPS_LETTERS.get(char.casefold(), char) if char.isalpha() else char for char in text)


def stylize_text(style: str, text: str) -> str:
    if style == "bold":
        return translate_font_ranges(text, 0x1D400, 0x1D41A, 0x1D7CE)
    if style == "italic":
        return translate_font_ranges(text, 0x1D434, 0x1D44E)
    if style == "bolditalic":
        return translate_font_ranges(text, 0x1D468, 0x1D482)
    if style == "sans":
        return translate_font_ranges(text, 0x1D5A0, 0x1D5BA, 0x1D7E2)
    if style == "sansbold":
        return translate_font_ranges(text, 0x1D5D4, 0x1D5EE, 0x1D7EC)
    if style == "mono":
        return translate_font_ranges(text, 0x1D670, 0x1D68A, 0x1D7F6)
    if style == "fullwidth":
        return translate_fullwidth(text)
    if style == "smallcaps":
        return translate_smallcaps(text)
    return text


def normalize_font_style(style: str) -> Optional[str]:
    key = normalize_lookup_text(style).replace(" ", "")
    return FONT_STYLE_ALIASES.get(key)


@bot.command(name="font", aliases=["fonts", "fontchu", "kieu", "fancy"])
async def font_command(ctx: commands.Context, style: Optional[str] = None, *, text: Optional[str] = None) -> None:
    prefix = get_prefix()
    if style is None or text is None:
        embed = make_embed(
            "Đổi Font Chữ",
            f"Cách dùng: `{prefix}font <kiểu> <chữ>`",
            discord.Color.magenta(),
        )
        embed.add_field(name="Kiểu có sẵn", value=", ".join(f"`{name}`" for name in FONT_STYLE_NAMES), inline=False)
        embed.add_field(
            name="Ví dụ",
            value=f"`{prefix}font bold SKG server`\n`{prefix}font mono hello 123`\n`{prefix}font fullwidth xin chào`",
            inline=False,
        )
        embed.set_footer(text="Chữ tiếng Việt có dấu có thể giữ nguyên nếu Unicode không có bản font tương ứng.")
        await ctx.send(embed=embed)
        return

    normalized_style = normalize_font_style(style)
    if normalized_style is None:
        await ctx.send(
            f"Kiểu font chưa có. Dùng một trong các kiểu: {', '.join(f'`{name}`' for name in FONT_STYLE_NAMES)}"
        )
        return

    result = stylize_text(normalized_style, text.strip())
    if not result:
        await ctx.send(f"Cách dùng: `{prefix}font <kiểu> <chữ>`")
        return
    if len(result) > 1900:
        result = f"{result[:1900]}..."

    embed = make_embed(f"Font • {normalized_style}", result, discord.Color.magenta())
    embed.set_footer(text="Copy phần chữ trong embed để dùng trong chat/tên kênh/rule.")
    await ctx.send(embed=embed)


@bot.command(name="meme")
async def meme(ctx: commands.Context) -> None:
    increment_challenge_progress(ctx.author.id, "meme")
    embed = make_embed("Meme ngẫu nhiên", "Xem tạm cho vui =)))", discord.Color.random())
    embed.set_image(url=pick_meme_url(ctx.channel.id))
    await ctx.send(embed=embed)


@bot.command(name="memespam")
async def memespam(ctx: commands.Context, amount: Optional[int] = None) -> None:
    count = amount or 3
    if count < 1 or count > MAX_MEME_SPAM:
        await ctx.send(f"Cách dùng: `{get_prefix()}memespam [số_lượng_từ_1_đến_{MAX_MEME_SPAM}]`")
        return
    if ctx.channel.id in meme_spam_active_channels:
        await ctx.send(f"Kênh này đang spam meme rồi. Dùng `{get_prefix()}memestop` để dừng trước nha :vv")
        return
    meme_spam_active_channels.add(ctx.channel.id)
    meme_spam_stop_requests.discard(ctx.channel.id)
    await ctx.send(embed=make_embed("Bắt đầu spam meme", f"Đang gửi **{count}** meme. Discord có thể chậm và rate limit nếu spam quá mạnh :vv", discord.Color.orange()))
    urls = pick_meme_batch(ctx.channel.id, count)
    try:
        for index, url in enumerate(urls, start=1):
            if ctx.channel.id in meme_spam_stop_requests:
                await ctx.send(embed=make_embed("Đã dừng memespam", f"Đã dừng ở meme **{index - 1}/{count}** theo yêu cầu.", discord.Color.red()))
                break
            embed = make_embed(f"Meme {index}/{count}", color=discord.Color.random())
            embed.set_image(url=url)
            await ctx.send(embed=embed)
            await asyncio.sleep(0.35)
    finally:
        meme_spam_active_channels.discard(ctx.channel.id)
        meme_spam_stop_requests.discard(ctx.channel.id)


@bot.command(name="memestop")
async def memestop(ctx: commands.Context) -> None:
    if ctx.channel.id not in meme_spam_active_channels:
        await ctx.send("Kênh này hiện không có memespam nào đang chạy cả :>")
        return
    meme_spam_stop_requests.add(ctx.channel.id)
    await ctx.send(embed=make_embed("Đang dừng memespam", "Bot sẽ dừng ngay sau meme hiện tại.", discord.Color.orange()))


@bot.command(name="roast")
async def roast(ctx: commands.Context, member: discord.Member) -> None:
    if member.bot:
        await ctx.send("Bot với nhau thì tha nhau đi =))")
        return
    if member == ctx.author:
        await ctx.send("Tự roast mình nghe hơi khó đỡ nha :vv")
        return
    await ctx.send(embed=make_embed("Roast nhẹ", f"{member.mention} {random.choice(DIRECT_ROAST_MESSAGES)}", discord.Color.magenta()))


@bot.command(name="roll")
async def roll(ctx: commands.Context, max_number: Optional[int] = None) -> None:
    limit = max_number or 100
    if limit < 2 or limit > 1000:
        await ctx.send(f"Cách dùng: `{get_prefix()}roll [số_tối_đa_từ_2_đến_1000]`")
        return
    value = random.randint(1, limit)
    await ctx.send(embed=make_embed("Roll", f"{ctx.author.mention} đã roll ra **{value}** trong khoảng **1 đến {limit}** :>", discord.Color.gold()))


@bot.command(name="daily")
async def daily(ctx: commands.Context) -> None:
    wallet = get_user_economy(ctx.author.id)
    if wallet["last_daily"] == utc_today():
        await ctx.send("Hôm nay bạn đã nhận daily rồi. Mai quay lại nhé :vv")
        return
    wallet["last_daily"] = utc_today()
    wallet["balance"] += DAILY_REWARD
    wallet["earned_total"] += DAILY_REWARD
    wallet["daily_streak_claims"] += 1
    save_economy_data()
    await ctx.send(embed=make_embed("Điểm danh thành công", f"Bạn nhận được **{DAILY_REWARD} xu** hôm nay :vv\n**Số dư hiện tại:** {wallet['balance']} xu", discord.Color.green()))


@bot.command(name="challenge")
async def challenge(ctx: commands.Context) -> None:
    wallet = get_user_economy(ctx.author.id)
    active = get_active_challenge(ctx.author.id)
    if not active:
        selected = random.choice(CHALLENGE_TEMPLATES)
        wallet["challenge"] = selected["key"]
        wallet["challenge_progress"][selected["action"]] = 0
        save_economy_data()
        active = selected
    progress = wallet["challenge_progress"].get(active["action"], 0)
    embed = make_embed("Thử thách hiện tại", color=discord.Color.teal())
    embed.add_field(name="Tên thử thách", value=active["name"], inline=False)
    embed.add_field(name="Mục tiêu", value=f"{active['goal']} lần `{active['action']}`", inline=True)
    embed.add_field(name="Tiến độ", value=f"{progress}/{active['goal']}", inline=True)
    embed.add_field(name="Phần thưởng", value=f"{active['reward']} xu", inline=True)
    embed.set_footer(text="Dùng !claim để nhận thưởng khi hoàn thành")
    await ctx.send(embed=embed)


@bot.command(name="claim")
async def claim(ctx: commands.Context) -> None:
    wallet = get_user_economy(ctx.author.id)
    active = get_active_challenge(ctx.author.id)
    if not active:
        await ctx.send("Bạn chưa có thử thách nào. Dùng `!challenge` để nhận thử thách mới.")
        return
    progress = wallet["challenge_progress"].get(active["action"], 0)
    if progress < active["goal"]:
        await ctx.send(f"Bạn chưa hoàn thành thử thách này đâu :vv Tiến độ hiện tại: {progress}/{active['goal']}")
        return
    wallet["balance"] += active["reward"]
    wallet["earned_total"] += active["reward"]
    wallet["challenge"] = None
    wallet["challenge_progress"] = {}
    save_economy_data()
    await ctx.send(embed=make_embed("Nhận thưởng thành công", f"Bạn đã hoàn thành **{active['name']}** và nhận **{active['reward']} xu** =)))", discord.Color.green()))


@bot.command(name="shop")
async def shop(ctx: commands.Context) -> None:
    embed = make_embed("Cửa Hàng", "Mua dụng cụ để đi săn và đi câu :vv", discord.Color.gold())
    rods = [
        f"`!buy {key}` - {item['name']} | {item['price']} xu | cấp {item['power']}"
        for key, item in SHOP_ITEMS.items()
        if item["type"] == "rod"
    ]
    guns = [
        f"`!buy {key}` - {item['name']} | {item['price']} xu | cấp {item['power']}"
        for key, item in SHOP_ITEMS.items()
        if item["type"] == "gun"
    ]
    axes = [
        f"`!buy {key}` - {item['name']} | {item['price']} xu | cấp {item['power']}"
        for key, item in SHOP_ITEMS.items()
        if item["type"] == "axe"
    ]
    pickaxes = [
        f"`!buy {key}` - {item['name']} | {item['price']} xu | cấp {item['power']}"
        for key, item in SHOP_ITEMS.items()
        if item["type"] == "pickaxe"
    ]
    supports = [
        f"`!buy {key}` - {item['name']} | {item['price']} xu | h? tr? {int(item.get('bonus_percent', 0) * 100)}%"
        for key, item in SHOP_ITEMS.items()
        if item["type"] == "support"
    ]
    embed.add_field(name="Cần câu", value="\n".join(rods), inline=False)
    embed.add_field(name="Súng săn", value="\n".join(guns), inline=False)
    embed.add_field(name="Dao / chặt", value="\n".join(axes), inline=False)
    embed.add_field(name="Cuốc / khoáng sản", value="\n".join(pickaxes), inline=False)
    embed.add_field(name="�? h? tr?", value="\n".join(supports), inline=False)
    embed.add_field(name="Xem bảng giá trị", value="Dùng `!value` để xem giá các đồ vật trong game", inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="value")
async def value(ctx: commands.Context) -> None:
    embed = make_embed("Bảng giá trị đồ vật", color=discord.Color.gold())
    embed.add_field(name="Giá đồ trong shop", value=build_value_table_text(), inline=False)
    embed.add_field(
        name="Giá trị tài nguyên",
        value=(
            "Cá / mồi săn / gỗ / khoáng sản có giá trị tăng theo cấp đồ bạn dùng.\n"
            "Đồ càng mạnh thì phần thưởng càng cao."
        ),
        inline=False,
    )
    embed.add_field(
        name="May mắn đồ xịn",
        value="Đồ cấp cao, đặc biệt cần/súng top tier, có cơ hội rơi thêm vật phẩm hiếm và bonus xu.",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="buy")
async def buy(ctx: commands.Context, item_key: str) -> None:
    key = item_key.strip().lower()
    if key not in SHOP_ITEMS:
        await ctx.send("Món này không có trong shop. Dùng `!shop` để xem danh sách.")
        return
    wallet = get_user_economy(ctx.author.id)
    item = SHOP_ITEMS[key]
    if has_item(ctx.author.id, key):
        await ctx.send(f"Bạn đã có **{item['name']}** rồi :>")
        return
    if wallet["balance"] < item["price"]:
        await ctx.send(f"Bạn không đủ tiền mua **{item['name']}**. Cần {item['price']} xu.")
        return
    wallet["balance"] -= item["price"]
    wallet["lost_total"] += item["price"]
    add_item(ctx.author.id, key)
    save_economy_data()
    await ctx.send(embed=make_embed("Mua đồ thành công", f"Bạn đã mua **{item['name']}** với giá **{item['price']} xu**\n**Số dư còn lại:** {wallet['balance']} xu", discord.Color.green()))


@bot.command(name="fish")
async def fish(ctx: commands.Context) -> None:
    rod_key = best_item_by_type(ctx.author.id, "rod")
    if not rod_key:
        await ctx.send("Bạn cần mua **cần câu** trước. Dùng `!shop` rồi `!buy can_tre` nha :vv")
        return
    remaining = check_activity_cooldown(ctx.author.id, "fish", FISH_COOLDOWN_SECONDS)
    if remaining > 0:
        await ctx.send(f"Bạn vừa đi câu xong, đợi thêm **{remaining} giây** rồi câu tiếp nha :vv")
        return
    rod = SHOP_ITEMS[rod_key]
    fish_name, min_reward, max_reward = random.choice(FISH_TABLE[rod["power"]])
    reward = random.randint(min_reward, max_reward)
    lucky_loot = roll_lucky_loot("rod", rod["power"])
    lucky_text = ""
    support_key = best_support_item_for_activity(ctx.author.id, "fish")
    support_label = None
    if lucky_loot:
        lucky_name, lucky_reward = lucky_loot
        reward += lucky_reward
        lucky_text = f"\n**May mắn nổ:** nhặt thêm **{lucky_name}** (+{lucky_reward} xu) =)))"
    if support_key:
        support_item = SHOP_ITEMS[support_key]
        bonus = int(reward * support_item.get("bonus_percent", 0.0))
        reward += bonus
        support_remaining, support_max, support_broken = consume_tool_durability(ctx.author.id, support_key)
        support_label = f"{support_item['name']} +{bonus} xu | d� h?ng ;-;" if support_broken else f"{support_item['name']} +{bonus} xu | b?n {support_remaining}/{support_max}"
    wallet = get_user_economy(ctx.author.id)
    wallet["balance"] += reward
    wallet["earned_total"] += reward
    increment_challenge_progress(ctx.author.id, "fish")
    remaining_durability, max_durability, broken = consume_tool_durability(ctx.author.id, rod_key)
    save_economy_data()
    embed = make_embed(
        "Đi câu thành công",
        f"{ctx.author.mention} dùng **{rod['name']}** và câu được **{fish_name}**\nBán được **{reward} xu** :vv{lucky_text}\n**Số dư mới:** {wallet['balance']} xu",
        discord.Color.blue(),
    )
    if broken:
        embed.add_field(name="Độ bền", value=f"**{rod['name']}** đã gãy rồi ;-;", inline=False)
    else:
        embed.add_field(name="Độ bền", value=f"{remaining_durability}/{max_durability}", inline=False)
    if support_label:
        embed.add_field(name="H? tr?", value=support_label, inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="hunt")
async def hunt(ctx: commands.Context) -> None:
    gun_key = best_item_by_type(ctx.author.id, "gun")
    if not gun_key:
        await ctx.send("Bạn cần mua **súng săn** trước. Dùng `!shop` rồi `!buy sung_cu` nha =)))")
        return
    gun = SHOP_ITEMS[gun_key]
    prey_name, min_reward, max_reward = random.choice(HUNT_TABLE[gun["power"]])
    reward = random.randint(min_reward, max_reward)
    lucky_loot = roll_lucky_loot("gun", gun["power"])
    lucky_text = ""
    support_key = best_support_item_for_activity(ctx.author.id, "hunt")
    support_label = None
    if lucky_loot:
        lucky_name, lucky_reward = lucky_loot
        reward += lucky_reward
        lucky_text = f"\n**May mắn nổ:** nhặt thêm **{lucky_name}** (+{lucky_reward} xu) =)))"
    if support_key:
        support_item = SHOP_ITEMS[support_key]
        bonus = int(reward * support_item.get("bonus_percent", 0.0))
        reward += bonus
        support_remaining, support_max, support_broken = consume_tool_durability(ctx.author.id, support_key)
        support_label = f"{support_item['name']} +{bonus} xu | d� h?ng ;-;" if support_broken else f"{support_item['name']} +{bonus} xu | b?n {support_remaining}/{support_max}"
    wallet = get_user_economy(ctx.author.id)
    wallet["balance"] += reward
    wallet["earned_total"] += reward
    increment_challenge_progress(ctx.author.id, "hunt")
    remaining_durability, max_durability, broken = consume_tool_durability(ctx.author.id, gun_key)
    save_economy_data()
    embed = make_embed(
        "Đi săn thành công",
        f"{ctx.author.mention} dùng **{gun['name']}** và săn được **{prey_name}**\nBán được **{reward} xu** =))){lucky_text}\n**Số dư mới:** {wallet['balance']} xu",
        discord.Color.dark_green(),
    )
    if broken:
        embed.add_field(name="Độ bền", value=f"**{gun['name']}** đã hỏng rồi ;-;", inline=False)
    else:
        embed.add_field(name="Độ bền", value=f"{remaining_durability}/{max_durability}", inline=False)
    if support_label:
        embed.add_field(name="H? tr?", value=support_label, inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="chop")
async def chop(ctx: commands.Context) -> None:
    axe_key = best_item_by_type(ctx.author.id, "axe")
    if not axe_key:
        await ctx.send("Bạn cần mua **dao** trước. Dùng `!shop` rồi `!buy dao_cu` nha :vv")
        return
    axe = SHOP_ITEMS[axe_key]
    wood_name, min_reward, max_reward = random.choice(CHOP_TABLE[axe["power"]])
    reward = random.randint(min_reward, max_reward)
    lucky_loot = roll_lucky_loot("axe", axe["power"])
    lucky_text = ""
    support_key = best_support_item_for_activity(ctx.author.id, "chop")
    support_label = None
    if lucky_loot:
        lucky_name, lucky_reward = lucky_loot
        reward += lucky_reward
        lucky_text = f"\n**May mắn nổ:** chặt thêm **{lucky_name}** (+{lucky_reward} xu) =)))"
    if support_key:
        support_item = SHOP_ITEMS[support_key]
        bonus = int(reward * support_item.get("bonus_percent", 0.0))
        reward += bonus
        support_remaining, support_max, support_broken = consume_tool_durability(ctx.author.id, support_key)
        support_label = f"{support_item['name']} +{bonus} xu | d� h?ng ;-;" if support_broken else f"{support_item['name']} +{bonus} xu | b?n {support_remaining}/{support_max}"
    wallet = get_user_economy(ctx.author.id)
    wallet["balance"] += reward
    wallet["earned_total"] += reward
    increment_challenge_progress(ctx.author.id, "chop")
    remaining_durability, max_durability, broken = consume_tool_durability(ctx.author.id, axe_key)
    save_economy_data()
    embed = make_embed(
        "Chặt gỗ thành công",
        f"{ctx.author.mention} dùng **{axe['name']}** và chặt được **{wood_name}**\nBán được **{reward} xu** =))){lucky_text}\n**Số dư mới:** {wallet['balance']} xu",
        discord.Color.dark_teal(),
    )
    if broken:
        embed.add_field(name="Độ bền", value=f"**{axe['name']}** đã mẻ hỏng rồi ;-;", inline=False)
    else:
        embed.add_field(name="Độ bền", value=f"{remaining_durability}/{max_durability}", inline=False)
    if support_label:
        embed.add_field(name="H? tr?", value=support_label, inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="mine")
async def mine(ctx: commands.Context) -> None:
    pickaxe_key = best_item_by_type(ctx.author.id, "pickaxe")
    if not pickaxe_key:
        await ctx.send("Bạn cần mua **cuốc** trước. Dùng `!shop` rồi `!buy cuoc_cu` nha =)))")
        return
    remaining = check_activity_cooldown(ctx.author.id, "mine", MINE_COOLDOWN_SECONDS)
    if remaining > 0:
        await ctx.send(f"Bạn vừa đào xong, đợi thêm **{remaining} giây** rồi đào tiếp nha =))")
        return
    pickaxe = SHOP_ITEMS[pickaxe_key]
    ore_name, min_reward, max_reward = random.choice(MINE_TABLE[pickaxe["power"]])
    reward = random.randint(min_reward, max_reward)
    lucky_loot = roll_lucky_loot("pickaxe", pickaxe["power"])
    lucky_text = ""
    support_key = best_support_item_for_activity(ctx.author.id, "mine")
    support_label = None
    if lucky_loot:
        lucky_name, lucky_reward = lucky_loot
        reward += lucky_reward
        lucky_text = f"\n**May mắn nổ:** đào thêm **{lucky_name}** (+{lucky_reward} xu) =)))"
    if support_key:
        support_item = SHOP_ITEMS[support_key]
        bonus = int(reward * support_item.get("bonus_percent", 0.0))
        reward += bonus
        support_remaining, support_max, support_broken = consume_tool_durability(ctx.author.id, support_key)
        support_label = f"{support_item['name']} +{bonus} xu | d� h?ng ;-;" if support_broken else f"{support_item['name']} +{bonus} xu | b?n {support_remaining}/{support_max}"
    wallet = get_user_economy(ctx.author.id)
    wallet["balance"] += reward
    wallet["earned_total"] += reward
    increment_challenge_progress(ctx.author.id, "mine")
    remaining_durability, max_durability, broken = consume_tool_durability(ctx.author.id, pickaxe_key)
    save_economy_data()
    embed = make_embed(
        "Đào khoáng sản thành công",
        f"{ctx.author.mention} dùng **{pickaxe['name']}** và đào được **{ore_name}**\nBán được **{reward} xu** :vv{lucky_text}\n**Số dư mới:** {wallet['balance']} xu",
        discord.Color.dark_gold(),
    )
    if broken:
        embed.add_field(name="Độ bền", value=f"**{pickaxe['name']}** đã vỡ rồi ;-;", inline=False)
    else:
        embed.add_field(name="Độ bền", value=f"{remaining_durability}/{max_durability}", inline=False)
    if support_label:
        embed.add_field(name="H? tr?", value=support_label, inline=False)
    reminder = get_daily_reminder(ctx.author.id)
    if reminder:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="give")
async def give(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if member.bot:
        await ctx.send("Không chuyển tiền cho bot nha =))")
        return
    if member == ctx.author:
        await ctx.send("Tự đưa tiền cho mình thì kỳ quá :vv")
        return
    if amount <= 0:
        await ctx.send("Số tiền phải lớn hơn 0.")
        return
    sender_wallet = get_user_economy(ctx.author.id)
    if sender_wallet["balance"] < amount:
        await ctx.send(f"Bạn không đủ tiền. Số dư hiện tại: {sender_wallet['balance']} xu")
        return
    receiver_wallet = get_user_economy(member.id)
    sender_wallet["balance"] -= amount
    sender_wallet["lost_total"] += amount
    receiver_wallet["balance"] += amount
    receiver_wallet["earned_total"] += amount
    save_economy_data()
    await ctx.send(embed=make_embed("Chuyển tiền thành công", f"{ctx.author.mention} đã chuyển **{amount} xu** cho {member.mention}\n**Số dư còn lại:** {sender_wallet['balance']} xu", discord.Color.green()))


@bot.command(name="loan")
async def loan(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if member.bot:
        await ctx.send("Bot không vay tiền đâu =)))")
        return
    if member == ctx.author:
        await ctx.send("Tự cho mình vay nghe sai sai :>")
        return
    if amount <= 0:
        await ctx.send("Số tiền vay phải lớn hơn 0.")
        return
    if amount > MAX_LOAN_AMOUNT:
        await ctx.send(f"Lệnh `!loan` chỉ cho vay tối đa **{MAX_LOAN_AMOUNT} xu** mỗi lần thôi :vv")
        return
    lender_wallet = get_user_economy(ctx.author.id)
    if lender_wallet["balance"] < amount:
        await ctx.send(f"Bạn không đủ tiền để cho vay. Số dư hiện tại: {lender_wallet['balance']} xu")
        return
    borrower_wallet = get_user_economy(member.id)
    lender_wallet["balance"] -= amount
    lender_wallet["lost_total"] += amount
    borrower_wallet["balance"] += amount
    borrower_wallet["earned_total"] += amount
    add_debt(ctx.author.id, member.id, amount)
    save_economy_data()
    due_date = (discord.utils.utcnow().date() + timedelta(days=DEBT_DEFAULT_DAYS)).isoformat()
    await ctx.send(embed=make_embed("Cho vay thành công", f"{ctx.author.mention} đã cho {member.mention} vay **{amount} xu** =)))\n**Hạn trả:** {due_date}", discord.Color.gold()))


@bot.command(name="borrow")
async def borrow(ctx: commands.Context, amount: int) -> None:
    if amount <= 0:
        await ctx.send("Số tiền mượn phải lớn hơn 0.")
        return
    if amount > MAX_BOT_BORROW_AMOUNT:
        await ctx.send(f"Bạn chỉ được mượn tối đa **{MAX_BOT_BORROW_AMOUNT} xu** từ bot mỗi lần thôi :vv")
        return
    existing_bot_debt = [
        item for item in get_debts()
        if item["borrower_id"] == ctx.author.id and item["lender_id"] == BOT_LENDER_ID
    ]
    if existing_bot_debt:
        total_existing = sum(item["amount"] for item in existing_bot_debt)
        await ctx.send(
            f"Bạn đang có khoản vay từ bot rồi =)) Trả hết trước đã nha. Nợ hiện tại: **{total_existing} xu**"
        )
        return

    wallet = get_user_economy(ctx.author.id)
    wallet["balance"] += amount
    wallet["earned_total"] += amount
    add_debt(BOT_LENDER_ID, ctx.author.id, amount)
    save_economy_data()
    due_date = (discord.utils.utcnow().date() + timedelta(days=DEBT_DEFAULT_DAYS)).isoformat()
    await ctx.send(
        embed=make_embed(
            "Mượn tiền từ bot thành công",
            f"Bạn đã mượn **{amount} xu** từ bot :vv\n**Hạn trả:** {due_date}\n**Số dư mới:** {wallet['balance']} xu",
            discord.Color.gold(),
        )
    )


@bot.command(name="balance")
async def balance(ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
    target = member or ctx.author
    wallet = get_user_economy(target.id)
    owes, owed = get_user_debt_summary(target.id)
    embed = make_embed(f"Số dư của {target.display_name}", color=discord.Color.blurple())
    embed.add_field(name="Số dư hiện tại", value=f"**{wallet['balance']} xu**", inline=True)
    embed.add_field(name="Đang nợ", value=f"{owes} xu", inline=True)
    embed.add_field(name="Được nợ", value=f"{owed} xu", inline=True)
    embed.add_field(name="Tổng kiếm được", value=f"{wallet['earned_total']} xu", inline=True)
    embed.add_field(name="Tổng đã thua/chi", value=f"{wallet['lost_total']} xu", inline=True)
    embed.add_field(name="Dụng cụ", value=inventory_text(target.id), inline=False)
    if target.id == ctx.author.id:
        reminder = get_daily_reminder(ctx.author.id)
        if reminder:
            embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="profile")
async def profile(ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
    target = member or ctx.author
    wallet = get_user_economy(target.id)
    owes, owed = get_user_debt_summary(target.id)
    overdue_amount = sum(item["amount"] for item in overdue_debts() if item["borrower_id"] == target.id)
    embed = make_embed(f"Hồ sơ tiền của {target.display_name}", color=discord.Color.purple())
    embed.add_field(name="Số dư", value=f"{wallet['balance']} xu", inline=True)
    embed.add_field(name="Tổng kiếm được", value=f"{wallet['earned_total']} xu", inline=True)
    embed.add_field(name="Tổng đã thua/chi", value=f"{wallet['lost_total']} xu", inline=True)
    embed.add_field(name="Đã nhận daily", value=f"{wallet['daily_streak_claims']} lần", inline=True)
    embed.add_field(name="Đang nợ", value=f"{owes} xu", inline=True)
    embed.add_field(name="Quá hạn", value=f"{overdue_amount} xu", inline=True)
    embed.add_field(name="Dụng cụ", value=inventory_text(target.id), inline=False)
    if target.id == ctx.author.id:
        reminder = get_daily_reminder(ctx.author.id)
        if reminder:
            embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="debt")
async def debt(ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
    target = member or ctx.author
    debt_lines = []
    for debt_item in get_debts():
        if debt_item["borrower_id"] == target.id:
            debt_lines.append(f"Nợ {lender_name(debt_item['lender_id'])}: {debt_item['amount']} xu | hạn {debt_item['due_date']}")
        elif debt_item["lender_id"] == target.id:
            debt_lines.append(f"<@{debt_item['borrower_id']}> đang nợ: {debt_item['amount']} xu | hạn {debt_item['due_date']}")
    if not debt_lines:
        await ctx.send(embed=make_embed("Danh sách nợ", f"{target.display_name} hiện không có khoản nợ nào :vv", discord.Color.green()))
        return
    await ctx.send(embed=make_embed(f"Danh sách nợ của {target.display_name}", "\n".join(debt_lines[:20]), discord.Color.orange()))


@bot.command(name="repay")
async def repay(ctx: commands.Context, member: discord.Member, amount: int) -> None:
    if member.bot:
        await ctx.send("Không trả nợ cho bot nha =))")
        return
    if amount <= 0:
        await ctx.send("Số tiền trả phải lớn hơn 0.")
        return
    borrower_wallet = get_user_economy(ctx.author.id)
    if borrower_wallet["balance"] < amount:
        await ctx.send(f"Bạn không đủ tiền để trả. Số dư hiện tại: {borrower_wallet['balance']} xu")
        return
    paid_total, remaining_payment = repay_debt(ctx.author.id, member.id, amount)
    if paid_total <= 0:
        await ctx.send(f"Bạn hiện không nợ {member.mention} đồng nào cả :>")
        return
    lender_wallet = get_user_economy(member.id)
    borrower_wallet["balance"] -= paid_total
    borrower_wallet["lost_total"] += paid_total
    lender_wallet["balance"] += paid_total
    lender_wallet["earned_total"] += paid_total
    save_economy_data()
    message = f"{ctx.author.mention} đã trả **{paid_total} xu** cho {member.mention}."
    if remaining_payment > 0:
        message += f"\nCòn dư **{remaining_payment} xu** vì khoản nợ nhỏ hơn số bạn định trả."
    await ctx.send(embed=make_embed("Trả nợ thành công", message, discord.Color.green()))


@bot.command(name="repaybot")
async def repaybot(ctx: commands.Context, amount: int) -> None:
    if amount <= 0:
        await ctx.send("Số tiền trả phải lớn hơn 0.")
        return
    wallet = get_user_economy(ctx.author.id)
    if wallet["balance"] < amount:
        await ctx.send(f"Bạn không đủ tiền để trả bot. Số dư hiện tại: {wallet['balance']} xu")
        return

    paid_total, remaining_payment = repay_debt(ctx.author.id, BOT_LENDER_ID, amount)
    if paid_total <= 0:
        await ctx.send("Bạn hiện không nợ bot đồng nào cả :>")
        return

    wallet["balance"] -= paid_total
    wallet["lost_total"] += paid_total
    save_economy_data()
    message = f"Bạn đã trả **{paid_total} xu** cho bot."
    if remaining_payment > 0:
        message += f"\nCòn dư **{remaining_payment} xu** vì số nợ bot ít hơn số bạn định trả."
    await ctx.send(embed=make_embed("Trả nợ bot thành công", message, discord.Color.green()))


@bot.command(name="overdue")
async def overdue(ctx: commands.Context) -> None:
    items = overdue_debts()
    if not items:
        await ctx.send(embed=make_embed("Nợ quá hạn", "Hiện chưa có khoản nợ nào quá hạn :vv", discord.Color.green()))
        return
    lines = [
        f"<@{item['borrower_id']}> nợ {lender_name(item['lender_id'])} **{item['amount']} xu** | hạn {item['due_date']}"
        for item in items[:20]
    ]
    await ctx.send(embed=make_embed("Danh sách nợ quá hạn", "\n".join(lines), discord.Color.red()))


@bot.command(name="reminddebt")
async def reminddebt(ctx: commands.Context, member: discord.Member) -> None:
    debts = [item for item in get_debts() if item["borrower_id"] == member.id and item["lender_id"] == ctx.author.id]
    if not debts:
        await ctx.send(f"{member.mention} hiện không nợ bạn khoản nào cả :>")
        return
    today = utc_today()
    for item in debts:
        item["last_reminded"] = today
    save_economy_data()
    total = sum(item["amount"] for item in debts)
    await ctx.send(embed=make_embed("Nhắc nợ", f"{member.mention} bạn đang có khoản nợ **{total} xu**. Nhớ trả đúng hạn nha :vv", discord.Color.orange()))


@bot.command(name="clear", aliases=["purge", "trash"])
async def clear_messages(ctx: commands.Context, amount: Optional[int] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    if amount is None or amount < 1 or amount > 100:
        await ctx.send(f"Cách dùng: `{get_prefix()}clear <số_tin_từ_1_đến_100>`")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_messages:
        await ctx.send("Bot đang thiếu quyền **Manage Messages** nên chưa xóa chat được.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    notice = await ctx.send(
        embed=make_embed(
            "Dọn chat",
            f"Đã xóa **{max(len(deleted) - 1, 0)}** tin nhắn trong kênh này.",
            discord.Color.orange(),
        )
    )
    try:
        await notice.delete(delay=5)
    except (discord.Forbidden, discord.HTTPException):
        pass


def build_channel_style_help(prefix: str) -> discord.Embed:
    embed = make_embed(
        "Làm Đẹp Tên Kênh",
        "Bot tự chọn icon theo tên kênh: rules -> 📜, announcement -> 📢, mail -> ✉️, art -> 🎨, boost -> 💎...",
        discord.Color.fuchsia(),
    )
    embed.add_field(name="Style", value=", ".join(f"`{style}`" for style in CHANNEL_STYLE_TEMPLATES), inline=False)
    embed.add_field(
        name="Đổi 1 kênh",
        value=(
            f"`{prefix}stylechannel cute mail`\n"
            f"`{prefix}stylechannel #rules soft rules`\n"
            f"`{prefix}stylechannel #art star art`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Đổi toàn bộ",
        value=(
            f"`{prefix}stylechannels cute` - xem trước\n"
            f"`{prefix}stylechannels cute confirm` - đổi toàn bộ text channel"
        ),
        inline=False,
    )
    return embed


@bot.command(name="stylechannel", aliases=["lamdepkenh", "kenhdep", "decorchannel", "channelstyle"])
async def stylechannel(
    ctx: commands.Context,
    channel: Optional[discord.TextChannel] = None,
    style_or_name: Optional[str] = None,
    *,
    name: Optional[str] = None,
) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_channels:
        await ctx.send("Bạn cần quyền **Manage Channels** để đổi style tên kênh.")
        return

    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa đổi tên kênh được.")
        return

    target_channel = channel
    if target_channel is None:
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send(embed=build_channel_style_help(get_prefix()))
            return
        target_channel = ctx.channel

    if style_or_name is None:
        await ctx.send(embed=build_channel_style_help(get_prefix()))
        return

    detected_style = normalize_channel_style(style_or_name)
    if detected_style is not None and name:
        style = detected_style
        raw_name = name
    else:
        style = "cute"
        raw_name = " ".join(part for part in (style_or_name, name) if part)

    new_name = decorate_channel_name(style, raw_name)
    old_name = target_channel.name
    try:
        await target_channel.edit(name=new_name, reason=f"Đổi style tên kênh bởi {ctx.author}")
    except discord.Forbidden:
        await ctx.send("Bot không đủ quyền để đổi tên kênh này. Kiểm tra role bot và quyền **Manage Channels**.")
        return
    except discord.HTTPException as exc:
        await ctx.send(f"Discord không nhận tên kênh này: `{type(exc).__name__}`")
        return

    await ctx.send(embed=make_embed("Đã Làm Đẹp Kênh", f"`{old_name}` -> `{new_name}`", discord.Color.fuchsia()))


@bot.command(name="stylechannels", aliases=["lamdepallkenh", "decorchannels", "styleallchannels"])
async def stylechannels(ctx: commands.Context, style_name: Optional[str] = "cute", confirm: Optional[str] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Đổi toàn bộ kênh là lệnh lớn, chỉ **chủ server** mới dùng được.")
        return

    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa đổi tên kênh được.")
        return

    style = normalize_channel_style(style_name) or "cute"
    previews = [
        (channel.name, decorate_channel_name(style, channel.name))
        for channel in ctx.guild.text_channels
    ]
    if (confirm or "").strip().lower() != "confirm":
        lines = [f"`{old}` -> `{new}`" for old, new in previews[:15]]
        if len(previews) > 15:
            lines.append(f"...và {len(previews) - 15} kênh nữa")
        embed = make_embed(
            "Xem Trước Làm Đẹp Kênh",
            "\n".join(lines) or "Không có kênh text nào.",
            discord.Color.fuchsia(),
        )
        embed.set_footer(text=f"Nếu muốn đổi thật, dùng: {get_prefix()}stylechannels {style} confirm")
        await ctx.send(embed=embed)
        return

    renamed = 0
    skipped = 0
    for channel, (_, new_name) in zip(ctx.guild.text_channels, previews):
        if channel.name == new_name:
            skipped += 1
            continue
        try:
            await channel.edit(name=new_name, reason=f"Làm đẹp toàn bộ kênh bởi {ctx.author}")
            renamed += 1
            await asyncio.sleep(0.8)
        except (discord.Forbidden, discord.HTTPException):
            skipped += 1

    await ctx.send(
        embed=make_embed(
            "Đã Làm Đẹp Kênh",
            f"Đã đổi **{renamed}** kênh. Bỏ qua **{skipped}** kênh do đã đúng tên hoặc thiếu quyền.",
            discord.Color.fuchsia(),
        )
    )


@bot.command(name="serverinfo", aliases=["severinfo", "svinfo"])
async def serverinfo(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return

    guild = ctx.guild
    humans = sum(1 for member in guild.members if not member.bot)
    bots = sum(1 for member in guild.members if member.bot)
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    created_at = discord.utils.format_dt(guild.created_at, style="F")

    embed = make_embed("Thông Tin Server", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Tên", value=guild.name, inline=True)
    embed.add_field(name="ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="Chủ server", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Thành viên", value=f"{humans} người | {bots} bot | tổng {guild.member_count}", inline=False)
    embed.add_field(name="Kênh", value=f"{text_channels} text | {voice_channels} voice | {categories} category", inline=False)
    embed.add_field(name="Role", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Boost", value=f"Level {guild.premium_tier} | {guild.premium_subscription_count} boost", inline=True)
    embed.add_field(name="Tạo lúc", value=created_at, inline=False)
    await ctx.send(embed=embed)


@bot.command(name="sendrules", aliases=["rules15", "guirule", "ruleserver"])
async def sendrules(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_guild:
        await ctx.send("Bạn cần quyền **Manage Server** để gửi bảng luật.")
        return

    target_channel = channel or ctx.channel
    rules_text = "\n".join(f"**{index}.** {rule}" for index, rule in enumerate(SERVER_RULES_15, start=1))
    embed = make_embed(
        "Luật Server",
        rules_text,
        discord.Color.gold(),
    )
    embed.set_footer(text="Vui lòng đọc kỹ luật trước khi tham gia hoạt động trong server.")
    try:
        await target_channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send("Bot không gửi được bảng luật vào kênh đó.")
        return

    if target_channel.id != ctx.channel.id:
        await ctx.send(f"Đã gửi bảng luật vào {target_channel.mention}.")


@bot.command(name="announce", aliases=["thongbao", "announcement"])
async def announce(ctx: commands.Context, channel: discord.TextChannel, *, message: str) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_guild:
        await ctx.send("Bạn cần quyền **Manage Server** để gửi thông báo.")
        return

    embed = make_embed("Thông Báo", message[:4000], discord.Color.blurple())
    embed.set_footer(text=f"Gửi bởi {ctx.author.display_name}")
    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send("Bot không gửi được thông báo vào kênh đó.")
        return
    await ctx.send(f"Đã gửi thông báo vào {channel.mention}.")


@bot.command(name="slowmode", aliases=["slow", "chamchat"])
async def slowmode(ctx: commands.Context, seconds: Optional[int] = None, channel: Optional[discord.TextChannel] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_channels:
        await ctx.send("Bạn cần quyền **Manage Channels** để chỉnh slowmode.")
        return
    if seconds is None or seconds < 0 or seconds > 21600:
        await ctx.send(f"Cách dùng: `{get_prefix()}slowmode <0-21600_giây> [#kênh]`")
        return

    target_channel = channel or ctx.channel
    if not isinstance(target_channel, discord.TextChannel):
        await ctx.send("Slowmode chỉ dùng cho kênh text.")
        return
    try:
        await target_channel.edit(slowmode_delay=seconds, reason=f"Đổi slowmode bởi {ctx.author}")
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send("Bot không chỉnh được slowmode kênh đó.")
        return

    await ctx.send(embed=make_embed("Đã Chỉnh Slowmode", f"{target_channel.mention}: **{seconds} giây**", discord.Color.green()))


async def set_channel_lock(ctx: commands.Context, channel: Optional[discord.TextChannel], locked: bool) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.manage_channels:
        await ctx.send("Bạn cần quyền **Manage Channels** để khóa/mở kênh.")
        return

    target_channel = channel or ctx.channel
    if not isinstance(target_channel, discord.TextChannel):
        await ctx.send("Lệnh này chỉ dùng cho kênh text.")
        return

    overwrite = target_channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False if locked else None
    try:
        await target_channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{'Khóa' if locked else 'Mở'} kênh bởi {ctx.author}",
        )
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send("Bot không chỉnh được permission kênh đó.")
        return

    title = "Đã Khóa Kênh" if locked else "Đã Mở Kênh"
    description = f"{target_channel.mention} {'đã bị khóa chat cho @everyone.' if locked else 'đã mở chat lại cho @everyone.'}"
    await ctx.send(embed=make_embed(title, description, discord.Color.red() if locked else discord.Color.green()))


@bot.command(name="lockchannel", aliases=["lock", "khoakenh"])
async def lockchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_channel_lock(ctx, channel, True)


@bot.command(name="unlockchannel", aliases=["unlock", "mokenh"])
async def unlockchannel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    await set_channel_lock(ctx, channel, False)


@bot.command(name="setupserver", aliases=["beautifyserver", "lamdepserver"])
async def setupserver(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa tự setup được.")
        return
    if not me.guild_permissions.manage_roles:
        await ctx.send("Bot đang thiếu quyền **Manage Roles** nên chưa tự tạo role trong lúc setup được.")
        return

    progress_message = await ctx.send(
        embed=make_embed(
            "Đang Setup Server",
            "Bắt đầu dựng layout mới...\n`[1/6]` Chuẩn bị danh sách category, kênh và role",
            discord.Color.blurple(),
        )
    )
    applied_overwrites = 0
    created_roles: list[str] = []

    try:
        await progress_message.edit(
            embed=make_embed(
                "Đang Setup Server",
                "Đang dọn layout cũ do bot từng tạo...\n`[2/6]` Dọn category và kênh cũ",
                discord.Color.orange(),
            )
        )
        deleted_channels, deleted_categories = await cleanup_legacy_server_style(ctx.guild)

        await progress_message.edit(
            embed=make_embed(
                "Đang Setup Server",
                "Đang tạo category và kênh mới...\n`[3/6]` Dựng bố cục server",
                discord.Color.gold(),
            )
        )
        created_text_channels: dict[str, discord.TextChannel] = {}
        created_voice_names: list[str] = []
        created_categories: list[str] = []
        for block in SERVER_STYLE_LAYOUT:
            category = await get_or_create_category(ctx.guild, block["category"])
            created_categories.append(block["category"])
            for name in block["text"]:
                created_text_channels[name] = await get_or_create_text_channel(ctx.guild, category, name)
            for name in block["voice"]:
                await get_or_create_voice_channel(ctx.guild, category, name)
                created_voice_names.append(name)

        await progress_message.edit(
            embed=make_embed(
                "Đang Setup Server",
                "Đang tạo bộ role mẫu cho server...\n`[4/6]` Dựng role",
                discord.Color.fuchsia(),
            )
        )
        created_roles = await setup_server_roles(ctx.guild)

        await progress_message.edit(
            embed=make_embed(
                "Đang Setup Server",
                "Đang thả embed mẫu vào các kênh chính...\n`[5/6]` Hoàn thiện giao diện",
                discord.Color.green(),
            )
        )
        await send_server_style_embeds(created_text_channels)

        await progress_message.edit(
            embed=make_embed(
                "Đang Setup Server",
                "Đang khóa bot khác vào đúng kênh của chúng...\n`[6/6]` Áp permission cố định",
                discord.Color.teal(),
            )
        )
        applied_overwrites = await apply_external_bot_channel_rules(ctx.guild)
    except discord.Forbidden:
        await progress_message.edit(embed=make_embed("Setup Server Thất Bại", "Bot bị thiếu quyền khi tạo hoặc chỉnh kênh.", discord.Color.red()))
        return
    except discord.HTTPException as exc:
        await progress_message.edit(embed=make_embed("Setup Server Thất Bại", f"Discord trả lỗi khi setup server: `{type(exc).__name__}`", discord.Color.red()))
        return

    embed = make_embed(
        "Setup Server Xong",
        "Bot đã dựng lại bố cục server theo kiểu nhiều mục tách riêng giống mẫu bạn gửi.",
        discord.Color.green(),
    )
    embed.add_field(name="Category", value="\n".join(created_categories), inline=False)
    embed.add_field(name="Kênh text", value="\n".join(created_text_channels.keys())[:1024], inline=True)
    embed.add_field(name="Kênh voice", value="\n".join(created_voice_names) or "Không có", inline=True)
    embed.add_field(name="Role mẫu", value="\n".join(created_roles)[:1024] or "Không có", inline=False)
    embed.add_field(
        name="Đã dọn",
        value=f"{deleted_channels} kênh cũ, {deleted_categories} category cũ",
        inline=False,
    )
    embed.add_field(name="Permission bot", value=f"Đã áp **{applied_overwrites}** overwrite cho bot ngoài.", inline=False)
    await progress_message.edit(embed=embed)


@bot.command(name="setuproles", aliases=["createroles", "taorole", "taorolesever"])
async def setuproles(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_roles:
        await ctx.send("Bot đang thiếu quyền **Manage Roles** nên chưa tự tạo role được.")
        return

    created_roles = await setup_server_roles(ctx.guild)
    embed = make_embed(
        "Đã Tạo Role Mẫu",
        "Bot đã đồng bộ bộ role mẫu cho server.",
        discord.Color.green(),
    )
    embed.add_field(name="Role", value="\n".join(created_roles)[:1024], inline=False)
    await ctx.send(embed=embed)


def format_skg_member_nickname(member: discord.Member) -> str:
    base_name = member.display_name.strip()
    if base_name.startswith(MEMBER_NICKNAME_PREFIX):
        base_name = base_name[len(MEMBER_NICKNAME_PREFIX):].strip()
    elif base_name.startswith("SKG|"):
        base_name = base_name[len("SKG|"):].strip()
    if not base_name:
        base_name = member.name
    return f"{MEMBER_NICKNAME_PREFIX}{base_name}"[:MAX_DISCORD_NICKNAME_LENGTH].rstrip()


async def sync_server_bots(guild: discord.Guild) -> tuple[int, int, int]:
    renamed_bots = 0
    role_assigned = 0
    skipped = 0
    for member in guild.members:
        if not member.bot:
            continue
        if await assign_bot_role(member):
            role_assigned += 1
        if member.display_name == BOT_NICKNAME:
            skipped += 1
            continue
        try:
            await member.edit(nick=BOT_NICKNAME, reason="Đồng bộ tên bot theo lệnh changenamebot")
            renamed_bots += 1
        except (discord.Forbidden, discord.HTTPException):
            skipped += 1
    return renamed_bots, role_assigned, skipped


async def sync_server_members(guild: discord.Guild) -> tuple[int, int]:
    renamed_members = 0
    skipped = 0
    for member in guild.members:
        if member.bot:
            continue
        nickname = format_skg_member_nickname(member)
        if member.display_name == nickname:
            skipped += 1
            continue
        try:
            await member.edit(nick=nickname, reason="Đồng bộ tên member theo lệnh changenamemember")
            renamed_members += 1
        except (discord.Forbidden, discord.HTTPException):
            skipped += 1
    return renamed_members, skipped


def split_member_id_pages(lines: list[str], limit: int = 1000) -> list[str]:
    pages: list[str] = []
    current = ""
    for line in lines:
        addition = f"{line}\n"
        if len(current) + len(addition) > limit:
            pages.append(current.rstrip())
            current = addition
        else:
            current += addition
    if current.strip():
        pages.append(current.rstrip())
    return pages or ["Không có."]


@bot.command(name="changenamebot", aliases=["memberids", "listmemberid", "tagids", "listtags"])
async def memberids(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return

    me = ctx.guild.me
    renamed_bots = 0
    role_assigned = 0
    skipped = 0
    if me is not None and (me.guild_permissions.manage_nicknames or me.guild_permissions.manage_roles):
        renamed_bots, role_assigned, skipped = await sync_server_bots(ctx.guild)
    else:
        skipped = len([member for member in ctx.guild.members if member.bot])

    members = sorted(ctx.guild.members, key=lambda m: m.display_name.lower())
    if not members:
        await ctx.send("Server này chưa có member nào để liệt kê.")
        return

    bot_lines = [f"{member.mention} — `{member.id}`" for member in members if member.bot]
    user_lines = [f"{member.mention} — `{member.id}`" for member in members if not member.bot]
    sections = [
        ("ID Bot", split_member_id_pages(bot_lines)),
        ("ID Người", split_member_id_pages(user_lines)),
    ]
    total_pages = sum(len(pages) for _, pages in sections)

    page_index = 1
    for section_name, pages in sections:
        for page in pages:
            embed = make_embed(
                f"{section_name} ({page_index}/{total_pages})",
                page,
                discord.Color.blurple(),
            )
            if page_index == 1:
                embed.set_footer(
                    text=f"Đã đổi tên {renamed_bots} bot thành {BOT_NICKNAME}, gắn role {BOT_ROLE_NAME} cho {role_assigned} bot. Bỏ qua {skipped} bot do đã đúng tên hoặc thiếu quyền."
                )
            await ctx.send(embed=embed)
            page_index += 1


@bot.command(name="changenamemember", aliases=["doitenmember", "renamemember"])
async def changenamemember(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return

    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_nicknames:
        await ctx.send("Bot đang thiếu quyền **Manage Nicknames** nên chưa đổi tên member được.")
        return

    renamed_members, skipped = await sync_server_members(ctx.guild)
    users = sorted((member for member in ctx.guild.members if not member.bot), key=lambda m: m.display_name.lower())
    user_lines = [f"{member.mention} — `{member.id}`" for member in users]
    pages = split_member_id_pages(user_lines)

    for index, page in enumerate(pages, start=1):
        embed = make_embed(
            f"ID Người ({index}/{len(pages)})",
            page,
            discord.Color.blurple(),
        )
        if index == 1:
            embed.set_footer(
                text=f"Đã đổi tên {renamed_members} member thành dạng {MEMBER_NICKNAME_PREFIX}<tên>. Bỏ qua {skipped} do đã đúng tên hoặc thiếu quyền."
            )
        await ctx.send(embed=embed)


@bot.command(name="setupticketsv2", aliases=["ticketsv2setup", "ticketsetup", "setupticketbot"])
async def setupticketsv2(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None:
        await ctx.send("Bot chưa lấy được thông tin member của chính nó trong server.")
        return
    if not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa dựng khung Tickets v2 được.")
        return
    if not me.guild_permissions.manage_roles:
        await ctx.send("Bot đang thiếu quyền **Manage Roles** nên chưa tạo role Tickets v2 được.")
        return

    progress = await ctx.send(
        embed=make_embed(
            "Đang Setup Tickets v2",
            "Bot đang dựng role, category, kênh panel và permission cơ bản cho Tickets v2...",
            discord.Color.gold(),
        )
    )

    try:
        roles, category, panel_channel, log_channel, notify_channel = await setup_tickets_v2_structure(ctx.guild)
    except discord.Forbidden:
        await progress.edit(
            embed=make_embed(
                "Setup Tickets v2 Thất Bại",
                "Bot bị thiếu quyền khi tạo role hoặc chỉnh permission.",
                discord.Color.red(),
            )
        )
        return
    except discord.HTTPException as exc:
        await progress.edit(
            embed=make_embed(
                "Setup Tickets v2 Thất Bại",
                f"Discord trả lỗi khi setup Tickets v2: `{type(exc).__name__}`",
                discord.Color.red(),
            )
        )
        return

    panel_embed = make_embed(
        "Open a Ticket",
        "Bấm nút bên dưới để mở ticket trực tiếp bằng chính bot này. Không cần Tickets v2 nữa nếu bạn dùng panel này.",
        discord.Color.blurple(),
    )
    panel_embed.add_field(name="Panel channel", value=panel_channel.mention, inline=True)
    panel_embed.add_field(name="Ticket category", value=category.name, inline=True)
    panel_embed.add_field(name="Transcript / log", value=log_channel.mention, inline=True)
    panel_embed.add_field(name="Thread notify", value=notify_channel.mention, inline=True)
    panel_embed.add_field(name="Role support", value=roles["Tickets Support"].mention, inline=True)
    panel_embed.add_field(name="Role admin", value=roles["Tickets Admin"].mention, inline=True)
    await panel_channel.send(embed=panel_embed, view=NativeTicketPanelView())

    result = make_embed(
        "Setup Ticket Native Xong",
        "Bot của bạn đã dựng xong hệ ticket cơ bản và gửi panel mở ticket thật.",
        discord.Color.green(),
    )
    result.add_field(name="Role", value="\n".join(f"`{role.name}`" for role in roles.values()), inline=False)
    result.add_field(name="Panel", value=panel_channel.mention, inline=True)
    result.add_field(name="Logs", value=log_channel.mention, inline=True)
    result.add_field(name="Notify", value=notify_channel.mention, inline=True)
    result.add_field(
        name="Bạn còn phải làm",
        value=(
            f"1. Gán role support/admin cho người cần xử lý ticket\n"
            f"2. Cho member bấm nút trong {panel_channel.mention}\n"
            f"3. Test claim / close / delete ticket"
        ),
        inline=False,
    )
    await progress.edit(embed=result)


@bot.command(name="ticketpanel", aliases=["sendticketpanel", "openticketpanel"])
async def ticketpanel(ctx: commands.Context, channel: Optional[discord.TextChannel] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return

    target_channel = channel or ticket_panel_channel(ctx.guild) or ctx.channel
    support_role = get_ticket_support_role(ctx.guild)
    admin_role = get_ticket_admin_role(ctx.guild)
    embed = make_embed(
        "Open a Ticket",
        "Bấm nút bên dưới để mở ticket hỗ trợ với bot này.",
        discord.Color.blurple(),
    )
    if support_role:
        embed.add_field(name="Support", value=support_role.mention, inline=True)
    if admin_role:
        embed.add_field(name="Admin", value=admin_role.mention, inline=True)
    embed.add_field(name="Lưu ý", value="Mỗi người chỉ mở 1 ticket đang hoạt động tại một thời điểm.", inline=False)
    await target_channel.send(embed=embed, view=NativeTicketPanelView())
    if target_channel.id != ctx.channel.id:
        await ctx.send(f"Đã gửi panel ticket ở {target_channel.mention}")


@bot.command(name="cleansetupserver", aliases=["xoasetupserver", "resetlayoutserver"])
async def cleansetupserver(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa tự xóa layout được.")
        return

    progress_message = await ctx.send(
        embed=make_embed(
            "Đang Xóa Layout",
            "Bot đang dọn toàn bộ category/kênh mà `!setupserver` từng tạo...",
            discord.Color.orange(),
        )
    )
    deleted_channels, deleted_categories = await cleanup_all_server_style(ctx.guild)
    await progress_message.edit(
        embed=make_embed(
            "Đã Xóa Layout Setupserver",
            f"Đã xóa **{deleted_channels}** kênh và **{deleted_categories}** category thuộc layout của bot.",
            discord.Color.red(),
        )
    )


@bot.command(name="applybotrules", aliases=["syncbotchannels", "botruleapply"])
async def applybotrules(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa set permission cho bot khác được.")
        return

    progress_message = await ctx.send(
        embed=make_embed(
            "Đang Đồng Bộ Bot",
            "Bot đang áp permission cố định cho các bot khác theo đúng kênh của chúng...",
            discord.Color.teal(),
        )
    )
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild)
    await progress_message.edit(
        embed=make_embed(
            "Đồng Bộ Bot Xong",
            f"Đã áp **{applied_overwrites}** overwrite để khóa bot khác vào đúng kênh phù hợp.",
            discord.Color.green(),
        )
    )


@bot.command(name="autosetallbots", aliases=["autobotsetup", "scanallbots"])
async def autosetallbots(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa autoset bot khác được.")
        return

    progress_message = await ctx.send(
        embed=make_embed(
            "Đang Auto Set Bot",
            "Bot đang quét toàn bộ bot ngoài server và tự đoán khu phù hợp cho từng bot...",
            discord.Color.teal(),
        )
    )

    summary_lines: list[str] = []
    for member in await fetch_all_bot_members(ctx.guild):
        if bot.user and member.id == bot.user.id:
            continue
        guessed_zone = guess_bot_zone_from_name(member)
        bot_route_data[str(member.id)] = guessed_zone
        summary_lines.append(f"`{member.display_name}` -> **{guessed_zone}**")

    save_bot_route_data()
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild)

    embed = make_embed(
        "Auto Set Bot Xong",
        f"Đã áp **{applied_overwrites}** overwrite cho bot ngoài sau khi quét tự động.",
        discord.Color.green(),
    )
    if summary_lines:
        embed.add_field(name="Kết quả đoán khu", value="\n".join(summary_lines)[:1024], inline=False)
    else:
        embed.add_field(name="Kết quả", value="Không thấy bot ngoài nào để quét.", inline=False)
    embed.set_footer(text="Nếu bot nào bị đoán sai, dùng !setbotchannel hoặc !setbotzone để sửa tay.")
    await progress_message.edit(embed=embed)


@bot.command(name="setbotzone", aliases=["botzone", "setbotchannelzone"])
async def setbotzone(ctx: commands.Context, member: discord.Member, zone: str) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    if not member.bot:
        await ctx.send("Lệnh này chỉ gán khu cho bot thôi.")
        return
    normalized_zone = BOT_ZONE_ALIASES.get(zone.strip().lower(), zone.strip().lower())
    if normalized_zone not in BOT_ZONE_CHANNELS:
        zone_list = ", ".join(f"`{name}`" for name in BOT_ZONE_CHANNELS)
        await ctx.send(f"Zone không hợp lệ. Dùng một trong các zone sau: {zone_list}")
        return

    bot_route_data[str(member.id)] = normalized_zone
    save_bot_route_data()
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild, member)
    allowed_text = ", ".join(f"`{name}`" for name in sorted(BOT_ZONE_CHANNELS[normalized_zone]))
    await ctx.send(
        embed=make_embed(
            "Đã Gán Khu Cho Bot",
            f"Bot `{member.display_name}` đã được gán vào zone **{normalized_zone}**.\nĐược phép nói ở: {allowed_text}\nĐã áp **{applied_overwrites}** overwrite.",
            discord.Color.green(),
        )
    )


async def assign_bot_zone_shortcut(ctx: commands.Context, member: discord.Member, zone: str) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    if not member.bot:
        await ctx.send("Lệnh này chỉ gán khu cho bot thôi.")
        return
    normalized_zone = BOT_ZONE_ALIASES.get(zone.strip().lower(), zone.strip().lower())
    if normalized_zone not in BOT_ZONE_CHANNELS:
        zone_list = ", ".join(f"`{name}`" for name in BOT_ZONE_CHANNELS)
        await ctx.send(f"Zone không hợp lệ. Dùng một trong các zone sau: {zone_list}")
        return

    bot_route_data[str(member.id)] = normalized_zone
    save_bot_route_data()
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild, member)
    allowed_text = ", ".join(f"`{name}`" for name in sorted(BOT_ZONE_CHANNELS[normalized_zone]))
    await ctx.send(
        embed=make_embed(
            "Đã Gán Khu Cho Bot",
            f"Bot `{member.display_name}` đã được gán vào zone **{normalized_zone}**.\nĐược phép nói ở: {allowed_text}\nĐã áp **{applied_overwrites}** overwrite.",
            discord.Color.green(),
        )
    )


@bot.command(name="botchat")
async def botchat(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "bot")


@bot.command(name="botwelcome")
async def botwelcome(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "welcome")


@bot.command(name="botgiveaway")
async def botgiveaway(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "giveaway")


@bot.command(name="botticket")
async def botticket(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "ticket")


@bot.command(name="botboost")
async def botboost(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "boost")


@bot.command(name="botpartner")
async def botpartner(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "partner")


@bot.command(name="botvouch")
async def botvouch(ctx: commands.Context, member: discord.Member) -> None:
    await assign_bot_zone_shortcut(ctx, member, "vouch")


@bot.command(name="setbotchannel", aliases=["bindbotchannel", "ganbotkenh"])
async def setbotchannel(
    ctx: commands.Context,
    member: discord.Member,
    channel: discord.TextChannel,
) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    if not member.bot:
        await ctx.send("Lệnh này chỉ gán kênh cho bot thôi.")
        return

    bot_route_data[str(member.id)] = f"channel:{channel.name}"
    save_bot_route_data()
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild, member)
    await ctx.send(
        embed=make_embed(
            "Đã Gán Kênh Riêng Cho Bot",
            f"Bot `{member.display_name}` giờ chỉ được nói ở kênh {channel.mention}.\nĐã áp **{applied_overwrites}** overwrite.",
            discord.Color.green(),
        )
    )


@bot.command(name="clearbotzone", aliases=["removebotzone"])
async def clearbotzone(ctx: commands.Context, member: discord.Member) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return
    if not member.bot:
        await ctx.send("Lệnh này chỉ áp dụng cho bot thôi.")
        return

    removed = bot_route_data.pop(str(member.id), None)
    save_bot_route_data()
    applied_overwrites = await apply_external_bot_channel_rules(ctx.guild, member)
    if removed is None:
        await ctx.send("Bot này chưa có zone riêng từ trước.")
        return
    await ctx.send(
        embed=make_embed(
            "Đã Xóa Zone Riêng",
            f"Bot `{member.display_name}` đã bỏ zone riêng và quay về cách nhận diện tự động.\nĐã áp **{applied_overwrites}** overwrite mới.",
            discord.Color.orange(),
        )
    )


@bot.command(name="checkbotperms", aliases=["botperms", "auditbots"])
async def checkbotperms(ctx: commands.Context) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh server này chỉ **chủ server** mới dùng được.")
        return

    lines = await dangerous_bot_permission_report(ctx.guild)
    if not lines:
        await ctx.send(embed=make_embed("Kiểm Tra Quyền Bot", "Hiện chưa thấy bot ngoài nào có quyền nguy hiểm nổi bật :vv", discord.Color.green()))
        return

    embed = make_embed(
        "Kiểm Tra Quyền Bot",
        "Các bot dưới đây đang có quyền mạnh. Nếu muốn khóa chúng chặt hơn khi bot bạn offline, nên xem lại các quyền này, đặc biệt là **Administrator**.",
        discord.Color.orange(),
    )
    embed.add_field(name="Bot có quyền mạnh", value="\n".join(lines)[:1024], inline=False)
    embed.set_footer(text="Bot có Administrator thường sẽ khó bị khóa chặt chỉ bằng overwrite kênh.")
    await ctx.send(embed=embed)


@bot.command(name="wipeallserver", aliases=["xoaganhetserver", "xoatatcakenh"])
async def wipeallserver(ctx: commands.Context, confirm: Optional[str] = None) -> None:
    if ctx.guild is None:
        await ctx.send("Lệnh này chỉ dùng trong server thôi :vv")
        return
    if not is_server_owner(ctx.author):
        await ctx.send("Lệnh này chỉ **chủ server** mới dùng được.")
        return
    me = ctx.guild.me
    if me is None or not me.guild_permissions.manage_channels:
        await ctx.send("Bot đang thiếu quyền **Manage Channels** nên chưa xóa server được.")
        return
    if (confirm or "").strip().lower() != "confirm":
        await ctx.send(f"Dùng đúng cú pháp: `{get_prefix()}wipeallserver confirm`\nBot sẽ xóa gần như toàn bộ kênh/category và giữ lại đúng kênh hiện tại.")
        return

    progress_message = await ctx.send(
        embed=make_embed(
            "Đang Xóa Server",
            "Bot đang xóa gần như toàn bộ kênh/category của server...\nKênh hiện tại sẽ được giữ lại để báo kết quả.",
            discord.Color.dark_red(),
        )
    )
    deleted_channels, deleted_categories = await wipe_server_except_channel(ctx.guild, ctx.channel.id)
    await progress_message.edit(
        embed=make_embed(
            "Đã Xóa Gần Hết Server",
            f"Đã xóa **{deleted_channels}** kênh và **{deleted_categories}** category.\nKênh hiện tại được giữ lại để bạn tiếp tục setup lại server.",
            discord.Color.red(),
        )
    )


@bot.command(name="help")
async def help_command(ctx: commands.Context, category: Optional[str] = None) -> None:
    prefix = get_prefix()
    page = normalize_help_page(category)
    embed = build_help_page(prefix, page)
    if category is not None and page is None:
        embed.add_field(
            name="Không thấy nhóm đó",
            value=f"Dùng `{prefix}help` để xem các nhóm hợp lệ.",
            inline=False,
        )
    reminder = get_daily_reminder(ctx.author.id)
    if reminder and page is None:
        embed.add_field(name="Nhắc daily", value=reminder, inline=False)
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if hasattr(ctx.command, "on_error"):
        return

    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Không tìm thấy lệnh đó nha :vv Dùng `{get_prefix()}help` để xem hướng dẫn.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Bạn đang thiếu tham số rồi :> Dùng `{get_prefix()}help` để xem cách dùng.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(f"Tham số chưa đúng rồi =)) Dùng `{get_prefix()}help` để xem ví dụ.")
        return


async def main() -> None:
    global client
    try:
        client = get_openai_client()
    except RuntimeError:
        client = None
    await start_keep_alive_server()
    await bot.start(get_discord_token())


if __name__ == "__main__":
    asyncio.run(main())





