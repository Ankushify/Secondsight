import numpy as np
import cv2

def thresholding(img):
    imgHsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lowerYellow = np.array([18, 105, 152])
    upperYellow = np.array([179, 255, 255])
    maskYellow = cv2.inRange(imgHsv, lowerYellow, upperYellow)
    return maskYellow

def warping(img, points, w, h):
    pts1 = np.float32(points)
    pts2 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    imgWarp = cv2.warpPerspective(img, matrix, (w, h))
    return imgWarp

def getHistogram(img, minPer=0.1, region=1):
    if region == 1:
        histValues = np.sum(img, axis=0)
    else:
        histValues = np.sum(img[img.shape[0] // region:, :], axis=0)

    maxValue = np.max(histValues)

    # if no lane detected at all return center
    if maxValue == 0:
        return img.shape[1] // 2

    minValue = minPer * maxValue
    indexArray = np.where(histValues >= minValue)
    basePoint = int(np.average(indexArray))
    return basePoint
