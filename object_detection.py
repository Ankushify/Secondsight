import numpy as np
import cv2
from ultralytics import YOLO
from collections import deque

model = YOLO('yolov8n.pt')
WATCH_CLASSES = {'person','bicycle','car','motorcycle','truck','bus'}
wT, hT = 480, 240
LANE_LEFT  = wT * 0.25
LANE_RIGHT = wT * 0.75

class KalmanTracker:
    def __init__(self, obj_id, cx, cy):
        self.id = obj_id
        self.lost = 0
        self.MAX_LOST = 8
        self.label = None
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.transitionMatrix = np.array([
            [1,0,1,0],[0,1,0,1],[0,0,1,0],[0,0,0,1]
        ], dtype=np.float32)
        self.kf.measurementMatrix = np.array([
            [1,0,0,0],[0,1,0,0]
        ], dtype=np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5
        self.kf.errorCovPost = np.eye(4, dtype=np.float32)
        self.kf.statePost = np.array([[cx],[cy],[0.],[0.]], dtype=np.float32)

    def predict(self):
        return self.kf.predict()

    def update(self, cx, cy):
        self.lost = 0
        self.kf.correct(np.array([[cx],[cy]], dtype=np.float32))

    def getState(self):
        s = self.kf.statePost
        return float(s[0]), float(s[1]), float(s[2]), float(s[3])

    def willIntersectLane(self, steps=15):
        x, y, vx, vy = self.getState()
        for step in range(1, steps+1):
            fx = x + vx * step
            if LANE_LEFT <= fx <= LANE_RIGHT:
                return True, step
        return False, -1

class MultiTracker:
    def __init__(self):
        self.trackers = {}
        self.next_id = 0
        self.DIST_THRESH = 60

    def update(self, detections):
        for t in self.trackers.values():
            t.predict()
        matched = set()
        for cx, cy, label, conf in detections:
            best_id, best_dist = None, self.DIST_THRESH
            for tid, tr in self.trackers.items():
                tx, ty, _, _ = tr.getState()
                d = np.sqrt((cx-tx)**2 + (cy-ty)**2)
                if d < best_dist:
                    best_dist, best_id = d, tid
            if best_id is not None:
                self.trackers[best_id].update(cx, cy)
                self.trackers[best_id].label = label
                matched.add(best_id)
            else:
                t = KalmanTracker(self.next_id, cx, cy)
                t.label = label
                self.trackers[self.next_id] = t
                matched.add(self.next_id)
                self.next_id += 1
        for tid in list(self.trackers.keys()):
            if tid not in matched:
                self.trackers[tid].lost += 1
                if self.trackers[tid].lost > self.trackers[tid].MAX_LOST:
                    del self.trackers[tid]
        return self.trackers

tracker = MultiTracker()
frame_count = 0
YOLO_SKIP = 3
last_detections = []

def normX(px):
    return (px - wT/2) / (wT/2)

def detect(img):
    global frame_count, last_detections
    frame_count += 1

    if frame_count % YOLO_SKIP == 0:
        results = model(img, conf=0.45, verbose=False)
        raw = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = model.names[cls_id]
                if label not in WATCH_CLASSES: continue
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                cx, cy = (x1+x2)//2, (y1+y2)//2
                raw.append((cx, cy, label, float(box.conf[0])))
        last_detections = raw

    active = tracker.update(last_detections)

    obstacle_detected = False
    obstacle_instruction = None
    obstacle_deviation = None
    will_block = False
    frames_until_block = -1
    closest_label = None

    for tid, t in active.items():
        x, y, vx, vy = t.getState()
        in_lane = LANE_LEFT <= x <= LANE_RIGHT
        will_intersect, eta = t.willIntersectLane(steps=15)
        lane_centre = wT / 2
        approaching = ((x < lane_centre and vx > 0) or (x > lane_centre and vx < 0)) and abs(vx) > 0.8

        if in_lane or (will_intersect and approaching):
            obstacle_detected = True
            will_block = True
            frames_until_block = eta if will_intersect else 0
            obstacle_deviation = normX(x)
            closest_label = t.label
            speed = np.sqrt(vx**2 + vy**2)

            if in_lane:
                if speed < 1.0:
                    obstacle_instruction = "Obstacle on path, please wait"
                elif approaching:
                    obstacle_instruction = "Obstacle approaching, please stop"
                else:
                    obstacle_instruction = "Obstacle moving away, wait a moment"
            else:
                obstacle_instruction = "Obstacle will enter path, slow down"
            break

    return {
        "object_detected":    obstacle_detected,
        "object_label":       closest_label,
        "object_instruction": obstacle_instruction,
        "obstacle_deviation": obstacle_deviation,
        "will_block":         will_block,
        "frames_until_block": frames_until_block,
        "approaching":        approaching if obstacle_detected else False,
    }
