import re
import time
import requests
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

from config import (
    BOT_TOKEN, BOT_NAME, OWNER_ID,
    TIKTOK_API, YOUTUBE_API, PINTEREST_API, INSTAGRAM_API, API_KEY,
    LIMITS,
)
from storage import (
    load_data, save_data, get_user, is_admin, is_owner, is_premium,
    premium_status_text, check_and_use, grant_premium, add_admin, all_user_ids,
)
from ui import (
    b, i, code, quote, branded, header,
    primary_button, danger_button, success_button, neutral_button, url_button,
    menu_button, with_menu_button, limit_reached_text, loading_text,
)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
data = load_data()

API_HEADERS = {"X-API-Key": API_KEY}
pending_broadcast = {}          # admin_id -> broadcast text waiting for confirm
search_cache = {}                # chat_id -> {video_id: url}   (youtube inline results)


def api_post(base, path, payload, timeout=90):
    return requests.post(f"{base}{path}", json=payload, headers=API_HEADERS, timeout=timeout)


def send_loading(message, action):
    return bot.reply_to(message, loading_text(action))


def finish(loading_msg, text, markup=None):
    if markup is None:
        markup = with_menu_button()
    try:
        bot.edit_message_text(text, chat_id=loading_msg.chat.id, message_id=loading_msg.message_id, reply_markup=markup)
    except Exception:
        try:
            bot.send_message(loading_msg.chat.id, text, reply_markup=markup)
        except Exception:
            bot.send_message(loading_msg.chat.id, text)


def register(message):
    return get_user(data, message.from_user.id, message.from_user.username, message.from_user.first_name)


def parse_query_and_count(text, default=10, max_count=100):
    parts = text.split(maxsplit=1)
    body = parts[1] if len(parts) > 1 else ""
    tokens = body.split()
    if tokens and tokens[-1].isdigit():
        count = min(int(tokens[-1]), max_count)
        query = " ".join(tokens[:-1])
    else:
        count = default
        query = body
    return query.strip(), count


def fmt_num(n):
    return f"{n:,}" if isinstance(n, (int, float)) else "N/A"


# ══════════════════════════════════════════════════════════════ /start & /status

CATEGORY_INFO = {
    "tiktok": {
        "title": "🎵 TikTok",
        "features": [
            ("ttdl", "⬇️ Download Video"),
        ],
    },
    "youtube": {
        "title": "▶️ YouTube",
        "features": [
            ("ytdl", "⬇️ Download Video"),
            ("ytaudio", "🎧 Download Audio"),
            ("ytsearch", "🔍 Search Videos"),
            ("ytshort", "🔍 Search Shorts"),
        ],
    },
    "instagram": {
        "title": "📷 Instagram",
        "features": [
            ("instadl", "⬇️ Download Post/Reel"),
            ("instasearch", "🔍 Search Reels"),
            ("instapsearch", "🔍 Search Photos"),
        ],
    },
    "pinterest": {
        "title": "📌 Pinterest",
        "features": [
            ("pindl", "⬇️ Download Pin"),
            ("pinsearch", "🔍 Search Images"),
            ("pinvsearch", "🔍 Search Videos"),
        ],
    },
}

FEATURE_PROMPTS = {
    "ttdl": "🔗 Send the TikTok link.",
    "ytdl": "🔗 Send the YouTube link.",
    "ytaudio": "🔗🎵 Send a YouTube link, or a song / surah name.",
    "ytsearch": f"🔍 Send the video name to search. Add a number for count, e.g. {code('cats 15')}",
    "ytshort": f"🔍 Send the name to search shorts for. Add a number for count, e.g. {code('cats 15')}",
    "instadl": "🔗 Send the Instagram post/reel link.",
    "instasearch": f"🔍 Send a query. Add a number for count, e.g. {code('cats 15')}",
    "instapsearch": f"🔍 Send a query. Add a number for count, e.g. {code('cats 15')}",
    "pindl": "🔗 Send the Pinterest pin link.",
    "pinsearch": f"🔍 Send a query. Add a number for count, e.g. {code('mahiru 20')}",
    "pinvsearch": f"🔍 Send a query. Add a number for count, e.g. {code('mahiru 20')}",
}


