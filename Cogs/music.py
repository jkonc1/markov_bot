# discord api
from discord.ext import commands, tasks
from discord.commands import slash_command, permissions, Option
import discord

# system
import os
import asyncio
from dotenv import load_dotenv
from collections import defaultdict
from requests import get


# custom utilities
from Utilities import log
import youtube_dl

log = log.Logger("music")

# youtube-dl setup

ytdl_format_options = {
    "format": "worstaudio",
    "outtmpl": "Data/music/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {"options": "-vn"}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


def ytdl_search(arg):
    try:
        get(arg)
    except:
        video = ytdl.extract_info(f"ytsearch:{arg}", download=False)["entries"][0]
    else:
        video = ytdl.extract_info(arg, download=False)
    return video


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.FFmpegAudio, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(filename, **ffmpeg_options),
            data=data,
        )

    @classmethod
    async def stream_from_data(cls, data):
        return cls(discord.FFmpegPCMAudio(data["url"]), data=data)

    @classmethod
    async def download_and_play(cls, data):
        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


GuildID = os.getenv("GUILD_ID")
Home_Guild = int(GuildID)


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = defaultdict(list)
        self.volume = defaultdict(lambda: 100)
        self.caching = set()

    @commands.Cog.listener()
    async def on_ready(self):
        await log.info("Music cog loaded.")

    @commands.slash_command(
        name="join", description="Join the voice channel you're in.", guilds=[GuildID]
    )
    async def join(self, ctx: commands.Context):
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.respond("Connected.", ephemeral=True)

    @commands.slash_command(name="play", description="Play a song.", guilds=[GuildID])
    async def play(
        self,
        ctx: commands.Context,
        name: Option(str, "The URL or name of song to play.", required=True),
    ):
        video_data = ytdl_search(name)
        self.queue[ctx.guild.id].append(video_data)

        await ctx.respond(f"Added {video_data['webpage_url']} to queue.")
        if not ctx.voice_client.is_playing():
            await self.play_from_queue(ctx)

    async def play_from_queue(self, ctx: commands.Context):
        if ctx.guild.id in self.caching:
            await log.info("A song is being cached.")
            return
        if ctx.voice_client.is_playing():
            await log.warning("Music is being played already.")
            return
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            return
        if not self.queue[ctx.guild.id]:
            await log.warning("The queue is empty.")
            return

        data = self.queue[ctx.guild.id][0]
        del self.queue[ctx.guild.id][0]
        if not os.path.isfile(ytdl.prepare_filename(data)):
            await ctx.channel.send(
                "The song hasn't been played yet, please wait for it to cache."
            )
            self.caching.add(ctx.guild.id)
        source = await YTDLSource.from_url(data["webpage_url"])
        if ctx.guild.id in self.caching:
            self.caching.remove(ctx.guild.id)
            await ctx.channel.send("Caching finished!")
        ctx.voice_client.play(
            source,
            after=lambda x: asyncio.run_coroutine_threadsafe(
                self.play_from_queue(ctx), self.client.loop
            ),
        )

    @commands.slash_command(
        name="pause", description="Pause the current song.", guilds=[GuildID]
    )
    async def pause(self, ctx: commands.Context):
        if not ctx.voice_client.is_playing():
            await ctx.respond("No audio is being played.")
            return
        if ctx.voice_client.is_paused():
            await ctx.respond("The song is already paused.")
            return

        ctx.voice_client.pause()
        await ctx.respond("Paused.")

    @commands.slash_command(
        name="resume", description="Resume playing the song.", guilds=[GuildID]
    )
    async def resume(self, ctx: commands.Context):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("Resumed playing.")
        elif not ctx.voice_client.is_playing():
            await ctx.respond("No audio is being played.")
        else:
            await ctx.respond("The song is not paused.")
            return

    @commands.slash_command(
        name="disconnect",
        description="Disconnect from voice channel.",
        guilds=[GuildID],
    )
    async def disconnect(self, ctx: commands.Context):
        if not ctx.voice_client:
            await ctx.respond("Not connected to a channel.")
            return

        if ctx.guild.id in self.queue:
            del self.queue[ctx.guild.id]
        if ctx.guild.id in self.caching:
            self.caching.remove(ctx.guild.id)
        await ctx.voice_client.disconnect()
        await ctx.respond("Disconnected.")

    @commands.slash_command(
        name="skip", description="Skip the current song.", guilds=[GuildID]
    )
    async def skip(self, ctx: commands.Context):
        ctx.voice_client.stop()
        await self.play_from_queue(ctx)
        await ctx.respond("Skipped the current song!")

    @commands.slash_command(
        name="volume",
        description="Get or set the volume of the music.",
        guild_ids=[Home_Guild],
    )
    async def volume(
        self,
        ctx: commands.Context,
        volume: Option(float, "The volume to set to", required=False),
    ):
        if volume is None:
            await ctx.respond(
                f"The current volume of the bot is {self.volume[ctx.guild.id]}%"
            )
        elif volume <= 0 or volume > 150:
            await ctx.respond(f"The volume must be in interval (0; 150>.")
        else:
            self.volume[ctx.guild.id] = volume
            ctx.voice_client.source.volume = volume / 100
            await ctx.respond(f"Set the volume to {volume}%.")

    @commands.slash_command(
        name="clear_queue", description="Clear the music queue.", guild_ids=[Home_Guild]
    )
    async def clear_queue(self, ctx: commands.Context):
        del self.queue[ctx.guild.id]
        ctx.voice_client.stop()
        await ctx.respond("The queue has been cleared.")

    @play.before_invoke
    async def ensure_connect_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.respond("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

    @volume.before_invoke
    @skip.before_invoke
    async def ensure_playing(self, ctx):
        await self.ensure_voice(ctx)
        if not ctx.voice_client.is_playing():
            await ctx.respond("No song is being played.")
            raise commands.CommandError("No song is being played.")

    @pause.before_invoke
    @resume.before_invoke
    @volume.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            await ctx.respond("The bot is not connected to a channel.")
            raise commands.CommandError("The bot is not connected to a channel.")

    @pause.before_invoke
    @resume.before_invoke
    @volume.before_invoke
    @skip.before_invoke
    async def caching_lock(self, ctx):
        if ctx.guild.id in self.caching:
            await ctx.respond("Please wait, the song is being cached.")
            raise commands.CommandError("A song is being cached.")


def setup(client):
    client.add_cog(Music(client))
