"""Verify yt-dlp's separate video/audio workflow using an official CC BY film."""
import json
import time

from smoke import get_json, request

SOURCE = 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'


def main():
    preview = get_json('/inspect', {'url': SOURCE})
    assert preview['title'] and 480 in preview['heights']
    result = get_json('/tasks', {'urls': [SOURCE], 'preset': 'commute', 'clip_start': 0, 'clip_end': 2})
    task_id = result['added'][0]['id']
    try:
        for _ in range(180):
            task = get_json(f'/tasks/{task_id}')
            if task['status'] in {'completed', 'failed'}:
                break
            time.sleep(2)
        assert task['status'] == 'completed', task['error'] or task['status']
        with request(f'/tasks/{task_id}/file', headers={'Range': 'bytes=0-127'}) as response:
            assert response.status == 206 and len(response.read()) == 128
        print(json.dumps({'result': 'passed', 'source': SOURCE, 'title': preview['title'],
                          'checks': ['platform metadata', 'separate streams', 'merge', 'clip', 'range'],
                          'file_bytes': task['file_size']}, ensure_ascii=True))
    finally:
        task = get_json(f'/tasks/{task_id}')
        if task['status'] in {'downloading', 'processing'}:
            get_json(f'/tasks/{task_id}/actions/cancel', {})
            time.sleep(3)
        get_json(f'/tasks/{task_id}', method='DELETE')


if __name__ == '__main__':
    main()
