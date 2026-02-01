# parser.py
import requests
import feedparser
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from data.database import DB

# Отключаем предупреждения SSL (только для разработки!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    """Create requests session with retry logic and browser-like headers"""
    session = requests.Session()
    
    # Retry стратегия
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Заголовки как у настоящего браузера
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
    })
    
    return session

def load_podcasts_feeds():
    """Load podcasts.json data"""
    with open('./data/podcasts.json', 'r') as f:
        return json.load(f)

def fetch_new_episodes():
    """Fetch new episodes from RSS feeds"""
    feeds = load_podcasts_feeds()
    new_episodes = []
    session = create_session()
    
    for category, podcasts in feeds.items():
        print(f"\n📂 Category: {category}")
        
        for podcast_id, podcast_data in podcasts.items():
            print(f"\n🎙️  Fetching: {podcast_data['name']}")
            
            try:
                # Пауза между запросами (важно!)
                time.sleep(3)
                
                # Fetch RSS
                response = session.get(
                    podcast_data['rss'], 
                    verify=False,  # В продакшене убрать!
                    timeout=15
                )
                response.raise_for_status()
                
                # Parse feed
                feed = feedparser.parse(response.content)
                
                # Проверка на ошибки парсинга
                if feed.bozo:
                    print(f"   ⚠️  Bozo error: {feed.bozo_exception}")
                    continue
                
                # Проверка наличия эпизодов
                if not feed.entries:
                    print(f"   ❌ No entries found")
                    continue
                
                print(f"   ✅ Success: {len(feed.entries)} episodes")
                
                # Обработка первых 10 эпизодов
                for entry in feed.entries[:10]:
                    episode = {

                        'podcast_id': podcast_id,
                        'podcast_name': podcast_data['name'],
                        'category': podcast_data['category'],
                        'title': entry.get('title', 'No title'),
                        'published': entry.get('published', ''),
                        'description': entry.get('summary', '')[:200],
                        'audio_url': None,
                        'duration': None
                    }
                    
                    # Получение audio URL
                    if hasattr(entry, 'enclosures') and entry.enclosures:
                        episode['audio_url'] = entry.enclosures[0].get('href')
                    elif hasattr(entry, 'links'):
                        for link in entry.links:
                            if 'audio' in link.get('type', ''):
                                episode['audio_url'] = link.get('href')
                                break
                    
                    # Получение длительности
                    if hasattr(entry, 'itunes_duration'):
                        episode['duration'] = entry.itunes_duration
                    
                    if not DB.episode_exist(podcast_id=episode['podcast_id'], podcast_title=episode['title']):

                        new_episodes.append(episode)
                        DB.save_episode(podcast_id=podcast_id, podcast_title=episode['title'],
                                        category=episode['category'], published=False,
                                        audio_url=episode['audio_url'], duration=episode['duration'])
                    
                        # Вывод для дебага
                        print(f"      • {entry.title[:60]}...")
                
            except requests.exceptions.HTTPError as e:
                print(f"   ❌ HTTP Error: {e}")
            except requests.exceptions.ConnectionError as e:
                print(f"   ❌ Connection Error: {e}")
            except requests.exceptions.Timeout:
                print(f"   ❌ Timeout")
            except Exception as e:
                print(f"   ❌ Unexpected error: {type(e).__name__}: {e}")
    
    print(f"\n\n📊 Total episodes fetched: {len(new_episodes)}")
    return new_episodes