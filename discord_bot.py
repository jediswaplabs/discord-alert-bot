#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
In this file the DiscordBot class is defined. DiscordBot instantiates a
telegram bot of its own to forward the Discord messages to Telegram.
"""

import os, discord, logging
from dotenv import load_dotenv
from telegram import Bot
from pandas import read_pickle
from helpers import return_pretty, log
load_dotenv()


class DiscordBot:
    """A class to encapsulate all relevant methods of the Discord bot."""

    def __init__(self):
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

        log('discord_bot.refresh_data(self): self.users right now:', self.users)

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

            # Add Discord roles to set of notification triggers
            if "discord roles" in v:
                roles = v["discord roles"]
                self.listening_to["roles"].update(roles)
                # Add Discord roles to reverse lookup
                for role in roles:
                    if role not in self.discord_telegram_map["roles"]:
                        self.discord_telegram_map["roles"][role] = set()
                    self.discord_telegram_map["roles"][role].add(TG_id)

            # Add Discord channels to channel whitelist
            if "discord channels" in v:
                self.channel_whitelist[k] = v["discord channels"]

        log(
            f"\nDATA READ FROM PICKLE FILE:\n{self.users}\n\n"
            f"\nlistening_to:\t\t{self.listening_to}"
            f"\ndiscord_telegram_map:\t{self.discord_telegram_map}"
            f"\nchannel_whitelist:\t{self.channel_whitelist}\n"
        )

    async def send_to_TG(self, telegram_user_id, msg, parse_mode='Markdown') -> None:
        """
        Sends a message a specific Telegram user id.
        Defaults to Markdown V1 for inline link capability.
        """
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
        log(f"get_user_roles(): Got these roles for {discord_username}: {roles}")

        return roles


    async def get_channels(self, guild_id) -> list:
        """Takes a guild ID, returns all text channel names of this guild."""
        out_channels = []
        guild = await self.get_guild(guild_id)
        channels = guild.channels

        # Filter out anything but text channels
        for channel in channels:
            if channel.category:
                if channel.category.name == 'Text Channels':
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

        # Actions taken at startup
        @client.event
        async def on_ready():

            log(f"{client.user.name} has connected to Discord")
            msg = "Discord bot is up & running!\nHit /menu to begin."
            #await self.send_to_all(msg)

        # Actions taken for every new Discord message
        @client.event
        async def on_message(message):

            log(f"Discord message -> {message}")
            log(f"message.mentions -> {message.mentions}")
            log(f"message.channel.name -> {message.channel.name}")
            line = "\n"+("~"*22)+"\n"

            # If no user mentions in message -> Skip this part
            if message.mentions != []:

                log(f"USER MENTIONS IN MESSAGE: {message.mentions}")
                channel = message.channel.name
                whitelist = self.channel_whitelist

                # User mentions: Forward to TG as specified in lookup dict
                for username in self.listening_to["handles"]:

                    user = message.guild.get_member_named(username)

                    if user in message.mentions:
                        log(f"USER IN MENTIONS: {message.author} mentioned {username}")
                        author, guild_name = message.author, message.guild.name
                        alias, url = user.display_name, message.jump_url
                        contents = message.content[message.content.find(">")+1:]
                        header = f"\nMentioned by {author} in {guild_name}:\n\n"
                        out_msg = line+header+contents+"\n"+line
                        TG_ids = self.discord_telegram_map["handles"][username]

                        # Forward to user if no channels are specified or channel is in whitelist
                        for _id in TG_ids:
                            if whitelist[_id] == set():
                                await self.send_to_TG(_id, out_msg)
                            else:
                                if channel in whitelist[_id]:
                                    await self.send_to_TG(_id, out_msg)


            # If no role mentions in message -> Skip this part
            if message.role_mentions != []:

                log(f"ROLE MENTIONS IN MESSAGE: {message.role_mentions}")
                channel = message.channel.name
                whitelist = self.channel_whitelist
                rolenames = [x.name for x in message.role_mentions]

                # Role mentions: Forward to TG as specified in lookup dict
                for role in self.listening_to["roles"]:

                    if role in rolenames:

                        log(f"MATCHED A ROLE: {message.author} mentioned {role}")
                        author, guild_name = message.author, message.guild.name
                        contents = message.content[message.content.find(">")+1:]
                        header = f"Message to {role} in {guild_name}:\n\n"
                        out_msg = line+header+contents+"\n"+line
                        TG_ids = self.discord_telegram_map["roles"][role]

                        # Forward to user if no channels are specified or channel is in whitelist
                        for _id in TG_ids:
                            if whitelist[_id] == set():
                                await self.send_to_TG(_id, out_msg)
                            else:
                                if channel in whitelist[_id]:
                                    await self.send_to_TG(_id, out_msg)

                # DONE: Have bot also check for mentioned roles
                # DONE: Less logging
                # DONE: Have bot listen to specified subset of channels only
                # TODO: Check behavior with multiple bot instances open at once
                # DONE: Multiple servers? Works. Guild(s) need to be specified via TG


        DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        await client.start(DISCORD_TOKEN)
