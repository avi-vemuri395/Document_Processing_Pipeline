#!/usr/bin/env python3
"""
Comprehensive Test for DocAI Semantic-First Architecture
Tests the new mapping flow with various document types and evaluates output quality.

This test:
1. Processes different document types (PFS, Tax Returns, Excel, Management Bios)
2. Evaluates DocAI extraction quality
3. Tests semantic mapping accuracy
4. Compares with/without semantic mapping
5. Provides detailed analysis and metrics
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Set environment for testing
os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'  # Disable to isolate semantic mapping
os.environ['DOCAI_CONFIDENCE_THRESHOLD'] = '0.6'


def check_docai_authentication():
    """Check if DocAI authentication is configured before running tests."""
    print("\n" + "="*70)
    print("  CHECKING GOOGLE CLOUD AUTHENTICATION")
    print("="*70)
    
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError
        
        # Try to get default credentials
        credentials, project = default()
        print(f"  ✅ Authentication found: {type(credentials).__name__}")
        
        # Try to initialize DocAI client
        from google.cloud import documentai
        from google.api_core.client_options import ClientOptions
        
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        print(f"  ✅ DocAI client initialized successfully")
        
        # Check for processor IDs
        form_parser_id = os.getenv("DOCAI_FORM_PARSER_ID")
        if not form_parser_id:
            print("  ⚠️  Warning: DOCAI_FORM_PARSER_ID not set in .env")
            print("     DocAI will not work without processor IDs")
            return False
            
        return True
        
    except DefaultCredentialsError as e:
        print(f"  ❌ Authentication error: {e}")
        print("\n  To fix this, run:")
        print("     gcloud auth application-default login")
        print("\n  See GOOGLE_CLOUD_AUTH.md for more details")
        return False
        
    except Exception as e:
        print(f"  ❌ Failed to initialize DocAI: {e}")
        print("\n  Check your Google Cloud setup and .env configuration")
        return False


class SemanticMappingComprehensiveTest:
    """Comprehensive test suite for DocAI Semantic Mapping."""
    
    def __init__(self):
        self.test_id = f"semantic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {
            'document_types_tested': [],
            'docai_extraction_stats': {},
            'semantic_mapping_stats': {},
            'quality_metrics': {},
            'errors': [],
            'recommendations': []
        }
        
    async def run_comprehensive_test(self):
        """Run comprehensive test with various document types."""
        
        print("\n" + "="*80)
        print("  COMPREHENSIVE DOCAI SEMANTIC MAPPING TEST")
        print("="*80)
        print(f"  Test ID: {self.test_id}")
        print(f"  Start Time: {datetime.now().isoformat()}")
        
        # Phase 1: Test different document types
        await self.test_document_types()
        
        # Phase 2: Test semantic mapping quality
        await self.test_semantic_mapping_quality()
        
        # Phase 3: Compare with/without semantic mapping
        await self.test_with_without_comparison()
        
        # Phase 4: Analyze and report results
        self.analyze_results()
        
        return self.results
    
    async def test_document_types(self):
        """Test with various document types."""
        
        print("\n" + "─"*70)
        print("  PHASE 1: Document Type Testing")
        print("─"*70)
        
        from src.template_extraction.comprehensive_processor import ComprehensiveProcessor
        processor = ComprehensiveProcessor()
        
        # Define test documents of different types
        test_documents = [
            {
                'path': Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
                'type': 'Personal Financial Statement',
                'expected_fields': ['Name', 'Business Phone', 'Total Assets', 'Total Liabilities']
            },
            {
                'path': Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"),
                'type': 'Business Tax Return',
                'expected_fields': ['Employer Identification Number', 'Partnership Name', 'Total assets']
            },
            {
                'path': Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),
                'type': 'Excel Financial Statement',
                'expected_fields': ['Revenue', 'Expenses', 'Net Income']
            },
            {
                'path': Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),
                'type': 'Narrative Document',
                'expected_fields': []  # Narrative docs have less structured data
            }
        ]
        
        for doc_info in test_documents:
            if not doc_info['path'].exists():
                print(f"  ⚠️ Skipping {doc_info['type']}: File not found")
                continue
            
            print(f"\n  📄 Testing: {doc_info['type']}")
            print(f"     File: {doc_info['path'].name}")
            
            try:
                # Process document
                start_time = time.time()
                result = await processor.process_document(
                    doc_info['path'],
                    self.test_id
                )
                processing_time = time.time() - start_time
                
                # Analyze extraction
                docai_fields = self._count_docai_fields(result)
                
                stats = {
                    'document_type': doc_info['type'],
                    'file_name': doc_info['path'].name,
                    'processing_time': processing_time,
                    'docai_fields_extracted': docai_fields['count'],
                    'avg_confidence': docai_fields['avg_confidence'],
                    'extraction_method': result.get('metadata', {}).get('extraction_method', 'unknown')
                }
                
                self.results['document_types_tested'].append(doc_info['type'])
                self.results['docai_extraction_stats'][doc_info['type']] = stats
                
                print(f"     ✅ Processed in {processing_time:.2f}s")
                print(f"     • DocAI fields extracted: {docai_fields['count']}")
                print(f"     • Average confidence: {docai_fields['avg_confidence']:.2%}")
                print(f"     • Method: {stats['extraction_method']}")
                
            except Exception as e:
                print(f"     ❌ Error: {e}")
                self.results['errors'].append({
                    'document': doc_info['path'].name,
                    'error': str(e)
                })
    
    async def test_semantic_mapping_quality(self):
        """Test semantic mapping quality on extracted data."""
        
        print("\n" + "─"*70)
        print("  PHASE 2: Semantic Mapping Quality Testing")
        print("─"*70)
        
        from src.template_extraction.form_mapping_service import FormMappingService
        
        # Load master data from Phase 1
        master_file = Path(f"outputs/applications/{self.test_id}/part1_document_processing/master_data.json")
        
        if not master_file.exists():
            print("  ❌ No master data found from Phase 1")
            return
        
        with open(master_file, 'r') as f:
            master_data = json.load(f)
        
        # Test mapping for different forms
        service = FormMappingService()
        
        test_forms = [
            ("live_oak_application_v1", "Live Oak Application"),
            ("huntington_business_app_v1", "Huntington Business Application"),
            ("wells_fargo_loan_app_v1", "Wells Fargo Loan Application")
        ]
        
        for form_key, form_name in test_forms:
            print(f"\n  📋 Testing: {form_name}")
            
            form_spec = service.form_specs.get(form_key)
            if not form_spec:
                print(f"     ⚠️ Form spec not found")
                continue
            
            try:
                # Test semantic mapping
                start_time = time.time()
                result = await service._map_fields_to_form(
                    master_data, form_spec, form_key
                )
                mapping_time = time.time() - start_time
                
                # Analyze mapping quality
                mapped_fields = result.get('mapped_data', {})
                filled_count = len([v for v in mapped_fields.values() if v is not None])
                total_fields = len(form_spec.get('fields', []))
                coverage = (filled_count / total_fields * 100) if total_fields > 0 else 0
                
                stats = {
                    'form_name': form_name,
                    'total_fields': total_fields,
                    'filled_fields': filled_count,
                    'coverage_percentage': coverage,
                    'mapping_time': mapping_time,
                    'extraction_method': result.get('extraction_method', 'unknown'),
                    'overall_confidence': result.get('overall_confidence', 0.0)
                }
                
                self.results['semantic_mapping_stats'][form_key] = stats
                
                print(f"     ✅ Mapped in {mapping_time:.2f}s")
                print(f"     • Coverage: {filled_count}/{total_fields} ({coverage:.1f}%)")
                print(f"     • Confidence: {stats['overall_confidence']:.2%}")
                print(f"     • Method: {stats['extraction_method']}")
                
                # Show sample mappings
                if mapped_fields:
                    print(f"     • Sample mappings:")
                    for field, value in list(mapped_fields.items())[:3]:
                        if value:
                            print(f"       - {field}: {str(value)[:50]}")
                
            except Exception as e:
                print(f"     ❌ Error: {e}")
                self.results['errors'].append({
                    'form': form_name,
                    'error': str(e)
                })
    
    async def test_with_without_comparison(self):
        """Compare results with and without semantic mapping."""
        
        print("\n" + "─"*70)
        print("  PHASE 3: With/Without Semantic Mapping Comparison")
        print("─"*70)
        
        from src.template_extraction.form_mapping_service import FormMappingService
        
        # Load master data
        master_file = Path(f"outputs/applications/{self.test_id}/part1_document_processing/master_data.json")
        
        if not master_file.exists():
            print("  ❌ No master data found")
            return
        
        with open(master_file, 'r') as f:
            master_data = json.load(f)
        
        service = FormMappingService()
        test_form_key = "live_oak_application_v1"
        form_spec = service.form_specs.get(test_form_key)
        
        if not form_spec:
            print("  ❌ Form spec not found")
            return
        
        print(f"  📊 Comparing mapping approaches for Live Oak Application")
        
        # Test WITH semantic mapping
        os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
        print("\n  1️⃣ WITH Semantic Mapping:")
        
        try:
            with_result = await service._map_fields_to_form(
                master_data, form_spec, test_form_key
            )
            with_filled = len([v for v in with_result.get('mapped_data', {}).values() if v])
            with_confidence = with_result.get('overall_confidence', 0.0)
            
            print(f"     • Fields filled: {with_filled}")
            print(f"     • Confidence: {with_confidence:.2%}")
            print(f"     • Method: {with_result.get('extraction_method')}")
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
            with_filled = 0
            with_confidence = 0.0
        
        # Test WITHOUT semantic mapping (direct fallback)
        os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'false'
        os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'
        print("\n  2️⃣ WITHOUT Semantic Mapping (direct OpenAI):")
        
        # Force reinitialize to pick up environment change
        service._semantic_mapper = None
        
        try:
            without_result = await service._map_fields_to_form(
                master_data, form_spec, test_form_key
            )
            without_filled = len([v for v in without_result.get('mapped_data', {}).values() if v])
            without_confidence = without_result.get('overall_confidence', 0.0)
            
            print(f"     • Fields filled: {without_filled}")
            print(f"     • Confidence: {without_confidence:.2%}")
            print(f"     • Method: {without_result.get('extraction_method')}")
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
            without_filled = 0
            without_confidence = 0.0
        
        # Calculate improvement
        if without_filled > 0:
            improvement = ((with_filled - without_filled) / without_filled) * 100
        else:
            improvement = 100 if with_filled > 0 else 0
        
        self.results['quality_metrics']['comparison'] = {
            'with_semantic': {
                'fields_filled': with_filled,
                'confidence': with_confidence
            },
            'without_semantic': {
                'fields_filled': without_filled,
                'confidence': without_confidence
            },
            'improvement_percentage': improvement
        }
        
        print(f"\n  📈 IMPROVEMENT ANALYSIS:")
        print(f"     • Field coverage improvement: {improvement:.1f}%")
        print(f"     • Confidence delta: {(with_confidence - without_confidence):.2%}")
        
        if improvement > 20:
            print(f"     🚀 Significant improvement with semantic mapping!")
        elif improvement > 0:
            print(f"     ✅ Positive improvement with semantic mapping")
        else:
            print(f"     ⚠️ No improvement or regression detected")
    
    def _count_docai_fields(self, result: Dict) -> Dict:
        """Count DocAI fields and calculate average confidence."""
        
        count = 0
        confidences = []
        
        for category in ['personal_info', 'business_info', 'financial_data', 'tax_data', 'debt_schedules']:
            if category in result:
                for key, value in result[category].items():
                    if key.startswith('docai_') and isinstance(value, dict):
                        for field_name, field_data in value.items():
                            count += 1
                            if isinstance(field_data, dict) and 'confidence' in field_data:
                                confidences.append(field_data['confidence'])
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'count': count,
            'avg_confidence': avg_confidence
        }
    
    def analyze_results(self):
        """Analyze test results and provide recommendations."""
        
        print("\n" + "="*80)
        print("  TEST RESULTS ANALYSIS")
        print("="*80)
        
        # Document type analysis
        print("\n📄 DOCUMENT TYPE PERFORMANCE:")
        for doc_type, stats in self.results['docai_extraction_stats'].items():
            print(f"  • {doc_type}:")
            print(f"    - Fields extracted: {stats['docai_fields_extracted']}")
            print(f"    - Avg confidence: {stats['avg_confidence']:.2%}")
            print(f"    - Processing time: {stats['processing_time']:.2f}s")
        
        # Semantic mapping analysis
        print("\n🧠 SEMANTIC MAPPING PERFORMANCE:")
        for form_key, stats in self.results['semantic_mapping_stats'].items():
            print(f"  • {stats['form_name']}:")
            print(f"    - Coverage: {stats['coverage_percentage']:.1f}%")
            print(f"    - Confidence: {stats['overall_confidence']:.2%}")
            print(f"    - Mapping time: {stats['mapping_time']:.2f}s")
        
        # Quality metrics
        if 'comparison' in self.results['quality_metrics']:
            comp = self.results['quality_metrics']['comparison']
            print("\n📊 WITH/WITHOUT COMPARISON:")
            print(f"  • With semantic: {comp['with_semantic']['fields_filled']} fields")
            print(f"  • Without semantic: {comp['without_semantic']['fields_filled']} fields")
            print(f"  • Improvement: {comp['improvement_percentage']:.1f}%")
        
        # Generate recommendations
        self._generate_recommendations()
        
        if self.results['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in self.results['recommendations']:
                print(f"  • {rec}")
        
        # Save detailed results
        results_file = Path(f"semantic_test_results_{self.test_id}.json")
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
    
    def _generate_recommendations(self):
        """Generate recommendations based on test results."""
        
        # Check DocAI extraction quality
        for doc_type, stats in self.results['docai_extraction_stats'].items():
            if stats['avg_confidence'] < 0.7:
                self.results['recommendations'].append(
                    f"Consider improving DocAI extraction for {doc_type} (confidence: {stats['avg_confidence']:.2%})"
                )
        
        # Check semantic mapping coverage
        for form_key, stats in self.results['semantic_mapping_stats'].items():
            if stats['coverage_percentage'] < 60:
                self.results['recommendations'].append(
                    f"Low coverage for {stats['form_name']} ({stats['coverage_percentage']:.1f}%) - review field mappings"
                )
        
        # Check improvement metrics
        if 'comparison' in self.results['quality_metrics']:
            comp = self.results['quality_metrics']['comparison']
            if comp['improvement_percentage'] < 10:
                self.results['recommendations'].append(
                    "Semantic mapping showing minimal improvement - consider tuning prompts or consolidation logic"
                )
            elif comp['improvement_percentage'] > 50:
                self.results['recommendations'].append(
                    "Excellent improvement with semantic mapping - consider making it the default approach"
                )


async def main():
    """Run the comprehensive semantic mapping test."""
    
    # Check authentication first
    if not check_docai_authentication():
        print("\n❌ TEST ABORTED: Google Cloud authentication not configured")
        print("   Please authenticate first, then re-run the test")
        return False
    
    print("\n✅ Authentication verified, proceeding with test...")
    
    test = SemanticMappingComprehensiveTest()
    results = await test.run_comprehensive_test()
    
    # Return success/failure status
    return len(results.get('errors', [])) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)