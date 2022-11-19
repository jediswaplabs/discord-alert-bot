'''
This file contains the discord bot to be called from within telegram_bot.py
'''
import os, discord
from dotenv import load_dotenv
from telegram import Bot
from helpers import read_from_json


def run_discord_bot(telegram_user_id):

    load_dotenv()
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    users = read_from_json('./users.json')
    assert telegram_user_id in users, f'Telegram user {telegram_user_id} not found in db.'

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    client = discord.Client(intents=intents)
    telegram_bot = Bot(TELEGRAM_TOKEN)
    discord_username = users[telegram_user_id]['discord_username']


#    telegram_bot = arg_dict['telegram_bot_instance']
#    discord_username = arg_dict['discord_username']

#    required_data = [
#        'discord_username',
#        'telegram_username',
#        'telegram_user_id',
#        'telegram_bot_instance'
#        ]
#    for x in required_data:
#        assert x in arg_dict, f'A {x} must be specified.'
#

    @client.event
    async def on_ready():
        print(f'{client.user.name} has connected to Discord!')
        out_msg = f'Success! The Discord bot is now listening for mentions of {discord_username}!'
        telegram_bot.send_message(telegram_user_id, out_msg)
        #telegram_bot = arg_dict['telegram_bot_instance']
        #print(f'Telegram bot started.')

    @client.event
    async def on_message(message):

        me = message.guild.get_member_named(discord_username) # TODO: Move one scope higher
        # check if user has been mentioned
        if me in message.mentions:
            author = message.author
            guild_name = message.guild.name
            print(f'{author} mentioned {me}:\n')
            msg = message.content
            out_msg = f'Mentioned by {author} in {guild_name}:\n\n'+msg
            telegram_bot.send_message(telegram_user_id, out_msg)

        # TODO: Have bot also check for mentioned roles
        # TODO: Have bot listen to specified channels only
        # TODO: Check behavior with multiple instances oopen at once

    client.run(DISCORD_TOKEN)
