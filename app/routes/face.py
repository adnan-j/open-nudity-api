from __future__ import annotations

import asyncio
from typing import Tuple

import aiohttp
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.auth import verify_api_key
from app.detector import detect_from_url, detect_from_bytes
from app.schemas import FaceResult, ImageUrlRequest
from app.config import settings

router = APIRouter()

FACE_CLASSES = {"FACE_FEMALE", "FACE_MALE"}


def _nsfw_thresholds():
    return {
        "FEMALE_BREAST_EXPOSED": settings.threshold_breast,
        "ANUS_EXPOSED": settings.threshold_anus,
        "BUTTOCKS_EXPOSED": settings.threshold_buttocks,
        "FEMALE_GENITALIA_EXPOSED": settings.threshold_genitalia,
        "MALE_GENITALIA_EXPOSED": settings.threshold_genitalia,
    }


def _parse(detections: list) -> Tuple[bool, bool]:
    t = _nsfw_thresholds()
    is_face = any(d.get("class") in FACE_CLASSES for d in detections)
    is_nsfw = any(
        (threshold := t.get(d.get("class"))) and d.get("score", 0) >= threshold
        for d in detections
    )
    return is_face, is_nsfw


async def _process(image_url: str, session: aiohttp.ClientSession) -> FaceResult:
    try:
        detections = await detect_from_url(image_url, session)
        is_face, is_nsfw = _parse(detections)
        return FaceResult(image_url=image_url, is_face=is_face, is_nsfw=is_nsfw)
    except Exception as e:
        return FaceResult(image_url=image_url, error=str(e))


@router.post("", response_model=list[FaceResult], dependencies=[Depends(verify_api_key)])
async def face_detection(body: ImageUrlRequest):
    if len(body.image_urls) > settings.max_images_per_request:
        raise HTTPException(400, f"Max {settings.max_images_per_request} images per request.")
    urls = [str(u) for u in body.image_urls]
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_process(u, session) for u in urls])
    return list(results)


@router.post("/upload", response_model=FaceResult, dependencies=[Depends(verify_api_key)])
async def face_detection_upload(file: UploadFile = File(...)):
    data = await file.read()
    suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
    try:
        detections = await detect_from_bytes(data, suffix)
        is_face, is_nsfw = _parse(detections)
        return FaceResult(image_url=file.filename or "upload", is_face=is_face, is_nsfw=is_nsfw)
    except Exception as e:
        return FaceResult(image_url=file.filename or "upload", error=str(e))
