"""
Projection-Based Intermediate Fusion Components

This module implements state-of-the-art multimodal fusion for document processing.
It aligns different data modalities (visual, structured, text) into a shared semantic
space for superior understanding.
"""

from .projectors import VisualProjector, DocAIProjector
from .cross_attention import MultiHeadCrossAttention
from .fusion_manager import FusionManager

__all__ = [
    'VisualProjector',
    'DocAIProjector', 
    'MultiHeadCrossAttention',
    'FusionManager'
]