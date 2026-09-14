"""Run authorized campus media through real endpoints in an isolated database.

Uses production guardrails and providers; does not upload any knowledge fixture
to the production service. Results are evidence, not model-accuracy estimates.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', action='append', type=Path, default=[])
    parser.add_argument('--video', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix='campus-delivery-') as temp:
        isolated = Path(temp)
        settings = Settings(
            database_url=f"sqlite:///{isolated / 'delivery.db'}",
            qdrant_path=str(isolated / 'qdrant'),
            upload_dir=isolated / 'uploads',
            output_dir=isolated / 'outputs',
            yolo_model_path=ROOT / 'models/yolo26-tt100k-best.pt',
            general_yolo_model_path=ROOT / 'models/yolo26m.pt',
            api_key=None,
        )
        app = create_app(settings)
        with TestClient(app) as client:
            # Same retained authoritative sources, not the example fixture.
            for source in sorted((ROOT / 'knowledge').glob('*.md')):
                if source.name == '校园交通巡检示例规范.md':
                    continue
                with source.open('rb') as stream:
                    response = client.post('/api/v1/knowledge/documents', files={'file': (source.name, stream, 'text/markdown')})
                response.raise_for_status()
            for image in args.image:
                with image.open('rb') as stream:
                    response = client.post('/api/v1/inspections', data={'location': f'隔离演示-{image.stem}', 'area_type': '校园主干道'}, files={'file': (image.name, stream, 'image/jpeg')})
                response.raise_for_status()
                task_id = response.json()['id']
                client.post(f'/api/v1/inspections/{task_id}/execute').raise_for_status()
                detail = client.get(f'/api/v1/inspections/{task_id}').json()
                report_id = detail.get('report_id')
                report_response = client.get(f'/api/v1/reports/{report_id}') if report_id else None
                trace = client.get(f'/api/v1/inspections/{task_id}/trace').json()
                results.append({'media': str(image), 'kind': 'image', 'status': detail['status'], 'detections': len(detail.get('detections', [])), 'people': sum(d['class_name'] == 'person' for d in detail.get('detections', [])), 'risk': detail.get('risk_result'), 'review_reasons': detail.get('review_reasons'), 'trace': trace, 'report_readable': report_response is not None and report_response.status_code == 200})
            if args.video:
                with args.video.open('rb') as stream:
                    response = client.post('/api/v1/video-analytics', data={'location': '隔离视频演示', 'allowed_direction': 'left_to_right'}, files={'file': (args.video.name, stream, 'video/mp4')})
                response.raise_for_status()
                results.append({'media': str(args.video), 'kind': 'video', 'result': response.json(), 'direction_note': '从左向右仅为配置测试，不代表现场真实通行方向；移动镜头不得用于逆行真值验证。'})
        app.state.database.engine.dispose()
        app.state.knowledge_base.client.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'isolated': True, 'production_guardrails': True, 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'cases': len(results)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
