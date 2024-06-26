"""Example script to load 1st image from instagram post and upload to
telegram @like bot with emojis after, and finally perform sending prepared
post to a destination chat.

It performs action each interval for a list of posts.

For instagram - simple aiohttp requests;
For telegram bot chat - telethon (on user mode).
"""
import asyncio
import logging
from typing import Union, List

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
BOT_TO_BOT_MESSAGING_DELAY = 7


# Env settings.
class Settings(BaseSettings):
    TG_SESSION: str = 'telegram_session'
    TG_API_HASH: str
    TG_API_ID: int
    # To notify about problems and flow end.
    TG_ADMIN_ID: int = 0
    # To where you want to sent a result of @like bot.
    TG_DESTINATION_ENTITY: Union[int, str] = 'me'

    DELAY_BEFORE_REPEAT_INSTAGRAM_REQUEST: int = 60

    INSTAGRAM_POSTS: List[str] = ['https://www.instagram.com/p/Ckh0_3eMrzb/']

    class Config:
        case_sensitive = True


# Client init.
settings = Settings()
client = TelegramClient(settings.TG_SESSION, settings.TG_API_ID, settings.TG_API_HASH)


class InstagramInvalidImageResponse(Exception):
    pass

class InstagramRequestLoginException(Exception):
    pass

# Instagram methods.
async def get_instagram_post_photo(post_url: str):
    url_to_image = f'{post_url}media/?size=l'

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url_to_image) as response:

            if response.status == 200:
                read_image = await response.read()

                # Additional check if realy image.
                if (not hasattr(read_image, '__len__')):
                    logger.warning(f"[get_instagram_post_photo] Image from url {url_to_image} has no len attribute. "
                                   f"Received object: {read_image}.")
                    raise InstagramInvalidImageResponse()

                if read_image.startswith(b'<!DOCTYPE html>') and "https://www.instagram.com/accounts/login" in read_image.decode():
                    logger.warning(f"[get_instagram_post_photo] Image from url {url_to_image} is not an image. "
                                   f"Received object started with <!DOCTYPE html> that possibly means it is a login page.")
                    raise InstagramRequestLoginException()

                return read_image

            logger.info(f'Error with post {post_url}')
            raise Exception


# Telethon methods.
async def _send_image_with_emoji(image: bytes, delay: int = 0):
    entity = await client.get_entity(TG_BOT_USERNAME)
    # Flush previous state.
    await client.send_message(entity, '/start')
    await asyncio.sleep(delay)

    await client.send_message(
        entity,
        file=image
    )
    await asyncio.sleep(delay)

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
        # Send image to bot, then send emojies to apply to the picture (@like bot logic).
        await _send_image_with_emoji(image, BOT_TO_BOT_MESSAGING_DELAY)
        # Wait before preview of image with emojies loaded for the user.
        await asyncio.sleep(BOT_TO_BOT_MESSAGING_DELAY)
        return await _get_prepared_query_with_image()


async def send_instagram_post_with_emoji(post_url: str, destination_chat: Union[int, str]):
    me = await client.get_me()
    username = me.username
    logger.info(f'U logged as {username}')

    try:
        image = await get_instagram_post_photo(post_url)
    except InstagramRequestLoginException:
        _msg = f"Instagram request login page, repeat 1 more time after {settings.DELAY_BEFORE_REPEAT_INSTAGRAM_REQUEST} sec delay."
        await client.send_message(settings.TG_ADMIN_ID, _msg)
        logger.warning(_msg)

        await asyncio.sleep(settings.DELAY_BEFORE_REPEAT_INSTAGRAM_REQUEST)
        image = await get_instagram_post_photo(post_url)

    logger.info(f'Got image from inst {image}')

    query = await _get_inline_query_from_bot(image)

    destination_entity = await client.get_entity(destination_chat)
    result = await query.click(destination_entity)

    logger.info(f'Finally sent, got {result = }')


async def main_impl():
    """Main Script logic.
    If error happens with the flow it sleeps instead of retry with the next image.
    """
    for idx, post_url in enumerate(settings.INSTAGRAM_POSTS):
        try:
            await send_instagram_post_with_emoji(post_url, settings.TG_DESTINATION_ENTITY)
        except Exception as e:
            _msg = f"Problem occurred {e} with post {post_url}, pass."
            await client.send_message(settings.TG_ADMIN_ID, _msg)
            logger.exception(_msg)

        if idx + 1 == len(settings.INSTAGRAM_POSTS):
            logger.info('Last post reached, break the process.')
            return await client.send_message(settings.TG_ADMIN_ID, 'Last post reached, break the process.')

        logger.info(f'Sleep for {WORKER_DELAY}...')
        await asyncio.sleep(WORKER_DELAY)


if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main_impl())
