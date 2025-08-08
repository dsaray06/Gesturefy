import csv
import time
import cv2
from hand_gesture_detection import GestureRecognizer

# Initialize detector and camera
detector = GestureRecognizer()
cap = cv2.VideoCapture(0)

# List of gesture names (matching your training labels)
gestures = ['open_fist', 'closed_fist', 'thumbs_up','peace_sign','pointing_up','pointing_down','pointing_left','pointing_right','no_gesture']
duration = 5  # seconds to record per gesture

for gesture in gestures:
    print(f"Get ready to record '{gesture}' for {duration}s. Press Enter to start...")
    input()
    csv_path = f'data/{gesture}.csv'
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        start = time.time()
        while time.time() - start < duration:
            ret, frame = cap.read()
            if not ret:
                break
            feats = detector.process_frame(frame)
            if feats:
                writer.writerow(feats)
            # Optional: show frame (comment out if not needed)
            # cv2.imshow('Recording', frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
    print(f"Saved samples for '{gesture}' → {csv_path}")

cap.release()
cv2.destroyAllWindows()
print("Data collection complete.")