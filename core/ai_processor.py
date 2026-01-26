import os
import requests
import whisper
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_TOKEN = os.getenv("GROQ_TOKEN")

def transcribe_audio(audio_path: str) -> str:
    """"
        Transcribes EN audio
    """
    model = whisper.load_model('base.en')

    result = model.transcribe(
        audio_path,
        word_timestamps=True
    )

    return result['text']

def summarize_huggingface(transcript: str, episode_title: str) -> str:
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
    }

    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        return None

    prompt = f"""Ты — редактор подкаст-дайджестов на русском языке.
            Эпизод: {episode_title}
            Транскрипт:
            {transcript[:8000]}
            Задача:
            1. Напиши краткое содержание (3-4 абзаца) на русском языке
            2. Выдели 5-7 ключевых инсайтов (bullet points)
            3. Добавь 2-3 самые интересные цитаты из эпизода
            4. Напиши, кому будет полезен этот эпизод (1-2 предложения)
            Формат ответа должен быть удобен для публикации в Telegram.
        """

    response = query({
        "messages": [
            {"role": "system", "content": "Ты эксперт по созданию дайджестов подкастов."},
            {"role": "user", "content": prompt}
        ],
        "model": "openai/gpt-oss-120b:cheapest",
        "max_tokens": 1500
    })

    if not response:
        return None
    return response["choices"][0]["message"]["content"]

def summarize_groq(transcript: str, episode_title: str) -> str:
    prompt = f"""Ты — редактор подкаст-дайджестов на русском языке.
            Эпизод: {episode_title}
            Транскрипт:
            {transcript[:8000]}
            Задача:
            1. Напиши краткое содержание (3-4 абзаца) на русском языке
            2. Выдели 5-7 ключевых инсайтов (bullet points)
            3. Добавь 2-3 самые интересные цитаты из эпизода
            4. Напиши, кому будет полезен этот эпизод (1-2 предложения)
            Формат ответа должен быть удобен для публикации в Telegram.
        """

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-oss-120b", 
            "messages": [
                {
                    "role": "system",
                    "content": "Ты эксперт по созданию кратких содержаний подкастов на русском языке."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
    )

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return None