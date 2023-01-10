#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this file the DiscordBot class is defined. DiscordBot instantiates a
Telegram bot of its own to forward the Discord messages to Telegram.
"""

import os, discord, logging, json
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
        # Set of Discord usernames & roles that trigger Telegram notifications
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

        if self.debug_mode:
            log(
                f"\nlistening_to:\t\t{self.listening_to}"
                f"\ndiscord_telegram_map:\t{self.discord_telegram_map}"
                f"\nchannel_whitelist:\t{self.channel_whitelist}"
            )

    async def send_to_TG(self, telegram_user_id, msg, parse_mode='Markdown') -> None:
        """
        Sends a message a specific Telegram user id.
        Defaults to Markdown V1 for inline link capability.
        """
        signature = "| _back to /menu_ |"
        escape_d = {
            '.': '\.',
            '!': '\!',
            '-': '\-',
            '#': '\#',
            '>': '\>',
            '<': '\<',
            '.': '\.',
            '_': '\_',
            '`': '\`',
            '*': '*',
        }

        # Escape markdown characters for main part of TG msg
        header_end = msg.find("):\n")

        no_header = msg[header_end+2:]
        footer_start = no_header.find(22*"~")
        discord_content = no_header[:footer_start]

        header = msg[:header_end+2]
        footer = no_header[footer_start:]
        escaped_msg = discord_content.translate(msg.maketrans(escape_d))

        msg = header + escaped_msg + footer

        await self.telegram_bot.send_message(
            chat_id=telegram_user_id,
            text=msg,
            disable_web_page_preview=True,
            parse_mode=parse_mode
            )


    async def send_to_all(self, msg) -> None:
        """Sends a message to all Telegram bot users except if they wiped their data."""
        TG_ids = [k for k, v in self.users.items() if v != {}]
        for _id in TG_ids:
            await self.send_to_TG(_id, msg)


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
        signature = "| _back to /menu_ |"

        # Actions taken at startup
        @client.event
        async def on_ready():

            log(f"{client.user.name} has connected to Discord")

        # Actions taken for every new Discord message
        @client.event
        async def on_message(message):

            if self.debug_mode == 'messages':
                log(
                    f"Discord message: {message}\n"
                    f"message.channel.name: {message.channel.name}\n"
                    f"message.mentions: {message.mentions}\n"
                    f"message.role_mentions: {message.role_mentions}\n"
                    f"message.channel_mentions: {message.channel_mentions}\n"
                    f"message.embeds: {message.embeds}\n"
                    f"message.flags: {message.flags}\n"
                    f"message.attachments: {message.attachments}\n"
                )

            line = "\n"+("~"*22)+"\n"

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

                        if self.debug_mode: log(f"USER IN MENTIONS: {message.author} mentioned {username}")

                        author, guild, channel = message.author, message.guild, message.channel.name
                        alias, url = user.display_name, message.jump_url
                        contents = message.content[message.content.find(">")+1:]
                        if author.nick: author = author.nick
                        header = f"\nMentioned by {author} in {guild.name} in [{channel}]({url}):\n\n"
                        out_msg = line+header+contents+"\n"+line+signature

                        # Cycle through all TG ids connected to this Discord handle
                        for _id in self.discord_telegram_map["handles"][username]:

                            target_guild_id = self.users[_id]["discord guild"]

                            if self.debug_mode:
                                log(
                                    f"GUILD CHECK: {type(guild.id)} {guild.id} =="
                                    f" {type(target_guild_id)} {target_guild_id}:"
                                    f" {guild.id == target_guild_id}"
                                )

                            # Condition 1: msg guild matches guild set up by user
                            if guild.id == target_guild_id:

                                if self.debug_mode:
                                    log(
                                        f"CHANNEL CHECK: {type(channel)} {channel} in"
                                        f" {whitelist[_id]}: {channel in whitelist[_id]}\n"
                                        f"SET UP CHANNELS: {whitelist[_id]}"
                                    )

                                # Condition 2: Channel matches or no channels set up
                                if whitelist[_id] == set():
                                    await self.send_to_TG(_id, out_msg)
                                else:
                                    if channel in whitelist[_id]:
                                        await self.send_to_TG(_id, out_msg)


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

                        if self.debug_mode: log(f"MATCHED A ROLE: {message.author} mentioned {role}")

                        author, guild, url = message.author, message.guild, message.jump_url
                        channel = message.channel.name
                        contents = message.content[message.content.find(">")+1:]
                        header = f"{role} mentioned in {guild.name} in [{channel}]({url}):\n\n"
                        out_msg = line+header+contents+"\n"+line+signature

                        # Cycle through all TG ids connected to this Discord role
                        for _id in self.discord_telegram_map["roles"][role]:

                            target_guild_id = self.users[_id]["discord guild"]

                            if self.debug_mode:
                                log(
                                    f"GUILD CHECK: {type(guild.id)} {guild.id} =="
                                    f" {type(target_guild_id)} {target_guild_id}:"
                                    f" {guild.id == target_guild_id}"
                                )

                            # Condition 1: msg guild matches guild set up by user
                            if guild.id == target_guild_id:

                                log(
                                    f"CHANNEL CHECK: {type(channel)} {channel} in"
                                    f" {whitelist[_id]}: {channel in whitelist[_id]}\n"
                                    f"SET UP CHANNELS: {whitelist[_id]}"
                                )

                            # Condition 2: Channel matches or no channels set up
                            if whitelist[_id] == set():
                                await self.send_to_TG(_id, out_msg)
                            else:
                                if channel in whitelist[_id]:
                                    await self.send_to_TG(_id, out_msg)


        DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        await client.start(DISCORD_TOKEN)
