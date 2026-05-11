from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = ""
    max_images_per_request: int = 10
    workers: int = 4

    # Detection thresholds — lower = more sensitive, higher = fewer false positives.
    # NudeNet scores on real-world photos are often in 0.30–0.55 range.
    threshold_breast: float = 0.30
    threshold_genitalia: float = 0.30
    threshold_buttocks: float = 0.40
    threshold_anus: float = 0.45

    model_config = {"env_file": ".env"}


settings = Settings()
