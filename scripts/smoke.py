"""Live smoke test against the running Docker stack, using public CC0 media."""
import http.cookiejar
import json
import os
import time
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = os.getenv("BASE_URL", "http://localhost:8090").rstrip('/')
MEDIA = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, data=None, method=None, headers=None):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(BASE + '/api' + path, body, {'Content-Type': 'application/json', **(headers or {})},
                  method=method or ('POST' if data is not None else 'GET'))
    try:
        return opener.open(req, timeout=60)
    except HTTPError as exc:
        raise RuntimeError(f"{exc.code}: {exc.read().decode()}") from exc


def get_json(path, data=None, method=None):
    with request(path, data, method) as response:
        return json.load(response)


def main():
    if os.getenv('SMOKE_TOKEN'):
        get_json('/session', {'token': os.environ['SMOKE_TOKEN']})
    assert get_json('/health')['status'] == 'ok'
    assert get_json('/status')['worker_online'], 'Worker is not ready'
    preview = get_json('/inspect', {'url': MEDIA})
    assert preview['title']
    created = get_json('/tasks', {'urls': [MEDIA], 'clip_start': 0, 'clip_end': 2, 'preset': 'commute'})
    if not created['added']:
        raise RuntimeError('A matching smoke task already exists; delete it or use another preset')
    task_id = created['added'][0]['id']
    keep = os.getenv('KEEP_SMOKE_MEDIA') == '1'
    try:
        for _ in range(90):
            task = get_json(f'/tasks/{task_id}')
            if task['status'] in {'completed', 'failed'}:
                break
            time.sleep(2)
        assert task['status'] == 'completed', task['error'] or task['status']
        assert task['file_size'] > 0
        with request(f'/tasks/{task_id}/file', headers={'Range': 'bytes=0-63'}) as response:
            assert response.status == 206 and len(response.read()) == 64
        get_json(f'/tasks/{task_id}/transcript', {'text': '这是一份用于验证字幕导入的测试资料。\n下载任务会持久化保存，独立 Worker 负责下载。\n视频片段使用 FFmpeg 精确剪辑。'})
        assert get_json(f'/tasks/{task_id}/summary', {'mode': 'local'})['summary']
        with request(f'/tasks/{task_id}/export') as response:
            assert 'FFmpeg' in response.read().decode()
        print(json.dumps({'result': 'passed', 'task_id': task_id, 'title': preview['title'], 'file_bytes': task['file_size'],
                          'checks': ['health', 'worker', 'inspect', 'download', 'clip', 'range', 'captions', 'local summary', 'export']}, ensure_ascii=True))
    finally:
        if not keep:
            current = get_json(f'/tasks/{task_id}')
            if current['status'] in {'downloading', 'processing'}:
                get_json(f'/tasks/{task_id}/actions/cancel', {}, 'POST')
                time.sleep(2)
            get_json(f'/tasks/{task_id}', method='DELETE')


if __name__ == '__main__':
    main()
