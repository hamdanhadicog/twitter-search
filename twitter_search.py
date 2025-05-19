import requests
import json
import base64
import mimetypes
import os
import time
from urllib.parse import unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_RAW_BEARER    = "AAAAAAAAAAAAAAAAAAAAAMupswEAAAAANC5Yk%2FHGiZmGDRV3EhXMBO3uX08%3DEwAT9YySxXZXGrYScXeoKUaeyqXQFeNVWUW4SaZUvtegCUVjIi"
BEARER_TOKEN   = unquote(_RAW_BEARER)
CREATE_TWEET_URL = "https://twitter.com/i/api/graphql/dOominYnbOIOpEdRJ7_lHw/CreateTweet"

# Default User-Agent (override by passing user_agent to create_twitter_session)
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

# ────────────────────────────────────────────────────────────────────────────────
def create_twitter_session(ct0: str,
                           auth_token: str,
                           user_agent: str = None) -> requests.Session:
    """
    Returns a retry-enabled, logged-in Session.  
    You only need to supply ct0 and auth_token.
    """
    sess = requests.Session()

    # ── Retry on connection errors & 5xx/429 ─────────────────────────────────────
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    # ─────────────────────────────────────────────────────────────────────────────

    # inject your login cookies
    sess.cookies.set("ct0",        ct0,        domain=".twitter.com", path="/")
    sess.cookies.set("auth_token", auth_token, domain=".twitter.com", path="/")

    # base headers
    sess.headers.update({
        "Authorization":       f"Bearer {BEARER_TOKEN}",
        "X-CSRF-Token":        ct0,
        "User-Agent":          user_agent or _DEFAULT_UA,
        "Accept":              "*/*",
        "Accept-Language":     "en-US,en;q=0.9",
        "Accept-Encoding":     "gzip, deflate, br",
        "Referer":             "https://twitter.com/",
        "Origin":              "https://twitter.com",
    })

    # fetch guest token
    resp = sess.post("https://api.twitter.com/1.1/guest/activate.json")
    resp.raise_for_status()
    sess.headers["X-Guest-Token"] = resp.json()["guest_token"]
    
    return sess
