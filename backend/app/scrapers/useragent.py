from __future__ import annotations
import random

# Realistic modern user-agents — updated periodically
_CHROME_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

_FIREFOX_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_SAFARI_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

ALL_AGENTS = _CHROME_AGENTS + _FIREFOX_AGENTS + _SAFARI_AGENTS

# Viewport sizes paired with realistic screen resolutions
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
    {"width": 2560, "height": 1440},
]

# Accepted language headers weighted toward common locales
ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-US,en;q=0.9",
    "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
]


def random_user_agent(browser: str = "any") -> str:
    if browser == "chrome":
        return random.choice(_CHROME_AGENTS)
    if browser == "firefox":
        return random.choice(_FIREFOX_AGENTS)
    if browser == "safari":
        return random.choice(_SAFARI_AGENTS)
    return random.choice(ALL_AGENTS)


def random_viewport() -> dict:
    return random.choice(VIEWPORTS)


def random_accept_language() -> str:
    return random.choice(ACCEPT_LANGUAGES)


def playwright_fingerprint(browser: str = "chrome") -> dict:
    """Returns kwargs to pass to browser.new_context() for fingerprint diversity."""
    return {
        "user_agent": random_user_agent(browser),
        "viewport": random_viewport(),
        "locale": random.choice(["zh-CN", "zh-TW", "en-US", "pt-BR"]),
        "timezone_id": random.choice(["Asia/Shanghai", "Asia/Taipei", "America/Sao_Paulo", "America/New_York"]),
        "extra_http_headers": {
            "Accept-Language": random_accept_language(),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
        },
    }
