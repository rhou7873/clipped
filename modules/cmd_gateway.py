import asyncio
import ui
from typing import Callable
from bw_secrets import DEV_GUILD_ID
import modules.database as db
from modules.data_streamer import DataStreamer
from modules.data_processor import DataProcessor

import discord
from discord.ext.commands import Cog
from discord.ext import commands


class GatewayCog(Cog, name="Command Gateway"):
    """Encapsulates all of Clipped's supported commands"""

    CLIP_SIZE = 30
    CHUNK_SIZE = 1

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.last_ui_message = None

    ################################################################
    #################### RESEND CONTROL BUTTONS ####################
    ################################################################

    @commands.slash_command(
        name="buttons",
        description="Resend Clipped control buttons.",
        guild_ids=[DEV_GUILD_ID])
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
            return

        await self.last_ui_message.delete()  # delete the old control buttons
        await self._display_gui(respond_func, interaction)

    ################################################################
    ######################## VOICE CLIPPING ########################
    ################################################################

    @commands.slash_command(
        name="clipthat",
        description="Clip the last 30 seconds of voice activity.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_clip_that(self, ctx: discord.ApplicationContext):
        """Definition for `/clipthat` slash command."""
        params = {
            "respond_func": ctx.respond,
            "guild": ctx.guild,
            "voice_client": ctx.voice_client,
            "send": ctx.send
        }
        await self._clip_that_handler(**params)

    async def _clip_that_handler(self,
                                 respond_func: Callable,
                                 guild: discord.Guild,
                                 voice_client: discord.VoiceClient, send):
        async def get_clip():
            streamer = DataStreamer.streams[guild.id]
            processor = DataProcessor(voice_client=voice_client,
                                      audio_data_buffer=streamer.audio_data_buffer,
                                      clip_size=GatewayCog.CLIP_SIZE,
                                      chunk_size=GatewayCog.CHUNK_SIZE)

            clip_bytes = await processor.process_audio_data(send=send)

            file = discord.File(clip_bytes, filename="clip.wav")
            await respond_func(file=file)

        asyncio.get_event_loop().create_task(get_clip())

    ################################################################
    ######################### JOINING VOICE ########################
    ################################################################

    @commands.slash_command(
        name="joinvc",
        description="Prompt Clipped bot to join your voice channel.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_join_vc(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/joinvc` slash command."""
        params = {
            "respond_func": ctx.respond,
            "interaction": ctx.interaction,
            "user": ctx.author,
            "guild": ctx.guild
        }
        await self._join_vc_handler(**params)

    async def _join_vc_handler(self,
                               respond_func: Callable,
                               interaction: discord.Interaction,
                               user: discord.Member | discord.User,
                               guild: discord.Guild) -> None:
        """Handler for `/joinvc` slash command"""
        voice = await self._join_vc(respond_func, user)
        if voice is None:
            return

        self._start_capturing_voice(voice)
        await self._display_gui(respond_func, interaction)

    async def _join_vc(self,
                       respond_func: Callable,
                       user: discord.Member | discord.User) -> discord.VoiceClient | None:
        if user.voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return None

        try:
            voice_client: discord.VoiceClient = await user.voice.channel.connect()
        except discord.ClientException as e:
            await respond_func(":warning: I'm already connected to a voice channel")
            return None
        except Exception as e:
            print(e)
            return None

        return voice_client

    def _start_capturing_voice(self, voice_client: discord.VoiceClient) -> None:
        streamer = DataStreamer(voice=voice_client,
                                clip_size=GatewayCog.CLIP_SIZE,
                                chunk_size=GatewayCog.CHUNK_SIZE)
        asyncio.get_event_loop().create_task(streamer.start())

    async def _display_gui(self, respond_func: Callable, interaction: discord.Interaction) -> None:
        clipped_buttons = ui.ControlsView(
            clip_that_func=self._clip_that_handler,
            leave_vc_func=self._leave_vc_handler)
        await respond_func(view=clipped_buttons)
        self.last_ui_message = await interaction.original_response()

    ################################################################
    ######################### LEAVING VOICE ########################
    ################################################################

    @commands.slash_command(
        name="leavevc",
        description="Prompt Clipped bot to leave your voice channel.",
        guild_ids=[DEV_GUILD_ID])
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
        self._stop_capturing_voice(guild)
        await self._leave_vc(respond_func, guild)
        await respond_func("No longer capturing audio for clips")

    async def _remove_gui(self):
        await self.last_ui_message.delete()

    def _stop_capturing_voice(self, guild: discord.Guild):
        DataStreamer.streams[guild.id].stop()

    async def _leave_vc(self, respond_func: Callable, guild: discord.Guild) -> None:
        bot_voice = guild.voice_client

        if bot_voice is None:
            await respond_func(":warning: I'm not connected to a voice channel")
            return

        await bot_voice.disconnect()

    ################################################################
    ########################## OPT-IN ##############################
    ################################################################

    @commands.slash_command(
        name="optin",
        description="Allow clips to capture your voice.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_opt_in(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/optin` slash command."""
        params = {
            "dm": await ctx.author.create_dm(),
            "guild": ctx.guild,
            "member": ctx.author
        }
        await GatewayCog.opt_in_handler(**params)
        await ctx.respond("Your opt-in preference has been updated")

    @staticmethod
    async def opt_in_handler(dm: discord.DMChannel,
                             guild: discord.Guild,
                             member: discord.Member):
        """Handler for `/optin` slash command."""
        db.set_opted_in_status(guild=guild,
                               user=member,
                               opted_in=True)

        await dm.send("**OPT-IN CONFIRMATION**\n"
                      f"You have ***opted in*** to audio capture in '{guild.name}', "
                      "meaning your voice ***will*** be heard in clips generated "
                      "from that server. This change will be reflected the next "
                      "time the bot joins a voice channel.")

    ################################################################
    ########################## OPT-OUT #############################
    ################################################################

    @commands.slash_command(
        name="optout",
        description="Don't allow clips to capture your voice.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_opt_out(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/optout` slash command."""
        params = {
            "dm": await ctx.author.create_dm(),
            "guild": ctx.guild,
            "member": ctx.author
        }
        await GatewayCog.opt_out_handler(**params)
        await ctx.respond("Your opt-in preference has been updated")

    @staticmethod
    async def opt_out_handler(dm: discord.DMChannel,
                              guild: discord.Guild,
                              member: discord.Member) -> None:
        """Handler for `/optout` slash command."""
        db.set_opted_in_status(guild=guild,
                               user=member,
                               opted_in=False)

        await dm.send("**OPT-OUT CONFIRMATION**\n"
                      f"You have ***opted out*** of audio capture in '{guild.name}', "
                      "meaning your voice ***will not*** be heard in clips generated "
                      "from that server. This change will be reflected the next "
                      "time the bot joins a voice channel.")

    ################################################################
    ########################## CLIP SEARCH #########################
    ################################################################

    @commands.slash_command(
        name="searchfor",
        description="Search for a clip with a prompt.",
        guild_ids=[DEV_GUILD_ID])
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
