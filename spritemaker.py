from pathlib import Path
from PIL import Image
import numpy as np
import sys
import os


def createSpritesheet(datasetPath, labelsNames, width, height):
    # print(Path(__file__).parent.absolute())
    # Constants
    TRAINING_PATH = datasetPath+'/spritesheet/'
    # SPRITE_SIZE = 60
    print(TRAINING_PATH, file=sys.stderr)

    # Initialization
    x_data = []
    y_data = []
    # final_image = np.array([])
    y_offset = 0
    imageCount = 0
    imageFiles = []
    for image_file in Path(TRAINING_PATH).glob("**/*.jpg"):
        imageCount += 1
        imageFiles.append(image_file)
    for image_file in Path(TRAINING_PATH).glob("**/*.png"):
        imageCount += 1
        imageFiles.append(image_file)
    for image_file in Path(TRAINING_PATH).glob("**/*.jpeg"):
        imageCount += 1
        imageFiles.append(image_file)

    print(imageCount, file=sys.stderr)
    new_im = Image.new('RGB', (width*height, imageCount))

    labels = [0]*(len(labelsNames))
    # print(len(sys.argv))

    # Load the training sprite by looping over every image file
    for image_file in imageFiles:

        # Load the current image file
        src_image = Image.open(image_file)
        # make it smaller
        downsized = src_image.resize((width, height))

        # get 1px high version
        pixels = list(downsized.getdata())
        smoosh = Image.new('RGB', (width * height, 1))
        smoosh.putdata(pixels)

        # store image
        x_data.append(smoosh)
        folderName = str(image_file.parent.absolute(
        ))[-(len(str(image_file.parent.absolute()))-str(image_file.parent.absolute()).rindex('/')-1):]
        # print(folderName)
        # for i in image_file.stem:
        #     print(i)
        # print(sys.argv[2])
        # Use image path to build our answer key
        for i in range(1, len(labelsNames)+1):
            if folderName == labelsNames[i-1]:
                y_data.append(i)
                labels[i-1] += 1

    print(labels)

    #  randomize X and Y the same way before making data

    assert len(y_data) == len(x_data)
    p = np.random.permutation(len(y_data))
    npy = np.array(y_data)
    shuffled_y = npy[p].tolist()

    one_hot_y = []
    # Build the data image and 1-hot encoded answer array
    for idx in p:
        # build master sprite 1 pixel down at a time
        new_im.paste(x_data[idx], (0, y_offset))

        for i in range(1, len(labelsNames)+1):
            if shuffled_y[y_offset] == i:
                for j in range(1, len(labelsNames)+1):
                    if j == i:
                        one_hot_y.append(1)
                    else:
                        one_hot_y.append(0)
        # build 1-hot encoded answer key

        y_offset += 1

    # Save answers file (Y)
    newFile = open(datasetPath+'/spritesheet/labels.bin', "wb")
    newFileByteArray = bytearray(one_hot_y)
    bytesWrite = newFile.write(newFileByteArray)
    # should be num classes * original answer key size
    assert bytesWrite == ((len(labelsNames)) * len(y_data))

    # Save Data Sprite (X)
    # new_im = new_im.convert("RGBA")

    # pixdata = new_im.load()

    # Clean the background noise, if color != white, then set to black.
    # change with your color

    # for y in range(new_im.size[1]):
    #     for x in range(new_im.size[0]):
    #         if pixdata[x, y][0] == 255:
    #             pixdata[x, y] = (255, 255, 255)

    new_im.save(datasetPath+'/spritesheet/data.jpg')
