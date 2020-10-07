#  Copyright (c) 2020 Hassan Abouelela
#  Licensed under the MIT License

import asyncio

from python import initialbuild

loop = asyncio.get_event_loop()
loop.run_until_complete(initialbuild.db_builder(host="localhost", database="postgres"))
loop.close()
