# spotify_integration.py
import cv2
import mediapipe as mp
import time
import platform
from hand_gesture_detection import GestureRecognizer
import threading
from io import BytesIO

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
    def __init__(self, sp, log_callback=None, depth_threshold = 0.0):
        super().__init__()
        self.sp = sp
        self._running = True
        self.log = log_callback or print
        self.cooldown = 1  # seconds between reset
        self.last_action_time = 0
        # MediaPipe init
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.9)
        self.recognizer = GestureRecognizer()
         # New: store depth values
        self.depth_threshold = depth_threshold
        self.gesture_counter = {
        "closed_fist": 0,
        "open_fist": 0,
        "thumbs_up": 0,
        "pointing_up": 0,
        "pointing_down": 0,
        "pointing_left": 0,
        "pointing_right": 0
     }
        self.GESTURE_HOLD_FRAMES = 8
        self.last_triggered = None

    def stop(self):
        self._running = False
    
    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open video capture.")
            return
        
        while self._running:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            SCALE_FACTOR = 100000000
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                   #Check how close the wrist or palm is
                    raw_z   = hand_landmarks.landmark[0].z    # e.g. –0.05 when very close
                    z_depth = abs(raw_z * SCALE_FACTOR)   
                    #print(z_depth)
                    if z_depth < self.depth_threshold:
                        print(f"⛔ Hand too far: {z_depth:.3f} > threshold {self.depth_threshold:.3f}")
                        continue  # Skip if hand is too far
                  
                    self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                    gesture = self.recognizer.recognize(hand_landmarks)

                    if gesture and gesture in self.gesture_counter:
                        self.gesture_counter[gesture] += 1

                        current_time = time.time()
                        if (
                            self.gesture_counter[gesture] >= self.GESTURE_HOLD_FRAMES
                            #and self.last_triggered != gesture
                            and (current_time - self.last_action_time) >= self.cooldown
                        ):
                            self.last_triggered = gesture
                            self.last_action_time = current_time
                            self.gesture_counter = {key: 0 for key in self.gesture_counter}
                            self.handle_gesture_action(gesture)
                    else:
                        # Only reset counters if no valid gesture or different gesture
                        self.gesture_counter = {key: 0 for key in self.gesture_counter}
                        self.last_triggered = None


        cap.release()

    def handle_gesture_action(self, gesture):
        try:
            if gesture == "closed_fist":
                playback_info = self.sp.current_playback()
                if not playback_info or not playback_info['is_playing']:
                    devices = self.sp.devices().get("devices", [])
                    if devices:
                        active_device = next((d for d in devices if d.get("is_active")), None)
                        if not active_device:
                            self.sp.transfer_playback(device_id=devices[0]["id"], force_play=False)
                            time.sleep(0.5)
                        self.sp.start_playback()
                        self.log("Closed Fist - Playing Song")
            elif gesture == "open_fist":
                playback_info = self.sp.current_playback()
                if playback_info and playback_info['is_playing']:
                    self.sp.pause_playback()
                    self.log("Open Fist - Pausing Song")
            elif gesture == "thumbs_up":
                current_playback = self.sp.current_playback()
                if current_playback and current_playback['item']:
                    track_id = current_playback['item']['id']
                    self.sp.current_user_saved_tracks_add([track_id])
                    self.log("Thumbs Up - Liked Song")
            elif gesture == "pointing_up":
                self.log("Pointing Up - Increasing Volume")
                set_volume(10)
            elif gesture == "pointing_down":
                self.log("Pointing Down - Decreasing Volume")
                set_volume(-10)
            elif gesture == "pointing_right":
                self.log("Pointing Right - Skipping to Next Track")
                self.sp.next_track()
            elif gesture == "pointing_left":
                self.log("Pointing Left - Replaying Previous Track")
                self.sp.previous_track()
        except Exception as e:
            self.log(f"Error performing action for {gesture}: {e}")
        

  

    