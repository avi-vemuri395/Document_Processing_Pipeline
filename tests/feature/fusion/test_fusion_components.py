"""
Unit tests for Projection-Based Fusion components.

Tests the multimodal fusion pipeline including projectors, cross-attention,
and fusion management.
"""

import asyncio
import json
import numpy as np
import pytest
from pathlib import Path
from typing import Dict, Any

# Import fusion components
from src.template_extraction.fusion import (
    VisualProjector,
    DocAIProjector,
    MultiHeadCrossAttention,
    FusionManager
)
from src.template_extraction.fusion.cross_attention import SimplifiedCrossAttention


class TestVisualProjector:
    """Test visual feature projection."""
    
    def test_visual_projector_initialization(self):
        """Test projector initializes correctly."""
        projector = VisualProjector(output_dim=2048)
        assert projector.output_dim == 2048
        assert len(projector.feature_extractors) == 4
    
    def test_visual_projection_with_valid_data(self):
        """Test projection with valid vision results."""
        projector = VisualProjector(output_dim=128)
        
        # Sample vision result
        vision_result = {
            'personal': {
                'name': 'John Doe',
                'ssn': '123-45-6789'
            },
            'business': {
                'name': 'Acme Corp',
                'ein': '12-3456789'
            },
            'financials': {
                'assets': {'total': 1000000},
                'liabilities': {'total': 500000}
            }
        }
        
        embeddings = projector.project(vision_result)
        
        assert embeddings is not None
        assert embeddings.shape == (128,)
        assert embeddings.dtype == np.float32
        # Check bounded output (tanh activation)
        assert np.all(embeddings >= -1.0) and np.all(embeddings <= 1.0)
    
    def test_visual_projection_with_error_result(self):
        """Test projection handles error results properly."""
        projector = VisualProjector()
        
        error_result = {'error': 'API rate limit exceeded'}
        embeddings = projector.project(error_result)
        
        assert embeddings is None
    
    def test_field_counting(self):
        """Test recursive field counting logic."""
        projector = VisualProjector()
        
        test_data = {
            'level1': {
                'level2': {
                    'field1': 'value',
                    'field2': None,  # Should not count
                    'level3': {
                        'field3': 'value'
                    }
                }
            }
        }
        
        count = projector._count_fields(test_data, max_depth=3)
        assert count == 3  # field1, level3 dict, field3


class TestDocAIProjector:
    """Test DocAI feature projection."""
    
    def test_docai_projector_initialization(self):
        """Test projector initializes correctly."""
        projector = DocAIProjector(output_dim=2048)
        assert projector.output_dim == 2048
        assert len(projector.feature_extractors) == 4
    
    def test_docai_projection_with_form_fields(self):
        """Test projection with DocAI form fields."""
        projector = DocAIProjector(output_dim=128)
        
        # Sample DocAI result
        docai_result = {
            'success': True,
            'confidence': 0.85,
            'form_fields': {
                'applicant_name': {'value': 'John Doe', 'confidence': 0.9},
                'business_ein': {'value': '12-3456789', 'confidence': 0.95},
                'annual_revenue': {'value': '1000000', 'confidence': 0.8}
            },
            'tables': [
                {
                    'headers': [['Asset', 'Amount']],
                    'rows': [['Cash', '100000'], ['Equipment', '50000']]
                }
            ],
            'entities': [
                {'type': 'PERSON', 'text': 'John Doe'},
                {'type': 'ORGANIZATION', 'text': 'Acme Corp'}
            ]
        }
        
        embeddings = projector.project(docai_result)
        
        assert embeddings is not None
        assert embeddings.shape == (128,)
        assert embeddings.dtype == np.float32
        # Check bounded output
        assert np.all(embeddings >= -1.0) and np.all(embeddings <= 1.0)
    
    def test_docai_projection_with_failed_result(self):
        """Test projection handles failed results."""
        projector = DocAIProjector()
        
        failed_result = {'success': False, 'error': 'Document too large'}
        embeddings = projector.project(failed_result)
        
        assert embeddings is None
    
    def test_field_categorization(self):
        """Test form field categorization logic."""
        projector = DocAIProjector()
        
        result = {
            'success': True,
            'form_fields': {
                'ssn': 'xxx-xx-xxxx',
                'business_name': 'Acme',
                'total_assets': '1000000',
                'tax_year_2023': '2023',
                'loan_amount': '500000',
                'random_field': 'value'
            }
        }
        
        features = projector._extract_form_field_features(result)
        assert features is not None
        # Check that fields are categorized (personal, business, financial, tax, debt, other)
        assert len(features) == 7  # 6 categories + total count


