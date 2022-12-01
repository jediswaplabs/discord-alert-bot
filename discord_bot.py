'''
This file contains the discord bot to be called from within telegram_bot.py
'''
import os, discord
from dotenv import load_dotenv
from telegram import Bot
from pandas import read_pickle
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
        # set of Discord usernames & roles that the Discord bot is listening to
        self.listening_to = {'handles': set(), 'roles': set()}
        # dictionary {discord username: telegram id}
        self.discord_telegram_map = {'handles': {}, 'roles': {}}
        # dictionary {telegram id: {data}}
        self.users = dict()
        # path to database
        self.data_path = './data'
        self.debug_code = int(os.getenv('DEBUG'))
        self.client = None

    def refresh_data(self):
        '''
        Populates/updates users, listening_to, discord_telegram_map.
        '''
        self.users = read_pickle(self.data_path)['user_data']

        # update sets of notification triggers where available
        for v in self.users.values():
            [self.listening_to['roles'].add(x) for x in v['roles']]
            try:
                discord_handle = v['discord_username']
            except KeyError:
                continue
            self.listening_to['handles'].add(discord_handle)

            # create set of all TG ids requesting notifications for this handle
            if discord_handle not in self.discord_telegram_map['handles']:
                self.discord_telegram_map['handles'][discord_handle] = set()
            self.discord_telegram_map['handles'][discord_handle].add(v['telegram_id'])

            # create set of all TG ids requesting notifications for each role
            for role in v['roles']:
                if role not in self.discord_telegram_map['roles']:
                    self.discord_telegram_map['roles'][role] = set()
                self.discord_telegram_map['roles'][role].add(v['telegram_id'])

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
        Sends a message to all Telegram bot users.
        '''
        telegram_ids = read_pickle(self.data_path).keys()
        for telegram_id in telegram_ids:
            self.send_to_TG(telegram_id, msg)

    def get_roles(self, discord_username, guild_id=1031616432049496225):
        '''
        Takes a Discord username, returns all roles set for user in current guild.
        '''
        #user = client.fetch_user(user_id)
        guild = self.client.get_guild(guild_id)
        user = guild.get_member_named(discord_username)
        roles = [role.name for role in user.roles]
        print(f'\n\n\nDEBUG DISCORD: Got these roles: {roles}')
        return roles

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
        self.client = discord.Client(intents=intents)
        client = self.client

        # actions taken at startup
        @client.event
        async def on_ready():
            all_handles = self.listening_to['handles']
            all_roles = self.listening_to['roles']
            mentions_update = f"""
            Notifications active for mentions of {all_handles} and {all_roles}.
            """
            print(f'{client.user.name} has connected to Discord!')
            msg = 'Discord bot is up & running!'
            self.send_to_all(msg)
            self.send_to_TG(self.debug_code, mentions_update)

        # actions taken on every new Discord message
        @client.event
        async def on_message(message):

            # handle mentions: forward to TG as in the Discord->Telegram lookup
            for username in self.listening_to['handles']:
                user = message.guild.get_member_named(username)

                if user in message.mentions:
                    telegram_ids = self.discord_telegram_map['handles'][username]

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

            # role mentions: forward to TG as in the Discord->Telegram lookup
            for role in self.listening_to['roles']:
                # probably some getter for role is needed for equality of objects
                if role in message.mentions:
                    telegram_ids = self.discord_telegram_map['roles'][role]
                    author = message.author
                    guild_name = message.guild.name
                    alias = user.display_name
                    url = message.jump_url
                    contents = '@'+alias+message.content[message.content.find('>')+1:]
                    header = f"Message to {role} in {guild_name}:\n\n"
                    link = '['+contents+']'+'('+url+')'
                    out_msg = header+link
                    print(f'\n{author} mentioned {role}:')

                    for telegram_id in telegram_ids:
                        if self.users[telegram_id]['alerts_active']:
                            self.send_to_TG(telegram_id, out_msg)

            # DONE: Have bot also check for mentioned roles
            # TODO: Have bot listen to specified subset of channels only
            # TODO: Check behavior with multiple bot instances open at once
            # TODO: Check behavior with bot on multiple servers simultaneously



        DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        client.run(DISCORD_TOKEN)
