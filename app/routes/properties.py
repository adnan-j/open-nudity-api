from __future__ import annotations

import asyncio

import aiohttp
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.auth import verify_api_key
from app.detector import detect_from_url, detect_from_bytes
from app.schemas import PropertiesResult, ImageUrlRequest
from app.config import settings

router = APIRouter()


async def _process(image_url: str, session: aiohttp.ClientSession) -> PropertiesResult:
    try:
        detections = await detect_from_url(image_url, session)
        return PropertiesResult(image_url=image_url, detections=detections)
    except Exception as e:
        return PropertiesResult(image_url=image_url, error=str(e))


@router.post("", response_model=list[PropertiesResult], dependencies=[Depends(verify_api_key)])
async def raw_detections(body: ImageUrlRequest):
    if len(body.image_urls) > settings.max_images_per_request:
        raise HTTPException(400, f"Max {settings.max_images_per_request} images per request.")
    urls = [str(u) for u in body.image_urls]
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[_process(u, session) for u in urls])
    return list(results)


@router.post("/upload", response_model=PropertiesResult, dependencies=[Depends(verify_api_key)])
async def raw_detections_upload(file: UploadFile = File(...)):
    data = await file.read()
    suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
    try:
        detections = await detect_from_bytes(data, suffix)
        return PropertiesResult(image_url=file.filename or "upload", detections=detections)
    except Exception as e:
        return PropertiesResult(image_url=file.filename or "upload", error=str(e))