def main_menu_text(first_name, is_admin_user):
    greeting = f"👋 {b('Welcome back, ' + (first_name or 'friend') + '!')}" if first_name else b("Welcome!")
    admin_note = "\n" + quote("🛠 " + b("You're an admin") + " — tap Admin Panel below.") if is_admin_user else ""
    return branded(
        header(BOT_NAME)
        + greeting + "\n\n"
        + quote(
            "🎵 TikTok · ▶️ YouTube · 📌 Pinterest · 📷 Instagram\n"
            "All-in-one downloader, fully free with daily limits."
        )
        + "\n\n" + b("👇 Pick a category to see its commands:") + admin_note
    )


def main_menu_markup(is_admin_user):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        primary_button("TikTok", "menu:tiktok"),
        primary_button("YouTube", "menu:youtube"),
    )
    markup.row(
        primary_button("Instagram", "menu:instagram"),
        primary_button("Pinterest", "menu:pinterest"),
    )
    markup.row(success_button("My Status", "menu:status"))
    if is_admin_user:
        markup.row(danger_button("Admin Panel", "menu:admin"))
    return markup


@bot.message_handler(commands=["start"])
def start(message):
    register(message)
    admin_user = is_admin(data, message.from_user.id)
    bot.reply_to(
        message,
        main_menu_text(message.from_user.first_name, admin_user),
        reply_markup=main_menu_markup(admin_user),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("menu:"))
def on_menu_action(call):
    register(call)
    action = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    admin_user = is_admin(data, call.from_user.id)

    if action == "home":
        try:
            bot.edit_message_text(
                main_menu_text(call.from_user.first_name, admin_user),
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                reply_markup=main_menu_markup(admin_user),
            )
        except Exception:
            bot.send_message(call.message.chat.id, main_menu_text(call.from_user.first_name, admin_user), reply_markup=main_menu_markup(admin_user))
        return

    if action == "status":
        user = get_user(data, call.from_user.id, call.from_user.username, call.from_user.first_name)
        bot.send_message(call.message.chat.id, status_text(user), reply_markup=with_menu_button())
        return

    if action == "admin":
        if not admin_user:
            bot.answer_callback_query(call.id, "🚫 Admins only.")
            return
        bot.send_message(call.message.chat.id, branded(header("Admin Panel")), reply_markup=admin_panel_markup())
        return

    cat = CATEGORY_INFO.get(action)
    if not cat:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for cmd, label in cat["features"]:
        markup.row(primary_button(label, f"feat:{cmd}"))
    markup.row(menu_button())
    text = branded(header(cat["title"]) + quote("👇 " + b("Tap a feature") + " and I'll ask you what I need."))
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("feat:"))
def on_feature_action(call):
    register(call)
    cmd = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    prompt = FEATURE_PROMPTS.get(cmd, "Send the required input.")
    msg = bot.send_message(call.message.chat.id, branded(quote(prompt)))
    bot.register_next_step_handler(msg, _handle_feature_input, cmd)


def _handle_feature_input(message, cmd):
    handler = FEATURE_HANDLERS.get(cmd)
    if not handler:
        return
    # Reuse the exact same /command handlers (parsing, limits, API calls)
    # by faking the command prefix onto the plain reply text — no logic
    # is duplicated between the text-command and button-tap flows.
    message.text = f"/{cmd} {message.text or ''}".strip()
    handler(message)


def status_text(user):
    lines = [header("Your Status"), quote(premium_status_text(user))]
    if not is_premium(user):
        lines.append("\n" + b("📊 Today's usage:"))
        for feature, limit in LIMITS.items():
            used = user["usage"].get(feature, 0)
            label = feature.replace("_", " ").title()
            lines.append(f"• {label}: {code(f'{used}/{limit}')}")
    return branded("\n".join(lines))


@bot.message_handler(commands=["status"])
def status(message):
    user = register(message)
    bot.reply_to(message, status_text(user), reply_markup=with_menu_button())


# ══════════════════════════════════════════════════════════════ TikTok

@bot.message_handler(commands=["ttdl"])
def tiktok_download(message):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: <code>/ttdl &lt;tiktok link&gt;</code>"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, "tiktok_download")
    if not allowed:
        bot.reply_to(message, limit_reached_text("TikTok download", used, limit))
        return

    url = parts[1].strip()
    loading = send_loading(message, "Fetching TikTok video")

    try:
        info_res = api_post(TIKTOK_API, "/api/info", {"url": url})
        info = info_res.json() if info_res.status_code == 200 else {}
        file_res = api_post(TIKTOK_API, "/api/download", {"url": url}, timeout=180)
    except Exception as e:
        finish(loading, branded(f"⚠️ Error: {e}"))
        return

    if file_res.status_code != 200:
        finish(loading, branded(f"⚠️ Download failed: {file_res.text[:200]}"))
        return

    finish(loading, branded("✅ Sending video..."))
    caption = branded(b(info.get("title") or "TikTok Video") + f"\n👤 {info.get('author') or ''}")
    bot.send_video(message.chat.id, file_res.content, caption=caption)


