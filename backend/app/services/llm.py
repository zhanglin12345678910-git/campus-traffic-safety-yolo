from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx

from app.config import Settings
from app.schemas import RiskResult
from app.tools.privacy_mask import mask_and_resize

logger = logging.getLogger(__name__)


class LLMServiceError(RuntimeError):
    pass


class VisionLLMServiceError(RuntimeError):
    pass


def vision_person_gate(detections: list[dict[str, Any]], skip_with_person: bool) -> bool:
    """隐私闸门：检出 person 的图片一律不上送云端视觉模型。

    返回 True 表示「允许上送」。检测里的 person 由本地 YOLO 已完成的推理给出，
    不引入额外模型；haar 人脸模糊只是兜底的尽力而为，不能替代这道闸门
    （评审 V-2：启发式「检测不到」不等于「画面里没有」）。
    """
    if not skip_with_person:
        return True
    return not any(str(item.get("class_name", "")).lower() == "person" for item in detections)


class LLMService:
    """兼容 OpenAI Chat Completions 的可替换大模型客户端。"""

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self._client = client

    @property
    def available(self) -> bool:
        return bool(self.settings.llm_base_url and self.settings.llm_api_key and self.settings.llm_model)

    def generate_risk(self, payload: dict[str, Any]) -> RiskResult:
        if not self.available:
            raise LLMServiceError("LLM 未配置")

        system_prompt = (
            "你是校园交通安全巡检辅助智能体。只能依据输入的真实检测结果和知识片段判断。"
            "不得把低置信度检测写成确定事实，不得仅凭单张图片断言标志缺失，不得编造法规编号。"
            "信息不足时必须将 risk_level 设为 review，并在 uncertainty_note 说明不确定性。"
            "是否转人工由后端确定性策略决定，不由大模型自由裁量。只返回合法 JSON。"
        )
        user_prompt = json.dumps(payload, ensure_ascii=False)
        request_body = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        if self._is_deepseek():
            # Flash defaults to thinking mode. Risk classification is a short,
            # schema-constrained task, so non-thinking mode is faster and keeps
            # the structured answer in message.content.
            request_body["thinking"] = {"type": "disabled"}
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        client = self._client or httpx.Client(
            timeout=self.settings.llm_timeout_seconds,
            proxy=self.settings.outbound_http_proxy,
        )
        close_client = self._client is None
        try:
            last_error: Exception | None = None
            for attempt in range(self.settings.llm_max_retries + 1):
                try:
                    response = client.post(self._chat_url(), headers=headers, json=request_body)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(self._strip_json_fence(content))
                    parsed["analysis_mode"] = "llm"
                    return RiskResult.model_validate(parsed)
                except Exception as exc:
                    last_error = exc
                    if attempt < self.settings.llm_max_retries:
                        time.sleep(min(0.25 * (2**attempt), 1.0))
            raise LLMServiceError(f"LLM 调用失败：{last_error}") from last_error
        finally:
            if close_client:
                client.close()

    def _chat_url(self) -> str:
        base = str(self.settings.llm_base_url).rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"

    def _is_deepseek(self) -> bool:
        return "api.deepseek.com" in str(self.settings.llm_base_url).lower()

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text.strip()


