"""Regression tests for unattended recovery from short supplier sessions."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock
from aiohttp import ClientResponseError, RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

SOURCE = Path(__file__).parents[1] / "custom_components/portsmouth_water/api.py"
spec = importlib.util.spec_from_file_location("water_api", SOURCE)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

SUCCESS = {"obtainKrakenToken": {"token": "example-access", "refreshToken": "example-refresh"}}


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    def client(self, **kwargs):
        return api.Client(None, email="example@example.com", password="example-password", **kwargs)

    async def test_expired_refresh_automatically_signs_in(self):
        client = self.client(refresh_token="expired-refresh")
        client.request = AsyncMock(side_effect=[api.AuthError("Expired"), SUCCESS])
        await client.login()
        self.assertEqual(client.token, "example-access")
        self.assertEqual(client.refresh_token, "example-refresh")
        self.assertEqual(client.request.call_args_list[0].args[1], {"input": {"refreshToken": "expired-refresh"}})
        self.assertEqual(client.request.call_args_list[1].args[1], {"input": {"email": "example@example.com", "password": "example-password"}})

    async def test_restart_and_repeated_expiry_recover(self):
        for _ in range(3):
            client = self.client(refresh_token="expired-refresh")
            client.request = AsyncMock(side_effect=[api.AuthError("Expired"), SUCCESS])
            await client.login()
            self.assertEqual(client.token, "example-access")

    async def test_working_refresh_does_not_send_password(self):
        client = self.client(refresh_token="valid-refresh")
        client.request = AsyncMock(return_value=SUCCESS)
        await client.login()
        client.request.assert_awaited_once()
        self.assertNotIn("password", client.request.call_args.args[1]["input"])

    async def test_network_failure_does_not_trigger_reauthentication(self):
        client = self.client(refresh_token="valid-refresh")
        client.request = AsyncMock(side_effect=api.ApiError("Unavailable"))
        with self.assertRaises(api.ApiError):
            await client.login()
        client.request.assert_awaited_once()

    async def test_initial_login_outage_remains_connection_error(self):
        client = self.client()
        client.request = AsyncMock(side_effect=api.ApiError("Unavailable"))
        with self.assertRaises(api.ApiError):
            await client.login("example@example.com", "example-password")

    async def test_rejected_saved_password_requests_reauthentication(self):
        client = self.client(refresh_token="expired-refresh")
        client.request = AsyncMock(side_effect=api.AuthError("Rejected"))
        with self.assertRaises(api.AuthError):
            await client.login()
        self.assertEqual(client.request.await_count, 2)

    async def test_legacy_token_only_entry_requests_credentials_once(self):
        client = api.Client(None, refresh_token="expired-refresh")
        client.request = AsyncMock(side_effect=api.AuthError("Expired"))
        with self.assertRaises(api.AuthError):
            await client.login()
        client.request.assert_awaited_once()

    async def test_malformed_login_response_is_not_auth_failure(self):
        client = self.client()
        client.request = AsyncMock(return_value={"obtainKrakenToken": None})
        with self.assertRaises(api.ApiError):
            await client.login()

    async def test_supplier_expiry_error_is_classified_correctly(self):
        class Response:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def raise_for_status(self): pass
            async def json(self):
                return {"errors": [{"extensions": {"errorType": "VALIDATION", "errorCode": "KT-CT-1134"}}]}
        class Session:
            def post(self, *args, **kwargs): return Response()
        with self.assertRaises(api.AuthError):
            await api.Client(Session()).request(api.AUTH, authenticated=False)

    async def test_http_503_is_not_auth_failure(self):
        info = RequestInfo(URL(api.URL), "POST", CIMultiDictProxy(CIMultiDict()), URL(api.URL))
        class Response:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def raise_for_status(self):
                raise ClientResponseError(info, (), status=503)
        class Session:
            def post(self, *args, **kwargs): return Response()
        with self.assertRaises(api.ApiError):
            await api.Client(Session()).request(api.AUTH, authenticated=False)


if __name__ == "__main__":
    unittest.main()
