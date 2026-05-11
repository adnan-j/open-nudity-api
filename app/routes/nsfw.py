from __future__ import annotations

import asyncio

import aiohttp
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.auth import verify_api_key
from app.detector import detect_from_url, detect_from_bytes
from app.schemas import NsfwResult, ImageUrlRequest
from app.config import settings

router = APIRouter()


def _thresholds():
    return {
        "FEMALE_BREAST_EXPOSED": settings.threshold_breast,
        "ANUS_EXPOSED": settings.threshold_anus,
        "BUTTOCKS_EXPOSED": settings.threshold_buttocks,
        "FEMALE_GENITALIA_EXPOSED": settings.threshold_genitalia,
        "MALE_GENITALIA_EXPOSED": settings.threshold_genitalia,
    }


def _is_nsfw(detections: list) -> bool:
    t = _thresholds()
    for d in detections:
        threshold = t.get(d.get("class"))
        if threshold and d.get("score", 0) >= threshold:
            return True
    return False


async def _process(image_url: str, session: aiohttp.ClientSession) -> NsfwResult:
    try:
        detections = await detect_from_url(image_url, session)
        return NsfwResult(image_url=image_url, is_nsfw=_is_nsfw(detections))
    except Exception as e:
        return NsfwResult(image_url=image_url, error=str(e))


@router.post("", response_model=list[NsfwResult], dependencies=[Depends(verify_api_key)])
async def nsfw_detection(body: ImageUrlRequest):
    if len(body.image_urls) > settings.max_images_per_request:
        raise HTTPException(400, f"Max {settings.max_images_per_request} images per request.")
    urls = [str(u) for u in body.image_urls]
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_process(u, session) for u in urls])
    return list(results)


@router.post("/upload", response_model=NsfwResult, dependencies=[Depends(verify_api_key)])
async def nsfw_detection_upload(file: UploadFile = File(...)):
    data = await file.read()
    suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
    try:
        detections = await detect_from_bytes(data, suffix)
        return NsfwResult(image_url=file.filename or "upload", is_nsfw=_is_nsfw(detections))
    except Exception as e:
        return NsfwResult(image_url=file.filename or "upload", error=str(e))
