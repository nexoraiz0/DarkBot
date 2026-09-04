import asyncio
import logging
import os
import random
import re
import sqlite3

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

logging.basicConfig(level=logging.INFO)

SLOT_JACKPOT_VALUE = 64

# Username админов (без @), которым разрешено смотреть/менять список наград.
ADMIN_USERNAMES = ["Nexoraizfuck", "Raivens1", "Mtl_sr"]

DEFAULT_REWARDS = [
    "https://t.me/nft/ViceCream-157848",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

# Список ссылок на награды хранится в БД, а не в памяти процесса и не в
# обычном файле — на Railway файловая система эфемерна и стирается при
# каждом редеплое, вместе с любым JSON-файлом рядом с ботом.
#
# Если задан DATABASE_URL (после того как в проект на Railway добавлен
# сервис PostgreSQL) — используем Postgres, он персистентный и переживает
# любой редеплой без доп. настройки.
#
# Если DATABASE_URL не задан — работаем через локальный SQLite-файл (удобно
# для теста на своём компьютере, но на Railway без Postgres он НЕ переживёт
# редеплой — там нужен именно DATABASE_URL).
DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.getenv("DB_PATH", "rewards.db")

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2


def _get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS rewards ("
            "id SERIAL PRIMARY KEY, "
            "url TEXT NOT NULL UNIQUE, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    else:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS rewards ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "url TEXT NOT NULL UNIQUE, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    conn.commit()
    cur.close()

    # Если таблица только что создана и пуста — заполняем стартовыми
    # значениями по умолчанию (только один раз, при самом первом запуске).
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rewards")
    count = cur.fetchone()[0]
    cur.close()
    if count == 0:
        for url in DEFAULT_REWARDS:
            _insert_reward(conn, url)
    conn.close()

    logging.info(
        "Хранилище наград: %s", "PostgreSQL" if USE_POSTGRES else f"SQLite ({DB_PATH})"
    )


def _insert_reward(conn, url: str) -> bool:
    """Вставляет ссылку, если её ещё нет (ловим конфликт уникальности).
    Возвращает True, если реально добавили, False — если уже была."""
    cur = conn.cursor()
    try:
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO rewards (url) VALUES (%s) ON CONFLICT (url) DO NOTHING",
                (url,),
            )
        else:
            cur.execute("INSERT OR IGNORE INTO rewards (url) VALUES (?)", (url,))
        added = cur.rowcount > 0
        conn.commit()
    finally:
        cur.close()
    return added


def get_rewards() -> list[str]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT url FROM rewards ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]


def add_reward_db(url: str) -> bool:
    """Возвращает True, если ссылка реально добавлена, False — если уже была в списке."""
    conn = _get_conn()
    try:
        return _insert_reward(conn, url)
    finally:
        conn.close()


def remove_reward_by_index(index: int) -> str | None:
    """index — 0-based позиция в списке, отсортированном как в get_rewards().
    Возвращает удалённый url или None, если индекс вне диапазона."""
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute("SELECT id, url FROM rewards ORDER BY id")
    rows = cur.fetchall()
    if index < 0 or index >= len(rows):
        cur.close()
        conn.close()
        return None
    reward_id, url = rows[index]
    cur.execute(f"DELETE FROM rewards WHERE id = {placeholder}", (reward_id,))
    conn.commit()
    cur.close()
    conn.close()
    return url



# ID премиум-эмодзи
SEVEN_EMOJI_ID = "5443135830883313930"
SLOT_EMOJI_ID = "5915833712368424979"
WIN_EMOJI_ID = "5208541126583136130"
GIFT_EMOJI_ID = "5436006606078769970"
FIRE_EMOJI_ID = "5424972470023104089"
ARROW_EMOJI_ID = "5301038027601098171"
LINK_EMOJI_ID = "5271604874419647061"
STAR_EMOJI_ID = "5924870095925942277"
DIAMOND_EMOJI_ID = "5280858699286471614"

router = Router()


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def is_admin(username: str | None) -> bool:
    return username is not None and username in ADMIN_USERNAMES



# Ищем t.me/nft/<slug> где угодно в тексте — пересланные сообщения часто
# содержат ссылку БЕЗ "https://" в начале (просто "t.me/nft/..."), поэтому
# проверка на префикс http(s):// раньше пропускала такие ссылки мимо.
NFT_LINK_RE = re.compile(r"(?:https?://)?t\.me/nft/([A-Za-z0-9_\-]+)", re.IGNORECASE)


def extract_nft_link(text: str) -> str | None:
    """Возвращает нормализованную ссылку https://t.me/nft/<slug>, если она
    есть в тексте (в любом виде — с http(s):// или без), иначе None."""
    match = NFT_LINK_RE.search(text)
    if not match:
        return None
    return f"https://t.me/nft/{match.group(1)}"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private" and is_admin(message.from_user.username):
        await message.answer(
            "Привет, админ! Управление наградами доступно прямо здесь, в личке:\n\n"
            "/rewards — показать список ссылок на NFT-награды\n"
            "Перешли сюда подарок (NFT) или пришли ссылку текстом — добавится в список\n"
            "/remove &lt;номер&gt; — убрать ссылку по номеру из /rewards"
        )
        return
    await message.answer("Привет! Отправь эмодзи 🎰, чтобы испытать удачу!")


@router.message(Command("rewards"))
async def cmd_rewards(message: Message) -> None:
    # Список наград — админская информация, показываем только в личке админам.
    if message.chat.type != "private" or not is_admin(message.from_user.username):
        return

    rewards = get_rewards()
    if not rewards:
        await message.reply("Список наград пуст.")
        return

    lines = ["🎁 Текущие ссылки на награды:\n"]
    for i, url in enumerate(rewards, start=1):
        lines.append(f"{i}. {url}")
    lines.append("\nЧтобы убрать ссылку: /remove &lt;номер&gt;")
    await message.reply("\n".join(lines))


