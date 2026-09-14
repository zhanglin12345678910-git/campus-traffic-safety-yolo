from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.schemas import KnowledgeHit, RiskResult
from app.services.llm import LLMService, LLMServiceError


logger = logging.getLogger(__name__)


class RiskAssessmentService:
    def __init__(self, settings: Settings, llm: LLMService):
        self.settings = settings
        self.llm = llm

    def evaluate(
        self,
        *,
        location: str,
        area_type: str,
        description: str | None,
        image_quality: dict[str, Any],
        detections: list[dict[str, Any]],
        knowledge_hits: list[KnowledgeHit],
        review_reasons: list[str],
        vision_events: list[dict[str, Any]] | None = None,
        vision_assessment: dict[str, Any] | None = None,
    ) -> RiskResult:
        events = vision_events or []
        reasons = list(dict.fromkeys(review_reasons))
        if any(not isinstance(event, dict) for event in events):
            reasons.append("视觉事件数据格式异常，需要人工复核")
            events = [event for event in events if isinstance(event, dict)]
        evidence = self._build_evidence(detections, image_quality, events)
        if vision_assessment:
            evidence.append(self._vision_evidence_line(vision_assessment))
        references = [
            {
                "document": hit.document_name,
                "chunk_id": hit.chunk_id,
                "content": hit.content,
                "score": round(hit.score, 4),
            }
            for hit in knowledge_hits
        ]
        if not knowledge_hits:
            reasons.append("未检索到足够可靠的知识依据")

        output_schema = RiskResult.model_json_schema()
        # review_required is an API field, but it is deliberately excluded from
        # the LLM contract. The backend owns the routing decision, but the
        # advisory risk_level remains an LLM input to policy B (not fully deterministic).
        output_schema.get("properties", {}).pop("review_required", None)
        output_schema.get("properties", {}).pop("policy_reasons", None)
        if "required" in output_schema:
            output_schema["required"] = [
                name for name in output_schema["required"] if name not in {"review_required", "policy_reasons"}
            ]

        payload = {
            "location": location,
            "area_type": area_type,
            "description": description,
            "image_quality": image_quality,
            "detections": detections,
            "vision_events": events,
            "knowledge_references": references,
            "required_review_reasons": reasons,
            "output_schema": output_schema,
        }
        if vision_assessment:
            # 模式乙：旁挂视觉模型的研判只是证据文本，最终 risk_level 仍由
            # DeepSeek 文字模型依据全部证据输出，本字段不产生任何策略字段。
            payload["vision_assessment"] = vision_assessment
            payload["vision_assessment_role"] = (
                "旁挂视觉模型对原图的独立研判，仅作证据参考；"
                "最终风险等级由你依据全部证据判定，不得直接采用其结论。"
            )
        if self.llm.available:
            try:
                result = self.llm.generate_risk(payload)
                policy_reasons = self.review_policy_reasons(
                    risk_level=result.risk_level,
                    review_reasons=reasons,
                    vision_events=events,
                )
                result.review_required = bool(policy_reasons)
                result.policy_reasons = policy_reasons
                if policy_reasons:
                    result.uncertainty_note = self._merge_uncertainty(
                        result.uncertainty_note, policy_reasons
                    )
                result.evidence = result.evidence or evidence
                result.knowledge_references = references
                return result
            except LLMServiceError as exc:
                logger.warning("LLM risk assessment failed; using rules-only fallback: %s", exc)
                reasons.append("大模型服务暂不可用，已自动切换为规则保守模式")
                if self.settings.llm_required:
                    raise

        return self._rules_only_result(detections, events, evidence, references, reasons)

    @staticmethod
    def review_policy_reasons(
        *,
        risk_level: str,
        review_reasons: list[str],
        vision_events: list[dict[str, Any]],
    ) -> list[str]:
        """Apply conservative risk assessment and manual-review policy.

        Explicit evidence/quality/tool reasons always require review.  A visual
        event that requests manual confirmation also requires review.  Clean
        low-risk results may complete automatically, while medium/high/review
        risk levels require a person to confirm the final judgement.
        """

        reasons = list(dict.fromkeys(item for item in review_reasons if item))
        for event in vision_events:
            if not isinstance(event, dict):
                reasons.append("视觉事件数据格式异常，需要人工复核")
                continue
            if event.get("requires_manual_review"):
                reason = str(event.get("evidence") or event.get("label") or "视觉事件需要人工复核")
                if reason not in reasons:
                    reasons.append(reason)
        if risk_level in {"medium", "high", "review"}:
            reason = f"风险等级为 {risk_level}，按校园安全复核策略需人工确认"
            if reason not in reasons:
                reasons.append(reason)
        return reasons

    def _rules_only_result(
        self,
        detections: list[dict[str, Any]],
        vision_events: list[dict[str, Any]],
        evidence: list[str],
        references: list[dict[str, Any]],
        reasons: list[str],
    ) -> RiskResult:
        if vision_events:
            labels = "、".join(str(item.get("label", "视觉事件")) for item in vision_events)
            summary = f"当前图片触发{labels}，静态图片结果需结合现场和连续视频人工复核。"
            recommendations = [
                "请核对检测框内人员与现场实际人数是否一致。",
                "人员聚集结论应结合监控视频持续时间和区域边界进行确认。",
            ]
        elif not detections:
            summary = "当前图片未检测到可确认的交通标志、人员或车辆，不能据此判断现场安全。"
            recommendations = ["请核对拍摄范围并补拍更清晰的全景和近景图片。", "结合地点应有标志台账进行人工复核。"]
        else:
            summary = f"图片中检测到 {len(detections)} 个视觉目标，需结合模型来源、现场与制度依据复核。"
            recommendations = ["核对检测类别与现场实物是否一致。", "对遮挡、人员车辆行为或标志设置异常情况补充证据并登记台账。"]
        if references:
            recommendations.append("依据已命中的校园管理资料执行并记录整改/复查过程。")
        policy_reasons = self.review_policy_reasons(
            risk_level="review", review_reasons=reasons, vision_events=vision_events
        )
        return RiskResult(
            risk_level="review",
            risk_score=50,
            problem_summary=summary,
            evidence=evidence,
            knowledge_references=references,
            recommendations=recommendations,
            review_required=True,
            policy_reasons=policy_reasons,
            uncertainty_note=self._merge_uncertainty("未调用大模型，当前为规则保守模式。", reasons),
            analysis_mode="rules_only",
        )

    @staticmethod
    def _vision_evidence_line(vision_assessment: dict[str, Any]) -> str:
        model = str(vision_assessment.get("model", "视觉模型"))
        conclusion = str(vision_assessment.get("parking_assessment", "uncertain"))
        confidence = vision_assessment.get("confidence")
        conf_text = f"，置信度 {confidence}" if confidence is not None else ""
        description = str(vision_assessment.get("scene_description", ""))[:200]
        return f"视觉研判（{model}）：停放判定 {conclusion}{conf_text}。{description}"

    @staticmethod
    def _build_evidence(
        detections: list[dict[str, Any]],
        quality: dict[str, Any],
        vision_events: list[dict[str, Any]],
    ) -> list[str]:
        evidence = [f"图片质量：{quality.get('message', '未知')}"]
        if not detections:
            evidence.append("YOLO 未检测到交通标志、人员或车辆目标")
        else:
            for item in detections:
                model_name = item.get("model_name", "YOLO")
                evidence.append(
                    f"{model_name} 候选：{item['class_name']}，置信度 {float(item['confidence']):.2f}，"
                    f"位置 {item['bbox_xyxy']}"
                )
        for item in vision_events:
            evidence.append(f"视觉事件：{item.get('evidence', item.get('label', '需要人工复核'))}")
        return evidence

    @staticmethod
    def _merge_uncertainty(current: str, reasons: list[str]) -> str:
        items = [current.strip()] if current.strip() else []
        items.extend(reason for reason in reasons if reason and reason not in items)
        return "；".join(items)
