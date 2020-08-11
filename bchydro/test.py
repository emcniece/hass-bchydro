import os
import asyncio

from api import BCHydroApi

a = BCHydroApi()

async def main():
    await a.authenticate(os.environ.get("BCH_USER"), os.environ.get("BCH_PASS"))

    usage = await a.get_daily_usage()
    print(usage)

    print(a.get_latest_point())
    print(a.get_latest_interval().start, a.get_latest_interval().end)
    print(a.get_latest_usage())
    print(a.get_latest_cost())

asyncio.run(main())
