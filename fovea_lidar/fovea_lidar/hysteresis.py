from foveation import ROI, apply_hysteresis
from typing import List


class HysteresisManager:
    def __init__(self, hysteresis_frames: int = 5):
        self.hysteresis_frames = hysteresis_frames
        self.previous_rois: List[ROI] = []
        self.frame_counter = 0

    def update(self, current_rois: List[ROI]) -> List[ROI]:
        self.frame_counter += 1
        self.previous_rois = apply_hysteresis(
            current_rois,
            self.previous_rois,
            self.hysteresis_frames,
            self.frame_counter,
        )
        return self.previous_rois

    def reset(self):
        self.previous_rois = []
        self.frame_counter = 0