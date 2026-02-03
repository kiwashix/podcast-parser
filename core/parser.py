# parser.py
import requests
import feedparser
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from data.database import DB
from utils.logger import get_logger, log_execution_time

# Get module logger
logger = get_logger(__name__)

# Отключаем предупреждения SSL (только для разработки!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_session():
    """Create requests session with retry logic and browser-like headers"""
    logger.debug("Creating HTTP session with retry strategy")
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
    
    logger.debug("HTTP session created successfully")
    return session

def load_podcasts_feeds():
    """Load podcasts.json data"""
    logger.debug("Loading podcasts feeds from podcasts.json")
    try:
        with open('./data/podcasts.json', 'r') as f:
            feeds = json.load(f)
        logger.info(f"Loaded {len(feeds)} podcast categories")
        return feeds
    except FileNotFoundError:
        logger.error("podcasts.json file not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in podcasts.json: {e}")
        raise

@log_execution_time(logger, "fetch new episodes")
def fetch_new_episodes():
    """Fetch new episodes from RSS feeds"""
    logger.info("Starting to fetch new episodes from RSS feeds")
    feeds = load_podcasts_feeds()
    new_episodes = []
    session = create_session()
    
    for category, podcasts in feeds.items():
        logger.info(f"Processing category: {category}")
        
        for podcast_id, podcast_data in podcasts.items():
            podcast_name = podcast_data['name']
            logger.info(f"Fetching podcast: {podcast_name}", extra={
                "podcast_id": podcast_id,
                "category": category
            })
            
            try:
                # Пауза между запросами (важно!)
                time.sleep(3)
                
                # Fetch RSS
                logger.debug(f"Requesting RSS feed: {podcast_data['rss']}")
                response = session.get(
                    podcast_data['rss'], 
                    verify=False,  # В продакшене убрать!
                    timeout=15
                )
                response.raise_for_status()
                logger.debug(f"RSS feed response: {response.status_code}")
                
                # Parse feed
                feed = feedparser.parse(response.content)
                
                # Проверка на ошибки парсинга
                if feed.bozo:
                    logger.warning(f"Feed parsing warning for {podcast_name}: {feed.bozo_exception}")
                    continue
                
                # Проверка наличия эпизодов
                if not feed.entries:
                    logger.warning(f"No entries found in feed: {podcast_name}")
                    continue
                
                logger.info(f"Found {len(feed.entries)} episodes in {podcast_name}")
                
                # Обработка первых 10 эпизодов
                new_count = 0
                for entry in feed.entries[:10]:
                    episode = {
                        'podcast_id': podcast_id,
                        'podcast_name': podcast_name,
                        'category': category,
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
                        DB.save_episode(podcast_id=podcast_id, podcast_name=podcast_name, podcast_title=episode['title'],
                                        category=episode['category'], published=False,
                                        audio_url=episode['audio_url'], duration=episode['duration'])
                        new_count += 1
                        logger.debug(f"New episode saved: {entry.title[:60]}...")
                
                logger.info(f"Added {new_count} new episodes from {podcast_name}")
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP Error fetching {podcast_name}: {e}", exc_info=True)
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection Error fetching {podcast_name}: {e}", exc_info=True)
            except requests.exceptions.Timeout:
                logger.error(f"Timeout fetching {podcast_name}")
            except Exception as e:
                logger.error(f"Unexpected error fetching {podcast_name}: {type(e).__name__}: {e}", exc_info=True)
    
    logger.info(f"Total new episodes fetched: {len(new_episodes)}")
    return new_episodes