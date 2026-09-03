import asyncio
import json
import logging
import os
import random

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

# Файл, в котором сохраняется список ссылок на NFT-награды — так список
# переживает перезапуск/редеплой бота (иначе всё в памяти обнулялось бы).
REWARDS_FILE = os.getenv("REWARDS_FILE", "rewards.json")

DEFAULT_REWARDS = [
    "https://t.me/nft/ViceCream-157848",
    "https://example.com/reward2",
    "https://example.com/reward3",
]


def load_rewards() -> list[str]:
    if os.path.exists(REWARDS_FILE):
        try:
            with open(REWARDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception as e:
            logging.error("Не удалось прочитать %s: %s", REWARDS_FILE, e)
    return list(DEFAULT_REWARDS)


def save_rewards(rewards: list[str]) -> None:
    try:
        with open(REWARDS_FILE, "w", encoding="utf-8") as f:
            json.dump(rewards, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error("Не удалось сохранить %s: %s", REWARDS_FILE, e)


# Список наград — единственный источник правды в памяти процесса,
# подгружается из REWARDS_FILE при старте и сохраняется туда при любом
# изменении (добавление/удаление ссылки админом).
rewards_list: list[str] = load_rewards()

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


def looks_like_url(text: str) -> bool:
    text = text.strip()
    return text.startswith("http://") or text.startswith("https://")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private" and is_admin(message.from_user.username):
        await message.answer(
            "Привет, админ! Управление наградами доступно прямо здесь, в личке:\n\n"
            "/rewards — показать список ссылок на NFT-награды\n"
            "Просто пришли ссылку сообщением — она добавится в список\n"
            "/remove &lt;номер&gt; — убрать ссылку по номеру из /rewards"
        )
        return
    await message.answer("Привет! Отправь эмодзи 🎰, чтобы испытать удачу!")


@router.message(Command("rewards"))
async def cmd_rewards(message: Message) -> None:
    # Список наград — админская информация, показываем только в личке админам.
    if message.chat.type != "private" or not is_admin(message.from_user.username):
        return

    if not rewards_list:
        await message.reply("Список наград пуст.")
        return

    lines = ["🎁 Текущие ссылки на награды:\n"]
    for i, url in enumerate(rewards_list, start=1):
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
    if index < 0 or index >= len(rewards_list):
        await message.reply("Нет ссылки с таким номером. Посмотри актуальный список: /rewards")
        return

    removed = rewards_list.pop(index)
    save_rewards(rewards_list)
    await message.reply(f"✅ Удалено: {removed}\nОсталось наград: {len(rewards_list)}")


@router.message(F.chat.type == "private", F.text)
async def handle_admin_dm_link(message: Message) -> None:
    """Админ просто присылает ссылку в личку боту — она добавляется в награды.
    Ловим этот хендлер последним (после команд выше), чтобы не мешать им."""
    if not is_admin(message.from_user.username):
        return
    if message.text.startswith("/"):
        return  # неизвестная команда — не пытаемся трактовать как ссылку
    if not looks_like_url(message.text):
        return  # обычное сообщение не от команды и не похожее на ссылку — игнорируем

    url = message.text.strip()
    if url in rewards_list:
        await message.reply("Такая ссылка уже есть в списке наград.")
        return

    rewards_list.append(url)
    save_rewards(rewards_list)
    await message.reply(f"✅ Добавлено в награды: {url}\nВсего наград: {len(rewards_list)}")


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
    if not rewards_list:
        logging.warning("Список наград пуст — нечего выдавать.")
        return

    reward_url = random.choice(rewards_list)

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
