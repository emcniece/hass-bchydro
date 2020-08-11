"""BCHydro Constants"""

# Customized user agent for getting the attention of BCHydro devs
USER_AGENT = "https://github.com/emcniece/hass-bchydro#disclaimer"

# Main login page. Several redirects follow.
URL_POST_LOGIN = "https://app.bchydro.com/sso/UI/Login"

# This GET endpoint returns JSON account details.
URL_GET_ACCOUNT_JSON = "https://app.bchydro.com/evportlet/web/global-data.html"

# This GET endpoint returns XML of the last 7 days usage. The `cost` field is zero.
# Deprecated in favor of URL_POST_CONSUMPTION_XML
# URL_GET_USAGE_XML = "https://app.bchydro.com/evportlet/web/account-profile-data.html"

# This consmption URL has more detail than URL_GET_USAGE but needs different form fields.
URL_POST_CONSUMPTION_XML = "https://app.bchydro.com/evportlet/web/consumption-data.html"
