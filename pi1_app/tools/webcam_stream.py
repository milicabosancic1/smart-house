import atexit
import time

from flask import Flask, Response, request
import numpy as np

try:
    import cv2
except Exception as exc:
    raise SystemExit(
        "OpenCV nije dostupan. Pokreni: py -m pip install -r webcam_requirements.txt"
    ) from exc

app = Flask(__name__)


def _open_camera():
    backends = [None]
    if hasattr(cv2, "CAP_DSHOW"):
        backends.insert(0, cv2.CAP_DSHOW)

    for index in (0, 1, 2):
        for backend in backends:
            cam = cv2.VideoCapture(index, backend) if backend is not None else cv2.VideoCapture(index)
            if cam.isOpened():
                return cam
            try:
                cam.release()
            except Exception:
                pass
    return None


_camera = _open_camera()


def _release_camera():
    try:
        _camera.release()
    except Exception:
        pass


atexit.register(_release_camera)


def _mjpeg_frames():
    global _camera
    fail_count = 0
    while True:
        if _camera is None:
            _camera = _open_camera()
            if _camera is None:
                time.sleep(0.3)
                continue

        try:
            ok, frame = _camera.read()
        except Exception:
            ok = False

        if not ok:
            fail_count += 1
            try:
                _camera.release()
            except Exception:
                pass
            _camera = None
            time.sleep(0.2 if fail_count < 10 else 0.6)
            continue

        fail_count = 0
        ok, jpg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        payload = jpg.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
        )


def _placeholder_frames():
    global _camera
    while True:
        cam = _open_camera()
        if cam is not None:
            _camera = cam
            return

        frame = np.zeros((240, 640, 3), dtype="uint8")
        frame[:] = (30, 30, 30)
        cv2.putText(frame, "Kamera nije dostupna (zatvori Zoom/Teams)", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "Automatski retry...", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
        ok, jpg = cv2.imencode(".jpg", frame)
        if not ok:
            time.sleep(0.3)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
        )
        time.sleep(0.4)


@app.get("/")
def root():
    action = (request.args.get("action") or "").lower()
    if action == "stream":
        return Response(_mjpeg_or_placeholder_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
    return (
        "Local webcam stream je aktivan. Koristi /?action=stream ili /video_feed",
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


@app.get("/video_feed")
def video_feed():
    return Response(_mjpeg_or_placeholder_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _mjpeg_or_placeholder_frames():
    while True:
        if _camera is None:
            yield from _placeholder_frames()
            continue
        yield from _mjpeg_frames()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
