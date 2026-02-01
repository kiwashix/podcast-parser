from core.parser import fetch_new_episodes
from core.audio_processor import download_episode
from core.ai_processor import summarize_groq, summarize_huggingface, transcribe_audio
from utils.image_creator import create_episode_image
from data.database import DB
import time

def create_summary(transcript: str, episode_title: str) -> str:
    summary = summarize_groq(transcript, episode_title)
    if not summary:
        summary = summarize_huggingface(transcript, episode_title)

    return summary

def main_pipeline():
    episodes = DB.get_random()
    if not episodes:
        print("Нет доступных неп опубликованных эпизодов")
        return
    
    episode = episodes[0]
    id = episode[0]
    podcast_id = episode[1]
    title = episode[2]
    category = episode[3]
    audio_url = episode[5]
    
    print(f"Обработка {title}")
    audio_file = download_episode(audio_url=audio_url, episode_title=title)
    transcript = transcribe_audio(audio_path=audio_file)
    summary = create_summary(transcript=transcript, episode_title=title)
    print(summary)
    # for episode in new_episodes:
    #     print(f"Обработка: {episode['title']}")
    #     audio_file = download_episode(audio_url=episode['audio_url'], episode_title=episode['title'])
    #     transcript = transcribe_audio(audio_path=audio_file)

    #     summary = create_summary(transcript=transcript, episode_title=episode['title'])

    #     if summary:
    #         print(summary)
    #     else:
    #         print("Failed to summarize episode")
    #     time.sleep(3600)

main_pipeline()