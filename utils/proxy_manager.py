import random
import requests
from typing import Optional, List
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class ProxyManager:
    def __init__(self, proxy_file: str = "./data/proxies.txt"):
        self.proxy_file = proxy_file
        self.proxies: List[str] = []
        self.working_proxies: List[str] = []
        self.failed_proxies: set = set()
        self.current_proxy: Optional[str] = None
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from file"""
        try:
            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.proxies)} proxies from {self.proxy_file}")
        except FileNotFoundError:
            logger.warning(f"Proxy file {self.proxy_file} not found")
            self.proxies = []
    
    def test_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """Test if proxy is working"""
        try:
            proxies = {
                'http': proxy,
                'https': proxy
            }
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if response.status_code == 200:
                logger.debug(f"✓ Proxy working: {proxy}")
                return True
        except Exception as e:
            logger.debug(f"✗ Proxy failed: {proxy} - {type(e).__name__}")
        return False
    
    def find_working_proxies(self, max_test: int = 10, parallel: bool = False):
        """Find working proxies from the list"""
        logger.info(f"Testing up to {max_test} proxies...")
        
        tested = 0
        for proxy in self.proxies:
            if tested >= max_test:
                break
            
            if proxy in self.failed_proxies:
                continue
            
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
                logger.info(f"✓ Found working proxy: {proxy}")
            else:
                self.failed_proxies.add(proxy)
            
            tested += 1
            time.sleep(0.5)  # Небольшая задержка между тестами
        
        logger.info(f"Found {len(self.working_proxies)} working proxies out of {tested} tested")
        return len(self.working_proxies) > 0
    
    def get_proxy(self) -> Optional[dict]:
        """Get a random working proxy"""
        if not self.working_proxies:
            logger.warning("No working proxies available, trying to find some...")
            if not self.find_working_proxies(max_test=20):
                logger.error("Could not find any working proxies")
                return None
        
        # Выбираем случайный прокси из рабочих
        self.current_proxy = random.choice(self.working_proxies)
        logger.debug(f"Using proxy: {self.current_proxy}")
        
        return {
            'http': self.current_proxy,
            'https': self.current_proxy
        }
    
    def mark_proxy_as_failed(self, proxy: str):
        """Mark proxy as failed and remove from working list"""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
            self.failed_proxies.add(proxy)
            logger.warning(f"Marked proxy as failed: {proxy}")
            logger.info(f"Remaining working proxies: {len(self.working_proxies)}")
    
    def get_next_proxy(self) -> Optional[dict]:
        """Get next proxy (marks current as failed and gets new one)"""
        if self.current_proxy:
            self.mark_proxy_as_failed(self.current_proxy)
        return self.get_proxy()


# Глобальный экземпляр менеджера прокси
proxy_manager = ProxyManager()