import cv2

# Load the mask image
mask = cv2.imread('C:/Users/tonvi/PycharmProjects/bitsXlaMarato/videos/mascara/30.tiff')
# Convert the image to grayscale
gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
# Threshold the image to create a binary image
threshold, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

(threshold, binary) = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Find all of the contours in the binary image
contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
# Initialize variables to store the contour with the longest vertical distance
longest_contour = None
longest_distance = 0

# Iterate through the contours
for contour in contours:
    # Calculate the vertical distance of the contour
    x, y, w, h = cv2.boundingRect(contour)
    distance = h

    # Update the longest contour and distance if necessary
    if distance > longest_distance:
        longest_contour = contour
        longest_distance = distance

print(longest_distance*0.03378378378378378378378378378378)

# Find the highest point of the
x, y, w, h = cv2.boundingRect(longest_contour)
highest_point = y

cv2.line(mask, (0, highest_point), (mask.shape[1], highest_point), (255, 0, 0), 2)

cv2.imshow('Mask with Line', mask)
cv2.waitKey(0)
cv2.destroyAllWindows()



