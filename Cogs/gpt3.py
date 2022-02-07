# discord api
import discord
from discord.ext import commands
from discord.commands import slash_command, permissions, Option

# system
import os
import sys
from dotenv import load_dotenv
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import textwrap
import openai

# custom utilities
from Utilities import log

log = log.Logger("havetator")

# grab home guild from '.env' and typecast horribly lol
GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)

Awesome_Guild = 798164313863880734

openai.api_key = os.getenv("OPENAI_API_KEY")


class OpenAI(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("OpenAI cog loaded.")

    @commands.slash_command(
        name="gpt3",
        description="Generate a response using GPT3.",
        guild_ids=[Home_Guild, Awesome_Guild],
    )
    @permissions.is_owner()
    async def havetator(
        self,
        ctx: commands.Context,
        prompt: Option(
            str,
            required=True,
            description="The prompt to use.",
        ),
        engine: Option(
            str,
            required=False,
            description="The engine to use.",
            options=["ada", "babbage", "curie", "davinci"],
            default="babbage",
        ),
        max_tokens: Option(
            int,
            required=False,
            description="The maximum number of tokens to use in the response.",
            default=50,
        ),
    ):
        await ctx.defer()
        completion = openai.Completion.create(
            prompt=prompt, engine=f"text-{engine}-001", max_tokens=max_tokens
        )
        await ctx.respond(completion.choices[0].text)


def setup(client):
    client.add_cog(OpenAI(client))
