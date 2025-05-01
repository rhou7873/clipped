import os
import discord
from discord.ext import commands
from threading import Thread
from cmd_gateway import GatewayCog


def run_bot(bot: commands.Bot):
    bot.run(os.getenv("BOT_TOKEN"))


def main():
    """ Setup bot intents and cogs and bring General Walarus to life """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True

    bot: commands.Bot = commands.Bot(command_prefix="clip", intents=intents)
    bot.load_extension("cmd_gateway")

    run_bot(bot)


if __name__ == "__main__":
    main()
