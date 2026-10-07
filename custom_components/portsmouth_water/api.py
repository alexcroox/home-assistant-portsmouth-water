"""Read-only Portsmouth Water Kraken client."""
import asyncio
from datetime import datetime, timedelta, timezone
from aiohttp import ClientError, ClientResponseError, ClientSession

URL = "https://api.pwl.kraken.tech/v1/graphql/"
AUTH = "mutation($input:ObtainJSONWebTokenInput!){obtainKrakenToken(input:$input){token refreshToken}}"
ACCOUNTS = "query{viewer{accounts{number}}}"
METERS = "query($accountNumber:String!){account(accountNumber:$accountNumber){properties{activeWaterMeters{meterPointReference serialNumber capabilityType}}}}"
READINGS = """query($accountNumber:String!,$startAt:DateTime,$endAt:DateTime,$utilityFilters:[UtilityFiltersInput]!){account(accountNumber:$accountNumber){properties{measurements(first:1000,startAt:$startAt,endAt:$endAt,utilityFilters:$utilityFilters){pageInfo{hasNextPage} edges{node{... on IntervalMeasurementType{startAt endAt} value unit source metaData{extras{label value}}}}}}}}"""
class AuthError(Exception):
    """Authentication needs renewing."""
class ApiError(Exception):
    """Request failed."""
class Client:
    def __init__(self, session: ClientSession, refresh_token=None, email=None, password=None):
        self.session = session
        self.refresh_token = refresh_token
        self.token = None
        self.email = email
        self.password = password
    async def request(self, query, variables=None, authenticated=True):
        headers = {"Authorization": self.token} if authenticated and self.token else {}
        try:
            async with asyncio.timeout(30):
                async with self.session.post(URL, json={"query":query,"variables":variables or {}}, headers=headers) as response:
                    response.raise_for_status()
                    result = await response.json()
        except ClientResponseError as err:
            if err.status == 401:
                raise AuthError("Please sign in again") from err
            raise ApiError("Portsmouth Water is unavailable") from err
        except (ClientError, TimeoutError, ValueError) as err:
            raise ApiError("Portsmouth Water is unavailable") from err
        if result.get("errors"):
            codes = [e.get("extensions",{}).get("errorCode", "") for e in result["errors"]]
            kinds = [e.get("extensions",{}).get("errorType", "") for e in result["errors"]]
            if any(k in {"AUTHORIZATION", "AUTHENTICATION"} or "TOKEN" in k for k in kinds) or any(c in {"KT-CT-1134","KT-CT-1112","KT-CT-1111"} for c in codes):
                raise AuthError("Please sign in again")
            raise ApiError("Portsmouth Water rejected the query: " + ",".join(codes))
        return result["data"]
    async def _authenticate(self, credentials):
        # Never turn a timeout, outage or malformed response into an auth failure.
        result = await self.request(AUTH, {"input": credentials}, False)
        auth = result.get("obtainKrakenToken")
        if not auth or not auth.get("token"):
            raise ApiError("Portsmouth Water returned an invalid login response")
        self.token = auth["token"]
        if auth.get("refreshToken"):
            self.refresh_token = auth["refreshToken"]

    async def login(self, email=None, password=None):
        if email is not None:
            await self._authenticate({"email": email, "password": password})
            return
        if self.refresh_token:
            try:
                await self._authenticate({"refreshToken": self.refresh_token})
                return
            except AuthError:
                if not (self.email and self.password):
                    raise
        if self.email and self.password:
            await self._authenticate({"email": self.email, "password": self.password})
            return
        raise AuthError("Please sign in again")
    async def accounts(self):
        return (await self.request(ACCOUNTS))["viewer"]["accounts"]
    async def meters(self, account):
        data = await self.request(METERS,{"accountNumber":account})
        return [m for prop in data["account"]["properties"] for m in prop["activeWaterMeters"] if m["capabilityType"] == "AMI"]
    async def readings(self, account, meter, frequency):
        end = datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
        start = (end-timedelta(days=30)).replace(hour=0)
        variables = {"accountNumber":account,"startAt":start.isoformat(),"endAt":end.isoformat(),"utilityFilters":[{"waterFilters":{"readingFrequencyType":frequency,"marketSupplyPointId":meter["meterPointReference"],"deviceId":meter["serialNumber"]}}]}
        data = await self.request(READINGS,variables)
        nodes=[]
        for prop in data["account"]["properties"]:
            connection=prop["measurements"]
            if connection["pageInfo"]["hasNextPage"]:
                raise ApiError("Reading limit reached; refusing incomplete consumption data")
            nodes.extend(e["node"] for e in connection["edges"])
        return nodes
