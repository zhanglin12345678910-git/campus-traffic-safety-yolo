from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


class AMapServiceError(RuntimeError):
    """Raised when the configured AMap Web Service cannot fulfil a request."""


@dataclass(frozen=True)
class StaticMapImage:
    content: bytes
    content_type: str


class AMapService:
    # AMap refreshes live weather roughly hourly; a short cache keeps the
    # topbar from calling the provider on every page load.
    WEATHER_CACHE_SECONDS = 600

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.key = (settings.amap_web_service_key or "").strip()
        self.base_url = settings.amap_base_url.rstrip("/")
        self.client = client or httpx.Client(
            timeout=settings.amap_timeout_seconds,
            proxy=settings.outbound_http_proxy,
        )
        self._weather_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._weather_lock = threading.Lock()

    @property
    def available(self) -> bool:
        return bool(self.key)

    def weather(self, adcode: str) -> dict[str, Any]:
        with self._weather_lock:
            cached = self._weather_cache.get(adcode)
            if cached and time.monotonic() - cached[0] < self.WEATHER_CACHE_SECONDS:
                return dict(cached[1])
        payload = self._get_json(
            "/v3/weather/weatherInfo",
            {"city": adcode, "extensions": "base", "output": "JSON"},
        )
        lives = payload.get("lives") or []
        if not lives or not lives[0].get("weather") or not str(lives[0].get("temperature") or "").strip():
            raise AMapServiceError("高德未返回该区域的实况天气")
        item = lives[0]
        result = {
            "provider": "amap",
            "adcode": str(item.get("adcode") or adcode),
            "city": item.get("city") or "",
            "weather": item["weather"],
            "temperature": str(item["temperature"]).strip(),
            "humidity": item.get("humidity") or "",
            "wind_direction": item.get("winddirection") or "",
            "wind_power": item.get("windpower") or "",
            "report_time": item.get("reporttime") or "",
        }
        with self._weather_lock:
            self._weather_cache[adcode] = (time.monotonic(), result)
        return dict(result)

    def geocode(self, address: str, city: str | None = None) -> dict[str, Any]:
        payload = self._get_json(
            "/v3/geocode/geo",
            {
                "address": address,
                "city": city or "",
                "output": "JSON",
            },
        )
        geocodes = payload.get("geocodes") or []
        if not geocodes:
            raise AMapServiceError("高德未找到该地址的坐标")
        item = geocodes[0]
        location = str(item.get("location") or "")
        try:
            lng_text, lat_text = location.split(",", 1)
            lng, lat = float(lng_text), float(lat_text)
        except (TypeError, ValueError) as exc:
            raise AMapServiceError("高德返回了无效的坐标格式") from exc
        return {
            "provider": "amap",
            "formatted_address": item.get("formatted_address") or address,
            "province": item.get("province") or "",
            "city": item.get("city") or "",
            "district": item.get("district") or "",
            "adcode": item.get("adcode") or "",
            "level": item.get("level") or "",
            "location": {"lng": lng, "lat": lat},
        }

    def static_map(
        self,
        *,
        lng: float,
        lat: float,
        zoom: int,
        width: int,
        height: int,
        traffic: bool = False,
    ) -> StaticMapImage:
        self._require_key()
        try:
            response = self.client.get(
                f"{self.base_url}/v3/staticmap",
                params={
                    "key": self.key,
                    "location": f"{lng:.6f},{lat:.6f}",
                    "zoom": zoom,
                    "size": f"{width}*{height}",
                    "scale": 1,
                    "traffic": 1 if traffic else 0,
                    "markers": f"mid,0x438DFF,校:{lng:.6f},{lat:.6f}",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AMapServiceError("高德静态地图网络请求失败") from exc

        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if not content_type.startswith("image/"):
            detail = self._error_detail(response)
            raise AMapServiceError(f"高德静态地图调用失败：{detail}")
        if not response.content:
            raise AMapServiceError("高德静态地图返回了空图片")
        if len(response.content) > 5 * 1024 * 1024:
            raise AMapServiceError("高德静态地图响应超过安全大小限制")
        return StaticMapImage(response.content, content_type)

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._require_key()
        try:
            response = self.client.get(f"{self.base_url}{path}", params={"key": self.key, **params})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AMapServiceError("高德 Web 服务网络请求或响应解析失败") from exc
        if str(payload.get("status")) != "1":
            detail = payload.get("info") or payload.get("infocode") or "未知错误"
            raise AMapServiceError(f"高德 Web 服务调用失败：{detail}")
        return payload

    def _require_key(self) -> None:
        if not self.available:
            raise AMapServiceError("高德 Web 服务 Key 尚未配置")

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            return str(payload.get("info") or payload.get("infocode") or "响应不是地图图片")
        except ValueError:
            return "响应不是地图图片"
