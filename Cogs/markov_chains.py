# discord api
import discord
from discord.ext import commands
from discord.commands import slash_command, permissions, Option

# system
import os
import sys
from dotenv import load_dotenv
import random
from collections import defaultdict

# custom utilities
from Utilities import log

log = log.Logger("markov_chains")

# grab home guild from '.env' and typecast horribly lol
GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)

Awesome_Guild = 798164313863880734


async def markov_generate(beginning: str, quote_list) -> str:
    MAX_MSG_LENGTH = 50
    wordlist = set()
    following = defaultdict(lambda: defaultdict(int))
    for quote in quote_list:
        split = quote.split()
        for word in split:
            wordlist.add(word)
        for i in range(len(split) - 1):
            following[split[i]][split[i + 1]] += 1

    word = beginning.split()[-1] if beginning else random.choice(list(wordlist))
    result = beginning if beginning else word

    for i in range(MAX_MSG_LENGTH - 1):
        possibilities = following[word]
        if not possibilities:
            break
        word = random.choices(
            population=list(possibilities.keys()),
            weights=list(possibilities.values()),
            k=1,
        )[0]
        result += " " + word

    return result


class Markov_chains(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("Markov chain cog loaded.")

    @commands.user_command(name="markov generator")
    async def hi(self, ctx: commands.Context, user: discord.User):
        await ctx.defer(ephemeral=True)
        guild = ctx.guild
        l = []
        for channel in guild.text_channels:
            async for message in channel.history(limit=None):
                if message.author == user and message.content:
                    l.append(message.content)
        print(l)
        if not l:
            await ctx.channel.send(f"{user.name} hasn't sent a message yet!")
            return
        else:
            reply = await markov_generate("", l)
            await ctx.channel.send(reply)

    @commands.slash_command(
        name="domekator",
        description="Generate a message similar to Domek's.",
        guild_ids=[Home_Guild, Awesome_Guild],
    )
    async def domekator(self, ctx: commands.Context, beginning: str = ""):
        with open("Data/messagelist.txt", "r") as messages:
            reply = await markov_generate(beginning, messages.readlines())
            await ctx.respond(reply)


def setup(client):
    client.add_cog(Markov_chains(client))
