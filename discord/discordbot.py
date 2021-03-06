#  Copyright (c) 2020 Hassan Abouelela
#  Licensed under the MIT License

import asyncio
import json
import logging
import os

import aiohttp
import discord as discord
import math
from discord.ext import commands

from python import articlesearch

logger = logging.getLogger("galnet_discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="galnet_discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


# Loading Settings
def download_settings():
    async def fetch_settings():
        async with aiohttp.ClientSession() as settings_session:
            async with settings_session.get(
                    "https://raw.githubusercontent.com/HassanAbouelela/Galnet-Newsfeed/"
                    "4499a01e6b5a679b807e95697effafde02f8d5e0/discord/BotSettings.json") as response:
                if response.status == 200:
                    raw_json = json.loads(await response.read())
        with open("BotSettings.json", "w+") as file:
            json.dump(raw_json, file, indent=2)

    asyncio.get_event_loop().run_until_complete(fetch_settings())


if not os.path.exists("BotSettings.json"):
    download_settings()
    raise RuntimeError("Please fill in bot settings file: `BotSettings.json`")


with open("BotSettings.json") as settings_file:
    settings = json.load(settings_file)
    if not all(key in settings.keys() for key in ("Maintainer-ID", "TOKEN", "PREFIX")):
        print(RuntimeWarning("Error reading bot settings file."))
    if settings["PREFIX"] == "_mention":
        settings["PREFIX"] = commands.when_mentioned
    else:
        settings["PREFIX"] = settings["PREFIX"].split(",")


bot = commands.Bot(command_prefix=settings["PREFIX"], case_insensitive=True, help_command=None)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        if ctx.invoked_with == "read":
            await ctx.send("That ID is not valid. The ID must be a number.")
        else:
            await ctx.send(f"{error.args}. Please send this to the developer.")
        return
    elif isinstance(error, commands.CommandNotFound):
        if settings["PREFIX"] == commands.when_mentioned:
            await ctx.send(f"That is not a valid command. Try: {bot.get_user(bot.user.id).mention} help")
        else:
            await ctx.send(f"That is not a valid command. Try: {settings['PREFIX']}help")

        return
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use this command.")
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
        return
    elif isinstance(error, commands.CommandInvokeError):
        if type(error.original) == discord.errors.Forbidden:
            try:
                await ctx.send("The bot doesn't have permission to send embeds here.")
            except discord.errors.Forbidden:
                logger.warning(error)
                raise error
        else:
            logger.warning(error)
            raise error
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        if ctx.invoked_with.lower() == "search":
            if settings["PREFIX"] == commands.when_mentioned:
                await ctx.send(f"That is an invalid query. Try: {bot.get_user(bot.user.id).mention} help search")
            else:
                await ctx.send(f"That is an invalid query. Try: {settings['PREFIX']}help search")
            return

        elif ctx.invoked_with.lower() == "count":
            if settings["PREFIX"] == commands.when_mentioned:
                await ctx.send(f"Count requires at least one search term."
                               f" Try: {bot.get_user(bot.user.id).mention} help count")
            else:
                await ctx.send(f"Count requires at least one search term."
                               f" Try: {settings['PREFIX']}help count")

            return

        else:
            if settings["PREFIX"] == commands.when_mentioned:
                await ctx.send(f"A required argument is missing."
                               f" Try: {bot.get_user(bot.user.id).mention} help {ctx.invoked_with.lower()}")
            else:
                await ctx.send(f"A required argument is missing."
                               f" Try: {settings['PREFIX']}help {ctx.invoked_with.lower()}")

            return
    logger.error(error)
    raise error


@bot.event
async def on_ready():
    print("(Re)Started")
    if settings["PREFIX"] == commands.when_mentioned:
        await bot.change_presence(activity=discord.Game(name=f"@{bot.user.name} help"))
    else:
        await bot.change_presence(activity=discord.Game(name=f"{settings['PREFIX']}help"))


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong `{round(bot.latency * 1000)} ms`")


@bot.command()
@commands.is_owner()
async def stop(ctx):
    try:
        print("Bot has been turned off by: {}".format(ctx.author))
        logger.warning("Bot has been turned off by: {}".format(ctx.author))

        await bot.get_user(int(settings["Maintainer-ID"])).send("Bot has been turned off by: {}".format(ctx.author))

    finally:
        await bot.close()


@bot.command()
async def search(ctx, *, terms):
    temp_msg = await ctx.send("Searching")
    results = await articlesearch.search(terms)
    final = {}
    embeds = math.floor(len(results[0]) / 8)
    if len(results[0]) % 8:
        embeds += 1
    if embeds == 0 and results[1] > 0:
        embeds = 1
    current_embed = 1
    numbers = ["\u0031\u20E3",
               "\u0032\u20E3",
               "\u0033\u20E3",
               "\u0034\u20E3",
               "\u0035\u20E3",
               "\u0036\u20E3",
               "\u0037\u20E3",
               "\u0038\u20E3"]
    start = 0
    end = 8
    await temp_msg.delete()
    if results[1] == 0:
        await ctx.send("No results match your query")
        return
    cont = True
    while cont:
        embed = discord.Embed(
            title=f"Here are your search results | Page {current_embed} / {embeds}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"{results[1]} Results Found")
        embed.add_field(name="Key", value="ID | Title | Date Released", inline=False)
        i = 1
        for row in results[0][start:end]:
            embed.add_field(name=f"Option {i}", value=f"{row['ID']} | {row['Title']} | "
                                                      f"{row['dateReleased'].strftime('%d %b %Y')}", inline=False)
            final[i] = row['ID']
            i += 1
        message = await ctx.send(embed=embed)
        ids = {ctx.message.id: message.id}
        number = 0
        if current_embed > 1:
            await message.add_reaction("\u23EA")
        while number < len(results[0][start:end]):
            await message.add_reaction(numbers[number])
            number += 1
        if current_embed < embeds:
            await message.add_reaction("\u23E9")

        def check(payload):
            if payload.user_id != ctx.author.id:
                return False
            if payload.message_id != ids[ctx.message.id]:
                return False
            if payload.emoji.name in numbers:
                pass
            elif payload.emoji.name == "\u23E9" or payload.emoji.name == "\u23EA":
                pass
            else:
                return False
            return True

        try:
            reaction = await bot.wait_for("raw_reaction_add", timeout=120.0, check=check)
            if reaction.emoji.name == "\u23E9":
                await message.delete()
                current_embed += 1
                start += 8
                end += 8
            elif reaction.emoji.name == "\u23EA":
                await message.delete()
                current_embed -= 1
                start -= 8
                end -= 8
            elif reaction.emoji.name in numbers:
                result = await command_read(final[numbers.index(reaction.emoji.name) + 1])
                await ctx.send(embed=result[0])
                await message.delete()
                cont = False
        except asyncio.TimeoutError:
            try:
                await ctx.send(f"Are you still there {ctx.author.mention}? Your search timed out, please start over.")
                await message.clear_reactions()
                cont = False
            except discord.Forbidden:
                cont = False
                pass


@search.error
async def search_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        return ctx
    return


@bot.command()
async def count(ctx, *, terms):
    await ctx.send(f"{await articlesearch.count(terms)} results found.")


@bot.command()
async def update(ctx):
    await command_update()
    await ctx.send("Done")


async def command_update():
    result = await articlesearch.update()

    if result:
        article_number = result[0]
        article_uids = result[1]
        if not os.path.exists("newschannels.txt"):
            return
        with open("newschannels.txt", "r") as file:
            if int(article_number) == 1:
                for channelid in file.readlines():
                    try:
                        await bot.get_channel(int(channelid)).send("1 new article added")
                    except AttributeError:
                        with open("newschannels.txt", "r") as newslist:
                            lines = newslist.readlines()
                        with open("newschannels.txt", "w") as newslist:
                            for line in lines:
                                if line != channelid:
                                    newslist.write(line)
            else:
                for channelid in file.readlines():
                    try:
                        await bot.get_channel(int(channelid)).send(f"{article_number} new articles added")
                    except AttributeError:
                        with open("newschannels.txt", "r") as newslist:
                            lines = newslist.readlines()
                        with open("newschannels.txt", "w") as newslist:
                            for line in lines:
                                if line != channelid:
                                    newslist.write(line)
            for article in article_uids:
                row = await articlesearch.read(uid=article)

                file.seek(0)
                for channelid in file.readlines():
                    try:
                        embed = await command_read(0, row)
                        try:
                            await bot.get_channel(int(channelid)).send(embed=embed[0])
                        except discord.HTTPException as e:
                            import datetime
                            await bot.get_user(int(settings["Maintainer-ID"])).send(
                                "Error updating news base. Message too long, could not fix `CS{}-{}`"
                                " .\nText: {}. \nCode: {}."
                            ).format(datetime.datetime.now().strftime('%d%m%y%H%M'), article, e.text, e.code)
                    except AttributeError:
                        pass


@bot.command()
async def read(ctx, articleid: int):
    result = await command_read(articleid)

    if result == "Nothing Found":
        await ctx.send(result)
    else:
        try:
            await ctx.send(embed=result[0])
        except discord.HTTPException:
            import datetime
            await ctx.send("An error was encountered. For now, feel free to read the article on the official website:"
                           f"\nhttps://community.elitedangerous.com/galnet/uid/{result[1]}"
                           "\n\nPlease submit a report at the issues page, and include this error code"
                           f" `CS{datetime.datetime.now().strftime('%d%m%y%H%M')}-{articleid}` and a brief description"
                           " of what happened:"
                           "\n<https://github.com/HassanAbouelela/Galnet-Newsfeed/issues/new?assignees=&labels"
                           "=&template=bug_report.md&title=Bug>")
            return


async def command_read(articleid: int, command_up: tuple = False):
    if not command_up:
        row = await articlesearch.read(articleid)
    else:
        row = command_up
    if not row:
        return "Nothing Found"
    row = row[0]

    # Making sure the message fits
    remaining = 6000
    sixk = False

    title = row["Title"]
    description = row["Text"].replace("\n", "\n\n")
    footer = (f"ID: {row['ID']}"
              f" | Date Released: {row['dateReleased'].strftime('%d %b %Y')}"
              f" | Date Indexed: {row['dateAdded'].strftime('%d %b %Y')}")

    if len(title) + len(description) + len(footer) > 6000:
        if len(title) > 256:
            if title[:250].rfind(" ") != -1:
                title = title[:title[:250].rfind(" ")] + "..."
            else:
                title = title[:256]
        remaining -= (len(title) + len(footer))
        sixk = True

    if len(title) > 256:
        if title[:250].rfind(" ") != -1:
            title = title[:title[:250].rfind(" ")] + "..."
        else:
            title = title[:256]

    if len(description) + len(footer) > 2048 or sixk:
        remaining_len = 2048 - len(footer)
        if remaining < remaining_len:
            pass
        else:
            remaining = remaining_len
        if description[:remaining - 10].rfind(".") != -1:
            description = description[:description[:remaining].rfind(".")] +\
                          f" [[...]](http://community.elitedangerous.com/galnet/uid/{row['UID']})"
        else:
            description = description[:remaining - 5] +\
                          f" [[...]](http://community.elitedangerous.com/galnet/uid/{row['UID']})"

    embed = discord.Embed(
        title=title,
        url=f"http://community.elitedangerous.com/galnet/uid/{row['UID']}",
        description=description,
        color=discord.Color.orange()
    )
    embed.set_footer(text=footer)
    return [embed, row["UID"]]


@bot.command()
async def newschannel(ctx):
    if ctx.message.guild is None or ctx.author.guild_permissions.manage_channels:
        keep = True
        with open("newschannels.txt", "a+") as newslist:
            newslist.seek(0)
            for line in newslist.readlines():
                if str(ctx.channel.id) in str(line):
                    keep = False
        if keep:
            with open("newschannels.txt", "a+") as newslist:
                newslist.write(f"{str(ctx.channel.id)}\n")
            await ctx.send("Channel added to newslist.")
        else:
            with open("newschannels.txt", "r") as old:
                with open("tempchannelslist.txt", "w") as new:
                    for line in old:
                        if str(ctx.channel.id) not in str(line):
                            new.write(line)
            os.remove("newschannels.txt")
            os.rename("tempchannelslist.txt", "newschannels.txt")
            await ctx.send("Channel removed from newslist.")
    else:
        await ctx.send("You don't have permission to use this command.")


@bot.command()
async def help(ctx, command: str = None):
    embed = discord.Embed(
        title="Galnet Commands",
        description="These are the available commands. To learn more about any command, type: `help command`",
        color=discord.Color.orange()
    )
    embed.add_field(name="Ping", value="Checks if the bot is online.", inline=False)
    embed.add_field(name="Search",
                    value="Searches the database based on the given options. Format: search --options keywords",
                    inline=False)
    embed.add_field(name="Count",
                    value="Counts the amount of the given input. Format: count --options keywords",
                    inline=False)
    embed.add_field(name="Update", value="Checks for new articles", inline=False)
    embed.add_field(name="Read", value="Opens an article for reading. Format: read (id)", inline=False)
    embed.add_field(name="NewsChannel", value="Marks the channel where this command is run as a news channel",
                    inline=False)
    embed.add_field(name="Source", value="Links to [github page](https://github.com/HassanAbouelela/Galnet-Newsfeed/"
                                         "wiki), and [bot invite link](https://discordapp.com/oauth2/authorize?client"
                                         "_id=624620325090361354&permissions=379968&scope=bot)", inline=False)
    embed.add_field(name="Bugs", value="[Link to submit bugs/feedback.](https://github.com/"
                                       "HassanAbouelela/Galnet-Newsfeed/issues/new)", inline=False)
    embed.add_field(name="Help", value="This menu. Format: help (command)", inline=False)
    if command:
        command = command.lower().strip()
        if command == "ping":
            embed = discord.Embed(
                title="Ping",
                description="Check if the bot is online",
                color=discord.Color.orange()
            )
        elif command == "search":
            embed = discord.Embed(
                title="Search",
                description="Searches the database based on the given options. "
                            "You can read any result by clicking the matching ID below the result, "
                            "or by using the `read` command.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Format", value="search --options keywords", inline=False)
            embed.add_field(name="Options", value="""
All options must be preceded by (--).
A full list is [available here.](https://github.com/HassanAbouelela/Galnet-Newsfeed/wiki/Usage#search)
- title: Searches only in the titles of the articles (default search mode)
- content: Searches only in the content of an article, and ignores the title
- searchall: Searches both title and content of an article
- searchreverse: Searches the DB from the oldest article
- limit: Returns only the latest results up to number given (default 5). Format: limit=XYZ
- limitall: Returns all results found
- before: Looks for articles that were written before a given date. Format: YYYY-MM-DD
- after: Looks for articles that were written after a given date. Format: YYYY-MM-DD
(If both the --after & --before tags are given, the search is limited to the dates between both options.)
                                                  """, inline=False)
        elif command == "count":
            embed = discord.Embed(
                title="Count",
                description="Counts the amount of articles that fit the given conditions.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Format", value="count --options keywords", inline=False)
            embed.add_field(name="Options", value="""
All options must be preceded by (--).
A full list is [available here.](https://github.com/HassanAbouelela/Galnet-Newsfeed/wiki/Usage#count)
- title: Counts the amount of articles that contain a certain term in the title.
- content: Counts the amount of articles that contain a certain term only in their content.
- all: Counts the amount of articles that contain a certain term in either the title or the content.
- before: Counts the amount of articles before a given date. Format: YYYY-MM-DD
- after: Counts the amount of articles after a given date. Format: YYYY-MM-DD
(If both the --after & --before tags are given, the search is limited to the dates between both options.)
            """, inline=False)
        elif command == "update":
            embed = discord.Embed(
                title="Update",
                description="Checks for new articles",
                color=discord.Color.orange()
            )
        elif command == "read":
            embed = discord.Embed(
                title="Read",
                description="Sends an article to read. (Embeds must be enabled)",
                color=discord.Color.orange()
            )
            embed.add_field(name="Format", value="read ID", inline=False)
        elif command == "newschannel":
            embed = discord.Embed(
                title="NewsChannel",
                description="Marks the channel where this command is run as a news channel",
                color=discord.Color.orange()
            )
            embed.add_field(name="Extra Info.", value="The bot must have message access, and embed permissions"
                                                      " in this channel. The \"Manage Channel\" permission is required"
                                                      " to use this command.", inline=False)
        elif command == "source":
            embed = discord.Embed(
                title="Source",
                description="Links to [github page](https://github.com/HassanAbouelela/Galnet-Newsfeed/wiki),"
                            " and [bot invite link](https://discordapp.com/oauth2/authorize?client"
                            "_id=624620325090361354&permissions=379968&scope=bot)",
                color=discord.Color.orange()
            )
        elif command == "bugs":
            embed = discord.Embed(
                title="Bugs",
                description="[Link to submit bugs/feedback.](https://github.com/"
                            "HassanAbouelela/Galnet-Newsfeed/issues/new)",
                color=discord.Color.orange()
            )
        elif command == "help":
            embed = discord.Embed(
                title="Help",
                description="Sends help for a command.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Format", value="help (command)", inline=False)
    await ctx.send(embed=embed)


async def sync():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await bot.change_presence(activity=discord.Game(name=f"@{bot.user.name} help"))
        await command_update()
        await asyncio.sleep(900)


bg_task = bot.loop.create_task(sync())
bot.run(settings["TOKEN"])
