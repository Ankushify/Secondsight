import csv
import os
from datetime import datetime

DEVIATION_LOG = "deviation_log.csv"
BLOCKAGE_LOG  = "blockage_log.csv"

# Create files with headers if they don't exist
def initLogs():
    if not os.path.exists(DEVIATION_LOG):
        with open(DEVIATION_LOG, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "segment", "deviation", "direction"])

    if not os.path.exists(BLOCKAGE_LOG):
        with open(BLOCKAGE_LOG, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "segment", "duration_seconds", "type"])

def logDeviation(segment, deviation, direction):
    """Log a deviation event."""
    if abs(deviation) < 0.1:
        return  # Don't log if user is on path
    with open(DEVIATION_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%H:%M:%S"),
            segment,
            round(deviation, 3),
            direction
        ])

def logBlockage(segment, duration, blockage_type):
    """Log a blockage event."""
    with open(BLOCKAGE_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%H:%M:%S"),
            segment,
            duration,
            blockage_type
        ])

def getLogs():
    """Read both logs and return as dict for upload."""
    deviations = []
    blockages  = []

    if os.path.exists(DEVIATION_LOG):
        with open(DEVIATION_LOG, "r") as f:
            deviations = list(csv.DictReader(f))

    if os.path.exists(BLOCKAGE_LOG):
        with open(BLOCKAGE_LOG, "r") as f:
            blockages = list(csv.DictReader(f))

    return {"deviations": deviations, "blockages": blockages}

def clearLogs():
    """Clear logs after upload."""
    initLogs()
    open(DEVIATION_LOG, "w").close()
    open(BLOCKAGE_LOG,  "w").close()
    initLogs()
