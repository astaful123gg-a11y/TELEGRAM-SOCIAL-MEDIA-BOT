import json
import os
import time
import threading
from datetime import datetime, timezone

from config import DATA_FILE, OWNER_ID, LIMITS

_lock = threading.Lock()


def _default_data():
    return {"owner_id": OWNER_ID, "admins": [OWNER_ID], "users": {}}


def load_data():
    if not os.path.exists(DATA_FILE):
        data = _default_data()
        save_data(data)
        return data
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return _default_data()


def save_data(data):
    with _lock:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_user(data, user_id, username=None, first_name=None):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "username": username,
            "first_name": first_name,
            "premium_until": None,     # None | "unlimited" | unix timestamp
            "joined": int(time.time()),
            "usage": {"date": today_str()},
        }
        save_data(data)
    else:
        # keep username/first_name fresh
        changed = False
        if username and data["users"][uid].get("username") != username:
            data["users"][uid]["username"] = username
            changed = True
        if first_name and data["users"][uid].get("first_name") != first_name:
            data["users"][uid]["first_name"] = first_name
            changed = True
        if changed:
            save_data(data)

    user = data["users"][uid]
    if user["usage"].get("date") != today_str():
        user["usage"] = {"date": today_str()}
        save_data(data)

    return user


def is_admin(data, user_id):
    return user_id in data.get("admins", []) or user_id == data.get("owner_id")


def is_owner(data, user_id):
    return user_id == data.get("owner_id")


def is_premium(user):
    pu = user.get("premium_until")
    if pu == "unlimited":
        return True
    if isinstance(pu, (int, float)) and pu > time.time():
        return True
    return False


def premium_status_text(user):
    pu = user.get("premium_until")
    if pu == "unlimited":
        return "💎 Unlimited Premium"
    if isinstance(pu, (int, float)) and pu > time.time():
        remaining = int(pu - time.time())
        days = remaining // 86400
        hours = (remaining % 86400) // 3600
        return f"💎 Premium — {days}d {hours}h left"
    return "🆓 Free user"


def check_and_use(data, user_id, feature):
    """Returns (allowed: bool, used: int, limit: int). Increments usage if allowed."""
    user = get_user(data, user_id)
    limit = LIMITS.get(feature, 30)

    if is_premium(user):
        return True, 0, limit

    used = user["usage"].get(feature, 0)
    if used >= limit:
        return False, used, limit

    user["usage"][feature] = used + 1
    save_data(data)
    return True, used + 1, limit


def grant_premium(data, user_id, duration):
    """duration: 'unlimited' or an integer number of days (as int or str)."""
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "username": None, "first_name": None,
            "premium_until": None, "joined": int(time.time()),
            "usage": {"date": today_str()},
        }

    if str(duration).lower() == "unlimited":
        data["users"][uid]["premium_until"] = "unlimited"
    else:
        days = int(duration)
        current = data["users"][uid].get("premium_until")
        base = current if isinstance(current, (int, float)) and current > time.time() else time.time()
        data["users"][uid]["premium_until"] = base + days * 86400

    save_data(data)
    return data["users"][uid]["premium_until"]


def add_admin(data, user_id):
    if user_id not in data["admins"]:
        data["admins"].append(user_id)
        save_data(data)
        return True
    return False


def all_user_ids(data):
    return [int(uid) for uid in data["users"].keys()]
