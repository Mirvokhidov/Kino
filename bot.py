"""
🎬 Telegram Kino Bot — v2.0 (Render Webhook uchun to'g'rilangan)
"""

import logging
import json
import os
import warnings
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.warnings import PTBUserWarning  # <--- Xato shu yerda to'g'rilandi

# Keraksiz sariq eslatmalarni (Warning) terminaldan yashirish
warnings.filterwarnings("ignore", category=PTBUserWarning)

# ============================================================
# ⚙️ SOZLAMALAR
# ============================================================
BOT_TOKEN       = "5610040264:AAHZmFcB8Yrkry2DPxPMI8-p2MvgcCYbsnI"
ADMIN_IDS       = [5061870104]
OPEN_CHANNEL    = "@YASHIRIN_EHTIROSLI_HIKOYALAR"
PRIVATE_CHANNEL = -1002220410072
BOT_USERNAME    = "muzik_mir_bot"
DATA_FILE       = "movies.json"

# Majburiy obuna: nechta kino so'rovdan keyin ko'rsatilsin
SUBSCRIBE_EVERY = 2
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation holatlari
(
    ADD_MOVIE_FILE,
    ADD_MOVIE_TITLE,
    ADD_MOVIE_DESC,
    ADD_MOVIE_POSTER,
    DELETE_MOVIE_ID,
    BROADCAST_TEXT,
    ADD_AD_CHANNEL,
    REMOVE_AD_CHANNEL,
) = range(8)

# ============================================================
# 📦 Ma'lumotlar bilan ishlash
# ============================================================
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "movies": {},
        "users": {},
        "next_id": 1,
        "ad_channels": [],
    }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def register_user(user_id: int):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"count": 0}
        save_data(data)

def increment_user_count(user_id: int) -> int:
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"count": 0}
    data["users"][uid]["count"] += 1
    count = data["users"][uid]["count"]
    save_data(data)
    return count

# ============================================================
# 📢 Majburiy obuna tekshiruvi
# ============================================================
async def check_subscriptions(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list:
    data = load_data()
    not_subscribed = []

    for ch in data["ad_channels"]:
        username = ch.get("username", "")
        if not username:
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=username, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)

    return not_subscribed

def build_subscribe_keyboard(not_subscribed: list, movie_id: str) -> InlineKeyboardMarkup:
    buttons = []
    for ch in not_subscribed:
        label = ch.get("title") or ch.get("username", "Kanal")
        url   = ch.get("invite") or f"https://t.me/{ch['username'].lstrip('@')}"
        buttons.append([InlineKeyboardButton(f"📢 {label}", url=url)])

    buttons.append([
        InlineKeyboardButton("✅ Obuna bo'ldim, tekshir", callback_data=f"check_sub_{movie_id}")
    ])
    return InlineKeyboardMarkup(buttons)

# ============================================================
# 🏠 /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id)

    args = context.args
    if args and args[0].startswith("movie_"):
        movie_id = args[0].replace("movie_", "")
        await handle_movie_request(update, context, movie_id)
        return

    if is_admin(user.id):
        await show_admin_panel(update, context)
    else:
        data = load_data()
        channels_text = ""
        if data["ad_channels"]:
            lines = [f"  • {ch.get('title', ch['username'])}" for ch in data["ad_channels"]]
            channels_text = "\n\n📢 *Kanallarimiz:*\n" + "\n".join(lines)

        await update.message.reply_text(
            f"👋 Salom, *{user.first_name}*!\n\n"
            f"🎬 Kino ko'rish uchun kanalimizga o'ting va kinoni tanlang.\n\n"
            f"📢 Kanal: {OPEN_CHANNEL}"
            f"{channels_text}",
            parse_mode="Markdown",
        )

# ============================================================
# 🎬 Kino so'rovi
# ============================================================
async def handle_movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id: str):
    user_id = update.effective_user.id
    count   = increment_user_count(user_id)

    if count % SUBSCRIBE_EVERY == 0:
        not_subscribed = await check_subscriptions(context, user_id)
        if not_subscribed:
            kb = build_subscribe_keyboard(not_subscribed, movie_id)
            await update.message.reply_text(
                "⚠️ *Kinoni olish uchun quyidagi kanallarga obuna bo'ling:*\n\n"
                "Obuna bo'lgandan so'ng \"✅ Obuna bo'ldim, tekshir\" tugmasini bosing.",
                parse_mode="Markdown",
                reply_markup=kb,
            )
            return

    await send_movie(update, context, movie_id)

