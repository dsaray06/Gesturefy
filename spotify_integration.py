# spotify_integration.py
import cv2
import mediapipe as mp
import time
import platform
from hand_gesture_detection import (
    is_closed_fist, is_open_fist, 
    is_pointing_right, is_pointing_left,
    is_pointing_up, is_pointing_down, 
    is_thumbs_up
)
import threading

# Volume control (platform-specific)
if platform.system() == "Windows":
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
elif platform.system() == "Darwin":
    import subprocess

def set_volume(volume_change):
    if platform.system() == "Windows":
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        current_volume = volume.GetMasterVolumeLevelScalar()
        new_volume = max(0.0, min(1.0, current_volume + volume_change / 100.0))
        volume.SetMasterVolumeLevelScalar(new_volume, None)
    elif platform.system() == "Darwin":
        current_volume = int(subprocess.check_output(
            ["osascript", "-e", "output volume of (get volume settings)"]
        ).strip())
        new_volume = max(0, min(100, current_volume + volume_change))
        subprocess.call(["osascript", "-e", f"set volume output volume {new_volume}"])

class GestureControl(threading.Thread):
    def __init__(self, sp, log_callback=None):
        super().__init__()
        self.sp = sp
        self._running = True
        self.log = log_callback or print
        # MediaPipe init
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

    def stop(self):
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open video capture.")
            return

        gesture_detected = None
        gesture_timeout = 2
        gesture_delay = 3
        gesture_printed = False

        while self._running:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                    if is_closed_fist(hand_landmarks) and not gesture_printed:
                        playback_info = self.sp.current_playback()
                        if playback_info and playback_info['is_playing']:
                            pass
                        else:
                            devices = self.sp.devices().get("devices", [])
                            if devices:
                                active_device = next((d for d in devices if d.get("is_active")), None)
                                if not active_device:
                                    self.sp.transfer_playback(device_id=devices[0]["id"], force_play=False)
                                    time.sleep(0.5)

                                try:
                                    self.sp.start_playback()
                                    gesture_detected = "Closed Fist - Playing Song"
                                    gesture_timeout = time.time() + gesture_delay
                                    self.log(gesture_detected)
                                    gesture_printed = True
                                except Exception as e:
                                    self.log(f"Error starting playback: {e}")
                            else:
                                self.log("No available devices found for playback.")


                    elif is_open_fist(hand_landmarks) and not gesture_printed:
                        playback_info = self.sp.current_playback()
                        if playback_info and not playback_info['is_playing']:
                            pass
                        else:
                            try:
                                self.sp.pause_playback()
                                gesture_detected = "Open Fist - Pausing Song"
                                gesture_timeout = time.time() + gesture_delay
                                self.log(gesture_detected)
                                gesture_printed = True
                            except Exception as e:
                                self.log(f"Error pausing playback: {e}")

                    elif is_thumbs_up(hand_landmarks) and not gesture_printed:
                        current_playback = self.sp.current_playback()
                        if current_playback and current_playback['item']:
                            track_id = current_playback['item']['id']
                            self.sp.current_user_saved_tracks_add([track_id])
                            gesture_detected = "Thumbs Up - Liked Song"
                            gesture_timeout = time.time() + gesture_delay
                            self.log(gesture_detected)
                            gesture_printed = True
                        else:
                            self.log("No song is currently playing.")

                    elif is_pointing_up(hand_landmarks) and not gesture_printed:
                        gesture_detected = "Pointing Up - Increasing Volume"
                        gesture_timeout = time.time() + gesture_delay
                        self.log(gesture_detected)
                        gesture_printed = True
                        set_volume(10)

                    elif is_pointing_down(hand_landmarks) and not gesture_printed:
                        gesture_detected = "Pointing Down - Decreasing Volume"
                        gesture_timeout = time.time() + gesture_delay
                        self.log(gesture_detected)
                        gesture_printed = True
                        set_volume(-10)

                    elif is_pointing_right(hand_landmarks) and not gesture_printed:
                        gesture_detected = "Pointing Right - Skipping to Next Track"
                        gesture_timeout = time.time() + gesture_delay
                        self.log(gesture_detected)
                        gesture_printed = True
                        self.sp.next_track()

                    elif is_pointing_left(hand_landmarks) and not gesture_printed:
                        gesture_detected = "Pointing Left - Replaying Previous Track"
                        gesture_timeout = time.time() + gesture_delay
                        self.log(gesture_detected)
                        gesture_printed = True
                        self.sp.previous_track()

            if gesture_detected and time.time() >= gesture_timeout:
                gesture_detected = None
                gesture_printed = False

        cap.release()
