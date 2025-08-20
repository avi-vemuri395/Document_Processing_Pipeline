#!/usr/bin/env python3
"""
Simple validation script for fusion components.
Runs without pytest dependency.
"""

import asyncio
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, '.')

# Import fusion components
from src.template_extraction.fusion import (
    VisualProjector,
    DocAIProjector,
    MultiHeadCrossAttention,
    FusionManager
)


def test_visual_projector():
    """Test visual projector functionality."""
    print("\n🧪 Testing VisualProjector...")
    
    projector = VisualProjector(output_dim=128)
    
    # Test with valid data
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
    
    assert embeddings is not None, "Embeddings should not be None"
    assert embeddings.shape == (128,), f"Expected shape (128,), got {embeddings.shape}"
    assert embeddings.dtype == np.float32, f"Expected float32, got {embeddings.dtype}"
    assert np.all(embeddings >= -1.0) and np.all(embeddings <= 1.0), "Embeddings not bounded [-1, 1]"
    
    print("  ✅ Visual projector working correctly")
    print(f"     • Output shape: {embeddings.shape}")
    print(f"     • Value range: [{embeddings.min():.3f}, {embeddings.max():.3f}]")
    
    return True


def test_docai_projector():
    """Test DocAI projector functionality."""
    print("\n🧪 Testing DocAIProjector...")
    
    projector = DocAIProjector(output_dim=128)
    
    # Test with DocAI result
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
    
    assert embeddings is not None, "Embeddings should not be None"
    assert embeddings.shape == (128,), f"Expected shape (128,), got {embeddings.shape}"
    assert embeddings.dtype == np.float32, f"Expected float32, got {embeddings.dtype}"
    assert np.all(embeddings >= -1.0) and np.all(embeddings <= 1.0), "Embeddings not bounded [-1, 1]"
    
    print("  ✅ DocAI projector working correctly")
    print(f"     • Output shape: {embeddings.shape}")
    print(f"     • Value range: [{embeddings.min():.3f}, {embeddings.max():.3f}]")
    
    return True


def test_cross_attention():
    """Test cross-attention mechanism."""
    print("\n🧪 Testing MultiHeadCrossAttention...")
    
    attention = MultiHeadCrossAttention(dim=64, num_heads=4)
    
    # Create sample embeddings
    query = np.random.randn(64).astype(np.float32)
    key = np.random.randn(64).astype(np.float32)
    value = np.random.randn(64).astype(np.float32)
    
    # Test with both modalities
    output = attention.forward(query, key, value)
    
    assert output.shape == (64,), f"Expected shape (64,), got {output.shape}"
    assert output.dtype == np.float32, f"Expected float32, got {output.dtype}"
    assert np.all(output >= -1.0) and np.all(output <= 1.0), "Output not bounded [-1, 1]"
    
    # Test with missing modality
    output_single = attention.forward(query, None, None)
    assert output_single.shape == (64,), "Single modality should still produce output"
    
    print("  ✅ Cross-attention working correctly")
    print(f"     • Attention heads: {attention.num_heads}")
    print(f"     • Head dimension: {attention.head_dim}")
    print(f"     • Output bounded: [{output.min():.3f}, {output.max():.3f}]")
    
    return True


async def test_fusion_manager():
    """Test fusion manager orchestration."""
    print("\n🧪 Testing FusionManager...")
    
    config = {
        'embedding_dim': 256,
        'num_attention_heads': 4,
        'enable_fusion': True
    }
    
    manager = FusionManager(config=config)
    
    # Test data
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
    
    # Test fusion
    fused = await manager.fuse_multimodal(
        docai_result=docai_result,
        vision_result=vision_result,
        document_path=Path('test.pdf'),
        return_diagnostics=True
    )
    
    assert fused is not None, "Fused result should not be None"
    assert 'fusion_metadata' in fused, "Should have fusion metadata"
    assert 'fusion_quality' in fused['fusion_metadata'], "Should have fusion quality score"
    assert 'fusion_diagnostics' in fused, "Should have diagnostics when requested"
    
    quality = fused['fusion_metadata']['fusion_quality']
    strategy = fused['fusion_metadata']['strategy']
    
    print("  ✅ Fusion manager working correctly")
    print(f"     • Fusion strategy: {strategy}")
    print(f"     • Fusion quality: {quality:.3f}")
    print(f"     • Processing time: {fused['fusion_metadata']['processing_time']:.3f}s")
    
    # Test metrics
    metrics = manager.get_fusion_metrics()
    print(f"     • Total fusions: {metrics['total_fusions']}")
    print(f"     • Successful fusions: {metrics['successful_fusions']}")
    
    return True


async def test_integration():
    """Test end-to-end fusion pipeline."""
    print("\n🧪 Testing End-to-End Integration...")
    
    # Create components
    visual_proj = VisualProjector(output_dim=512)
    docai_proj = DocAIProjector(output_dim=512)
    manager = FusionManager({'embedding_dim': 512})
    
    # Sample extraction results
    docai_result = {
        'success': True,
        'confidence': 0.92,
        'form_fields': {
            'applicant_ssn': {'value': '123-45-6789', 'confidence': 0.95},
            'business_name': {'value': 'Acme Corp', 'confidence': 0.88},
            'annual_revenue': {'value': '2500000', 'confidence': 0.76}
        },
        'tables': [
            {'headers': [['Year', 'Revenue']], 'rows': [['2023', '2500000']]}
        ]
    }
    
    vision_result = {
        'personal': {
            'ssn': '123-45-6789',
            'name': 'John Doe'
        },
        'business': {
            'name': 'Acme Corporation',
            'type': 'LLC'
        },
        'financials': {
            'annual_revenue': 2500000,
            'net_income': 500000
        }
    }
    
    # Perform fusion
    fused = await manager.fuse_multimodal(
        docai_result=docai_result,
        vision_result=vision_result,
        document_path=Path('sample_form.pdf'),
        return_diagnostics=True
    )
    
    # Validate results
    assert fused['fusion_metadata']['strategy'] == 'both', "Should use both modalities"
    assert fused['fusion_metadata']['has_docai'] == True
    assert fused['fusion_metadata']['has_vision'] == True
    
    # Check that DocAI tables are preserved
    assert 'docai_tables' in fused, "DocAI tables should be preserved"
    
    # Check embedding statistics
    assert 'embedding_stats' in fused, "Should have embedding statistics"
    
    print("  ✅ End-to-end integration successful")
    print(f"     • Fusion strategy: {fused['fusion_metadata']['strategy']}")
    print(f"     • Quality score: {fused['fusion_metadata']['fusion_quality']:.3f}")
    print(f"     • Combined modalities successfully")
    
    return True


async def main():
    """Run all validation tests."""
    print("=" * 60)
    print("🚀 FUSION COMPONENT VALIDATION")
    print("=" * 60)
    
    all_passed = True
    
    try:
        # Run synchronous tests
        all_passed &= test_visual_projector()
        all_passed &= test_docai_projector()
        all_passed &= test_cross_attention()
        
        # Run async tests
        all_passed &= await test_fusion_manager()
        all_passed &= await test_integration()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL FUSION COMPONENT TESTS PASSED!")
    else:
        print("❌ Some tests failed - review output above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)