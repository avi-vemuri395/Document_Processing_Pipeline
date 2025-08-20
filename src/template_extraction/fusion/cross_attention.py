"""
Cross-attention mechanism for multimodal fusion.

This module implements cross-modal attention to enable bidirectional
information flow between different modalities (visual and structured data).
"""

import numpy as np
from typing import Optional, Tuple


class MultiHeadCrossAttention:
    """
    Multi-head cross-attention for fusing multimodal embeddings.
    
    This implementation uses a simplified attention mechanism that doesn't
    require neural network training, making it immediately usable.
    """
    
    def __init__(self, dim: int = 4096, num_heads: int = 8):
        """
        Initialize cross-attention mechanism.
        
        Args:
            dim: Dimension of embeddings
            num_heads: Number of attention heads
        """
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        
        if dim % num_heads != 0:
            raise ValueError(f"Dimension {dim} must be divisible by num_heads {num_heads}")
    
    def forward(
        self, 
        query: Optional[np.ndarray], 
        key: Optional[np.ndarray], 
        value: Optional[np.ndarray]
    ) -> np.ndarray:
        """
        Perform cross-modal attention fusion.
        
        Args:
            query: Query embeddings (e.g., visual features)
            key: Key embeddings (e.g., DocAI features)
            value: Value embeddings (e.g., DocAI features)
            
        Returns:
            Fused embeddings combining information from both modalities
        """
        # Handle None inputs (when one modality is unavailable)
        if query is None and key is None and value is None:
            # No data available
            return np.zeros(self.dim, dtype=np.float32)
        
        if query is None:
            # Only structured data available
            if key is not None and value is not None:
                return self._self_attention(key, value)
            return value if value is not None else key
        
        if key is None or value is None:
            # Only visual data available
            return self._self_attention(query, query)
        
        # Both modalities available - perform cross-attention
        return self._cross_attention(query, key, value)
    
    def _cross_attention(
        self, 
        query: np.ndarray, 
        key: np.ndarray, 
        value: np.ndarray
    ) -> np.ndarray:
        """
        Perform cross-attention between modalities.
        
        This computes attention weights based on similarity between
        query and key, then uses these weights to combine values.
        """
        # Ensure inputs have correct shape
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if key.ndim == 1:
            key = key.reshape(1, -1)
        if value.ndim == 1:
            value = value.reshape(1, -1)
        
        batch_size = query.shape[0]
        
        # Split into multiple heads
        query_heads = self._split_heads(query)
        key_heads = self._split_heads(key)
        value_heads = self._split_heads(value)
        
        # Compute attention scores for each head
        attention_outputs = []
        
        for h in range(self.num_heads):
            q_h = query_heads[h]
            k_h = key_heads[h]
            v_h = value_heads[h]
            
            # Compute attention scores
            scores = np.dot(q_h, k_h.T) / np.sqrt(self.head_dim)
            
            # Apply softmax to get attention weights
            attention_weights = self._softmax(scores)
            
            # Apply attention weights to values
            attended = np.dot(attention_weights, v_h)
            attention_outputs.append(attended)
        
        # Concatenate heads
        concatenated = np.concatenate(attention_outputs, axis=-1)
        
        # Apply final projection (using deterministic mixing)
        output = self._output_projection(concatenated)
        
        # Flatten if single batch
        if batch_size == 1:
            output = output.flatten()
        
        return output
    
    def _self_attention(self, features: np.ndarray, values: np.ndarray) -> np.ndarray:
        """
        Perform self-attention within a single modality.
        
        This enhances the features by allowing different parts
        to attend to each other.
        """
        # Use features as query, key, and values
        return self._cross_attention(features, features, values)
    
    def _split_heads(self, x: np.ndarray) -> list:
        """
        Split embeddings into multiple attention heads.
        
        Args:
            x: Input embeddings of shape (batch, dim)
            
        Returns:
            List of head embeddings, each of shape (batch, head_dim)
        """
        if x.ndim == 1:
            x = x.reshape(1, -1)
        
        batch_size = x.shape[0]
        
        # Reshape to (batch, num_heads, head_dim)
        x_reshaped = x.reshape(batch_size, self.num_heads, self.head_dim)
        
        # Split into list of heads
        heads = [x_reshaped[:, i, :] for i in range(self.num_heads)]
        
        return heads
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """
        Compute softmax activation.
        
        Args:
            x: Input scores
            
        Returns:
            Normalized attention weights
        """
        # Subtract max for numerical stability
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)
    
    def _output_projection(self, x: np.ndarray) -> np.ndarray:
        """
        Apply output projection after concatenating heads.
        
        This mixes information from different heads using a
        deterministic transformation.
        """
        # Create a deterministic mixing matrix
        mixing_matrix = self._create_mixing_matrix()
        
        # Apply mixing
        output = np.dot(x, mixing_matrix)
        
        # Apply non-linearity
        output = np.tanh(output)
        
        return output.astype(np.float32)
    
    def _create_mixing_matrix(self) -> np.ndarray:
        """
        Create a deterministic mixing matrix for output projection.
        
        This uses a fixed pattern that encourages information
        mixing between heads.
        """
        matrix = np.zeros((self.dim, self.dim), dtype=np.float32)
        
        # Create a circulant-like pattern for mixing
        for i in range(self.dim):
            for j in range(self.dim):
                if i == j:
                    matrix[i, j] = 0.8  # Strong diagonal
                elif abs(i - j) <= self.head_dim:
                    # Mix within head distance
                    distance = abs(i - j)
                    matrix[i, j] = 0.2 * np.exp(-distance / self.head_dim)
        
        # Normalize rows
        row_sums = np.sum(matrix, axis=1, keepdims=True)
        matrix = matrix / (row_sums + 1e-8)
        
        return matrix


class SimplifiedCrossAttention:
    """
    A simplified version of cross-attention for lightweight fusion.
    
    This can be used when computational efficiency is more important
    than sophisticated attention mechanisms.
    """
    
    def __init__(self, dim: int = 4096):
        """
        Initialize simplified cross-attention.
        
        Args:
            dim: Dimension of embeddings
        """
        self.dim = dim
    
    def forward(
        self, 
        visual_features: Optional[np.ndarray],
        docai_features: Optional[np.ndarray]
    ) -> np.ndarray:
        """
        Perform simplified fusion using weighted averaging.
        
        Args:
            visual_features: Visual embeddings
            docai_features: DocAI embeddings
            
        Returns:
            Fused embeddings
        """
        if visual_features is None and docai_features is None:
            return np.zeros(self.dim, dtype=np.float32)
        
        if visual_features is None:
            return docai_features
        
        if docai_features is None:
            return visual_features
        
        # Compute similarity between modalities
        similarity = self._compute_similarity(visual_features, docai_features)
        
        # Adaptive weighting based on similarity
        # High similarity -> equal weighting
        # Low similarity -> prefer structured data (DocAI)
        docai_weight = 0.5 + (0.3 * (1 - similarity))
        visual_weight = 1 - docai_weight
        
        # Weighted combination
        fused = (visual_weight * visual_features + 
                docai_weight * docai_features)
        
        # Apply non-linearity
        fused = np.tanh(fused)
        
        return fused.astype(np.float32)
    
    def _compute_similarity(
        self, 
        features1: np.ndarray, 
        features2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Similarity score between 0 and 1
        """
        # Flatten if needed
        if features1.ndim > 1:
            features1 = features1.flatten()
        if features2.ndim > 1:
            features2 = features2.flatten()
        
        # Compute cosine similarity
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Normalize to [0, 1]
        similarity = (similarity + 1) / 2
        
        return float(similarity)