import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from core.config import Config
from utils.proxy_manager import proxy_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def download_episode(audio_url: str, episode_title: str, timeout: int = 90, max_proxy_retries: int = 3) -> str:
    """
    Download episode with proxy rotation support
    """
    for proxy_attempt in range(max_proxy_retries):
        # Получаем прокси (если включено)
        proxies = None
        if Config.USE_PROXY:
            proxies = proxy_manager.get_proxy()
            if proxies:
                proxy_host = list(proxies.values())[0]
                logger.info(f"Attempt {proxy_attempt + 1}/{max_proxy_retries} with proxy: {proxy_host}")
            else:
                logger.warning("No working proxies available, downloading without proxy")
        
        # Настройка session
        session = requests.Session()
        retry_strategy = Retry(
            total=2,  # Меньше retry для каждого прокси
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            response = session.get(
                audio_url,
                stream=True,
                timeout=(30, 90),  # (connect timeout, read timeout)
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                proxies=proxies
            )
            response.raise_for_status()
            
            # Сохранение файла
            filename = f"downloads/{episode_title[:50].replace('/', '_').replace(':', '_')}.mp3"
            os.makedirs("downloads", exist_ok=True)
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            logger.info(f"Starting download: {total_size / (1024*1024):.2f} MB")
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and downloaded % (1024 * 1024 * 10) < 8192:  # Каждые ~10MB
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"✓ Successfully downloaded {downloaded / (1024*1024):.2f} MB")
            session.close()
            return filename
            
        except (requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError, 
                requests.exceptions.ProxyError) as e:
            
            error_type = type(e).__name__
            logger.warning(f"✗ Download failed with {error_type}: {e}")
            
            # Если используем прокси и он не сработал, пробуем следующий
            if Config.USE_PROXY and proxies and proxy_attempt < max_proxy_retries - 1:
                if proxy_manager.current_proxy:
                    proxy_manager.mark_proxy_as_failed(proxy_manager.current_proxy)
                logger.info(f"Switching to next proxy...")
                continue
            else:
                raise Exception(f"Download failed after {proxy_attempt + 1} attempts: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise
        
        finally:
            session.close()
    
    raise Exception(f"Failed to download after {max_proxy_retries} proxy attempts")