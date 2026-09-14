"""Real browser/API acceptance in disposable, migrated local stores.

No production writes. Real providers may incur the existing project's API cost.
Run with yolo_change from the repository root; keep formal GPU weights.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BROWSER = Path(os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE', r'local-path/chrome-headless-shell.exe'))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend-port', type=int, default=8002)
    parser.add_argument('--frontend-port', type=int, default=5176)
    args = parser.parse_args()
    image = args.image.resolve(strict=True)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for port in (args.backend_port, args.frontend_port):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))  # Fail safely; never stop an unrelated listener.
    cases: list[dict] = []
    runtime: dict = {'isolated': True, 'device_requested': '0'}
    signals: dict = {'page_errors': [], 'console_errors': []}
    def case(name, action):
        start = time.monotonic()
        try:
            action()
            cases.append({'name': name, 'status': 'passed', 'seconds': round(time.monotonic() - start, 2)})
        except Exception as exc:
            # Do not dump HTTP request headers, bodies or provider keys.
            cases.append({'name': name, 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}', 'seconds': round(time.monotonic() - start, 2)})
    children = []
    with tempfile.TemporaryDirectory(prefix='functional-acceptance-', dir=ROOT / 'outputs') as temp:
        isolated = Path(temp)
        env = dict(os.environ, DATABASE_URL=f'sqlite:///{isolated / "acceptance.db"}',
                   QDRANT_URL='', QDRANT_PATH=str(isolated / 'qdrant'),
                   UPLOAD_DIR=str(isolated / 'uploads'), OUTPUT_DIR=str(isolated / 'outputs'),
                   YOLO_MODEL_PATH=str(ROOT / 'models/yolo26-tt100k-best.pt'),
                   GENERAL_YOLO_MODEL_PATH=str(ROOT / 'models/yolo26m.pt'),
                   YOLO_DEVICE='0', API_KEY='',
                   VITE_DEV_API_TARGET=f'http://127.0.0.1:{args.backend_port}')
        with (isolated / 'process.log').open('w', encoding='utf-8') as log:
            def migrate():
                proc = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT / 'backend', env=env, stdout=log, stderr=log, timeout=60)
                assert proc.returncode == 0, 'isolated migration failed'
                from sqlalchemy import create_engine, text
                engine = create_engine(env['DATABASE_URL'])
                with engine.connect() as connection:
                    revision = connection.execute(text('select version_num from alembic_version')).scalar()
                    assert revision == '0002_multimodel_vision', revision
                engine.dispose()
                runtime['migration_head'] = revision
            case('隔离 SQLite 从空库迁移到当前 head', migrate)
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(args.backend_port)], cwd=ROOT / 'backend', env=env, stdout=log, stderr=log, creationflags=flags))
                children.append(subprocess.Popen([shutil.which('node') or 'node', str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(args.frontend_port), '--strictPort'], cwd=ROOT / 'frontend', env=env, stdout=log, stderr=log, creationflags=flags))
                base = f'http://127.0.0.1:{args.frontend_port}'
                with httpx.Client(base_url=base, timeout=180, trust_env=False) as client:
                    deadline = time.monotonic() + 90
                    while True:
                        try:
                            client.get('/api/v1/health').raise_for_status()
                            break
                        except httpx.HTTPError:
                            assert all(p.poll() is None for p in children), 'isolated process exited'
                            if time.monotonic() > deadline:
                                raise TimeoutError('isolated services did not become ready')
                            time.sleep(1)
                    def knowledge():
                        assert client.get('/api/v1/knowledge/documents').json()['total'] == 0
                        for source in sorted((ROOT / 'knowledge').glob('*.md')):
                            if source.name == '校园交通巡检示例规范.md':
                                continue
                            with source.open('rb') as stream:
                                client.post('/api/v1/knowledge/documents', files={'file': (source.name, stream, 'text/markdown')}).raise_for_status()
                        docs = client.get('/api/v1/knowledge/documents').json()['items']
                        assert len(docs) == 5 and all(d['status'] == 'ready' for d in docs)
                        runtime['knowledge_chunks'] = sum(d['chunk_count'] for d in docs)
                        hits = client.post('/api/v1/knowledge/search', json={'query': '消防通道禁止停车', 'top_k': 5})
                        hits.raise_for_status()
                        assert hits.json()['hits'], 'no real retrieval hits'
                    case('真实五份知识来源入隔离库、分块与检索', knowledge)
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch(executable_path=str(BROWSER), headless=True)
                        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                        page = context.new_page()
                        page.on('pageerror', lambda e: signals['page_errors'].append(str(e)))
                        page.on('console', lambda m: signals['console_errors'].append(m.text) if m.type == 'error' else None)
                        def upload():
                            page.goto(base + '/inspection/new')
                            page.get_by_role('button', name='开始智能巡检', exact=True).click()
                            page.get_by_text('请填写地点并选择巡检图片', exact=True).wait_for()
                            page.get_by_placeholder('例如：学校大门东侧入口').fill('隔离验收-校园人员与车辆')
                            page.locator('.upload-zone input[type="file"]').set_input_files(str(image))
                            page.get_by_role('button', name='开始智能巡检', exact=True).click()
                            page.wait_for_url(re.compile(r'/inspection/[0-9a-f-]{36}$'), timeout=60_000)
                            task_id = page.url.rsplit('/', 1)[-1]
                            deadline = time.monotonic() + 240
                            while time.monotonic() < deadline:
                                response = client.get(f'/api/v1/inspections/{task_id}')
                                response.raise_for_status()
                                task = response.json()
                                if task['status'] in ('completed', 'review', 'error', 'rejected'):
                                    break
                                time.sleep(1)
                            assert task['status'] == 'review', task['status']
                            assert task['risk_result'] and task['report_id']
                            assert len(task['detections']) > 0
                            assert task['risk_result']['analysis_mode'] == 'llm', 'real DeepSeek did not complete'
                            health = client.get('/api/v1/health').json()
                            assert health['services']['yolo']['loaded'] and health['services']['general_yolo']['loaded']
                            gpu = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=15)
                            assert gpu.returncode == 0 and str(children[0].pid) in gpu.stdout.split(), 'isolated inference process was not observed on GPU'
                            runtime['gpu_process_seen'] = True
                            runtime.update(task_id=task_id, people=sum(d['class_name'] == 'person' for d in task['detections']), detections=len(task['detections']), analysis_mode=task['risk_result']['analysis_mode'], vision_model=health['services']['vision_llm']['model'])
                            trace = client.get(f'/api/v1/inspections/{task_id}/trace').json()['steps']
                            assert len(trace) >= 9 and not any(s['status'] == 'error' for s in trace)
                            page.reload()
                            page.get_by_role('button', name='人工确认', exact=True).wait_for(timeout=30_000)
                            page.screenshot(path=str(output.parent / 'functional-detail-before-review.png'), full_page=True)
                        case('浏览器必填校验→真实图片上传→GPU 双模型→RAG/DeepSeek→报告与轨迹', upload)
                        def review():
                            task_id = runtime['task_id']
                            task = client.get(f'/api/v1/inspections/{task_id}').json()
                            report = client.get(f'/api/v1/reports/{task["report_id"]}/view')
                            assert report.status_code == 200 and len(report.text) > 100
                            page.goto(base + '/reviews')
                            page.get_by_role('button', name='进入复核', exact=True).first.click()
                            page.wait_for_url('**/inspection/' + task_id)
                            page.get_by_role('button', name='人工确认', exact=True).click()
                            page.get_by_text('人工复核已确认', exact=True).wait_for()
                            confirmed = client.get(f'/api/v1/inspections/{task_id}').json()
                            assert confirmed['status'] == 'completed' and not confirmed['review_required']
                            client.post(f'/api/v1/inspections/{task_id}/feedback', json={'rating': 5, 'comment': '隔离测试反馈'}).raise_for_status()
                            assert client.get(f'/api/v1/inspections/{task_id}').json()['feedback_rating'] == 5
                            summary = client.get('/api/v1/analytics/overview').json()['summary']
                            assert summary['total_tasks'] == 1 and summary['completed_tasks'] == 1 and summary['review_required'] == 0
                            page.goto(base + '/inspections')
                            page.get_by_text(task['task_no'], exact=True).first.wait_for()
                        case('复核入口→人工确认持久化→报告 HTML→反馈→档案与统计一致', review)
                        def pages():
                            for width, height in ((1440, 1000), (390, 844)):
                                page.set_viewport_size({'width': width, 'height': height})
                                for route in ('/dashboard', '/analytics', '/inspection/new', '/inspections', '/reviews', '/knowledge', '/settings'):
                                    response = page.goto(base + route)
                                    assert response and response.status == 200
                                    page.wait_for_timeout(500)
                                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{width} {route} overflow'
                            assert not signals['page_errors'], signals['page_errors']
                        case('七页面桌面/移动端布局与清空后的真实复核空态', pages)
                        browser.close()
                    def negative():
                        assert client.get('/api/v1/inspections/not-found').status_code == 404
                        assert client.post('/api/v1/knowledge/search', json={'query': '', 'top_k': 0}).status_code == 422
                        assert client.post(f'/api/v1/inspections/{runtime["task_id"]}/feedback', json={'rating': 6}).status_code == 422
                        assert client.post('/api/v1/inspections', data={'location': '隔离无效图片', 'area_type': '校门口'}, files={'file': ('broken.jpg', b'not an image', 'image/jpeg')}).status_code == 400
                    case('不存在资源、检索/反馈边界、损坏图片拒绝', negative)
            finally:
                for child in reversed(children):
                    child.terminate()
                    try:
                        child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=15)
    report = {'runtime': runtime, 'cases': cases, 'signals': signals, 'passed': sum(c['status'] == 'passed' for c in cases), 'failed': sum(c['status'] == 'failed' for c in cases)}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    if report['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
