from bw_secrets import CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION
import modules.database as db

import discord
from discord.ext.commands import Cog
from discord.ext import commands
from typing import List, Dict


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
        query_result = db._read_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                                        filter={"_id": guild.id},
                                        projection={"_id": 0, "channel_id": 1})

        # bot_channel_id=None would indicate bot isn't in a voice channel
        bot_channel_id = query_result[0]["channel_id"] if len(
            query_result) > 0 else None

        # `bot_joined_vc`: bot joined a VC with users in it
        # `bot_left_vc`: bot left a VC that it was in
        # `user_joined_bot_vc`: user joins VC with the bot in it
        bot_joined_vc = member_updated.id == self.bot.user.id and after.channel is not None
        bot_left_vc = member_updated.id == self.bot.user.id and after.channel is None
        user_joined_bot_vc = after.channel is not None and after.channel.id == bot_channel_id

        db.update_clipped_sessions(guild=guild,
                                   voice_channel=after.channel if bot_joined_vc else before.channel,
                                   bot_joined_vc=bot_joined_vc,
                                   bot_left_vc=bot_left_vc)

        self._manage_voice_capture(member_updated=member_updated,
                                   new_state=after,
                                   bot_joined_vc=bot_joined_vc,
                                   user_joined_bot_vc=user_joined_bot_vc)

    def _manage_voice_capture(self,
                              member_updated: discord.Member,
                              new_state: discord.VoiceState,
                              bot_joined_vc: bool,
                              user_joined_bot_vc: bool) -> None:
        # Both of these scenarios is when we want to fetch opt-in statuses
        # before we start capturing voice data
        new_opted_in_statuses = {}
        if bot_joined_vc:
            new_opted_in_statuses = db.get_opted_in_statuses(bot=self.bot,
                                                             members=new_state.channel.members)
        elif user_joined_bot_vc:
            new_opted_in_statuses = db.get_opted_in_statuses(bot=self.bot,
                                                             members=[member_updated])

        # TODO: now that we have opted-in statuses (of all users in VC that bot joined,
        # or of the single member that just joined the VC), we want to use this information
        # to manage whose voice data we're capturing
        for member, opted_in in new_opted_in_statuses.items():
            pass


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(EventsCog(bot))
