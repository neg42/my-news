import urllib.request, urllib.error, xml.etree.ElementTree as ET
import json, datetime, re, time

SOURCES = [
  {"id":"s1","name":"NHK ニュース",
   "urls":["https://www.nhk.or.jp/rss/news/cat0.xml",
           "https://www3.nhk.or.jp/rss/news/cat0.xml"]},
  {"id":"s2","name":"朝日新聞",
   "urls":["https://www.asahi.com/rss/asahi/newsheadlines.rdf"]},
  {"id":"s3","name":"日本経済新聞",
   "urls":["https://www.nikkei.com/rss/news.rdf",
           "https://www.nikkei.com/rss/index.rdf"]},
  {"id":"s4","name":"テレ朝NEWS",
   "urls":["https://news.tv-asahi.co.jp/rss20/news_all.xml",
           "https://news.tv-asahi.co.jp/rss/index.xml"]},
  {"id":"s5","name":"TBS NEWS DIG",
   "urls":["https://newsdig.tbs.co.jp/rss",
           "https://newsdig.tbs.co.jp/articles/rss"]},
  {"id":"s6","name":"FNNプライムオンライン",
   "urls":["https://feeds.fnn.jp/fnnprime/rss.xml",
           "https://www.fnn.jp/rss/articles"]},
  {"id":"s7","name":"毎日新聞",
   "urls":["https://mainichi.jp/rss/etc/mainichi-flash.rss",
           "https://mainichi.jp/rss/etc/mainichi-news.rss"]},
]

RDF_NS   = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
RSS_NS   = 'http://purl.org/rss/1.0/'
ATOM_NS  = 'http://www.w3.org/2005/Atom'
MEDIA_NS = 'http://search.yahoo.com/mrss/'
DC_NS    = 'http://purl.org/dc/elements/1.1/'

USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html)',
]

def fetch_url(url):
  for ua in USER_AGENTS:
    try:
      req = urllib.request.Request(url, headers={
        'User-Agent': ua,
        'Accept': 'application/rss+xml,application/rdf+xml,application/xml,text/xml,*/*',
        'Accept-Language': 'ja,en;q=0.9',
      })
      with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
      if len(data) > 200:
        return data
    except urllib.error.HTTPError as e:
      print(f"  HTTP {e.code}: {url}")
    except Exception as e:
      print(f"  ERR: {e}")
    time.sleep(0.3)
  return None

def get_text(el, *tags):
  for tag in tags:
    child = el.find(tag)
    if child is not None and child.text:
      return child.text.strip()
  return ''

def get_image(item):
  for tag in [f'{{{MEDIA_NS}}}thumbnail', f'{{{MEDIA_NS}}}content']:
    el = item.find(tag)
    if el is not None:
      u = el.get('url', '')
      if u: return u
  enc = item.find('enclosure')
  if enc is not None and enc.get('type', '').startswith('image'):
    return enc.get('url', '')
  desc = get_text(item, 'description', f'{{{RSS_NS}}}description')
  m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc, re.I)
  return m.group(1) if m else ''

def parse_feed(data, src):
  items_out = []
  try:
    root = ET.fromstring(data)
    tag  = root.tag
    if ATOM_NS in tag:
      for item in root.findall(f'{{{ATOM_NS}}}entry'):
        title = get_text(item, f'{{{ATOM_NS}}}title')
        link  = ''
        lel   = item.find(f'{{{ATOM_NS}}}link')
        if lel is not None:
          link = lel.get('href', '') or lel.text or ''
        pub = get_text(item, f'{{{ATOM_NS}}}published', f'{{{ATOM_NS}}}updated')
        items_out.append((title, link, pub, get_image(item)))
    elif RDF_NS in tag or 'RDF' in tag:
      for item in root.findall(f'{{{RSS_NS}}}item'):
        title = get_text(item, f'{{{RSS_NS}}}title', 'title')
        link  = get_text(item, f'{{{RSS_NS}}}link',  'link')
        pub   = get_text(item, f'{{{DC_NS}}}date',   'pubDate')
        items_out.append((title, link, pub, get_image(item)))
      if not items_out:
        for item in root.findall('.//item'):
          title = get_text(item, 'title')
          link  = get_text(item, 'link')
          pub   = get_text(item, 'pubDate', f'{{{DC_NS}}}date')
          items_out.append((title, link, pub, get_image(item)))
    else:
      for item in root.findall('.//item'):
        title = get_text(item, 'title')
        link  = get_text(item, 'link')
        pub   = get_text(item, 'pubDate', f'{{{DC_NS}}}date')
        items_out.append((title, link, pub, get_image(item)))
  except ET.ParseError as e:
    print(f"  XMLパースエラー: {e}")
    return []

  result = []
  for title, link, pub, image in items_out[:20]:
    title = title.strip()
    link  = link.strip()
    if not title or not link or not link.startswith('http'):
      continue
    link = link.replace('//www.nhk.or.jp/news/', '//www3.nhk.or.jp/news/')
    result.append({
      'id': link, 'title': title, 'link': link,
      'pubDate': pub, 'image': image,
      'source': src['name'], 'sid': src['id'],
    })
  return result

all_items = []
for src in SOURCES:
  print(f"\n=== {src['name']} ===")
  data = None
  for url in src['urls']:
    print(f"  試行: {url}")
    data = fetch_url(url)
    if data:
      print(f"  取得: {len(data)} bytes")
      break
  if not data:
    print(f"  失敗")
    continue
  items = parse_feed(data, src)
  print(f"  件数: {len(items)}")
  if items:
    print(f"  例: {items[0]['title'][:50]}")
  all_items.extend(items)

output = {
  'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'items': all_items,
}
with open('data.json', 'w', encoding='utf-8') as f:
  json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n=== 保存完了: {len(all_items)}件 ===")
