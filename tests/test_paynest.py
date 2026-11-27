import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from app.paynest import Handler


class PayNestHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_health(self):
        with urlopen(self.url + "/health", timeout=3) as res:
            self.assertEqual(200, res.status)
            self.assertEqual({"status": "ok"}, json.load(res))

    def test_demo_payment(self):
        with urlopen(self.url + "/payments/demo-001", timeout=3) as res:
            self.assertEqual({"reference": "demo-001", "amount_cents": 2500, "currency": "LKR"}, json.load(res))

    def test_missing_payment(self):
        with self.assertRaises(HTTPError) as failure:
            urlopen(self.url + "/payments/missing", timeout=3)
        self.assertEqual(404, failure.exception.code)
        failure.exception.close()
