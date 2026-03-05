import asyncio
import logging
import random
import json

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ChatType, ContentType

import os, io
from dotenv import load_dotenv

from PIL import Image, ImageFont
from demotivator import Demotivator
from demotivator.indent import ImageIndentation

from texts import TROLL_STRINGS, ANSWER_STRINGS, CAPTIONS

# =========================
# Configuration
# =========================

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN must be set in .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# =========================
# Data
# =========================

ALPHABET = [
    'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м',
    'н', 'о', 'п', 'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ъ',
    'ы', 'ь', 'э', 'ю', 'я'
]

last_asked = set()

TARGET_MIN_WIDTH = 800
TARGET_MAX_WIDTH = 800

# =========================
# Demotivator setup
# =========================

font = ImageFont.truetype("LiberationSerif-Regular.ttf", 60)

border = ImageIndentation.css_like(3)
padding = ImageIndentation.css_like(8)
margin = ImageIndentation.css_like(50, 50, 200)

demotivator_template = Demotivator(
    font=font,
    border=border,
    margin=margin,
    padding=padding,
    background="#000",
    foreground="#fff"
)

# =========================
# Utility functions
# =========================

def tran_string(input_text: str, fontname: str):
    input_text = input_text.lower()
    output = ""

    with open(f'fonts/{fontname}.json', mode='r', encoding='utf-8') as file:
        font = json.load(file)

    for char in input_text:
        if char in font:
            output += random.choice(font[char])
        else:
            output += char

    return output


def chance(probability: float) -> bool:
    return random.random() < probability

def normalize_image(image, min_width=800, max_width=1600):
    width, height = image.size
    
    if width < min_width:
        scale = min_width / width
    elif width > max_width:
        scale = max_width / width
    else:
        return image
    
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.LANCZOS)

# =========================
# Handlers
# =========================

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(START_MSG)


@router.message(Command("copy"))
async def cmd_copy(message: Message):
    if message.reply_to_message:
        try:
            await message.reply_to_message.send_copy(
                chat_id=message.chat.id,
                reply_to_message_id=message.message_id
            )
        except Exception:
            await message.reply("Ошибка копирования.")
    else:
        await message.reply("Отправь команду ответом на сообщение.")


@router.message(Command("tran"))
async def cmd_tran(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        translated = tran_string(parts[1], "china")
        await message.reply(translated)
    else:
        await message.reply("Введите текст после команды.")


@router.message(Command("ask"))
async def cmd_ask(message: Message):
    user_id = message.from_user.id

    if user_id in last_asked:
        await message.reply("Дождись ответа на предыдущий вопрос!")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) <= 1:
        await message.reply("Введите запрос.")
        return

    last_asked.add(user_id)
    temp = await message.reply("⏳")

    await asyncio.sleep(random.randint(4, 15))

    await temp.delete()
    await message.reply(random.choice(ANSWER_STRINGS))
    last_asked.remove(user_id)


@router.message(
    F.content_type == ContentType.TEXT,
    F.chat.type == ChatType.PRIVATE
)
async def private_translate(message: Message):
    await message.reply(tran_string(message.text, "china"))

@router.message(
    F.content_type == ContentType.PHOTO,
    F.chat.type == ChatType.PRIVATE
)
async def handle_photo(message: Message):
    try:
        # 1. Get highest resolution photo
        photo = message.photo[-1]

        # 2. Download file into memory
        file = await bot.get_file(photo.file_id)
        file_bytes = io.BytesIO()
        await bot.download(file, destination=file_bytes)
        file_bytes.seek(0)

        # 3. Open image with Pillow
        image = Image.open(file_bytes).convert("RGB")
        image = normalize_image(image, TARGET_MIN_WIDTH, TARGET_MAX_WIDTH)


        # 4. Generate random caption
        caption = random.choice(CAPTIONS)

        # 5. Create demotivator
        result_image = demotivator_template.demotivate(image, caption)

        # 6. Save result to memory buffer
        output_buffer = io.BytesIO()
        result_image.save(output_buffer, format="JPEG")
        output_buffer.seek(0)

        # 7. Send back to user
        await message.answer_photo(
            photo=BufferedInputFile(
                output_buffer.read(),
                filename="demotivator.jpg"
            )
        )

    except Exception as e:
        logger.exception("Error processing image")
        await message.answer("Ошибка обработки изображения.")

@router.message()
async def troll_handler(message: Message):
    if chance(0.015):
        await asyncio.sleep(random.randint(10, 180))
        await message.reply(random.choice(TROLL_STRINGS))


# =========================
# Main entry point
# =========================

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())