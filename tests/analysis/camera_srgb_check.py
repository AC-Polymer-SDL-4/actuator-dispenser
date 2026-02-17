"""Deprecated helper: camera diagnostic script.

This script has been deprecated to streamline `tests/analysis`.
If you need to quickly check camera output, use OpenCV directly:

Example (Python):

    import cv2
    cap = cv2.VideoCapture(0, cv2.CAP_ANY)
    ok, frame = cap.read()
    print(frame.shape, frame.dtype, frame.min(), frame.max())
    cv2.imwrite('camera_check_frame.png', frame)
    cap.release()

For analysis, rely on `uncertainty_plot_and_stats.py` for normalized processing.
"""

if __name__ == '__main__':
    print("camera_srgb_check.py is deprecated. Use inline OpenCV snippets as needed.")