class VisionLLMService:
    """旁挂的视觉语言模型（VLM）客户端 —— 只出证据，不做决策。

    模式乙（docs/VLM_INTEGRATION_PROPOSAL.md 评审第 7 节定案）：
    本服务的输出是 `vision_assessment`（画面描述 + 停放研判 + 可见证据），
    作为纯文本证据并入 DeepSeek 文字研判的 payload；最终 risk_level 仍由
    DeepSeek 文字模型输出，本服务不产生任何策略字段，非确定性不叠加。

    工程纪律与 DeepSeek 文字链路一致：temperature=0、非流式、显式关闭思维链、
    response_format=json_object；所有提供方默认继承应用出站代理，未配置代理即
    直连，也可显式选择直连。不能按供应商品牌假定本机 DNS/路由可直连。
    """

    ALLOWED_KEYS = (
        "scene_description",
        "parking_assessment",
        "confidence",
        "visible_evidence",
        "legal_scenarios_checked",
        "notes",
    )

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self._client = client

    @property
    def api_key(self) -> str | None:
        return self.settings.vision_llm_api_key or self.settings.llm_api_key

    @property
    def available(self) -> bool:
        return bool(
            self.settings.vision_llm_enabled
            and self.settings.vision_llm_base_url
            and self.settings.vision_llm_model
            and self.api_key
        )

    @property
    def _is_deepseek(self) -> bool:
        return "deepseek" in str(self.settings.vision_llm_base_url).lower()

    def assess_image(self, *, image_path: str, context: dict[str, Any]) -> dict[str, Any]:
        """对单张巡检图片做视觉研判，返回仅含 ALLOWED_KEYS 的证据字典。"""
        if not self.available:
            raise VisionLLMServiceError("视觉研判服务未启用或未完整配置")
        jpeg = mask_and_resize(image_path, max_side=self.settings.vision_image_max_side)
        b64 = base64.b64encode(jpeg).decode("ascii")

        system_prompt = (
            "你是校园交通安全巡检辅助智能体的视觉研判模块。你会同时收到 YOLO 检测结果的 JSON"
            "（类别、置信度、坐标），请把视觉判断与检测结果互相印证，不要重复计数检测框已覆盖的对象。"
            "只能依据图片中可见的证据判断，看不出就明确说不确定，不得编造画面里不存在的东西。"
            "判断「车辆停放是否合规」时，必须排除以下合法情形：等交通灯、排队通行、礼让行人、"
            "装卸货临时停靠、执行公务的车辆；只有图内可见证据表明车辆无合法理由占用车行道、"
            "人行道、绿化区域、消防车通道或未按车位线停放时，才能判断为违停。"
            "图片模糊、角度异常、倒置或没有车辆时，结论必须是不确定（uncertain）。"
            "先描述看到什么，再给结论。只返回合法 JSON。"
        )
        question = (
            "这是校园交通巡检现场照片，附巡检上下文 JSON（地点、区域、现场描述、YOLO 检测结果）。"
            "请判断图中车辆的停放行为是否合规，返回 JSON："
            "{\"scene_description\": \"先客观描述画面\", "
            "\"parking_assessment\": \"compliant|suspected_violation|violation|uncertain\", "
            "\"confidence\": 0到1的小数, "
            "\"visible_evidence\": [\"支撑结论的画面内可见证据\"], "
            "\"legal_scenarios_checked\": [\"你排除过的合法停放情形\"], "
            "\"notes\": \"其他需要提醒人工复核的事项，没有则为空字符串\"}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{question}\n\n上下文：{json.dumps(context, ensure_ascii=False)}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ]
        body: dict[str, Any] = {
            "model": self.settings.vision_llm_model,
            "messages": messages,
            "temperature": 0.0,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        if self._is_deepseek:
            body["thinking"] = {"type": "disabled"}
        else:
            body["enable_thinking"] = False

        # Fake-IP DNS also affects domestic providers. Keep routing explicit
        # and independent from the provider-specific request-body dialect.
        proxy = self.settings.outbound_http_proxy if self.settings.vision_llm_use_outbound_proxy else None
        client = self._client or httpx.Client(
            timeout=self.settings.vision_llm_timeout_seconds,
            proxy=proxy,
            trust_env=False,
        )
        close_client = self._client is None
        try:
            last_error: Exception | None = None
            for attempt in range(self.settings.llm_max_retries + 1):
                try:
                    response = client.post(self._chat_url(), headers=self._headers(), json=body)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(LLMService._strip_json_fence(content))
                    if not isinstance(parsed, dict):
                        raise VisionLLMServiceError("视觉研判返回不是 JSON 对象")
                    return self._sanitize(parsed)
                except Exception as exc:
                    last_error = exc
                    if attempt < self.settings.llm_max_retries:
                        time.sleep(min(0.25 * (2**attempt), 1.0))
            raise VisionLLMServiceError(f"视觉研判调用失败：{last_error}") from last_error
        finally:
            if close_client:
                client.close()

    def _chat_url(self) -> str:
        base = str(self.settings.vision_llm_base_url).rstrip("/")
        return base if base.endswith("/chat/completions") else f"{base}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _sanitize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """只保留约定字段，并把字段类型收敛为后端可安全转发的纯文本证据。"""
        out: dict[str, Any] = {}
        for key in self.ALLOWED_KEYS:
            value = parsed.get(key)
            if value is None:
                continue
            if key == "confidence":
                try:
                    out[key] = round(min(max(float(value), 0.0), 1.0), 3)
                except (TypeError, ValueError):
                    continue
            elif key in {"visible_evidence", "legal_scenarios_checked"}:
                if isinstance(value, list):
                    out[key] = [str(item) for item in value][:10]
            else:
                out[key] = str(value)[:2000]
        out["model"] = self.settings.vision_llm_model
        return out
