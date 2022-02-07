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

# custom utilities
from Utilities import log

log = log.Logger("havetator")

# grab home guild from '.env' and typecast horribly lol
GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)

Awesome_Guild = 798164313863880734


async def meme_generate(file, text):
    image = Image.open(file)
    x, y = image.size
    font = ImageFont.truetype("truetype/dejavu/DejaVuSans-Bold.ttf", int(0.04 * x))
    editable = ImageDraw.Draw(image)
    margin = 40
    offset = int(0.9 * y)
    stroke_width = 3
    for line in textwrap.wrap(text, width=35)[::-1]:
        W, H = editable.textsize(line, font, stroke_width=stroke_width)
        editable.text(
            ((x - W) / 2, offset),
            line,
            font=font,
            fill="#ffffff",
            stroke_width=3,
            stroke_fill="#000000",
        )
        offset -= H
    return image.convert("RGB")


class Havetator(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("Havetator cog loaded.")

    @commands.slash_command(
        name="havetator",
        description="Create meme with Haveta's quote.",
        guild_ids=[Home_Guild, Awesome_Guild],
    )
    async def havetator(
        self,
        ctx: commands.Context,
        quote: Option(
            str,
            required=False,
            description="The text to put in the meme. Default: random from a quote database.",
        ),
    ):
        await ctx.defer()
        if quote is None:
            with open("Data/haveta_hlasky.txt", "r") as quotes:
                quote = random.choice(quotes.readlines())
        file = "Data/havetator_images/" + random.choice(
            os.listdir("Data/havetator_images")
        )
        image = await meme_generate(file, quote)
        image.save("Data/meme.jpg")
        await ctx.respond(file=discord.File("Data/meme.jpg"))


def setup(client):
    client.add_cog(Havetator(client))
