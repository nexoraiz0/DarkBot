import asyncio
import logging
import random
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения для безопасности на Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Значение value=64 в Telegram Dice API соответствует комбинации 🎰 777 (джекпот)
SLOT_JACKPOT_VALUE = 64

# Список наград — ссылок, которые получит пользователь при выигрыше
rewards_list = [
    "https://example.com/reward1",
    "https://example.com/reward2",
    "https://example.com/reward3",
]

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Отправь эмодзи 🎰, чтобы испытать удачу и попробовать выиграть приз!"
    )


@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    """
    Обрабатывает бросок слот-машины.
    """
    dice_value = message.dice.value

    logging.info(f"User {message.from_user.id} rolled slot machine: {dice_value}")

    if dice_value == SLOT_JACKPOT_VALUE:
        await handle_win(message)
    else:
        await message.answer("Увы, не повезло! Попробуй ещё раз 🎰")


async def handle_win(message: Message) -> None:
    """Логика победы: отправка кастомных премиум-эмодзи семерок и оригинального текста."""
    random_link = random.choice(rewards_list)
    
    # ID кастомных семерок с вашего скриншота
    emoji_id = "5364243419164064459"
    
    # Собираем три премиум-семерки через официальный тег Telegram
    premium_sevens = (
        f'<tg-emoji id="{emoji_id}">7</tg-emoji>'
        f'<tg-emoji id="{emoji_id}">7</tg-emoji>'
        f'<tg-emoji id="{emoji_id}">7</tg-emoji>'
    )

    # Итоговый текст строго по вашему шаблону с маскировкой ссылки под @SeeSheperdBank
    response_text = (
        f"Джекпот {premium_sevens} !\n\n"
        f"Поздравляю ты выбил нфт себе в профиль\n"
        f"Нфт скоро будет зачислен на твой аккаунт\n"
        f"Выбивай {premium_sevens} и забирай нфт из коллекции\n"
        f"Колекция - (<a href=\"{random_link}\">@SeeSheperdBank</a>)"
    )

    # Добавляем инлайн-кнопку "ПОКАЗАТЬ ПОДАРОК" как на скриншоте
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ПОКАЗАТЬ ПОДАРОК", url=random_link)]
        ]
    )

    await message.answer(response_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
