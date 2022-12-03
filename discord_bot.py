#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains the discord bot to be called from within telegram_bot.py.
DiscordBot instantiates a second telegram bot for sending out the notifications.
"""

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
        Constructor of the class. Initializes some instance variables.
        """
        # Instantiate Telegram bot to send out messages to users
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_bot = Bot(TELEGRAM_TOKEN)
        # Set of Discord usernames & roles that the Discord bot is listening to
        self.listening_to = {"handles": set(), "roles": set()}
        # Reverse lookup {"handles": {discord username: {telegram id, telegram id}}
        self.discord_telegram_map = {"handles": {}, "roles": {}}
        # Dictionary {telegram id: {data}}
        self.users = dict()
        # Path to shared database (data entry via telegram_bot.py)
        self.data_path = "./data"
        self.debug_chat_id = int(os.getenv("DEBUG_TG_ID"))
        self.client = None

    def refresh_data(self):
        """
        Populates/updates users, listening_to, discord_telegram_map.
        """
        # Reload database from file
        self.users = read_pickle(self.data_path)["user_data"]
        print('\n\nself.users -> ', self.users)
        # Update sets of notification triggers and reverse lookups
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
        # Debug area
        print("\nself.discord_bot.refresh_data() called successfully!\n")
        print("Data updated from Pickle file:")
        print(f"users: {self.users}")
        print(f"listening_to: {self.listening_to}")
        print(f"discord_telegram_map: {self.discord_telegram_map}")

    async def send_to_TG(self, telegram_user_id, msg):
        """
        Sends a message a specific Telegram user id.
        Uses Markdown V1 for inline link capability.
        """
        await self.telegram_bot.send_message(
            chat_id=telegram_user_id,
            text=msg,
            disable_web_page_preview=True,
            parse_mode="Markdown"
            )

    async def send_to_all(self, msg):
        """Sends a message to all Telegram bot users."""
        TG_ids = list(self.users.keys())
        for _id in TG_ids:
            await self.send_to_TG(_id, msg)

    def get_roles(self, discord_username, guild_id=1031616432049496225):
        """
        Takes a Discord username, returns all roles set for user in current guild.
        """
        #TODO Pass guild_id arg along from TG bot
        #user = client.fetch_user(user_id)
        guild = self.client.get_guild(guild_id)
        user = guild.get_member_named(discord_username)
        roles = [role.name for role in user.roles]

        print(f"\n\nDEBUG DISCORD: Got these roles: {roles}") # Debug only
        return roles

    def get_listening_to(self, TG_id):
        """
        Takes a TG username, returns whatever this user gets notifications for
        currently.
        """
        _map = self.discord_telegram_map
        handles_active = {k for k, v in _map["handles"].items() if TG_id in v}
        roles_active = {k for k, v in _map["roles"].items() if TG_id in v}

        return {"handles": handles_active, "roles": roles_active}


    async def run_bot(self):
        """Actual logic of the bot is stored here."""
        # Update data to listen to at startup
        self.refresh_data()

        # Fire up discord client
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        client = self.client

        # Actions taken at startup
        @client.event
        async def on_ready():
            handles = self.listening_to["handles"]
            roles = self.listening_to["roles"]
            mentions_update = f"""
            Notifications active for mentions of {handles} and {roles}.
            """
            print(f"\n\n{client.user.name} has connected to Discord!\n\n")
            msg = "Discord bot is up & running!"
            await self.send_to_all(msg)
            await self.send_to_TG(self.debug_chat_id, mentions_update)

        # Actions taken on every new Discord message
        @client.event
        async def on_message(message):
            # Debug area
            print(f"\n\nDiscord message -> {message}\n\n")
            print(f"\n\nmessage.mentions type -> {type(message.mentions)}\n\n")
            print(f"\n\nmessage.mentions -> {message.mentions}\n\n")
            print(f"\n\nmessage.mentions == []-> {message.mentions == []}\n\n")
            # TODO: Check for an empty message.mentions here to skip all the rest

            # Handle mentions: Forward to TG as specified in Discord->Telegram lookup
            for username in self.listening_to["handles"]:
                user = message.guild.get_member_named(username)

                # Debug area
                print('\nusername in listening:', username)
                print('user from guild:', user)
                print('message.mentions:', message.mentions)

                if user in message.mentions:
                    print(f"\n\nUSER IN MENTIONS\n\n")
                    TG_ids = self.discord_telegram_map["handles"][username]

                    for _id in TG_ids:
                        author, guild_name = message.author, message.guild.name
                        alias, url = user.display_name, message.jump_url
                        print(f"\n{author} mentioned {username}!\n") # Debug only
                        contents = "@"+alias+message.content[message.content.find(">")+1:]
                        header = f"\nMentioned by {author} in {guild_name}:\n\n"
                        #link = "["+contents+"]"+"("+url+")"
                        out_msg = header+contents
                        await self.send_to_TG(_id, out_msg)

            # Role mentions: Forward to TG as in the Discord->Telegram lookup
            for role in self.listening_to["roles"]:
                # probably some getter for role is needed for equality of objects
                if role in message.mentions:
                    TG_ids = self.discord_telegram_map["roles"][role]
                    author, guild_name = message.author, message.guild.name
                    alias, url = user.display_name, message.jump_url
                    contents = "@"+alias+message.content[message.content.find(">")+1:]
                    header = f"Message to {role} in {guild_name}:\n\n"
                    link = "["+contents+"]"+"("+url+")"
                    out_msg = header+link
                    print(f"\n{author} mentioned {role}!\n") # Debug only

                    for _id in TG_ids:
                        await self.send_to_TG(_id, out_msg)

            # DONE: Have bot also check for mentioned roles
            # TODO: Have bot listen to specified subset of channels only
            # TODO: Check behavior with multiple bot instances open at once
            # TODO: Check behavior with bot on multiple servers simultaneously



        DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        #client.run(DISCORD_TOKEN)
        await client.start(DISCORD_TOKEN)
