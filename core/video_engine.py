"""
Video Processing Engine for Gallery Cube.
Handles MP4, MOV, MKV, AVI, and WebM playback, timestamp seeking, metadata extraction,
and frame snapshot extraction for mobile & flagship phone video recordings.
"""
import os
from typing import Optional, Tuple, Dict, Any
import cv2
from PIL import Image

SUPPORTED_VIDEO_EXTENSIONS = (
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".3gp", ".wmv"
)


class VideoEngine:
    def __init__(self):
        self.file_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 30.0
        self.total_frames: int = 0
        self.duration_seconds: float = 0.0
        self.current_frame_idx: int = 0
        self.current_pil_frame: Optional[Image.Image] = None

    def load_video(self, file_path: str) -> Tuple[bool, str]:
        """Opens video file and extracts technical video parameters."""
        self.close()

        if not os.path.exists(file_path):
            return False, "File does not exist."

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False, "Could not open video stream (unsupported codec or corrupt file)."

        self.cap = cap
        self.file_path = file_path
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if self.fps <= 0 or self.fps > 240:
            self.fps = 30.0

        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.total_frames > 0:
            self.duration_seconds = self.total_frames / self.fps
        else:
            self.duration_seconds = 0.0

        self.current_frame_idx = 0
        # Read first frame
        self.read_next_frame()

        return True, f"Loaded {self.width}×{self.height} @ {self.fps:.1f} FPS"

    def read_next_frame(self) -> Optional[Image.Image]:
        """Reads the next consecutive frame from the video stream."""
        if not self.cap or not self.cap.isOpened():
            return None

        ret, frame = self.cap.read()
        if not ret:
            return None

        self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        # Convert BGR (OpenCV) to RGB (PIL)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_pil_frame = Image.fromarray(rgb_frame)
        return self.current_pil_frame

    def seek_to_frame(self, frame_idx: int) -> Optional[Image.Image]:
        """Jumps directly to a specific frame number."""
        if not self.cap or not self.cap.isOpened():
            return None

        target = max(0, min(self.total_frames - 1, frame_idx))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        return self.read_next_frame()

    def seek_to_ratio(self, ratio: float) -> Optional[Image.Image]:
        """Jumps to normalized position (0.0 to 1.0)."""
        if self.total_frames <= 0:
            return None
        target_frame = int(round(max(0.0, min(1.0, ratio)) * (self.total_frames - 1)))
        return self.seek_to_frame(target_frame)

    @property
    def current_time_seconds(self) -> float:
        if self.fps <= 0:
            return 0.0
        return self.current_frame_idx / self.fps

    @property
    def formatted_current_time(self) -> str:
        return self._format_time(self.current_time_seconds)

    @property
    def formatted_total_time(self) -> str:
        return self._format_time(self.duration_seconds)

    def _format_time(self, seconds: float) -> str:
        total_sec = int(round(seconds))
        mins = total_sec // 60
        secs = total_sec % 60
        return f"{mins:02d}:{secs:02d}"

    def get_metadata(self) -> Dict[str, Any]:
        """Returns structured metadata about the active video."""
        file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024) if self.file_path else 0.0
        
        # Categorize resolution
        res_label = f"{self.width} × {self.height}"
        if self.width >= 7680 or self.height >= 4320:
            res_label += " (8K UHD)"
        elif self.width >= 3840 or self.height >= 2160:
            res_label += " (4K UHD)"
        elif self.width >= 1920 or self.height >= 1080:
            res_label += " (1080p FHD)"
        elif self.width >= 1280 or self.height >= 720:
            res_label += " (720p HD)"

        return {
            "Filename": os.path.basename(self.file_path) if self.file_path else "Unknown",
            "Resolution": res_label,
            "FPS": f"{self.fps:.2f} fps",
            "TotalFrames": f"{self.total_frames:,}",
            "Duration": self.formatted_total_time,
            "FileSize": f"{file_size_mb:.2f} MB"
        }

    def close(self):
        """Releases video capture resources."""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.file_path = None
        self.current_pil_frame = None
        self.total_frames = 0

