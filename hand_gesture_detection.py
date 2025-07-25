import mediapipe as mp
import math

# Initialize MediaPipe hands module
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

def is_closed_fist(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
    wristCor = (wrist.x, wrist.y)
    indexCor = (index_finger_tip.x, index_finger_tip.y)
    middleCor = (middle_finger_tip.x, middle_finger_tip.y)
    ringCor = (ring_finger_tip.x, ring_finger_tip.y)
    thumbCor = (thumb_tip.x, thumb_tip.y)
    
    relVar = .24
    checkOne = math.dist(indexCor, wristCor) < relVar
    checkTwo = math.dist(middleCor, wristCor) < relVar
    checkThree = math.dist(ringCor, wristCor) < relVar
    checkFour = math.dist(thumbCor, wristCor) < .32
    
    return checkOne and checkTwo and checkThree and checkFour

def is_open_fist(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    
    wristCor = (wrist.x, wrist.y)
    indexCor = (index_finger_tip.x, index_finger_tip.y)
    middleCor = (middle_finger_tip.x, middle_finger_tip.y)
    ringCor = (ring_finger_tip.x, ring_finger_tip.y)
    
    relVar = .2
    checkOne = math.dist(indexCor, wristCor) > relVar
    checkTwo = math.dist(middleCor, wristCor) > relVar
    checkThree = math.dist(ringCor, wristCor) > relVar
    checkFour = math.dist(middleCor, indexCor) < 0.2
    
    return checkOne and checkTwo and checkThree and checkFour

def is_pointing_right(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    return index_finger_tip.x > wrist.x and abs(index_finger_tip.y - wrist.y) < 0.4

def is_pointing_left(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    return index_finger_tip.x < wrist.x and abs(index_finger_tip.y - wrist.y) < 0.4

def is_pointing_up(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    return index_finger_tip.y < wrist.y and abs(index_finger_tip.x - wrist.x) < 0.2

def is_pointing_down(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    return index_finger_tip.y > wrist.y and abs(index_finger_tip.x - wrist.x) < 0.2

def is_thumbs_up(hand_landmarks):
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    return thumb_tip.y < thumb_ip.y and thumb_tip.y < index_finger_tip.y
