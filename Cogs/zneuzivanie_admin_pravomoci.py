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
    ):
        for member in self.client.get_all_members():
            if member.voice is not None and member.voice.channel.id == int(channel_id):
                channel = member.voice.channel
                author = channel.guild.get_member(ctx.author.id)
                await author.move_to(channel)
                await ctx.respond("Moved!")


def setup(client):
    client.add_cog(Zneuzivanie_admina(client))
