from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_gradient(width, height, start_color, end_color):
    """Создает градиентный фон."""
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def create_episode_image(episode_title: str, podcast_name: str) -> str:
    width, height = 1200, 630
    # Градиент от #1a1a2e к #2a2a4e для глубины
    img = create_gradient(width, height, '#001233', '#001845')
    draw = ImageDraw.Draw(img)

    # Шрифты (предполагаем, что они есть)
    font_title = ImageFont.truetype("./fonts/Inter-Bold.ttf", 72)
    font_podcast = ImageFont.truetype("./fonts/Inter-Regular.ttf", 48)
    font_small = ImageFont.truetype("./fonts/Inter-Regular.ttf", 24)  # Для "Эпизод"

    # Обертывание заголовка: макс. 30 символов на строку
    wrapped_title = textwrap.wrap(episode_title, width=30)
    y_pos = 150  # Начальная позиция для заголовка

    # Рисуем заголовок по центру
    for line in wrapped_title:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) / 2, y_pos), line, fill="#edf6f9", font=font_title)
        y_pos += 80  # Отступ между строками

    # "Подкаст:" по центру ниже
    podcast_text = podcast_name
    bbox = draw.textbbox((0, 0), podcast_text, font=font_podcast)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, y_pos + 50), podcast_text, fill="#0466c8", font=font_podcast)

    # Опционально: добавьте "Эпизод" сверху
    small_text = "Эпизод"
    bbox = draw.textbbox((0, 0), small_text, font=font_small)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 50), small_text, fill="#0466c8", font=font_small)

    # Сохранение
    output = f"images/{episode_title[:20].replace('?', '')}.png"  # Убрал "?" для имени файла
    img.save(output)
    return output

# Пример вызова
create_episode_image("Is AI gonna really take us to the Moon?", "Bullshit Generator")