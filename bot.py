import asyncio
import logging
import os
import random

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
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
        await handle_win(message)
    elif dice_value in SLOT_TWO_SEVENS_VALUES:
        await message.reply("7️⃣7️⃣7️⃣ Близко! Ещё чуть-чуть и джекпот — попробуй ещё раз 🎰")
    else:
        await message.reply("Не повезло, попробуй ещё раз 🎰")


def build_win_text(reward_url: str, use_custom_emoji: bool) -> str:
    if use_custom_emoji:
        sevens = custom_emoji(SEVEN_EMOJI_ID, "7️⃣") * 3
        firecrackers = custom_emoji(FIRECRACKER_EMOJI_ID, "🧨") * 3
    else:
        sevens = "7️⃣" * 3
        firecrackers = "🧨" * 3

    return (
Джекпот <tg-emoji emoji-id=\"5364243419164064459\">7️⃣</tg-emoji><tg-emoji emoji-id=\"5364243419164064459\">7️⃣</tg-emoji><tg-emoji emoji-id=\"5364243419164064459\">7️⃣</tg-emoji>!

Поздравляю ты выбил <a href=\"http://t.me/nft/ViceCream-157848\">нфт</a> себе в профиль  
Нфт скоро будет зачислен на твой аккаунт
Выбивай <tg-emoji emoji-id=\"5915988541644475488\">🎰</tg-emoji><tg-emoji emoji-id=\"5915988541644475488\">🎰</tg-emoji><tg-emoji emoji-id=\"5915988541644475488\">🎰</tg-emoji>и забирай нфт из колекции
Колекция - (@LudoBanks)
    )


async def handle_win(message: Message) -> None:
    reward_url = random.choice(rewards_list)

    try:
        response_text = build_win_text(reward_url, use_custom_emoji=True)
        await message.reply(response_text)
    except TelegramBadRequest as e:
        # Скорее всего невалидный/недоступный custom_emoji_id — шлём без них
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
