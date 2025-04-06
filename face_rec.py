import numpy as np
import dlib
import os
import cv2
import mysql.connector
from datetime import datetime

class FaceRecognizer:
    def __init__(self, cnn_model_path, shape_predictor_path, face_recognition_model_path, database_path, db_config):
        # Initialize Dlib models
        self.cnn_face_detector = dlib.cnn_face_detection_model_v1(cnn_model_path)
        self.predictor = dlib.shape_predictor(shape_predictor_path)
        self.face_rec = dlib.face_recognition_model_v1(face_recognition_model_path)

        # Load the database into memory
        self.database = self._load_database(database_path)
        self.db_config = db_config  # Store MySQL Config

    def _load_database(self, database_path):
        face_descriptors = []
        for file in os.listdir(database_path):
            if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            img = dlib.load_rgb_image(os.path.join(database_path, file))
            faces = self.cnn_face_detector(img, 1)

            for face in faces:
                shape = self.predictor(img, face.rect)
                descriptor = self.face_rec.compute_face_descriptor(img, shape)
                face_descriptors.append({
                    "name": file.split('.')[0],  # Extract name from filename
                    "descriptor": np.array(descriptor)
                })
        return face_descriptors

    def recognize(self, frame, location="Unknown"):  # Added location parameter
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.cnn_face_detector(rgb_frame, 1)
        results = []

        for face in faces:
            rect = face.rect
            shape = self.predictor(rgb_frame, rect)
            descriptor = np.array(self.face_rec.compute_face_descriptor(rgb_frame, shape))

            # Match with database
            min_dist = float('inf')
            name = "UNKNOWN"

            for db_face in self.database:
                dist = np.linalg.norm(descriptor - db_face["descriptor"])
                if dist < 0.55 and dist < min_dist:
                    min_dist = dist
                    name = db_face["name"]

            if name != "UNKNOWN":
                self.log_criminal(name, location)  # Store in MySQL

            results.append({
                "name": name,
                "rect": (rect.left(), rect.top(), rect.right(), rect.bottom()),
                "distance": min_dist
            })

        return results

    def log_criminal(self, name, location):
        """ Stores detected criminals in MySQL """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            query = "INSERT INTO log (name, location, time) VALUES (%s, %s, %s)"
            values = (name, location, datetime.now())

            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            print(f"Logged criminal: {name} at {location}")
        except mysql.connector.Error as err:
            print(f"Error logging to database: {err}")
