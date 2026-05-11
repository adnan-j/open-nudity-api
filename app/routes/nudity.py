from __future__ import annotations

import asyncio
from typing import Tuple, List

import aiohttp
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.auth import verify_api_key
from app.detector import detect_from_url, detect_from_bytes
from app.schemas import NudityResult, ImageUrlRequest
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


def _analyze(detections: list) -> Tuple[bool, float, List[str]]:
    """Returns (is_nude, nudity_score 0-1, detected_regions)."""
    t = _thresholds()
    max_score = 0.0
    regions = []
    for d in detections:
        cls, score = d.get("class"), d.get("score", 0)
        threshold = t.get(cls)
        if threshold is not None and score >= threshold:
            regions.append(cls)
            if score > max_score:
                max_score = score
    return bool(regions), round(max_score, 4), regions


async def _process(image_url: str, session: aiohttp.ClientSession) -> NudityResult:
    try:
        detections = await detect_from_url(image_url, session)
        is_nude, score, regions = _analyze(detections)
        return NudityResult(
            image_url=image_url,
            is_nude=is_nude,
            nudity_score=score,
            detected_regions=regions if regions else None,
        )
    except Exception as e:
        return NudityResult(image_url=image_url, error=str(e))


@router.post("", response_model=list[NudityResult], dependencies=[Depends(verify_api_key)])
async def nudity_detection(body: ImageUrlRequest):
    if len(body.image_urls) > settings.max_images_per_request:
        raise HTTPException(400, f"Max {settings.max_images_per_request} images per request.")
    urls = [str(u) for u in body.image_urls]
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_process(u, session) for u in urls])
    return list(results)


@router.post("/upload", response_model=NudityResult, dependencies=[Depends(verify_api_key)])
async def nudity_detection_upload(file: UploadFile = File(...)):
    data = await file.read()
    suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
    try:
        detections = await detect_from_bytes(data, suffix)
        is_nude, score, regions = _analyze(detections)
        return NudityResult(
            image_url=file.filename or "upload",
            is_nude=is_nude,
            nudity_score=score,
            detected_regions=regions if regions else None,
        )
    except Exception as e:
        return NudityResult(image_url=file.filename or "upload", error=str(e))
