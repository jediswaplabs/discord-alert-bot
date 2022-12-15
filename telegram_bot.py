#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, wrong-import-position
"""
In this file, the TelegramBot class is defined. Usage:
Send /start to initiate the conversation on Telegram. Press Ctrl-C on the
command line to stop the bot.
"""

import logging, os, random, asyncio
from helpers import log, iter_to_str
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
load_dotenv("./.env")


class TelegramBot:
    """A class to encapsulate all relevant methods of the Telegram bot."""

    def __init__(self, discord_bot_instance):
        """
        Constructor of the class. Initializes certain instance variables.
        """
        # The single data file the bot is using
        self.data_path = "./data"
        # Discord bot instance
        self.discord_bot = discord_bot_instance

        # Set up conversation states & inline keyboard
        self.CHOOSING, self.TYPING_REPLY = range(2)
        reply_keyboard = [
            ["Discord handle", "Discord channels"],
            ["Discord roles", "Discord guild",],
            ["Delete my data", "Done"]
        ]
        self.markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        self.application = None


    def set_discord_instance(self, bot) -> None:
        """Setter if bot instance needs to be set from outside this scope."""
        self.discord_bot = bot


    async def start_discord_bot(self) -> None:
        """
        Starts Discord bot. This needs to be the final addition to the event loop
        since anything after starting the Discord bot will only be run after
        the Discord bot is closed.
        """
        await self.discord_bot.run_bot()


    def parse_str(self, user_data) -> str:
        """Helper function for formatting the gathered user info."""
        out_list = []
        # Only show non-empty values
        for key, value in user_data.items():
            if value not in [set(), [], None, ""]:
                out_list.append(f"{key} - {value}")
        return "\n".join(out_list).join(["\n", "\n"])


    def under_construction_msg(self, custom_msg=None) -> str:
        """A placeholder message for yet to be implemented features."""

        if custom_msg:
            reply = "🚧 "*8+"\n\n" + custom_msg + "\n\n"+"🚧 "*8
            reply += "\n\nBack to /menu or /done."
        else:
            reply = (
                "🚧 "*8+"\n\n\t...under construction...\n\n"+"🚧 "*8+ \
                "\n\nBack to /menu or /done."
            )
        return str(reply)


    async def add_placeholders(self, update, context) -> None:
        """Helper function to create some user_data entries."""
        guild = int(os.getenv("DEFAULT_GUILD"))
        context.user_data["discord roles"] = set()
        context.user_data["discord channels"] = set()
        context.user_data["discord guild"] = guild
        await self.refresh_discord_bot()
        return


    async def start(self, update, context) -> int:
        """Start the conversation, show active notifications & button menu."""

        chat_id = update.message.chat_id
        user_data = context.user_data
        check_keys = ["discord roles", "discord channels", "discord guild"]

        # Add missing user_data keys if not existing yet
        if user_data and not all(x in user_data for x in check_keys):
            # Add missing keys to user data
            await self.add_placeholders(update, context)

        # Possibility: Known user -> show active notifications & button menu
        if user_data:

            # Get current notification triggers from Discord bot
            await self.refresh_discord_bot()
            active_notifications = await self.discord_bot.get_active_notifications(chat_id)

            # Possibility: No notification triggers set yet
            if all(v == set() for v in active_notifications.values()):
                reply_text = (
                    "~~~~~~~~~~~~~~~~~~~~~~\n\n"
                    "There are no notifications from Discord set up currently. "
                    "\n\n~~~~~~~~~~~~~~~~~~~~~~\nPlease choose an option:"
                )
                # Send out message & end it here
                await update.message.reply_text(reply_text, reply_markup=self.markup)
                return self.CHOOSING

            # Possibility: At least one active notification trigger
            reply_text = (
                "~~~~~~~~~~~~~~~~~~~~~~\n\n"
                "Current active notifications:\n"
            )

            reply_text += self.parse_str(active_notifications)

            # Show Discord channel restirictions if any channels are set up
            if user_data["discord channels"] != set():

                reply_text += "\nWill only notify if mentioned in channel"
                if len(user_data["discord channels"]) > 1: reply_text += "s"
                reply_text += f"\n{user_data['discord channels']}\n"

            reply_text += "\n~~~~~~~~~~~~~~~~~~~~~~\n"

        # Possibility: New user -> show explainer & button menu
        else:
            # Add "guild", "roles", "channels" keys to user data
            await self.add_placeholders(update, context)
            await asyncio.sleep(2)    # Prevent KeyErrors with very fast users

            reply_text = (
                "Hello!\n\n"
                "To receive a notification whenever your Discord handle is mentioned,"
                " please select 'Discord handle' from the menu below. "
                " To restrict notifications to certain channels only,"
                " select 'Discord channels'."
                " To receive notifications for mentions of specific roles,"
                " select 'Discord roles'."
                " \n\nPlease choose:"
            )

        # Send out message
        await update.message.reply_text(reply_text, reply_markup=self.markup)
        return self.CHOOSING


    async def discord_handle(self, update, context) -> int:
        """Discord username menu"""

        context.user_data["choice"] = "discord handle"

        # Prompt for Discord handle
        rand_name = random.choice(["tom", "anna", "mia", "max"])
        rand_i = str(random.randint(100,999))
        rand_user = rand_name+"#"+rand_i

        reply_text = (
            f"Please enter your Discord username (i.e. {rand_user}). "
            f"You can find it by tapping your avatar or in settings -> "
            f"my account -> username."
        )
        await update.message.reply_text(reply_text)
        return self.TYPING_REPLY


    async def discord_roles(self, update, context) -> int:
        """Discord roles menu"""

        context.user_data["choice"] = "discord roles"
        guild_id = context.user_data["discord guild"]

        # Possibility: No Discord username is set yet. Forward to username prompt instead.
        if "discord handle" not in context.user_data:
            log("DISCORD HANDLE CHECK: NO KEY FOUND")
            await update.message.reply_text("Please enter a Discord username first!")
            return await self.discord_handle(update, context)

        log("DISCORD HANDLE CHECK: KEY FOUND")
        discord_handle = context.user_data["discord handle"]
        guild_name = await self.discord_bot.get_guild(guild_id)
        roles_available = await self.discord_bot.get_user_roles(discord_handle, guild_id)

        reply_text = f"On {guild_name}, these are the roles which are available to you:"
        reply_text += iter_to_str(roles_available)
        reply_text += (
            f"Please enter the name of a role you would like"
            " to receive notifications for, or hit /menu to go back."
        )
        await update.message.reply_text(reply_text)
        return self.TYPING_REPLY


    async def discord_channels(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""

        context.user_data["choice"] = "discord channels"
        guild_id = context.user_data["discord guild"]
        log(
            f"GOT THIS GUILD ID: {guild_id}"
            f"TYPE: {type(guild_id)}"
        )

        # Possibility: No Discord username is set yet. Forward to username prompt instead.
        if "discord handle" not in context.user_data:
            log("DISCORD HANDLE CHECK: NO KEY FOUND")
            await update.message.reply_text("Please enter a Discord username first!")
            return await self.discord_handle(update, context)

        # Parse message prompting for user input & send out
        log("DISCORD HANDLE CHECK: KEY FOUND")
        guild_name = await self.discord_bot.get_guild(guild_id)
        channels_available = await self.discord_bot.get_channels(guild_id)

        reply_text = f"Available channels on {guild_name}:"
        reply_text += iter_to_str(channels_available)

        if context.user_data["discord channels"] == set():
            reply_text += "Currently you're getting notifications for"
            reply_text += f" all channels on {guild_name}.\n\n"

        else:
            reply_text += "Currently your notifications are restricted to"
            reply_text += f" messages sent on these channels:."
            reply_text += iter_to_str(context.user_data["discord channels"])

        reply_text += (
            f"Hit /menu to leave it at that or alternatively enter a channel from the above"
            " list you would like to restrict the notifications to:"
        )

        await update.message.reply_text(reply_text)
        return self.TYPING_REPLY


    async def discord_guild(self, update, context) -> int:
        """Ask the user for info about the selected predefined choice."""
        context.user_data["choice"] = "discord guild"
        default_guild = int(os.getenv("DEFAULT_GUILD"))

        # Prevent KeyError for new users
        if "discord guild" not in context.user_data:
            context.user_data["discord guild"] = default_guild

        current_guild = int(context.user_data["discord guild"])
        guild_name = await self.discord_bot.get_guild(current_guild)

        reply_text = (
            f"Currently the bot is set up for:\n\n\t*{guild_name.name}*\n\t(ID {str(current_guild)})\n\n"
        )
        if current_guild == default_guild: reply_text += "This is the default setup. "
        reply_text += (
            "To change, please enter a valid Discord guild ID ( = server ID)."
            " See [instructions](https://support.discord.com/hc/en-us/articles/"
            "206346498-Where-can-I-find-my-User-Server-Message-ID-) for help on finding it."
            "\nOr hit /menu to leave the current guild unchanged."
        )

        await update.message.reply_text(
            reply_text,
            disable_web_page_preview=True,
            parse_mode="Markdown")

        return self.TYPING_REPLY


    async def delete_my_data(self, update, context) -> int:
        """Deletes user entry from pickle file, context & Discord bot's triggers."""

        if context.user_data == {}:

            reply_text = (
                "There's nothing here to be deleted yet!"
                " Back to /menu"
            )
        else:
            await update.message.reply_text("Please wait...")
            for k in context.user_data.copy().keys():
                del context.user_data[k]

            reply_text = (
                f"Data successfully wiped! "
                f"Hit /menu to start over."
            )

            # Refresh Discord bot to propagate changes
            await self.refresh_discord_bot()
            await asyncio.sleep(2.5)

        # Notify user
        await update.message.reply_text(reply_text)
        return ConversationHandler.END


    async def received_information(self, update, context) -> int:
        """
        Checks if info provided by user points to existing data on Discord.
        Stores information if valid, requests re-entry if not.
        """

        text = update.message.text
        category = context.user_data["choice"]
        guild_id = context.user_data["discord guild"]
        guild_name = await self.discord_bot.get_guild(guild_id)

        # Check if user-entered data exists on Discord
        if category == "discord handle":
            check = await self.discord_bot.get_user(guild_id, text)

        elif category == "discord channels":
            channels_available = await self.discord_bot.get_channels(guild_id)
            check = True if text in channels_available else None

        elif category == "discord guild":
            if text.isdigit():
                check = await self.discord_bot.get_guild(int(text))
            else:
                check = None    # Guild ID has to consist of numbers only

        elif category == "discord roles":
            roles = await self.discord_bot.get_guild_roles(guild_id)
            check = True if text in roles else None

        else:
            check = True

        # If invalid data -> Repeat prompt with notice.
        if check == None:

            if category == "discord guild":
                reply_text = (
                    f"No guild found on Discord with ID {text}."
                    " Please make sure the entered ID is correct and the bot"
                    " has been [added to the Discord guild](https://www.howtogeek.com/"
                    "744801/how-to-add-a-bot-to-discord/) using [this](https://discord."
                    "com/oauth2/authorize?client_id=1031609181700104283&scope=bot&permissions"
                    "=1024) invite link."
                )

            else:
                guild_name = await self.discord_bot.get_guild(guild_id)
                reply_text = f"{text} doesn't seem to exist on {guild_name}."

            if category == "discord channels":
                reply_text += f" Please choose a text channel from this list or go back to /menu."
                reply_text += iter_to_str(channels_available)

            else:
                cat = category.replace("discord", "Discord").rstrip("s")
                reply_text += f"\nPlease enter a valid {cat} or go back to /menu."

            await update.message.reply_text(
                reply_text,
                disable_web_page_preview=True,
                parse_mode="Markdown"
                )

            return self.TYPING_REPLY

        # If valid data -> Update database with entered information

        # Possibility: No entry yet under this key -> Create entry if in allow_list
        allow_list = ["discord handle", "discord guild"]
        if (category not in context.user_data) and (category in allow_list):
            log(f"received_information():\tPOSSIBILITY 1: NO KEY FOUND -> CREATE ENTRY")
            context.user_data[category] = text

        # Possibility: Key known & points to set -> Add to set (i.e. for roles, channels)
        elif isinstance(context.user_data[category], set):
            log(f"received_information():\tPOSSIBILITY 2: ADD TO SET")
            context.user_data[category].add(text)

        # Possibility: Key known & points to anything other than a set -> Overwrite
        else:
            log(f"received_information():\tPOSSIBILITY 3: OVERWRITE OLD VALUE")
            context.user_data[category] = text

        # TODO: If coming from roles or channels: Ask if another should be added
        del context.user_data["choice"]
        log(f"RECEIVED INFORMATION:\n\ntext: {text}\ncategory: {category}")

        # Relay changes to Discord bot
        await self.refresh_discord_bot()

        success_msg = (
            "Success! Your data so far:"
            f"\n{self.parse_str(context.user_data)}\n"
            " If the changes don't show up under 'Current active notifications'"
            " yet, please allow the bot about 30s, then hit /menu again."
        )

        await update.message.reply_text(success_msg, reply_markup=self.markup)
        return await self.start(update, context)


    async def show_source(self, update, context) -> None:
        """Display link to github."""
        await update.message.reply_text(
            "Collaboration welcome! -> [github](https://github.com/jediswaplabs/discord-alert-bot)"
            "\nBack to /menu or /done.",
            parse_mode="Markdown"
        )


    async def done(self, update, context) -> int:
        """Display the gathered info and end the conversation."""
        user_data = context.user_data

        if "choice" in user_data:
            del user_data["choice"]

        await update.message.reply_text(
            "Bring back the /menu anytime!",
            reply_markup=ReplyKeyboardRemove(),
        )

        return ConversationHandler.END


    async def refresh_discord_bot(self) -> None:
        """Needs to be called for changes of notification settings to take effect."""

        # Update pickle db
        await self.application.update_persistence()
        await asyncio.sleep(1)

        # Reload pickle file in Discord bot & update notification triggers accordingly
        await self.discord_bot.refresh_data()
        log("REFRESHED DISCORD_BOT")


    async def run(self) -> None:
        """Start-up procedure to run TG & Discord bots within the same event loop."""

        # Some config for the application
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
        # Create the application and pass it your bot's token.
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.application = (
            Application.builder().token(token).persistence(persistence).build()
        )

        # Define conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                CommandHandler("menu", self.start),
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
                    )
                ],
                self.TYPING_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~(filters.COMMAND | filters.Regex("^(back|Done|menu)$")),
                        self.received_information
                    ),
                    MessageHandler(
                        filters.Regex("^menu$"),
                        self.start
                    ),
                    MessageHandler(
                        filters.COMMAND,
                        self.start
                    )
                ],
            },
            fallbacks=[
                MessageHandler(
                    filters.Regex("^Done$"),
                    self.done
                ),
                CommandHandler(
                    "menu",
                    self.start
                ),
                CommandHandler(
                    "done",
                    self.done
                )
            ],
            name="my_conversation",
            persistent=False
        )

        # Add additional handlers
        self.application.add_handler(conv_handler)
        show_source_handler = CommandHandler("github", self.show_source)
        self.application.add_handler(show_source_handler)

        # Run application and discord bot simultaneously & asynchronously
        async with self.application:
            await self.application.initialize() # inits bot, update, persistence
            await self.application.start()
            await self.application.updater.start_polling()
            await self.start_discord_bot()
