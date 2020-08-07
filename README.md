# Home Assistant BCHydro Sensor

🚧 In development, but you can copy `sensor.py` down to your HASS install: just copy-paste `sensor.py` into a file name the same inside your HASS `custom_components/bchydro` directory. Edit `bchydro_username` and `bchydro_password` to match your BCHydro account.

## BCHydro Data Formats

Several calls are made to the BCHydro website for varying purposes.


### Account Data

The `URL_ACCT_INFO` URL is used to obtain the user account `slid` which is later used for fetching usage data. This endpoint has a lot of other info that might be useful for consumption at a later time - here's a sample of the JSON response:

```js
{
  "accountType": "residential",
  "evpSlid": "0001111111",
  "evpAccount": "000011111111",
  "evpAccountId": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
  "evpProfileId": "bchusername",
  "evpRateCategory": "BCRSE1101",
  "evpBillingClass": "Residential",
  "evpRateGroup": "RES1",
  "evpReadRoute": "BAAAAAAA",
  "evpBillingStart": "2020-06-06T00:00:00-07:00",
  "evpBillingEnd": "2020-08-06T00:00:00-07:00",
  "evpBilledStart": "2020-04-07T00:00:00-07:00",
  "evpBilledEnd": "2020-06-05T00:00:00-07:00",
  "evpValidityStart": "2020-06-29T00:00:00-07:00",
  "evpValidityEnd": "9999-12-31T00:00:00-08:00",
  "evpEnablementDate": "2012-12-23T23:00:00-08:00",
  "evpHeatingType": "N",
  "evpPremiseType": "10",
  "evpPostalCode": "V1V 1V1",
  "evpBillingArea": "99",
  "evpConsToDate": "584kWh",
  "evpCostToDate": "$67",
  "yesterdayPercentage": "97",
  "evpStepThreshold": "1375.89",
  "evpDaysInBillingPeriod": "62",
  "evpStepThresholdDate": "",
  "evpEstConsCurPeriod": "594",
  "evpEstCostCurPeriod": "68",
  "evpCurrentDateTime": "2020-08-06T23:30:46-07:00",
  "evpRole": "user",
  "evpCsrId": "bchusername",
  "evpComLastBillingPeakDemand": "",
  "evpComLastBillingPowerFactor": "",
  "enableSMSAlerts": "true",
  "nonWan": "False",
  "timezone": "GMT",
  "isEnDateinCBP": "True"
}
```


### Usage Data

Points may be one of `INVALID`, `ACTUAL`, `ESTIMATED`(?). While evidence of `ESTIMATED` has been captured it seems to occur infrequently. This is something to plan for in the future and is noted in the ToDo.

After logging in, the usage `URL_GET_USAGE` URL returns data like this:

```html
<Data>
  <Rates rateGroup="RES1" bpStart="Jun 6" bpEnd="Aug 6, 2020" daysSince="61" cons2date="584kWh" cost2date="$67" estCons="594" estCost="68"/>
  <Series name="Consumption data" step2Value="1375.89" isEnDateinCBP="true" evpCurrentDateTime="2020-08-06T22:41:06-07:00" blockStatus="0" nonWan="false">
    <Point type="SMI" quality="ACTUAL" dateTime="2020-07-30T00:00:00-07:00" endTime="2020-07-30T00:00:00-07:00" value="16.88" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-07-31T00:00:00-07:00" endTime="2020-07-31T00:00:00-07:00" value="12.36" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-08-01T00:00:00-07:00" endTime="2020-08-01T00:00:00-07:00" value="18.31" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-08-02T00:00:00-07:00" endTime="2020-08-02T00:00:00-07:00" value="16.27" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-08-03T00:00:00-07:00" endTime="2020-08-03T00:00:00-07:00" value="12.46" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-08-04T00:00:00-07:00" endTime="2020-08-04T00:00:00-07:00" value="14.66" cost="0.00"/>
    <Point type="SMI" quality="ACTUAL" dateTime="2020-08-05T00:00:00-07:00" endTime="2020-08-05T00:00:00-07:00" value="16.31" cost="0.00"/>
  </Series>
</Data>
```

In the sensor API, each of these `<Point />` elements is processed like so:

```py
for point in root.findall('Series')[0].findall('Point'):
    print(point.items())
    # [
    #   ('type', 'SMI'),
    #   ('quality', 'ACTUAL'),
    #   ('dateTime', '2020-07-30T00:00:00-07:00'),
    #   ('endTime', '2020-07-30T00:00:00-07:00'),
    #   ('value', '16.88'),
    #   ('cost', '0.00')
    # ]
```


## ToDo

- [ ] Unit tests + CI
- [ ] Figure out how to read secrets
- [ ] Implement HASS config flow for browser-based entry of secrets
- [ ] Hass.io, integration, Supervisor, HACS compatibility
- [ ] Add more sensors for `days_since_billing`, `consumption_to_date`, `cost_to_date`, `estimated_consumption`, `estimated_cost`
- [ ] Handle `ESTIMATED` datapoints
    - Parse dates and only take `latest_usage` from days matching the current timestamp?


## References

- [HASS Community discussion](https://community.home-assistant.io/t/bchydro-component-where-did-it-go/123371/33)
