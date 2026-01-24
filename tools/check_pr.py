import os, json, urllib.request, sys
TOKEN = os.environ.get('GHTOKEN')
if not TOKEN:
    print('Missing token', file=sys.stderr); sys.exit(2)
url = 'https://api.github.com/repos/GroverChorizo/TickerTape/pulls?head=GroverChorizo:feat/backend/mvp-snapshots-alerts'
req = urllib.request.Request(url, headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'TickerTape-Agent'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print(json.dumps(data, indent=2))
