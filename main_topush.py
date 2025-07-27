import customtkinter as ctk
from pathlib import Path
import threading
import webbrowser
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotify_integration import GestureControl
from PIL import Image, ImageDraw, ImageTk
import io
from io import BytesIO
import requests
import time
from dotenv import load_dotenv

# Constants
TOKEN_PATH = 'tokens.json'
PORT = 8888

load_dotenv()  # This loads the .env file 

# Grabs Spotify credentials from environment variables
# Ensure you have a .env file with these variables set
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
scope = os.getenv("SPOTIFY_SCOPE")

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        if 'code' in query_components:
            self.server.auth_code = query_components['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authentication successful. You can close this window now.</h1></body></html>")
        else:
            self.send_response(400)
            self.end_headers()

# Helper functions
def start_http_server(server_class=HTTPServer, handler_class=OAuthCallbackHandler):
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    httpd.auth_code = None
    httpd.handle_request()
    return httpd.auth_code

def save_tokens(token_info):
    with open(TOKEN_PATH, 'w') as f:
        json.dump(token_info, f)

def load_tokens():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            return json.load(f)
    return None

def authenticate_spotify(status_callback=None):
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    scope = os.getenv("SPOTIFY_SCOPE")


    sp_oauth = SpotifyOAuth(client_id=client_id,
                            client_secret=client_secret,
                            redirect_uri=redirect_uri,
                            scope=scope,
                            cache_path=TOKEN_PATH,
                            show_dialog=True)

    token_info = load_tokens()

    if not token_info:
        if status_callback:
            status_callback("Opening browser for Spotify login...")
        auth_url = sp_oauth.get_authorize_url()
        webbrowser.open(auth_url)
        auth_code = start_http_server()
        if not auth_code:
            if status_callback:
                status_callback("Failed to get auth code.")
            return None
        token_info = sp_oauth.get_access_token(auth_code)
        save_tokens(token_info)
    else:
        if sp_oauth.is_token_expired(token_info):
            if status_callback:
                status_callback("Refreshing Spotify access token...")
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            save_tokens(token_info)

    return token_info['access_token']

def get_spotify_client(status_callback=None):
    access_token = authenticate_spotify(status_callback)
    if not access_token:
        if status_callback:
            status_callback("Authentication failed.")
        return None
    sp = spotipy.Spotify(auth=access_token)
    return sp

def get_circular_image(image_source, size=(32, 32), upscale=4):
    try:
        if image_source.startswith("http://") or image_source.startswith("https://"):
            response = requests.get(image_source)
            img = Image.open(BytesIO(response.content)).convert("RGBA")
        else:
            img = Image.open(image_source).convert("RGBA")
    except Exception as e:
        print("Error loading image:", e)
        return None

    large_size = (size[0] * upscale, size[1] * upscale)
    img = img.resize(large_size, Image.LANCZOS)

    mask = Image.new('L', large_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, large_size[0], large_size[1]), fill=255)

    img.putalpha(mask)

    img = img.resize(size, Image.LANCZOS)

    return ctk.CTkImage(light_image=img, size=size)

