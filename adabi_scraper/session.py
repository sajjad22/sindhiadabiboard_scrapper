import logging
import re
import time
from urllib.parse import urljoin, unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "http://www.sindhiadabiboard.org/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,sd;q=0.8,ur;q=0.7",
}


def normalize_url(raw_url: str, base: str = BASE_URL) -> str:
    """
    Normalizes URLs, handling relative links, redundant slashes,
    and legacy local file paths like file:///D:/Adabi/Catalogue/...
    """
    if not raw_url:
        return ""

    raw_url = raw_url.strip()

    # Handle local Windows file paths hardcoded by original web author
    if raw_url.lower().startswith("file:"):
        match = re.search(r"catalogue[\\/].*$", raw_url, re.IGNORECASE)
        if match:
            raw_url = "/" + match.group(0).replace("\\", "/")
        else:
            match_file = re.search(r"[^\\/]+\.html?$", raw_url, re.IGNORECASE)
            if match_file:
                raw_url = "/" + match_file.group(0)

    # Join with base URL
    full_url = urljoin(base, raw_url)

    # Force http if https gives SSL handshake issues
    if full_url.startswith("https://www.sindhiadabiboard.org"):
        full_url = full_url.replace("https://", "http://", 1)

    return full_url


class ScraperSession:
    """
    A resilient HTTP session for scraping sindhiadabiboard.org
    """

    def __init__(self, delay: float = 0.3, max_retries: int = 3, timeout: int = 25):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        retries = Retry(
            total=max_retries,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url: str, **kwargs) -> requests.Response:
        """
        Sends GET request with error handling and rate-limiting delay.
        """
        url = normalize_url(url)
        timeout = kwargs.pop("timeout", self.timeout)

        if self.delay > 0:
            time.sleep(self.delay)

        try:
            resp = self.session.get(url, timeout=timeout, **kwargs)
            # Ensure correct encoding for Sindhi text
            if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                resp.encoding = "utf-8"
            return resp
        except requests.exceptions.RequestException as e:
            logger.warning("Request failed for %s: %s", url, e)
            raise

    def get_soup(self, url: str, **kwargs) -> tuple[BeautifulSoup, requests.Response]:
        """
        Fetches a page and returns (BeautifulSoup, Response)
        """
        resp = self.get(url, **kwargs)
        # Parse content with utf-8 encoding
        soup = BeautifulSoup(resp.content, "html.parser", from_encoding="utf-8")
        return soup, resp
