from core.parser import fetch_new_episodes
from core.audio_processor import download_episode
from core.ai_processor import summarize_groq, summarize_huggingface, transcribe_audio
from utils.image_creator import create_episode_image
import time

def create_summary(transcript: str, episode_title: str) -> str:
    summary = summarize_groq(transcript, episode_title)
    if not summary:
        summary = summarize_huggingface(transcript, episode_title)

    return summary

def main_pipeline():
    new_episodes = fetch_new_episodes()

    for episode in new_episodes:
        print(f"Обработка: {episode['title']}")
        audio_file = download_episode(audio_url=episode['audio_url'], episode_title=episode['title'])
        transcript = transcribe_audio(audio_path=audio_file)

        summary = create_summary(transcript=transcript, episode_title=episode['title'])

        if summary:
            print(summary)
        else:
            print("Failed to summarize episode")
        time.sleep(3600)

main_pipeline()