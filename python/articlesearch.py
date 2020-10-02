#  Copyright (c) 2020 Hassan Abouelela
#  Licensed under the MIT License

import datetime
import json
import os
import re
from urllib.parse import unquote

import aiohttp
import asyncpg
from bs4 import BeautifulSoup as Bs4


async def fetch_settings():
    async with aiohttp.ClientSession() as settings_session:
        async with settings_session.get(
                "https://raw.githubusercontent.com/HassanAbouelela/Galnet-Newsfeed/"
                "d75fb12bd48c23b1fc1acdecf240857df231e3b1/python/Settings.json") as response:
            if response.status == 200:
                raw_json = json.loads(await response.read())
    with open("Settings.json", "w+") as file:
        json.dump(raw_json, file, indent=2)


async def connect(host: str = "localhost", database: str = "postgres", user: str = "postgres",
                  port: int = None, password: str = None, passfile=None, ssl: bool = False, use_file: bool = True):
    """Connects to a database"""
    if use_file:
        # Load Settings
        if not os.path.exists("Settings.json"):
            await fetch_settings()
        with open("Settings.json") as file:
            settings = json.load(file)
        host = settings["host"]
        database = settings["database"]
        user = settings["user"]
        passfile = settings["passfile"]
        password = settings["password"]
        ssl = settings["ssl"]
        port = settings["port"]
    connection = await asyncpg.connect(host=host, port=port, user=user, password=password,
                                       passfile=passfile, database=database, ssl=ssl)
    return connection


async def update():
    """Looks for new articles."""
    # Load Settings
    if not os.path.exists("Settings.json"):
        await fetch_settings()
    with open("Settings.json") as file:
        settings = json.load(file)
    table = settings["table"]
    async with aiohttp.ClientSession() as session:
        async with session.get("https://community.elitedangerous.com/") as response:
            html = Bs4(await response.text(), "html.parser")
    connection = await connect()
    uids = []
    new_articles = []
    uid_records = await connection.fetch(f"""
                SELECT "UID" FROM "{table}" ORDER BY "dateReleased" DESC LIMIT 50;
                """)
    for record in uid_records:
        uids.append(record["UID"])
    for entry in html.find_all("h3", {"class": "hiLite galnetNewsArticleTitle"}):
        entry = entry.find("a").get("href")[re.search("^/galnet/uid/", entry.find("a").get("href")).end():]
        if entry not in uids:
            new_articles.append(entry)
    for article in new_articles:
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://community.elitedangerous.com/galnet/uid/{article}") as response:
                bs4 = Bs4(await response.text(), "html.parser")
        entry = bs4.find("h3", {"class": "hiLite galnetNewsArticleTitle"})
        entry_title = entry.get_text().strip().replace("'", "''")
        if entry_title == "" or entry_title is None:
            entry_title = "No Title Available"
        date_article = bs4.find("p").get_text()
        if "29 FEB" in date_article:
            date_clean = date_article[re.search("^29 FEB ", date_article).end():].replace("#", "")
            date_article = f"{date_clean}-02-28"
        else:
            date_article = datetime.datetime.strptime(date_article, "%d %b %Y").strftime("%Y-%m-%d")
        text = unquote(bs4.find_all("p")[1].get_text().replace("'", "''"))
        await connection.execute(f"""
        INSERT INTO "{table}"("Title", "UID", "dateReleased", "dateAdded", "Text") VALUES (
        '{entry_title}', '{article}', '{date_article}', '{date_today}', '{text}');
        """)
    await connection.close()
    if len(new_articles) > 0:
        return len(new_articles), new_articles


