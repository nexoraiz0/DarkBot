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

rewards_list = [
    "https://example.com/reward1",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

# ID премиум-эмодзи
SEVEN_EMOJI_ID = "5364243419164064459"
SLOT_EMOJI_ID = "5915988541644475488"

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
    # На всех остальных комбинациях бот молчит.


def build_win_text(reward_url: str, use_custom_emoji: bool) -> str:
    if use_custom_emoji:
        sevens = custom_emoji(SEVEN_EMOJI_ID, "7️⃣") * 3
        slots = custom_emoji(SLOT_EMOJI_ID, "🎰") * 3
    else:
        sevens = "7️⃣" * 3
        slots = "🎰" * 3

    return (
        f"Джекпот {sevens}!\n\n"
        f'Поздравляю ты выбил <a href="{reward_url}">нфт</a> себе в профиль  \n'
        f"Нфт скоро будет зачислен на твой аккаунт\n"
        f"Выбивай {slots}и забирай нфт из колекции\n"
        f"Колекция - (@LudoBanks)"
    )


async def handle_win(message: Message) -> None:
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
