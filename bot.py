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
    "https://t.me/nft/ViceCream-157848",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

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
