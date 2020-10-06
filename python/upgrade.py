#  Copyright (c) 2020 Hassan Abouelela
#  Licensed under the MIT License

from python import articlesearch
import asyncio
import datetime


async def clean_up():
    starting_time = datetime.datetime.now()
    print(f"Starting... ({starting_time})")
    await articlesearch.clean_up()
    print(f"Done ({datetime.datetime.now()})")
    print(f"Time taken: {datetime.datetime.now() - starting_time}")

asyncio.get_event_loop().run_until_complete(clean_up())
