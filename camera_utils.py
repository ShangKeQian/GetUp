import sys
import cv2


def enumerate_cameras(max_index: int = 10) -> list[dict]:
    cameras = []
    for i in range(max_index):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                try:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    backend = cap.getBackendName()
                    name = f"Camera {i} ({width}x{height}, {backend})"
                    cameras.append({"index": i, "name": name})
                finally:
                    cap.release()
        except Exception as e:
            print(f"[camera_utils] 探测摄像头 {i} 失败: {e}", file=sys.stderr)
    return cameras
