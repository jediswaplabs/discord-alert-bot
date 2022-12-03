#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, wrong-import-position
"""
In this file, the TelegramBot class is defined.
Usage:
Send /start to initiate the conversation on Telegram. Press Ctrl-C on the
command line to stop the bot.
"""

import logging, os, random
from typing import Dict
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    PersistenceInput,
    filters,
)
load_dotenv('./.env')


class TelegramBot:
    """
    A class to encapsulate all relevant methods of the Telegram bot.
    """

    def __init__(self, discord_bot_instance):
        """
        Constructor of the class. Initializes certain instance variables.
        """
        # The single data file the bot is using
        self.data_path = './data'
        # Discord bot instance (set from outside this scope)
        self.discord_bot = discord_bot_instance

        # Enable logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO
        )
        logger = logging.getLogger(__name__)

        # Set up conversation states & inline keyboard
        self.CHOOSING, self.TYPING_REPLY = range(2)
        reply_keyboard = [
            ["Discord handle", "Discord channels"],
            ["Discord roles", "Discord guild",],
            ["Delete my data", "Done"]
        ]
        self.markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    def set_discord_instance(self, bot):
        """Setter if bot instance needs to be set from outside this scope."""
        self.discord_bot = bot

    async def start_discord_bot(self):
        """
        Starts Discord bot. This needs to be the final addition to the event loop
        since anything after starting the Discord bot will only be run after
        the Discord bot is closed.
        """
        await self.discord_bot.run_bot()

    def parse_str(self, user_data: Dict[str, str]) -> str:
        """Helper function for formatting the gathered user info."""
        out_list = []
        # Only show non-null values
        for key, value in user_data.items():
            if value not in [set(), [], None, '']:
                out_list.append(f'{key} - {value}')
        return "\n".join(out_list).join(["\n", "\n"])

    def under_construction_msg(self):
        """A placeholder message for yet to be implemented features."""
        reply = (
            "🚧 "*8+"\n\n\t_*...under construction...*_\n\n"+"🚧 "*8+ \
            "\n\nEnter 'Done' to go back."
        )
        return str(reply)

    async def add_placeholders(self, update, context) -> None:
        """Helper function to create some user_data entries."""
        guild = int(os.getenv("TESTGUILD"))
        context.user_data["discord roles"] = set()
        context.user_data["discord channels"] = set()
        context.user_data["discord guild"] = guild
        return

    async def start(self, update, context) -> int:
        """Start the conversation, display any stored data and ask user for input."""
        reply_text = "Hello!\n"

        if context.user_data:
            # Add 'guild', 'roles', 'channels' keys to user data
            await self.add_placeholders(update, context)

            reply_text += (
                f" Your data so far: \n{self.parse_str(context.user_data)}\n."
                f" Please choose:"
            )
        else:
            reply_text += (
                " To receive a notification whenever your Discord handle is mentioned,"
                " please select 'Discord handle' from the menu below."
                " To restrict notifications to certain channels only,"
                " select 'Discord channels'."
                " To receive notifications for mentions of specific roles,"
                " select 'Discord roles'."
            )
        await update.message.reply_text(reply_text, reply_markup=self.markup)

        return self.CHOOSING

    async def discord_handle(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""
        text = update.message.text.lower()
        context.user_data["choice"] = text

        # Prompt for Discord handle
        rand_name = random.choice(['Tom', 'Anna', 'Mia', 'Max'])
        rand_i = str(random.randint(100,999))
        rand_user = rand_name+'#'+rand_i

        # Show current set Discord handle if it exists and give option to
        # leave it unchanged (i.e. 'go /back')

        reply_text = (
            f"Please enter your Discord username (i.e. {rand_user}). "
            f"You can find it by tapping your avatar or in settings -> "
            f"my account -> username."
        )
        await update.message.reply_text(reply_text)

        return self.TYPING_REPLY

    async def discord_channels(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""
        # TODO
        text = update.message.text.lower()
        context.user_data["choice"] = text

        if context.user_data.get(text):
            reply_text = (
                f"Your {text}? I already know the following about that: {context.user_data[text]}"
            )
        else:
            reply_text = f"Your {text}? Yes, I would love to hear about that!"
        reply_text = self.under_construction_msg()
        await update.message.reply_text(reply_text)

        return self.TYPING_REPLY

    async def discord_roles(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""
        # TODO
        text = update.message.text.lower()
        context.user_data["choice"] = text

        if context.user_data.get(text):
            reply_text = (
                f"Your {text}? I already know the following about that: {context.user_data[text]}"
            )
        else:
            reply_text = f"Your {text}? Yes, I would love to hear about that!"
        reply_text = self.under_construction_msg()
        await update.message.reply_text(reply_text)

        return self.TYPING_REPLY

    async def discord_guild(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""
        # TODO
        text = update.message.text.lower()
        context.user_data["choice"] = text

        if context.user_data.get(text):
            reply_text = (
                f"Your {text}? I already know the following about that: {context.user_data[text]}"
            )
        else:
            reply_text = f"Your {text}? Yes, I would love to hear about that!"
        reply_text = self.under_construction_msg()
        await update.message.reply_text(reply_text)

        return self.TYPING_REPLY

    async def delete_my_data(self, update, context) -> int:
        """Deletes user entry from pickle file and context."""
        text = update.message.text.lower()
        context.user_data["choice"] = text

        chat_id = update.message.chat_id
        print('\n\n\n', 'user data requested:', context.user_data, '\n\n\n') # DEBUG
        if context.user_data == {}:
            reply_text = (
                "There's nothing here to be deleted yet!"
                " Back to /menu"
            )
        else:
            for k in context.user_data.copy().keys():
                del context.user_data[k]
            reply_text = f"Data successfully wiped!"
            # refresh Discord bot here

        await update.message.reply_text(reply_text)

        return ConversationHandler.END

    async def received_information(self, update, context) -> int:
        """Store info provided by user and ask for the next category."""
        text = update.message.text
        category = context.user_data["choice"]
        context.user_data[category] = text.lower()
        del context.user_data["choice"]

        # if coming from roles or channels. Ask if another should be added
        print("\n\n I'm in fct received_information() now!") # Debug only
        print("text ->", text)
        if "choice" in context.user_data:
            print("choice ->", choice)
            category = context.user_data["choice"]
            context.user_data[category] = text.lower()
            del context.user_data["choice"]

        await update.message.reply_text(
            "Success! Your data so far:"
            f"\n{self.parse_str(context.user_data)}\n"
            "Hit /menu to edit.",
            reply_markup=self.markup,
        )
        # Relay changes in data to Discord bot
        self.discord_bot.refresh_data()

        return self.CHOOSING


    async def show_data(self, update, context) -> None:
        """Display the gathered info."""
        await update.message.reply_text(
            f"This is what you already told me: {self.parse_str(context.user_data)}"
        )


    async def done(self, update, context) -> int:
        """Display the gathered info and end the conversation."""
        user_data = context.user_data

        if "choice" in user_data:
            del user_data["choice"]

        await update.message.reply_text(
            f"Your data so far: \n{self.parse_str(user_data)}\n"
            f"Hit /menu to edit.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    def refresh_discord_bot(self):
        """Needs to be called for changes to notification settings to take effect."""
        self.discord_bot.refresh_data()

    async def run(self):
        """
        A custom start-up procedure to run the TG bot alongside another
        process in the same event loop.
        """
        # Create the Application and pass it your bot's token.
        config = PersistenceInput(
            bot_data=False,
            chat_data=False,
            user_data=True,
            callback_data=True
        )
        persistence = PicklePersistence(
            filepath=self.data_path,
            store_data=config,
            update_interval=30
        )
        # Here we set updater to None because we want our custom webhook server to handle the updates
        # and hence we don't need an Updater instance
        token = os.environ['TELEGRAM_BOT_TOKEN']
        application = (
            Application.builder().token(token).persistence(persistence).build()
        )
        # save the values in `bot_data` such that we may easily access them in the callbacks
        application.bot_data["admin_chat_id"] = int(os.getenv("DEBUG_TG_ID"))
        application.bot_data["default_guild"] = 1031616432049496225

        # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        conv_handler = ConversationHandler(
            #entry_points=[CommandHandler("start", self.start)],
            entry_points=[
                CommandHandler("start", self.start),
                CommandHandler("menu", self.start),
                CommandHandler("back", self.start)
            ],
            states={
                self.CHOOSING: [
                    MessageHandler(filters.Regex("^Discord handle$"),
                        self.discord_handle
                    ),
                    MessageHandler(filters.Regex("^Discord channels$"),
                        self.discord_channels
                    ),
                    MessageHandler(filters.Regex("^Discord roles$"),
                        self.discord_roles
                    ),
                    MessageHandler(filters.Regex("^Discord guild$"),
                        self.discord_guild
                    ),
                    MessageHandler(filters.Regex("^Delete my data$"),
                        self.delete_my_data
                    ),
                ],
                self.TYPING_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~(filters.COMMAND | filters.Regex("^(back|Done)$")),
                        self.received_information
                    )
                ],
            },
            fallbacks=[MessageHandler(filters.Regex("^Done$"), self.done)],
            name="my_conversation",
            persistent=True,
        )

        application.add_handler(conv_handler)

        show_data_handler = CommandHandler("show_data", self.show_data)
        application.add_handler(show_data_handler)

        # Run application and discord bot simultaneously & asynchronously
        async with application:
            await application.initialize() # inits bot, update, persistence
            await application.start()
            await application.updater.start_polling()
            await self.start_discord_bot()
