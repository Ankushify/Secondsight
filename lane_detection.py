import numpy as np
import cv2
from collections import deque

wT, hT = 480, 240
TRACKBAR_VALS = [147, 131, 90, 216]
ROLLING_N = 10
curveList = deque(maxlen=ROLLING_N)
histMaxHistory = deque(maxlen=5)

K_ATTRACT = 0.0
K_REPEL = 0.8
REPEL_RADIUS = 0.5

def thresholding(img):
    imgHsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([10, 50, 100])
    upper = np.array([179, 255, 255])
    mask = cv2.inRange(imgHsv, lower, upper)
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask

def getWarpPoints():
    wTop, hTop, wBot, hBot = TRACKBAR_VALS
    return np.float32([
        (wTop, hTop), (wT-wTop, hTop),
        (wBot, hBot), (wT-wBot, hBot)
    ])

def warping(img, points):
    pts2 = np.float32([[0,0],[wT,0],[0,hT],[wT,hT]])
    matrix = cv2.getPerspectiveTransform(points, pts2)
    return cv2.warpPerspective(img, matrix, (wT, hT))

def getHistogram(img, minPer=0.1, region=1):
    if region == 1:
        histValues = np.sum(img, axis=0)
    else:
        histValues = np.sum(img[img.shape[0]//region:,:], axis=0)
    maxValue = np.max(histValues)
    if maxValue == 0:
        return wT//2, 0
    minValue = minPer * maxValue
    indexArray = np.where(histValues >= minValue)
    basePoint = int(np.average(indexArray))
    return basePoint, int(maxValue)

def getHistRateOfChange():
    if len(histMaxHistory) < 2:
        return 0.0
    vals = list(histMaxHistory)
    return (vals[-1] - vals[0]) / len(vals)

def artificialPotentialField(laneDeviation, obstacleDeviation=None):
    F_attract = -K_ATTRACT * laneDeviation
    F_repel = 0.0
    if obstacleDeviation is not None:
        dist = abs(laneDeviation - obstacleDeviation)
        if 0 < dist < REPEL_RADIUS:
            F_repel = K_REPEL * (1.0/dist) * np.sign(laneDeviation - obstacleDeviation)
    resultant = laneDeviation + F_attract + F_repel
    return float(max(-1.0, min(1.0, resultant)))

def getInstruction(deviation):
    a = abs(deviation)
    if a < 0.10: return "Continue Straight"
    if deviation < 0:
        if a < 0.35: return "Move Slightly Left"
        if a < 0.60: return "Move Left"
        return "Move Quickly Left"
    else:
        if a < 0.35: return "Move Slightly Right"
        if a < 0.60: return "Move Right"
        return "Move Quickly Right"

def getVibration(deviation, laneDetected):
    if not laneDetected: return 1.0
    a = abs(deviation)
    if a < 0.10: return 0.0
    if a < 0.35: return 0.25
    if a < 0.60: return 0.55
    return 0.80

def getLaneCurve(img, obstacleDeviation=None, display=0):
    imgResize = cv2.resize(img, (wT, hT))
    imgThres = thresholding(imgResize)
    points = getWarpPoints()
    imgWarp = warping(imgThres, points)

    midPoint, _ = getHistogram(imgWarp, minPer=0.5, region=4)
    basePoint, histMax = getHistogram(imgWarp, minPer=0.9)

    histMaxHistory.append(histMax)
    histRate = getHistRateOfChange()
    laneDetected = histMax > 0

    if not laneDetected:
        curveList.append(0)
        apfDeviation = 0.0
        rawDeviation = 0.0
    else:
        rawDeviation = (basePoint - wT//2) / (wT//2)
        rawDeviation = max(-1.0, min(1.0, rawDeviation))
        curveList.append(rawDeviation)
        smoothDeviation = sum(curveList) / len(curveList)
        apfDeviation = artificialPotentialField(smoothDeviation, obstacleDeviation)

    instruction = getInstruction(apfDeviation) if laneDetected else "Path Lost, Please Stop"
    vibration = getVibration(apfDeviation, laneDetected)

    return {
        "deviation":     round(apfDeviation, 4),
        "raw_deviation": round(rawDeviation, 4),
        "instruction":   instruction,
        "vibration":     round(vibration, 2),
        "lane_detected": laneDetected,
        "hist_max":      histMax,
        "hist_rate":     round(histRate, 2),
    }
