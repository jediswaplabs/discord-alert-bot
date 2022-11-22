# Discord Alert Bot
A Telegram bot that notifies you when your handle is mentioned in a specific Discord server

To run, look for 'discord-alert-bot' on Telegram and start a conversation with it.
It will prompt for your Discord handle and the Discord server you want to use it in.
Once the information is entered, it will forward you each message you have been mentioned
in for this server.

A requirement on the Discord side of things is that the Discord bot 'Telegram Alerts' is added
to the server with permissions to read messages.

## Requirements & Installation

The bot requires python >= 3.6 and uses the packages listed in `requirements.txt`.
The best practice would be to install a virtual environment and install the
requirements afterwards using `pip`:

```
pip3 install -r requirements.txt
```

If you're using `conda`, you can create a virtual environment and install the
requirements using this code:

```
conda create -n discord-alert-bot python=3.6
conda activate discord-alert-bot
pip3 install -r requirements.txt
```

## License

This project is licensed under the [MIT license](https://github.com/jediswaplabs/discord-alert-bot/blob/main/LICENSE) - see the [LICENSE](https://github.com/jediswaplabs/discord-alert-bot/blob/main/LICENSE) file for details.