# ══════════════════════════════════════════════════════════════ YouTube

def yt_caption(info):
    lines = [b(info.get("title") or ""), f"👤 {info.get('channel') or ''}"]
    if info.get("view_count") is not None:
        lines.append(f"👁 {fmt_num(info['view_count'])} views")
    if info.get("like_count") is not None:
        lines.append(f"❤️ {fmt_num(info['like_count'])} likes")
    if info.get("subscriber_count") is not None:
        lines.append(f"📢 {fmt_num(info['subscriber_count'])} subscribers")
    if info.get("upload_date"):
        d = info["upload_date"]
        lines.append(f"📅 {d[:4]}-{d[4:6]}-{d[6:]}")
    return branded("\n".join(lines))


@bot.message_handler(commands=["ytdl"])
def youtube_download(message):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: <code>/ytdl &lt;youtube link&gt;</code>"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, "youtube_download")
    if not allowed:
        bot.reply_to(message, limit_reached_text("YouTube download", used, limit))
        return

    send_youtube_video(message.chat.id, parts[1].strip(), send_loading(message, "Fetching YouTube video"))


def send_youtube_video(chat_id, url, loading=None):
    try:
        info = api_post(YOUTUBE_API, "/api/info", {"url": url}).json()
    except Exception:
        info = {}
    try:
        file_res = api_post(YOUTUBE_API, "/api/download", {"url": url}, timeout=240)
    except Exception as e:
        if loading:
            finish(loading, branded(f"⚠️ Error: {e}"))
        return
    if file_res.status_code != 200:
        if loading:
            finish(loading, branded(f"⚠️ Download failed: {file_res.text[:200]}"))
        return
    if loading:
        finish(loading, branded("✅ Sending video..."))
    bot.send_video(chat_id, file_res.content, caption=yt_caption(info))


@bot.message_handler(commands=["ytaudio"])
def youtube_audio_cmd(message):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: <code>/ytaudio &lt;link or song name&gt;</code>"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, "youtube_audio")
    if not allowed:
        bot.reply_to(message, limit_reached_text("YouTube audio", used, limit))
        return

    query = parts[1].strip()
    loading = send_loading(message, "Fetching audio")

    url = query
    if not query.startswith(("http://", "https://")):
        try:
            res = api_post(YOUTUBE_API, "/api/search", {"query": query, "type": "video", "limit": 1})
            results = res.json().get("results", [])
            if not results:
                finish(loading, branded("❌ No results found."))
                return
            url = results[0]["url"]
        except Exception as e:
            finish(loading, branded(f"⚠️ API error: {e}"))
            return

    try:
        info = api_post(YOUTUBE_API, "/api/info", {"url": url}).json()
    except Exception:
        info = {}
    try:
        file_res = api_post(YOUTUBE_API, "/api/audio", {"url": url}, timeout=240)
    except Exception as e:
        finish(loading, branded(f"⚠️ Error: {e}"))
        return
    if file_res.status_code != 200:
        finish(loading, branded(f"⚠️ Download failed: {file_res.text[:200]}"))
        return

    finish(loading, branded("✅ Sending audio..."))
    bot.send_audio(
        message.chat.id, file_res.content, caption=yt_caption(info),
        title=info.get("title"), performer=info.get("channel"),
    )


