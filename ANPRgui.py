from io import BytesIO
from pathlib import Path

import cv2 as cv
import easyocr
import imutils
import numpy as np
import PySimpleGUI as sg
from PIL import Image, UnidentifiedImageError


def image_to_data(im):
    """
    Image object to bytes object.
    : Parameters
      im - Image object
    : Return
      bytes object.
    """
    with BytesIO() as output:
        im.save(output, format="PNG")
        data = output.getvalue()
    return data

def Process(OGimg):
    # Resize image
    proImg = imutils.resize(OGimg, width=500)
    # Grayscale image
    gray = cv.cvtColor(proImg, cv.COLOR_BGR2GRAY)
    # cv.imshow('Grayscale', gray)
    
    # De-noising 
    gray = cv.bilateralFilter(gray, 11, 17, 17)

    # Find edges
    edged = cv.Canny(gray, 170, 200)
    # cv.imshow('Canny edge', edged)

    # Find contours based on Edges
    cnts, new  = cv.findContours(edged.copy(), cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)

    # Sort contours based on their area keeping minimum required area as '30' (anything smaller than this will not be considered)
    cnts = sorted(cnts, key = cv.contourArea, reverse = True)[:30]
    NumberPlateCnt = None # we currently have no Number plate contour
    
    img1 = proImg.copy()
    cv.drawContours(img1, cnts, -1, (0,255,0), 2)
    cv.imshow('Contours', img1)

    try:
        # loop over our contours to find the best possible approximate contour of number plate
        for c in cnts:
            peri = cv.arcLength(c, True) # Calculates a contour perimeter or a curve length
            approx = cv.approxPolyDP(c, 0.02 * peri, True) #Approximates a polygonal curve(s) with precision of 0.02
            if len(approx) == 4:  # Select the contour with 4 corners
                NumberPlateCnt = approx #This is our approx Number Plate Contour

                # Crop those contours and store it in Cropped Images folder
                x, y, w, h = cv.boundingRect(c) #This will find out co-ord for plate
                new_img = gray[y:y + h, x:x + w] #Create new image
                cv.imwrite('cropped plate.png', new_img) #Store new image
                break
    
        # Drawing the selected contour on the original image
        cv.drawContours(proImg, [NumberPlateCnt], -1, (0,255,0), 3)
    except cv.error:
        print("No plate found")
        window['CHECK'].update("No plate found !")

    return proImg

def ReadPlate(cropped):    
    # Use EasyOCR to read text on plate
    reader = easyocr.Reader(['en']) 
    ocr_result = reader.readtext(cropped)
    #Put all lines to a list and convert back to string
    list = [] 
    for result in ocr_result:
        list.append(result[1]) 
    read_result = '\n'.join(list)   

    return read_result

width, height = size = 700, 400    # Scale image

layout1 = [
    [
        sg.Text('WEBCAM', size=(60, 1), 
        justification="center"),
        sg.Radio("OFF", "Radio", True, size=(10, 1), key="-CAM OFF-"),
        sg.Radio("ON", "Radio", size=(10, 1), key="-CAM ON-"),
        sg.Button("Cam 1", size=(10, 1), key="-CAM 0-"),
        sg.Button("Cam 2", size=(10, 1), key="-CAM 1-")
        ],
    [
        sg.Button('Process Cam', size=(15,1)), 
        sg.Text('', expand_x=True, key='CHECK')
        ],
    [
        sg.Image(filename="", key="FRAME", size=size), 
        sg.Text("RESULT:"), 
        sg.Image(key= "CroppedCAM"), 
        sg.Text('', key='NumberCAM')
        ]
]

