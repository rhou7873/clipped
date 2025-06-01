from bw_secrets import CLIPPED_SESSIONS_COLLECTION, USERS_COLLECTION, DEV_GUILD_ID
from .cmd_gateway import GatewayCog
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
        guild_id = member_updated.guild.id
        query_result = db.read_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                                        filter={"_id": guild_id},
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

        self._update_db_clipped_sessions(before,
                                         after,
                                         bot_joined_vc,
                                         bot_left_vc)
        self._manage_voice_capture(member_updated,
                                   after,
                                   bot_joined_vc,
                                   user_joined_bot_vc)

    def _update_db_clipped_sessions(self,
                                    old_state: discord.VoiceState,
                                    new_state: discord.VoiceState,
                                    bot_joined_vc: bool,
                                    bot_left_vc: bool) -> None:
        if bot_joined_vc:
            if new_state.channel is None:
                raise Exception(
                    "Voice state channel shouldn't be None if bot joined VC")

            guild_id = new_state.channel.guild.id
            channel_id = new_state.channel.id

            # Register voice session in DB
            db.create_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                               obj={"_id": guild_id,
                                    "channel_id": channel_id})
        elif bot_left_vc:
            if new_state.channel is not None:
                raise Exception(
                    "Voice state channel should be None if bot left VC")

            guild_id = old_state.channel.guild.id

            # Remove voice session from DB
            db.delete_document(collection_name=CLIPPED_SESSIONS_COLLECTION,
                               id=guild_id)

    def _manage_voice_capture(self,
                              member_updated: discord.Member,
                              new_state: discord.VoiceState,
                              bot_joined_vc: bool,
                              user_joined_bot_vc: bool) -> None:
        # Both of these scenarios is when we want to fetch opt-in statuses
        # before we start capturing voice data
        new_opted_in_statuses = {}
        if bot_joined_vc:
            new_opted_in_statuses = self._get_opted_in_statuses(
                members=new_state.channel.members)
        elif user_joined_bot_vc:
            new_opted_in_statuses = self._get_opted_in_statuses(
                members=[member_updated])

        # TODO: now that we have opted-in statuses (of all users in VC that bot joined,
        # or of the single member that just joined the VC), we want to use this information
        # to manage whose voice data we're capturing
        for member, opted_in in new_opted_in_statuses.items():
            pass

    def _get_opted_in_statuses(self, members: List[discord.Member]) -> Dict[discord.Member, bool]:
        statuses = {}

        for user in members:
            if user.id == self.bot.user.id:  # skip the Clipped bot
                continue

            # Fetch users' `opt_in` status from DB
            query_results = db.read_document(collection_name=USERS_COLLECTION,
                                             filter={"_id": user.id},
                                             projection={"_id": 0, "opted_in": 1})

            # If user doesn't exist in DB, create new user document
            opted_in = True  # default to opt-in status
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


def setup(bot):
    """Function needed to support load_extension() call in main driver script"""
    bot.add_cog(EventsCog(bot))
