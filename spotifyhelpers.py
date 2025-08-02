import requests
from io import BytesIO
from colorthief import ColorThief
import colorsys

def mild_tint_from_rgb(rgb, sat_scale=0.3, light_scale=0.4):
    """
    rgb: (r,g,b) 0–255
    sat_scale: how much to damp the saturation (smaller → gentler tint)
    light_scale: how much closer to white you want to go
    """
    r, g, b = rgb
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)

    # in Dark mode we might want a stronger tint;
    # in Light we usually want a more washed-out pastel
    mild_l = l + (1 - l) * light_scale
    mild_s = s * sat_scale

    r2, g2, b2 = colorsys.hls_to_rgb(h, mild_l, mild_s)
    return (int(r2*255), int(g2*255), int(b2*255))


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

# in spotifyhelpers.py
def blend_tint(rgb, bg_rgb, alpha=0.1):
    """Return a hex color α-blend of rgb over bg_rgb."""
    blended = tuple(int(alpha*c + (1-alpha)*b) for c, b in zip(rgb, bg_rgb))
    return '#{:02x}{:02x}{:02x}'.format(*blended)

