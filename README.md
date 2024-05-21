# instagram-image-to-telegram-bot-chat-example
Example script to load 1st image from instagram post and upload to
telegram @like bot, append emojis, and finally send to the target chat.

## Stack
- For instagram - simple aiohttp requests;
- For telegram bot chat - telethon (on user mode).

_This script consists of such periodic tasks in advance._

_It designed to use .env via dotenv_

# Client
- For instagram - simple aiohttp requests;
- For telegram bot chat - **telethon** (on user mode).

# Requirements
Check `Dockerfile`, thus here is python3.8+. For python requirement: [src/requirements.txt](src/requirements.txt)

# Start
Firstly, Prepare `.env` in **src**.

## Bash
`cd src && python main.py`

## Docker [help wanted]
Currently, no possibility to run through docker coz of threading problem in telethon.
To build an image:
```bash
docker build . --tag instagram-post-to-telegram-bot
```

To run
```bash
docker run --rm -v $(pwd)/src:/opt instagram-post-to-telegram-bot
```
