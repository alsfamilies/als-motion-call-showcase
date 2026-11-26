"""Close the public download release seven days after it was published."""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = 'alsfamilies/als-motion-call-showcase'
TAG = 'trial-v0.8.2'
START = '<!-- downloads:start -->'
END = '<!-- downloads:end -->'
CLOSED = '本轮试用下载已结束。'

def github(path, method='GET', data=None):
    req = Request(
        f'https://api.github.com/repos/{REPOSITORY}/{path}',
        data=None if data is None else json.dumps(data).encode(),
        headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
        },
        method=method,
    )
    with urlopen(req, timeout=20) as response:
        body = response.read()
        return json.loads(body) if body else None

def close_if_due(now):
    try:
        release = github('releases/tags/' + TAG)
    except HTTPError as error:
        if error.code != 404:
            raise
        release = None
    if release:
        if release['draft']:
            print('Download release has not opened.')
            return
        published = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
        deadline = published + timedelta(days=7)
        if now < deadline:
            print('Download remains open until', deadline.isoformat())
            return
        github(f"releases/{release['id']}", 'DELETE')
        print('Expired release and attached downloads removed.')

    readme = github('contents/README.md')
    original = base64.b64decode(readme['content']).decode()
    before, marker, tail = original.partition(START)
    current, end, after = tail.partition(END)
    if not marker or not end:
        raise RuntimeError('Download section markers are missing.')
    if 'releases/tag/' + TAG not in current:
        return
    updated = before + START + '\n' + CLOSED + '\n' + END + after
    github('contents/README.md', 'PUT', {
        'message': 'Close the expired trial download',
        'sha': readme['sha'],
        'content': base64.b64encode(updated.encode()).decode(),
    })
    print('Download entry removed from README.')

if __name__ == '__main__':
    if os.environ['GITHUB_REPOSITORY'] != REPOSITORY:
        raise SystemExit('Unexpected repository.')
    close_if_due(datetime.now(timezone.utc))
