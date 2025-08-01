import mediapipe as mp
import math

# Initialize MediaPipe hands module
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.8, min_tracking_confidence=0.9)

class GestureRecognizer:
    def recognize(self, hand_landmarks):
        if is_peace_sign(hand_landmarks):
            return "peace_sign"
        elif is_closed_fist(hand_landmarks):
            return "closed_fist"
        elif is_open_fist(hand_landmarks):
            return "open_fist"
        elif is_thumbs_up(hand_landmarks):
            return "thumbs_up"
        elif is_pointing_up(hand_landmarks):
            return "pointing_up"
        elif is_pointing_down(hand_landmarks):
            return "pointing_down"
        elif is_pointing_left(hand_landmarks):
            return "pointing_left"
        elif is_pointing_right(hand_landmarks):
            return "pointing_right"
        else:
            return None


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
    index_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

    horizontal_distance = index_finger_tip.x - wrist.x
    vertical_alignment = abs(index_finger_tip.y - wrist.y)

    # More lenient: allow slightly greater vertical variance
    return horizontal_distance > 0.12 and vertical_alignment < 0.5 and \
           index_finger_tip.x > index_finger_mcp.x

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
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

    # Stricter: ensure thumb is clearly above index and bent upwards
    is_thumb_above_ip = thumb_tip.y < thumb_ip.y
    is_thumb_above_index = thumb_tip.y < index_finger_tip.y - 0.05
    is_thumb_outward = abs(thumb_tip.x - wrist.x) < 0.2

    return is_thumb_above_ip and is_thumb_above_index and is_thumb_outward

def is_peace_sign(hand_landmarks):
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP] #tip
    index_finger_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP] #bottom bend
    middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_finger_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    is_index_extended = index_finger_tip.y < index_finger_pip.y
    is_middle_extended = middle_finger_tip.y < middle_finger_pip.y
    ring_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP] 
    return is_index_extended and is_middle_extended and ring_finger_tip.y > thumb_tip.y
