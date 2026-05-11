"""
MyNews RSS フェッチスクリプト - 完全デバッグ版
GitHub Actions で実行される
"""
import sys, urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
import json, datetime, re, time, subprocess, os

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# feedparser をインストール（より確実なRSSパース）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("=== feedparser インストール ===")
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', 'feedparser', '-q'],
    capture_output=True, text=True
)
print(result.stdout or "OK")
if result.returncode != 0:
    print("WARNING:", result.stderr)

import feedparser
print(f"feedparser version: {feedparser.__version__}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ソース定義
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RSS_SOURCES = [
    # NHK（カテゴリ別・全部試す）
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat0.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat1.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat3.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat4.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat5.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat6.xml"},
    {"id":"s1","name":"NHK ニュース","url":"https://www.nhk.or.jp/rss/news/cat7.xml"},
    # NHK 新URL（NHK ONE移行後）
    {"id":"s1","name":"NHK ニュース","url":"https://news.web.nhk/n-data/conf/na/rss/cat0.xml"},
    # 朝日新聞
    {"id":"s2","name":"朝日新聞","url":"https://www.asahi.com/rss/asahi/newsheadlines.rdf"},
    # 毎日新聞
    {"id":"s7","name":"毎日新聞","url":"https://mainichi.jp/rss/etc/mainichi-flash.rss"},
    # 産経ニュース
    {"id":"s8","name":"産経ニュース","url":"https://www.sankei.com/rss/news/flash/today/newsflash-story.rss"},
]

YOUTUBE_SOURCES = [
    {"id":"s4","name":"テレ朝NEWS",          "channel_id":"UCivjgV3f4b5kBFj-4WExXAQ"},
    {"id":"s5","name":"TBS NEWS DIG",         "channel_id":"UC6AG81pAkf6Lbi_1VC5NmPA"},
    {"id":"s6","name":"FNNプライムオンライン","channel_id":"UCoQBJMzcwmXrRSHBFAlTsIw"},
    {"id":"s3","name":"日テレNEWS",           "channel_id":"UCuTAXTexrhetbOe3zgskJBQ"},
    {"id":"s10","name":"日本経済新聞",        "channel_id":"UCHL12woHGeiqAqLrK-pJe7g"},
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# User-Agent リスト（複数試す）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Feedfetcher-Google; (+http://www.google.com/feedfetcher.html; 1 subscribers; feed-id=1)',
    'python-feedparser/6.0',
]

def fetch_raw(url):
    """生データをfetch。複数UAを試し、詳細ログを出力"""
    for i, ua in enumerate(USER_AGENTS):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': ua,
                'Accept': 'application/rss+xml,application/rdf+xml,application/atom+xml,application/xml,text/xml,*/*',
                'Accept-Language': 'ja,en;q=0.9',
                'Cache-Control': 'no-cache',
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                code = r.getcode()
                data = r.read()
            print(f"  [UA{i+1}] HTTP {code}, {len(data):,} bytes")
            if len(data) > 100:
                return data
            print(f"  [UA{i+1}] レスポンスが小さすぎる: {data[:100]}")
        except urllib.error.HTTPError as e:
            print(f"  [UA{i+1}] HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            print(f"  [UA{i+1}] URL Error: {e.reason}")
        except Exception as e:
            print(f"  [UA{i+1}] Error: {type(e).__name__}: {e}")
        time.sleep(0.5)
    return None

def parse_with_feedparser(url, name, sid):
    """feedparserで直接パース（最も確実）"""
    try:
        # feedparserは内部でfetchするのでUAを設定
        feedparser.USER_AGENT = USER_AGENTS[0]
        d = feedparser.parse(url)
        
        bozo = d.get('bozo', False)
        status = d.get('status', 'N/A')
        entries = d.get('entries', [])
        
        print(f"  feedparser: status={status}, entries={len(entries)}, bozo={bozo}")
        if bozo:
            print(f"  bozo_exception: {d.get('bozo_exception','')}")
        
        if not entries:
            # rawデータを見る
            raw = fetch_raw(url)
            if raw:
                print(f"  rawデータ先頭: {raw[:200]}")
            return []
        
        results = []
        for entry in entries:
            title = entry.get('title','').strip()
            link  = entry.get('link','').strip()
            
            # pubDate
            pub = ''
            if entry.get('published'):
                pub = entry['published']
            elif entry.get('updated'):
                pub = entry['updated']
            
            # サムネイル
            image = ''
            # media_thumbnail
            thumbs = entry.get('media_thumbnail', [])
            if thumbs:
                image = thumbs[0].get('url','')
            # enclosures
            if not image:
                for enc in entry.get('enclosures', []):
                    if enc.get('type','').startswith('image'):
                        image = enc.get('url','')
                        break
            # summary内のimg
            if not image:
                summary = entry.get('summary','')
                m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary, re.I)
                if m:
                    image = m.group(1)
            
            if not title or not link or not link.startswith('http'):
                continue
            
            # NHKリンク正規化
            link = re.sub(r'https?://www\.nhk\.or\.jp/news/',
                          'https://www3.nhk.or.jp/news/', link)
            
            results.append({
                'id': link, 'title': title, 'link': link,
                'pubDate': pub, 'image': image,
                'source': name, 'sid': sid,
            })
        return results
    except Exception as e:
        print(f"  feedparser例外: {type(e).__name__}: {e}")
        return []

def parse_youtube_atom(data, name, sid):
    """YouTube AtomフィードをET直接パース"""
    ATOM  = 'http://www.w3.org/2005/Atom'
    MEDIA = 'http://search.yahoo.com/mrss/'
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"  XML ParseError: {e}")
        print(f"  先頭200bytes: {data[:200]}")
        return []
    
    results = []
    entries = root.findall(f'{{{ATOM}}}entry')
    print(f"  Atom entries: {len(entries)}")
    
    for entry in entries:
        # title
        t = entry.find(f'{{{ATOM}}}title')
        title = t.text.strip() if t is not None and t.text else ''
        
        # link
        l = entry.find(f'{{{ATOM}}}link')
        link = l.get('href','') if l is not None else ''
        
        # published
        p = entry.find(f'{{{ATOM}}}published')
        pub = p.text.strip() if p is not None and p.text else ''
        
        # thumbnail: media:group/media:thumbnail
        image = ''
        group = entry.find(f'{{{MEDIA}}}group')
        if group is not None:
            th = group.find(f'{{{MEDIA}}}thumbnail')
            if th is not None:
                image = th.get('url','')
        if not image:
            th = entry.find(f'.//{{{MEDIA}}}thumbnail')
            if th is not None:
                image = th.get('url','')
        
        if title and link and link.startswith('http'):
            results.append({
                'id': link, 'title': title, 'link': link,
                'pubDate': pub, 'image': image,
                'source': name, 'sid': sid,
            })
    return results

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
all_items = []
seen = set()

