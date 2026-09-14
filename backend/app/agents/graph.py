from __future__ import annotations

import html
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from langgraph.graph import END, START, StateGraph
from sqlalchemy import delete, func, select

from app.agents.state import InspectionState
from app.config import Settings
from app.database import Database
from app.models import (
    AgentRun,
    AgentStep,
    DetectionResult,
    InspectionTask,
    Report,
    RiskAssessment,
)
from app.schemas import KnowledgeHit, RiskResult
from app.services.llm import VisionLLMService, vision_person_gate
from app.services.rag import KnowledgeBaseService
from app.services.risk import RiskAssessmentService
from app.tools.image_quality import ImageQualityTool
from app.tools.yolo import TrafficSignDetectionTool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InspectionWorkflow:
    """以真实 LangGraph StateGraph 编排单个巡检任务。"""

    def __init__(
        self,
        settings: Settings,
        database: Database,
        image_quality_tool: ImageQualityTool,
        yolo_tool: TrafficSignDetectionTool,
        knowledge_base: KnowledgeBaseService,
        risk_service: RiskAssessmentService,
        vision_llm: VisionLLMService | None = None,
    ):
        self.settings = settings
        self.database = database
        self.image_quality_tool = image_quality_tool
        self.yolo_tool = yolo_tool
        self.knowledge_base = knowledge_base
        self.risk_service = risk_service
        self.vision_llm = vision_llm
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(InspectionState)
        builder.add_node("validate_input", self.validate_input)
        builder.add_node("check_image_quality", self.check_image_quality)
        builder.add_node("detect_traffic_signs", self.detect_traffic_signs)
        builder.add_node("check_detection_result", self.check_detection_result)
        builder.add_node("retrieve_knowledge", self.retrieve_knowledge)
        builder.add_node("evaluate_risk", self.evaluate_risk)
        builder.add_node("generate_recommendations", self.generate_recommendations)
        builder.add_node("generate_report", self.generate_report)
        builder.add_node("save_result", self.save_result)
        builder.add_node("manual_review", self.manual_review)
        builder.add_node("handle_error", self.handle_error)

        builder.add_edge(START, "validate_input")
        builder.add_conditional_edges(
            "validate_input",
            self._route_validation,
            {"quality": "check_image_quality", "review": "manual_review"},
        )
        builder.add_conditional_edges(
            "check_image_quality",
            self._route_quality,
            {"detect": "detect_traffic_signs", "review": "manual_review", "error": "handle_error"},
        )
        builder.add_conditional_edges(
            "detect_traffic_signs",
            self._route_error,
            {"continue": "check_detection_result", "error": "handle_error"},
        )
        builder.add_edge("check_detection_result", "retrieve_knowledge")
        builder.add_conditional_edges(
            "retrieve_knowledge",
            self._route_error,
            {"continue": "evaluate_risk", "error": "handle_error"},
        )
        builder.add_conditional_edges(
            "evaluate_risk",
            self._route_error,
            {"continue": "generate_recommendations", "error": "handle_error"},
        )
        builder.add_edge("generate_recommendations", "generate_report")
        builder.add_edge("manual_review", "generate_report")
        builder.add_edge("handle_error", "generate_report")
        builder.add_edge("generate_report", "save_result")
        builder.add_edge("save_result", END)
        return builder.compile()

    def run(self, task_id: str) -> dict[str, Any]:
        started = time.perf_counter()
        with self.database.session() as db:
            task = db.get(InspectionTask, task_id)
            if task is None:
                raise ValueError("巡检任务不存在")
            image = task.images[0] if task.images else None
            if image is None:
                raise ValueError("巡检任务没有图片")
            task.status = "running"
            run = AgentRun(task_id=task.id, status="running")
            db.add(run)
            db.commit()
            db.refresh(run)
            initial_state: InspectionState = {
                "task_id": task.id,
                "run_id": run.id,
                "location": task.location,
                "area_type": task.area_type,
                "description": task.description,
                "image_path": image.stored_path,
                "review_required": False,
                "review_reasons": [],
                "detections": [],
                "vision_events": [],
                "knowledge_results": [],
                "error": None,
            }

        final_state: dict[str, Any]
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as exc:
            final_state = dict(initial_state)
            final_state.update(error=str(exc), review_required=True, review_reasons=["工作流发生未处理异常"])
            self._force_failure_report(final_state)

        duration_ms = (time.perf_counter() - started) * 1000
        with self.database.session() as db:
            run = db.get(AgentRun, initial_state["run_id"])
            task = db.get(InspectionTask, task_id)
            if run:
                run.status = "completed_with_review" if final_state.get("review_required") else "completed"
                if final_state.get("error"):
                    run.status = "error"
                    run.error_message = str(final_state["error"])
                run.finished_at = utcnow()
                run.duration_ms = round(duration_ms, 2)
            if task:
                task.total_duration_ms = round(duration_ms, 2)
                if task.status == "running":
                    task.status = "review" if final_state.get("review_required") else "completed"
            db.commit()
        final_state["total_duration_ms"] = round(duration_ms, 2)
        return final_state

    def validate_input(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            reasons = list(state.get("review_reasons", []))
            if not state.get("location", "").strip():
                reasons.append("未填写巡检地点")
            if not Path(state.get("image_path", "")).is_file():
                reasons.append("巡检图片不存在")
            return {"review_required": bool(reasons), "review_reasons": reasons}

        return self._execute_step("validate_input", state, action)

    def check_image_quality(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            quality = self.image_quality_tool.analyze_path(state["image_path"])
            reasons = list(state.get("review_reasons", []))
            if not quality["valid"]:
                reasons.append(quality["message"])
            return {"image_quality": quality, "review_required": bool(reasons), "review_reasons": reasons}

        return self._execute_step("check_image_quality", state, action)

    def detect_traffic_signs(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            output = self.yolo_tool.detect(state["image_path"])
            return {
                "detection_output": output,
                "detections": output["detections"],
                "vision_events": output.get("vision_events", []),
            }

        return self._execute_step("detect_traffic_signs", state, action)

    def check_detection_result(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            detections = state.get("detections", [])
            events = state.get("vision_events", [])
            reasons = list(state.get("review_reasons", []))
            if not detections:
                reasons.append("未检测到可确认的交通标志、人员或车辆目标，不能据此判断现场安全")
            confidence_reason = self._confidence_review_reason(detections)
            if confidence_reason:
                reasons.append(confidence_reason)
            for event in events:
                if event.get("requires_manual_review"):
                    reasons.append(str(event.get("evidence") or event.get("label") or "视觉事件需要人工复核"))
            model_failures = [
                item
                for item in state.get("detection_output", {}).get("models", [])
                if item.get("role") == "general_object" and item.get("error")
            ]
            if model_failures:
                reasons.append("通用人员车辆模型暂不可用，交通标志模型已继续完成检测")
            return {"review_required": bool(reasons), "review_reasons": reasons}

        return self._execute_step("check_detection_result", state, action)

    def retrieve_knowledge(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            class_names = " ".join(str(item.get("class_name", "")) for item in state.get("detections", []))
            query = f"{state.get('area_type', '')} {state.get('location', '')} {class_names} 校园交通安全巡检"
            started = time.perf_counter()
            hits = self.knowledge_base.search(query)
            elapsed_ms = (time.perf_counter() - started) * 1000
            reasons = list(state.get("review_reasons", []))
            if not hits:
                reasons.append("未检索到足够可靠的知识依据")
            return {
                "knowledge_results": hits,
                "knowledge_elapsed_ms": round(elapsed_ms, 2),
                "review_required": bool(reasons),
                "review_reasons": reasons,
            }

        return self._execute_step("retrieve_knowledge", state, action)

    def evaluate_risk(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            detections = state.get("detections", [])
            reasons = list(state.get("review_reasons", []))
            vision_assessment = self._run_vision_assessment(state, detections, reasons)
            result = self.risk_service.evaluate(
                location=state["location"],
                area_type=state["area_type"],
                description=state.get("description"),
                image_quality=state.get("image_quality", {}),
                detections=detections,
                vision_events=state.get("vision_events", []),
                knowledge_hits=state.get("knowledge_results", []),
                review_reasons=reasons,
                vision_assessment=vision_assessment,
            )
            return {
                "risk_result": result.model_dump(),
                "review_required": result.review_required,
                "review_reasons": list(result.policy_reasons),
            }

        return self._execute_step("evaluate_risk", state, action)

    def _run_vision_assessment(
        self,
        state: InspectionState,
        detections: list[dict[str, Any]],
        reasons: list[str],
    ) -> dict[str, Any] | None:
        """旁挂视觉研判（模式乙证据侧车）。任何失败都不允许阻断巡检流程。

        - 服务未启用 / 未注入 → 直接返回 None（与改造前逐字节等价）；
        - 人员闸门：检出 person 的图片不上送云端（隐私，评审 V-2）；
        - 打码/调用失败 → 降级纯文本并追加复核原因（fail-closed，进人工复核）。
        """
        service = self.vision_llm
        if service is None or not service.available:
            return None
        if not vision_person_gate(detections, self.settings.vision_skip_images_with_person):
            return None  # 隐私闸门按设计静默跳过，不追加复核原因
        try:
            return service.assess_image(
                image_path=str(state["image_path"]),
                context={
                    "location": state["location"],
                    "area_type": state["area_type"],
                    "description": state.get("description"),
                    "detections": detections,
                },
            )
        except Exception as exc:  # noqa: BLE001
            reasons.append("视觉研判服务暂不可用，已降级为纯文本研判")
            return None

    def generate_recommendations(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            risk = RiskResult.model_validate(state["risk_result"])
            recommendations = list(dict.fromkeys(item.strip() for item in risk.recommendations if item.strip()))
            if not recommendations:
                recommendations = ["请由校园安全管理人员结合现场情况人工复核并记录处置结果。"]
            risk.recommendations = recommendations
            return {"risk_result": risk.model_dump(), "recommendations": recommendations}

        return self._execute_step("generate_recommendations", state, action)

    def manual_review(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            reasons = list(state.get("review_reasons", [])) or ["输入信息不足，需要人工复核"]
            result = RiskResult(
                risk_level="review",
                risk_score=50,
                problem_summary="当前材料不足以形成确定性风险结论。",
                evidence=[state.get("image_quality", {}).get("message", "输入校验未通过")],
                knowledge_references=[],
                recommendations=["请补充合格图片或完整地点信息后重新执行巡检。", "由校园安全管理人员进行人工复核。"],
                review_required=True,
                uncertainty_note="；".join(reasons),
                analysis_mode="manual_review_guardrail",
            )
            return {
                "risk_result": result.model_dump(),
                "recommendations": result.recommendations,
                "review_required": True,
                "review_reasons": reasons,
            }

        return self._execute_step("manual_review", state, action)

    def handle_error(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            reason = state.get("error") or "工具调用失败"
            reasons = list(state.get("review_reasons", []))
            reasons.append(reason)
            result = RiskResult(
                risk_level="review",
                risk_score=50,
                problem_summary="智能巡检流程未完整执行，系统没有生成确定性安全结论。",
                evidence=[],
                knowledge_references=[],
                recommendations=["检查失败节点配置后重新执行。", "在系统恢复前由管理人员人工复核现场。"],
                review_required=True,
                uncertainty_note="；".join(dict.fromkeys(reasons)),
                analysis_mode="error_guardrail",
            )
            return {
                "risk_result": result.model_dump(),
                "recommendations": result.recommendations,
                "review_required": True,
                "review_reasons": list(dict.fromkeys(reasons)),
            }

        return self._execute_step("handle_error", state, action)

    def generate_report(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            risk = RiskResult.model_validate(state["risk_result"])
            detections = state.get("detections", [])
            detection_rows = "".join(
                "<tr>"
                f"<td>{html.escape(str(item['class_name']))}</td>"
                f"<td>{html.escape(str(item.get('model_name', '未知模型')))}</td>"
                f"<td>{float(item['confidence']):.2%}</td>"
                f"<td>{html.escape(str(item['bbox_xyxy']))}</td>"
                "</tr>"
                for item in detections
            ) or '<tr><td colspan="4">未检测到可确认的视觉目标</td></tr>'
            event_rows = "".join(
                "<tr>"
                f"<td>{html.escape(str(item.get('label', item.get('event_type', '视觉事件'))))}</td>"
                f"<td>{int(item.get('object_count', 0))}</td>"
                f"<td>{int(item.get('threshold', 0))}</td>"
                f"<td>{html.escape(str(item.get('evidence', '')))}</td>"
                "</tr>"
                for item in state.get("vision_events", [])
            ) or '<tr><td colspan="4">未触发视觉事件规则</td></tr>'
            knowledge_items = "".join(
                f"<li><strong>{html.escape(str(ref.get('document', '未知文档')))}</strong>："
                f"{html.escape(str(ref.get('content', '')))}</li>"
                for ref in risk.knowledge_references
            ) or "<li>未检索到足够可靠的知识依据</li>"
            recommendation_items = "".join(f"<li>{html.escape(item)}</li>" for item in risk.recommendations)
            report = f"""
<article class="inspection-report">
  <h1>校园交通安全智能巡检报告</h1>
  <p><strong>任务编号：</strong>{html.escape(state['task_id'])}</p>
  <p><strong>巡检地点：</strong>{html.escape(state['location'])}</p>
  <p><strong>区域类型：</strong>{html.escape(state['area_type'])}</p>
  <p><strong>生成时间：</strong>{utcnow().astimezone().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <h2>视觉检测证据</h2>
  <table><thead><tr><th>类别</th><th>模型</th><th>置信度</th><th>检测框</th></tr></thead><tbody>{detection_rows}</tbody></table>
  <h2>视觉事件</h2>
  <table><thead><tr><th>事件</th><th>目标数</th><th>阈值</th><th>证据</th></tr></thead><tbody>{event_rows}</tbody></table>
  <h2>风险研判</h2>
  <p><strong>风险等级：</strong>{html.escape(risk.risk_level)}</p>
  <p>{html.escape(risk.problem_summary)}</p>
  <p><strong>不确定性：</strong>{html.escape(risk.uncertainty_note or '无')}</p>
  <h2>知识依据</h2><ul>{knowledge_items}</ul>
  <h2>整改建议</h2><ol>{recommendation_items}</ol>
  <p><strong>人工复核：</strong>{'需要' if risk.review_required else '暂不需要'}</p>
</article>
""".strip()
            return {"report_html": report}

        return self._execute_step("generate_report", state, action)

    def save_result(self, state: InspectionState) -> dict[str, Any]:
        def action() -> dict[str, Any]:
            risk = RiskResult.model_validate(state["risk_result"])
            with self.database.session() as db:
                task = db.get(InspectionTask, state["task_id"])
                if task is None:
                    raise ValueError("保存结果时任务不存在")
                db.execute(delete(DetectionResult).where(DetectionResult.task_id == task.id))
                db.execute(delete(RiskAssessment).where(RiskAssessment.task_id == task.id))
                db.execute(delete(Report).where(Report.task_id == task.id))
                inference_ms = (state.get("detection_output", {}).get("timing", {}) or {}).get("inference_ms")
                for item in state.get("detections", []):
                    x1, y1, x2, y2 = item["bbox_xyxy"]
                    db.add(
                        DetectionResult(
                            task_id=task.id,
                            class_id=int(item["class_id"]),
                            class_name=str(item["class_name"]),
                            display_name=str(item.get("display_name", item["class_name"])),
                            model_role=str(item.get("model_role", "traffic_sign")),
                            model_name=str(item.get("model_name", self.settings.yolo_model_path.name)),
                            confidence=float(item["confidence"]),
                            x1=float(x1),
                            y1=float(y1),
                            x2=float(x2),
                            y2=float(y2),
                            inference_ms=inference_ms,
                        )
                    )
                db.add(
                    RiskAssessment(
                        task_id=task.id,
                        risk_level=risk.risk_level,
                        risk_score=risk.risk_score,
                        problem_summary=risk.problem_summary,
                        evidence_json=json.dumps(risk.evidence, ensure_ascii=False),
                        knowledge_references_json=json.dumps(risk.knowledge_references, ensure_ascii=False),
                        recommendations_json=json.dumps(risk.recommendations, ensure_ascii=False),
                        review_required=risk.review_required,
                        uncertainty_note=risk.uncertainty_note,
                        analysis_mode=risk.analysis_mode,
                    )
                )
                report = Report(
                    task_id=task.id,
                    title=f"{task.task_no} 校园交通安全智能巡检报告",
                    html_content=state["report_html"],
                )
                db.add(report)
                task.status = "review" if risk.review_required else "completed"
                task.risk_level = risk.risk_level
                task.review_required = risk.review_required
                task.review_reasons_json = json.dumps(state.get("review_reasons", []), ensure_ascii=False)
                task.vision_events_json = json.dumps(state.get("vision_events", []), ensure_ascii=False)
                output = state.get("detection_output", {})
                task.result_image_url = output.get("result_image_url")
                if task.images and state.get("image_quality"):
                    task.images[0].width = state["image_quality"].get("width")
                    task.images[0].height = state["image_quality"].get("height")
                db.commit()
                db.refresh(report)
                return {"report_id": report.id, "saved": True}

        return self._execute_step("save_result", state, action)

    def _execute_step(
        self, node_name: str, state: InspectionState, action: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        started = time.perf_counter()
        step_id = self._start_step(node_name, state)
        try:
            updates = action()
            self._finish_step(step_id, "success", self._summarize_output(node_name, updates), None, started)
            return updates
        except Exception as exc:
            message = f"{node_name} 失败：{exc}"
            self._finish_step(step_id, "error", None, message, started)
            reasons = list(state.get("review_reasons", []))
            reasons.append(message)
            return {"error": message, "review_required": True, "review_reasons": reasons}

    def _start_step(self, node_name: str, state: InspectionState) -> str:
        with self.database.session() as db:
            sequence = db.scalar(
                select(func.coalesce(func.max(AgentStep.sequence), 0)).where(AgentStep.run_id == state["run_id"])
            )
            step = AgentStep(
                task_id=state["task_id"],
                run_id=state["run_id"],
                sequence=int(sequence or 0) + 1,
                node_name=node_name,
                status="running",
                input_summary=self._summarize_input(node_name, state),
            )
            db.add(step)
            db.commit()
            db.refresh(step)
            return step.id

    def _finish_step(
        self,
        step_id: str,
        status: str,
        output_summary: str | None,
        error: str | None,
        started: float,
    ) -> None:
        with self.database.session() as db:
            step = db.get(AgentStep, step_id)
            if step:
                step.status = status
                step.finished_at = utcnow()
                step.duration_ms = round((time.perf_counter() - started) * 1000, 2)
                step.output_summary = output_summary
                step.error_message = error
                db.commit()

    @staticmethod
    def _summarize_input(node_name: str, state: InspectionState) -> str:
        return json.dumps(
            {
                "node": node_name,
                "task_id": state.get("task_id"),
                "detections": len(state.get("detections", [])),
                "review_required": state.get("review_required", False),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _summarize_output(node_name: str, updates: dict[str, Any]) -> str:
        summary: dict[str, Any] = {"node": node_name, "status": "success"}
        if "detections" in updates:
            summary["detections"] = len(updates["detections"])
        if "vision_events" in updates:
            summary["vision_events"] = len(updates["vision_events"])
        if "knowledge_results" in updates:
            summary["knowledge_hits"] = len(updates["knowledge_results"])
        if "review_required" in updates:
            summary["review_required"] = updates["review_required"]
        if "saved" in updates:
            summary["saved"] = updates["saved"]
        return json.dumps(summary, ensure_ascii=False)

    @staticmethod
    def _route_validation(state: InspectionState) -> Literal["quality", "review"]:
        return "review" if state.get("review_required") else "quality"

    @staticmethod
    def _route_quality(state: InspectionState) -> Literal["detect", "review", "error"]:
        if state.get("error"):
            return "error"
        quality = state.get("image_quality", {})
        return "detect" if quality.get("analyzable") is True else "review"

    def _confidence_review_reason(self, detections: list[dict[str, Any]]) -> str | None:
        """Require review only when no detection clears its model threshold.

        Low-confidence secondary boxes remain visible as candidates, but they no
        longer force an otherwise well-supported task into the manual queue.
        """

        if not detections:
            return None
        reliable_count = sum(
            float(item.get("confidence", 0))
            >= (
                self.settings.general_yolo_review_conf
                if item.get("model_role") == "general_object"
                else self.settings.yolo_review_conf
            )
            for item in detections
        )
        if reliable_count:
            return None
        return f"全部 {len(detections)} 个检测结果均低于对应模型的可靠置信度阈值"

    @staticmethod
    def _route_error(state: InspectionState) -> Literal["continue", "error"]:
        return "error" if state.get("error") else "continue"

    def _force_failure_report(self, state: dict[str, Any]) -> None:
        result = RiskResult(
            risk_level="review",
            risk_score=50,
            problem_summary="工作流发生未处理异常，未形成确定性风险结论。",
            recommendations=["请检查系统日志并由管理人员人工复核。"],
            review_required=True,
            uncertainty_note=str(state.get("error", "未知错误")),
            analysis_mode="fatal_error_guardrail",
        )
        state["risk_result"] = result.model_dump()
        state["report_html"] = f"<h1>巡检失败报告</h1><p>{html.escape(result.uncertainty_note)}</p>"
        try:
            self.save_result(state)
        except Exception:
            with self.database.session() as db:
                task = db.get(InspectionTask, state["task_id"])
                if task:
                    task.status = "error"
                    task.review_required = True
                    db.commit()