@router.message(Command("remove"))
async def cmd_remove_reward(message: Message) -> None:
    if message.chat.type != "private" or not is_admin(message.from_user.username):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.reply("Использование: /remove &lt;номер&gt; (номер бери из /rewards)")
        return

    index = int(parts[1].strip()) - 1
    removed = remove_reward_by_index(index)
    if removed is None:
        await message.reply("Нет ссылки с таким номером. Посмотри актуальный список: /rewards")
        return

    await message.reply(f"✅ Удалено: {removed}\nОсталось наград: {len(get_rewards())}")


async def add_reward(message: Message, url: str) -> None:
    """Общая логика добавления ссылки в награды — используется и для
    текстовых ссылок, и для настоящих пересланных Telegram-подарков."""
    added = add_reward_db(url)
    if not added:
        await message.reply("Такая ссылка уже есть в списке наград.")
        return
    await message.reply(f"✅ Добавлено в награды: {url}\nВсего наград: {len(get_rewards())}")


@router.message(F.chat.type == "private", F.unique_gift)
async def handle_admin_dm_gift(message: Message) -> None:
    """Админ пересылает/отправляет боту НАСТОЯЩИЙ Telegram-подарок (NFT).
    Такое сообщение не содержит message.text — Telegram передаёт его через
    отдельное поле unique_gift (Bot API: UniqueGiftInfo), поэтому раньше
    он просто не ловился хендлером на текстовые ссылки. Слаг из
    unique_gift.gift.name — это ровно то, что идёт в ссылку t.me/nft/<slug>.
    """
    if not is_admin(message.from_user.username):
        return

    slug = message.unique_gift.gift.name
    url = f"https://t.me/nft/{slug}"
    await add_reward(message, url)


@router.message(F.chat.type == "private", F.text)
async def handle_admin_dm_link(message: Message) -> None:
    """Админ присылает ссылку ТЕКСТОМ или пересылает сообщение со ссылкой
    (например, форвард поста с t.me/nft/... — Telegram при пересылке не
    сохраняет настоящий unique_gift, только текст со ссылкой, часто БЕЗ
    "https://" в начале). Настоящие "живые" подарки, отправленные боту
    напрямую (не форвардом), ловит handle_admin_dm_gift выше."""
    if not is_admin(message.from_user.username):
        return
    if message.text.startswith("/"):
        return  # неизвестная команда — не пытаемся трактовать как ссылку

    url = extract_nft_link(message.text)
    if url is None:
        # Не t.me/nft-ссылка — на всякий случай всё равно принимаем обычный
        # http(s)-адрес целиком (например, не-NFT награду добавили вручную).
        stripped = message.text.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            url = stripped
    if url is None:
        return  # в тексте нет распознаваемой ссылки — игнорируем

    await add_reward(message, url)


@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    dice_value = message.dice.value
    logging.info(f"User {message.from_user.id} rolled slot machine: {dice_value}")

    if dice_value == SLOT_JACKPOT_VALUE:
        await handle_win(message)
    # На всех остальных комбинациях бот молчит.


def build_win_text(reward_url: str, use_custom_emoji: bool) -> str:
    if use_custom_emoji:
        win = custom_emoji(WIN_EMOJI_ID, "🎉")
        sevens = custom_emoji(SEVEN_EMOJI_ID, "7️⃣") * 3
        gift = custom_emoji(GIFT_EMOJI_ID, "🎁")
        fire = custom_emoji(FIRE_EMOJI_ID, "🔥")
        arrow = custom_emoji(ARROW_EMOJI_ID, "👇")
        link = custom_emoji(LINK_EMOJI_ID, "🔗")
        slots = custom_emoji(SLOT_EMOJI_ID, "🎰")
        star = custom_emoji(STAR_EMOJI_ID, "⭐")
        diamond = custom_emoji(DIAMOND_EMOJI_ID, "💎")
    else:
        win = "🎉"
        sevens = "7️⃣" * 3
        gift = "🎁"
        fire = "🔥"
        arrow = "👇"
        link = "🔗"
        slots = "🎰"
        star = "⭐"
        diamond = "💎"

    return (
        f"{win} Выигрыш! Слот выдал\n"
        f"{sevens}!\n\n"
        f"Твой профиль пополнился новым NFT{gift}. NFT скоро будет отправлен на ваш аккаунт{fire}\n"
        f"NFT {arrow}\n"
        f'{link} <a href="{reward_url}">Ссылка</a>\n\n'
        f"На этом веселье не заканчивается! Крути {slots} дальше и выбивай другие предметы. {star}\n\n"
        f"{diamond} Вся коллекция: @LudoBanks {star}"
    )


async def handle_win(message: Message) -> None:
    rewards = get_rewards()
    if not rewards:
        logging.warning("Список наград пуст — нечего выдавать.")
        return

    reward_url = random.choice(rewards)

    try:
        response_text = build_win_text(reward_url, use_custom_emoji=True)
        await message.reply(response_text)
    except TelegramBadRequest as e:
        # Скорее всего невалидный/недоступный custom_emoji_id — шлём без него
        logging.error(f"Не удалось отправить с premium emoji, отправляю fallback: {e}")
        response_text = build_win_text(reward_url, use_custom_emoji=False)
        await message.reply(response_text)
    except Exception as e:
        logging.error(f"Ошибка в handle_win: {e}", exc_info=True)


async def main() -> None:
    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
