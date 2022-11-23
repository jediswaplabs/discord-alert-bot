#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram_bot import TelegramBot
from discord_bot import DiscordBot

tg_bot = TelegramBot()
disc_bot = DiscordBot()

tg_bot.run_bot()
#disc_bot.set_telegram_bot_instance(tg_bot)
disc_bot.run_bot()

# TODO: implement Telegram frontend (button menu for data entry)
# TODO: function for users to delete their data!
# TODO: Prompt for discord handle, guild/channel to listen to
# TODO: Move data from local json to cloud (MongoDB)
# TODO: Switch off logging before bot is 'released'