# Main application class
class GesturefyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesturefy")
        self.root.withdraw()

        montserrat_path = Path("fonts/Montserrat-Regular.ttf")
        if not montserrat_path.exists():
            raise FileNotFoundError("Montserrat-Regular.ttf not found in fonts/ folder.")
        self.root.tk.call("font", "create", "Montserrat", "-family", "Montserrat", "-size", "12")
        self.root.tk.call("font", "create", "MontserratBold", "-family", "Montserrat", "-size", "12", "-weight", "bold")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        taskbar_height = 40

        self.root.geometry(f"{screen_width}x{screen_height - taskbar_height}+0+0")
        self.root.resizable(True, True)
        self.root.deiconify()
        self.root.update()
        self.root.state("normal")
        self.root.state("zoomed")

        self.running = False
        self.sp = None
        self.gesture_thread = None
            
    # Make login screen
        self.login_screen = ctk.CTkFrame(root, fg_color="#212121")
        self.login_screen.pack(fill="both", expand=True)

        # Centered container to place login elements
        self.login_container = ctk.CTkFrame(self.login_screen, fg_color="transparent")
        self.login_container.place(relx=0.5, rely=0.45, anchor="center")  # Moved up from 0.4

        # App icon
        self.original_icon_image = Image.open("assets/gesturefy_nobg.png").resize((170, 170))
        self.app_icon = ctk.CTkImage(light_image=self.original_icon_image, size=(170, 170))
        self.app_icon_label = ctk.CTkLabel(self.login_container, image=self.app_icon, text="", anchor="center")
        self.app_icon_label.pack(pady=(0, 0))

        # Wave animation logic
        self.wave_running = False
        def animate_wave_once():
            if self.wave_running:
                return

            self.wave_running = True
            angles = []

            # Build wave pattern: 3 full smooth waves (e.g., [0→+20→0→-20→0] x3)
            for _ in range(3):  # 3 waves
                for angle in range(0, -26, -3):     # 0 to -30
                    angles.append(angle)
                for angle in range(-25, 21, 3):  # -30 to +20
                    angles.append(angle)
                for angle in range(20, 1, -3):    # +20 to 0
                    angles.append(angle)

            def update_wave(i=0):
                if i >= len(angles):
                    self.app_icon = ctk.CTkImage(light_image=self.original_icon_image, size=(170, 170))
                    self.app_icon_label.configure(image=self.app_icon)
                    self.wave_running = False
                    return

                rotated = self.original_icon_image.rotate(angles[i])
                self.app_icon = ctk.CTkImage(light_image=rotated, size=(170, 170))
                self.app_icon_label.configure(image=self.app_icon)
                self.root.after(5, update_wave, i + 1)

            update_wave()
        self.animate_wave_once = animate_wave_once

        # Run wave on startup
        self.root.after(500, self.animate_wave_once)
        
        # Main title
        self.login_label = ctk.CTkLabel(
            self.login_container,
            width=200,
            height=50,
            text="Gesturefy",
            font=ctk.CTkFont(family="Montserrat", size=72, weight="bold"),
            text_color="white"
        )
        self.login_label.pack(pady=(0, 5))

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.login_container,
            text="Control Spotify with gestures",
            font=ctk.CTkFont(family="Montserrat", size=18, weight="normal"),
            text_color="#A0A0A0"
        )
        self.subtitle_label.pack(pady=(0, 20))

        # Login button
        self.login_button = ctk.CTkButton(
            self.login_container,
            width=200,
            height=50,
            text="Log in",
            corner_radius=20,
            command=self.spotify_login,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="white",
            fg_color="#343333",
            hover_color="#545454",
            border_color="#1F1F1F",
            border_width=4
        )
        self.login_button.pack(pady=(0, 10))
        # Trigger wave animation on hover
        self.login_button.bind("<Enter>", lambda e: self.animate_wave_once())

        # Hide login screen initially
        self.login_screen.pack_forget()

    # If not already logged in, show login screen
        if not load_tokens():
            self.login_screen.pack(fill="both", expand=True)
            # Prepare main screen
            self.main_screen = ctk.CTkFrame(root, fg_color="#212121")
            self.main_screen.pack(fill="both", expand=True)
            self.main_screen.pack_forget()  # Hide main screen initially
            login = True
    # Else, just show the main screen
        if not hasattr(self, 'main_screen'):
            self.main_screen = ctk.CTkFrame(root, fg_color="#212121")
            self.main_screen.pack(fill="both", expand=True)
            login = False
            
    # All main screen elements
    
        # Sidebar
        self.sidebar = ctk.CTkFrame(self.main_screen, width=300, corner_radius=18, fg_color="#191414")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Title and subtitle
        self.title_label = ctk.CTkLabel(self.sidebar, text="GESTUREFY", font=ctk.CTkFont(family="Montserrat", size=44, weight="bold"), text_color="white", anchor="center")
        self.title_label.pack(pady=(280, 10))

        self.subtitle = ctk.CTkLabel(self.sidebar, text="Control Spotify\nwith gestures!", font=ctk.CTkFont(family="Montserrat", size=22, weight="bold"), justify="center", text_color="#A0A0A0")
        self.subtitle.pack(pady=5)

        # Start/Stop button
        self.start_stop_btn = ctk.CTkButton(self.sidebar, width=200, height=50, corner_radius= 20, text="Start", command=self.toggle, fg_color="#343333", hover_color="#545454", text_color="white", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"), border_color="#1F1F1F", border_width=4)
        self.start_stop_btn.pack(pady=(40, 10))

        # Top bar for profile and settings
        self.topbar = ctk.CTkFrame(self.main_screen, height=40, corner_radius=15, fg_color="#191414")
        self.topbar.pack(side="top", anchor="ne", padx=20, pady=(10, 0))
        
        # Log output area
        self.log_output = ctk.CTkTextbox(self.main_screen, height=160, wrap="word", corner_radius=15, font=ctk.CTkFont(family="Montserrat", size=12), fg_color="#2c2c2c", text_color="gray")
        self.log_output.pack(side="bottom", fill="x", padx=20, pady=(5,10))
        self.log_output.configure(state="disabled")

        # Center frame for currently playing song info and next up info
        # This frame will hold the main content of the app
        self.center_frame = ctk.CTkFrame(self.main_screen, fg_color="#191414", corner_radius=15, width=800, height=600)
        self.center_frame.pack(side="top", pady=(10,5), padx=20, fill="both", expand=True)

        # Now Playing Frame
        self.now_playing_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.now_playing_frame.pack(fill="x", padx=40, pady=(40, 10))

        # Album Art (left)
        self.album_art_label = ctk.CTkLabel(self.now_playing_frame, text="", image=None, width=100, height=100)
        self.album_art_label.pack(side="left", padx=(0, 20))
        
        # "Currently Playing" label (right)
        self.now_playing_label = ctk.CTkLabel(
            self.now_playing_frame,
            text="Currently Playing",
            font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"),
            text_color="#1DB954"
        )
        self.now_playing_label.pack(anchor="w")

        # Song Title + Artist (right)
        self.song_info_frame = ctk.CTkFrame(self.now_playing_frame, fg_color="transparent")
        self.song_info_frame.pack(side="left", anchor="n")

        self.song_title_label = ctk.CTkLabel(
            self.song_info_frame,
            text="Song Title",
            font=ctk.CTkFont(family="Montserrat", size=40, weight="bold"),
            text_color="white"
        )
        self.song_title_label.pack(anchor="w", pady=(75, 5))

        self.artist_label = ctk.CTkLabel(
            self.song_info_frame,
            text="Artist Name",
            font=ctk.CTkFont(family="Montserrat", size=28),
            text_color="#B3B3B3"
        )
        self.artist_label.pack(anchor="w")

        # --- Progress Bar + Time ---
        self.progress_bar = ctk.CTkProgressBar(self.center_frame, width=600, progress_color="#1DB954")
        self.progress_bar.set(0)
        self.progress_bar.pack(padx=(0, 545), pady=(50, 5))

        self.track_time_label = ctk.CTkLabel(
            self.center_frame,
            text="0:00 / 0:00",
            font=ctk.CTkFont(family="Montserrat", size=12, weight="bold"),
            text_color="white"
        )
        self.track_time_label.pack(padx=(0, 10))

        # --- "Next Up" Song Info ---
        self.next_up_container = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.next_up_container.pack(anchor="e", padx=(0, 20), pady=(40, 20))

        self.next_album_art_label = ctk.CTkLabel(self.next_up_container, text="", image=None, width=75, height=75)
        self.next_album_art_label.pack(side="left", padx=(0, 10))

        self.next_up_info = ctk.CTkFrame(self.next_up_container, fg_color="transparent")
        self.next_up_info.pack(side="left")

        self.next_up_label = ctk.CTkLabel(
            self.next_up_info,
            text="Next Up",
            font=ctk.CTkFont(family="Montserrat", size=14, weight="bold"),
            text_color="#1DB954"
        )
        self.next_up_label.pack(anchor="w")

        self.next_song_title_label = ctk.CTkLabel(
            self.next_up_info,
            text="Next Song Title",
            font=ctk.CTkFont(family="Montserrat", size=14, weight="bold"),
            text_color="white"
        )
        self.next_song_title_label.pack(anchor="w")

        self.next_artist_label = ctk.CTkLabel(
            self.next_up_info,
            text="Next Artist",
            font=ctk.CTkFont(family="Montserrat", size=12),
            text_color="#B3B3B3"
        )
        self.next_artist_label.pack(anchor="w")

        # Logs in if initially displaying main_screen
        if not login:
            self.spotify_login()

    def log(self, msg: str):
        print(msg)
        self.log_output.configure(state="normal")
        self.log_output.insert("end", msg + "\n")
        self.log_output.see("end")
        self.log_output.configure(state="disabled")

    def toggle(self):
        if self.running:
            self.stop_gesture_control()
        else:
            self.start_stop_btn.configure(state="disabled")
            threading.Thread(target=self.start_gesture_control).start()

    def spotify_login(self):
        self.log("Logging in to Spotify...")
        self.sp = get_spotify_client(status_callback=self.log)
        if not self.sp:
            self.log("Spotify login failed.")
            return

        user = self.sp.current_user()
        self.log(f"Logged in as: {user['display_name']}")
        self.log("Welcome to Gesturefy!")
        self.log("Press start to begin gesture control.")
        self.start_updating_track_info()
        if hasattr(self, "loading_screen"):
            self.loading_screen.pack_forget()
        if hasattr(self, "login_screen"):
            self.login_screen.pack_forget()
            self.main_screen.pack(fill="both", expand=True)
            # Clear topbar
            for widget in self.topbar.winfo_children():
                widget.destroy()

        # Remake topbar - prevents duplication
        settings_image_url = "assets/settings_gear_transparent.png"
        circular_settings_image = get_circular_image(settings_image_url, size=(37, 37))

        self.settings_button = ctk.CTkButton(
            self.topbar,
            image=circular_settings_image,
            command=self.open_settings,
            text="",
            width=32,
            fg_color="transparent",
            bg_color="transparent",
            hover_color="#191414"
        )
        self.settings_button.pack(side="right", padx=(10, 0), pady=10)  # Right-align gear button
       

        # Displays profile picture and username in a profile frame
        self.profile_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.profile_frame.pack(side="right", padx=15, pady=10)

        image_url = user["images"][0]["url"] if user.get("images") else "assets/default_pfp.png"
        circular_image = get_circular_image(image_url, size=(34, 34))

        self.profile_pic_label = ctk.CTkLabel(self.profile_frame, image=circular_image, text="")
        self.profile_pic_label.image = circular_image
        self.profile_pic_label.pack(side="left", padx=(10, 10))

        self.username_label = ctk.CTkLabel(self.profile_frame, text=f"{user['display_name']}", font=ctk.CTkFont(family="Montserrat", size=22, weight="bold"), text_color="#F1F1F1")
        self.username_label.pack(side="left", anchor="center")
        
        self.profile_frame.pack_configure(padx=(0, 8))
           
    def open_settings(self):
        self.log("Opening settings...")
        self.main_screen.pack_forget()
        
        # Main setting screen
        self.settings_screen = ctk.CTkFrame(self.root, fg_color="#212121")
        self.settings_screen.pack(fill="both", expand=True)
        self.settings_label = ctk.CTkLabel(self.settings_screen, text="Settings", font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"), text_color="#1DB954")
        self.settings_label.pack(pady=(20, 10))
        
        # Back button
        self.back_button = ctk.CTkButton(
            self.settings_screen,
            text="Back",
            command=self.back_to_main,
            fg_color="#1DB954",
            hover_color="#1ed760",
            text_color="black",
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold")
        )
        self.back_button.pack(pady=(10, 20))
        
        # Switch user button
        self.switch_user_button = ctk.CTkButton(
            self.settings_screen,
            text="Switch User",
            command=self.switch_user,
            fg_color="#1DB954",
            hover_color="#1ed760",
            text_color="black",
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold")
        )
        self.switch_user_button.pack(pady=(10, 20))

        # Logout button
        self.logout_button = ctk.CTkButton(
            self.settings_screen,
            text="Logout",
            command=self.logout,
            fg_color="#ff4d4d",
            hover_color="#ff6666",
            text_color="black",
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold")
        )
        self.logout_button.pack(pady=(10, 20))

    def back_to_main(self):
        self.log("Returning to main screen...")
        self.settings_screen.pack_forget()
        self.main_screen.pack(fill="both", expand=True)
            
    def switch_user(self):
        self.log("Switching user...")
        # Log out of gesturefy
        self.logout()
        self.login_screen.pack_forget() # Hide login screen
        # Show a loading screen saying "Switching user..."
        self.loading_screen = ctk.CTkFrame(self.root, fg_color="#212121")
        self.loading_screen.pack(fill="both", expand=True)
        self.loading_label = ctk.CTkLabel(self.loading_screen, 
                                          text="Switching user...\nPlease navigate to opened browser tab to log in with a different account.", 
                                          font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"), text_color="#1DB954")
        self.loading_label.pack(pady=(20, 10))
        
        # Log out of spotify.com to log in with a different account
        # Open Spotify logout page in browser
        # Path to local HTML logout helper
        logout_page = Path(__file__).parent / "logout_redirect.html"
        logout_url = f"file://{logout_page.resolve()}"

        # Open the logout helper in browser
        webbrowser.open(logout_url)

        # Delay to allow logout and tab closure
        self.switch_user_button.after(2000, self.spotify_login)  # 2 seconds
    
    def logout(self):
        if self.sp:
            self.sp = None
            self.log("Logged out of Spotify.")
            self.start_stop_btn.configure(state="normal")
            if hasattr(self, 'gesture_thread'):
                self.stop_gesture_control()
            self.settings_screen.pack_forget()
            self.login_screen.pack(fill="both", expand=True)
            #also have to delete tokens.json
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH)
            self.log_output.configure(state="normal")
            self.log_output.delete("1.0", "end")
            self.log_output.configure(state="disabled")
                
    def start_gesture_control(self):
        if not self.sp:
            self.log("Please log in to Spotify first.")
            self.start_stop_btn.configure(state="normal")
            return

        self.gesture_thread = GestureControl(self.sp, log_callback=self.log)
        self.gesture_thread.start()
        self.running = True
        self.log("Gesture control started. Press stop to end.")
        self.log("Scanning for gestures...")
        self.start_stop_btn.configure(text="Stop", state="normal")

    def stop_gesture_control(self):
        if self.gesture_thread:
            self.gesture_thread.stop()
            self.gesture_thread.join()
            self.gesture_thread = None
        self.running = False
        self.log("Stopped gesture control. Press start to resume.")
        self.start_stop_btn.configure(text="Start")
   
    
    def start_updating_track_info(self):
        def update_loop():
            last_track = None  
            last_progress = 0  
            placeholder_path = os.path.join("assets", "placeholder_album.png")

            while True:
                try:
                    if not self.sp:
                        time.sleep(1)
                        continue

                    current = self.sp.current_playback()

                    if current and current.get("item"):
                        track = current["item"]
                        name = track["name"]
                        artists = ", ".join([a["name"] for a in track["artists"]])
                        album_art_url = track["album"]["images"][0]["url"]
                        progress_ms = current["progress_ms"] or 0
                        duration_ms = track["duration_ms"]

                        last_track = {
                            "name": name,
                            "artists": artists,
                            "album_art_url": album_art_url,
                            "duration_ms": duration_ms
                        }
                        last_progress = progress_ms

                        self.song_title_label.configure(text=name)
                        self.artist_label.configure(text=artists)
                        self.progress_bar.set(progress_ms / duration_ms)
                        self.track_time_label.configure(
                            text=f"{int(progress_ms / 1000 // 60)}:{int((progress_ms / 1000) % 60):02d} / "
                                f"{int(duration_ms / 1000 // 60)}:{int((duration_ms / 1000) % 60):02d}"
                        )

                        image_bytes = requests.get(album_art_url).content
                        image_pil = Image.open(io.BytesIO(image_bytes)).resize((315, 315))
                        self.album_art_img = ImageTk.PhotoImage(image_pil)
                        self.album_art_label.configure(image=self.album_art_img)

                        queue = self.sp.queue()
                        if queue and queue.get("queue"):
                            next_song = queue["queue"][0]
                            next_name = next_song["name"]
                            next_artist = ", ".join([a["name"] for a in next_song["artists"]])
                            self.next_song_title_label.configure(text=next_name)
                            self.next_artist_label.configure(text=next_artist)

                            next_album_art_url = next_song["album"]["images"][0]["url"]
                            next_image_bytes = requests.get(next_album_art_url).content
                            next_image_pil = Image.open(io.BytesIO(next_image_bytes)).resize((100, 100))
                            self.next_album_art_img = ImageTk.PhotoImage(next_image_pil)
                            self.next_album_art_label.configure(image=self.next_album_art_img)
                        else:
                            self.next_song_title_label.configure(text="N/A")
                            self.next_artist_label.configure(text="")
                            self.next_album_art_label.configure(image=None)

                    else:
                        self.song_title_label.configure(text="Not Playing")
                        self.artist_label.configure(text="Ensure Spotify is open, and start playing a song to see track info")
                        self.progress_bar.set(0)
                        self.track_time_label.configure(text="0:00 / 0:00")

                        if os.path.exists(placeholder_path):
                            placeholder_img = Image.open(placeholder_path).resize((250, 250))
                            self.album_art_img = ImageTk.PhotoImage(placeholder_img)
                            self.album_art_label.configure(image=self.album_art_img)
                            
                            placeholder_img = Image.open(placeholder_path).resize((100, 100))
                            self.next_album_art_img = ImageTk.PhotoImage(placeholder_img)
                            self.next_album_art_label.configure(image=self.next_album_art_img)
                        else:
                            self.album_art_label.configure(image=None)

                        self.next_song_title_label.configure(text="N/A")
                        self.next_artist_label.configure(text="")
                        self.next_album_art_label.configure(image=None)

                except Exception as e:
                    print(f"Error updating track info: {e}")

                time.sleep(0.5)

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

# On run, create the app and start the main loop
if __name__ == "__main__":
    app = ctk.CTk()
    app.iconbitmap("assets/gesturefy.ico")
    GesturefyApp(app)
    app.mainloop()

