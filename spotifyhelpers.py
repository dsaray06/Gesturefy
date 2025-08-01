import requests
from io import BytesIO
from colorthief import ColorThief
import colorsys

def mild_tint_from_rgb(rgb):
    # Convert RGB (0-255) to HLS (note: HLS in colorsys, lightness is middle)
    r, g, b = [x/255 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # Reduce saturation and lightness for mild effect
    mild_s = 0.3  # low saturation
    mild_l = 0.1  # dark lightness
    
    # Build new RGB from mild hue, low saturation and lightness
    r2, g2, b2 = colorsys.hls_to_rgb(h, mild_l, mild_s)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)


def get_current_album_art_url(sp):
    current_playback = sp.current_playback()
    if current_playback and current_playback['item']:
        album_images = current_playback['item']['album']['images']
        if album_images:
            return album_images[0]['url']
    return None

def get_dominant_color_from_url(image_url):
    response = requests.get(image_url)
    img_bytes = BytesIO(response.content)
    color_thief = ColorThief(img_bytes)
    dominant_color = color_thief.get_color(quality=1)  # RGB tuple
    return dominant_color

def rgb_to_hex(rgb_tuple):
    return '#%02x%02x%02x' % rgb_tuple
