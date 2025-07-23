# Clipped modules
from bw_secrets import DEV_GUILD_ID
from models.session import ClippedSession
from models.member import ClippedMember
from models.voice_client import ClippedVoiceClient
from modules.storage_handler import StorageHandler
from ui.controls_view import ControlsView

# Pycord modules
import discord
from discord.ext.commands import Cog
from discord.ext import commands

# Other modules
import asyncio
from typing import Callable, Dict


class GatewayCog(Cog, name="Command Gateway"):
    """Encapsulates all of Clipped's supported commands"""

    CLIP_SIZE = 30  # length of clips (in seconds)
    CHUNK_SIZE = 1  # length of audio chunks in buffer (in seconds)

    clipped_sessions: Dict[int, ClippedSession] = {}

    def __init__(self, bot: discord.Bot):
        self.bot = bot

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
            "guild": ctx.guild,
            "respond_func": ctx.respond,
            "interaction": ctx.interaction,
            "user": ctx.author
        }
        await self._buttons_handler(**params)

    async def _buttons_handler(self,
                               guild: discord.Guild,
                               respond_func: Callable,
                               interaction: discord.Interaction,
                               user: discord.Member) -> None:
        if user.voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return
        if GatewayCog.clipped_sessions[guild.id].last_ui_message is None:
            await respond_func(":warning: Make sure you've started a Clipped "
                               "session with `/joinvc`")
            return

        # delete old control buttons
        await GatewayCog.clipped_sessions[guild.id].last_ui_message.delete()
        await self._display_gui(guild, respond_func, interaction)

    ################################################################
    ######################## VOICE CLIPPING ########################
    ################################################################

    @commands.slash_command(
        name="clipthat",
        description="Clip the last 30 seconds of voice activity.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_clip_that(self, ctx: discord.ApplicationContext):
        """Definition for `/clipthat` slash command."""
        await ctx.defer()  # make take a while to process, this extends timeout
        params = {
            "respond_func": ctx.respond,
            "guild": ctx.guild,
            "user": ctx.author
        }
        await self._clip_that_handler(**params)

    async def _clip_that_handler(self,
                                 respond_func: Callable,
                                 guild: discord.Guild,
                                 user: discord.Member) -> None:
        if user.voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return

        async def process_clip():
            session = GatewayCog.clipped_sessions[guild.id]
            clip = session.processor.process_audio_data()

            # immediately send clip w/ overlayed voice to text channel
            file = discord.File(clip, filename="clip.wav")
            await respond_func(file=file)

            # persist clip and its metadata in storage for later retrieval
            clip_by_member = session.processor.process_audio_data_by_member()
            bucket_location = StorageHandler.store_clip_audio(guild, clip)
            StorageHandler.store_clip_metadata(
                guild, bucket_location, clip_by_member)

        asyncio.create_task(process_clip())

    ################################################################
    ######################### JOINING VOICE ########################
    ################################################################

    @commands.slash_command(
        name="joinvc",
        description="Prompt Clipped bot to join your voice channel.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_join_vc(self, ctx: discord.ApplicationContext) -> None:
        """Definition for `/joinvc` slash command."""
        await ctx.defer()
        params = {
            "respond_func": ctx.send_followup,
            "interaction": ctx.interaction,
            "user": ctx.author,
            "guild": ctx.guild
        }
        await self._join_vc_handler(**params)

    async def _join_vc_handler(self,
                               respond_func: Callable,
                               interaction: discord.Interaction,
                               user: discord.Member,
                               guild: discord.Guild) -> None:
        """Handler for `/joinvc` slash command"""
        if user.voice is None:
            msg = ":warning: You must be in a voice channel"
            await respond_func(msg)
            return

        voice = await self._join_vc(respond_func, user)
        if voice is None:
            return

        self._start_capturing_voice(voice, user)

        if GatewayCog.clipped_sessions.get(guild.id) is not None:
            # indicates voice connection succeeded and a Clipped
            # session has successfully been instantiated
            await self._display_gui(guild, respond_func, interaction)

    async def _join_vc(self,
                       respond_func: Callable,
                       user: discord.Member) -> discord.VoiceClient | None:
        try:
            voice_client: discord.VoiceClient = await (user
                                                       .voice
                                                       .channel
                                                       .connect(cls=ClippedVoiceClient))
        except discord.ClientException as e:
            msg = ":warning: I'm already connected to a voice channel"
            await respond_func(msg)
            return None
        except Exception as e:
            print(e)
            msg = ":warning: There was an error trying to join voice"
            await respond_func(msg)
            return None

        return voice_client

    def _start_capturing_voice(self,
                               voice: discord.VoiceClient,
                               user: discord.Member) -> None:
        guild = voice.guild
        new_session = ClippedSession(voice=voice,
                                     started_by=user,
                                     clip_size=GatewayCog.CLIP_SIZE,
                                     chunk_size=GatewayCog.CHUNK_SIZE)
        GatewayCog.clipped_sessions[guild.id] = new_session

    async def _display_gui(self,
                           guild: discord.Guild,
                           respond_func: Callable,
                           interaction: discord.Interaction) -> None:
        clipped_buttons = ControlsView(
            clip_that_func=self._clip_that_handler,
            leave_vc_func=self._leave_vc_handler)

        await respond_func(view=clipped_buttons)

        session = GatewayCog.clipped_sessions[guild.id]
        session.last_ui_message = await interaction.original_response()

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
            "guild": ctx.guild,
            "user": ctx.author
        }
        await self._leave_vc_handler(**params)

    async def _leave_vc_handler(self,
                                respond_func: Callable,
                                guild: discord.Guild,
                                user: discord.Member) -> None:
        """Handler for `/leavevc` slash command."""
        if user.voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return

        # Note: this command handler simply disconnects the bot from voice.
        # Other processes like GUI removal and Clipped session cleanup
        # are handled in events_handler.py:on_voice_state_update().
        await self._leave_vc(respond_func, guild)
        await respond_func("No longer capturing audio for clips")

    async def _leave_vc(self,
                        respond_func: Callable,
                        guild: discord.Guild) -> None:
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
        ClippedMember.set_opted_in_status(guild=guild,
                                          member=member,
                                          opted_in=True)

        msg = ("**OPT-IN CONFIRMATION**\n"
               f"You have ***opted in*** to audio capture in '{guild.name}', "
               "meaning your voice ***will*** be heard in clips generated "
               "from that server. This change will be reflected the next "
               "time a clip is generated.")
        await dm.send(msg)

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
        ClippedMember.set_opted_in_status(guild=guild,
                                          member=member,
                                          opted_in=False)

        msg = ("**OPT-OUT CONFIRMATION**\n"
               f"You have ***opted out*** of audio capture in '{guild.name}', "
               "meaning your voice ***will not*** be heard in clips generated "
               "from that server. This change will be reflected the next "
               "time a clip is generated.")
        await dm.send(msg)

    ################################################################
    ########################## CLIP SEARCH #########################
    ################################################################

    @commands.slash_command(
        name="searchfor",
        description="Search for a clip with a prompt.",
        guild_ids=[DEV_GUILD_ID])
    async def cmd_search_for(self,
                             ctx: discord.ApplicationContext,
                             *args) -> None:
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
