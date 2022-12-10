#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is running a Telegram bot and a Discord bot asynchronously
within the same event loop. In general, the Telegram bot is used as a
frontend to write user data to the db, from which the Discord bot is only
reading data to update notification triggers on Discord.
Written by Al Matty - github.com/al-matty
"""

import logging
from telegram_bot import TelegramBot
from discord_bot import DiscordBot
import asyncio

# Enable logging
logging.basicConfig(
    #format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    format="%(asctime)s :\n%(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# initialize bots & insert Discord bot instance into TG bot
disc_bot = DiscordBot()
tg_bot = TelegramBot(disc_bot)

# Initialize Telegram bot. Discord bot gets initialized from event loop started
# from within TG bot
asyncio.run(tg_bot.run())


# DONE: add botpic, about info, description
# DONE: implement Telegram frontend (button menu for data entry)
# DONE: function for users to delete their data!
# DONE: Prompt for discord handle, roles to listen to
# DONE: Find out best way to run both bots within 1 thread asynchronously
# TODO: Switch off logging once debugging is done
# TODO: Implement some way to assert that bot is not offline
#       (i.e. call some bot function every 5 minutes & check for a reply)