async def search(terms):
    """Searches the DB for given input.
    Options:
    --title: Searches only in the titles of the articles (default search mode)
    --content: Searches only in the content of an article, and ignores the title
    --searchall: Searches both title and content of an article
    --searchreverse: Searches the DB from the oldest article
    --limit: Returns only the latest results up to number given (default 5). Format: limit=XYZ
    --limitall: Returns all results found
    --before: Looks for articles that were written before a given date. Format: YYYY-MM-DD
    --after: Looks for articles that were written after a given date. Format: YYYY-MM-DD
    If both the --after & --before tags are given, the search is limited to the dates between both options."""

    # Load Settings
    if not os.path.exists("Settings.json"):
        await fetch_settings()
    with open("Settings.json") as file:
        settings = json.load(file)
    table = settings["table"]

    if ";" in terms:
        terms.replace(";", "")
        return "You can't use ';' in your searches!"
    terms = terms.split(" ")
    options = []
    words = []
    results = []
    limit = 5
    searchorder = "DESC"
    datebegin = "0000-00-00"
    dateend = "4000-01-01"

    # Separating Options and Search Terms
    for item in terms:
        if "--" in item[:2]:
            option = item.replace("--", "")
            if option == "limitall" or option == "listall":
                limit = 10000000
            elif "limit" in option:
                try:
                    limit = int(option[6:])
                except ValueError:
                    limit = 5
            elif "before" in option:
                year = datetime.datetime.strptime(option[7:], "%Y-%m-%d").strftime("%Y")
                # Convert date to format stored table
                if int(year) < 3300:
                    converted_year = str(3300 + (int(year) - 2014)) + option[11:]
                    dateend = datetime.datetime.strptime(converted_year, "%Y-%m-%d")
                else:
                    dateend = datetime.datetime.strptime(option[7:], "%Y-%m-%d")
                options.append("before")
            elif "after" in option:
                year = datetime.datetime.strptime(option[6:], "%Y-%m-%d").strftime("%Y")
                # Convert date to format stored in table
                if int(year) < 3300:
                    converted_year = str(3300 + (int(year) - 2014)) + option[10:]
                    datebegin = datetime.datetime.strptime(converted_year, "%Y-%m-%d")
                else:
                    datebegin = datetime.datetime.strptime(option[6:], "%Y-%m-%d")
                options.append("after")
            elif option == "searchreverse":
                searchorder = "ASC"
            else:
                options.append(option)
        else:
            words.append(item.lower())

    # Searching
    connection = await connect()
    if "before" in options and "after" in options:
        rows = await connection.fetch(f"""
        SELECT * FROM "{table}" 
        WHERE "dateReleased" BETWEEN $1 AND $2
        ORDER BY "dateReleased" {searchorder};
        """, datebegin, dateend)
    elif "before" in options:
        rows = await connection.fetch(f"""
                SELECT * FROM "{table}" 
                WHERE "dateReleased" < $1
                ORDER BY "dateReleased" {searchorder};
                """, dateend)
    elif "after" in options:
        rows = await connection.fetch(f"""
                    SELECT * FROM "{table}" 
                    WHERE "dateReleased" > $1
                    ORDER BY "dateReleased" {searchorder};
                    """, datebegin)
    else:
        rows = await connection.fetch(f"""
        SELECT * FROM "{table}" ORDER BY "dateReleased" {searchorder};
        """)
    await connection.close()
    if "searchall" in options:
        for row in rows:
            for word in words:
                if word in row["Title"].lower():
                    results.append(row)
                if word in row["Text"].lower():
                    if row in results:
                        pass
                    else:
                        results.append(row)
    elif "content" in options:
        for row in rows:
            for word in words:
                if word in row["Text"].lower():
                    results.append(row)
    else:
        for row in rows:
            for word in words:
                if word in row["Title"].lower():
                    results.append(row)
    return results[:limit], len(results)


async def read(articleid=True, uid=False):
    """Returns the article with the matching ID.
    If the input is invalid or the article is not found, empty list is returned."""

    # Load Settings
    if not os.path.exists("Settings.json"):
        await fetch_settings()
    with open("Settings.json") as file:
        settings = json.load(file)
    table = settings["table"]

    if uid:
        connection = await connect()
        row = await connection.fetch(f"""
        SELECT * FROM "{table}" WHERE "UID" = $1;
        """, str(uid))
        await connection.close()
        return row
    try:
        articleid = int(articleid)
    except ValueError:
        return []
    connection = await connect()
    row = await connection.fetch(f"""
    SELECT * FROM "{table}" WHERE "ID" = $1;
    """, articleid)
    await connection.close()
    return row


async def count(options):
    """Counts the amount of articles that fit the given conditions.
    Options:
    --title: Counts the amount of articles that contain a certain term in the title.
    --content: Counts the amount of articles that contain a certain term only in their content.
    --all: Counts the amount of articles that contain a certain term in either the title or the content.
    --before: Counts the amount of articles before a given date. Format: YYYY-MM-DD
    --after: Counts the amount of articles after a given date. Format: YYYY-MM-DD
    If both the --after & --before tags are given, the search is limited to the dates between both options."""
    if ";" in options:
        options.replace(";", "")
        return "You can't use ';'!"
    options = options.replace("--all", "--searchall")
    results = await search(f"--limitall {options}")
    return results[1]
