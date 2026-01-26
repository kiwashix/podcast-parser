from PIL import Image, ImageDraw, ImageFont

def create_episode_image(episode_title: str, podcast_name: str) -> any:
    img = Image.new('RGB', (1200, 630), color='#1a1a2e')
    draw = ImageDraw.Draw(img)

    font_title = ImageFont.truetype("./fonts/Inter-Bold.ttf")
    draw.text((50, 200), episode_title[:50], fill="#ffffff", font=font_title)

    font_podcast = ImageFont.truetype("./fonts/Inter-Regular.ttf")
    draw.text((50, 400), f"Подкаст: {podcast_name}", fill="#16c79a", font=font_podcast)
    
    output = f"images/{episode_title[:20]}.jpg"
    img.save(output)
    return output

create_episode_image("Is AI gonna really take us to the Moon?", "Bullshit Generator")