def youtube_search_cmd(message, search_type, feature, label):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded(f"❌ Format: /{label} &lt;name&gt;"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, feature)
    if not allowed:
        bot.reply_to(message, limit_reached_text(label, used, limit))
        return

    query = parts[1].strip()
    loading = send_loading(message, "Searching YouTube")

    try:
        res = api_post(YOUTUBE_API, "/api/search", {"query": query, "type": search_type, "limit": 5})
    except Exception as e:
        finish(loading, branded(f"⚠️ API error: {e}"))
        return

    if res.status_code != 200:
        finish(loading, branded(f"⚠️ Failed: {res.text[:200]}"))
        return

    results = res.json().get("results", [])
    if not results:
        finish(loading, branded("❌ No results found."))
        return

    search_cache[message.chat.id] = {r["video_id"]: r["url"] for r in results}
    markup = types.InlineKeyboardMarkup()
    for r in results:
        title = (r["title"] or "Untitled")[:60]
        markup.add(types.InlineKeyboardButton(f"▶️ {title}", callback_data=f"yt:{r['video_id']}"))

    finish(loading, branded(f"🔎 Results for: {b(query)}"))
    bot.send_message(message.chat.id, "Pick one:", reply_markup=markup)


@bot.message_handler(commands=["ytsearch"])
def ytsearch_cmd(message):
    youtube_search_cmd(message, "video", "youtube_search", "ytsearch")


@bot.message_handler(commands=["ytshort"])
def ytshort_cmd(message):
    youtube_search_cmd(message, "short", "youtube_search", "ytshort")


@bot.callback_query_handler(func=lambda call: call.data.startswith("yt:"))
def on_yt_pick(call):
    video_id = call.data.split(":", 1)[1]
    url = search_cache.get(call.message.chat.id, {}).get(video_id)
    if not url:
        bot.answer_callback_query(call.id, "⚠️ Expired, search again.")
        return

    allowed, used, limit = check_and_use(data, call.from_user.id, "youtube_download")
    if not allowed:
        bot.answer_callback_query(call.id, "🚫 Daily limit reached.")
        bot.send_message(call.message.chat.id, limit_reached_text("YouTube download", used, limit))
        return

    bot.answer_callback_query(call.id, "⏳ Downloading...")
    send_youtube_video(call.message.chat.id, url)


# ══════════════════════════════════════════════════════════════ Pinterest

@bot.message_handler(commands=["pindl"])
def pinterest_download(message):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: <code>/pindl &lt;pin link&gt;</code>"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, "pinterest_download")
    if not allowed:
        bot.reply_to(message, limit_reached_text("Pinterest download", used, limit))
        return

    url = parts[1].strip()
    loading = send_loading(message, "Fetching pin")

    try:
        file_res = api_post(PINTEREST_API, "/api/download", {"url": url}, timeout=120)
    except Exception as e:
        finish(loading, branded(f"⚠️ Error: {e}"))
        return
    if file_res.status_code != 200:
        finish(loading, branded(f"⚠️ Download failed: {file_res.text[:200]}"))
        return

    finish(loading, branded("✅ Sending..."))
    content_type = file_res.headers.get("content-type", "")
    if "video" in content_type:
        bot.send_video(message.chat.id, file_res.content)
    else:
        bot.send_photo(message.chat.id, file_res.content)


def _send_pin_batch(chat_id, group, media_type):
    """Send one batch of media. If Telegram throttles us (429), wait the
    exact time it tells us to and retry once instead of dropping the batch."""
    def _do_send():
        if len(group) == 1:
            # Telegram's send_media_group requires 2-10 items; a lone
            # item must be sent as a single message or it silently fails.
            only = group[0]
            if media_type == "video":
                bot.send_video(chat_id, only.media)
            else:
                bot.send_photo(chat_id, only.media)
        else:
            bot.send_media_group(chat_id, group)

    try:
        _do_send()
    except ApiTelegramException as e:
        retry_after = None
        try:
            retry_after = e.result_json.get("parameters", {}).get("retry_after")
        except Exception:
            pass
        if e.error_code == 429 and retry_after:
            time.sleep(retry_after + 1)
            _do_send()
        else:
            raise


