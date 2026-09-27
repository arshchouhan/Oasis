"""Backend sampling for uploaded eye-assessment videos.

This module intentionally stores no local copy of a patient's video: it downloads
the just-uploaded Cloudinary asset to a temporary file, samples frames, and deletes
the file before returning the aggregate measurements.
"""

import os
from tempfile import NamedTemporaryFile

import cv2
import requests


def analyse_recording(recording_url, max_samples=24):
    """Return video-derived duration, face-tracking quality and redness estimate."""
    temp_path = None
    try:
        response = requests.get(recording_url, timeout=45)
        response.raise_for_status()
        with NamedTemporaryFile(suffix='.webm', delete=False) as temporary_file:
            temporary_file.write(response.content)
            temp_path = temporary_file.name

        capture = cv2.VideoCapture(temp_path)
        if not capture.isOpened():
            raise ValueError('The uploaded video could not be opened for analysis.')

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames_per_second = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        duration = int(round(frame_count / frames_per_second)) if frames_per_second else 0
        samples = min(max_samples, frame_count) if frame_count else 0
        face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        readable_frames = 0
        detected_faces = 0
        redness_values = []

        for sample_index in range(samples):
            position = int(sample_index * max(frame_count - 1, 0) / max(samples - 1, 1))
            capture.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, frame = capture.read()
            if not ok:
                continue
            readable_frames += 1
            grey_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(grey_frame, scaleFactor=1.12, minNeighbors=5, minSize=(70, 70))
            if len(faces) == 0:
                continue
            detected_faces += 1
            x, y, width, height = max(faces, key=lambda item: item[2] * item[3])
            # Upper-middle face region contains both visible eye areas. This is a
            # lighting-sensitive visual screen, not a clinical redness diagnosis.
            eye_region = frame[y + int(height * .18):y + int(height * .58), x:x + width]
            if eye_region.size:
                blue, green, red = cv2.split(eye_region)
                red_excess = (red.astype('float32') - (green.astype('float32') + blue.astype('float32')) / 2).mean()
                redness_values.append(max(0.0, min(10.0, red_excess / 9.0)))

        capture.release()
        return {
            'duration_seconds': max(1, duration),
            'sampled_frames': readable_frames,
            'tracking_quality': round(detected_faces / readable_frames * 100) if readable_frames else 0,
            'redness_score': round(sum(redness_values) / len(redness_values), 1) if redness_values else None,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
