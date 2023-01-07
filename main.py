#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is running a Telegram bot and a Discord bot asynchronously within
the same event loop. In general, the Telegram bot is used as a frontend for
user data entry. The Discord bot is only ever reading data, updating its
notification triggers accordingly and listening to Discord events.
Written by Al Matty - github.com/al-matty
"""

import logging
from telegram_bot import TelegramBot
from discord_bot import DiscordBot
import asyncio

# Configure logging
logging.basicConfig(format="%(asctime)s :\n%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
# Toggle more extensive logging (bot data, Discord messages, TG inline button presses)
debug_mode = False

# Instantiate bots
disc_bot = DiscordBot(debug_mode=debug_mode)
tg_bot = TelegramBot(disc_bot, debug_mode=debug_mode)

# Initialize Telegram bot. Discord bot gets initialized from within TG bot instance
asyncio.run(tg_bot.run())
