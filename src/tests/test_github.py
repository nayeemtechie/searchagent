"""GitHub API test. Usage: python -m src.tests.test_github"""
import os, requests
from dotenv import load_dotenv
REPOS = ['apache/solr','opensearch-project/OpenSearch','elastic/elasticsearch','pgvector/pgvector']

def main():
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN'); headers = {'Accept':'application/vnd.github+json'}
    if token: headers['Authorization'] = f'Bearer {token}'
    for repo in REPOS:
        rel = requests.get(f'https://api.github.com/repos/{repo}/releases?per_page=3', headers=headers, timeout=20)
        if rel.status_code == 200:
            print(f'== {repo} releases ==')
            for r in rel.json():
                print('-', r.get('tag_name'), r.get('name') or '', '→', r.get('html_url'))
        else:
            print(f'!! {repo} releases error {rel.status_code}: {rel.text[:120]}')
    print('✅ GitHub API test complete.')

if __name__ == '__main__':
    main()