print("\n" + "="*60)
print("RSS ソース処理")
print("="*60)

for src in RSS_SOURCES:
    print(f"\n--- {src['name']} ({src['id']}) ---")
    print(f"URL: {src['url']}")
    
    items = parse_with_feedparser(src['url'], src['name'], src['id'])
    new = [i for i in items if i['link'] not in seen]
    for i in new:
        seen.add(i['link'])
    all_items.extend(new)
    print(f"結果: {len(new)}件追加（重複除去後）")
    if new:
        print(f"  先頭: {new[0]['title'][:60]}")

print("\n" + "="*60)
print("YouTube ソース処理")
print("="*60)

for src in YOUTUBE_SOURCES:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={src['channel_id']}"
    print(f"\n--- {src['name']} ({src['id']}) ---")
    print(f"URL: {url}")
    
    data = fetch_raw(url)
    if not data:
        print("  → 全UA失敗")
        continue
    
    items = parse_youtube_atom(data, src['name'], src['id'])
    new = [i for i in items if i['link'] not in seen]
    for i in new:
        seen.add(i['link'])
    all_items.extend(new)
    print(f"結果: {len(new)}件追加")
    if new:
        print(f"  先頭: {new[0]['title'][:60]}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ソート & 保存
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
all_items.sort(key=lambda i: i.get('pubDate',''), reverse=True)

output = {
    'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'items':   all_items,
}
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n" + "="*60)
print(f"完了: 合計 {len(all_items)} 件")
sid_count = {}
for i in all_items:
    sid_count[i['source']] = sid_count.get(i['source'], 0) + 1
for name, count in sorted(sid_count.items()):
    print(f"  {name}: {count}件")
print("="*60)
