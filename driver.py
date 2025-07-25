# Clipped modules
from bw_secrets import BOT_TOKEN
from models.session import ClippedSession

# Pycord modules
import discord
from discord.ext import commands

# Other modules
import logging


def main():
    """ Setup bot intents and cogs and bring General Walarus to life """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True

    bot: commands.Bot = commands.Bot(command_prefix="clip", intents=intents)
    bot.load_extension("modules.cmd_gateway")
    bot.load_extension("modules.events_handler")

    ClippedSession.db_clear_all_clipped_sessions()

    logging.basicConfig(level=logging.ERROR)

    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
