from core.parser import fetch_new_episodes
from core.audio_processor import download_episode
from core.ai_processor import summarize_groq, summarize_huggingface, transcribe_audio
from utils.image_creator import create_episode_image
from data.database import DB
from utils.logger import init_logging, get_logger, log_execution_time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import Config
from utils.proxy_manager import proxy_manager
import time
import signal
import sys
from typing import Optional
from datetime import datetime

# Initialize logging at application startup
init_logging()

# Get module logger
logger = get_logger(__name__)


@log_execution_time(logger, "summary creation")
def create_summary(transcript: str, episode_title: str) -> str:
    summary = summarize_groq(transcript, episode_title)
    if not summary:
        summary = summarize_huggingface(transcript, episode_title)

    return summary


def download_with_retry(audio_url: str, episode_title: str, max_retries: int = 3) -> Optional[str]:
    """Download episode with retry logic and exponential backoff"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Download attempt {attempt + 1}/{max_retries} for: {episode_title}")
            audio_file = download_episode(audio_url=audio_url, episode_title=episode_title)
            if audio_file:
                logger.info(f"✓ Successfully downloaded on attempt {attempt + 1}")
                return audio_file
        except Exception as e:
            logger.warning(f"✗ Download attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"✗ All {max_retries} download attempts failed")
    return None


def mark_episode_as_failed(episode_id: int, reason: str):
    """Mark episode as failed but not published, so it can be retried later"""
    logger.warning(f"Episode {episode_id} marked for retry. Reason: {reason}")


@log_execution_time(logger, "episode fetching")
def fetch_episodes_job():
    """Wrapper for fetch_new_episodes with logging"""
    logger.info("=" * 60)
    logger.info(f"Starting episode fetch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        result = fetch_new_episodes()
        logger.info("=" * 60)
        logger.info(f"✓ Episode fetch completed successfully")
        logger.info("=" * 60)
        return result
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ Episode fetch failed: {e}", exc_info=True)
        logger.error("=" * 60)


@log_execution_time(logger, "main pipeline")
def main_pipeline():
    logger.info("=" * 60)
    logger.info(f"Starting main pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        episodes = DB.get_random()
        if not episodes:
            logger.warning("⚠ No unpublished episodes available")
            return
        
        episode = episodes[0]
        
        # Безопасное извлечение с fallback значениями
        episode_id = episode.get('id')
        podcast_id = episode.get('podcast_id', 'unknown')
        podcast_name = episode.get('podcast_name', 'Unknown Podcast')
        podcast_title = episode.get('podcast_title', 'Untitled')
        category = episode.get('category', 'General')
        audio_url = episode.get('audio_url')
        duration = episode.get('duration', 'Unknown')
        
        # Обязательные поля
        if not episode_id:
            logger.error("✗ Episode missing required field: id")
            return
        
        if not audio_url:
            logger.error(f"✗ Episode {episode_id} missing audio_url")
            return
        
        logger.info(f"📝 Processing episode: '{podcast_title}'")
        logger.info(f"   Podcast: {podcast_name}")
        logger.info(f"   Category: {category}")
        logger.info(f"   Duration: {duration}")
        logger.info(f"   Episode ID: {episode_id}")
        
        # Проверка валидности URL
        if not isinstance(audio_url, str):
            logger.error(f"✗ Invalid audio_url type: {type(audio_url)}")
            return
        
        if not audio_url.startswith(('http://', 'https://')):
            logger.error(f"✗ audio_url doesn't start with http(s): {audio_url}")
            return
        
        logger.info(f"⬇ Downloading from: {audio_url[:80]}...")
        
        # Скачивание с retry
        audio_file = download_with_retry(audio_url, podcast_title, max_retries=3)
        
        if not audio_file:
            error_msg = f"Failed to download episode after retries: {podcast_title}"
            logger.error(f"✗ {error_msg}")
            mark_episode_as_failed(episode_id, "download_timeout")
            return
        
        logger.info(f"🎙 Transcribing audio file: {audio_file}")
        transcript = transcribe_audio(audio_path=audio_file)
        
        if not transcript:
            logger.error(f"✗ Failed to transcribe episode: {podcast_title}")
            mark_episode_as_failed(episode_id, "transcription_failed")
            return
        
        logger.info(f"✍ Creating summary for: {podcast_title}")
        summary = create_summary(transcript=transcript, episode_title=podcast_title)
        
        if not summary:
            logger.error(f"✗ Failed to create summary for: {podcast_title}")
            mark_episode_as_failed(episode_id, "summarization_failed")
            return
        
        # Отмечаем эпизод как опубликованный
        DB.mark_as_used(episode_id)
        
        logger.info("=" * 60)
        logger.info(f"✓ SUCCESS: Episode processed and published")
        logger.info(f"  Title: {podcast_title}")
        logger.info(f"  Summary length: {len(summary)} chars")
        logger.info(f"  Transcript length: {len(transcript)} chars")
        logger.info("=" * 60)
        
        return {
            "episode": episode,
            "summary": summary,
            "transcript": transcript,
            "audio_file": audio_file
        }
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ Pipeline execution failed: {e}", exc_info=True)
        logger.error("=" * 60)


def graceful_shutdown(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM"""
    logger.info("=" * 60)
    logger.info("Received shutdown signal, stopping scheduler...")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped gracefully")
    logger.info("=" * 60)
    sys.exit(0)


