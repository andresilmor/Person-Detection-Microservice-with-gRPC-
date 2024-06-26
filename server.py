# server.py
# we will use asyncio to run our service
import asyncio
import grpc

from io import BytesIO 
from PIL import Image, ImageOps
import cv2
import numpy as np
from numpy import random
import base64
import os

from ms_personDetection_pb2_grpc import PersonDetectionService, add_PersonDetectionServiceServicer_to_server
from ms_personDetection_pb2 import PersonDetectionRequest, PersonDetectionInferenceReply, DetectionBox

import logging
from time import perf_counter


from utils.torch_utils import select_device, load_classifier, time_synchronized, TracedModel
import torch
from utils.plots import plot_one_box
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from models.experimental import attempt_load

logging.basicConfig(level=logging.INFO)

class PersonDetectionService(PersonDetectionService):

    def __init__(self) -> None:
        self.model = attempt_load("weights/yolov7x.pt", map_location= 'cpu') 
        super().__init__()

    async def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True, stride=32):
        # Resize and pad image while meeting stride-multiple constraints
        shape = img.shape[:2]  # current shape [height, width]
        
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        if not scaleup:  # only scale down, do not scale up (for better test mAP)
            r = min(r, 1.0)

        # Compute padding
        ratio = r, r  # width, height ratios
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - \
            new_unpad[1]  # wh padding
        if auto:  # minimum rectangle
            dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
        elif scaleFill:  # stretch
            dw, dh = 0.0, 0.0
            new_unpad = (new_shape[1], new_shape[0])
            ratio = new_shape[1] / shape[1], new_shape[0] / \
                shape[0]  # width, height ratios

        dw /= 2  # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad:  # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(
            img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
        return img, ratio, (dw, dh)


    async def Inference(self, request: PersonDetectionRequest, context) -> PersonDetectionInferenceReply:
        start = perf_counter()

        npimg = cv2.imdecode(np.frombuffer(request.image, np.uint8), -1)

        cv2.rectangle(npimg, ( 0, 0 ), (200, 856) , (0, 0, 0), -1) # |o
        cv2.rectangle(npimg, ( 1300, 0 ), (1504, 856) , (0, 0, 0), -1) # o|
        cv2.rectangle(npimg, ( 200, 720 ), (1300, 856) , (0, 0, 0), -1) # _

        #cv2.imwrite(os.getcwd() + "/frame4.png",npimg)
        
        classes_to_filter = ["bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
                         "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table", "toilet", "mouse", "remote", "keyboard", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]  # You can give list of classes to filter by name, Be happy you don't have to put class number. ['train','person' ]

        opt = {

            # Path to weights file default weights are for nano model
            "weights": "weights/yolov7x.pt",
            "yaml": "data/coco.yaml",
            "img-size": 640,  # default image size
            "conf-thres": 0.25,  # confidence threshold for inference.
            "iou-thres": 0.45,  # NMS IoU threshold for inference.
            "device": 'cpu',  # device to run our model i.e. 0 or 0,1,2,3 or cpu
            "classes": classes_to_filter  # list of classes to filter or None

        }

        with torch.no_grad():
            weights, imgsz = opt['weights'], opt['img-size']
          
            device = select_device(opt['device'])
            half = device.type != 'cpu'
            model = self.model  # load FP32 model
            
            stride = int(model.stride.max())  # model stride
            imgsz = check_img_size(imgsz, s=stride)  # check img_size
            if half:
                model.half()

            names = model.module.names if hasattr(model, 'module') else model.names
            colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]
            if device.type != 'cpu':
                model(torch.zeros(1, 3, imgsz, imgsz).to(
                    device).type_as(next(model.parameters())))

            img = await self.letterbox(npimg, imgsz, stride=stride)
            img = img[0]
            img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
            img = np.ascontiguousarray(img)
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            t1 = time_synchronized()
            pred = model(img, augment=False)[0]

            # Apply NMS
            classes = None
            if opt['classes']:
                classes = []
                for class_name in opt['classes']:
                    classes.append(names.index(class_name))

            if classes:
                classes = [i for i in range(len(names)) if i not in classes]

            pred = non_max_suppression(
                pred, opt['conf-thres'], opt['iou-thres'], classes=classes, agnostic=False)
            t2 = time_synchronized()
            
            persons = []
            #persons = {"persons": []}
            #filtering = {"filter": []}
            filter = []
            for i, det in enumerate(pred):
                s = ''
                s += '%gx%g ' % img.shape[2:]  # print string
                gn = torch.tensor(npimg.shape)[[1, 0, 1, 0]]
                if len(det):
                    det[:, :4] = scale_coords(
                        img.shape[2:], det[:, :4], npimg.shape).round()

                    for c in det[:, -1].unique():
                        n = (det[:, -1] == c).sum()  # detections per class
                        # add to string
                        s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "

                    for *xyxy, conf, cls in reversed(det):
                        label = f'{names[int(cls)]} {conf:.2f}'
                        plot_one_box(xyxy, npimg, label=label,
                                    color=colors[int(cls)], line_thickness=3)
                        if (label.startswith(('laptop', 'cell', 'tv'))):
                            detectionBox = DetectionBox()
                            detectionBox.point["x1"] = int(np.array(xyxy)[0])
                            detectionBox.point["y1"] = int(np.array(xyxy)[1])
                            detectionBox.point["x2"] = int(np.array(xyxy)[2])
                            detectionBox.point["y2"] = int(np.array(xyxy)[3])
                            filter.append(detectionBox)
                            
                            #filtering["filter"].append({"box": {"x1": int(np.array(xyxy)[0]), "y1": int(np.array(
                            #    xyxy)[1]), "x2": int(np.array(xyxy)[2]), "y2": int(np.array(xyxy)[3])}})

                        else:
                            detectionBox = DetectionBox()
                            detectionBox.point["x1"] = int(np.array(xyxy)[0])
                            detectionBox.point["y1"] = int(np.array(xyxy)[1])
                            detectionBox.point["x2"] = int(np.array(xyxy)[2])
                            detectionBox.point["y2"] = int(np.array(xyxy)[3])
                                                 
                            persons.append(detectionBox)

                            #persons["persons"].append({"box": {"x1": int(np.array(xyxy)[0]), "y1": int(np.array(xyxy)[
                             #                       1]), "x2": int(np.array(xyxy)[2]), "y2": int(np.array(xyxy)[3])}})

        logging.info(
            f"[✅] In {(perf_counter() - start) * 1000:.2f}ms"
        )


        return PersonDetectionInferenceReply(persons=persons, filter=filter)



async def serve():
    server = grpc.aio.server()
    add_PersonDetectionServiceServicer_to_server(PersonDetectionService(), server)
    # using ip v6
    adddress = "[::]:50070"
    server.add_insecure_port(adddress)
    logging.info(f"[📡] Starting server on {adddress}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
