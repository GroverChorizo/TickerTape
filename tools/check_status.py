import os
import urllib.request
import sys
TOKEN = os.environ.get('GHTOKEN')
if not TOKEN:
    print('Missing token', file=sys.stderr); sys.exit(2)
sha = '94645ca94d44086f810d006e40accf3a232a73ed'
url = f'https://api.github.com/repos/GroverChorizo/TickerTape/commits/{sha}/status'
req = urllib.request.Request(url, headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','User-Agent':'TickerTape-Agent'})
with urllib.request.urlopen(req) as resp:
    print(resp.read().decode('utf-8'))
