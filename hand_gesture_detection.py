import mediapipe as mp
import math
import cv2
import numpy as np
import math
import pickle
from mediapipe import solutions as mp_solutions
from mediapipe.framework.formats import landmark_pb2
import time

# Initialize MediaPipe hands module
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.8, min_tracking_confidence=0.9)

class GestureRecognizer:
    def __init__(self, model_path='gesture_model.pkl'):
        # Mediapipe hands
        self.hands = mp_solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7)
        # smoothing buffer
        self.prev_landmarks = None
        self.smooth_alpha = 0.7
        self.cooldown = 2
        self.last_action_time = 0
        # load classifier if available
        self.model = None
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
        except FileNotFoundError:
            print(f"Warning: model file '{model_path}' not found. GestureDetector will work for data collection but classify() will return None.")
        # calibration centroids (optional)
        self.centroids = {}

    def smooth_landmarks(self, lm_list):
        if self.prev_landmarks is None:
            self.prev_landmarks = lm_list
            return lm_list
        smoothed = []
        for prev, curr in zip(self.prev_landmarks, lm_list):
            x = self.smooth_alpha*prev.x + (1-self.smooth_alpha)*curr.x
            y = self.smooth_alpha*prev.y + (1-self.smooth_alpha)*curr.y
            z = self.smooth_alpha*prev.z + (1-self.smooth_alpha)*curr.z

            lm = landmark_pb2.NormalizedLandmark(x=x, y=y, z=z)
            smoothed.append(lm)
        self.prev_landmarks = smoothed
        return smoothed

    def extract_features(self, lm_list):
        # translate to wrist-origin & scale by palm size
        wrist = lm_list[0]
        pts = []
        for lm in lm_list:
            pts.append(((lm.x - wrist.x), (lm.y - wrist.y), (lm.z - wrist.z)))
        # palm size distance
        palm_size = math.dist(pts[5], pts[17])
        pts = [(x/palm_size, y/palm_size, z/palm_size) for x,y,z in pts]
        # compute key angles and distances
        features = []
        def angle(a,b,c):
            ba = np.array(a) - np.array(b)
            bc = np.array(c) - np.array(b)
            return math.degrees(math.acos(np.dot(ba,bc)/(np.linalg.norm(ba)*np.linalg.norm(bc))))
        # e.g. index knuckle
        features.append(angle(pts[6], pts[5], pts[0]))
        # add more angles/distances as-needed
        for tip_idx in [8, 12, 16, 20]:
            dist = math.dist(pts[tip_idx], pts[tip_idx-2])
            features.append(dist)
        return features

    def process_frame(self, frame):
        # run Mediapipe
        results = self.hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not results.multi_hand_landmarks:
            return None
        lm = results.multi_hand_landmarks[0].landmark
        lm = self.smooth_landmarks(lm)
        feats = self.extract_features(lm)
        return feats

    def classify(self, features):
        # if user calibrated centroids:
        if self.centroids:
            # nearest centroid
            dmin, label = float('inf'), None
            for lbl,c in self.centroids.items():
                d = math.dist(c, features)
                if d < dmin:
                    dmin, label = d, lbl
            return label
        return self.model.predict([features])[0]

    def calibrate(self, gesture_name, features_list):
        # call during startup, pass list of feature vectors
        self.centroids[gesture_name] = np.mean(features_list, axis=0)
    def is_cooldown_over(self):
        return (time.time() - self.last_action_time) >= self.cooldown

# class GestureRecognizer:
#     def recognize(self, hand_landmarks):
#         if is_peace_sign(hand_landmarks):
#             return "peace_sign"
#         elif is_closed_fist(hand_landmarks):
#             return "closed_fist"
#         elif is_open_fist(hand_landmarks):
#             return "open_fist"
#         elif is_thumbs_up(hand_landmarks):
#             return "thumbs_up"
#         elif is_pointing_up(hand_landmarks):
#             return "pointing_up"
#         elif is_pointing_down(hand_landmarks):
#             return "pointing_down"
#         elif is_pointing_left(hand_landmarks):
#             return "pointing_left"
#         elif is_pointing_right(hand_landmarks):
#             return "pointing_right"
#         else:
#             return None


# def is_closed_fist(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
#     ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
#     thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
#     wristCor = (wrist.x, wrist.y)
#     indexCor = (index_finger_tip.x, index_finger_tip.y)
#     middleCor = (middle_finger_tip.x, middle_finger_tip.y)
#     ringCor = (ring_finger_tip.x, ring_finger_tip.y)
#     thumbCor = (thumb_tip.x, thumb_tip.y)
    
#     relVar = .24
#     checkOne = math.dist(indexCor, wristCor) < relVar
#     checkTwo = math.dist(middleCor, wristCor) < relVar
#     checkThree = math.dist(ringCor, wristCor) < relVar
#     checkFour = math.dist(thumbCor, wristCor) < .32
    
#     return checkOne and checkTwo and checkThree and checkFour

# def is_open_fist(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
#     ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
#     wristCor = (wrist.x, wrist.y)
#     indexCor = (index_finger_tip.x, index_finger_tip.y)
#     middleCor = (middle_finger_tip.x, middle_finger_tip.y)
#     ringCor = (ring_finger_tip.x, ring_finger_tip.y)
    
#     relVar = .2
#     checkOne = math.dist(indexCor, wristCor) > relVar
#     checkTwo = math.dist(middleCor, wristCor) > relVar
#     checkThree = math.dist(ringCor, wristCor) > relVar
#     checkFour = math.dist(middleCor, indexCor) < 0.2
    
#     return checkOne and checkTwo and checkThree and checkFour

# def is_pointing_right(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     index_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

#     horizontal_distance = index_finger_tip.x - wrist.x
#     vertical_alignment = abs(index_finger_tip.y - wrist.y)

#     # More lenient: allow slightly greater vertical variance
#     return horizontal_distance > 0.12 and vertical_alignment < 0.5 and \
#            index_finger_tip.x > index_finger_mcp.x

# def is_pointing_left(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
#     return index_finger_tip.x < wrist.x and abs(index_finger_tip.y - wrist.y) < 0.4

# def is_pointing_up(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
#     return index_finger_tip.y < wrist.y and abs(index_finger_tip.x - wrist.x) < 0.2

# def is_pointing_down(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
#     return index_finger_tip.y > wrist.y and abs(index_finger_tip.x - wrist.x) < 0.2

# def is_thumbs_up(hand_landmarks):
#     thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
#     thumb_ip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
#     thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

#     # Stricter: ensure thumb is clearly above index and bent upwards
#     is_thumb_above_ip = thumb_tip.y < thumb_ip.y
#     is_thumb_above_index = thumb_tip.y < index_finger_tip.y - 0.05
#     is_thumb_outward = abs(thumb_tip.x - wrist.x) < 0.2

#     return is_thumb_above_ip and is_thumb_above_index and is_thumb_outward

# def is_peace_sign(hand_landmarks):
#     index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP] #tip
#     index_finger_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP] #bottom bend
#     middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
#     middle_finger_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
#     wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
#     is_index_extended = index_finger_tip.y < index_finger_pip.y
#     is_middle_extended = middle_finger_tip.y < middle_finger_pip.y
#     ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
#     thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP] 
#     return is_index_extended and is_middle_extended and ring_finger_tip.y > thumb_tip.y
