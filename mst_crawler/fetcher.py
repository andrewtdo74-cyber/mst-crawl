"""HTTP client: delay ngẫu nhiên, retry lùi dần, báo Blocked khi bị chặn liên tục."""
import random
import threading
import time

import requests

BASE_URL = "https://masothue.com"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


class Blocked(Exception):
    """Trang chặn liên tục sau mọi lần thử -> dừng crawl, chạy lại sau."""


class Fetcher:
    def __init__(self, delay=2.0, retries=5, timeout=25):
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self._local = threading.local()

    def _session(self):
        if not hasattr(self._local, "s"):
            s = requests.Session()
            s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "vi-VN,vi;q=0.9"})
            self._local.s = s
        return self._local.s

    def get(self, path, check=None):
        url = path if path.startswith("http") else BASE_URL + path
        for attempt in range(self.retries):
            try:
                r = self._session().get(url, timeout=self.timeout)
                r.encoding = "utf-8"
                time.sleep(self.delay * random.uniform(0.7, 1.3))
                if r.status_code == 200 and (check is None or check(r.text)):
                    return r.text
            except requests.RequestException:
                pass
            time.sleep(min(120, 10 * 2 ** attempt))
        raise Blocked(url)
