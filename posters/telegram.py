import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv, find_dotenv
from os import getenv

from data.database import DB

load_dotenv(find_dotenv())

TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

async def post_podcast() -> None:
    podcast = DB.get_random()
    print(podcast)