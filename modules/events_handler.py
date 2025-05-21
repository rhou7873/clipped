from bw_secrets import CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION, DEV_GUILD_ID
from cmd_gateway import GatewayCog
import modules.database as db

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
            "member": member,
            "before": before,
            "after": after
        }
        await self._on_voice_state_update_handler(**params)

    async def _on_voice_state_update_handler(self,
                                             member: discord.Member,
                                             before: discord.VoiceState,
                                             after: discord.VoiceState) -> None:
        if member.id == self.bot.user.id:  # ignore if it's the bot that joined voice
            return

        # Check DB to see if bot is in voice channel for this server,
        # and if so, retrieve the voice channel ID
        guild_id = member.guild.id
        query_result = db.read_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                                        filter={"_id": guild_id},
                                        projection={"_id": 0, "channel_id": 1})
        bot_channel_id = query_result[0]["channel_id"] if len(
            query_result) > 0 else None

        # A user has joined the channel the Clipped bot is in
        # bot_channel_id=None would indicate bot isn't in a voice channel
        if after.channel is not None and after.channel.id == bot_channel_id:
            opted_in_statuses = GatewayCog.get_opted_in_statuses(bot=self.bot,
                                                                 users=[member])
            opted_in = opted_in_statuses[member]

            if opted_in:
                pass  # TODO: start capturing this user's voice for clips


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(EventsCog(bot))
