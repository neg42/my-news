import urllib.request, urllib.error, xml.etree.ElementTree as ET
import json, datetime, re, time

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ソース定義
# type: "rss" = 通常RSS/RDF, "youtube" = YouTube チャンネルRSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCES = [
  # ── NHK（カテゴリ別・合計40〜50件）──────────────────────────
  {"id":"s1","name":"NHK ニュース","type":"rss",
   "url":"https://www.nhk.or.jp/rss/news/cat0.xml"},
  {"id":"s1","name":"NHK ニュース","type":"rss",
   "url":"https://www.nhk.or.jp/rss/news/cat1.xml"},
  {"id":"s1","name":"NHK ニュース","type":"rss",
   "url":"https://www.nhk.or.jp/rss/news/cat4.xml"},
  {"id":"s1","name":"NHK ニュース","type":"rss",
   "url":"https://www.nhk.or.jp/rss/news/cat5.xml"},
  {"id":"s1","name":"NHK ニュース","type":"rss",
   "url":"https://www.nhk.or.jp/rss/news/cat6.xml"},

  # ── 新聞社（RSS）────────────────────────────────────────
  {"id":"s2","name":"朝日新聞","type":"rss",
   "url":"https://www.asahi.com/rss/asahi/newsheadlines.rdf"},
  {"id":"s7","name":"毎日新聞","type":"rss",
   "url":"https://mainichi.jp/rss/etc/mainichi-flash.rss"},
  {"id":"s8","name":"産経ニュース","type":"rss",
   "url":"https://www.sankei.com/rss/news/flash/today/newsflash-story.rss"},

  # ── テレビ局（YouTube RSS）───────────────────────────────
  {"id":"s4","name":"テレ朝NEWS","type":"youtube",
   "channel_id":"UCivjgV3f4b5kBFj-4WExXAQ"},   # ANNnewsCH
  {"id":"s5","name":"TBS NEWS DIG","type":"youtube",
   "channel_id":"UC6AG81pAkf6Lbi_1VC5NmPA"},
  {"id":"s6","name":"FNNプライムオンライン","type":"youtube",
   "channel_id":"UCoQBJMzcwmXrRSHBFAlTsIw"},
  {"id":"s3","name":"日テレNEWS","type":"youtube",
   "channel_id":"UCuTAXTexrhetbOe3zgskJBQ"},
  {"id":"s10","name":"日本経済新聞","type":"youtube",
   "channel_id":"UCHL12woHGeiqAqLrK-pJe7g"},
]

ATOM_NS  = 'http://www.w3.org/2005/Atom'
MEDIA_NS = 'http://search.yahoo.com/mrss/'
RSS_NS   = 'http://purl.org/rss/1.0/'
RDF_NS   = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
DC_NS    = 'http://purl.org/dc/elements/1.1/'
YT_NS    = 'http://www.youtube.com/xml/schemas/2015'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) '
      'Version/17.0 Safari/605.1.15')

def fetch(url):
  for attempt in range(3):
    try:
      req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'application/rss+xml,application/rdf+xml,application/atom+xml,application/xml,text/xml,*/*',
        'Accept-Language': 'ja,en;q=0.9',
      })
      with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()
      if len(data) > 200:
        return data
    except urllib.error.HTTPError as e:
      print(f"  HTTP {e.code} (試行{attempt+1}): {url}")
    except Exception as e:
      print(f"  ERR {e} (試行{attempt+1}): {url}")
    time.sleep(1)
  return None

def txt(el, *tags):
  for tag in tags:
    try:
      c = el.find(tag)
      if c is not None and c.text:
        return c.text.strip()
    except: pass
  return ''

def get_image_rss(item):
  # media:thumbnail / media:content[url]
  for tag in [f'{{{MEDIA_NS}}}thumbnail', f'{{{MEDIA_NS}}}content']:
    try:
      el = item.find(tag)
      if el is not None:
        u = el.get('url','')
        if u: return u
    except: pass
  # enclosure
  enc = item.find('enclosure')
  if enc is not None and enc.get('type','').startswith('image'):
    return enc.get('url','')
  # img in description
  desc = txt(item,'description',f'{{{RSS_NS}}}description')
  m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc, re.I)
  return m.group(1) if m else ''

