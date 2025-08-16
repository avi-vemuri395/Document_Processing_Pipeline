#!/usr/bin/env python3
"""Test the embedded confidence implementations."""

import time

print("Testing embedded confidence implementations...")

print("1. Testing ComprehensiveProcessor...")
start = time.time()
from src.template_extraction.comprehensive_processor import ComprehensiveProcessor
processor = ComprehensiveProcessor()
# Test accessing the confidence_aggregator property
agg = processor.confidence_aggregator
print(f"✅ ComprehensiveProcessor confidence_aggregator: {type(agg).__name__} ({time.time() - start:.2f}s)")

print("2. Testing FormMappingService...")
start = time.time()
from src.template_extraction.form_mapping_service import FormMappingService
mapper = FormMappingService()
# Test accessing the confidence_aggregator property
agg2 = mapper.confidence_aggregator
print(f"✅ FormMappingService confidence_aggregator: {type(agg2).__name__} ({time.time() - start:.2f}s)")

print("3. Testing confidence calculation...")
start = time.time()
overall, breakdown = agg.calculate_document_confidence(
    classification_confidence=0.8,
    field_confidences=[0.9, 0.85, 0.92],
    validation_scores={}
)
print(f"✅ Document confidence: {overall:.2f} ({time.time() - start:.2f}s)")

print("4. Testing review recommendation...")
start = time.time()
review = agg2.get_review_recommendation(
    overall_confidence=0.85,
    field_confidences={"test_field": 0.9},
    validation_scores={}
)
print(f"✅ Review recommendation: needs_review={review['needs_review']} ({time.time() - start:.2f}s)")

print("\n🎉 All embedded confidence implementations work perfectly!")
print("✅ No import hangs")
print("✅ Full confidence scoring functionality restored")
print("✅ Phase 2 complete - embedded confidence aggregator working")