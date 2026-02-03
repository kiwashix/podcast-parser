import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.markdown import hlink
from dotenv import load_dotenv, find_dotenv
from os import getenv

from data.database import DB

load_dotenv(find_dotenv())

TOKEN = getenv("BOT_TOKEN")
CHAT_ID = getenv("CHAT_ID")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

async def post_podcast(podcast_title: str, summary: str, category: str) -> None:
    try:
        link = hlink('devdigest', 'https://t.me/devdigest_ru')
        summary = f"{summary}\n\n{link}"
        await bot.send_message(chat_id=CHAT_ID,
                               text=summary,
                               parse_mode="HTML")
    except Exception as e:
        print(f"Telegram error: {e}")