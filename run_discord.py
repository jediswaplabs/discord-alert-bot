#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This file is for testing & debugging purposes only
'''

from discord_bot import *
load_dotenv()
discord_user = os.getenv('DISCORD_NAME')

arg_dict = {
    'telegram_user_name': '',
    'telegram_chat_ID': '',
    'discord_user_name': '',
    'discord_channel_list': [],  # <- take channel IDs here?
    'discord_roles_list': []
    }

arg_dict['discord_user_name'] = discord_user

run_bot(arg_dict)
