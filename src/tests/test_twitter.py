"""Twitter/X API v2 Recent Search. Usage: python -m src.tests.test_twitter"""
import os, requests
from dotenv import load_dotenv

def main():
    load_dotenv()
    bearer = os.getenv('TWITTER_BEARER_TOKEN')
    if not bearer: raise SystemExit('Set TWITTER_BEARER_TOKEN in .env')
    headers = {'Authorization': f'Bearer {bearer}'}
    params = {'query':'(hybrid search) (ecommerce OR retail) lang:en -is:retweet',
              'max_results':'10','tweet.fields':'author_id,created_at,public_metrics,text'}
    url = 'https://api.twitter.com/2/tweets/search/recent'
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code != 200: raise SystemExit(f'X API error {r.status_code}: {r.text}')
    data = r.json()
    for t in data.get('data', []):
        pm = t.get('public_metrics', {})
        print(f"- {t.get('created_at')}  ❤️{pm.get('like_count',0)}  {t.get('text')[:120]!r}")
    print('✅ Twitter/X API test complete.')

if __name__ == '__main__':
    main()
