from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.detector import get_detector
from app.routes import nsfw, nudity, face, properties


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_detector()  # warm up: load ONNX model once at startup
    yield


app = FastAPI(
    title="Cloudants Vision API",
    description=(
        "Open-source image analysis API powered by NudeNet. "
        "Detects NSFW content, nudity, faces, and raw image properties."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(nsfw.router, prefix="/v1/nsfw", tags=["NSFW Detection"])
app.include_router(nudity.router, prefix="/v1/nudity", tags=["Nudity Detection"])
app.include_router(face.router, prefix="/v1/face", tags=["Face Detection"])
app.include_router(properties.router, prefix="/v1/detections", tags=["Raw Detections"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