# Глобальная переменная для scheduler
scheduler = None


if __name__ == "__main__":
    try:
        # Инициализация прокси при старте
        if Config.USE_PROXY and Config.TEST_PROXIES_ON_STARTUP:
            logger.info("=" * 60)
            logger.info("Testing proxies on startup...")
            logger.info("=" * 60)
            proxy_manager.find_working_proxies(max_test=Config.MAX_PROXIES_TO_TEST)
            logger.info("")

        scheduler = BackgroundScheduler()
        
        # Удаляем все существующие задачи
        scheduler.remove_all_jobs()
        
        # Job 1: Парсинг новых эпизодов (8:00, 14:00, 20:00)
        scheduler.add_job(
            fetch_episodes_job,
            CronTrigger(hour='8,14,20', minute=0),
            id='daily_fetch',
            name='Daily Episode Fetching',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=300  # 5 минут grace period
        )
        
        # Job 2: Обработка эпизодов (9:00, 15:00, 21:00)
        scheduler.add_job(
            main_pipeline,
            CronTrigger(hour='9,15,21', minute=0),
            id='daily_pipeline',
            name='Daily Episode Processing',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600  # 1 час grace period
        )
        
        # Настройка graceful shutdown
        signal.signal(signal.SIGINT, graceful_shutdown)
        signal.signal(signal.SIGTERM, graceful_shutdown)
        
        scheduler.start()
        
        logger.info("")
        logger.info("╔" + "═" * 58 + "╗")
        logger.info("║" + " " * 12 + "PODCAST BOT SCHEDULER STARTED" + " " * 17 + "║")
        logger.info("╚" + "═" * 58 + "╝")
        logger.info("")
        
        # Логируем все запланированные задачи
        jobs = scheduler.get_jobs()
        logger.info(f"📅 Total jobs scheduled: {len(jobs)}")
        logger.info("")
        for job in jobs:
            logger.info(f"  📌 Job ID: {job.id}")
            logger.info(f"     Name: {job.name}")
            logger.info(f"     Next run: {job.next_run_time}")
            logger.info(f"     Schedule: {job.trigger}")
            logger.info("")
        
        logger.info("=" * 60)
        logger.info("🚀 Application is running")
        logger.info("⏰ Schedule:")
        logger.info("   📥 Fetch episodes: 08:00, 14:00, 20:00")
        logger.info("   ⚙️  Process episodes: 09:00, 15:00, 21:00")
        logger.info("🛑 Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")
        
        # Опционально: запустить сразу при старте для тестирования
        logger.info("▶ Running initial test execution...")
        fetch_episodes_job()
        main_pipeline()
        
        # Держим приложение активным
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("\n⚠ Received keyboard interrupt")
        graceful_shutdown(None, None)
    except Exception as e:
        logger.critical("=" * 60)
        logger.critical(f"💥 Application crashed: {e}", exc_info=True)
        logger.critical("=" * 60)
        raise