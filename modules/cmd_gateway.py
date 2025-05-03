import os
import modules.database as db
import views
from typing import Callable 

import discord
from discord.ext.commands import Cog
from discord.ext import commands


class GatewayCog(Cog, name="Command Gateway"):
    """Encapsulates all of Clipped's supported commands"""

    def __init__(self, bot: discord.Bot):
        self.CLIPPED_SESSIONS_COLLECTION = os.getenv(
            "CLIPPED_SESSIONS_COLLECTION")

        if self.CLIPPED_SESSIONS_COLLECTION is None:
            raise Exception(
                "Clipped sessions collection name is not in environment variables")

        self.bot = bot
        self.last_ui_message = None

    ####### RESEND CONTROL BUTTONS #######

    @commands.slash_command(
        name="buttons",
        description="Resend Clipped control buttons.",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_buttons(self, ctx: discord.ApplicationContext):
        """Definition for `/buttons` slash command."""
        params = {
            "respond_func": ctx.respond,
            "interaction": ctx.interaction
        }
        await self._buttons_handler(**params)

    async def _buttons_handler(self,
                               respond_func: Callable,
                               interaction: discord.Interaction) -> None:
        if self.last_ui_message is None:
            await respond_func(":warning: Make sure you've started a Clipped "
                               "session with `/joinvc`")

        await self.last_ui_message.delete()  # delete the old control buttons
        await self._display_gui(respond_func, interaction)

    ####### VOICE CLIPPING #######

    @commands.slash_command(
        name="clipthat",
        description="Clip the last 30 seconds of voice activity.",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_clip_that(self, ctx: discord.ApplicationContext):
        """Definition for `/clipthat` slash command."""
        pass

    async def _clip_that_handler(self):
        pass

    ####### JOINING VOICE #######

    @commands.slash_command(
        name="joinvc",
        description="Prompt Clipped bot to join your voice channel.",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_join_vc(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/joinvc` slash command."""
        params = {
            "respond_func": ctx.respond,
            "interaction": ctx.interaction,
            "user_voice": ctx.author.voice,
            "guild": ctx.guild,
            "channel": ctx.channel
        }
        await self._join_vc_handler(**params)

    async def _join_vc_handler(self,
                               respond_func: Callable,
                               interaction: discord.Interaction,
                               user_voice: discord.VoiceState | None,
                               guild: discord.Guild,
                               channel: discord.VoiceChannel) -> None:
        """Handler for `/joinvc` slash command"""
        voice = await self._join_vc(respond_func, user_voice, guild, channel)
        if voice is None:
            return

        self._start_capturing_voice()
        await self._display_gui(respond_func, interaction)

    async def _join_vc(self,
                       respond_func: Callable,
                       user_voice: discord.VoiceState | None,
                       guild: discord.Guild,
                       channel: discord.VoiceChannel) -> discord.VoiceClient | None:
        if user_voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return None

        try:
            voice_client: discord.VoiceClient = await user_voice.channel.connect()
        except discord.ClientException as e:
            await respond_func(":warning: I'm already connected to a voice channel")
            return None
        except Exception as e:
            print(e)
            return None

        # Register voice session in DB
        db.create_document(collection_name=self.CLIPPED_SESSIONS_COLLECTION,
                           obj={"_id": guild.id,
                                "channel_id": channel.id})

        return voice_client

    def _start_capturing_voice(self) -> None:
        pass

    async def _display_gui(self, respond_func: Callable, interaction: discord.Interaction) -> None:
        clipped_buttons = views.ControlsView(
            clip_that_func=self._clip_that_handler,
            leave_vc_func=self._leave_vc_handler)
        await respond_func(view=clipped_buttons)
        self.last_ui_message = await interaction.original_response()

    ####### LEAVING VOICE #######

    @commands.slash_command(
        name="leavevc",
        description="Prompt Clipped bot to leave your voice channel.",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_leave_vc(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/leavevc` slash command."""
        params = {
            "respond_func": ctx.respond,
            "guild": ctx.guild
        }
        await self._leave_vc_handler(**params)

    async def _leave_vc_handler(self, respond_func: Callable, guild: discord.Guild) -> None:
        """Handler for `/leavevc` slash command."""
        await self._remove_gui()
        self._stop_capturing_voice()
        await self._leave_vc(respond_func, guild)

    async def _remove_gui(self):
        await self.last_ui_message.delete()

    def _stop_capturing_voice(self):
        pass

    async def _leave_vc(self, respond_func: Callable, guild: discord.Guild) -> None:
        bot_voice = guild.voice_client

        if bot_voice is None:
            await respond_func(":warning: I'm not connected to a voice channel")
            return

        await bot_voice.disconnect()

        # Remove voice session from DB
        db.delete_document(collection_name=self.CLIPPED_SESSIONS_COLLECTION,
                           id=guild.id)

    ####### CLIP SEARCH #######

    @commands.slash_command(
        name="searchfor",
        description="Search for a clip with a prompt.",
        guild_ids=[os.getenv("DEV_GUILD_ID")])
    async def cmd_search_for(self, ctx: discord.ApplicationContext, *args) -> None:
        """Definition for `/searchfor` slash command."""
        params = {
            "respond_func": ctx.respond,
            "prompt": args
        }
        await self._search_for_handler(**params)

    async def _search_for_handler(self, respond_func: Callable, prompt: str):
        """Handler for `/searchfor` slash command."""
        await respond_func(":octagonal_sign: Command currently unsupported")


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(GatewayCog(bot))
