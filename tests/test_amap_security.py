import unittest

import requests

from mcp_core.amp_server import _request_error


class AmapSecurityTest(unittest.TestCase):
    def test_provider_request_details_are_not_returned_to_callers(self):
        error = _request_error(requests.exceptions.SSLError("key=should-not-be-exposed"))

        self.assertEqual(error, {"error": "Amap request failed: SSLError"})


if __name__ == "__main__":
    unittest.main()
