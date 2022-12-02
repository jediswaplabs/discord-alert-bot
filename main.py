#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram_bot import TelegramBot
from discord_bot import DiscordBot
import asyncio
import tracemalloc
tracemalloc.start()

# initialize bots & insert Discord bot instance into TG bot
disc_bot = DiscordBot()
tg_bot = TelegramBot(disc_bot)

# Initialize Telegram bot
# Discord bot gets initialized from within async framework of TG bot
tg_bot.run_bot()




# DONE: add botpic, about info, description
# DONE: implement Telegram frontend (button menu for data entry)
# DONE: function for users to delete their data!
# DONE: Prompt for discord handle, guild/channel to listen to
# TODO: Switch off logging before bot is 'released'
# TODO: Find out best way to run both bots within 1 thread asynchronously
# TODO: Implement some way to assert that bot is not offline
#       (i.e. call some bot function every 5 minutes & check for a reply)
