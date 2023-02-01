#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this file the DiscordBot class is defined. DiscordBot instantiates a
Telegram bot of its own to forward the Discord messages to Telegram.
Messages forwarded using send_to_TG() uses HTML parsing, so the characters
"<", ">", and "&" will be replaced.
"""

import os, discord, logging, json, re
from dotenv import load_dotenv
from telegram import Bot
from pandas import read_pickle
from helpers import return_pretty, log, iter_to_str
load_dotenv()


class DiscordBot:
    """A class to encapsulate all relevant methods of the Discord bot."""

    def __init__(self, debug_mode=False):
        """Constructor of the class. Initializes some instance variables."""

        # Instantiate Telegram bot to send out messages to users
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_bot = Bot(TELEGRAM_TOKEN)
        # Sets of Discord usernames & roles that trigger Telegram notifications
        self.listening_to = {"handles": set(), "roles": set()}
        # Reverse lookup {"handles": {discord username: {telegram id, telegram id}}
        self.discord_telegram_map = {"handles": {}, "roles": {}}
        # Dict to store whitelisted channels per TG_id if user has specified any
        self.channel_whitelist = {}
        # Switch on logging of bot data & callback data (inline button presses) for debugging
        self.debug_mode = debug_mode
        # Dictionary {telegram id: {data}}
        self.users = dict()
        # Path to shared database (data entry via telegram_bot.py)
        self.data_path = "./data"
        self.client = None


    async def refresh_data(self) -> None:
        """Updates from pickle: users, listening_to, discord_telegram_map, channel_whitelist."""

        # Reload database from file. Skip all if no file created yet.
        try:
            self.users = read_pickle(self.data_path)["user_data"]
        except FileNotFoundError:
            return    # Pickle file will be created automatically

        # Wipe listening_to, discord_telegram_map, channel_whitelist
        self.listening_to = {"handles": set(), "roles": set()}
        self.discord_telegram_map = {"handles": {}, "roles": {}}
        self.channel_whitelist = {}

        # Repopulate sets of notification triggers and reverse lookups
        for k, v in self.users.items():
            TG_id = k

            # Add Discord handles to set of notification triggers
            if "discord handle" in v:
                handle = v["discord handle"]
                self.listening_to["handles"].add(handle)
                # Add Discord handle to reverse lookup
                if handle not in self.discord_telegram_map["handles"]:
                    self.discord_telegram_map["handles"][handle] = set()
                self.discord_telegram_map["handles"][handle].add(TG_id)

            # Add Discord roles to set of notification triggers & reverse lookup
            if "discord roles" in v:
                roles = v["discord roles"]

                # Possibility: Only one role set up -> Add it to dicts
                if isinstance(roles, str):
                    role = roles

                    if role not in self.discord_telegram_map["roles"]:
                        self.discord_telegram_map["roles"][role] = set()

                    self.discord_telegram_map["roles"][role].add(TG_id)
                    self.listening_to["roles"].add(role)

                # Possibility: Multiple roles set up -> Add all to dicts
                else:
                    for role in roles:

                        if role not in self.discord_telegram_map["roles"]:
                            self.discord_telegram_map["roles"][role] = set()

                        self.discord_telegram_map["roles"][role].add(TG_id)

                    self.listening_to["roles"].update(roles)

            # Add Discord channels to channel whitelist
            if "discord channels" in v:
                self.channel_whitelist[k] = v["discord channels"]


    async def send_to_TG(self, telegram_user_id, content, line="", header="", signature="", parse_mode='HTML') -> None:
        """
        Sends a message a specific Telegram user id. Escapes some characters.
        Adds dividing lines, header & signature to msg. Defaults to HTML parsing.
        """

        # Escape HTML special characters & add hyperlinks for main part of TG msg

        def add_html_hyperlinks(_str):
            """Adds html hyperlink tags around any url starting with http or https."""
            url_pattern = re.compile(r"""((https://|http://)[^ <>'"{}|\\^`[\]]*)""")
            return url_pattern.sub(r"<a href='\1'>\1</a>", _str)

        # Replace "&" with "&amp;" everywhere
        content = re.sub("&", "&amp;", content)

        # Replace "<" with "&lt;" if not followed by "b>", "i>", "/", or "a"
        lt_not_part_of_tag = "<(?!(b>|i>|/|a))" # negative lookahead
        content = re.sub(lt_not_part_of_tag, "&lt;", content)

        # Replace ">" with "&gt;" if not preceded by "b", "i", "a", or "'"
        gt_not_part_of_tag = "(?<!(b|i|a|'))>" # negative lookbehind
        content = re.sub(gt_not_part_of_tag, "&gt;", content)

        # Convert urls to hyperlinks & concatenate msg back together
        content = add_html_hyperlinks(content)

        parsed_msg = line+header+content+"\n"+line+signature

        await self.telegram_bot.send_message(
            chat_id=telegram_user_id,
            text=parsed_msg,
            disable_web_page_preview=True,
            parse_mode=parse_mode
            )

        if self.debug_mode:
            log(f"FORWARDED A MESSAGE!")


    async def send_to_all(self, content, **kwargs) -> None:
        """Sends a message to all Telegram bot users except if they wiped their data."""
        TG_ids = [k for k, v in self.users.items() if v != {}]
        for _id in TG_ids:
            await self.send_to_TG(_id, content, **kwargs)


    async def get_guild(self, guild_id) -> discord.Guild:
        """Takes guild id, [converts to int,] returns guild object or None if not found."""
        if isinstance(guild_id, str):
            if guild_id.isdigit():
                guild_id = int(guild_id)
        return self.client.get_guild(guild_id)


    async def get_channel(self, guild_id, channel_id) -> discord.abc.GuildChannel:
        """Takes channel id, returns channel object or None if not found."""
        guild = await self.get_guild(guild_id)
        return guild.get_channel(channel_id)


    async def get_user(self, guild_id, username) -> discord.User:
        """Takes guild id & username, returns user object or None if not found."""
        guild = await self.get_guild(guild_id)
        return guild.get_member_named(username)


    async def get_user_id(self, guild_id, username) -> str:
        """Takes guild id & username, str(<Discord ID>)."""
        user = await self.get_user(guild_id, username)
        return user.id


    async def get_guild_roles(self, guild_id) -> list:
        """Takes guild id returns list of names of all roles on guild."""
        guild = await self.get_guild(guild_id)
        return [x.name for x in guild.roles]


    async def get_user_roles(self, discord_username, guild_id) -> list:
        """Takes a Discord username, returns all user's role names in current guild."""
        guild = await self.get_guild(guild_id)
        user = guild.get_member_named(discord_username)
        roles = [role.name for role in user.roles]
        return roles


    async def get_channels(self, guild_id) -> list:
        """Takes a guild ID, returns subset of text channel names of this guild."""

        out_channels = []
        guild = await self.get_guild(guild_id)
        channels = guild.channels

        # Only show channels from welcome, community & contribute categories
        allowed_channel_categories = json.loads(os.getenv("ALLOWED_CHANNEL_CATEGORIES"))

        # Filter out anything but text channels + anything specified here:
        filter_out = ["ticket", "closed"]
        for channel in channels:
            if "text" in channel.type and not any(x in channel.name for x in filter_out):
                if channel.category_id in allowed_channel_categories:
                    out_channels.append(channel.name)

        return out_channels


    def get_listening_to(self, TG_id) -> dict:
        """Takes a TG username, returns whatever this user gets notifications for currently."""
        _map = self.discord_telegram_map
        handles_active = {k for k, v in _map["handles"].items() if TG_id in v}
        roles_active = {k for k, v in _map["roles"].items() if TG_id in v}
        return {"handles": handles_active, "roles": roles_active}


    async def get_active_notifications(self, TG_id) -> dict:
        """
        Returns a dictionary of type {category_1: {triggers}, category_2: ...}
        for all Discord triggers the bot is currently listening to for this
        Telegram user.
        """
        lookup = self.discord_telegram_map

        d = {category: set() for category in lookup}

        # Add all triggers containing this Telegram id to their respective category in d
        for category, trigger_dict in lookup.items():
            for trigger, id_set in trigger_dict.items():
                if TG_id in id_set:
                    d[category].add(trigger)
        return d


    async def run_bot(self) -> None:
        """Actual logic of the bot is stored here."""

        # Update data to listen to at startup
        await self.refresh_data()

        # Fire up discord client
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        client = self.client

        # Divider & signature appended to every notification
        line = "\n"+("~"*22)+"\n"
        signature = "| <i>back to /menu</i> |"

        # Actions taken at startup
        @client.event
        async def on_ready():

            log(f"{client.user.name} has connected to Discord")

        # Actions taken for every new Discord message
        @client.event
        async def on_message(message):

            # If message in non-deactivatable channel -> Forward to everyone known to TG bot
            always_active_channels = json.loads(os.getenv("ALWAYS_ACTIVE_CHANNELS"))
            always_active_channels = [int(x) for x in always_active_channels]
            channel_id = message.channel.id

            if channel_id in always_active_channels:
                channel = message.channel.name

                if self.debug_mode:
                    log(f"MSG IN ALWAYS ACTIVE CHANNEL ({channel}). SENT TO EVERYONE.")

                content = message.content[message.content.find(">")+1:]
                url = message.jump_url
                header = f"\nMessage in <a href='{url}'>{channel}</a>:\n\n"

                await self.send_to_all(
                    content,
                    line=line,
                    header=header,
                    signature=signature
                )

                return    # -> Skip every other case


            # If no user mentions in message -> Skip this part
            if message.mentions != []:

                if self.debug_mode: log(f"{len(message.mentions)} USER MENTIONS IN {message.channel.name}.")

                channel = message.channel.name
                whitelist = self.channel_whitelist

                # User mentions: Forward to TG as specified in lookup dict
                for username in self.listening_to["handles"]:
                    user = message.guild.get_member_named(username)

                    # Cycle through all user mentions in message
                    if user in message.mentions:

                        if self.debug_mode: log(f"USER IN MENTIONS: {username} mentioned.")

                        author, guild, channel = message.author, message.guild, message.channel.name
                        alias, url = user.display_name, message.jump_url
                        content = message.content[message.content.find(">")+1:]
                        if author.nick: author = author.nick
                        header = f"\nMentioned by {author} in {guild.name} in <a href='{url}'>{channel}</a>:\n\n"

                        # Cycle through all TG ids connected to this Discord handle
                        for _id in self.discord_telegram_map["handles"][username]:

                            target_guild_id = self.users[_id]["discord guild"]

                            if self.debug_mode:
                                log(
                                    f"GUILD CHECK: {type(guild.id)} {guild.id} =="
                                    f" {type(target_guild_id)} {target_guild_id}:"
                                    f" {guild.id == target_guild_id}"
                                )

                            # Condition 1: User Discord is verified
                            if self.users[_id]["verified discord"]:

                                # Condition 2: msg guild matches guild set up by user
                                if guild.id == target_guild_id:

                                    if self.debug_mode:
                                        log(
                                            f"CHANNEL CHECK: {channel} in whitelist:"
                                            f" {channel in whitelist[_id]}\n"
                                            f"SET UP CHANNELS: {whitelist[_id]}"
                                        )

                                    # Condition 3: Channel matches or no channels set up
                                    if whitelist[_id] == set():

                                        await self.send_to_TG(
                                            _id,
                                            content,
                                            line=line,
                                            header=header,
                                            signature=signature
                                        )

                                    else:

                                        if channel in whitelist[_id]:

                                            await self.send_to_TG(
                                                _id,
                                                content,
                                                line=line,
                                                header=header,
                                                signature=signature
                                            )

                            else:
                                if self.debug_mode: log(f"UNVERIFIED DISCORD: {_id}. NO HANDLE NOTIFICATION SENT.")


            # If no role mentions in message -> Skip this part
            if message.role_mentions != [] or message.mention_everyone:

                if self.debug_mode: log(f"ROLE MENTIONS IN MESSAGE: {message.role_mentions}")

                channel = message.channel.name
                whitelist = self.channel_whitelist
                rolenames = [x.name for x in message.role_mentions]

                # Add in mention of @everyone as role mention
                if message.mention_everyone:
                    rolenames.append('@everyone')

                # Role mentions: Forward to TG as specified in lookup dict
                for role in self.listening_to["roles"]:

                    if role in rolenames:

                        if self.debug_mode: log(f"MATCHED A ROLE: {role} mentioned.")

                        author, guild, url = message.author, message.guild, message.jump_url
                        channel = message.channel.name
                        content = message.content[message.content.find(">")+1:]
                        header = f"{role} mentioned in <a href='{url}'>{channel}</a>:\n\n"

                        # Cycle through all TG ids connected to this Discord role
                        for _id in self.discord_telegram_map["roles"][role]:

                            target_guild_id = self.users[_id]["discord guild"]

                            if self.debug_mode:
                                log(
                                    f"GUILD CHECK: {guild.id} == {target_guild_id}:"
                                    f" {guild.id == target_guild_id}"
                                )

                            # Condition 1: User Discord is verified
                            if self.users[_id]["verified discord"]:

                                # Condition 2: msg guild matches guild set up by user
                                if guild.id == target_guild_id:
                                    if self.debug_mode:
                                        log(
                                            f"CHANNEL CHECK: {type(channel)} {channel} in"
                                            f" {whitelist[_id]}: {channel in whitelist[_id]}\n"
                                            f"SET UP CHANNELS: {whitelist[_id]}"
                                        )

                                    # Condition 3: Channel matches or no channels set up
                                    if whitelist[_id] == set():

                                        await self.send_to_TG(
                                            _id,
                                            content,
                                            line=line,
                                            header=header,
                                            signature=signature
                                        )

                                    else:

                                        if channel in whitelist[_id]:

                                            await self.send_to_TG(
                                                _id,
                                                content,
                                                line=line,
                                                header=header,
                                                signature=signature
                                            )
                            else:
                                if self.debug_mode: log("UNVERIFIED DISCORD. NO ROLE NOTIFICATION SENT.")

        DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        await client.start(DISCORD_TOKEN)
