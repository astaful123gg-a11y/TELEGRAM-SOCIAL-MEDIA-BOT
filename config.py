BOT_TOKEN = "8841209055:AAHfIzI5x0_OtzeqiAyrXc-PiAB6dI6e0Lc"

# Telegram numeric user id of the bot owner (get yours from @userinfobot)
OWNER_ID = 8600328303  # <-- replace with your real Telegram user id

BOT_NAME = "SHUVO ALL-IN-ONE BOT"
FOOTER = "\n\n<i>👑 Developer:</i> @Shuvobhai"

# ── Downstream APIs (already deployed) ────────────────────────────────────────
TIKTOK_API = "https://tiktok-download-api-xapo.onrender.com"
YOUTUBE_API = "https://youtube-api-all-in-one-by-shuvo.onrender.com"
PINTEREST_API = "https://pinterest-api-by-shuvo-uxk1.onrender.com"
INSTAGRAM_API = "https://insta-all-in-one-api-by-shuvo.onrender.com"
API_KEY = "SHUVO-apis"

# ── Daily free limits per feature (premium users bypass all of these) ───────
LIMITS = {
    "tiktok_download": 30,
    "youtube_download": 30,
    "youtube_audio": 30,
    "youtube_search": 40,
    "instagram_download": 30,
    "instagram_search": 20,
    "instagram_psearch": 20,
    "pinterest_download": 30,
    "pinterest_search": 100,
}

DATA_FILE = "user.json"
