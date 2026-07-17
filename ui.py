from telebot import types
from telebot.types import InlineKeyboardButton
from config import FOOTER, BOT_NAME

DIVIDER = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈"


def b(text):
    return f"<b>{text}</b>"


def i(text):
    return f"<i>{text}</i>"


def code(text):
    return f"<code>{text}</code>"


def quote(text):
    return f"<blockquote>{text}</blockquote>"


def divider():
    return DIVIDER


def branded(text):
    return f"{text}\n{DIVIDER}\n{FOOTER}"


def header(title, emoji="✨"):
    prefix = f"{emoji}  " if emoji else ""
    return f"{b(f'{prefix}{title.upper()}')}\n{DIVIDER}\n"


def progress_bar(used, limit, width=10):
    """Renders usage as a filled/empty block bar, e.g. ▰▰▰▰▰▱▱▱▱▱ 5/10"""
    if limit <= 0:
        filled = width
    else:
        filled = max(0, min(width, round((used / limit) * width)))
    bar = "▰" * filled + "▱" * (width - filled)
    return f"{code(bar)} {b(str(used))}/{limit}"


class SBtn(InlineKeyboardButton):
    """Inline button with an optional visual style ('success', 'primary',
    'danger'). Falls back to a plain button on Telegram clients that don't
    support styled buttons — the style is just extra metadata."""

    def __init__(self, text, style=None, **kwargs):
        super().__init__(text, **kwargs)
        self._style = style

    def to_dict(self):
        d = super().to_dict()
        if self._style:
            d["style"] = self._style
        return d


def success_button(text, callback_data):
    return SBtn(f"✅ {text}", style="success", callback_data=callback_data)


def primary_button(text, callback_data):
    return SBtn(f"🔷 {text}", style="primary", callback_data=callback_data)


def danger_button(text, callback_data):
    return SBtn(f"🗑 {text}", style="danger", callback_data=callback_data)


def neutral_button(text, callback_data):
    return SBtn(text, callback_data=callback_data)


def url_button(text, url):
    return SBtn(f"🔗 {text}", url=url)


def menu_button():
    return neutral_button("🏠 Main Menu", "menu:home")


def with_menu_button(*rows):
    """Build an InlineKeyboardMarkup from rows of buttons and always append
    a Main Menu button as its own row at the bottom."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in rows:
        markup.row(*row)
    markup.row(menu_button())
    return markup


def limit_reached_text(feature_label, used, limit):
    return branded(
        header("Daily Limit Reached", "🚫")
        + quote(f"{b(feature_label)}\n{progress_bar(used, limit)}")
        + f"\n\n💎 {b('Upgrade to Premium')} for unlimited access — ask an admin."
    )


def loading_text(action):
    return branded(f"⏳ {i(action + '...')}")
