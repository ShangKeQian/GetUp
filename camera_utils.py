import cv2


def enumerate_cameras(max_index: int = 10) -> list[dict]:
    cameras = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            backend = cap.getBackendName()
            name = f"Camera {i} ({width}x{height}, {backend})"
            cameras.append({"index": i, "name": name})
            cap.release()
    return cameras
