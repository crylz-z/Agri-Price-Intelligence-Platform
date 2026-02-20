import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from . import config


class AgriHttpClient:
    def __init__(self):
        self.session = requests.Session()

        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Referer": "http://www.bantaypresyo.da.gov.ph/",
            }
        )
        # 120s per request. The government server (bantaypresyo.da.gov.ph) is slow;
        # 30s caused premature ConnectionErrors that triggered retries and compounded total runtime.
        self.timeout = 120

    def get(self, url, params=None, timeout=None, **kwargs):
        try:
            # Use provided timeout or default
            req_timeout = timeout if timeout is not None else self.timeout
            response = self.session.get(
                url, params=params, timeout=req_timeout, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as err:
            raise err
        except requests.exceptions.RequestException as e:
            raise e

    def post(self, url, data=None, json=None, timeout=None, **kwargs):
        try:
            req_timeout = timeout if timeout is not None else self.timeout
            response = self.session.post(
                url, data=data, json=json, timeout=req_timeout, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise e
