import requests
from bs4 import BeautifulSoup
UA = {'User-Agent': 'Mozilla/5.0 (SearchIntel/1.0)'}
def _get(url):
    r = requests.get(url, headers=UA, timeout=20); r.raise_for_status(); return r
def scrape_flipkart(url: str):
    r = _get(url); soup = BeautifulSoup(r.text, 'html.parser')
    cards = soup.select('article, div.post, div.card, li')
    items = []
    for c in cards[:15]:
        a = c.find('a')
        if not a or not a.get('href'): continue
        title = a.get_text(strip=True); href = a['href']
        if href.startswith('/'): href = url.rstrip('/') + href
        if not title or len(title) < 8: continue
        items.append({'source':'Flipkart Tech','title':title,'url':href,'published':'','summary':'','content':''})
    return items
def scrape_target(url: str):
    r = _get(url); soup = BeautifulSoup(r.text, 'html.parser')
    articles = soup.select('article a, h2 a, h3 a')
    items, seen = [], set()
    for a in articles[:20]:
        href = a.get('href'); title = a.get_text(strip=True)
        if not href or not title or title in seen: continue
        seen.add(title)
        if href.startswith('/'): href = url.rstrip('/') + href
        items.append({'source':'Target Tech','title':title,'url':href,'published':'','summary':'','content':''})
    return items
def scrape_generic(url: str):
    r = _get(url); soup = BeautifulSoup(r.text, 'html.parser')
    items = []
    for a in soup.select('a'):
        title = a.get_text(strip=True); href = a.get('href')
        if not href or not title or len(title) < 12: continue
        if href.startswith('/'): href = url.rstrip('/') + href
        items.append({'source':url,'title':title,'url':href,'published':'','summary':'','content':''})
    return items
