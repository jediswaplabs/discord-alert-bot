'''
This file contains the discord bot to be called from within telegram_bot.py
'''
import os, discord
from dotenv import load_dotenv
from telegram import Bot
from helpers import read_from_json
load_dotenv()

class DiscordBot:
    """
    A class to encapsulate all relevant methods of the Discord bot.
    """

    def __init__(self):
        """
        Constructor of the class. Initializes certain instance variables
        and checks if everything's O.K. for the bot to work as expected.
        """
        # instantiate Telegram bot to send out messages to users
        TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_bot = Bot(TELEGRAM_TOKEN)
        # set of Discord usernames that the Discord bot is listening to currently
        self.listening_to = set()
        # dictionary {discord username: telegram id}
        self.discord_telegram_map = dict()
        # dictionary {telegram id: {data}}
        self.users = dict()

    def refresh_data(self):
        '''
        Populates/updates listening_to, discord_telegram_map & users.
        '''
        self.users = read_from_json('./users.json')
        for v in self.users.values():
            self.listening_to.add(v['discord_username'])
        self.discord_telegram_map = {v['discord_username']: v['telegram_id'] for v in self.users.values()}
        print('Data updated!')

    def send_to_TG(self, telegram_user_id, msg):
        '''
        Sends a message a specific Telegram user id.
        '''
        self.telegram_bot.send_message(telegram_user_id, msg)

    def send_to_all(self, msg):
        '''
        Sends a message to all Telegram users in users.json.
        '''
        telegram_ids = read_from_json('./users.json').keys()
        for telegram_id in telegram_ids:
            self.telegram_bot.send_message(telegram_id, msg)

    def run_bot(self):
        '''
        Actual logic of the bot is stored here.
        '''

        # update data to listen to at startup
        self.refresh_data()

        # fire up discord client
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        client = discord.Client(intents=intents)
        #telegram_bot = self.telegram_bot_instance

        # actions taken at startup
        @client.event
        async def on_ready():
            print(f'{client.user.name} has connected to Discord!')
            print(f'Discord bot is now listening for mentions of {self.listening_to}')
            msg = 'Discord bot is up & running!'
            self.send_to_all(msg)

        # actions taken on every new Discord message
        @client.event
        async def on_message(message):

            # send out msg to TG user if their Discord handle has been mentioned
            for username in self.listening_to:
                user = message.guild.get_member_named(username)

                if user in message.mentions:
                    if self.users[telegram_id]['alerts_active']:
                        telegram_id = self.discord_telegram_map[username]
                        author = message.author
                        guild_name = message.guild.name
                        print(f'{author} mentioned {username}:\n')
                        msg = message.content[message.content.find('>'):]
                        out_msg = f'Mentioned by {author} in {guild_name}:\n\n'+msg
                        self.send_to_TG(telegram_id, out_msg)

            # TODO: Have bot also check for mentioned roles
            # TODO: Have bot listen to specified subset of channels only
            # TODO: Check behavior with multiple bot instances open at once
            # TODO: Check behavior with bot on multiple servers simultaneously



        DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        client.run(DISCORD_TOKEN)
