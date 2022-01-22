# discord api
import discord
from discord.ext import commands, tasks
from discord.commands import slash_command, permissions, Option
import Utilities.db.db as db

# system
import os
import sys
import re
import aiohttp
import difflib
from dotenv import load_dotenv

# custom utilities
from Utilities import log

log = log.Logger("website_update_notifier")

# grab home guild from '.env' and typecast horribly lol
GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)


class Notificator(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

    def cog_unload(self):
        self.check_for_updates.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("Notificator cog loaded.")
        self.check_for_updates.start()

    @commands.slash_command(
        name="watch",
        description="Add a website to watch for changes.",
        guilds=[GuildID],
    )
    async def watch(
        self,
        ctx: commands.Context,
        website: Option(str, "The website to watch", required=True),
        regex: Option(
            str, "Only check a part of website matched by a regex.", required=False
        ),
    ):
        if regex == None:
            regex = ".*"
        async with aiohttp.ClientSession() as session:
            async with session.get(website) as resp:
                if resp.status != 200:
                    await ctx.respond(f"Fetching site failed: code {resp.status}")
                    return
                content = await resp.text()
                content = content.replace("\r", "").replace("\n", "")
                match = re.search(regex, content)
                if match is None:
                    await ctx.respond(
                        "No part of the website matches the provided regex."
                    )
                    return

                id = await db.insert_getid(
                    f"""insert into notifications (DiscordUserID, Website, Regex, ChannelID) values (?, ?, ?, ?)""",
                    ctx.author.id,
                    website,
                    regex,
                    str(ctx.channel.id),
                )
                print(id)
                with open(f"Data/watched_websites/{id}", "w") as file:
                    file.write(match.group(0))
        await ctx.respond("Sucessfully started watching website.")

    @commands.slash_command(
        name="unwatch", description="Stop watching a website.", guilds=[GuildID]
    )
    async def unwatch(
        self,
        ctx: commands.Context,
        website: Option(str, "The website to stop watching.", required=True),
    ):
        rows = await db.records(
            "select * from notifications where DiscordUserID=? and Website=? and ChannelID=?",
            ctx.author.id,
            website,
            ctx.channel.id,
        )
        if len(rows) == 0:
            await ctx.respond("No such website followed!")
            return
        elif len(rows) > 1:
            # TODO: make a picker
            await ctx.respond("Multiple subscriptions satisfy the criteria.")
            return
        await db.execute(
            "delete from notifications where NotificationID=?",
            rows[0]["NotificationID"],
        )
        await ctx.respond(f"Stopped watching {website}.")

    @tasks.loop(seconds=60)
    async def check_for_updates(self):
        await log.info("Checking for updates on watched websites.")
        rows = await db.records("""select * from notifications""")
        for row in rows:
            async with aiohttp.ClientSession() as session:
                async with session.get(row["Website"]) as resp:
                    if resp.status != 200:
                        await log.warning(f"Failed to fetch website {row['Website']}")
                        continue
                    content = await resp.text()
                    content = content.replace("\r", "").replace("\n", "")
                    match = re.search(row["Regex"], content)
                    if match is None:
                        await log.warning(
                            f"No part of the website {row['Website']} matches the provided regex."
                        )
                        continue

                    match = match.group(0)
                    with open(
                        f"Data/watched_websites/{row['NotificationID']}", "r"
                    ) as file:
                        previous_content = file.read()
                        if match != previous_content:
                            with open(
                                f"Data/watched_websites/{row['NotificationID']}", "w"
                            ) as file:
                                file.write(match)
                            channel = self.client.get_partial_messageable(
                                int(row["ChannelID"])
                            )
                            await channel.send(f"Website {row['Website']} has changed!")


def setup(client):
    client.add_cog(Notificator(client))
