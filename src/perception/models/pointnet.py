"""PointNet Semantic Segmentation Architecture for 3D LiDAR Point Clouds.

Reference:
    Qi et al., "PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation",
    CVPR 2017. https://arxiv.org/abs/1612.00593

Implements point-wise semantic segmentation using shared multi-layer perceptrons (MLPs),
global feature aggregation via symmetric max-pooling, and multi-scale feature concatenation.
"""

import os
from typing import Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAVE_TORCH = True
except ImportError:
    torch = None
    nn = object
    F = None
    HAVE_TORCH = False


if HAVE_TORCH:
    class PointNetSegmentation(nn.Module):
        """PointNet architecture for point-wise semantic segmentation (Qi et al., 2017).
        
        Maps an (B, C_in, N) point cloud to (B, num_classes, N) per-point logits.
        """

        def __init__(self, in_channels: int = 4, num_classes: int = 4):
            super().__init__()
            self.in_channels = in_channels
            self.num_classes = num_classes

            # Local feature extraction (Shared MLP: in_channels -> 64 -> 128)
            self.conv1 = nn.Conv1d(in_channels, 64, kernel_size=1)
            self.bn1 = nn.BatchNorm1d(64)

            self.conv2 = nn.Conv1d(64, 128, kernel_size=1)
            self.bn2 = nn.BatchNorm1d(128)

            # Global feature extraction (Shared MLP: 128 -> 256 -> 512)
            self.conv3 = nn.Conv1d(128, 256, kernel_size=1)
            self.bn3 = nn.BatchNorm1d(256)

            self.conv4 = nn.Conv1d(256, 512, kernel_size=1)
            self.bn4 = nn.BatchNorm1d(512)

            # Point-wise Segmentation Head
            # Concatenates local features (128) + global features (512) = 640
            self.seg_conv1 = nn.Conv1d(512 + 128, 256, kernel_size=1)
            self.seg_bn1 = nn.BatchNorm1d(256)

            self.seg_conv2 = nn.Conv1d(256, 128, kernel_size=1)
            self.seg_bn2 = nn.BatchNorm1d(128)

            self.seg_conv3 = nn.Conv1d(128, num_classes, kernel_size=1)

            self.dropout = nn.Dropout(p=0.3)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Forward pass.
            
            Args:
                x: (Batch, Channels, NumPoints) tensor where Channels >= 3 (X, Y, Z, [Intensity])
            
            Returns:
                logits: (Batch, NumClasses, NumPoints) per-point class logits
            """
            num_points = x.size(2)

            # Local features (B, 128, N)
            h1 = F.relu(self.bn1(self.conv1(x)))
            local_feat = F.relu(self.bn2(self.conv2(h1)))

            # High-level features (B, 512, N)
            h3 = F.relu(self.bn3(self.conv3(local_feat)))
            h4 = self.bn4(self.conv4(h3))

            # Symmetric function: Global max-pooling across point dimension (B, 512, 1)
            global_feat = torch.max(h4, dim=2, keepdim=True)[0]

            # Replicate global feature across all N points (B, 512, N)
            global_feat_expanded = global_feat.repeat(1, 1, num_points)

            # Concatenate local features with global context (B, 640, N)
            concat_feat = torch.cat([local_feat, global_feat_expanded], dim=1)

            # Segmentation MLP
            s1 = F.relu(self.seg_bn1(self.seg_conv1(concat_feat)))
            s2 = F.relu(self.seg_bn2(self.seg_conv2(s1)))
            s2 = self.dropout(s2)
            logits = self.seg_conv3(s2)  # (B, num_classes, N)

            return logits

        def predict_numpy(self, points: "np.ndarray", device: str = "cpu") -> Tuple["np.ndarray", "np.ndarray"]:
            """Convenience inference method for NumPy input arrays (N, C)."""
            import numpy as np

            if points.shape[0] == 0:
                return np.empty(0, dtype=np.int32), np.empty(0, dtype=np.float32)

            self.eval()
            with torch.no_grad():
                # Pad to in_channels if only (N, 3) provided
                if points.shape[1] < self.in_channels:
                    pad = np.ones((points.shape[0], self.in_channels - points.shape[1]), dtype=np.float32) * 0.5
                    points = np.hstack([points, pad])
                elif points.shape[1] > self.in_channels:
                    points = points[:, :self.in_channels]

                # Shape: (1, Channels, N)
                tensor_in = torch.from_numpy(points.T).float().unsqueeze(0).to(device)
                logits = self.forward(tensor_in)  # (1, num_classes, N)
                probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()  # (num_classes, N)

                labels = np.argmax(probs, axis=0).astype(np.int32)
                confidences = np.max(probs, axis=0).astype(np.float32)

                return labels, confidences

else:
    class PointNetSegmentation:
        """Dummy placeholder when PyTorch is not installed."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is not installed in the active environment.")
