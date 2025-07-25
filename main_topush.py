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

load_dotenv()  # This loads the .env file into environment variables

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
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")  # Spotify green
            
        #make login screen, dont show it yet
        # Login screen base
        self.login_screen = ctk.CTkFrame(root, fg_color="#212121")
        self.login_screen.pack(fill="both", expand=True)

        # Centering container inside login_screen
        self.login_container = ctk.CTkFrame(self.login_screen, fg_color="transparent")
        self.login_container.place(relx=0.5, rely=0.5, anchor="center")  # Center of screen

        # Login label and button and app icon inside the centered container
        self.app_icon = ctk.CTkImage(light_image=Image.open("assets/gesturefy_nobg.png").resize((128, 128)), size=(128, 128))
        self.app_icon_label = ctk.CTkLabel(self.login_container, image=self.app_icon, text="")
        self.app_icon_label.pack(pady=(0, 10))
        
        self.login_label = ctk.CTkLabel(
            self.login_container,
            width=200,
            height=50,
            text="Gesturefy",
            font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"),
            text_color="#1DB954"
        )
        self.login_label.pack(pady=(0, 10))

        self.login_button = ctk.CTkButton(
            self.login_container,
            width=200,
            height=50,
            text="Log in",
            command=self.spotify_login,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="black",
            fg_color="#1DB954",
            hover_color="#1ed760"
        )
        self.login_button.pack(pady=(0, 10))

        self.login_screen.pack_forget()  # Hide login screen initially
        #if not already logged in, show login screen
        if not load_tokens():
            self.login_screen.pack(fill="both", expand=True)
            #prepare main screen
            self.main_screen = ctk.CTkFrame(root, fg_color="#212121")
            self.main_screen.pack(fill="both", expand=True)
            self.main_screen.pack_forget()  # Hide main screen initially
            login = True

        if not hasattr(self, 'main_screen'):
            self.main_screen = ctk.CTkFrame(root, fg_color="#212121")
            self.main_screen.pack(fill="both", expand=True)
            login = False
            
        self.sidebar = ctk.CTkFrame(self.main_screen, width=300, corner_radius=18, fg_color="#191414")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.title_label = ctk.CTkLabel(self.sidebar, text="GESTUREFY", font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"), text_color="#1DB954")
        self.title_label.pack(pady=(40, 10))

        self.subtitle = ctk.CTkLabel(self.sidebar, text="Control Spotify\nwith gestures!", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"), justify="center", text_color="white")
        self.subtitle.pack(pady=5)

        self.start_stop_btn = ctk.CTkButton(self.sidebar, text="Start", command=self.toggle, fg_color="#1DB954", hover_color="#1ed760", text_color="black", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"))
        self.start_stop_btn.pack(pady=(40, 10))

        self.topbar = ctk.CTkFrame(self.main_screen, height=40, corner_radius=15, fg_color="#191414")
        self.topbar.pack(side="top", anchor="ne", padx=10, pady=(10, 0))
        
        self.log_output = ctk.CTkTextbox(self.main_screen, height=160, wrap="word", corner_radius=15, font=ctk.CTkFont(family="Montserrat", size=12), fg_color="#2c2c2c", text_color="gray")
        self.log_output.pack(side="bottom", fill="x", padx=20, pady=10)
        self.log_output.configure(state="disabled")

        self.center_frame = ctk.CTkFrame(self.main_screen, fg_color="transparent")
        self.center_frame.pack(side="top", pady=20)

        self.album_art_label = ctk.CTkLabel(self.center_frame, text="", image=None)
        self.album_art_label.pack(pady=(10, 10))

        self.song_info_label = ctk.CTkLabel(self.center_frame, text="Currently Playing:\n...", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"), text_color="white")
        self.song_info_label.pack(pady=5)

        self.next_up_label = ctk.CTkLabel(self.center_frame, text="Next Up:\n...", font=ctk.CTkFont(family="Montserrat", size=14, weight="bold"), text_color="#1DB954")
        self.next_up_label.pack(pady=(5, 15))

        self.progress_bar = ctk.CTkProgressBar(self.center_frame, width=300, progress_color="#1DB954")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))

        self.track_time_label = ctk.CTkLabel(self.center_frame, text="0:00 / 0:00", font=ctk.CTkFont(family="Montserrat", size=12, weight="bold"), text_color="white")
        self.track_time_label.pack(pady=(2, 0))
        
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
        self.profile_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.profile_frame.pack(side="right", padx=20, pady=10)

        image_url = user["images"][0]["url"] if user.get("images") else "assets/default_pfp.png"
        circular_image = get_circular_image(image_url, size=(32, 32))

        self.profile_pic_label = ctk.CTkLabel(self.profile_frame, image=circular_image, text="")
        self.profile_pic_label.image = circular_image
        self.profile_pic_label.pack(side="left", padx=(0, 8))

        self.username_label = ctk.CTkLabel(self.profile_frame, text=f"{user['display_name']}", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"), text_color="white")
        self.username_label.pack(side="left", anchor="center")
        
        self.settings_button = ctk.CTkButton(
            self.profile_frame,
            text="Settings",
            command=self.open_settings,
            fg_color="#1DB954",
            hover_color="#1ed760",
            text_color="black",
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold")
        )
        self.settings_button.pack(side="right", anchor="center", padx=(0, 10))

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

                        # Store last known info
                        last_track = {
                            "name": name,
                            "artists": artists,
                            "album_art_url": album_art_url,
                            "duration_ms": duration_ms
                        }
                        last_progress = progress_ms

                        self.song_info_label.configure(text=f"Currently Playing:\n{name} - {artists}")
                        self.progress_bar.set(progress_ms / duration_ms)
                        self.track_time_label.configure(text=f"{int(progress_ms / 1000 // 60)}:{int((progress_ms / 1000) % 60):02d} / {int(duration_ms / 1000 // 60)}:{int((duration_ms / 1000) % 60):02d}")

                        image_bytes = requests.get(album_art_url).content
                        image_pil = Image.open(io.BytesIO(image_bytes)).resize((150, 150))
                        self.album_art_img = ImageTk.PhotoImage(image_pil)
                        self.album_art_label.configure(image=self.album_art_img)

                        queue = self.sp.queue()
                        if queue and queue.get("queue"):
                            next_song = queue["queue"][0]
                            next_name = next_song["name"]
                            next_artist = ", ".join([a["name"] for a in next_song["artists"]])
                            self.next_up_label.configure(text=f"Next Up:\n{next_name} - {next_artist}")
                        else:
                            self.next_up_label.configure(text="Next Up:\nN/A")

                    elif last_track:
                        # Use last known info if paused or playback is None
                        self.song_info_label.configure(text=f"Currently Playing:\n{last_track['name']} - {last_track['artists']}")
                        self.progress_bar.set(last_progress / last_track["duration_ms"])
                        self.track_time_label.configure(text=f"{int(last_progress / 1000 // 60)}:{int((last_progress / 1000) % 60):02d} / {int(last_track['duration_ms'] / 1000 // 60)}:{int((last_track['duration_ms'] / 1000) % 60):02d}")

                        image_bytes = requests.get(last_track["album_art_url"]).content
                        image_pil = Image.open(io.BytesIO(image_bytes)).resize((150, 150))
                        self.album_art_img = ImageTk.PhotoImage(image_pil)
                        self.album_art_label.configure(image=self.album_art_img)

                        self.next_up_label.configure(text="Next Up:\nN/A")

                    else:
                        self.song_info_label.configure(text="Currently Playing:\nNone")
                        self.next_up_label.configure(text="Next Up:\nN/A")
                        self.progress_bar.set(0)
                        self.track_time_label.configure(text="0:00 / 0:00")

                except Exception as e:
                    print(f"Error updating track info: {e}")

                time.sleep(0.5)

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

if __name__ == "__main__":
    app = ctk.CTk()
    app.iconbitmap("assets/gesturefy.ico")
    GesturefyApp(app)
    app.mainloop()

