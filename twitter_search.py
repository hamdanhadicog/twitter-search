import requests
import json
import logging
from urllib.parse import unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ——— Setup basic logging ———————————————————————————————————————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_RAW_BEARER    = "AAAAAAAAAAAAAAAAAAAAAMupswEAAAAANC5Yk%2FHGiZmGDRV3EhXMBO3uX08%3DEwAT9YySxXZXGrYScXeoKUaeyqXQFeNVWUW4SaZUvtegCUVjIi"
BEARER_TOKEN   = unquote(_RAW_BEARER)

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

def parse_tweets_and_cursor(data):
    """
    Given one SearchTimeline GraphQL response JSON (`data`),
    returns a tuple (tweets, next_cursor) where:
      - tweets is a list of raw tweet JSON objects
      - next_cursor is the Bottom‐cursor string or None
    """
    tweets = []
    next_cursor = None

    for section in data.get("data", {}).values():
        timeline = section.get("search_timeline", {}).get("timeline", {})
        for instr in timeline.get("instructions", []):
            entries = (
                instr.get("addEntries", {}).get("entries")
                or instr.get("entries", [])
            )
            for entry in entries:
                content = entry.get("content", {})

                # collect tweet
                tweet = (
                    content
                        .get("itemContent", {})
                        .get("tweet_results", {})
                        .get("result")
                )
                if tweet:
                    tweets.append(tweet)

                # detect next cursor
                op = content.get("operation", {})
                cursor_obj = op.get("cursor") if op else None
                if cursor_obj and cursor_obj.get("cursorType") == "Bottom":
                    next_cursor = cursor_obj.get("value")

    return tweets, next_cursor


def latest_twitter_search(sess: requests.Session,
                            query: str,
                            max_results: int = 100,
                            result_type: str = "latest",
                            _cursor: str = None,
                            _accum: list = None) -> list:
    """
    Returns the latest tweets matching the search query.
    """

    url = "https://twitter.com/i/api/graphql/nKAncKPF1fV1xltvF3UUlw/SearchTimeline"

    variables = {
    "rawQuery":    query,
    "count":       max_results,
    "cursor":      _cursor,   # None for first page
    "querySource": "typed_query",
    "product":     "Latest",
    }

    features = {
    "rweb_video_screen_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": False,
    "responsive_web_grok_share_attachment_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_enhance_cards_enabled": False
    }

    payload = {}
    headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9,ar-LB;q=0.8,ar;q=0.7,en-GB;q=0.6',
    'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
    'content-type': 'application/json',
    'priority': 'u=1, i',
    'referer': f'https://twitter.com/search?q{query}=&src=typed_query&f=live',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'x-client-transaction-id': 'JCDKtrUYfAe6k+6MY3q+BELaixPmJMMQkkFLThLs+nO0shj6LKwfwteCYHZYLOl2yYio/yctn9oZ9DOG82/MwC1BmaPqJw',
    'x-csrf-token': f'{sess.cookies.get("ct0")}',
    'x-twitter-active-user': 'yes',
    'x-twitter-auth-type': 'OAuth2Session',
    'x-twitter-client-language': 'en',
    'Cookie': f'_ga=GA1.1.657568565.1745564354; _ga_RJGMY4G45L=GS1.1.1745564353.1.1.1745564452.46.0.0; kdt=PZ8M55uOXDRkv052ajWFyMElbZK0qX7K3wrgdJtB; lang=en; dnt=1; guest_id=v1%3A174730703406571143; guest_id_marketing=v1%3A174730703406571143; guest_id_ads=v1%3A174730703406571143; personalization_id="v1_i8zRUsZDHupv4uL/ADwl/w=="; gt=1924384488278065387; auth_token={sess.cookies.get("auth_token")}; ct0={sess.cookies.get("ct0")}; guest_id=v1%3A174712392023652800'
    }

    response = requests.request("GET", url, headers=headers, data=payload, params={
    "variables": json.dumps(variables),
    "features":  json.dumps(features)
    })
    response.raise_for_status()
    data = response.json()

    with open("C:\\Users\\user\\Documents\\response.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=2)
    logger.info("Wrote raw data to response.json")
   # parse_tweets_and_cursor(data)

   # print(response.text)
    return data


def main(ct0:str,auth_token:str,query:str):
    """
    Main function to create a Twitter session and perform a search.
    """
    # Create a Twitter session
    sess = create_twitter_session(ct0, auth_token)

    # Perform the search
    results = latest_twitter_search(sess, query)

    # Print the results
    print(json.dumps(results, indent=4))
    return results

# def extract_cursor(js: dict) -> str | None:
#     for instr in js['data']['search_by_raw_query']['timeline']['instructions']:
#         if 'addEntries' in instr:
#             for entry in instr['addEntries']['entries']:
#                 content = entry.get('content', {})
#                 if content.get('cursorType') == 'Bottom':
#                     return content.get('value')
#     return None

# usage


if __name__ == "__main__":
    main(
        ct0="d27c9d7aee37e26071909b8b7e5dd6962789bd7f488c2903fd19a3fc94fa0a19c0a66b245a65795eda7198f3f3d136ee42fa017a6a4e6b346defa7331646d3b5b94253c6fbcc5ab2f7bc2147f6620055",
        auth_token="42321ec745cdf546151c328931a31773b01afe0d",
        query="ronaldo"
    )
    # js = response.json()
    # next_cursor = extract_cursor(js)
    
