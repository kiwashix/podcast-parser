import requests

def download_episode(audio_url: str, episode_title: str) -> str:
    """
    Downloads audiofile of episode by url
    
    :param audio_url: url leading to .mp3 file
    :type audio_url: str
    :param episode_id: episode id
    :type episode_id: str
    :return: returns filename
    :rtype: str
    """

    response = requests.get(audio_url, stream=True)
    filename = f"episodes/{episode_title[:20]}.mp3"

    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return filename