# Clipped modules
from bw_secrets import BOT_USER_ID
from models.member import ClippedMember
from modules.cmd_gateway import GatewayCog
from ui.opt_in_view import OptInView

# Pycord modules
import discord
from discord.ext.commands import Cog
from discord.ext import commands


class EventsCog(Cog, name="Event Handler"):
    """Encapsulates all of Clipped's event listeners """

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    ####################################################################
    ############################ ON READY ##############################
    ####################################################################

    @commands.Cog.listener()
    async def on_ready(self):
        print("Clipped bot ready")

    ####################################################################
    ################### VOICE CHANNEL STATUS UPDATE ####################
    ####################################################################

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        """
        Event triggered when voice channel status updates
        (e.g. user leaves/joins VC)
        """
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

        if after.channel is not None:
            await self._notify_opt_in_options(voice=after.channel)

        bot_left_vc = member_updated.id == BOT_USER_ID and after.channel is None
        if bot_left_vc:
            self._stop_capturing_voice(guild)
            if GatewayCog.clipped_sessions.get(guild.id) is not None:
                # mapping may not exist if bot failed voice connection
                # and is undergoing a reconnect
                await GatewayCog.clipped_sessions[guild.id].last_ui_message.delete()
                del GatewayCog.clipped_sessions[guild.id]

    async def _notify_opt_in_options(self,
                                     voice: discord.VoiceChannel) -> None:
        """
        If members in voice channel don't exist in database yet (i.e.
        first interaction with the bot), then send them DM w/ opt-in
        preference options
        """
        if BOT_USER_ID not in [member.id for member in voice.members]:
            # Bot isn't in voice, so no need to send notification
            return

        for member in voice.members:
            if member.id == BOT_USER_ID:  # skip the bot itself
                continue

            member_exists = ClippedMember.member_exists(guild_id=member.guild.id,
                                                        member_id=member.id)
            if not member_exists:
                ClippedMember.set_opted_in_status(
                    member.guild, member, opted_in=True)
                dm = await member.create_dm()
                view = OptInView(member=member,
                                 opt_in_handler=GatewayCog.opt_in_handler,
                                 opt_out_handler=GatewayCog.opt_out_handler,
                                 show_opt_in=True,
                                 show_opt_out=True)

                msg = ("**OPT-IN PREFERENCE OPTIONS**\n"
                       "Your voice is currently being captured by the Clipped bot in "
                       f"the '{member.guild.name}' server for any audio clips "
                       "generated. You may click either option below to opt-in or "
                       "opt-out of voice capture moving forward")
                await dm.send(msg, view=view)

    def _stop_capturing_voice(self, guild: discord.Guild):
        session = GatewayCog.clipped_sessions[guild.id]
        session.stop_session()


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(EventsCog(bot))
