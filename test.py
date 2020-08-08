import os
from sensor import BCHydroApi

a = BCHydroApi(os.environ.get("BCH_USER"), os.environ.get("BCH_PASS"))
a.login()
a.fetch_data()

print("data:")
print(a.data)

print("latest value")
print(a.get_latest_usage())

print("latest cost")
print(a.data["rates"]["consumption_to_date"])
