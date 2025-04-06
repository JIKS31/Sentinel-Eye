from flask import Flask, render_template, Response, jsonify
import cv2
import mysql.connector
from face_rec import FaceRecognizer
from processor1 import VideoProcessor
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from flask import send_from_directory
app = Flask(__name__)
import os
# =================== ALERT CONFIGURATION ===================
@app.route('/get_criminal_images')
def get_criminal_images():
    image_folder = os.path.join(app.static_folder, 'criminals')
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return jsonify({'images': image_files})

@app.route('/criminal_image/<filename>')
def criminal_image(filename):
    return send_from_directory(os.path.join(app.static_folder, 'criminals'), filename)

# Twilio Configuration
TWILIO_ACCOUNT_SID = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_AUTH_TOKEN = "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_PHONE_NUMBER = "XXXXXXXXXXX"
ALERT_RECIPIENT = "XXXXXXXXXXX"

# Email Configuration (Optional)
EMAIL_SENDER = "fromaddress@gmail.com"
EMAIL_PASSWORD = "xxxxxxxxxxxxxx"
EMAIL_RECIPIENT = "toaddress@gmail.com"

# =================== ALERT FUNCTIONS ===================

# Track sent alerts to avoid duplicates
sent_criminal_alerts = set()
sent_incident_alerts = set()

def send_sms_alert(message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=ALERT_RECIPIENT)
        print("✅ SMS alert sent.")
    except Exception as e:
        print("❌ Failed to send SMS:", e)

def send_email_alert(subject, body, recipient=EMAIL_RECIPIENT):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email alert sent to {recipient}")
    except Exception as e:
        print("❌ Failed to send email:", e)

# =================== DATABASE & MODELS ===================

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "sentinel"
}

# Model paths
cnn_model_path = r'/Sentinel_Eye\face-recognition.js-models\models\mmod_human_face_detector.dat'
shape_predictor_path = r"/Sentinel_Eye\face-recognition.js-models\models\shape_predictor_68_face_landmarks_GTX.dat"
face_recognition_model_path = r'/Sentinel_Eye\face-recognition.js-models\models\dlib_face_recognition_resnet_model_v1.dat'
database_path = r'/Sentinel_Eye\static\criminals'

criminal_model_path = r'/Sentinel_Eye\YOLO_MODELS\best.pt'  #Weapon detection model gun and knife.
accident_model_path = r'/Sentinel_Eye\YOLO_MODELS\NICEONE\best1.pt'  #Accident detection model with various classes.
criminal_image_dir = r"C:\Main\CriminalCroppedImages"
accident_image_dir = r"C:\Main\AccidentCroppedImages"

# Initialize face recognizer and processor
face_recognizer = FaceRecognizer(cnn_model_path, shape_predictor_path, face_recognition_model_path, database_path, db_config)
processor = VideoProcessor(criminal_model_path, accident_model_path, criminal_image_dir, accident_image_dir, db_config)

# Load video
video_path = 0
cap = cv2.VideoCapture(video_path)

# =================== FETCH LOGS ===================

def get_logs():
    global sent_criminal_alerts, sent_incident_alerts

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT name, location, time FROM log ORDER BY time DESC LIMIT 8")
    criminal_data = cursor.fetchall()

    cursor.execute("SELECT name, location, time FROM incident ORDER BY time DESC LIMIT 7")
    incident_data = cursor.fetchall()

    cursor.close()
    conn.close()

    for criminal in criminal_data:
        if criminal['name'].upper().startswith("CRIMINAL"):
            key = (criminal['name'], criminal['location'])
            if key not in sent_criminal_alerts:
                alert_message = f"ALERT: {criminal['name']} detected at {criminal['location']} on {criminal['time']}"
                send_sms_alert(alert_message)
                send_email_alert("Criminal Alert", alert_message)
                sent_criminal_alerts.add(key)

    for incident in incident_data:
        if incident['name'] in ['car_bike_accident', 'car_car_accident', 'car_object_accident', 'car_person_accident', 'gun']:
            key = (incident['name'], incident['location'])
            if key not in sent_incident_alerts:
                alert_message = f"ALERT: {incident['name']} detected at {incident['location']} on {incident['time']}"
                send_sms_alert(alert_message)
                send_email_alert("Incident Alert", alert_message)
                sent_incident_alerts.add(key)

    return {"criminals": criminal_data, "incidents": incident_data}

# =================== VIDEO STREAM ===================

def generate_frames():
    global cap
    if cap is None or not cap.isOpened():
        print("Error: Unable to open video file.")
        return

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        processed_frame = processor.process_frame(frame)
        if processed_frame is None:
            continue

        face_results = face_recognizer.recognize(processed_frame)

        for face in face_results:
            left, top, right, bottom = face['rect']
            name = face['name']
            cv2.rectangle(processed_frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(processed_frame, f"{name} ({face['distance']:.2f})",
                        (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# =================== ROUTES ===================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_logs')
def fetch_logs():
    return jsonify(get_logs())

# =================== MAIN ===================

if __name__ == '__main__':
    import atexit
    atexit.register(lambda: cap.release() if cap is not None else None)

    try:
        app.run(host="127.0.0.1", port=5000, debug=False)
    except OSError:
        print("Port 5000 in use. Trying port 8000...")
        app.run(host="127.0.0.1", port=8000, debug=False)