def pinterest_search_cmd(message, media_type, feature, label):
    register(message)
    query, count = parse_query_and_count(message.text)
    if not query:
        bot.reply_to(message, branded(f"❌ Format: /{label} &lt;name&gt; [count]"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, feature)
    if not allowed:
        bot.reply_to(message, limit_reached_text(label, used, limit))
        return

    loading = send_loading(message, "Searching Pinterest")

    try:
        res = api_post(PINTEREST_API, "/api/search", {"query": query, "type": media_type, "limit": count})
    except Exception as e:
        finish(loading, branded(f"⚠️ API error: {e}"))
        return
    if res.status_code != 200:
        finish(loading, branded(f"⚠️ Failed: {res.text[:200]}"))
        return

    results = res.json().get("results", [])
    if not results:
        finish(loading, branded("❌ No results found."))
        return

    finish(loading, branded(f"✅ Sending {len(results)} {media_type}(s) for: {b(query)}"))

    for i_ in range(0, len(results), 10):
        batch = results[i_:i_ + 10]
        group = []
        for item in batch:
            url = item["video_url"] if media_type == "video" else item["image_url"]
            if not url:
                continue
            group.append(types.InputMediaVideo(media=url) if media_type == "video" else types.InputMediaPhoto(media=url))
        if not group:
            continue
        try:
            _send_pin_batch(message.chat.id, group, media_type)
        except Exception as e:
            bot.send_message(message.chat.id, branded(f"⚠️ Batch failed: {e}"))
        # Small pause between batches so back-to-back albums don't trip
        # Telegram's flood control (this is what caused the 429 errors).
        if i_ + 10 < len(results):
            time.sleep(1.5)


@bot.message_handler(commands=["pinsearch"])
def pinsearch_cmd(message):
    pinterest_search_cmd(message, "image", "pinterest_search", "pinsearch")


@bot.message_handler(commands=["pinvsearch"])
def pinvsearch_cmd(message):
    pinterest_search_cmd(message, "video", "pinterest_search", "pinvsearch")


# ══════════════════════════════════════════════════════════════ Instagram

@bot.message_handler(commands=["instadl"])
def instagram_download(message):
    register(message)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: <code>/instadl &lt;post/reel link&gt;</code>"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, "instagram_download")
    if not allowed:
        bot.reply_to(message, limit_reached_text("Instagram download", used, limit))
        return

    url = parts[1].strip()
    loading = send_loading(message, "Fetching Instagram post")

    try:
        res = api_post(INSTAGRAM_API, "/api/download", {"url": url})
    except Exception as e:
        finish(loading, branded(f"⚠️ Error: {e}"))
        return
    if res.status_code != 200:
        finish(loading, branded(f"⚠️ Failed: {res.text[:200]}"))
        return

    result = res.json()
    media = result.get("media", [])
    if not media:
        finish(loading, branded("❌ No media found."))
        return

    finish(loading, branded(f"✅ {b(result.get('owner') or '')} — {result.get('count')} item(s)"))

    for i_ in range(0, len(media), 10):
        batch = media[i_:i_ + 10]
        group = []
        for item in batch:
            group.append(types.InputMediaVideo(media=item["url"]) if item["type"] == "video" else types.InputMediaPhoto(media=item["url"]))
        try:
            bot.send_media_group(message.chat.id, group)
        except Exception as e:
            bot.send_message(message.chat.id, branded(f"⚠️ Batch failed: {e}"))


def instagram_search_cmd(message, path, feature, label):
    register(message)
    query, count = parse_query_and_count(message.text)
    if not query:
        bot.reply_to(message, branded(f"❌ Format: /{label} &lt;query&gt; [count]"))
        return

    allowed, used, limit = check_and_use(data, message.from_user.id, feature)
    if not allowed:
        bot.reply_to(message, limit_reached_text(label, used, limit))
        return

    loading = send_loading(message, "Searching Instagram")

    try:
        res = api_post(INSTAGRAM_API, path, {"query": query, "limit": count})
    except Exception as e:
        finish(loading, branded(f"⚠️ API error: {e}"))
        return
    if res.status_code != 200:
        finish(loading, branded(f"⚠️ Failed: {res.text[:200]}"))
        return

    results = res.json().get("results", [])
    if not results:
        finish(loading, branded("❌ No results found."))
        return

    lines = [header(f"Results for #{query}")]
    for idx, r in enumerate(results, 1):
        lines.append(
            f"{idx}. 👤 {r.get('channel_name') or 'unknown'} (👥 {fmt_num(r.get('channel_followers'))})\n"
            f"   ❤️ {fmt_num(r.get('like_count'))}"
            + (f" · 👁 {fmt_num(r.get('view_count'))}" if r.get("view_count") is not None else "")
            + f"\n   📅 {r.get('upload_date') or 'N/A'} · {r.get('url')}"
        )
    finish(loading, branded("\n".join(lines))[:4000])

    for i_ in range(0, len(results), 10):
        batch = results[i_:i_ + 10]
        group = []
        for r in batch:
            if not r.get("media_url"):
                continue
            group.append(types.InputMediaVideo(media=r["media_url"]) if r["media_type"] == "video" else types.InputMediaPhoto(media=r["media_url"]))
        if group:
            try:
                bot.send_media_group(message.chat.id, group)
            except Exception as e:
                bot.send_message(message.chat.id, branded(f"⚠️ Media batch failed: {e}"))


@bot.message_handler(commands=["instasearch"])
def instasearch_cmd(message):
    instagram_search_cmd(message, "/api/search", "instagram_search", "instasearch")


@bot.message_handler(commands=["instapsearch"])
def instapsearch_cmd(message):
    instagram_search_cmd(message, "/api/psearch", "instagram_psearch", "instapsearch")


# ══════════════════════════════════════════════════════════════ ADMIN: /give /addadmin

@bot.message_handler(commands=["give"])
def give_cmd(message):
    register(message)
    if not is_admin(data, message.from_user.id):
        bot.reply_to(message, branded("🚫 Admins only."))
        return

    parts = message.text.split()
    target_id = None
    duration = None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if len(parts) >= 2:
            duration = parts[1]
    elif len(parts) >= 3:
        try:
            target_id = int(parts[1])
        except ValueError:
            bot.reply_to(message, branded("❌ User id must be numeric."))
            return
        duration = parts[2]

    if not target_id or not duration:
        bot.reply_to(
            message,
            branded(
                "❌ Format:\n"
                "<code>/give &lt;user_id&gt; &lt;days|unlimited&gt;</code>\n"
                "OR reply to the user's message with:\n"
                "<code>/give &lt;days|unlimited&gt;</code>"
            ),
        )
        return

    try:
        result = grant_premium(data, target_id, duration)
    except ValueError:
        bot.reply_to(message, branded("❌ Duration must be a number of days or 'unlimited'."))
        return

    label = "Unlimited" if result == "unlimited" else f"{duration} day(s)"
    bot.reply_to(message, branded(header("Premium Granted") + quote(f"👤 User: {code(target_id)}\n💎 {label}")))

    try:
        bot.send_message(target_id, branded(header("You got Premium! 🎉") + quote(f"💎 {label} — enjoy unlimited access.")))
    except Exception:
        pass


@bot.message_handler(commands=["addadmin"])
def addadmin_cmd(message):
    register(message)
    if not is_admin(data, message.from_user.id):
        bot.reply_to(message, branded("🚫 Admins only."))
        return

    parts = message.text.split()
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(parts) >= 2:
        try:
            target_id = int(parts[1])
        except ValueError:
            bot.reply_to(message, branded("❌ User id must be numeric."))
            return

    if not target_id:
        bot.reply_to(message, branded("❌ Format: <code>/addadmin &lt;user_id&gt;</code> or reply to their message."))
        return

    added = add_admin(data, target_id)
    msg = "✅ Added as admin." if added else "ℹ️ Already an admin."
    bot.reply_to(message, branded(quote(f"👤 {code(target_id)} — {msg}")))


# ══════════════════════════════════════════════════════════════ ADMIN PANEL

def admin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        primary_button("Stats", "adm:stats"),
        primary_button("Users", "adm:users"),
    )
    markup.row(
        success_button("Give Premium", "adm:giveprem"),
        success_button("Add Admin", "adm:addadmin"),
    )
    markup.row(danger_button("Broadcast", "adm:broadcast"))
    markup.row(menu_button())
    return markup


