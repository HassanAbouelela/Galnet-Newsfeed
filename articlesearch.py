import aiohttp
from bs4 import BeautifulSoup as Bs4
import asyncpg
import re
import datetime
from urllib.parse import unquote


async def connect(host: str = "localhost", database: str = "postgres", user: str = "postgres",
                  port: int = None, password: str = None, passfile=None, ssl=False):
    """Connects to a database"""
    connection = await asyncpg.connect(host=host, port=port, user=user, password=password,
                                       passfile=passfile, database=database, ssl=ssl)
    return connection


async def update():
    """Looks for new articles."""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://community.elitedangerous.com/") as response:
            html = Bs4(await response.text(), "html.parser")
    connection = await connect()
    uids = []
    new_articles = []
    uid_records = await connection.fetch(f"""
                SELECT "UID" FROM "Articles" ORDER BY "dateReleased" DESC LIMIT 50;
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
        INSERT INTO "Articles"("Title", "UID", "dateReleased", "dateAdded", "Text") VALUES (
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
            if option == "limitall":
                limit = 10000000
            elif "limit" in option:
                try:
                    limit = int(option[6:])
                except ValueError:
                    limit = 5
            elif "before" in option:
                dateend = option[7:]
                options.append("before")
            elif "after" in option:
                datebegin = option[6:]
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
        SELECT * FROM "Articles" 
        WHERE "dateReleased" BETWEEN '{datebegin}' AND '{dateend}'
        ORDER BY "dateReleased" {searchorder};
        """)
    elif "before" in options:
        rows = await connection.fetch(f"""
                SELECT * FROM "Articles" 
                WHERE "dateReleased" < '{dateend}'
                ORDER BY "dateReleased" {searchorder};
                """)
    elif "after" in options:
        rows = await connection.fetch(f"""
                    SELECT * FROM "Articles" 
                    WHERE "dateReleased" > '{datebegin}'
                    ORDER BY "dateReleased" {searchorder};
                    """)
    else:
        rows = await connection.fetch(f"""
        SELECT * FROM "Articles" ORDER BY "dateReleased" {searchorder};
        """)
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
    await connection.close()
    return results[:limit], len(results)


async def read(articleid=True, uid=False):
    """Returns the article with the matching ID.
    If the input is invalid or the article is not found, empty list is returned."""
    if uid:
        connection = await connect()
        row = await connection.fetch(f"""
        SELECT * FROM "Articles" WHERE "UID" = '{uid}';
        """)
        await connection.close()
        return row
    try:
        articleid = int(articleid)
    except ValueError:
        return []
    connection = await connect()
    row = await connection.fetch(f"""
    SELECT * FROM "Articles" WHERE "ID" = {articleid};
    """)
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
    options = options.replace("--all", "--searchall")
    results = await search(f"--limitall {options}")
    return results[1]
