# Clipped modules
from bw_secrets import CLIPPED_SESSIONS_COLLECTION, BOT_USER_ID
from modules.cmd_gateway import GatewayCog, DataStreamer
import modules.database as db
import ui

# Pycord modules
import discord
from discord.ext.commands import Cog
from discord.ext import commands


class EventsCog(Cog, name="Event Handler"):
    """Encapsulates all of Clipped's event listeners """

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    ####################################################################
    ################### VOICE CHANNEL STATUS UPDATE ####################
    ####################################################################

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        """ Event triggered when voice channel status updates (e.g. user leaves/joins VC) """
        params = {
            "member_updated": member,
            "before": before,
            "after": after
        }
        await self._on_voice_state_update_handler(**params)

    async def _on_voice_state_update_handler(self,
                                             member_updated: discord.Member,
                                             before: discord.VoiceState,
                                             after: discord.VoiceState) -> None:
        # Check DB to see if bot is in voice channel for this server,
        # and if so, retrieve the voice channel ID
        guild = member_updated.guild

        # `bot_joined_vc`: bot joined a VC with users in it
        # `bot_left_vc`: bot left a VC that it was in
        # `user_joined_bot_vc`: user joins VC with the bot in it
        bot_joined_vc = member_updated.id == BOT_USER_ID and after.channel is not None
        bot_left_vc = member_updated.id == BOT_USER_ID and after.channel is None

        if member_updated.id == BOT_USER_ID:  # when bot leaves/joins VC
            db.update_clipped_sessions(guild=guild,
                                       voice_channel=after.channel if bot_joined_vc else before.channel,
                                       bot_joined_vc=bot_joined_vc,
                                       bot_left_vc=bot_left_vc)

        if after.channel is not None:
            await self._notify_opt_in_options(voice_channel=after.channel)

        if bot_left_vc:
            # Repetitive call to disconnect() (also called in
            # cmd_gateway._leave_vc()), but ensures voice client
            # is truly disconnected when user "right-click > disconnect"s
            # instead of using /leavevc or clicking "Leave" button
            await DataStreamer.streams[guild.id].voice.disconnect(force=True)
            del DataStreamer.streams[guild.id]

    async def _notify_opt_in_options(self, voice_channel: discord.VoiceChannel) -> None:
        """
        If members in voice channel don't exist in database yet (i.e. first interaction
        with the bot), then send them DM w/ opt-in preference options
        """
        for member in voice_channel.members:
            if member.id == BOT_USER_ID:  # skip the bot itself
                continue

            if not db.member_exists(guild_id=member.guild.id, user_id=member.id):
                db.set_opted_in_status(member.guild, member, opted_in=True)
                dm = await member.create_dm()
                view = ui.OptInView(member=member,
                                    opt_in_handler=GatewayCog.opt_in_handler,
                                    opt_out_handler=GatewayCog.opt_out_handler,
                                    show_opt_in=True,
                                    show_opt_out=True)
                await dm.send("**OPT-IN PREFERENCE OPTIONS**\n"
                              "Your voice is currently being captured by the Clipped bot in "
                              f"the '{member.guild.name}' server for any audio clips generated. "
                              "You may click either option below to opt-in or opt-out of "
                              "voice capture moving forward", view=view)


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(EventsCog(bot))
