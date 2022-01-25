# discord api
from discord.ext import commands, tasks
from discord.commands import slash_command, permissions, Option
import discord

# system
import os
import sys
import typing
import datetime
from dotenv import load_dotenv
from edupage_api.messages import EduNotification

import Utilities.db.db as db

import edupage_api

# custom utilities
from Utilities import log

log = log.Logger("edupage")

GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)


def edutime_to_datetime(t: edupage_api.EduExactDateTime):
    res = datetime.datetime(
        year=int(t.date.year),
        month=int(t.date.month),
        day=int(t.date.day),
        hour=int(t.time.hour),
        minute=int(t.time.minute),
        second=int(t.time.second),
    )
    return res


class Edupage(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.previous_notification_check_time = datetime.datetime.now()

    def cog_unload(self):
        self.check_for_new_notifications.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        accounts = await db.records("select * from users")
        for account in accounts:
            edupage = edupage_api.Edupage(
                account["EdupageServer"],
                account["EdupageUserName"],
                account["EdupagePassword"],
            )
            edupage.login()
        self.check_for_new_notifications.start()
        await log.info("Edupage cog loaded.")

    @slash_command(
        name="edupage_add_account",
        description="Add an edupage account.",
    )
    async def add_account(
        self,
        ctx: commands.Context,
        server: Option(str, "Domain name of the edupage server.", required=True),
        username: Option(str, "The username or email used to log in.", required=True),
        password: Option(str, "The edupage password", required=True),
    ):
        server = server.replace(".edupage.org", "")
        edupage = edupage_api.Edupage(server, username, password)
        try:
            edupage.login()
        except edupage_api.BadCredentialsException:
            await ctx.respond("Wrong username or password.", ephemeral=True)
            return
        except edupage_api.LoginDataParsingException:
            await ctx.respond(
                "Logging in failed, please try again later.", ephemeral=True
            )
            return
        except:
            await ctx.respond(
                "An internal error occured, please try again later.", ephemeral=True
            )
            return
        await db.execute(
            """insert into users (DiscordUserID, EdupageUserName, EdupagePassword, EdupageServer)
             values (?, ?, ?, ?)""",
            str(ctx.author.id),
            username,
            password,
            server,
        )
        account_id = await db.field(
            "select UserID from users where DiscordUserID=? and EdupageUserName=? and EdupagePassword=? and EdupageServer=?",
            str(ctx.author.id),
            username,
            password,
            server,
        )
        await ctx.respond(
            f"Account {username} at {server} added succesfully.", ephemeral=True
        )

    @slash_command(
        name="edupage_subscribe",
        description="Subscribe to notifications from an edupage account in this channel.",
    )
    async def subscribe(
        self,
        ctx: commands.Context,
        destination: Option(
            str, "Filter notifications by destination. Supports regex.", required=False
        ),
        sender: Option(
            str, "Filter notifications by sender. Supports regex.", required=False
        ),
        type: Option(
            str, "Filter notifications by type. Supports regex.", required=False
        ),
    ):
        # TODO support multiple edupage accounts per discord

        account = await db.field(
            """select UserID from users where DiscordUserID=?""", ctx.author.id
        )
        await log.info(account)

        await db.execute(
            """insert into subscriptions (ChannelID, Account, SourceName, DestinationName, Type) values (?, ?, ?, ?, ?)""",
            ctx.channel.id,
            account,
            sender,
            destination,
            type,
        )

        await ctx.respond("Sucessfully subscribed.")

    async def print_notification(
        self, notification: edupage_api.EduNotification, user_id: str
    ):
        user = await db.record("select * from users where UserID=?", user_id)
        server = user["EdupageServer"]
        account_discord_name = self.client.get_user(
            int(user["DiscordUserId"])
        ).display_name
        res = f"""{str(notification.date_added)} - New notification at server {server} (subscription by {account_discord_name}): \n {notification.text}"""
        if notification.attachments:
            res += f"Attachments: {', '.join(f'{i.filename}({i.url})' for i in notification.attachments)}"
        return res

    @tasks.loop(seconds=60)
    async def check_for_new_notifications(self):
        already_sent = set()
        await log.info("Checking for new notifications")
        current_time = datetime.datetime.now()
        edupage_accounts = await db.records("select * from users")
        for account in edupage_accounts:
            user_id = account["UserID"]
            edupage = edupage_api.Edupage(
                account["EdupageServer"],
                account["EdupageUserName"],
                account["EdupagePassword"],
            )
            edupage.login()
            notifications = edupage.get_notifications()
            for notification in notifications:
                notification_time = edutime_to_datetime(notification.date_added)
                if (
                    notification_time > self.previous_notification_check_time
                    and notification_time < current_time
                ):
                    subscriptions = await db.records(
                        """select * from subscriptions where
                     Account = ? and ? regexp SourceName and
                      ? regexp DestinationName and ? regexp Type""",
                        user_id,
                        notification.author,
                        notification.recipient,
                        type(notification.event_type).__name__,
                    )
                    for subscription in subscriptions:
                        if (subscription["ChannelID"], notification.id) in already_sent:
                            continue
                        channel = self.client.get_partial_messageable(
                            int(subscription["ChannelID"])
                        )
                        if channel is None:
                            await log.warning(
                                f"Subscription {subscription['SubscriptionID']}: channel {subscription['ChannelID']} not found"
                            )
                        else:
                            await channel.send(
                                await self.print_notification(notification, user_id)
                            )
                            already_sent.add(
                                (subscription["ChannelID"], notification.id)
                            )

        self.previous_notification_check_time = current_time


def setup(client):
    client.add_cog(Edupage(client))
