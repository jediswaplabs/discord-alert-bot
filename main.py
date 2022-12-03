#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This script is running a Telegram bot and a Discord asynchronously within
the same event loop. In general, the Telegram bot is used as a frontend to
write user data to the db, while the Discord bot only reads data from there
to update his notification triggers on Discord.
"""

from telegram_bot import TelegramBot
from discord_bot import DiscordBot
import asyncio

# initialize bots & insert Discord bot instance into TG bot
disc_bot = DiscordBot()
tg_bot = TelegramBot(disc_bot)

# Initialize Telegram bot
# Discord bot gets initialized from event loop started from within TG bot
asyncio.run(tg_bot.run())



# DONE: add botpic, about info, description
# DONE: implement Telegram frontend (button menu for data entry)
# DONE: function for users to delete their data!
# DONE: Prompt for discord handle, guild/channel to listen to
# DONE: Find out best way to run both bots within 1 thread asynchronously
# TODO: Switch off logging when most basic features seem implemented
# TODO: Implement some way to assert that bot is not offline
#       (i.e. call some bot function every 5 minutes & check for a reply)
