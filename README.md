# SHUVO ALL-IN-ONE BOT

TikTok + YouTube + Pinterest + Instagram, one bot. Free daily limits, premium
system (no credits — just time-based unlimited access), full admin panel,
branded UI on every message.

## Setup
1. `config.py` te:
   - `BOT_TOKEN` — your bot token
   - `OWNER_ID` — **your own Telegram numeric user id** (get it from @userinfobot).
     This is the first admin, hardcoded — without this you can't use `/admin`,
     `/give`, or `/addadmin` at all on a fresh `user.json`.
2. `pip install -r requirements.txt`
3. `python bot.py`

`user.json` auto-creates on first run, right next to `bot.py`. It stores every
user's premium status, daily usage counters, and the admin list. Back this file
up if you redeploy — losing it resets everyone's premium/usage/admin status.

## Commands (users)
- `/start` — welcome + full command list
- `/status` — your premium status + today's usage per feature
- `/ttdl <link>` — TikTok video
- `/ytdl <link>` — YouTube video
- `/ytaudio <link or song name>` — YouTube audio (song, surah, lecture, etc.)
- `/ytsearch <name>` — YouTube video search (tap a button to download)
- `/ytshort <name>` — YouTube shorts search
- `/instadl <link>` — Instagram post/reel — sends ALL photos/videos in it
- `/instasearch <query> [count]` — Instagram reels search + auto-sends media
- `/instapsearch <query> [count]` — Instagram photo search + auto-sends media
- `/pindl <link>` — Pinterest pin
- `/pinsearch <query> [count]` — Pinterest images
- `/pinvsearch <query> [count]` — Pinterest videos

## Commands (admin only)
- `/admin` — inline control panel (Stats, Users, Give Premium, Add Admin, Broadcast)
- `/give <user_id> <days|unlimited>` — grant premium directly
- `/give <days|unlimited>` — **reply to the user's message** with this instead of typing their id
- `/addadmin <user_id>` — or reply to their message with `/addadmin`

## Daily free limits (premium bypasses all of these)
| Feature | Limit/day |
|---|---|
| TikTok download | 30 |
| YouTube download | 30 |
| YouTube audio | 30 |
| YouTube search | 40 |
| Instagram download | 30 |
| Instagram search | 20 |
| Instagram photo search | 20 |
| Pinterest download | 30 |
| Pinterest search | 100 |

Change these anytime in `config.py` → `LIMITS`.

## Premium system
No credits — just a time window:
- `/give 123456789 1` → 1 day unlimited access
- `/give 123456789 unlimited` → unlimited forever
- Stacks: giving more days to an already-premium user extends from their current expiry, not from now.

## Deploy on Render
Build: `pip install -r requirements.txt`
Start: `python bot.py`
⚠️ `user.json` lives on Render's ephemeral disk — it survives restarts but is
wiped on a fresh deploy/rebuild. For permanent persistence across redeploys,
you'd need external storage (a database, or periodic backup) — ask if you want
that added later.
