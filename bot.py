import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

logging.basicConfig(level=logging.INFO)

SLOT_JACKPOT_VALUE = 64
SLOT_TWO_SEVENS_VALUES = {16, 32, 48, 52, 56, 60, 61, 62, 63}

rewards_list = [
    "https://example.com/reward1",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

# ID премиум-эмодзи
SEVEN_EMOJI_ID = "5364243419164064459"
FIRECRACKER_EMOJI_ID = "5919885416644475488"
reward_url = random.choice(rewards_list)   # ← переменная называется reward_url

router = Router()


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer("Привет! Отправь эмодзи 🎰, чтобы испытать удачу!")

@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    dice_value = message.dice.value
    logging.info(f"User {message.from_user.id} rolled slot machine: {dice_value}")

    if dice_value == SLOT_JACKPOT_VALUE:
        try:
            await handle_win(message)
        except Exception as e:
            logging.error(f"Ошибка в handle_win: {e}", exc_info=True)
    elif dice_value in SLOT_TWO_SEVENS_VALUES:
        await message.reply("7️⃣7️⃣7️⃣ Близко! Ещё чуть-чуть и джекпот — попробуй ещё раз 🎰")


# --- ВОТ ЭТА ФУНКЦИЯ (замени старую целиком на неё) ---
async def handle_win(message: Message) -> None:
    reward_url = random.choice(rewards_list)

    sevens = custom_emoji(SEVEN_EMOJI_ID, "7") * 3
    firecrackers = custom_emoji(FIRECRACKER_EMOJI_ID, "🧨") * 3

    response_text = (
        f"Джекпот {sevens}!\n\n"
        f"Поздравляю ты выбил нфт себе в профиль\n"
        f"Нфт скоро будет зачислен на твой аккаунт\n"
        f"Выбивай {firecrackers} и забирай нфт из коллекции\n"
        f'Колекция - (<a href="{reward_url}">@SeeSheperdBank</a>)'
    )

    await message.reply(response_text)


