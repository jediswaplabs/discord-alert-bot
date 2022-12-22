# Discord Alerts Bot

![Preview](https://github.com/jediswaplabs/discord-alert-bot/blob/main/example.png)


A Telegram bot that notifies you when your handle is mentioned in a specific Discord server.
To run, add the bot [Telegram Alerts](https://discord.com/oauth2/authorize?client_id=1031609181700104283&scope=bot&permissions=1024) to the **Discord** server you want to get notifications for. It only needs permissions to read messages. Feel free to use the [invite link](https://discord.com/oauth2/authorize?client_id=1031609181700104283&scope=bot&permissions=1024).

On **Telegram**, start a conversation with [@DiscordAlertsBot](https://t.me/DiscordAlertsBot).
It will prompt for your Discord handle and the Discord server you want to use it in.
You can now customize the bot to forward any message mentioning your Discord handle or
a role you want notifications for. These notifications can be switched on on a per-channel
basis as well.

_Alternatively, to run your own fully customizable version of this bot, follow these steps:_

- Clone this repository.
- [Get a Discord bot token](https://www.writebots.com/discord-bot-token/) at the Discord Developer Portal.
- Set the bot up with the permission to view channels and add [server members intent and message content intent](https://discordpy.readthedocs.io/en/stable/intents.html#member-intent).
- [Get a Telegram bot token.](https://riptutorial.com/telegram-bot/example/25075/create-a-bot-with-the-botfather)
- Enter both bot tokens to the `.env` file as shown in [sample.env](https://github.com/jediswaplabs/discord-alert-bot/blob/main/sample.env). No quotes allowed in the `.env` file.
- Add your Discord server ID to the `.env` file under `DEFAULT_GUILD`.
- Add the bot to your Discord server as shown [here](https://www.writebots.com/discord-bot-token/) or set up an [invite link](https://discordapi.com/permissions.html#66560).
- Run `main.py`.

## Requirements & Installation

The bot requires python >= 3.7 (3.9 is recommended) and uses the packages listed in `requirements.txt`.
The best practice would be to install a virtual environment and install the
requirements afterwards using `pip`:

```
pip install -r requirements.txt
```
The bot relies on a pre-release of [python-telegram-bot](https://docs.python-telegram-bot.org/en/v20.0a6/),
so if you choose to install the dependencies manually using `pip`, the `--pre` flag will be necessary ([see here](https://docs.python-telegram-bot.org/en/v20.0a6/)). If you're using [anaconda](https://www.anaconda.com), you can create a virtual environment and install all requirements using this code:

```
conda create -n discord-alert-bot python=3.9
conda activate discord-alert-bot
pip install -r requirements.txt
```

## Usage

Enter the Telegram and Discord bot tokens into `.env` to their respective keys, as shown in [sample.env](https://github.com/jediswaplabs/discord-alert-bot/blob/main/sample.env). Likewise, enter the guild id of the guild you want to use it in to the file. This guild has to have _Telegram Alerts_ bot as member. The bot also needs to be added as member to any private channels you want to receive notifications for.

Run `main.py` to start the bot.
```
python main.py
```

On Telegram, start a conversation with [@DiscordAlertsBot](https://t.me/DiscordAlertsBot) to set up notifications.

## License

This project is licensed under the [MIT license](https://github.com/jediswaplabs/discord-alert-bot/blob/main/LICENSE) - see the [LICENSE](https://github.com/jediswaplabs/discord-alert-bot/blob/main/LICENSE) file for details.
