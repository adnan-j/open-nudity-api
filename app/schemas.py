from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, HttpUrl, field_validator


class ImageUrlRequest(BaseModel):
    image_urls: List[HttpUrl]

    @field_validator("image_urls")
    @classmethod
    def check_not_empty(cls, v):
        if not v:
            raise ValueError("image_urls must not be empty")
        return v


class NsfwResult(BaseModel):
    image_url: str
    is_nsfw: Optional[bool] = None
    error: Optional[str] = None


class NudityResult(BaseModel):
    image_url: str
    is_nude: Optional[bool] = None
    nudity_score: Optional[float] = None  # 0.0–1.0: highest confidence among detected nudity regions
    detected_regions: Optional[List[str]] = None  # which nudity classes were detected
    error: Optional[str] = None


class FaceResult(BaseModel):
    image_url: str
    is_face: Optional[bool] = None
    is_nsfw: Optional[bool] = None
    error: Optional[str] = None


class PropertiesResult(BaseModel):
    image_url: str
    detections: Optional[List[dict[str, Any]]] = None
    error: Optional[str] = None