class TestCrossAttention:
    """Test cross-attention mechanisms."""
    
    def test_multihead_attention_initialization(self):
        """Test multi-head attention initialization."""
        attention = MultiHeadCrossAttention(dim=256, num_heads=8)
        assert attention.dim == 256
        assert attention.num_heads == 8
        assert attention.head_dim == 32
    
    def test_multihead_attention_with_both_modalities(self):
        """Test attention with both modalities present."""
        attention = MultiHeadCrossAttention(dim=64, num_heads=4)
        
        query = np.random.randn(64).astype(np.float32)
        key = np.random.randn(64).astype(np.float32)
        value = np.random.randn(64).astype(np.float32)
        
        output = attention.forward(query, key, value)
        
        assert output.shape == (64,)
        assert output.dtype == np.float32
        # Check output is bounded by tanh
        assert np.all(output >= -1.0) and np.all(output <= 1.0)
    
    def test_multihead_attention_with_missing_modality(self):
        """Test attention handles missing modalities."""
        attention = MultiHeadCrossAttention(dim=64, num_heads=4)
        
        query = np.random.randn(64).astype(np.float32)
        
        # Only query available (vision only)
        output = attention.forward(query, None, None)
        assert output.shape == (64,)
        
        # Only key/value available (DocAI only)
        output = attention.forward(None, query, query)
        assert output.shape == (64,)
        
        # No data available
        output = attention.forward(None, None, None)
        assert output.shape == (64,)
        assert np.all(output == 0)
    
    def test_simplified_attention(self):
        """Test simplified cross-attention."""
        attention = SimplifiedCrossAttention(dim=64)
        
        visual = np.random.randn(64).astype(np.float32)
        docai = np.random.randn(64).astype(np.float32)
        
        output = attention.forward(visual, docai)
        
        assert output.shape == (64,)
        assert output.dtype == np.float32
        # Check bounded output
        assert np.all(output >= -1.0) and np.all(output <= 1.0)


class TestFusionManager:
    """Test fusion orchestration."""
    
    @pytest.mark.asyncio
    async def test_fusion_manager_initialization(self):
        """Test manager initializes with config."""
        config = {
            'embedding_dim': 512,
            'num_attention_heads': 4,
            'use_simplified_attention': True,
            'enable_fusion': True
        }
        
        manager = FusionManager(config=config)
        
        assert manager.config['embedding_dim'] == 512
        assert manager.config['num_attention_heads'] == 4
        assert manager.config['use_simplified_attention'] == True
        assert isinstance(manager.attention, SimplifiedCrossAttention)
    
    @pytest.mark.asyncio
    async def test_fusion_with_both_modalities(self):
        """Test fusion with both DocAI and vision results."""
        manager = FusionManager()
        
        docai_result = {
            'success': True,
            'confidence': 0.9,
            'form_fields': {
                'name': 'John Doe',
                'ein': '12-3456789'
            }
        }
        
        vision_result = {
            'personal': {'name': 'John Doe'},
            'business': {'ein': '12-3456789'},
            'financials': {'revenue': 1000000}
        }
        
        fused = await manager.fuse_multimodal(
            docai_result=docai_result,
            vision_result=vision_result,
            document_path=Path('test.pdf'),
            return_diagnostics=True
        )
        
        assert fused is not None
        assert 'fusion_metadata' in fused
        assert fused['fusion_metadata']['strategy'] in ['both', 'docai_only', 'vision_only']
        assert 'fusion_quality' in fused['fusion_metadata']
        assert 'fusion_diagnostics' in fused
    
    @pytest.mark.asyncio
    async def test_fusion_with_single_modality(self):
        """Test fusion with only one modality available."""
        manager = FusionManager()
        
        vision_result = {
            'personal': {'name': 'John Doe'},
            'business': {'ein': '12-3456789'}
        }
        
        # Only vision available
        fused = await manager.fuse_multimodal(
            docai_result=None,
            vision_result=vision_result,
            document_path=Path('test.pdf')
        )
        
        assert fused is not None
        assert fused['fusion_metadata']['strategy'] == 'vision_only'
        assert fused['extraction_mode'] == 'vision'
    
    @pytest.mark.asyncio
    async def test_fusion_disabled(self):
        """Test fusion can be disabled via config."""
        config = {'enable_fusion': False}
        manager = FusionManager(config=config)
        
        docai_result = {'success': True, 'data': 'docai'}
        vision_result = {'data': 'vision'}
        
        fused = await manager.fuse_multimodal(
            docai_result=docai_result,
            vision_result=vision_result,
            document_path=Path('test.pdf')
        )
        
        # Should return DocAI result without fusion
        assert fused == docai_result
    
    @pytest.mark.asyncio
    async def test_fusion_metrics_tracking(self):
        """Test fusion metrics are tracked correctly."""
        manager = FusionManager()
        
        # Reset metrics
        manager.reset_metrics()
        initial_metrics = manager.get_fusion_metrics()
        assert initial_metrics['total_fusions'] == 0
        
        # Perform fusion
        await manager.fuse_multimodal(
            docai_result={'success': True, 'data': 'test'},
            vision_result={'data': 'test'},
            document_path=Path('test.pdf')
        )
        
        # Check metrics updated
        metrics = manager.get_fusion_metrics()
        assert metrics['total_fusions'] == 1
        assert metrics['successful_fusions'] >= 0
    
    @pytest.mark.asyncio
    async def test_fusion_quality_calculation(self):
        """Test fusion quality score calculation."""
        manager = FusionManager()
        
        # Create mock embeddings
        docai_emb = np.random.randn(4096).astype(np.float32)
        vision_emb = np.random.randn(4096).astype(np.float32)
        fused_emb = (docai_emb + vision_emb) / 2  # Simple average
        
        quality = manager._calculate_fusion_quality(
            docai_emb, vision_emb, fused_emb
        )
        
        assert isinstance(quality, float)
        assert 0.0 <= quality <= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])