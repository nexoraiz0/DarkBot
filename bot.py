import asyncio
import logging
import random

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

logging.basicConfig(level=logging.INFO)



# value=64 -> три семёрки (джекпот)
SLOT_JACKPOT_VALUE = 64

# Значения, при которых выпадает ровно две семёрки из трёх барабанов
SLOT_TWO_SEVENS_VALUES = {16, 32, 48, 52, 56, 60, 61, 62, 63}

rewards_list = [
    "https://example.com/reward1",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

router = Router()


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
        await message.answer("7️⃣7️⃣7️⃣  Близко! Ещё чуть-чуть и джекпот — попробуй ещё раз 🎰")
    # На всех остальных комбинациях бот теперь молчит — как ты и просил


async def handle_win(message: Message) -> None:
    reward_url = random.choice(rewards_list)
    response_text = (
        f"Джекпот {premium_sevens} !\n\n"
        f"Поздравляю ты выбил нфт себе в профиль\n"
        f"Нфт скоро будет зачислен на твой аккаунт\n"
        f"Выбивай {premium_sevens} и забирай нфт из коллекции\n"
        f"Колекция - (<a href=\"{random_link}\">@SeeSheperdBank</a>)"
    )
    await message.answer(response_text)


async def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Критически важно против дублей: сбрасываем вебхук и все накопленные апдейты
    # перед стартом поллинга. Если где-то параллельно висит webhook или второй
    # процесс поллинга — апдейты будут долетать по несколько раз, как у тебя на скрине.
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
