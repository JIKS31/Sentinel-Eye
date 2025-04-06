import os
import cv2
import torch
from collections import deque
from ultralytics import YOLO
import mysql.connector
from datetime import datetime


class VideoProcessor:
    def __init__(self, criminal_model_path, accident_model_path, criminal_image_dir, accident_image_dir, db_config):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.criminal_model = YOLO(criminal_model_path).to(self.device)
        self.accident_model = YOLO(accident_model_path).to(self.device)
        self.criminal_image_dir = criminal_image_dir
        self.accident_image_dir = accident_image_dir
        self.db_config = db_config  # Database config

        os.makedirs(self.criminal_image_dir, exist_ok=True)
        os.makedirs(self.accident_image_dir, exist_ok=True)

        self.accident_count = len(os.listdir(self.accident_image_dir))
        self.criminal_count = len(os.listdir(self.criminal_image_dir))

        # Detection history buffers
        self.criminal_history = deque(maxlen=5)
        self.accident_history = deque(maxlen=5)

    def confirm_detections(self, history, min_frames=3):
        """Confirms an object detection if it appears in 'min_frames' consecutive frames."""
        confirmed = []
        for obj_list in history:
            for obj in obj_list:
                class_id, box = obj
                count = sum(1 for h in history if obj in h)
                if count >= min_frames:
                    confirmed.append((class_id, box))
        return confirmed

    def store_incident(self, name, location):
        """Store detected incident in the database"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()

        # Insert into the incident table
        cursor.execute("INSERT INTO incident (name, location, time) VALUES (%s, %s, %s)",
                       (name, location, timestamp))
        conn.commit()
        cursor.close()
        conn.close()

    def process_frame(self, frame):
        with torch.no_grad():
            frame_copy = frame.copy()

            # Weapon detection
            criminal_results = self.criminal_model(frame, conf=0.55, iou=0.5, device=self.device)
            valid_criminals = [(int(detection.cls.cpu().numpy()[0]),
                                tuple(map(int, detection.xyxy[0].cpu().numpy())))
                               for detection in criminal_results[0].boxes]

            self.criminal_history.append(valid_criminals)
            confirmed_criminals = self.confirm_detections(self.criminal_history, min_frames=1)

            for class_id, xyxy in confirmed_criminals:
                x_min, y_min, x_max, y_max = xyxy
                cropped_image = frame_copy[y_min:y_max, x_min:x_max]
                class_name = "gun" if class_id == 0 else "knife"
                self.criminal_count += 1
                cv2.imwrite(os.path.join(self.criminal_image_dir, f"{class_name}{self.criminal_count}.jpg"),
                            cropped_image)

                cv2.rectangle(frame_copy, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)
                cv2.putText(frame_copy, class_name, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                self.store_incident(class_name, "Unknown Location")

            # Accident detection
            accident_results = self.accident_model(frame, conf=0.65, iou=0.5, device=self.device)
            valid_accidents = [(int(detection.cls.cpu().numpy()[0]),
                                tuple(map(int, detection.xyxy[0].cpu().numpy())))
                               for detection in accident_results[0].boxes]

            self.accident_history.append(valid_accidents)
            confirmed_accidents = self.confirm_detections(self.accident_history, min_frames=2)

            for class_id, xyxy in confirmed_accidents:
                x_min, y_min, x_max, y_max = xyxy
                class_name = accident_results[0].names.get(class_id, "Unknown")
                cropped_image = frame_copy[y_min:y_max, x_min:x_max]
                self.accident_count += 1
                cv2.imwrite(os.path.join(self.accident_image_dir, f"{class_name}{self.accident_count}.jpg"),
                            cropped_image)

                cv2.rectangle(frame_copy, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
                cv2.putText(frame_copy, class_name, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                self.store_incident(class_name, "Unknown Location")

            return frame_copy
