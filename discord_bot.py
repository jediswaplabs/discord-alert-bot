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
        #self.telegram_bot = TelegramBot()
        # set of Discord usernames that the Discord bot is listening to currently
        self.listening_to = set()
        # dictionary {discord username: telegram id}
        self.discord_telegram_map = dict()
        # dictionary {telegram id: {data}}
        self.users = dict()
        # path to database
        self.users_path = './users.json'

    def refresh_data(self):
        '''
        Populates/updates listening_to, discord_telegram_map & users.
        '''
        self.users = read_from_json(self.users_path)

        # update set of notification triggers where available
        for v in self.users.values():
            try:
                self.listening_to.add(v['discord_username'])
            except KeyError:
                continue

        # update Discord->Telegram lookup
        for v in self.users.values():
            # skip if no discord_username set yet for this user
            try:
                discord_handle = v['discord_username']
            except KeyError:
                continue
            # create set of all telegram ids requesting notifications for this handle
            if discord_handle not in self.discord_telegram_map:
                self.discord_telegram_map[discord_handle] = set()
            self.discord_telegram_map[discord_handle].add(v['telegram_id'])

        print('Data updated!')

    def send_to_TG(self, telegram_user_id, msg):
        '''
        Sends a message a specific Telegram user id.
        Uses Markdown V1 for inline link capability.
        '''
        self.telegram_bot.send_message(
            chat_id=telegram_user_id,
            text=msg,
            disable_web_page_preview=True,
            parse_mode='Markdown'
            )

    def send_to_all(self, msg):
        '''
        Sends a message to all Telegram users in users.json.
        '''
        telegram_ids = read_from_json(self.users_path).keys()
        for telegram_id in telegram_ids:
            self.send_to_TG(telegram_id, msg)

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

            # forward mention to each TG user as in the Discord->Telegram lookup
            for username in self.listening_to:
                user = message.guild.get_member_named(username)

                if user in message.mentions:
                    telegram_ids = self.discord_telegram_map[username]
                    for telegram_id in telegram_ids:
                        if self.users[telegram_id]['alerts_active']:
                            author = message.author
                            guild_name = message.guild.name
                            alias = user.display_name
                            url = message.jump_url
                            print(f'\n{author} mentioned {username}:')
                            contents = '@'+alias+message.content[message.content.find('>')+1:]
                            header = f"Mentioned by {author} in {guild_name}:\n\n"
                            link = '['+contents+']'+'('+url+')'
                            out_msg = header+link
                            self.send_to_TG(telegram_id, out_msg)

            # TODO: Have bot also check for mentioned roles
            # TODO: Have bot listen to specified subset of channels only
            # TODO: Check behavior with multiple bot instances open at once
            # TODO: Check behavior with bot on multiple servers simultaneously



        DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        client.run(DISCORD_TOKEN)
