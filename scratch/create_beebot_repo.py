import urllib.request
import json
import sys
import os

token = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_HERE")
repo_name = "beebot"

data = {
    "name": repo_name,
    "description": "Beebot - Autonomous boat project (IDA) for water navigation, obstacle avoidance, and Teknofest competition.",
    "private": False,
    "has_issues": True,
    "has_projects": True,
    "has_wiki": True
}

req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=json.dumps(data).encode('utf-8'),
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        print("SUCCESS")
        print("Clone URL:", res_data["clone_url"])
        print("HTML URL:", res_data["html_url"])
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
    sys.exit(1)
