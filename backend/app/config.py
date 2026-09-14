from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.amap", PROJECT_ROOT / ".env.proxy"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "安巡智脑"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_key: str | None = None
    # Day boundaries for dashboard statistics such as "今日巡检" and the 7-day
    # trend. Timestamps are stored in UTC; containers usually run in UTC.
    app_timezone: str = "Asia/Shanghai"

    # Optional proxy used only for outbound provider calls. This is useful on
    # Windows when a VPN provides a local HTTP proxy but leaves WinHTTP and
    # process-level proxy variables disabled (for example Mihomo/Clash).
    outbound_http_proxy: str | None = None

    database_url: str = "sqlite:///./data/campus_safety.db"
    sql_echo: bool = False

    yolo_model_path: Path = Path("../models/yolo26-tt100k-best.pt")
    yolo_device: str = "cpu"
    yolo_default_conf: float = 0.3
    yolo_review_conf: float = 0.5
    yolo_default_iou: float = 0.5
    yolo_default_imgsz: int = 640
    ultralytics_config_dir: Path = Path("./data/ultralytics")

    # A second, official COCO-pretrained YOLO26 model complements the custom
    # TT100K traffic-sign checkpoint.  It is intentionally restricted to
    # people and vehicles so generic COCO sign predictions cannot override the
    # domain-specific traffic-sign model.
    general_yolo_enabled: bool = True
    general_yolo_model_path: Path = PROJECT_ROOT / "models" / "yolo26m.pt"
    general_yolo_default_conf: float = 0.2
    general_yolo_review_conf: float = 0.35
    general_yolo_classes: str = "person,bicycle,car,motorcycle,bus,truck"

    # A still image can only create a crowd *candidate*.  Directional events
    # such as wrong-way travel require consecutive video frames and tracking.
    crowd_detection_enabled: bool = True
    crowd_min_persons: int = 8

    video_max_upload_mb: int = 100
    video_max_frames: int = 900
    video_frame_stride: int = 2
    video_target_fps: int = 10
    video_max_dimension: int = 960
    wrong_way_min_track_points: int = 8
    wrong_way_min_displacement_ratio: float = 0.03

    upload_dir: Path = Path("../uploads")
    output_dir: Path = Path("../outputs")
    max_upload_mb: int = 20

    # The AMap Web Service key stays server-side. The browser only talks to
    # backend proxy endpoints, so the key never enters the frontend bundle.
    amap_web_service_key: str | None = None
    amap_base_url: str = "https://restapi.amap.com"
    amap_timeout_seconds: float = 10.0

    # Blur scoring is performed after normalizing the image's long side.  The
    # previous raw-resolution threshold produced very different values for the
    # same scene at different resolutions and rejected sharp, low-texture
    # campus images.  500 separates the audited soft sample (152.6) from the
    # clear campus set (minimum 622.1) at a 1024-pixel long side.
    blur_threshold: float = 500.0
    blur_normalize_long_side: int = 1024
    dark_threshold: float = 45.0
    bright_threshold: float = 225.0
    min_image_width: int = 320
    min_image_height: int = 240

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_path: str = "./data/qdrant"
    qdrant_collection: str = "campus_safety_knowledge"
    embedding_provider: str = "hash"
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 384
    rag_top_k: int = 5
    rag_score_threshold: float = 0.08
    chunk_size: int = 500
    chunk_overlap: int = 80

    # DeepSeek V4 Flash is the project's ready-to-use LLM provider. Operators
    # only need to supply LLM_API_KEY in the project-root .env file.
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str | None = None
    llm_model: str = "deepseek-v4-flash"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_required: bool = False

    # Optional visual evidence supplements text assessment; it does not decide
    # risk levels. Set VISION_LLM_ENABLED=false to use text-only assessment.
    vision_llm_enabled: bool = True
    vision_llm_base_url: str = "https://api.deepseek.com/v1"
    vision_llm_api_key: str | None = None  # empty -> reuse llm_api_key
    vision_llm_model: str = "deepseek-v4-flash-vision-exp"
    vision_llm_timeout_seconds: float = 45.0
    # Use the configured application proxy for any VLM provider, not only
    # DeepSeek: VPN Fake-IP DNS can also affect DashScope. Set false to opt
    # into direct access; an empty outbound_http_proxy already means direct.
    vision_llm_use_outbound_proxy: bool = True
    vision_image_max_side: int = 1024
    # Privacy gate: images that contain any detected person are never uploaded
    # to the provider (fallback to text-only assessment instead).
    vision_skip_images_with_person: bool = True

    @field_validator(
        "yolo_default_conf",
        "yolo_review_conf",
        "yolo_default_iou",
        "general_yolo_default_conf",
        "general_yolo_review_conf",
        "wrong_way_min_displacement_ratio",
    )
    @classmethod
    def validate_probability(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("threshold must be between 0 and 1")
        return value

    @field_validator(
        "max_upload_mb",
        "embedding_dimension",
        "chunk_size",
        "rag_top_k",
        "crowd_min_persons",
        "video_max_upload_mb",
        "video_max_frames",
        "video_frame_stride",
        "video_target_fps",
        "video_max_dimension",
        "wrong_way_min_track_points",
        "blur_normalize_long_side",
        "vision_image_max_side",
    )
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("outbound_http_proxy", mode="before")
    @classmethod
    def normalize_optional_proxy(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown IANA time zone: {value}") from exc
        return value

    @property
    def display_timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def video_max_upload_bytes(self) -> int:
        return self.video_max_upload_mb * 1024 * 1024

    @property
    def general_object_class_names(self) -> set[str]:
        return {item.strip().lower() for item in self.general_yolo_classes.split(",") if item.strip()}

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ultralytics_config_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite:///"):
            Path(self.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
