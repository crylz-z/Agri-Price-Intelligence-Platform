import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from . import config

class AgriHttpClient:
    def __init__(self):
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=config.BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.timeout = config.TIMEOUT_SECONDS

    def get(self, url, params=None, **kwargs):
        try:
            response = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as err:
            # Log error here
            raise err
        except requests.exceptions.RequestException as e:
            # Log critical failure
            raise e

    def post(self, url, data=None, json=None, **kwargs):
        try:
            response = self.session.post(url, data=data, json=json, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise e
