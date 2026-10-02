"""Verify pause/resume on an active, rate-limited real download."""
import json
import time

from smoke import MEDIA, get_json


def main():
    result = get_json('/tasks', {'urls': [MEDIA], 'preset': 'commute', 'clip_start': 0, 'clip_end': 3,
                               'rate_limit': 48})
    task_id = result['added'][0]['id']
    try:
        for _ in range(60):
            task = get_json(f'/tasks/{task_id}')
            if task['status'] == 'downloading' and task['progress'] > 5:
                break
            if task['status'] == 'failed':
                raise AssertionError(task['error'])
            time.sleep(0.5)
        assert task['status'] == 'downloading' and task['progress'] > 5
        get_json(f'/tasks/{task_id}/actions/pause', {})
        time.sleep(2)
        paused = get_json(f'/tasks/{task_id}')
        assert paused['status'] == 'paused'
        time.sleep(2)
        assert get_json(f'/tasks/{task_id}')['progress'] == paused['progress']
        get_json(f'/tasks/{task_id}/actions/resume', {})
        for _ in range(120):
            task = get_json(f'/tasks/{task_id}')
            if task['status'] in {'completed', 'failed'}:
                break
            time.sleep(1)
        assert task['status'] == 'completed', task['error']
        print(json.dumps({'result': 'passed', 'checks': ['rate limit', 'active download pause', 'stable paused progress',
                          'resume', 'completed file'], 'paused_progress': paused['progress'], 'file_bytes': task['file_size']}))
    finally:
        task = get_json(f'/tasks/{task_id}')
        if task['status'] in {'downloading', 'processing'}:
            get_json(f'/tasks/{task_id}/actions/cancel', {})
            time.sleep(2)
        get_json(f'/tasks/{task_id}', method='DELETE')


if __name__ == '__main__':
    main()