layout2 = [
    [
        sg.Text("Choose your image file: ")
        ],
    [
        sg.Input(expand_x=True, disabled=True, key='File'), sg.Button('Browse')
        ],
    [
        sg.Text('', expand_x=True, key='Status')
        ],
    [
        sg.Button('Process Image', size=(15,1))
        ],
    [
        sg.Image(size=size, background_color='black', key = "IMAGE"), 
        sg.Text("RESULT:"), 
        sg.Image(key= "Cropped"), 
        sg.Text('', key='Number')
        ]
]
sg.theme("DarkGrey14")
layout = [   
    [
        sg.Column(layout1, visible=False, key='-COL1-'), 
        sg.Column(layout2, key='-COL2-')
        ],
    [
        sg.Button('Use Image File', size=(15,1)), 
        sg.Button('Use Webcam', size=(15,1)), 
        sg.Button('Exit', size=(10,1), pad=((300,0),(0,0)))
        ]
]

window = sg.Window("License Plate Regconition", layout)

camCount = 0

def main():
    cap = np.void
    while True:
        event, values = window.read(timeout=20)
        if event == "Exit" or event == sg.WIN_CLOSED:
            break  

        if cap != np.void:
            _, frame = cap.read()
            try:
                imgbytes = cv.imencode(".png", frame)[1].tobytes()
                window["FRAME"].update(data=imgbytes, size=size)
            except cv.error:
                pass
        
        if event == "Use Image File":
            cap = np.void
            window[f'-COL{1}-'].update(visible=False)
            window[f'-COL{2}-'].update(visible=True)

        elif event == "Use Webcam":           
            window[f'-COL{2}-'].update(visible=False)
            window[f'-COL{1}-'].update(visible=True)  

        if values["-CAM OFF-"]:
            camCount = 0
            cap = np.void
            window["FRAME"].update(data=cv.imencode(".png", np.zeros((height,width,3), np.uint8))[1].tobytes(), size=size)

        elif values["-CAM ON-"] and event == "-CAM 0-":            
            if camCount == -1:
                pass
            else:
                camCount = 0
                camCount = camCount - 1
                cap = cv.VideoCapture(0)

        elif values["-CAM ON-"] and event == "-CAM 1-":            
            if camCount == 1:
                pass
            else:
                camCount = 0
                camCount = camCount + 1
                cap = cv.VideoCapture(1)

        if event == "Process Cam":
            frame1 = Process(frame)
            cropframe = cv.imread('cropped plate.png')
            text = ReadPlate(cropframe)
            
            print("Number is:\n", text)
            window['NumberCAM'].update(text)
            
            framebytes = cv.imencode(".png",frame1)[1].tobytes()
            cropbyte = cv.imencode(".png", cropframe)[1].tobytes()

            window['FRAME'].update(data=framebytes)
            window['CroppedCAM'].update(data=cropbyte)
        
        elif event == "Browse":
            path = sg.popup_get_file("Choose Image",None,'','*.png', no_window=True)
            if path == '':
                continue
            window['Status'].update('')
            window['File'].update(path)
            if not Path(path).is_file():
                window['Status'].update('Image file not found !')
                continue
            try:
                img = Image.open(path)
            except UnidentifiedImageError:
                window['Status'].update("Cannot identify image file !")
                continue        
            w, h = img.size
            scale = min(width/w, height/h, 1)
            if scale != 1:
                img = img.resize((int(w*scale), int(h*scale)))            

            data = image_to_data(img)
            window['IMAGE'].update(data=data, size=size)
            
        elif event == "Process Image":
            try:
                imgFile = Process(cv.imread(path))
                crop = cv.imread('cropped plate.png')
                text = ReadPlate(crop)

                print("Number is:\n", text)
                window['Number'].update(text)         

                imgbytes = cv.imencode(".png", imgFile)[1].tobytes()                
                crop = imutils.resize(crop, height=200, width=300)
                cropbytes = cv.imencode(".png", crop)[1].tobytes()

                window['IMAGE'].update(data=imgbytes, size=size)
                window['Cropped'].update(data=cropbytes)
            except NameError:
                window['Status'].update("No image selected")
                continue


if __name__=="__main__":
    main()

window.close()