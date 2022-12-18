import cv2

# Load the mask image
mask = cv2.imread('C:/Users/tonvi/PycharmProjects/bitsXlaMarato/videos/mascara/51.tiff')

# Convert the image to grayscale
gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

# Threshold the image to create a binary image
threshold, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

(threshold, binary) = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Get the dimensions of the image
height, width = binary.shape

most_pixels = 0
column = 0

# Iterate through the columns of the image
for i in range(width):
    # Count the number of white pixels in the current column
    white_pixels = cv2.countNonZero(binary[:, i])

    if white_pixels > most_pixels:
        most_pixels = white_pixels
        column = i

    # Print the result
    # print(f'Column {i}: {white_pixels} white pixels')


print(most_pixels*0.03378378378378378378378378378378)

cv2.line(mask, (column, 0), (column, height), (255, 0, 0), 2)

# Show the image with the line drawn on it
cv2.imshow('Image with Line', mask)
cv2.waitKey(0)
cv2.destroyAllWindows()