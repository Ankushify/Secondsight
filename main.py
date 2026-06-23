import base64
import csv
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import lane_detection
try:
    from visualizer import visualize_frame
    VISUALIZE = True
except:
    VISUALIZE = False
import object_detection
from checkpoint_navigator import navigator, CHECKPOINTS, CHECKPOINT_MODE

app = FastAPI()

# ── CORS — allow all origins ───────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=2)

# ── CSV logging ────────────────────────────────────────────
DEVIATION_LOG = "deviation_log.csv"
BLOCKAGE_LOG  = "blockage_log.csv"

for f, headers in [
    (DEVIATION_LOG, ["timestamp","segment","deviation","direction"]),
    (BLOCKAGE_LOG,  ["timestamp","segment","duration","type"]),
]:
    if not os.path.exists(f):
        with open(f, "w", newline="") as fp:
            csv.writer(fp).writerow(headers)

def logDeviation(segment, deviation, direction):
    with open(DEVIATION_LOG, "a", newline="") as fp:
        csv.writer(fp).writerow([datetime.now().isoformat(), segment, deviation, direction])

def logBlockage(segment, duration, obj_type):
    with open(BLOCKAGE_LOG, "a", newline="") as fp:
        csv.writer(fp).writerow([datetime.now().isoformat(), segment, duration, obj_type])

# ── Request models ─────────────────────────────────────────
class DetectRequest(BaseModel):
    image: str
    frame_id: int = 0
    segment: str = "unknown"
    mode: str = "path"

class LocationRequest(BaseModel):
    lat: float
    lng: float

class RouteRequest(BaseModel):
    start_id: str
    destination_id: str

# ── Endpoints ──────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "checkpoint_mode": CHECKPOINT_MODE}


@app.post("/detect")
async def detect(req: DetectRequest):
    try:
        img_bytes = base64.b64decode(req.image)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        img       = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            return {"error": "Invalid image"}

        # Run object detection first to get obstacle position for APF
        obj_result  = object_detection.detect(img)
        obs_dev     = obj_result.get("obstacle_deviation")

        # Run lane detection with obstacle deviation for APF
        lane_result = lane_detection.getLaneCurve(img, obstacleDeviation=obs_dev)

        # Determine final instruction
        instruction = lane_result["instruction"]
        vibration   = lane_result["vibration"]

        # If obstacle will block — override instruction and max vibration
        if obj_result["will_block"]:
            instruction = obj_result["object_instruction"]
            vibration   = 1.0

        # Log deviation if significant
        if abs(lane_result["deviation"]) > 0.1:
            logDeviation(req.segment, lane_result["deviation"],
                         "left" if lane_result["deviation"] < 0 else "right")

        # Log blockage
        if obj_result["object_detected"]:
            logBlockage(req.segment, 0, obj_result["object_label"] or "unknown")

        # ── Live visualization on laptop ──────────────────
        if VISUALIZE:
            visualize_frame(img, lane_result, obj_result)

        return {
            "instruction":       instruction,
            "deviation":         lane_result["deviation"],
            "raw_deviation":     lane_result["raw_deviation"],
            "vibration":         vibration,
            "lane_detected":     lane_result["lane_detected"],
            "hist_max":          lane_result["hist_max"],
            "hist_rate":         lane_result["hist_rate"],
            "object_detected":   obj_result["object_detected"],
            "object_label":      obj_result["object_label"],
            "object_instruction":obj_result["object_instruction"],
            "will_block":        obj_result["will_block"],
            "approaching":       obj_result["approaching"],
        }

    except Exception as e:
        return {"error": str(e)}


@app.post("/location")
def location(req: LocationRequest):
    if not CHECKPOINT_MODE or not navigator.active:
        return {"checkpoint_mode": False}

    reached      = navigator.checkCheckpointReached(req.lat, req.lng)
    dest_reached = navigator.isDestinationReached()
    nxt          = navigator.getNextCheckpoint()
    cur          = navigator.getCurrentCheckpoint()
    route        = navigator.getRouteForFrontend()
    distance     = navigator.getDistanceToNext(req.lat, req.lng)
    bearing      = navigator.getBearingToNext(req.lat, req.lng)

    return {
        "checkpoint_reached":   reached,
        "destination_reached":  dest_reached,
        "current_checkpoint":   cur,
        "next_checkpoint":      nxt,
        "distance_to_next":     round(distance, 1),
        "bearing_to_next":      round(bearing, 1),
        "route":                route,
    }


@app.post("/route")
def route(req: RouteRequest):
    path = navigator.startNavigation(req.start_id, req.destination_id)
    if not path:
        return {"error": "No route found", "route_display": []}
    return {
        "route":         path,
        "route_display": navigator.getRouteForFrontend(),
        "hops":          len(path) - 1,
    }


@app.get("/destinations")
def destinations():
    major = [cp for cp in CHECKPOINTS if cp["type"] == "major"]
    return {"destinations": major}


@app.get("/checkpoints")
def checkpoints():
    # Returns all checkpoints for source location matching
    return {"checkpoints": CHECKPOINTS}


@app.get("/heatmap")
def heatmap():
    data = []
    if os.path.exists(DEVIATION_LOG):
        with open(DEVIATION_LOG, "r") as fp:
            reader = csv.DictReader(fp)
            data = list(reader)
    return {"data": data, "count": len(data)}
