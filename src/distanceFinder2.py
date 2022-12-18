import cv2

# Load the mask image
image = cv2.imread('C:/Users/tonvi/PycharmProjects/bitsXlaMarato/videos/output_601_S1/mascara/58.tiff', cv2.IMREAD_GRAYSCALE)

# Convert the image to grayscale
#gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

# Threshold the image to create a binary image
#threshold, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

#(threshold, binary) = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

# Get the dimensions of the image
height, width = image.shape

most_pixels = 0
column = 0

# Iterate through the columns of the image
for i in range(width):
    # Count the number of white pixels in the current column
    white_pixels = cv2.countNonZero(image[:, i])

    if white_pixels > most_pixels:
        most_pixels = white_pixels
        column = i

    # Print the result
    # print(f'Column {i}: {white_pixels} white pixels')


print(most_pixels*0.03378378378378378378378378378378)

cv2.line(image, (column, 0), (column, height), (255, 0, 0), 2)

# Show the image with the line drawn on it
cv2.imshow('Image with Line', image)
cv2.waitKey(0)
cv2.destroyAllWindows()