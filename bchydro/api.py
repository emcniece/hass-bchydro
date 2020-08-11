import aiohttp
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from __init__ import (
    BCHydroAccount,
    BCHydroInterval,
    BCHydroRates,
    BCHydroDailyElectricity,
    BCHydroDailyUsage,
)

from const import (
    USER_AGENT,
    URL_POST_LOGIN,
    URL_GET_ACCOUNT_JSON,
    URL_POST_CONSUMPTION_XML,
)

_LOGGER = logging.getLogger(__name__)


class BCHydroApi:
    def __init__(self):
        """Initialize the sensor."""
        self._cookie_jar = None
        self._bchydroparam = None
        self.account: BCHydroAccount = None
        self.usage: BCHydroDailyUsage = None
        self.rates: BCHydroRates = None

    async def authenticate(self, username, password) -> bool:
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            response = await session.post(
                URL_POST_LOGIN,
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

            # Extract hydroparam from page HTML for use in the consumption endpoint.
            # The param appears twice: a hidden <input /> and a span with an id.
            text = await response.text()
            soup = BeautifulSoup(text, features="html.parser")
            self._bchydroparam = soup.find(id="bchydroparam").text

            try:
                response = await session.get(URL_GET_ACCOUNT_JSON)
                json_res = await response.json()

                self.account = BCHydroAccount(
                    json_res["evpSlid"],
                    json_res["evpAccount"],
                    json_res["evpAccountId"],
                    json_res["evpProfileId"],
                    json_res["evpRateGroup"],
                    json_res["evpBillingStart"],
                    json_res["evpBillingEnd"],
                    json_res["evpConsToDate"],
                    json_res["evpCostToDate"],
                    json_res["yesterdayPercentage"],
                    json_res["evpEstConsCurPeriod"],
                    json_res["evpEstCostCurPeriod"],
                    json_res["evpCurrentDateTime"],
                )

            except Exception as e:
                _LOGGER.error("Auth error: %s", e)
                return False

        return True

    async def get_daily_usage(self) -> BCHydroDailyUsage:
        async with aiohttp.ClientSession(
            cookie_jar=self._cookie_jar, headers={"User-Agent": USER_AGENT}
        ) as session:
            response = await session.post(
                URL_POST_CONSUMPTION_XML,
                data={
                    "Slid": self.account.evpSlid,
                    "Account": self.account.evpAccount,
                    "ChartType": "column",
                    "Granularity": "daily",
                    "Overlays": "none",
                    "DateRange": "currentBill",
                    "StartDateTime": self.account.evpBillingStart,
                    "EndDateTime": self.account.evpBillingEnd,
                    "RateGroup": self.account.evpRateGroup,
                },
                headers={"bchydroparam": self._bchydroparam},
            )

            try:
                text = await response.text()
                root = ET.fromstring(text)
                new_usage: BCHydroDailyUsage = []

                for point in root.findall("Series")[0].findall("Point"):
                    interval = BCHydroInterval(
                        point.get("dateTime"), point.get("endTime")
                    )

                    new_usage.append(
                        BCHydroDailyElectricity(
                            type=point.get("type"),
                            quality=point.get("quality"),
                            consumption=point.get("value"),
                            interval=interval,
                            cost=point.get("cost"),
                        )
                    )

                self.usage = BCHydroDailyUsage(new_usage)

                rates = root.find("Rates")
                self.rates = BCHydroRates(
                    rates.get("daysSince"),
                    rates.get("cons2date"),
                    rates.get("cost2date"),
                    rates.get("estCons"),
                    rates.get("estCost"),
                )

            except ET.ParseError as e:
                _LOGGER.error("Unable to parse XML from string: %s -- %s", e, text)
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                raise

        return self.usage

    def is_valid(self, point):
        return point.quality == "ACTUAL"

    def get_latest_point(self) -> BCHydroDailyElectricity:
        valid = list(filter(self.is_valid, self.usage.electricity))
        return valid[-1] if len(valid) else None

    def get_latest_interval(self) -> BCHydroInterval:
        valid = list(filter(self.is_valid, self.usage.electricity))
        return valid[-1].interval if len(valid) else None

    def get_latest_usage(self):
        valid = list(filter(self.is_valid, self.usage.electricity))
        return valid[-1].consumption if len(valid) else None

    def get_latest_cost(self):
        valid = list(filter(self.is_valid, self.usage.electricity))
        return valid[-1].cost if len(valid) else None
