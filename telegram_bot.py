#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, wrong-import-position
"""
In this file, the TelegramBot class is defined. Usage:
Send /start to initiate the conversation on Telegram. Press Ctrl-C on the
command line to stop the bot.
"""

import logging, os, random, asyncio
from helpers import log, iter_to_str, return_pretty
from pandas import read_pickle
from typing import Dict, Union, List
from dotenv import load_dotenv
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    PersistenceInput,
    filters,
)

load_dotenv("./.env")
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


class TelegramBot:
    """A class to encapsulate all relevant methods of the Telegram bot."""

    def __init__(self, discord_bot_instance, debug_mode=False):
        """
        Constructor of the class. Initializes certain instance variables.
        """
        # The single data file the bot is using
        self.data_path = "./data"
        # Discord bot instance
        self.discord_bot = discord_bot_instance
        # Switch on logging of bot data & callback data (inline button presses) for debugging
        self.debug_mode = debug_mode
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


    async def add_placeholders(self, update, context) -> None:
        """Create new user if not in database yet."""

        context.user_data["discord roles"] = set()
        context.user_data["discord channels"] = set()
        context.user_data["discord guild"] = int(os.getenv("DEFAULT_GUILD"))
        context.user_data["last callback"] = None
        context.user_data["verified discord"] = False
        context.user_data["discord id"] = None

        await self.refresh_discord_bot()
        return


    async def send_msg(self, msg, update, **kwargs) -> None:
        """Wrapper function to send out messages in all conditions."""

        if update.message:
            await update.message.reply_text(msg, **kwargs)
        else:
            await update._bot.send_message(update.effective_message.chat_id, msg, **kwargs)




    async def verify_discord(self, user_id, update, context) -> None:
        """
        Redirect user to Oauth2 verification page. Result can be fetched
        from inline callback data.
        """
        user_data = context.user_data
        # If no handle set: Notify and return
        if "discord handle" not in user_data:
            self.discord_handle(self, update, context)

        # Else: Get user id, put link together and redirect to Discord auth page.
        # Convert to str if necessary
        if isinstance(user_id, int):
            user_id = str(user_id)

        return




    async def start(self, update, context) -> int:
        """Start the conversation, show active notifications & button menu."""

        # TODO: Remove
        log(update)
        log(context)

        chat_id = update.message.chat_id if update.message else context._chat_id
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
                await self.send_msg(reply_text, update, reply_markup=self.markup)
                return self.CHOOSING

            # Possibility: At least one active notification trigger
            reply_text = (
                "~~~~~~~~~~~~~~~~~~~~~~\n\n"
                "Current active notifications:\n"
            )

            reply_text += self.parse_str(active_notifications).replace('handles', 'Handle').replace('roles', 'Roles')

            # Show Discord channel restirictions if any channels are set up
            if user_data["discord channels"] != set():

                reply_text += "\nWill only notify if mentioned in channel"
                if len(user_data["discord channels"]) > 1: reply_text += "s"
                reply_text += f"\n{user_data['discord channels']}\n"

            # Show Discord verification status
            if user_data["verified discord"]:
                reply_text += "Discord _*verified*_."
            else:
                reply_text += (
                    "\nDiscord _*unverified*_! "
                    "Please /verify to enable notifications!"
                )

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
                " To customize role notifications,"
                " select 'Discord roles'."
                " \n\nPlease choose:"
            )

        # Send out message
        await self.send_msg(reply_text, update, reply_markup=self.markup)
        return self.CHOOSING


    def build_button_menu(
        self,
        buttons: List[InlineKeyboardButton],
        n_cols: int,
        header_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None,
        footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]]=None
    ) -> List[List[InlineKeyboardButton]]:
        """Helper function. Returns an inline button menu from a list of buttons."""

        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]

        if header_buttons:
            menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
        if footer_buttons:
            menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])

        return menu


    async def inline_submenu(self, update, context) -> int:
        """A dynamic second button menu based on user's choice in main menu."""

        # Save category chosen by user for further conversation flow
        context.user_data["choice"] = update.message.text
        category = context.user_data["choice"].lower()
        button_list = []

        if self.debug_mode:
            log(f"GOT CATEGORY IN inline_submenu(): {category}")

        if category == "discord roles":
            buttons = ["Add roles", "Remove roles", "Back"]

        elif category == "discord channels":
            buttons = ["Add channels", "Remove channels", "Back"]

        button_list = [InlineKeyboardButton(x, callback_data=x) for x in buttons]
        reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

        await self.send_msg("Please choose:", update, reply_markup=reply_markup)

        return self.CHOOSING


    async def discord_handle(self, update, context) -> int:
        """Discord username menu."""

        context.user_data["choice"] = "discord handle"

        # Prompt for Discord handle
        rand_name = random.choice(["tom", "anna", "mia", "max"])
        rand_i = str(random.randint(100,999))
        rand_user = rand_name+"#"+rand_i

        reply_text = (
            f"Please enter your Discord username with or without the discriminator "
            f"(i.e. {rand_name} or {rand_user}). "
            f"You can find it by tapping your avatar or in settings -> "
            f"my account -> username. "
            f"Hit /menu to go back."
        )
        await self.send_msg(reply_text, update)
        return self.TYPING_REPLY


    async def roles_menu(self, update, context) -> int:
        """Discord roles main menu."""

        if self.debug_mode and not update.callback_query:
            log(f"ARRIVED AT roles_menu() WITH EMPTY CALLBACK")

        context.user_data["choice"] = "discord roles"
        guild_id = context.user_data["discord guild"]
        discord_handle = context.user_data["discord handle"]
        guild_name = await self.discord_bot.get_guild(guild_id)
        active_roles = context.user_data["discord roles"]
        roles_available = await self.discord_bot.get_user_roles(discord_handle, guild_id)

        callback_data = update.callback_query.data


        if active_roles == set():
            reply_text = "There are no role notifications set up yet. "

        else:
            reply_text = "Currently, you are receiving notifications for these roles:"
            reply_text += iter_to_str(active_roles)

        # Adding a role
        if callback_data == "Add roles":

            other_roles = set(roles_available) - active_roles

            if other_roles == set():

                reply_text = "All your roles have notifications enabled currently! "
                reply_text += "Please choose:"

                buttons = [("Remove roles", "Remove roles"), ("Back", "Back")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return


            else:
                reply_text = f"On {guild_name}, these roles are available to you:"
                reply_text += iter_to_str(other_roles)
                reply_text += (
                    f"Please enter the name of a role you would like"
                    " to receive notifications for, or hit /menu to go back."
                )

        # Removing a role
        elif callback_data == "Remove roles":

            if active_roles == set():

                reply_text += "Please choose:"
                buttons = [("Add a role", "Add roles"), ("Back", "Back")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return

            else:
                reply_text += (
                    f"Please enter the name of a role you would like"
                    " to deactivate notifications for, or hit /menu to go back."
                )

        # Send back to main menu if callback not recognized
        else:
            if self.debug_mode: log(f"REDIRECTED TO MENU: CALLBACK DATA = {callback_data}")
            return await self.start(update, context)

        # Prompt for user input
        await update.callback_query.message.edit_text(reply_text)

        return self.TYPING_REPLY


    async def channels_menu(self, update, context) -> int:
        """Discord channels main menu."""

        if self.debug_mode and not update.callback_query:
            log(f"ARRIVED AT channels_menu() WITH EMPTY CALLBACK")

        context.user_data["choice"] = "discord channels"
        guild_id = context.user_data["discord guild"]
        discord_handle = context.user_data["discord handle"]
        guild_name = await self.discord_bot.get_guild(guild_id)
        active_channels = context.user_data["discord channels"]
        channels_available = await self.discord_bot.get_channels(guild_id)

        if self.debug_mode:
            log(
                f"channels_menu(): CHANNELS_AVAILABLE: {channels_available}\n"
                f"channels_menu(): ACTIVE_CHANNELS: {active_channels}"
            )

        callback_data = update.callback_query.data

        if active_channels == set():
            reply_text = "Currently your notifications are not restricted to any specific channels. "

        else:
            reply_text = "Currently your notifications are restricted to this subset of channels:"
            reply_text += iter_to_str(active_channels)

        # Adding a channel
        if callback_data == "Add channels":

            other_channels = set(channels_available) - active_channels

            if other_channels == set():

                reply_text = "You've already added all channels available to you. "
                reply_text += "Please choose:"

                buttons = [("Remove channels", "Remove channels"), ("Back", "Back")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return


            else:
                reply_text = f"Channels on {guild_name}:"
                reply_text += iter_to_str(other_channels)
                reply_text += (
                    f"Please enter the name of a channel you would like"
                    " to add to the subset notifications are active for,"
                    " or hit /menu to go back."
                )

        # Removing a channel
        elif callback_data == "Remove channels":

            if active_channels == set():

                reply_text += "Please choose:"
                buttons = [("Add a channel", "Add channels"), ("Back", "Back")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return

            else:
                reply_text += (
                    f"Please enter the name of a channel you would like"
                    " to remove from the subset you receive notifications for,"
                    " or hit /menu to go back."
                )

        # Send back to main menu if callback not recognized
        else:
            if self.debug_mode: log(f"REDIRECTED TO MENU: CALLBACK DATA = {callback_data}")
            return await self.start(update, context)

        # Prompt for user input
        await update.callback_query.message.edit_text(reply_text)

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
            " Hit /menu to go back and leave the current guild unchanged."
        )
        await self.send_msg(
            reply_text,
            update,
            disable_web_page_preview=True,
            parse_mode="Markdown"
        )

        return self.TYPING_REPLY


    async def delete_my_data(self, update, context) -> int:
        """Deletes user entry from pickle file, context & Discord bot's triggers."""

        if context.user_data == {}:

            reply_text = (
                "There's nothing here to be deleted yet!"
                " Back to /menu"
            )
        else:
            await self.send_msg("Please wait...", update)
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
        await self.send_msg(reply_text, update)
        return ConversationHandler.END


    async def received_information(self, update, context) -> int:
        """
        Stores or removes data entered by user, depending on data, category,
        and callback data, if available.
        """

        text = update.message.text
        category = context.user_data["choice"].lower()
        guild_id = context.user_data["discord guild"]
        guild_name = await self.discord_bot.get_guild(guild_id)
        if "last callback" not in context.user_data: context.user_data["last callback"] = None
        callback_data = context.user_data["last callback"]

        if self.debug_mode:
            log(
                f"received_information() CALLBACK_DATA: {callback_data}\n"
                f"received_information() CATEGORY: {category}\n"
                f"received_information() UPDATE.CALLBACK_QUERY: {update.callback_query}"
            )

        removal_triggers = ("Remove roles", "Remove channels")
        non_removable = ("discord handle", "discord guild", "delete my data")

        # Possibility: User wants to store data, not remove it
        if callback_data not in removal_triggers or category in non_removable:

            # ====================   CASE: STORE DATA   ====================

            # Check if user-entered data exists on Discord
            if category == "discord guild":
                if text.isdigit():    # Convert guild ID to int
                    text = int(text)
                    check = await self.discord_bot.get_guild(text)
                else:
                    check = None    # Guild ID has to consist of numbers only

            elif category == "discord handle":
                check = await self.discord_bot.get_user(guild_id, text)
                # Automatically add user roles if Discord handle exists
                if check != None:
                    roles = await self.discord_bot.get_user_roles(text, guild_id)
                    if roles != []:
                        context.user_data["discord roles"] = set(roles)

            elif category == "discord channels":
                channels_available = await self.discord_bot.get_channels(guild_id)
                check = True if text in channels_available else None


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
                    reply_text += iter_to_str(channels_available)
                    reply_text += f" Please choose a channel from the above list or go back to /menu."

                else:
                    cat = category.replace("discord", "Discord").rstrip("s")
                    reply_text += f" Please enter a valid {cat} or go back to /menu."

                await self.send_msg(
                    reply_text,
                    update,
                    disable_web_page_preview=True,
                    parse_mode="Markdown"
                )

                return self.TYPING_REPLY

            # If valid data -> Update database with entered information

            # Possibility: No entry yet under this key -> Create entry if in allow_list
            allow_list = ["discord handle", "discord guild"]
            if (category not in context.user_data) and (category in allow_list):
                if self.debug_mode: log(f"received_information():\tPOSSIBILITY 1: NO KEY FOUND -> CREATE ENTRY")
                context.user_data[category] = text

            # Possibility: Key known & points to set -> Add to set (i.e. for roles, channels)
            elif isinstance(context.user_data[category], set):
                if self.debug_mode: log(f"received_information():\tPOSSIBILITY 2: ADD TO SET")
                context.user_data[category].add(text)

            # Possibility: Key known & points to anything other than a set -> Overwrite
            else:
                if self.debug_mode: log(f"received_information():\tPOSSIBILITY 3: OVERWRITE OLD VALUE")
                context.user_data[category] = text

            # ====================   POST-STORAGE ACTIONS   ====================

            # If new guild has been set -> wipe roles & channels from old guild
            if category == "discord guild" and check:
                context.user_data["discord roles"] = set()
                context.user_data["discord channels"] = set()

            # If new Discord handle has been set -> store Discord id & send to verification
            if category == "discord handle" and check:
                guild_id = context.user_data["discord guild"]
                handle = text
                user_id = await self.discord_bot.get_user_id(guild_id, handle)
                context.user_data["discord id"] = user_id
                await self.verify_discord(self, str(user_id), update, context)

            # Relay changes to Discord bot
            await self.refresh_discord_bot()

            # Show updated data to user
            ignore_list = ["last callback", "choice", "discord id"]
            show_data = {k: v for k, v in context.user_data.items() if k not in ignore_list}

            success_msg = (
                "Success! Your data so far:"
                f"\n{self.parse_str(show_data)}\n"
                " If the changes don't show up under 'current active notifications'"
                " yet, please allow the bot about 10s, then hit /menu again."
            )

            del context.user_data["choice"]
            await self.send_msg(success_msg, update, reply_markup=self.markup)
            return await self.start(update, context)


        # ====================   CASE: REMOVE DATA   ====================

        # Possibility: User wants to remove a role
        elif callback_data == "Remove roles":

            current_roles = context.user_data["discord roles"]

            if text in current_roles:

                current_roles.remove(text)
                context.user_data["discord roles"] = current_roles

                reply_text = f"\n'{text}' removed.\n"
                reply_text += "Do you want to remove another role?"

                buttons = [("Yes", "Remove roles"), ("No", "success_msg")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return self.CHOOSING

            else:

                reply_text = f"{text} is not in the list."
                reply_text += f" Please choose a role to remove from this list or go back to /menu."
                reply_text += iter_to_str(current_roles)

                await self.send_msg(reply_text, update)

        # Possibility: User wants to remove a channel
        elif callback_data == "Remove channels":

            current_channels = context.user_data["discord channels"]

            if text in current_channels:
                current_channels.remove(text)
                context.user_data["discord channels"] = current_channels

                reply_text = f"\n'{text}' removed.\n"
                reply_text += "Do you want to remove another channel?"
                buttons = [("Yes", "Remove channels"), ("No", "success_msg")]
                button_list = [InlineKeyboardButton(x[0], callback_data=x[1]) for x in buttons]
                reply_markup = InlineKeyboardMarkup(self.build_button_menu(button_list, n_cols=2))

                await self.send_msg(reply_text, update, reply_markup=reply_markup)
                return self.CHOOSING

            else:
                reply_text = f"{text} is not in the list."
                reply_text += f" Please choose a channel to remove from this list or go back to /menu."
                reply_text += iter_to_str(current_channels)

                await self.send_msg(reply_text, update)

        else:
            if self.debug_mode: log(f"UNHANDLED CALLBACK IN received_information: {callback_data}")

        return


    async def received_callback(self, update, context) -> int:
        """Callback logic is stored here. Any inline button will redirect here."""

        category = context.user_data["choice"].lower()
        guild_id = context.user_data["discord guild"]
        guild_name = await self.discord_bot.get_guild(guild_id)
        query = update.callback_query
        callback_data = query.data
        context.user_data["last callback"] = callback_data
        await query.answer()
        # Hide last inline keyboard
        await query.message.edit_reply_markup()

        if self.debug_mode:
            log(
                f"CALLBACK QUERY: {query}\n"
                f"CALLBACK DATA: {callback_data}\n"
                f"CATEGORY: {category}\n"
                f"UPDATE.MESSAGE: {update.message}\n"
                f"UPDATE.CALLBACK_QUERY.MESSAGE: {update.callback_query.message}\n"
                f"UPDATE: {update}"
            )

        # Possibility: User pressed "Back" -> Back to main menu
        if callback_data == "Back":

            await update.callback_query.edit_message_text("Going back to menu...")
            return await self.start(update, context)

        # Possibility: User pressed "No" button in received_information()
        elif callback_data == "success_msg":

            ignore_list = ["last callback", "choice"]
            show_data = {k: v for k, v in context.user_data.items() if k not in ignore_list}

            success_msg = (
                "Success! Your data so far:"
                f"\n{self.parse_str(show_data)}\n"
                " If the changes don't show up under 'current active notifications'"
                " yet, please allow the bot about 10s, then hit /menu again."
            )

            del context.user_data["choice"]

            await update.callback_query.message.edit_text(success_msg)
            return await self.start(update, context)

        # Possibility: User chose "Discord roles" at main menu
        elif category == "discord roles":
            if self.debug_mode: log("category == 'discord roles'")

            # Possibility: No Discord username is set yet. Forward to username prompt instead.
            if "discord handle" not in context.user_data:
                await update.callback_query.message.edit_text("Please enter a Discord username first!")
                return await self.discord_handle(update, context)

            return await self.roles_menu(update, context)

        # Possibility: User chose "Discord channels" at main menu
        elif category == "discord channels":
            if self.debug_mode: log("category == 'discord channels'")

            # Possibility: No Discord username is set yet. Forward to username prompt instead.
            if "discord handle" not in context.user_data:
                await update.callback_query.message.edit_text("Please enter a Discord username first!")
                return await self.discord_handle(update, context)# TODO: Check with deleted user if this works!

            return await self.channels_menu(update, context)

        # Any undefined button will fall back to the main menu
        else:
            if self.debug_mode: log(f"received_callback(): UNHANDLED CALLBACK DATA: {callback_data}")
            return await self.start(update, context)

        # TODO: Catch callback data from Discord oauth2
        #       If user_id matches stored user_id:
        #       context.user_data["verified discord"] = True
        #       call start()


    async def show_source(self, update, context) -> None:
        """Display link to github."""
        await self.send_msg(
            "Collaboration welcome! -> [github](https://github.com/jediswaplabs/discord-alert-bot)"
            "\nBack to /menu or /done.",
            update,
            parse_mode="Markdown"
        )
        return ConversationHandler.END


    async def debug(self, update, context) -> None:
        """Display some quick bot data for debugging."""

        chat_id = update.message.chat_id if update.message else context._chat_id
        debug_id = int(os.environ["DEBUG_ID"])

        if chat_id == debug_id:

            guild_id = context.user_data["discord guild"]
            guild = await self.discord_bot.get_guild(guild_id)
            filter_out = ["category", "news", "forum"]

            all_channels = [x for x in guild.channels if not any(w in x.type for w in filter_out)]
            all_channels = [x for x in all_channels if "ticket" not in x.name]
            all_channels = [x for x in all_channels if x.category_id == 852459762640486400]

            devs_channel = guild.get_channel(860920370764840990)
            bot_role = guild.get_role(1055915585332056076)
            contributors_channel = guild.get_channel(852459854844395540)

            bot = guild.get_member(1031609181700104283)
            bot_channels = [x.name for x in all_channels if bot in x.members]

            msg = ""
            msg = (
                f"\nBot roles: {[x.name for x in guild.get_member(1031609181700104283).roles]}\n"
                f"\nThreads visible to bot under devs channel: {[x.name for x in devs_channel.threads]}\n"
                f"\nThreads visible to bot under contributors channel: {[x.name for x in contributors_channel.threads]}\n"
                f"\nBot is member of channels:\n{bot_channels}"
                f"\n\n/menu  |  /done  |  /github"
            )

            await self.send_msg(msg, update)
            return ConversationHandler.END


    async def done(self, update, context) -> int:
        """Display the gathered info and end the conversation."""
        user_data = context.user_data

        if "choice" in user_data:
            del user_data["choice"]

        await self.send_msg(
            "Bring back the /menu anytime!",
            update,
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

        if self.debug_mode:
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
                    MessageHandler(filters.Regex("^Discord guild$"),
                        self.discord_guild
                    ),
                    MessageHandler(filters.Regex("^Delete my data$"),
                        self.delete_my_data
                    ),
                    MessageHandler(filters.Regex("^(Discord channels|Discord roles)$"),
                        self.inline_submenu
                    ),
                    CallbackQueryHandler(self.received_callback),

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
                    ),
                    CallbackQueryHandler(self.received_callback),
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
            persistent=False,
        )

        # Add additional handlers
        self.application.add_handler(conv_handler)

        auth_handler = CommandHandler("verify", self.verify_discord)
        show_source_handler = CommandHandler("github", self.show_source)
        debug_handler = CommandHandler("debug", self.debug)

        self.application.add_handler(auth_handler)
        self.application.add_handler(show_source_handler)
        self.application.add_handler(debug_handler)

        # Run application and discord bot simultaneously & asynchronously
        async with self.application:
            await self.application.initialize() # inits bot, update, persistence
            await self.application.start()
            await self.application.updater.start_polling()
            await self.start_discord_bot()