async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, movie_id: str):
    data  = load_data()
    movie = data["movies"].get(str(movie_id))

    if not movie:
        await update.message.reply_text("❌ Kino topilmadi!")
        return

    try:
        await context.bot.copy_message(
            chat_id=update.effective_user.id,
            from_chat_id=PRIVATE_CHANNEL,
            message_id=movie["message_id"],
        )
        await update.message.reply_text("✅ Kino yuborildi! Yaxshi tomosha 🍿")
    except Exception as e:
        logger.error(f"Kino yuborishda xato: {e}")
        await update.message.reply_text("❌ Xato yuz berdi. Keyinroq urinib ko'ring.")

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    user_id  = query.from_user.id
    movie_id = query.data.replace("check_sub_", "")

    not_subscribed = await check_subscriptions(context, user_id)
    if not_subscribed:
        kb = build_subscribe_keyboard(not_subscribed, movie_id)
        await query.edit_message_text(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!\n\n"
            "Quyidagi kanallarga obuna bo'ling:",
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        await query.edit_message_text("✅ Tekshirildi! Kino yuborilmoqda...")
        data  = load_data()
        movie = data["movies"].get(str(movie_id))
        if not movie:
            await context.bot.send_message(user_id, "❌ Kino topilmadi!")
            return
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=PRIVATE_CHANNEL,
                message_id=movie["message_id"],
            )
            await context.bot.send_message(user_id, "✅ Kino yuborildi! Yaxshi tomosha 🍿")
        except Exception as e:
            logger.error(f"Kino yuborishda xato: {e}")
            await context.bot.send_message(user_id, "❌ Xato yuz berdi.")

# ============================================================
# 👨‍💼 Admin panel
# ============================================================
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie")],
        [InlineKeyboardButton("❌ Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="list_movies")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Reklama yuborish", callback_data="broadcast")],
        [InlineKeyboardButton("📡 Reklama kanallari", callback_data="ad_channels_menu")],
        [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings")],
    ]
    text = "👨‍💼 *Admin Panel*\n\nNimani qilmoqchisiz?"
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