@bot.message_handler(commands=["admin"])
def admin_panel(message):
    register(message)
    if not is_admin(data, message.from_user.id):
        bot.reply_to(message, branded("🚫 Admins only."))
        return

    bot.reply_to(message, branded(header("Admin Panel") + quote("🛠 " + b("Manage users, premium & broadcasts."))), reply_markup=admin_panel_markup())


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm:"))
def on_admin_action(call):
    if not is_admin(data, call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 Admins only.")
        return

    action = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)

    if action == "stats":
        total_users = len(data["users"])
        premium_users = sum(1 for u in data["users"].values() if is_premium(u))
        total_admins = len(data["admins"])
        bot.send_message(
            call.message.chat.id,
            branded(
                header("Bot Stats")
                + quote(f"👥 {b('Total users')}: {code(total_users)}\n💎 {b('Premium')}: {code(premium_users)}\n🛠 {b('Admins')}: {code(total_admins)}")
            ),
            reply_markup=with_menu_button(),
        )

    elif action == "users":
        lines = [header(f"Users ({len(data['users'])})")]
        for uid, u in list(data["users"].items())[:30]:
            name = u.get("username") or u.get("first_name") or uid
            status = "💎" if is_premium(u) else "🆓"
            lines.append(f"{status} {code(uid)} — {name}")
        if len(data["users"]) > 30:
            lines.append(f"\n...and {len(data['users']) - 30} more")
        bot.send_message(call.message.chat.id, branded("\n".join(lines)), reply_markup=with_menu_button())

    elif action == "giveprem":
        msg = bot.send_message(
            call.message.chat.id,
            branded("✏️ Reply to this message with:\n<code>&lt;user_id&gt; &lt;days|unlimited&gt;</code>"),
        )
        bot.register_next_step_handler(msg, _handle_giveprem_input)

    elif action == "addadmin":
        msg = bot.send_message(call.message.chat.id, branded("✏️ Reply to this message with the user_id to make admin."))
        bot.register_next_step_handler(msg, _handle_addadmin_input)

    elif action == "broadcast":
        msg = bot.send_message(call.message.chat.id, branded("✏️ Reply to this message with the broadcast text."))
        bot.register_next_step_handler(msg, _handle_broadcast_input)


