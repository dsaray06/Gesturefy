import csv
import os
import pickle
from sklearn.neighbors import KNeighborsClassifier

# Load feature vectors from a CSV, skip if missing
def load_features(path):
    if not os.path.isfile(path):
        print(f"Warning: '{path}' not found, skipping.")
        return []
    features = []
    with open(path, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            features.append([float(val) for val in row])
    return features

# Prepare training data
X, y = [], []
gestures = ['open_fist', 'closed_fist', 'thumbs_up','peace_sign','pointing_up','pointing_down','pointing_left','pointing_right','no_gesture']
for gesture in gestures:
    csv_file = f'data/{gesture}.csv'
    feats = load_features(csv_file)
    for feat in feats:
        X.append(feat)
        y.append(gesture)

if not X:
    print("No training data found. Run collect_gesture_data.py first.")
    exit(1)

# Train classifier
model = KNeighborsClassifier(n_neighbors=3)
model.fit(X, y)

# Save model
with open('gesture_model.pkl', 'wb') as f:
    pickle.dump(model, f)
print("Model saved to gesture_model.pkl")