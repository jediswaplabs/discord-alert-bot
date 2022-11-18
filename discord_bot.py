'''
This file contains the discord bot to be called from within telegram_bot.py
'''
import os, discord
from dotenv import load_dotenv


def run_discord_bot(arg_dict):

    # initialize bot, check for required data
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    required_data = [
        'discord_user_name',
        'telegram_user_name',
        'telegram_chat_ID'
        ]
    for x in required_data:
        assert x in arg_dict, f'A {x} must be specified.'

    @client.event
    async def on_ready():
        print(f'{client.user.name} has connected to Discord!')

    @client.event
    async def on_message(message):
        discord_user = arg_dict['discord_user_name']
        me = message.guild.get_member_named(discord_user) # TODO: Move one scope higher
        # check if user has been mentioned
        if me in message.mentions:
            author = message.author
            print(f'{author} mentioned {me}:\n')
            msg = message.content
            print(msg)
            # TODO: parsed_msg = parse_msg(msg)
            # TODO: send_to_telegram(chat_id, user_id, parsed_msg)

        # TODO: Have bot also check for mentioned roles
        # TODO: Have bot listen to specified channels only

    client.run(TOKEN)
