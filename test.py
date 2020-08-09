import os
import asyncio

from sensor import BCHydroApi

a = BCHydroApi()


async def main():
    await a.authenticate(os.environ.get("BCH_USER"), os.environ.get("BCH_PASS"))
    print(a._slid)

    await a.fetch_data()
    print(a.data)

asyncio.run(main())
