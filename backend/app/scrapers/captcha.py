from __future__ import annotations
import asyncio
import time
from abc import ABC, abstractmethod
from enum import Enum
import httpx
from app.core.logging import get_logger

logger = get_logger(__name__)


class CaptchaType(str, Enum):
    recaptcha_v2 = "recaptcha_v2"
    recaptcha_v3 = "recaptcha_v3"
    image = "image"
    slider = "slider"       # Common on Shopee/JD.com
    rotate = "rotate"       # Image rotation CAPTCHA


class CaptchaResult:
    def __init__(self, token: str | None, solved: bool, method: str):
        self.token = token
        self.solved = solved
        self.method = method

    @classmethod
    def failed(cls, method: str = "unknown") -> "CaptchaResult":
        return cls(token=None, solved=False, method=method)


class BaseCaptchaSolver(ABC):
    @abstractmethod
    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> CaptchaResult:
        ...

    @abstractmethod
    async def solve_image(self, image_base64: str) -> CaptchaResult:
        ...

    async def solve_slider(self, page) -> CaptchaResult:
        """
        Slider CAPTCHAs (Shopee/JD) — simulate human drag with random jitter.
        Most slider implementations can be defeated without external APIs.
        """
        logger.info("attempting_slider_captcha")
        try:
            # Generic slider strategy: find slider handle, drag across
            slider = await page.query_selector('[class*="slider"] [class*="btn"], .nc_iconfont.btn_slide')
            if not slider:
                return CaptchaResult.failed("slider_element_not_found")

            box = await slider.bounding_box()
            if not box:
                return CaptchaResult.failed("slider_no_bounding_box")

            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2

            await page.mouse.move(start_x, start_y)
            await page.mouse.down()

            # Human-like movement: accelerate then decelerate
            track_width = 280
            import random
            x = start_x
            for i in range(20):
                progress = i / 19
                # Ease-in-out curve
                speed = progress * (1 - progress) * 4
                step = track_width * speed / 10
                jitter_y = random.uniform(-2, 2)
                x += step
                await page.mouse.move(x, start_y + jitter_y)
                await asyncio.sleep(random.uniform(0.01, 0.04))

            await page.mouse.up()
            await asyncio.sleep(1.5)
            return CaptchaResult(token="slider_completed", solved=True, method="slider_simulation")
        except Exception as e:
            logger.warning("slider_captcha_failed", error=str(e))
            return CaptchaResult.failed("slider_exception")


class TwoCaptchaSolver(BaseCaptchaSolver):
    """
    2captcha.com integration.
    Set CAPTCHA_SERVICE_KEY in .env to enable.
    Docs: https://2captcha.com/api-docs
    """

    BASE_URL = "https://2captcha.com"
    POLL_INTERVAL = 5
    MAX_WAIT = 120

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _submit(self, params: dict) -> str | None:
        params["key"] = self.api_key
        params["json"] = 1
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.BASE_URL}/in.php", data=params)
            data = r.json()
            if data.get("status") == 1:
                return str(data["request"])
            logger.warning("captcha_submit_failed", response=data)
            return None

    async def _poll(self, task_id: str) -> str | None:
        deadline = time.time() + self.MAX_WAIT
        async with httpx.AsyncClient(timeout=30) as client:
            while time.time() < deadline:
                await asyncio.sleep(self.POLL_INTERVAL)
                r = await client.get(
                    f"{self.BASE_URL}/res.php",
                    params={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
                )
                data = r.json()
                if data.get("status") == 1:
                    return str(data["request"])
                if data.get("request") not in ("CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"):
                    logger.warning("captcha_poll_error", response=data)
                    return None
        return None

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> CaptchaResult:
        logger.info("solving_recaptcha_v2", url=page_url)
        task_id = await self._submit({
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
        })
        if not task_id:
            return CaptchaResult.failed("2captcha_submit_failed")

        token = await self._poll(task_id)
        if token:
            return CaptchaResult(token=token, solved=True, method="2captcha_recaptchav2")
        return CaptchaResult.failed("2captcha_timeout")

    async def solve_image(self, image_base64: str) -> CaptchaResult:
        task_id = await self._submit({"method": "base64", "body": image_base64})
        if not task_id:
            return CaptchaResult.failed("2captcha_submit_failed")
        token = await self._poll(task_id)
        if token:
            return CaptchaResult(token=token, solved=True, method="2captcha_image")
        return CaptchaResult.failed("2captcha_timeout")


class NullCaptchaSolver(BaseCaptchaSolver):
    """No-op solver — used when no API key is configured."""

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> CaptchaResult:
        logger.warning("captcha_solver_not_configured", type="recaptcha_v2")
        return CaptchaResult.failed("no_solver_configured")

    async def solve_image(self, image_base64: str) -> CaptchaResult:
        logger.warning("captcha_solver_not_configured", type="image")
        return CaptchaResult.failed("no_solver_configured")


def get_captcha_solver() -> BaseCaptchaSolver:
    from app.core.config import get_settings
    settings = get_settings()
    if settings.captcha_service_key:
        return TwoCaptchaSolver(api_key=settings.captcha_service_key)
    logger.info("captcha_solver_null_mode")
    return NullCaptchaSolver()
