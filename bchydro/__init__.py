"""BCHydro API"""
from datetime import datetime
from typing import List


class BCHydroInterval:
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end


class BCHydroRates:
    def __init__(
        self,
        days_since_billing: int,
        consumption: float,
        cost: float,
        estimated_consumption: float,
        estimated_cost: float,
    ):
        self.days_since_billing = days_since_billing
        self.consumption = consumption
        self.cost = cost
        self.estimated_consumption = estimated_consumption
        self.estimated_cost = estimated_cost


class BCHydroDailyElectricity:
    def __init__(
        self,
        type: str,
        quality: str,
        consumption: float,
        interval: BCHydroInterval,
        cost: float,
    ):
        self.type = type
        self.quality = quality
        self.consumption = consumption
        self.interval = interval
        self.cost = cost


class BCHydroDailyUsage:
    def __init__(self, electricity: List[BCHydroDailyElectricity]):
        self.electricity = electricity


# Account details returned from the account JSON response.
# Only used fields are stored.
class BCHydroAccount:
    def __init__(
        self,
        evpSlid,
        evpAccount,
        evpAccountId,
        evpProfileId,
        evpRateGroup,
        evpBillingStart,
        evpBillingEnd,
        evpConsToDate,
        evpCostToDate,
        yesterdayPercentage,
        evpEstConsCurPeriod,
        evpEstCostCurPeriod,
        evpCurrentDateTime,
    ):
        self.evpSlid = evpSlid
        self.evpAccount = evpAccount
        self.evpAccountId = evpAccountId
        self.evpProfileId = evpProfileId
        self.evpRateGroup = evpRateGroup
        self.evpBillingStart = evpBillingStart
        self.evpBillingEnd = evpBillingEnd
        self.evpConsToDate = evpConsToDate
        self.evpCostToDate = evpCostToDate
        self.yesterdayPercentage = yesterdayPercentage
        self.evpEstConsCurPeriod = evpEstConsCurPeriod
        self.evpEstCostCurPeriod = evpEstCostCurPeriod
        self.evpCurrentDateTime = evpCurrentDateTime
