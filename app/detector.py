from __future__ import annotations

import asyncio
import os
import tempfile
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import aiohttp
from nudenet import NudeDetector

warnings.filterwarnings("ignore")

_detector: Optional[NudeDetector] = None
_executor = ThreadPoolExecutor(max_workers=4)


def get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CloudantsVisionAPI/1.0; +https://github.com/cloudants/vision-api)"}


async def download_image(url: str, session: aiohttp.ClientSession) -> bytes:
    async with session.get(url, headers=_HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            raise ValueError(f"Failed to fetch image (HTTP {resp.status}): {url}")
        return await resp.read()


async def run_detection(image_path: str) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, get_detector().detect, image_path)


async def detect_from_url(url: str, session: aiohttp.ClientSession) -> list[dict]:
    content = await download_image(url, session)
    suffix = os.path.splitext(url.split("?")[0])[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(content)
        tmp_path = f.name
    try:
        return await run_detection(tmp_path)
    finally:
        os.unlink(tmp_path)


async def detect_from_bytes(data: bytes, suffix: str = ".jpg") -> list[dict]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        tmp_path = f.name
    try:
        return await run_detection(tmp_path)
    finally:
        os.unlink(tmp_path)
