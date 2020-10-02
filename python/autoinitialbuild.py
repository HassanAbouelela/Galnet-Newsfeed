#  Copyright (c) 2020 Hassan Abouelela
#  Licensed under the MIT License

import asyncio

from python import initialbuild


async def main():
    await initialbuild.db_builder(host="localhost", database="postgres")
    loop.stop()

loop = asyncio.get_event_loop()
try:
    loop.create_task(main())
    loop.run_forever()
finally:
    loop.close()
