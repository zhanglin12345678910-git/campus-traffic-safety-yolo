# Agent 设计

系统使用 `langgraph.graph.StateGraph` 构建并编译，不是手写 if/else 流程的包装。

## 状态

状态携带任务/运行 ID、地点、区域、现场说明、图片路径、图片质量、检测结果、知识命中、风险结果、整改建议、报告、复核标记、复核原因和错误信息。前端不直接修改工作流状态，所有节点轨迹由后端持久化。

## 节点与路由

```text
START → validate_input
  ├─ 输入不足 → manual_review ─┐
  └─ 合法 → check_image_quality│
       ├─ 质量不足 → manual_review
       ├─ 工具异常 → handle_error
       └─ 合格 → detect_traffic_signs
                    ├─ 异常 → handle_error
                    └─ check_detection_result
                         → retrieve_knowledge
                         → evaluate_risk
                         → generate_recommendations
                         → generate_report
                         → save_result → END
```

`manual_review` 和 `handle_error` 也会生成“材料不足/执行失败”的正式报告，确保每次运行都有可追溯结论，但不会制造确定性安全判断。

## 人工复核条件

- 图片损坏、尺寸不足、过暗、过亮或模糊。
- YOLO 未检出目标。
- 任一检测置信度低于配置阈值。
- 没有达到阈值的知识依据。
- 未配置 LLM（规则保守模式）。
- LLM、YOLO、Qdrant 或其他节点发生异常。

每个步骤保存输入摘要、输出摘要、开始/结束时间、耗时、状态和错误。SSE 接口从数据库读取新增步骤，因此页面展示的是实际执行状态。
