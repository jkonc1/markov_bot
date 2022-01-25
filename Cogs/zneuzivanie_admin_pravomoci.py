# discord api
from discord.ext import commands
from discord.commands import slash_command, permissions, Option
import discord

# system
import os
import sys
from dotenv import load_dotenv

# custom utilities
from Utilities import log

log = log.Logger("zneuzivanie_admina")

# grab home guild from '.env' and typecast horribly lol
GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)


class Zneuzivanie_admina(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("Zneuzivanie_admina cog loaded.")

    # Load
    @commands.slash_command(
        name="move",
        guild_ids=[Home_Guild],
        description="Move to channel | owner-only command",
    )
    @permissions.is_owner()
    async def move(
        self,
        ctx: commands.Context,
        channel_id: Option(
            str,
            "ID of the channel to move to.",
            required=True,
        ),
        user_id: Option(
            str,
            "ID of the user to move (default yourself)",
            required=False,
        ),
    ):
        if user_id is None:
            user_id = ctx.author.id
        user_id = int(user_id)
        channel_id = int(channel_id)
        for guild in self.client.guilds:
            for voice in guild.voice_channels:
                if voice.id == channel_id:
                    user = guild.get_member(user_id)
                    if user is None:
                        ctx.respond(
                            "No matching member in the guild with the requested voice channel."
                        )
                        return
                    await user.move_to(voice)
                    await ctx.respond("Moved!")
                    return
        ctx.respond("No such voice channel found!")


def setup(client):
    client.add_cog(Zneuzivanie_admina(client))
