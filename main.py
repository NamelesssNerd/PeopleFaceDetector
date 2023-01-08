import cv2 as cv
import argparse
import logging
import os
import numpy
import time
from typing import Tuple, List
from enum import Enum, auto

VGA_HORIZONTAL_SIZE: Tuple[int, int] = (640, 480)
VGA_VERTICAL_SIZE: Tuple[int, int] = tuple(reversed(VGA_HORIZONTAL_SIZE))

class Point:
    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x: int = x
        self.y: int = y

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

class Region:
    def __init__(self, x: int = 0, y: int = 0, w: int = 0, h: int = 0) -> None:
        self.x: int = int(x)
        self.y: int = int(y)
        self.w: int = int(w)
        self.h: int = int(h)

    def get_area(self) -> int:
        return (self.w * self.h)

    def get_center(self) -> Point:
        return Point(self.x + self.w // 2, self.y + self.h // 2)

class Orientation(Enum):
    VERTICAL: int = auto()
    HORIZONTAL: int = auto()
    SQUARE: int = auto()

    @staticmethod
    def get_orientation(img: numpy.ndarray):
        w: int = img.shape[1]
        h: int = img.shape[0]
        if w > h:
            return Orientation.HORIZONTAL
        elif h > w:
            return Orientation.VERTICAL
        else:
            return Orientation.SQUARE

class Classifier:
    def __init__(self, model_name: str, video_source: str = None, image = None) -> None:

        self.model_cascade: cv.CascadeClassifier = cv.CascadeClassifier()
        self.model_cascade.load(cv.samples.findFile(model_name))
        self.video_source: str = video_source  
        self.image: str = image  
        self.start_time_int: int = None 
        self.times: numpy.array = None  
        self.times_index: int = 0  
        self.main_window_created: bool = False
    
    def __start_time(self) -> None:
     
        self.start_time_int = time.time()

    def __end_time(self) -> None:
   
        logging.info(f"time for 1 frame classification {time.time() - self.start_time_int}")
        if not str.isnumeric(self.video_source):  # If the video source is not a cam
            self.times[self.times_index] = time.time() - self.start_time_int
            self.times_index += 1
    
    def __draw_ellipse(self, frame: numpy.ndarray, region: Region) -> numpy.ndarray:
       
        return cv.ellipse(frame, region.get_center().to_tuple(), (region.w // 2, region.h // 2), 0, 0, 360, (0, 255, 0), 4)
    
    def detect(self, frame: numpy.ndarray, processed_frame_preview: bool = False) -> List[Region]:
        self.__start_time()
        frame_gray: numpy.ndarray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        orientation: Orientation = Orientation.get_orientation(frame)
        if orientation is Orientation.VERTICAL:
            size: Tuple[int, int] = VGA_VERTICAL_SIZE
        elif orientation is Orientation.HORIZONTAL:
            size: Tuple[int, int] = VGA_HORIZONTAL_SIZE
        downscaled_frame_gray: numpy.ndarray = cv.resize(frame_gray, dsize = size, interpolation = cv.INTER_AREA)
        downscaled_frame_gray: numpy.ndarray = cv.equalizeHist(downscaled_frame_gray)
        obj_list = self.model_cascade.detectMultiScale(downscaled_frame_gray, scaleFactor = 1.2)
        self.__end_time()
        original_frame_regions_list: List[Region] = list()
        processed_frame_regions_list: List[Region] = list()
        scale_factor_x: float = frame.shape[1] / size[0]  
        scale_factor_y: float = frame.shape[0] / size[1]  
        for (x, y, w, h) in obj_list:
            processed_frame_regions_list.append(Region(x, y, w, h))
            original_frame_regions_list.append(Region(x*scale_factor_x, y*scale_factor_y, w*scale_factor_x, h*scale_factor_y))
        if processed_frame_preview:
            self.display(downscaled_frame_gray, processed_frame_regions_list, 'Processed frame preview')
        return original_frame_regions_list

    def display(self, frame: numpy.ndarray, regions: List[Region], window_title: str = 'OpenCV show image', scale_factor: float = 1.0) -> None:
        for region in regions:
            frame: numpy.ndarray = self.__draw_ellipse(frame, region)
        cv.imshow(window_title, scale(frame, scale_factor))
        if not self.main_window_created:
            cv.moveWindow(window_title, 100, 100)
            self.main_window_created = True

    def detect_and_display(self, frame: numpy.ndarray, processed_frame_preview: bool) -> None:
        regions: List[Region] = self.detect(frame, processed_frame_preview)
        self.display(frame, regions, 'Face detection By : NameLessNerd', 1.5)  

    def start(self, processed_frame_preview: bool) -> None: 
      
        if self.image:
            img: numpy.ndarray = cv.imread(self.image)
            self.detect_and_display(img, processed_frame_preview)
            if cv.waitKey(0) == 27:  
                return

        cap = cv.VideoCapture(int(self.video_source) if str.isnumeric(self.video_source) else self.video_source)
        frames_number: int = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
        if frames_number > 0:  
            self.times = numpy.empty(frames_number, dtype='f', order='C')
        if not cap.isOpened():
            logging.error("Camera video stream can't be opened")
            exit(1)
        while True:
            ret, frame = cap.read()
            if frame is None:
                break
            self.detect_and_display(frame, processed_frame_preview)
            if cv.waitKey(1) == 27: 
                break

        if frames_number > 0:
            logging.info(f"Average time needed to classify each frame {numpy.average(self.times[:self.times_index])}")
            logging.info(f"Max time needed to classify each frame {numpy.amax(self.times[:self.times_index])}")
            logging.info(f"Min time needed to classify each frame {numpy.amin(self.times[:self.times_index])}")

def scale(img: numpy.ndarray, scale_factor: float) -> numpy.ndarray:  
    scaled_h: int = int(img.shape[0] * scale_factor)
    scaled_w: int = int(img.shape[1] * scale_factor)
    return cv.resize(img, (scaled_w, scaled_h))

def main(video_source: str, image: str, model: str, processed_frame_preview: bool) -> None:
    classifier = Classifier(model, video_source = video_source, image = image)
    classifier.start(processed_frame_preview)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='Cascade classifier model name', type=str, default='haarcascade_frontalface_alt.xml')
    parser.add_argument('--source', help='Camera number or video filename', type=str, default='0')
    parser.add_argument('--image', help='Image filename', type=str)
    parser.add_argument('--processed-frame-preview', help='Show the preview of processed frame', default=False, action='store_true')
    args = parser.parse_args()
    main(args.source, args.image, os.path.join(os.path.split(os.path.abspath(cv.__file__))[0], 'data', args.model), args.processed_frame_preview)
