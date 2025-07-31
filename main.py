# main.py
import customtkinter as ctk
from pathlib import Path
import threading
import webbrowser
import json
import os
import spotipy
from spotify_integration import GestureControl
from hand_gesture_detection import GestureRecognizer
from PIL import Image, ImageDraw, ImageTk
import io
from io import BytesIO
import requests
import time
import sys
import uuid
import subprocess
from colorthief import ColorThief
from spotifyhelpers import get_current_album_art_url, get_dominant_color_from_url, rgb_to_hex, mild_tint_from_rgb

TOKEN_PATH = 'tokens.json'
BACKEND_URL = "https://gesturefy-auth-backend-1f562dbd4c73.herokuapp.com"

def save_tokens(token_info):
    with open(TOKEN_PATH, 'w') as f:
        json.dump(token_info, f)

def load_tokens():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            return json.load(f)
    return None

def authenticate_spotify(status_callback=None):
    SPOTIFY_CLIENT_ID = "f99bddfb14a0460a8db59ad4628af5fb"
    SPOTIFY_SCOPE = "user-library-modify user-read-playback-state user-modify-playback-state"
    REDIRECT_URI = f"{BACKEND_URL}/callback"

    token_info = load_tokens()
    now = int(time.time())
    # Check if we already have tokens
    if token_info:
        expires_at = token_info.get("expires_at", 0)
        if expires_at < now + 60:
            # Token expired or about to expire - try refreshing
            if status_callback:
                status_callback("Refreshing access token...")
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/refresh_token",
                        json={"refresh_token": token_info.get("refresh_token")}
                    )
                    if response.status_code == 200:
                        new_tokens = response.json()
                        # Update token_info with new access token and expiry
                        token_info["access_token"] = new_tokens["access_token"]
                        expires_in = new_tokens.get("expires_in", 3600)
                        token_info["expires_at"] = now + int(expires_in)
                        # Save updated tokens
                        save_tokens(token_info)
                    else:
                        # Refresh failed - force full login
                        token_info = None
                except Exception as e:
                    if status_callback:
                        status_callback(f"Token refresh error: {e}")
                    token_info = None
        else:
            # Token valid, return access token directly
            return token_info["access_token"]
    else:
        # No valid tokens, start full auth flow:

        # Generate a random state string for security
        state = str(uuid.uuid4())

        # Build the Spotify authorization URL with your backend redirect and state
        auth_url = (
            "https://accounts.spotify.com/authorize"
            "?response_type=code"
            f"&client_id={SPOTIFY_CLIENT_ID}"
            f"&scope={SPOTIFY_SCOPE}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&state={state}"
            "&show_dialog=true"
        )

        if status_callback:
            status_callback("Opening browser for Spotify login...")
        
        def open_browser(url):
            print("Trying to open browser at:", url)
            try:
                if sys.platform.startswith("darwin"):
                    subprocess.run(["open", url], check=True)
                else:
                    success = webbrowser.open(url)
                    if not success:
                        raise Exception("webbrowser.open() failed")
            except Exception as e:
                print("Failed to open browser:", e)
        
        open_browser(auth_url)
        #webbrowser.open(auth_url)

        # Poll your backend for tokens
        token_info = None
        try:
            for _ in range(30):  # ~30 seconds max wait
                response = requests.get(f"{BACKEND_URL}/get_tokens?state={state}")
                if response.status_code == 200:
                    token_info = response.json()
                    break
                time.sleep(1)
        except Exception as e:
            if status_callback:
                status_callback(f"Error contacting backend: {e}")
            return None

        if not token_info:
            if status_callback:
                status_callback("Failed to retrieve tokens from backend.")
            return None

        # Save expiry as UNIX timestamp for easy comparison
        if "expires_in" in token_info:
            token_info["expires_at"] = int(time.time()) + int(token_info["expires_in"])

        save_tokens(token_info)
        return token_info["access_token"]

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

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Running normally
        return os.path.join(os.path.abspath("."), relative_path)