def _handle_giveprem_input(message):
    if not is_admin(data, message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, branded("❌ Format: &lt;user_id&gt; &lt;days|unlimited&gt;"))
        return
    try:
        target_id = int(parts[0])
    except ValueError:
        bot.reply_to(message, branded("❌ User id must be numeric."))
        return

    try:
        result = grant_premium(data, target_id, parts[1])
    except ValueError:
        bot.reply_to(message, branded("❌ Duration must be a number of days or 'unlimited'."))
        return

    label = "Unlimited" if result == "unlimited" else f"{parts[1]} day(s)"
    bot.reply_to(message, branded(quote(f"✅ Premium granted to {code(target_id)} — {label}")))
    try:
        bot.send_message(target_id, branded(header("You got Premium! 🎉") + quote(f"💎 {label}")))
    except Exception:
        pass


def _handle_addadmin_input(message):
    if not is_admin(data, message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        bot.reply_to(message, branded("❌ User id must be numeric."))
        return
    added = add_admin(data, target_id)
    bot.reply_to(message, branded(quote(f"{'✅ Added' if added else 'ℹ️ Already'} admin: {code(target_id)}")))


def _handle_broadcast_input(message):
    if not is_admin(data, message.from_user.id):
        return
    pending_broadcast[message.from_user.id] = message.text

    markup = types.InlineKeyboardMarkup()
    markup.add(
        success_button("Send to all", "bc:send"),
        danger_button("Cancel", "bc:cancel"),
    )
    preview = quote(message.text)
    bot.reply_to(
        message,
        branded(header("Confirm Broadcast") + preview + f"\n\n📢 Will send to {len(data['users'])} users."),
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("bc:"))
def on_broadcast_confirm(call):
    if not is_admin(data, call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 Admins only.")
        return

    action = call.data.split(":", 1)[1]
    text = pending_broadcast.pop(call.from_user.id, None)

    if action == "cancel" or not text:
        bot.answer_callback_query(call.id, "❌ Cancelled.")
        bot.edit_message_text("❌ Broadcast cancelled.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    bot.answer_callback_query(call.id, "📢 Sending...")
    bot.edit_message_text(branded("📢 Broadcasting..."), chat_id=call.message.chat.id, message_id=call.message.message_id)

    sent, failed = 0, 0
    for uid in all_user_ids(data):
        try:
            bot.send_message(uid, branded(text))
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.05)   # gentle pacing to avoid Telegram flood limits

    bot.send_message(call.message.chat.id, branded(quote(f"✅ Sent: {sent}\n❌ Failed: {failed}")))


FEATURE_HANDLERS = {
    "ttdl": tiktok_download,
    "ytdl": youtube_download,
    "ytaudio": youtube_audio_cmd,
    "ytsearch": ytsearch_cmd,
    "ytshort": ytshort_cmd,
    "pindl": pinterest_download,
    "pinsearch": pinsearch_cmd,
    "pinvsearch": pinvsearch_cmd,
    "instadl": instagram_download,
    "instasearch": instasearch_cmd,
    "instapsearch": instapsearch_cmd,
}


if __name__ == "__main__":
    print(f"{BOT_NAME} running...")
    bot.infinity_polling()
