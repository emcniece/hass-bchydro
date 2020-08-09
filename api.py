import aiohttp
from datetime import date
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

URL_LOGIN = "https://app.bchydro.com/sso/UI/Login"
URL_ACCT_INFO = "https://app.bchydro.com/evportlet/web/global-data.html"
URL_GET_USAGE = "https://app.bchydro.com/evportlet/web/account-profile-data.html"

# This URL has more detail than URL_GET_USAGE but seems to require more headers to access.
# Not used at the moment, but ideally it will replace URL_GET_USAGE.
URL_GET_CONSUMPTION = "https://app.bchydro.com/evportlet/web/consumption-data.html"
USER_AGENT = "https://github.com/emcniece/hass-bchydro#disclaimer"


class BCHydroApi:
    def __init__(self):
        """Initialize the sensor."""
        self._account_number = None
        self._slid = None
        self._cookie_jar = None
        self._bchydroparam = None
        self._current_usage = None
        self._current_cost = None
        self.data = {"usage": [], "rates": {}}

    async def authenticate(self, username, password) -> bool:
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            response = await session.post(
                URL_LOGIN,
                data={
                    "realm": "bch-ps",
                    "email": username,
                    "password": password,
                    "gotoUrl": "https://app.bchydro.com:443/BCHCustomerPortal/web/login.html",
                },
            )
            response.raise_for_status()
            if response.status != 200:
                return False

            self._cookie_jar = session.cookie_jar

            # Can we find hydroparam?
            text = await response.text()
            soup = BeautifulSoup(text, features="html.parser")
            self._bchydroparam = soup.find(id="bchydroparam").text

            try:
                response = await session.get(URL_ACCT_INFO)
                json_response = await response.json()

                if "evpSlid" in json_response:
                    self._slid = json_response["evpSlid"]
                else:
                    raise Exception("Unable to find SLID in response")

                if "evpAccount" in json_response:
                    self._account_number = json_response["evpAccount"]
                else:
                    raise Exception("Unable to find account number in response")

            except Exception as e:
                _LOGGER.error("Auth error: %s", e)
                return False

        return True

    async def fetch_data(self):
        # By using `today` as both start and end date, we get a single <Point /> back from
        # the consumption endpoint and it's almost guaranteed to be of type 'ACTUAL'.
        # This is all HASS needs, so we can reduce our processing efforts by avoiding
        # multiple datapoints. Documenting here & now in case of future needs.
        today = date.today().strftime("%Y-%m-06T00:00:00-00:00:00")

        async with aiohttp.ClientSession(
            cookie_jar=self._cookie_jar, headers={"User-Agent": USER_AGENT}
        ) as session:
            response = await session.post(
                URL_GET_CONSUMPTION,
                data={
                    "Slid": self._slid,
                    "Account": self._account_number,
                    "ChartType": "column",
                    "Granularity": "daily",
                    "Overlays": "none",
                    "StartDateTime": today,
                    "EndDateTime": today,
                    "DateRange": "currentBill",
                    "RateGroup": "RES1",
                },
                headers={"bchydroparam": self._bchydroparam},
            )

            try:
                text = await response.text()
                root = ET.fromstring(text)
                point = root.find("Series").find("Point")
                rates = root.find("Rates")

                if point.get("quality") != "ACTUAL":
                    raise Exception(
                        "Found non-ACTUAL point: %s",
                        ET.tostring(root.find("Series").find("Point")),
                    )

                self._current_usage = point.get("value")
                self._current_cost = point.get("cost")

                self.data["rates"] = {
                    "billing_period_start": rates.get("bpStart"),
                    "billing_period_end": rates.get("bpEnd"),
                    "consumption_to_date": rates.get("cons2date").strip("kWh"),
                    "cost_to_date": rates.get("cost2date").strip("$"),
                    "estimated_consumption": rates.get("estCons").strip("kWh"),
                    "estimated_cost": rates.get("estCost").strip("$"),
                }

            except ET.ParseError as e:
                _LOGGER.error("Unable to parse XML from string: %s -- %s", e, text)
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                raise

    def get_latest_usage(self):
        return self.data["usage"][-1]["value"] if len(self.data["usage"]) else None

    def get_latest_cost(self):
        return self.data["usage"][-1]["cost"] if len(self.data["usage"]) else None
