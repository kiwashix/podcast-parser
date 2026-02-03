import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()


class Config:
    # Прокси настройки
    USE_PROXY = os.getenv('USE_PROXY', 'true').lower() == 'true'  # По умолчанию включено
    PROXY_FILE = os.getenv('PROXY_FILE', 'proxies.txt')
    
    # Опциональные фиксированные прокси (если не хотите ротацию)
    PROXY_HTTP = os.getenv('PROXY_HTTP', None)
    PROXY_HTTPS = os.getenv('PROXY_HTTPS', None)
    
    # Тестировать прокси при старте
    TEST_PROXIES_ON_STARTUP = os.getenv('TEST_PROXIES_ON_STARTUP', 'true').lower() == 'true'
    
    # Максимальное количество прокси для тестирования при старте
    MAX_PROXIES_TO_TEST = int(os.getenv('MAX_PROXIES_TO_TEST', '20'))
    
    @staticmethod
    def get_proxies() -> Optional[dict]:
        """Get proxy configuration (deprecated - use ProxyManager instead)"""
        if not Config.USE_PROXY:
            return None
        
        proxies = {}
        if Config.PROXY_HTTP:
            proxies['http'] = Config.PROXY_HTTP
        if Config.PROXY_HTTPS:
            proxies['https'] = Config.PROXY_HTTPS
        
        return proxies if proxies else None