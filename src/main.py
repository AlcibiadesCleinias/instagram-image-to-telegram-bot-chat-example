"""Example script to load 1st image from instagram post and upload to
telegram @like bot with emojis after.

For instagram - simple aiohttp requests;
For telegram bot chat - telethon (on user mode).
"""
import asyncio

import aiohttp
from pydantic import BaseSettings
from telethon import TelegramClient
from dotenv import load_dotenv

# Load env with settings
load_dotenv('../.env')


async def get_photo_from_post(post_url: str):
    url_to_image = f'{post_url}media/?size=l'

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url_to_image) as response:

            if response.status == 200:
                return await response.read()

            print(f'Error with post {post_url}')
            raise Exception


class Settings(BaseSettings):
    TG_SESSION: str = 'telegram_session'
    TG_API_HASH: str
    TG_API_ID: int
    TG_BOT_USERNAME: str = '@like'

    INSTAGRAM_REQUEST_BATCH_PER_SECOND: int = 10

    class Config:
        case_sensitive = True


settings = Settings()
client = TelegramClient(settings.TG_SESSION, settings.TG_API_ID, settings.TG_API_HASH)


async def send_instagram_post_to_telegram_bot(post_url: str):
    entity = await client.get_entity('@like')
    me = await client.get_me()
    username = me.username
    print(f'U logged as {username}')

    image = await get_photo_from_post(post_url)
    print(f'Got image from inst {image}')

    async with asyncio.Lock():
        await client.send_message(
            entity,
            file=image
        )
        await client.send_message(
            entity,
            '😡 / 😔 / 😐 / ☺️ / 😍',
        )


async def main_impl():
    # TODO: insert from here
    # TODO: user argparser
    urls = ['https://www.instagram.com/p/Ckh0_3eMrzb/']

    for i in range(0, len(urls), settings.INSTAGRAM_REQUEST_BATCH_PER_SECOND):
        tasks = [
            send_instagram_post_to_telegram_bot(url) for url in urls[i:i + settings.INSTAGRAM_REQUEST_BATCH_PER_SECOND]
        ]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)


if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_impl())
