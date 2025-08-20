"""
Fusion Manager - Orchestrates the multimodal fusion pipeline.

This manager coordinates the projection and fusion of different data modalities
to create a unified understanding of documents.
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json
import time

from .projectors import VisualProjector, DocAIProjector
from .cross_attention import MultiHeadCrossAttention, SimplifiedCrossAttention


class FusionManager:
    """
    Manages the projection-based intermediate fusion pipeline.
    
    This class orchestrates:
    1. Projecting different modalities to shared space
    2. Fusing representations via cross-attention
    3. Calculating fusion quality metrics
    4. Enhancing extraction results with fusion insights
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize fusion manager with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        # Default configuration
        self.config = {
            'embedding_dim': 4096,
            'num_attention_heads': 8,
            'use_simplified_attention': False,
            'enable_fusion': True,  # Can be disabled for backward compatibility
            'fusion_mode': 'adaptive',  # 'adaptive', 'always', 'threshold'
            'confidence_threshold': 0.7,
            'cache_projections': True
        }
        
        if config:
            self.config.update(config)
        
        # Initialize components
        self.visual_projector = VisualProjector(output_dim=self.config['embedding_dim'])
        self.docai_projector = DocAIProjector(output_dim=self.config['embedding_dim'])
        
        # Choose attention mechanism
        if self.config['use_simplified_attention']:
            self.attention = SimplifiedCrossAttention(dim=self.config['embedding_dim'])
        else:
            self.attention = MultiHeadCrossAttention(
                dim=self.config['embedding_dim'],
                num_heads=self.config['num_attention_heads']
            )
        
        # Cache for projections (to avoid recomputing)
        self.projection_cache = {} if self.config['cache_projections'] else None
        
        # Metrics tracking
        self.fusion_metrics = {
            'total_fusions': 0,
            'successful_fusions': 0,
            'visual_only': 0,
            'docai_only': 0,
            'both_modalities': 0,
            'average_fusion_quality': 0.0
        }
    
    async def fuse_multimodal(
        self,
        docai_result: Optional[Dict[str, Any]],
        vision_result: Optional[Dict[str, Any]],
        document_path: Path,
        return_diagnostics: bool = False
    ) -> Dict[str, Any]:
        """
        Perform multimodal fusion on extraction results.
        
        Args:
            docai_result: Extraction from DocAI (can be None)
            vision_result: Extraction from Claude Vision (can be None)
            document_path: Path to the source document
            return_diagnostics: Whether to include diagnostic information
            
        Returns:
            Enhanced extraction result with fusion insights
        """
        if not self.config['enable_fusion']:
            # Fusion disabled - return best available result
            return docai_result if docai_result and docai_result.get('success') else vision_result
        
        start_time = time.time()
        
        # Step 1: Project modalities to shared space
        docai_embeddings = await self._project_docai(docai_result, document_path)
        vision_embeddings = await self._project_vision(vision_result, document_path)
        
        # Step 2: Determine fusion strategy
        fusion_strategy = self._determine_fusion_strategy(
            docai_embeddings, vision_embeddings, docai_result, vision_result
        )
        
        # Step 3: Perform fusion based on strategy
        if fusion_strategy == 'docai_only':
            self.fusion_metrics['docai_only'] += 1
            fused_result = self._enhance_with_single_modality(
                docai_result, 'docai', docai_embeddings
            )
        elif fusion_strategy == 'vision_only':
            self.fusion_metrics['visual_only'] += 1
            fused_result = self._enhance_with_single_modality(
                vision_result, 'vision', vision_embeddings
            )
        else:  # 'both'
            self.fusion_metrics['both_modalities'] += 1
            fused_embeddings = await self._perform_fusion(
                docai_embeddings, vision_embeddings
            )
            fused_result = self._create_fused_result(
                docai_result, vision_result, fused_embeddings, fusion_strategy
            )
        
        # Step 4: Calculate fusion quality
        fusion_quality = self._calculate_fusion_quality(
            docai_embeddings, vision_embeddings, 
            fused_result.get('fused_embeddings')
        )
        
        # Step 5: Add fusion metadata
        fusion_time = time.time() - start_time
        fused_result['fusion_metadata'] = {
            'strategy': fusion_strategy,
            'fusion_quality': fusion_quality,
            'processing_time': fusion_time,
            'has_docai': docai_embeddings is not None,
            'has_vision': vision_embeddings is not None,
            'document': str(document_path.name)
        }
        
        # Update metrics
        self.fusion_metrics['total_fusions'] += 1
        if fusion_quality > 0:
            self.fusion_metrics['successful_fusions'] += 1
            # Update running average
            n = self.fusion_metrics['successful_fusions']
            prev_avg = self.fusion_metrics['average_fusion_quality']
            self.fusion_metrics['average_fusion_quality'] = (
                (prev_avg * (n - 1) + fusion_quality) / n
            )
        
        # Add diagnostics if requested
        if return_diagnostics:
            fused_result['fusion_diagnostics'] = self._generate_diagnostics(
                docai_embeddings, vision_embeddings, fusion_quality
            )
        
        return fused_result
    
    async def _project_docai(
        self, 
        docai_result: Optional[Dict[str, Any]],
        document_path: Path
    ) -> Optional[np.ndarray]:
        """Project DocAI results to embedding space."""
        if not docai_result or not docai_result.get('success'):
            return None
        
        # Check cache
        if self.projection_cache is not None:
            cache_key = f"docai_{document_path.name}"
            if cache_key in self.projection_cache:
                return self.projection_cache[cache_key]
        
        # Project
        embeddings = self.docai_projector.project(docai_result)
        
        # Cache if enabled
        if self.projection_cache is not None and embeddings is not None:
            self.projection_cache[cache_key] = embeddings
        
        return embeddings
    
    async def _project_vision(
        self,
        vision_result: Optional[Dict[str, Any]],
        document_path: Path
    ) -> Optional[np.ndarray]:
        """Project vision results to embedding space."""
        if not vision_result or vision_result.get('error'):
            return None
        
        # Check cache
        if self.projection_cache is not None:
            cache_key = f"vision_{document_path.name}"
            if cache_key in self.projection_cache:
                return self.projection_cache[cache_key]
        
        # Project
        embeddings = self.visual_projector.project(vision_result)
        
        # Cache if enabled
        if self.projection_cache is not None and embeddings is not None:
            self.projection_cache[cache_key] = embeddings
        
        return embeddings
    
    def _determine_fusion_strategy(
        self,
        docai_embeddings: Optional[np.ndarray],
        vision_embeddings: Optional[np.ndarray],
        docai_result: Optional[Dict[str, Any]],
        vision_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        Determine the optimal fusion strategy based on available data.
        
        Returns:
            'both', 'docai_only', or 'vision_only'
        """
        if self.config['fusion_mode'] == 'always':
            # Always try to fuse if both available
            if docai_embeddings is not None and vision_embeddings is not None:
                return 'both'
        
        # Check availability
        has_docai = docai_embeddings is not None and docai_result and docai_result.get('success')
        has_vision = vision_embeddings is not None and vision_result and not vision_result.get('error')
        
        if not has_docai and not has_vision:
            return 'none'
        elif not has_docai:
            return 'vision_only'
        elif not has_vision:
            return 'docai_only'
        
        # Both available - check quality
        if self.config['fusion_mode'] == 'threshold':
            # Use confidence thresholds
            docai_confidence = docai_result.get('confidence', 0)
            vision_confidence = vision_result.get('confidence', 0.85)  # Default for vision
            
            threshold = self.config['confidence_threshold']
            
            if docai_confidence >= threshold and vision_confidence >= threshold:
                return 'both'
            elif docai_confidence >= threshold:
                return 'docai_only'
            elif vision_confidence >= threshold:
                return 'vision_only'
        
        # Default: use both if available
        return 'both'
    
    async def _perform_fusion(
        self,
        docai_embeddings: Optional[np.ndarray],
        vision_embeddings: Optional[np.ndarray]
    ) -> np.ndarray:
        """Perform the actual fusion using cross-attention."""
        if isinstance(self.attention, SimplifiedCrossAttention):
            # Simplified attention has different interface
            return self.attention.forward(vision_embeddings, docai_embeddings)
        else:
            # Multi-head cross-attention
            return self.attention.forward(
                query=vision_embeddings,
                key=docai_embeddings,
                value=docai_embeddings
            )
    
    def _enhance_with_single_modality(
        self,
        result: Dict[str, Any],
        modality: str,
        embeddings: Optional[np.ndarray]
    ) -> Dict[str, Any]:
        """Enhance single-modality result with embedding information."""
        if result is None:
            result = {}
        
        enhanced = result.copy()
        enhanced['extraction_mode'] = modality
        
        if embeddings is not None:
            # Add embedding statistics for downstream use
            enhanced['embedding_stats'] = {
                'mean': float(np.mean(embeddings)),
                'std': float(np.std(embeddings)),
                'min': float(np.min(embeddings)),
                'max': float(np.max(embeddings)),
                'norm': float(np.linalg.norm(embeddings))
            }
        
        return enhanced
    
    def _create_fused_result(
        self,
        docai_result: Optional[Dict[str, Any]],
        vision_result: Optional[Dict[str, Any]],
        fused_embeddings: np.ndarray,
        strategy: str
    ) -> Dict[str, Any]:
        """
        Create the final fused result by intelligently combining both modalities.
        
        This merges the structured data from DocAI with the comprehensive
        extraction from vision, using the fused embeddings to guide the process.
        """
        # Start with vision result as base (usually more comprehensive)
        if vision_result and not vision_result.get('error'):
            fused = vision_result.copy()
        else:
            fused = {}
        
        # Enhance with DocAI structured data
        if docai_result and docai_result.get('success'):
            # Add/override with high-confidence DocAI fields
            if 'form_fields' in docai_result:
                if 'form_fields' not in fused:
                    fused['form_fields'] = {}
                
                # Merge form fields, preferring DocAI for structured data
                for field_name, field_data in docai_result['form_fields'].items():
                    # Check confidence if available
                    if isinstance(field_data, dict):
                        confidence = field_data.get('confidence', 1.0)
                        if confidence > 0.8:  # High confidence threshold
                            fused['form_fields'][field_name] = field_data
                    else:
                        fused['form_fields'][field_name] = field_data
            
            # Add tables from DocAI (usually better structured)
            if 'tables' in docai_result:
                fused['docai_tables'] = docai_result['tables']
            
            # Add entities from DocAI
            if 'entities' in docai_result:
                fused['docai_entities'] = docai_result['entities']
        
        # Add fusion information
        fused['extraction_mode'] = 'fused'
        fused['fusion_strategy'] = strategy
        fused['fused_embeddings'] = fused_embeddings
        
        # Add embedding statistics
        fused['embedding_stats'] = {
            'mean': float(np.mean(fused_embeddings)),
            'std': float(np.std(fused_embeddings)),
            'min': float(np.min(fused_embeddings)),
            'max': float(np.max(fused_embeddings)),
            'norm': float(np.linalg.norm(fused_embeddings))
        }
        
        return fused
    
    def _calculate_fusion_quality(
        self,
        docai_embeddings: Optional[np.ndarray],
        vision_embeddings: Optional[np.ndarray],
        fused_embeddings: Optional[np.ndarray]
    ) -> float:
        """
        Calculate the quality of the fusion.
        
        Quality is based on:
        1. Availability of both modalities
        2. Similarity between modalities (coherence)
        3. Information preservation in fused representation
        """
        if fused_embeddings is None:
            # No fusion performed
            if docai_embeddings is not None or vision_embeddings is not None:
                return 0.5  # Single modality
            return 0.0  # No data
        
        quality_scores = []
        
        # Check if both modalities were available
        if docai_embeddings is not None and vision_embeddings is not None:
            # Calculate inter-modal coherence
            coherence = self._calculate_coherence(docai_embeddings, vision_embeddings)
            quality_scores.append(coherence)
            
            # Calculate information preservation
            docai_preservation = self._calculate_preservation(
                docai_embeddings, fused_embeddings
            )
            vision_preservation = self._calculate_preservation(
                vision_embeddings, fused_embeddings
            )
            quality_scores.append((docai_preservation + vision_preservation) / 2)
        else:
            # Single modality fusion
            source = docai_embeddings if docai_embeddings is not None else vision_embeddings
            preservation = self._calculate_preservation(source, fused_embeddings)
            quality_scores.append(preservation)
        
        # Calculate overall quality
        if quality_scores:
            quality = np.mean(quality_scores)
        else:
            quality = 0.0
        
        return float(quality)
    
    def _calculate_coherence(
        self,
        embeddings1: np.ndarray,
        embeddings2: np.ndarray
    ) -> float:
        """Calculate coherence (similarity) between two embeddings."""
        # Flatten if needed
        if embeddings1.ndim > 1:
            embeddings1 = embeddings1.flatten()
        if embeddings2.ndim > 1:
            embeddings2 = embeddings2.flatten()
        
        # Cosine similarity
        dot_product = np.dot(embeddings1, embeddings2)
        norm1 = np.linalg.norm(embeddings1)
        norm2 = np.linalg.norm(embeddings2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Convert to quality score (0 to 1)
        # High similarity (>0.5) indicates good coherence
        # Low similarity (<0) indicates poor coherence
        quality = max(0, min(1, (similarity + 0.5)))
        
        return quality
    
    def _calculate_preservation(
        self,
        source: np.ndarray,
        fused: np.ndarray
    ) -> float:
        """Calculate how well information is preserved in fusion."""
        # Flatten if needed
        if source.ndim > 1:
            source = source.flatten()
        if fused.ndim > 1:
            fused = fused.flatten()
        
        # Calculate correlation as a measure of preservation
        correlation = np.corrcoef(source, fused)[0, 1]
        
        # Convert to quality score
        preservation = max(0, correlation)
        
        return preservation
    
    def _generate_diagnostics(
        self,
        docai_embeddings: Optional[np.ndarray],
        vision_embeddings: Optional[np.ndarray],
        fusion_quality: float
    ) -> Dict[str, Any]:
        """Generate diagnostic information for debugging and analysis."""
        diagnostics = {
            'fusion_quality': fusion_quality,
            'modalities_available': {
                'docai': docai_embeddings is not None,
                'vision': vision_embeddings is not None
            }
        }
        
        if docai_embeddings is not None and vision_embeddings is not None:
            diagnostics['inter_modal_coherence'] = float(
                self._calculate_coherence(docai_embeddings, vision_embeddings)
            )
        
        if docai_embeddings is not None:
            diagnostics['docai_embedding_stats'] = {
                'mean': float(np.mean(docai_embeddings)),
                'std': float(np.std(docai_embeddings)),
                'norm': float(np.linalg.norm(docai_embeddings))
            }
        
        if vision_embeddings is not None:
            diagnostics['vision_embedding_stats'] = {
                'mean': float(np.mean(vision_embeddings)),
                'std': float(np.std(vision_embeddings)),
                'norm': float(np.linalg.norm(vision_embeddings))
            }
        
        # Add overall metrics
        diagnostics['fusion_metrics'] = self.fusion_metrics.copy()
        
        return diagnostics
    
    def get_fusion_metrics(self) -> Dict[str, Any]:
        """Get current fusion metrics."""
        return self.fusion_metrics.copy()
    
    def reset_metrics(self):
        """Reset fusion metrics."""
        self.fusion_metrics = {
            'total_fusions': 0,
            'successful_fusions': 0,
            'visual_only': 0,
            'docai_only': 0,
            'both_modalities': 0,
            'average_fusion_quality': 0.0
        }