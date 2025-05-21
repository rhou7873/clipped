import modules.database as db
import views
from typing import Callable, Dict, List, Tuple
from bw_secrets import CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION, DEV_GUILD_ID

import discord
from discord.ext.commands import Cog
from discord.ext import commands


class GatewayCog(Cog, name="Command Gateway"):
    """Encapsulates all of Clipped's supported commands"""

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
        pass

    async def _clip_that_handler(self):
        pass

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
            "guild": ctx.guild,
            "channel": ctx.channel
        }
        await self._join_vc_handler(**params)

    async def _join_vc_handler(self,
                               respond_func: Callable,
                               interaction: discord.Interaction,
                               user: discord.Member | discord.User,
                               guild: discord.Guild,
                               channel: discord.VoiceChannel) -> None:
        """Handler for `/joinvc` slash command"""
        voice, statuses = await self._join_vc(respond_func, user, guild, channel)
        if voice is None:
            return

        self._start_capturing_voice(voice, statuses)
        await self._display_gui(respond_func, interaction)

    async def _join_vc(self,
                       respond_func: Callable,
                       user: discord.Member | discord.User,
                       guild: discord.Guild,
                       channel: discord.VoiceChannel) -> Tuple[discord.VoiceClient | None, Dict[discord.Member, bool]]:
        if user.voice is None:
            await respond_func(":warning: You must be in a voice channel")
            return (None, dict())

        try:
            voice_client: discord.VoiceClient = await user.voice.channel.connect()
        except discord.ClientException as e:
            await respond_func(":warning: I'm already connected to a voice channel")
            return (None, dict())
        except Exception as e:
            print(e)
            return (None, dict())

        # Register voice session in DB
        db.create_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                           obj={"_id": guild.id,
                                "channel_id": channel.id})

        # Fetch opted-in statuses of users in the voice channel
        opted_in_statuses = GatewayCog.get_opted_in_statuses(bot=self.bot,
                                                             users=voice_client.channel.members)

        return (voice_client, opted_in_statuses)

    @staticmethod
    def get_opted_in_statuses(bot: discord.Bot, users: List[discord.Member]) -> Dict[discord.Member, bool]:
        statuses = {}

        for user in users:
            if user.id == bot.user.id:  # skip the Clipped bot
                continue

            # Fetch users' `opt_in` status from DB
            query_results = db.read_document(collection_name=USERS_COLLECTION,
                                             filter={"_id": user.id},
                                             projection={"_id": 0, "opted_in": 1})

            # If user doesn't exist in DB, create new user document
            opted_in = False  # default to opt-out status
            if len(query_results) == 0:
                db.create_document(collection_name=USERS_COLLECTION,
                                   obj={
                                       "_id": user.id,
                                       "opted_in": opted_in
                                   })
            else:
                opted_in = query_results[0]["opted_in"]

            statuses[user] = opted_in

        return statuses

    def _start_capturing_voice(self,
                               voice_client: discord.VoiceClient,
                               opted_in_statuses: Dict[discord.Member, bool]) -> None:
        pass

    async def _display_gui(self, respond_func: Callable, interaction: discord.Interaction) -> None:
        clipped_buttons = views.ControlsView(
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
        db.delete_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                           id=guild.id)

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
            "respond_func": ctx.respond,
        }
        await self._opt_in_handler(**params)

    async def _opt_in_handler(self, respond_func: Callable):
        """Handler for `/optout` slash command."""
        await respond_func(":octagonal_sign: Command currently unsupported")

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
            "respond_func": ctx.respond,
        }
        await self._opt_out_handler(**params)

    async def _opt_out_handler(self, respond_func: Callable):
        """Handler for `/optout` slash command."""
        await respond_func(":octagonal_sign: Command currently unsupported")

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