async def ad_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = load_data()
    channels = data["ad_channels"]

    if channels:
        lines = [f"  {i+1}. *{ch.get('title', ch['username'])}* — `{ch['username']}`" for i, ch in enumerate(channels)]
        ch_text = "\n".join(lines)
    else:
        ch_text = "  _(hozircha yo'q)_"

    text = (
        f"📡 *Reklama kanallari* ({len(channels)} ta)\n\n"
        f"{ch_text}\n\n"
        f"ℹ️ Foydalanuvchi har *{SUBSCRIBE_EVERY}* ta kino so'rovda obunaga yo'naltiriladi."
    )
    keyboard = [
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_ad_channel")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="remove_ad_channel")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("check_sub_"):
        await check_sub_callback(update, context)
        return

    if not is_admin(user_id):
        await query.edit_message_text("❌ Sizda ruxsat yo'q!")
        return

    cb = query.data
    if cb == "admin_panel":
        await show_admin_panel(update, context)

    elif cb == "ad_channels_menu":
        await ad_channels_menu(update, context)

    elif cb == "add_ad_channel":
        await query.edit_message_text(
            "📡 Yangi reklama kanalini qo'shish.\n\n"
            "Quyidagi formatda yuboring:\n"
            "`@username | Kanal nomi | https://t.me/invite_link`\n\n"
            "Bekor qilish: /cancel",
            parse_mode="Markdown",
        )
        return ADD_AD_CHANNEL

    elif cb == "remove_ad_channel":
        data = load_data()
        channels = data["ad_channels"]
        if not channels:
            await query.edit_message_text(
                "📡 O'chirish uchun kanal yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="ad_channels_menu")]]),
            )
            return
        await query.edit_message_text(
            "➖ O'chirmoqchi bo'lgan kanal *raqamini* kiriting:\n\n"
            + "\n".join(f"{i+1}. {ch.get('title','?')} — `{ch['username']}`" for i, ch in enumerate(channels))
            + "\n\nBekor qilish: /cancel",
            parse_mode="Markdown",
        )
        return REMOVE_AD_CHANNEL

    elif cb == "add_movie":
        await query.edit_message_text(
            "🎬 Kinoni *yopiq kanalga* yuboring, so'ng xabarni botga *forward* qiling.\n\nBekor qilish: /cancel",
            parse_mode="Markdown",
        )
        return ADD_MOVIE_FILE

    elif cb == "delete_movie":
        await query.edit_message_text(
            "❌ O'chirmoqchi bo'lgan kino *ID* sini kiriting:\n\nBekor qilish: /cancel",
            parse_mode="Markdown",
        )
        return DELETE_MOVIE_ID

    elif cb == "list_movies":
        data = load_data()
        movies = data["movies"]
        if not movies:
            text = "📋 Hozircha kinolar yo'q."
        else:
            lines = ["📋 *Kinolar ro'yxati:*\n"]
            for mid, m in movies.items():
                lines.append(f"🎬 ID: `{mid}` — {m['title']}")
            text = "\n".join(lines)
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif cb == "stats":
        data = load_data()
        total_requests = sum(u.get("count", 0) for u in data["users"].values())
        text = (
            f"📊 *Statistika*\n\n"
            f"👥 Foydalanuvchilar: *{len(data['users'])}*\n"
            f"🎬 Kinolar soni: *{len(data['movies'])}*\n"
            f"📥 Jami so'rovlar: *{total_requests}*\n"
            f"📡 Reklama kanallari: *{len(data['ad_channels'])}*"
        )
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif cb == "broadcast":
        await query.edit_message_text(
            "📢 Yubormoqchi bo'lgan *reklama matnini* kiriting:\n\nBekor qilish: /cancel",
            parse_mode="Markdown",
        )
        return BROADCAST_TEXT

    elif cb == "settings":
        text = (
            f"⚙️ *Sozlamalar*\n\n"
            f"🤖 Bot: @{BOT_USERNAME}\n"
            f"📢 Ochiq kanal: {OPEN_CHANNEL}\n"
            f"🔒 Yopiq kanal ID: `{PRIVATE_CHANNEL}`\n"
            f"👨‍💼 Admin(lar): {', '.join(str(a) for a in ADMIN_IDS)}\n"
            f"🔄 Obuna har: *{SUBSCRIBE_EVERY}* so'rovda"
        )
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ============================================================
# Conversation Handler Functions
# ============================================================
async def add_movie_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.forward_from_chat and msg.forward_from_chat.id == PRIVATE_CHANNEL:
        context.user_data["movie_msg_id"] = msg.forward_from_message_id
    elif msg.forward_from_message_id:
        context.user_data["movie_msg_id"] = msg.forward_from_message_id
    else:
        context.user_data["movie_msg_id"] = msg.message_id
    await msg.reply_text("✅ Xabar qabul qilindi!\n\n📝 Kino *nomini* kiriting:", parse_mode="Markdown")
    return ADD_MOVIE_TITLE

async def add_movie_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["movie_title"] = update.message.text
    await update.message.reply_text("📖 Kino *tavsifini* kiriting:", parse_mode="Markdown")
    return ADD_MOVIE_DESC

async def add_movie_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["movie_desc"] = update.message.text
    await update.message.reply_text("🖼 Kino *posterini* (rasmini) yuboring:", parse_mode="Markdown")
    return ADD_MOVIE_POSTER

async def add_movie_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.photo:
        await msg.reply_text("❌ Iltimos, rasm yuboring!")
        return ADD_MOVIE_POSTER

    data     = load_data()
    movie_id = str(data["next_id"])
    data["next_id"] += 1

    title  = context.user_data["movie_title"]
    desc   = context.user_data["movie_desc"]
    msg_id = context.user_data["movie_msg_id"]
    photo  = msg.photo[-1].file_id

    data["movies"][movie_id] = {
        "title": title, "description": desc,
        "message_id": msg_id, "poster": photo,
    }
    save_data(data)

    caption = f"🎬 *{title}*\n\n📖 {desc}\n\n🎟 Kod: `{movie_id}`"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Kinoni ko'rish", url=f"https://t.me/{BOT_USERNAME}?start=movie_{movie_id}")]])

    try:
        await context.bot.send_photo(chat_id=OPEN_CHANNEL, photo=photo, caption=caption, reply_markup=kb, parse_mode="Markdown")
        ch_status = f"✅ Post {OPEN_CHANNEL} kanaliga yuborildi!"
    except Exception as e:
        logger.error(f"Kanal post xatosi: {e}")
        ch_status = f"⚠️ Kanalga yuborishda xato: {e}"

    await msg.reply_text(
        f"✅ *Kino saqlandi!*\n\n🆔 ID: `{movie_id}`\n🎬 Nom: {title}\n🔗 `https://t.me/{BOT_USERNAME}?start=movie_{movie_id}`\n\n{ch_status}",
        parse_mode="Markdown",
    )
    kb2 = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    await msg.reply_text("Admin panelga qaytish:", reply_markup=InlineKeyboardMarkup(kb2))
    context.user_data.clear()
    return ConversationHandler.END

async def delete_movie_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    movie_id = update.message.text.strip()
    data = load_data()
    if movie_id in data["movies"]:
        title = data["movies"][movie_id]["title"]
        del data["movies"][movie_id]
        save_data(data)
        await update.message.reply_text(f"✅ *{title}* (ID: {movie_id}) o'chirildi!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ ID: `{movie_id}` topilmadi.", parse_mode="Markdown")

    kb = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    await update.message.reply_text("Admin panelga qaytish:", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def add_ad_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text.strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("❌ Noto'g'ri format.\nQayta kiriting yoki /cancel")
        return ADD_AD_CHANNEL

    username = parts[0] if parts[0].startswith("@") else "@" + parts[0]
    title    = parts[1]
    invite   = parts[2] if len(parts) >= 3 else f"https://t.me/{username.lstrip('@')}"

    data = load_data()
    existing = [ch["username"] for ch in data["ad_channels"]]
    if username in existing:
        await update.message.reply_text(f"⚠️ `{username}` allaqachon ro'yxatda!", parse_mode="Markdown")
    else:
        data["ad_channels"].append({"username": username, "title": title, "invite": invite})
        save_data(data)
        await update.message.reply_text(f"✅ *{title}* (`{username}`) qo'shildi!\nJami reklama kanallari: *{len(data['ad_channels'])}* ta", parse_mode="Markdown")

    kb = [[InlineKeyboardButton("🔙 Kanallar menyusi", callback_data="ad_channels_menu")]]
    await update.message.reply_text("Menyuga qaytish:", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def remove_ad_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    data = load_data()
    channels = data["ad_channels"]
    try:
        idx = int(text) - 1
        if idx < 0 or idx >= len(channels):
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"❌ Noto'g'ri raqam. 1 dan {len(channels)} gacha kiriting.\nQayta kiriting yoki /cancel")
        return REMOVE_AD_CHANNEL

    removed = channels.pop(idx)
    save_data(data)
    await update.message.reply_text(f"✅ *{removed.get('title', removed['username'])}* o'chirildi!\nQolgan kanallar: *{len(channels)}* ta", parse_mode="Markdown")
    kb = [[InlineKeyboardButton("🔙 Kanallar menyusi", callback_data="ad_channels_menu")]]
    await update.message.reply_text("Menyuga qaytish:", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text  = update.message.text
    data  = load_data()
    users = list(data["users"].keys())
    sent = failed = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"📢 Reklama yuborildi!\n✅ Muvaffaqiyatli: {sent}\n❌ Xato: {failed}")
    kb = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    await update.message.reply_text("Admin panelga qaytish:", reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")
    if is_admin(update.effective_user.id):
        await show_admin_panel(update, context)
    return ConversationHandler.END

# ============================================================
# 🚀 Botni ishga tushirish (Webhook va Polling)
# ============================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^add_movie$")],
        states={
            ADD_MOVIE_FILE:  [MessageHandler(filters.ALL & ~filters.COMMAND, add_movie_file)],
            ADD_MOVIE_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_title)],
            ADD_MOVIE_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_desc)],
            ADD_MOVIE_POSTER:[MessageHandler(filters.PHOTO, add_movie_poster)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^delete_movie$")],
        states={DELETE_MOVIE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_movie_id)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^broadcast$")],
        states={BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_text)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^add_ad_channel$")],
        states={ADD_AD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ad_channel_handler)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^remove_ad_channel$")],
        states={REMOVE_AD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_ad_channel_handler)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    PORT = int(os.environ.get("PORT", 10000))
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if RENDER_URL:
        logger.info(f"🌐 Webhook rejimi ishga tushdi: {RENDER_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{RENDER_URL}/{BOT_TOKEN}"
        )
    else:
        logger.info("🎬 Kino bot Polling rejimida ishga tushdi!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

