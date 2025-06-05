import json
import os
import subprocess
from datetime import datetime, timezone

import requests

REPO = os.getenv('GITHUB_REPOSITORY', 'your-org/ai-devops-buddy')


def latest_issue(token: str):
    url = f'https://api.github.com/repos/{REPO}/issues'
    r = requests.get(url, headers={'Authorization': f'token {token}'}, params={'state': 'open', 'sort': 'created', 'direction': 'desc'})
    r.raise_for_status()
    issues = [i for i in r.json() if 'pull_request' not in i]
    return issues[0] if issues else None


def repo_summary():
    return subprocess.check_output(['git', 'log', '-1', '--stat']).decode()


def log_stats(tokens: int, finish_reason: str, elapsed: float):
    path = os.path.join('logs', 'codex_stats.json')
    os.makedirs('logs', exist_ok=True)
    data = []
    if os.path.exists(path):
        data = json.load(open(path))
    data.append({'ts': datetime.utcnow().isoformat(), 'tokens': tokens, 'finish_reason': finish_reason, 'tests_elapsed': elapsed})
    json.dump(data, open(path, 'w'), indent=2)


def main():
    token = os.getenv('GITHUB_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    if not token or not openai_key:
        print('Missing tokens')
        return
    issue = latest_issue(token)
    if not issue:
        print('no issue')
        return
    prompt = f"Issue: {issue['title']}\n{issue['body']}\nRepo: {repo_summary()}"
    import openai
    openai.api_key = openai_key
    start = datetime.utcnow()
    resp = openai.ChatCompletion.create(model='gpt-4', messages=[{'role': 'user', 'content': prompt}])
    patch = resp.choices[0].message.content
    with open('codex.patch', 'w') as f:
        f.write(patch)
    subprocess.run(['git', 'apply', 'codex.patch'], check=True)
    subprocess.run(['git', 'commit', '-am', f"Codex update for issue #{issue['number']}"])
    branch = f'codex-{issue["number"]}'
    subprocess.run(['git', 'checkout', '-b', branch], check=True)
    subprocess.run(['git', 'push', 'origin', branch], check=True)
    pr = requests.post(f'https://api.github.com/repos/{REPO}/pulls',
                       headers={'Authorization': f'token {token}'},
                       json={'title': f"Codex fix for #{issue['number']}", 'head': branch, 'base': 'main'})
    pr.raise_for_status()
    prn = pr.json()['number']
    requests.post(f'https://api.github.com/repos/{REPO}/issues/{prn}/labels',
                  headers={'Authorization': f'token {token}'}, json=['code-generated'])
    elapsed = (datetime.utcnow() - start).total_seconds()
    log_stats(resp.usage.total_tokens, resp.choices[0].finish_reason, elapsed)


if __name__ == '__main__':
    main()