def parse_rss(data, src):
  """RSS 2.0 / RDF 1.0 パーサー"""
  try:
    root = ET.fromstring(data)
  except ET.ParseError as e:
    print(f"  XML parse error: {e}")
    return []

  tag = root.tag
  raw = []

  if RSS_NS in tag or RDF_NS in tag:
    # RDF 1.0（朝日など）
    for item in root.findall(f'{{{RSS_NS}}}item'):
      title = txt(item, f'{{{RSS_NS}}}title', 'title')
      link  = txt(item, f'{{{RSS_NS}}}link', 'link')
      if not link:
        lel = item.find(f'{{{RSS_NS}}}link')
        if lel is not None:
          link = lel.get(f'{{{RDF_NS}}}resource','')
      pub = txt(item, f'{{{DC_NS}}}date', 'pubDate')
      raw.append((title, link, pub, get_image_rss(item)))
    # フォールバック
    if not raw:
      for item in root.findall('.//item'):
        raw.append((
          txt(item,'title'),
          txt(item,'link'),
          txt(item,'pubDate',f'{{{DC_NS}}}date'),
          get_image_rss(item)
        ))
  else:
    # RSS 2.0
    for item in root.findall('.//item'):
      raw.append((
        txt(item,'title'),
        txt(item,'link'),
        txt(item,'pubDate',f'{{{DC_NS}}}date'),
        get_image_rss(item)
      ))

  return build_items(raw, src)

def parse_youtube(data, src):
  """YouTube Atom フィードパーサー（サムネイル付き）"""
  try:
    root = ET.fromstring(data)
  except ET.ParseError as e:
    print(f"  XML parse error: {e}")
    return []

  raw = []
  for entry in root.findall(f'{{{ATOM_NS}}}entry'):
    title = txt(entry, f'{{{ATOM_NS}}}title')
    link  = ''
    lel   = entry.find(f'{{{ATOM_NS}}}link')
    if lel is not None:
      link = lel.get('href','')
    pub = txt(entry, f'{{{ATOM_NS}}}published', f'{{{ATOM_NS}}}updated')

    # YouTube サムネイル（media:group > media:thumbnail）
    image = ''
    group = entry.find(f'{{{MEDIA_NS}}}group')
    if group is not None:
      th = group.find(f'{{{MEDIA_NS}}}thumbnail')
      if th is not None:
        image = th.get('url','')
    if not image:
      th = entry.find(f'{{{MEDIA_NS}}}thumbnail')
      if th is not None:
        image = th.get('url','')

    raw.append((title, link, pub, image))

  return build_items(raw, src)

def build_items(raw, src):
  result = []
  for title, link, pub, image in raw[:20]:
    title = (title or '').strip()
    link  = (link  or '').strip()
    if not title or not link or not link.startswith('http'):
      continue
    # NHKリンク正規化
    link = re.sub(r'https?://www\.nhk\.or\.jp/news/',
                  'https://www3.nhk.or.jp/news/', link)
    result.append({
      'id':      link,
      'title':   title,
      'link':    link,
      'pubDate': pub or '',
      'image':   image or '',
      'source':  src['name'],
      'sid':     src['id'],
    })
  return result

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
all_items = []
seen = set()

for src in SOURCES:
  if src['type'] == 'youtube':
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={src['channel_id']}"
  else:
    url = src['url']

  print(f"\n=== {src['name']} ({src['id']}) ===")
  print(f"  {url}")

  data = fetch(url)
  if not data:
    print(f"  → 失敗")
    continue
  print(f"  → 取得: {len(data):,} bytes")

  if src['type'] == 'youtube':
    items = parse_youtube(data, src)
  else:
    items = parse_rss(data, src)

  new = [i for i in items if i['link'] not in seen]
  for i in new:
    seen.add(i['link'])
  all_items.extend(new)
  print(f"  → {len(new)}件追加")
  if new:
    print(f"  例: {new[0]['title'][:50]}")

# 日付降順ソート
all_items.sort(key=lambda i: i['pubDate'], reverse=True)

output = {
  'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'items':   all_items,
}
with open('data.json', 'w', encoding='utf-8') as f:
  json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n=== 完了: 合計 {len(all_items)} 件 ===")
