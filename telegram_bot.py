#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This file contains the Telegram bot used for user data entry and for
calling the Discord bot. Initial bot framework taken from Andrés Ignacio
Torres <andresitorresm@gmail.com>.
'''

import os, logging
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater
from urllib.error import HTTPError
from dotenv import load_dotenv
from inspect import cleandoc
from helpers import read_from_json, write_to_json
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
        self.users = read_from_json('./users.json')

        # These will be checked against as substrings within each
        # message, so different variations are not required if their
        # radix is present (e.g. "all" covers "/all" and "ball")
        self.menu_trigger = ['/menu']

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

    def get_context(self):
        return context

    def send_to_chat_id(self, chat_id, msg, context):

        parsed_msg = self.parse_msg(msg)

        context.bot.send_message(
            chat_id=chat_id,
            text=parsed_msg,
            parse_mode='MarkdownV2'
            )

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
            }
        # removes unwanted indentation and adds escape characters as in escape_d
        return cleandoc(msg.translate(msg.maketrans(escape_d)))

    def show_menu(self, update, context):
        """
        Shows the menu with current items.
        """

        MENU_MSG = "*Bot Commands*\n\n" + \
                    "enter Discord /username to listen to\n" + \
                    "select Discord /guild to listen to\n" + \
                    "select Discord /channels to listen to\n\n" + \
                    "/pause Discord alerts\n" + \
                    "/continue Discord alerts\n"

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=MENU_MSG,
            parse_mode='MarkdownV2'
            )

    def send_msg(self, msg, context):
        """
        Sends a text message
        """
        parsed_msg = self.parse_msg(msg)
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=parsed_msg,
            parse_mode='MarkdownV2'
            )

    def send_to_user_id(self, user_id, msg):
        """
        Sends a text message to a Telegram Chat ID
        """
        parsed_msg = self.parse_msg(msg)
        context.bot.send_message(
            chat_id=user_id,
            text=parsed_msg,
            parse_mode='MarkdownV2'
            )

    def add_user(self, user_id, update, context):
        if user_id not in self.users:
            self.users[user_id] = {}
            telegram_name = update.message.from_user.username
            telegram_id = update.message.from_user.id
            self.users[user_id]['telegram_username'] = telegram_name
            self.users[user_id]['telegram_id'] = telegram_id
            write_to_json(self.users, './users.json')

    def start_dialogue(self, update, context):
        """
        Initiates the dialogue that appears when the bot is called by a user
        for the first time.
        """

        welcome_msg = self.parse_msg(
        """
        Welcome!
        This bot notifies you if your discord handle has been mentioned in a
        selection of Discord channels of your choosing.
        You can always get to the bot menu by typing /menu.
        """
        )

        user_id = update.message.chat_id
        self.add_user(user_id, update, context)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=welcome_msg,
            parse_mode='MarkdownV2'
            )

        self.add_channel(update, context)

    def add_discord_handle(self, update, context):
        user_id = update.message.chat_id
        # get discord username from prompt
        discord_handle = ''
        self.users[user_id]['discord_username'] = discord_handle
        write_to_json(self.users, './users.json')
        pass

    def add_channel(self, update, context):

        add_channel_msg = self.parse_msg(
        """
        Please type in a Discord channel address you want to receive notifications for,
        i.e. https://discord.gg/bh34Btvy or
        https://discord.com/channels/8276553372938765120/009266357485627752.

        You can get this information if you press and hold the Discord channel (mobile),
        select 'Invite', then 'Copy link', or right-click on the channel (laptop) and
        click 'Copy Link'.
        """
        )

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=add_channel_msg,
            disable_web_page_preview=True,
            parse_mode='MarkdownV2'
            )

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

            if word.startswith('/continue'):
                self.activate_discord_bot(update, context)
                #logging.info('Discord bot activated')
                return

            elif word.startswith('/pause'):
                self.deactivate_discord_bot(update, context)
                return

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
