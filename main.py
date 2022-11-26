#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram_bot import TelegramBot
from discord_bot import DiscordBot

tg_bot = TelegramBot()
disc_bot = DiscordBot()

# initialize bots & insert Discord bot instance into TG bot
tg_bot.run_bot()
tg_bot.set_discord_instance(disc_bot)
disc_bot.run_bot()


# TODO: add botpic, about info, description
# TODO: implement Telegram frontend (button menu for data entry)
# TODO: function for users to delete their data!
# TODO: Prompt for discord handle, guild/channel to listen to
# TODO: Move data from local json to cloud (MongoDB)
# TODO: Switch off logging before bot is 'released'
# TODO: Implement some way to assert that bot is not offline
#       (i.e. call some bot function every 5 minutes & check if it replies)
