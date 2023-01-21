"""Example script to load 1st image from instagram post and upload to
telegram @like bot with emojis after, and finally perform sending prepared
post to a destination chat.

It performs action each interval for a list of posts.

For instagram - simple aiohttp requests;
For telegram bot chat - telethon (on user mode).
"""
import asyncio
import logging

import aiohttp
from pydantic import BaseSettings
from telethon import TelegramClient
from dotenv import load_dotenv

# Load env with settings
load_dotenv('.env')
logging.basicConfig(
    format=u'%(levelname)-8s | %(asctime)s | %(message)s | %(filename)+13s',
    level='INFO',
)
logger = logging.getLogger(__name__)

# It works with @like bot flow (image -> emojis -> picture with publish button).
TG_BOT_USERNAME = '@like'

WORKER_DELAY = 3600 * 24


# Env settings.
class Settings(BaseSettings):
    TG_SESSION: str = 'telegram_session'
    TG_API_HASH: str
    TG_API_ID: int
    # To notify about problems and flow end.
    TG_ADMIN_ID: int = 0
    # To where you want to sent a result of @like bot.
    TG_DESTINATION_ENTITY: str = 'me'

    INSTAGRAM_POSTS: list[str] = ['https://www.instagram.com/p/Ckh0_3eMrzb/']

    class Config:
        case_sensitive = True


# Client init.
settings = Settings()
client = TelegramClient(settings.TG_SESSION, settings.TG_API_ID, settings.TG_API_HASH)


# Instagram methods.
async def get_instagram_post_photo(post_url: str):
    url_to_image = f'{post_url}media/?size=l'

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url_to_image) as response:

            if response.status == 200:
                return await response.read()

            logger.info(f'Error with post {post_url}')
            raise Exception


# Telethon methods.
async def _send_image_with_emoji(image: bytes):
    entity = await client.get_entity(TG_BOT_USERNAME)
    await client.send_message(
        entity,
        file=image
    )
    await client.send_message(
        entity,
        '😡 / 😔 / 😐 / ☺️ / 😍',
    )


async def _get_prepared_query_with_image():
    messages = await client.get_messages(TG_BOT_USERNAME)
    message_last = messages[0]
    if not message_last.buttons:
        return

    # TODO: more checks
    inline_query = message_last.buttons[1][0].inline_query
    logger.info(f'Got inline query {inline_query = }')
    query = await client.inline_query(TG_BOT_USERNAME, inline_query)
    return query[0]


async def _get_inline_query_from_bot(image: bytes):
    async with asyncio.Lock():
        await _send_image_with_emoji(image)
        await asyncio.sleep(5)
        return await _get_prepared_query_with_image()


async def send_instagram_post_with_emoji(post_url: str, destination_chat: str):
    me = await client.get_me()
    username = me.username
    logger.info(f'U logged as {username}')

    image = await get_instagram_post_photo(post_url)
    logger.info(f'Got image from inst {image}')

    query = await _get_inline_query_from_bot(image)

    destination_entity = await client.get_entity(destination_chat)
    result = await query.click(destination_entity)

    logger.info(f'Finally sent, got {result = }')


# Script logic.
async def main_impl():
    for idx, post_url in enumerate(settings.INSTAGRAM_POSTS):
        try:
            await send_instagram_post_with_emoji(post_url, settings.TG_DESTINATION_ENTITY)
        except Exception as e:
            await client.send_message(settings.TG_ADMIN_ID, f"Problem occurred {e}, bot stopped.")
            raise e

        if idx + 1 == len(settings.INSTAGRAM_POSTS):
            logger.info('Last post reached, break the process.')
            return await client.send_message(settings.TG_ADMIN_ID, 'Last post reached, break the process.')

        logger.info(f'Sleep for {WORKER_DELAY}...')
        await asyncio.sleep(WORKER_DELAY)


if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_impl())
