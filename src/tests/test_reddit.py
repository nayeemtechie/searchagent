"""Reddit API test (script app). Usage: python -m src.tests.test_reddit"""
import os, requests
from dotenv import load_dotenv
TOKEN_URL = 'https://www.reddit.com/api/v1/access_token'

def main():
    load_dotenv()
    sub = os.getenv('REDDIT_TEST_SUBREDDIT', 'elasticsearch')
    cid = os.getenv('REDDIT_CLIENT_ID'); csec = os.getenv('REDDIT_CLIENT_SECRET')
    user = os.getenv('REDDIT_USERNAME'); pwd = os.getenv('REDDIT_PASSWORD')
    ua = os.getenv('REDDIT_USER_AGENT', 'script:search-intel-agent:v1.0 (by /u/unknown)')
    if not all([cid, csec, user, pwd]):
        raise SystemExit('Set REDDIT_* env vars in .env')
    auth = requests.auth.HTTPBasicAuth(cid, csec)
    data = {'grant_type':'password','username':user,'password':pwd}
    headers = {'User-Agent': ua}
    r = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers, timeout=20)
    r.raise_for_status(); token = r.json().get('access_token')
    if not token: raise SystemExit(f'Failed token: {r.text}')
    print('✅ Got OAuth token')
    h2 = {'Authorization': f'bearer {token}', 'User-Agent': ua}
    resp = requests.get(f'https://oauth.reddit.com/r/{sub}/new?limit=5', headers=h2, timeout=20)
    if resp.status_code != 200:
        raise SystemExit(f'API error {resp.status_code}: {resp.text}')
    posts = resp.json().get('data', {}).get('children', [])
    if not posts:
        print('No posts found (subreddit may be empty/restricted).')
    for p in posts:
        d = p.get('data', {})
        print('-', d.get('title'), '→', 'https://reddit.com' + d.get('permalink',''))
    print('✅ Reddit API test complete.')

if __name__ == '__main__':
    main()