# Main application class
class GesturefyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesturefy")
        self.root.withdraw()
        self.recognizer = GestureRecognizer()
        self.keep_refreshing_token = False

        font_path = resource_path("fonts/Montserrat-Regular.ttf")
        montserrat_path = Path(font_path)
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
        pngicon_path = resource_path("assets/gesturefy_nobg.png")
        self.original_icon_image = Image.open(pngicon_path).resize((170, 170))
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
            text="Log in",
            width=200,
            height=50,
            corner_radius=20,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="white",
            fg_color="#343333",
            hover_color="#545454",
            border_color="#1F1F1F",
            border_width=4,
            command=self.spotify_login
            
        )
        self.login_button.pack(pady=(0, 10))
        # Trigger wave animation on hover
        self.login_button.bind("<Enter>", lambda e: self.animate_wave_once())

        # Hide login screen initially
        self.login_screen.pack_forget()

    # Create loading screen
        self.loading_screen = ctk.CTkFrame(self.root, fg_color="#212121")
        self.loading_label = ctk.CTkLabel(
            self.loading_screen,
            text="Logging in, please wait...",
            font=ctk.CTkFont(family="Montserrat", size=24, weight="bold"),
            text_color="white"
        )
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_screen.pack_forget()  # hide it initially - only show while logging in

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
        self.title_label.place(anchor="center", relx=0.5, rely=0.4)

        self.subtitle = ctk.CTkLabel(self.sidebar, text="Control Spotify\nwith gestures!", font=ctk.CTkFont(family="Montserrat", size=22, weight="bold"), justify="center", text_color="#A0A0A0")
        self.subtitle.place(anchor="center", relx=0.5, rely=0.5)

         # Slider
        # Frame to hold slider, place in alignment with center console and logbox
        self.slider_frame = ctk.CTkFrame(self.main_screen, height=65, width=450, corner_radius=15, fg_color="#191414")
        self.slider_frame.place(relx=0.355, rely=0.055, anchor='center')
        self.depth_slider = ctk.CTkSlider(
            self.slider_frame,
            button_color="#1DB954",
            button_hover_color="#23E065",
            progress_color="#1DB954",
            from_=0,
            to=50,
            number_of_steps=50,  # (0.1 - (-0.1)) / 0.01 = 20 steps
            width=300,
            command=self.update_depth_threshold
        )
        self.depth_slider.set(25)
        self.depth_slider.place(relx=0.5, rely=0.43, anchor="center")

        self.depth_label = ctk.CTkLabel(self.slider_frame, text_color="#F1F1F1", font=ctk.CTkFont(family="Poppins", size=12, weight="bold"), text="Detection Range")
        self.depth_label.place(relx=0.5, rely=0.8, anchor="center")
        self.depth_threshold = float(self.depth_slider.get())

        # Start/Stop button
        self.start_stop_btn = ctk.CTkButton(self.sidebar, width=200, height=50, corner_radius= 20, text="Start", command=self.toggle, fg_color="#343333", hover_color="#545454", text_color="white", font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"), border_color="#1F1F1F", border_width=4)
        self.start_stop_btn.place(anchor="center", relx=0.5, rely=0.6)

        # Top bar for profile and settings
        self.topbar = ctk.CTkFrame(self.main_screen, height=40, corner_radius=15, fg_color="#191414")
        self.topbar.pack(side="top", anchor="ne", padx=20, pady=(10, 0))
        
        
        # Log output area
        self.log_output = ctk.CTkTextbox(self.main_screen, height=160, wrap="word", corner_radius=15, font=ctk.CTkFont(family="Poppins", size=12), fg_color="#2c2c2c", text_color="gray")
        self.log_output.pack(side="bottom", fill="x", padx=20, pady=(5,10))
        self.log_output.configure(state="disabled")

        # Center frame for currently playing song info and next up info
        # This frame will hold the main content of the app
        self.center_frame = ctk.CTkFrame(self.main_screen, fg_color="#191414", corner_radius=15, width=800, height=600)
        self.center_frame.pack(side="top", pady=(10,5), padx=20, fill="both", expand=True)

        # Now Playing Frame
        self.now_playing_frame = ctk.CTkFrame(self.center_frame, width = 1000, height = 1000, fg_color="transparent")
        self.now_playing_frame.place(relx=0.015, rely=0.015, anchor="nw")

        # Album Art (left)
        self.album_art_label = ctk.CTkLabel(self.now_playing_frame, text="", image=None)
        self.album_art_label.place(relx=0.02, rely=0.02, anchor="nw")
        
        # "Currently Playing" label (right)
        self.now_playing_label = ctk.CTkLabel(
            self.now_playing_frame,
            text="Currently Playing",
            font=ctk.CTkFont(family="Poppins", size=32, weight="bold"),
            text_color="#1DB954", 
        )
        self.now_playing_label.place(relx=0.285, rely=0.025, anchor="nw")

        self.song_title_label = ctk.CTkLabel(
            self.now_playing_frame,
            text="Song Title",
            font=ctk.CTkFont(family="Poppins", size=40, weight="bold"),
            text_color="white"
        )
        self.song_title_label.place(relx=0.285, rely=0.22, anchor="sw")

        self.artist_label = ctk.CTkLabel(
            self.now_playing_frame,
            text="Artist Name",
            font=ctk.CTkFont(family="Poppins", size=28),
            text_color="#B3B3B3"
        )
        self.artist_label.place(relx=0.285, rely=0.26, anchor="sw")

        # Frame for progress bar + timestamp
        self.progress_frame = ctk.CTkFrame(self.now_playing_frame, width=601, height=50, fg_color = "transparent")
        self.progress_frame.place(relx=0.015, rely=0.3, anchor = "nw")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=600, progress_color="#1DB954")
        self.progress_bar.set(0)
        self.progress_bar.place(anchor="nw")

        self.track_time_label = ctk.CTkLabel(
            self.progress_frame,
            text="0:00 / 0:00",
            font=ctk.CTkFont(family="Montserrat", size=12, weight="bold"),
            text_color="white"
        )
        
        self.track_time_label.place(relx = 0.99, rely=0.17,anchor="ne")

        # --- "Next Up" Song Info ---
        self.next_up_container = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.next_up_container.pack(anchor="e", side="bottom", padx=(0, 20), pady=(0, 20))

        self.next_album_art_label = ctk.CTkLabel(self.next_up_container, text="", image=None)
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

    def update_depth_threshold(self, val):
        val = float(val)
        self.depth_threshold = val

        # push change to the running thread
        if hasattr(self, "gesture_thread") and self.gesture_thread:
            self.gesture_thread.depth_threshold = val

        pivot = 25
        band  = 5.0

        if pivot - band < val < pivot + band:
            msg = "Average Range"
        elif val < pivot - band:
            msg = "Further (More Recognition)"
        else:
            msg = "Closer (Less  Recognition)"

        # update the UI once (with both text + number)
        self.depth_label.configure(text=f"{msg} ({val:.0f})")

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

    def start_checking_for_expiry(self):
        def check_expiry():
            while True:
                time.sleep(5) # Check every 5 seconds
                self.sp = get_spotify_client(status_callback=self.log) #Auto refreshes if expired, if not expired then no change
                #print("Called sp client")
                self.user = self.sp.current_user()
        threading.Thread(target=check_expiry, daemon=True).start()
        
    def _perform_login(self):
        self.sp = get_spotify_client(status_callback=self.log)
        self.loading_screen.after(50, self._handle_login_result)

    def _handle_login_result(self, retried=False):
        if not self.sp:
            self.log("Spotify login failed.")
            self.login_screen.pack_forget()
            self.loading_screen.pack_forget()
            self.main_screen.pack_forget()
            if not retried:
                retried=True
                self.root.after(100, self.logout()) # Try deleting the current tokens.json
                self.root.after(1000, self.spotify_login())
            return

        self.loading_screen.pack_forget()
        self.main_screen.pack(fill="both", expand=True)

        user = self.sp.current_user()
        self.log(f"Logged in as: {user['display_name']}")
        self.log("Welcome to Gesturefy!")
        self.log("Press start to begin gesture control.")
        self.start_updating_track_info()
        self.start_checking_for_expiry()
        
        
        if hasattr(self, "loading_screen"):
            self.loading_screen.pack_forget()
        if hasattr(self, "login_screen"):
            self.login_screen.pack_forget()
            self.main_screen.pack(fill="both", expand=True)
            # Clear topbar
            for widget in self.topbar.winfo_children():
                widget.destroy()

        # Remake topbar - prevents duplication
        settings_image_url = resource_path("assets/settings_gear_transparent.png")
        self.circular_settings_image = get_circular_image(settings_image_url, size=(37, 37))

        self.settings_button = ctk.CTkButton(
            self.topbar,
            image=self.circular_settings_image,
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

        image_url = user["images"][0]["url"] if user.get("images") else resource_path("assets/default_pfp.png")
        circular_image = get_circular_image(image_url, size=(34, 34))

        self.profile_pic_label = ctk.CTkLabel(self.profile_frame, image=circular_image, text="")
        self.profile_pic_label.image = circular_image
        self.profile_pic_label.pack(side="left", padx=(10, 10))

        self.username_label = ctk.CTkLabel(self.profile_frame, text=f"{user['display_name']}", font=ctk.CTkFont(family="Montserrat", size=22, weight="bold"), text_color="#F1F1F1")
        self.username_label.pack(side="left", anchor="center")
        
        self.profile_frame.pack_configure(padx=(0, 8))

    def spotify_login(self):
        self.log("Logging in to Spotify...")
        self.login_screen.pack_forget()
        self.loading_screen.pack(fill="both", expand=True)

        threading.Thread(target=self._perform_login, daemon=True).start()        
        
    def open_settings(self):
        self.log("Opening settings...")
        self.main_screen.pack_forget()
        
        # Main setting screen
        self.settings_screen = ctk.CTkFrame(self.root, fg_color="#212121")
        self.settings_screen.pack(fill="both", expand=True)
        self.settings_label = ctk.CTkLabel(self.settings_screen, text="Settings", font=ctk.CTkFont(family="Montserrat", size=44, weight="bold"), text_color="white")
        self.settings_label.pack(pady=(20, 10))
        
        #Center frame for settings content
        self.settings_content_frame = ctk.CTkFrame(self.settings_screen, fg_color="transparent", width=600, height=400)
        self.settings_content_frame.place(relx=0.5, rely=0.5, anchor="center")
        # Back button
        self.back_button = ctk.CTkButton(
            self.settings_content_frame,
            text="Back",
            command=self.back_to_main,
            width=200,
            height=50,
            corner_radius=20,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="white",
            fg_color="#343333",
            hover_color="#545454",
            border_color="#1F1F1F",
            border_width=4
        )
        self.back_button.pack(pady=(10, 20))
        
        # Switch user button
        self.switch_user_button = ctk.CTkButton(
            self.settings_content_frame,
            text="Switch User",
            command=self.switch_user,
            width=200,
            height=50,
            corner_radius=20,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="white",
            fg_color="#343333",
            hover_color="#545454",
            border_color="#1F1F1F",
            border_width=4
        )
        self.switch_user_button.pack(pady=(10, 20))

        # Logout button
        self.logout_button = ctk.CTkButton(
            self.settings_content_frame,
            text="Logout",
            command=self.logout,
            width=200,
            height=50,
            corner_radius=20,
            font=ctk.CTkFont(family="Montserrat", size=16, weight="bold"),
            text_color="white",
            fg_color="#FF0000",
            hover_color="#C20A0A",
            border_color="#1F1F1F",
            border_width=4
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
                                          font=ctk.CTkFont(family="Montserrat", size=32, weight="bold"), text_color="white")
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Log out of spotify.com to log in with a different account
        # Open Spotify logout page in browser
        # Path to local HTML logout helper
        logout_page = Path(resource_path("logout_redirect.html"))
        logout_url = f"file://{logout_page.resolve()}"

        # Open the logout helper in browser
        webbrowser.open(logout_url)

        # Delay to allow logout and tab closure
        self.switch_user_button.after(1500, self.spotify_login)  # 1.5 seconds
    
    def logout(self):
        if self.sp:
            self.sp = None
            self.log("Logged out of Spotify.")
            self.keep_refreshing_token = False
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

        self.gesture_thread = GestureControl(
            self.sp,
            log_callback=self.log,
            depth_threshold=self.depth_threshold
        )
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
            placeholder_path = resource_path("assets/placeholder_album.png")

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
                        image_pil = Image.open(io.BytesIO(image_bytes)).resize((246, 246), Image.LANCZOS)

                        self.album_art_img = ctk.CTkImage(light_image=image_pil, size=(246, 246))
                        self.album_art_label.configure(image=self.album_art_img)
                        self.album_art_label.image = self.album_art_img  # prevent garbage collection
                        self.update_theme_based_on_album(album_art_url)

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
                        self.artist_label.configure(text="Play track in Spotify (make sure it's open)")
                        self.progress_bar.set(0)
                        self.track_time_label.configure(text="0:00 / 0:00")

                        if os.path.exists(placeholder_path):
                            placeholder_img = Image.open(placeholder_path).resize((246, 246), Image.LANCZOS)
                            self.album_art_img = ctk.CTkImage(light_image=placeholder_img, size=(246, 246))
                            self.album_art_label.configure(image=self.album_art_img)
                            self.album_art_label.image = self.album_art_img  # prevent garbage collection
                            
                            
                            placeholder_img = Image.open(placeholder_path).resize((100, 100), Image.LANCZOS)
                            self.next_album_art_img = ctk.CTkImage(light_image=placeholder_img, size=(100, 100))
                            self.next_album_art_label.configure(image=self.next_album_art_img)
                            self.next_album_art_label.image = self.next_album_art_img
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

    def update_theme_based_on_album(self, album_art_url):
        if not self.sp or not album_art_url:
            self.log("Spotify client not initialized or no album art URL.")
            return
        
        dominant_rgb = get_dominant_color_from_url(album_art_url)
        mild_rgb = mild_tint_from_rgb(dominant_rgb)
        hex_color = rgb_to_hex(mild_rgb)
        # TODO: Update your app UI colors with hex_color here
        self.main_screen.configure(fg_color=hex_color)
        self.sidebar.configure(fg_color=hex_color)
        self.topbar.configure(fg_color=hex_color)
        self.center_frame.configure(fg_color=hex_color)       # <-- main area
        self.now_playing_frame.configure(fg_color=hex_color)
        

# On run, create the app and start the main loop
if __name__ == "__main__":
    app = ctk.CTk()
    icon_path = resource_path("assets/gesturefy.ico")
    app.iconbitmap(icon_path) 
    GesturefyApp(app)
    app.mainloop()
