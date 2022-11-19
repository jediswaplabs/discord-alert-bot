#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram_bot import TelegramBot

telegram_bot = TelegramBot()
telegram_bot.run_bot()


# TODO: Prompt for discord handle, guild/channel to listen to
# TODO: Move data from local json to cloud (MongoDB)
# TODO: Switch off logging before bot is released into the wild
