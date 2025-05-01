import os
import modules.database as db

import discord
from discord.ext.commands import Cog
from discord.ext import commands


class GatewayCog(Cog, name="Command Gateway"):
    """Encapsulates all of Clipped's supported commands"""

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.CLIPPED_SESSIONS_COLLECTION = os.getenv(
            "CLIPPED_SESSIONS_COLLECTION")

        if self.CLIPPED_SESSIONS_COLLECTION is None:
            raise Exception(
                "Clipped sessions collection name is not in environment variables")

    ####### COMMAND REGISTRATIONS #######

    @commands.slash_command(
        name="joinvc",
        description="Prompt Clipped bot to join your voice channel",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_join_vc(self, ctx: discord.ApplicationContext):
        """ 
        Prompts Clipped bot to join voice channel so it can start listening. This
        command must be used before a clip can be requested.
        """
        voice = await self.join_vc(ctx)
        if voice is None:
            return

        self.start_capturing_voice(voice)
        self.display_gui(ctx)

    @commands.slash_command(
        name="leavevc",
        description="Prompt Clipped bot to leave your voice channel",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_leave_vc(self, ctx: discord.ApplicationContext):
        """ 
        Prompts Clipped bot to leave voice channel. This will stop any clipping 
        functionality until Clipped bot is prompted to join voice channel again.
        """
        self.remove_gui(ctx)
        self.stop_capturing_voice(ctx)
        await self.leave_vc(ctx)

    ####### HELPER FUNCTIONS #######

    async def join_vc(self, ctx: discord.ApplicationContext) -> discord.VoiceClient | None:
        voice = ctx.author.voice

        if voice is None:
            await ctx.respond(":warning: You must be in a voice channel")
            return None

        try:
            voice_client: discord.VoiceClient = await voice.channel.connect()
        except Exception as e:
            print(e)
            return None

        # Register voice session in DB
        db.create_document(collection_name=self.CLIPPED_SESSIONS_COLLECTION,
                           obj={"_id": ctx.guild_id,
                                "channel_id": ctx.channel_id})

        return voice_client

    def start_capturing_voice(self, voice: discord.VoiceClient) -> None:
        pass

    def display_gui(self, ctx: discord.ApplicationContext) -> None:
        pass

    def remove_gui(self, ctx: discord.ApplicationContext) -> None:
        pass

    def stop_capturing_voice(self, ctx: discord.ApplicationContext):
        pass

    async def leave_vc(self, ctx: discord.ApplicationContext):
        user_voice = ctx.author.voice
        bot_voice = ctx.guild.voice_client

        if user_voice is None:
            await ctx.respond(":warning: You must be in a voice channel")
            return
        if bot_voice is None:
            await ctx.respond(":warning: I'm not connected to a voice channel")
            return

        await bot_voice.disconnect()

        # Remove voice session from DB
        db.delete_document(collection_name=self.CLIPPED_SESSIONS_COLLECTION,
                           id=ctx.guild_id)

    def fetch_clip(self):
        """Invokes search handler to retrieve clip based on natural language prompt."""
        pass


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(GatewayCog(bot))
