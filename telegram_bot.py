#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This file contains the Telegram bot used as frontend and for user data entry.
Initial bot framework taken from Andrés Ignacio Torres <andresitorresm@gmail.com>.
'''

import os, logging, random
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from urllib.error import HTTPError
from dotenv import load_dotenv
from inspect import cleandoc
from helpers import read_from_json, write_to_json, create_if_not_found
load_dotenv('./.env')

class TelegramBot:
    """
    A class to encapsulate all relevant methods of the Telegram bot.
    """

    def __init__(self):
        """
        Constructor of the class. Initializes certain instance variables
        and checks if everything's O.K. for the bot to work as expected.
        """
        # This environment variable should be set before using the bot
        self.token = os.environ['TELEGRAM_BOT_TOKEN']

        # The single data file the bot is using
        self.users_path = './users.json'
        create_if_not_found({}, self.users_path)
        self.users = read_from_json(self.users_path)

        # These will be checked against as substrings within each
        # message, so different variations are not required if their
        # radix is present (e.g. "all" covers "/all" and "ball")
        self.menu_trigger = ['/menu', '/help']

        # Logic that ties TG commands to functions defined in this class
        self.command_map = {
            '/setup': self.setup_bot,
            '/username': self.edit_discord_handle,
            '/guild': self.set_guild,
            '/channels': self.add_channels,
            '/pause': self.pause_alerts,
            '/resume': self.resume_alerts,
            '/delete': self.delete_user,
            '/donate': self.show_donate,
            }

        # Discord bot instance (set from outside this scope)
        self.discord_bot = None

        # Stops runtime if no bot token has been set
        if self.token is None:
            raise RuntimeError(
                "FATAL: No token was found. " + \
                "You might need to specify one or more environment variables.")

        # Configures logging in debug level to check for errors
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.DEBUG)

    def run_bot(self):
        """
        Sets up the required bot handlers and starts the polling
        thread in order to successfully reply to messages.
        """

        # Instantiates the bot updater
        self.updater = Updater(self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Declares and adds handlers for commands that shows help info
        start_handler = CommandHandler('start', self.start_dialogue)
        help_handler = CommandHandler('help', self.show_menu)
        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(help_handler)

        # Declares and adds a handler for text messages that will reply with
        # a response if the message includes a trigger word
        text_handler = MessageHandler(Filters.text, self.handle_text_messages)
        self.dispatcher.add_handler(text_handler)

        # Fires up the polling thread. We're live!
        self.updater.start_polling()

    def set_discord_instance(self, bot):
        """
        To be called from outside this scope.
        """
        self.discord_bot = bot

    def parse_msg(self, msg):
        """
        Helper function to create telegram compatible text output
        and remove unwanted indentation from multiline strings
        """
        escape_d = {
            '.': '\.',
            '!': '\!',
            '(': '\(',
            ')': '\)',
            '-': '\-',
            '#': '\#',
            '>': '\>',
            '<': '\<',
            '.': '\.',
            }
        # removes unwanted indentation and adds escape characters as in escape_d
        return cleandoc(msg.translate(msg.maketrans(escape_d)))

    def start_dialogue(self, update, context):
        """
        Initiates the dialogue that appears when the bot is called by a user
        for the first time.
        """

        welcome_msg = """
        Welcome!
        This bot notifies you if your discord handle has been mentioned in a
        selection of Discord channels of your choosing.
        You can always get to the bot menu by typing /menu.
        """
        # Check if user exists already.
        # if not, run setup_bot(update, context)
        self.send_msg(welcome_msg, update, context)
        self.setup_bot(update, context)

    def show_menu(self, update, context):
        """
        Shows the menu with current items.
        """

        MENU_MSG = "*Bot Commands*\n\n" + \
                    "/setup bot step by step\n" + \
                    "show bot /menu\n" + \
                    "edit Discord /username to get notified for\n" + \
                    "edit the Discord /guild the bot is active for\n" + \
                    "specify certain Discord /channels only within guild\n\n" + \
                    "/pause all Discord alerts\n" + \
                    "/resume all Discord alerts\n" + \
                    "/delete my data (can re-enter data via /setup)\n"

        self.send_msg(MENU_MSG, update, context)
        return

    def send_msg(self, msg, update, context):
        """
        Sends a text message.
        """
        parsed_msg = self.parse_msg(msg)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=parsed_msg,
            disable_web_page_preview=True,
            parse_mode='MarkdownV2'
            )

    def under_construction_msg(self, update, context):
        """
        Sends a placeholder message.
        """
        msg = '🚧 '*8+'\n\n\t_*...under construction...*_\n\n'+'🚧 '*8
        parsed_msg = self.parse_msg(msg)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=parsed_msg,
            disable_web_page_preview=True,
            parse_mode='MarkdownV2'
            )

    def send_to_user_id(self, user_id, msg):
        """
        Sends a text message to a Telegram Chat ID.
        """
        parsed_msg = self.parse_msg(msg)
        context.bot.send_message(
            chat_id=user_id,
            text=parsed_msg,
            disable_web_page_preview=True,
            parse_mode='MarkdownV2'
            )

    def setup_bot(self, update, context):
        """
        Expandable wrapper to call functions that play a role in getting
        all necessary user information for the bot to work.
        """
        # check if user is already in dataset, set up if not
        self.add_user(update, context)

        # only top level here, calls of other functions
        # calls promts for discord handle, discord guild [, roles]

        # make new data available for Discord bot
        self.refresh_discord_bot()
        return

    def set_guild(self, update, context):
        """
        Setup wizard that's called if a user is not in the db yet.
        """
        user_id = update.message.chat_id
        self.under_construction_msg(update, context)
        return

    def edit_discord_handle(self, update, context):
        user_id = update.message.chat_id
        users = self.users

        # add new database entry if user is not known yet
        keys = ['telegram_username', 'telegram_id', 'alerts_active']
        if user_id in users:
            if not all(key in users[user_id] for key in keys):
                self.add_user(update, context)
                return

        # prompt for Discord handle
        rand_name = random.choice(['Tom', 'Anna', 'Mia', 'Max'])
        rand_i = str(random.randint(100,999))
        rand_user = rand_name+'#'+rand_i

        add_handle_msg = f"""
        Please enter your Discord username (i.e. {rand_user}).
        You can find it by tapping your avatar or in _*settings*_ -> _*my account*_ -> _*username*_.
        """
        self.send_msg(add_handle_msg, update, context)
        return

    def add_user(self, update, context):
        """
        Sets up user entry in database if not existing. Calls edit_discord_handle()
        once entry is created to prompt for the Discord username.
        """
        users = self.users
        user_id = update.message.chat_id
        telegram_name = update.message.from_user.username

        # if user data exists already: abort with message
        keys = ['telegram_username', 'telegram_id', 'discord_username', 'alerts_active']
        if user_id in users:
            if all(key in users[user_id] for key in keys):
                discord_handle = users[user_id]['discord_username']
                msg = f"""
                Discord bot already set up for {telegram_name}!
                Specified Discord username: {discord_handle}!
                Tap /username to change it.
                """
                self.send_msg(msg, update, context)
                return

        # if user not in users.json yet: Create entry
        else:
            msg = f"Didn't find TG id {user_id} in database."
            self.send_msg(msg, update, context)
            user_dict = {
                'telegram_username': telegram_name,
                'telegram_id': user_id,
                'alerts_active': True
                }
            self.users[user_id] = user_dict
            write_to_json(self.users, self.users_path)
            self.refresh_discord_bot()
            self.edit_discord_handle(update, context)    # prompt for Discord handle
            return

    def add_channels(self, update, context):
        """
        Function to restrict Discord bot to specific channels only.
        """
        rerun = False
        user_id = update.message.chat_id

        add_channel_msg = """
        Please type in a Discord channel address you want to receive notifications for,
        i.e. https://discord.gg/bh34Btvy or
        https://discord.com/channels/8276553372938765120/009266357485627752.

        You can get this information if you press and hold the Discord channel (mobile),
        select _*invite*_, then _*copy link*_, or right-click on the channel (laptop) and
        click _*copy link*_.
        """

        self.send_msg(add_channel_msg, update, context)

        # Ask if another channel should be added. If yes: rerun = True
        if rerun:
            add_channels(update, context)
        else:
            return

    def pause_alerts(self, update, context):
        """
        Deactivates Discord notification forwarding for this user.

        """
        user_id = update.message.chat_id
        self.users[user_id]['alerts_active'] = False
        write_to_json(self.users, self.users_path)
        self.refresh_discord_bot()
        msg = 'Bot paused. Tap /resume to reactivate notifications.'
        self.send_msg(msg, update, context)
        return

    def resume_alerts(self, update, context):
        """
        Reactivates Discord notification forwarding for this user.
        """
        user_id = update.message.chat_id
        self.users[user_id]['alerts_active'] = True
        write_to_json(self.users, self.users_path)
        self.refresh_discord_bot()
        msg ="""
        Mentions on Discord will now be forwarded again!
        """
        self.send_msg(msg, update, context)
        return

    def delete_user(self, update, context):
        user_id = update.message.chat_id

        if user_id in self.users:
            del self.users[user_id]
            write_to_json(self.users, self.users_path)
            msg = 'All data wiped!'
            self.send_msg(msg, update, context)
            self.refresh_discord_bot()

        else:
            msg = 'User data has already been deleted previously.'
            self.send_msg(msg, update, context)
        return

    def show_donate(self, update, context):
        """
        Show ETH donation addy.
        """
        msg = "Support the bot's development.\nDonate on Ethereum or any L2:"
        addy = "*0xD76beaffab0be32D0Cef2d0fE81e92C2ae7F55e9*"
        self.send_msg(msg, update, context)
        self.send_msg(addy, update, context)
        return

    def refresh_discord_bot(self):
        """
        Needs to be called after every change to 'users.json' for the
        changes to take effect on the Discord side of things.
        """
        self.discord_bot.refresh_data()

    def handle_text_messages(self, update, context):
        """
        Checks if a message comes from a group. If that is not the case,
        or if the message includes a trigger word, replies with merch.
        """
        words = set(update.message.text.lower().split())
        logging.debug(f'Received message: {update.message.text}')
        logging.debug(f'Splitted words: {", ".join(words)}')

        # For debugging: Log users that recieved message from bot
        chat_user_client = update.message.from_user.username
        if chat_user_client == None:
            chat_user_client = update.message.chat_id
            logging.info(f'{chat_user_client} interacted with the bot.')

        # Possibility: received command from menu_trigger
        for Trigger in self.menu_trigger:
            for word in words:
                if word.startswith(Trigger):
                    self.show_menu(update, context)
                    return

        # Possibility: received other command
        for word in words:

            # Run function for command as specified in self.command_map
            if word in self.command_map:
                self.command_map[word](update, context)

def main():
    """
    Entry point of the script. If run directly, instantiates the
    TelegramBot class and fires it up.
    """

    telegram_bot = TelegramBot()
    telegram_bot.run_bot()


# If the script is run directly, fires the main procedure
if __name__ == "__main__":
    main()
