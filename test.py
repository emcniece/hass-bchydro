import os
from sensor import BCHydroApi

a = BCHydroApi(os.environ.get("BCH_USER"), os.environ.get("BCH_PASS"))
latest = a.latest_usage()
print("latest:")
print(latest)
