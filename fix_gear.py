# Script to fix the settings gear icon by making the background color the same as the topbar 
# color, making it appear transparent
from PIL import Image

img = Image.open("assets/settings_gear.png").convert("RGBA")
background_color = (44, 44, 44, 255)  

new_img = Image.new("RGBA", img.size, background_color)
new_img.paste(img, (0, 0), img)  

new_img.save("assets/settings_gear_transparent.png")
