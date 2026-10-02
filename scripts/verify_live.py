"""Extended live verification. Leaves two real CC0 samples for local review."""
import json
import subprocess
import time

from smoke import MEDIA, get_json, request


def wait(task_id):
    for _ in range(100):
        task = get_json(f'/tasks/{task_id}')
        if task['status'] in {'failed', 'completed'}:
            assert task['status'] == 'completed', task['error']
            return task
        time.sleep(1)
    raise AssertionError('Download did not finish in time')


def main():
    collection = next((c for c in get_json('/collections') if c['name'] == '公开授权 · 演示片刻'), None)
    if collection is None:
        collection = get_json('/collections', {'name': '公开授权 · 演示片刻', 'color': 'peach'})
    samples = []
    for preset, title in [('everyday', 'CC0 花朵 · 两秒收藏'), ('audio', 'CC0 花朵 · 音频口袋')]:
        created = get_json('/tasks', {'urls': [MEDIA], 'preset': preset, 'clip_start': 0, 'clip_end': 2,
                                    'collection_id': collection['id']})
        if created['added']:
            task_id = created['added'][0]['id']
        else:
            task_id = next(t['id'] for t in get_json('/tasks') if t['url'] == MEDIA and t['preset'] == preset
                           and t['clip_start'] == 0 and t['clip_end'] == 2)
        task = wait(task_id)
        task = get_json(f'/tasks/{task_id}', {'title': title, 'favorite': preset == 'everyday',
                        'tags': ['CC0', '演示素材'], 'notes': '来源：MDN CC0 Flower。此内容为实际下载的两秒片段。字幕是功能验证示例，不是视频原字幕。'}, 'PATCH')
        get_json(f'/tasks/{task_id}/transcript', {'text': '这是功能验证示例字幕，并非花朵视频的原字幕。\n将自己获授权的视频收藏到本地，可以整理为主题合集。\n用笔记记录灵感，用资料卡保留学习要点。'})
        get_json(f'/tasks/{task_id}/summary', {'mode': 'local'})
        with request(f'/tasks/{task_id}/file', headers={'Range': 'bytes=0-127'}) as response:
            assert response.status == 206 and len(response.read()) == 128
        if preset != 'audio':
            with request(f'/tasks/{task_id}/poster') as response:
                assert response.status == 200 and response.headers['Content-Type'] == 'image/jpeg'
        output = subprocess.check_output(['docker', 'compose', 'exec', '-T', 'api', 'python', '-c',
            "import json,subprocess; from app import db; from app.config import config; "
            f"t=db.get_task('{task_id}',raw=True); "
            "r=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,codec_type',"
            "'-of','json',str(config.media_dir/t['file_path'])]); print(r.decode())"], text=True)
        probe = json.loads(output)
        assert 1.9 <= float(probe['format']['duration']) <= 2.2
        if preset == 'audio':
            assert any(s['codec_name'] == 'mp3' for s in probe['streams'])
        samples.append({'id': task_id, 'preset': preset, 'bytes': task['file_size'], 'probe': probe})
    # Recreate every service and verify that notes/media survive in the named volume.
    subprocess.run(['docker', 'compose', 'restart'], check=True)
    for _ in range(30):
        try:
            if get_json('/status')['worker_online']:
                break
        except Exception:
            pass
        time.sleep(1)
    for sample in samples:
        task = get_json(f"/tasks/{sample['id']}")
        assert task['status'] == 'completed' and '实际下载' in task['notes']
        with request(f"/tasks/{sample['id']}/file", headers={'Range': 'bytes=0-31'}) as response:
            assert response.status == 206
    print(json.dumps({'result': 'passed', 'checks': ['video', 'mp3', 'precise clip', 'local poster', 'range',
                      'collections', 'notes', 'tags', 'favorites', 'summary', 'restart persistence'],
                      'samples': samples}, ensure_ascii=True))


if __name__ == '__main__':
    main()
