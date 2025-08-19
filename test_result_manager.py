#!/usr/bin/env python3
"""
Simple Test Result Manager for Document Processing Pipeline Tests
Handles persistence and basic analysis of test results.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


class TestResultManager:
    """
    Simple manager for saving and organizing test results.
    Keeps it minimal - just timestamped directories and JSON persistence.
    """
    
    def __init__(self, base_output_dir: str = "outputs"):
        """Initialize with base output directory"""
        self.base_dir = Path(base_output_dir)
        self.test_results_dir = self.base_dir / "test_results"
        self.current_run_dir = None
        self.run_timestamp = None
        
    def start_test_run(self, test_suite_name: str = "enhanced_benchmark_test") -> Path:
        """Start a new test run with timestamped directory"""
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir_name = f"{self.run_timestamp}_{test_suite_name}"
        self.current_run_dir = self.test_results_dir / run_dir_name
        
        # Create directory structure
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different test types
        (self.current_run_dir / "backward_compatibility").mkdir(exist_ok=True)
        (self.current_run_dir / "document_routing").mkdir(exist_ok=True)
        (self.current_run_dir / "mixed_processing").mkdir(exist_ok=True)
        (self.current_run_dir / "rate_limiting").mkdir(exist_ok=True)
        
        print(f"📁 Test results will be saved to: {self.current_run_dir}")
        return self.current_run_dir
    
    def save_test_result(self, test_name: str, test_category: str, 
                        extraction_result: Dict[str, Any], 
                        metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Save individual test result with metadata"""
        if not self.current_run_dir:
            raise RuntimeError("Must call start_test_run() first")
        
        # Prepare result data
        result_data = {
            "test_name": test_name,
            "test_category": test_category,
            "timestamp": datetime.now().isoformat(),
            "extraction_result": extraction_result,
            "metadata": metadata or {}
        }
        
        # Save to appropriate subdirectory
        category_dir = self.current_run_dir / test_category
        result_file = category_dir / f"{test_name}.json"
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        print(f"💾 Saved {test_name} results to: {result_file}")
        return result_file
    
    def save_routing_decision(self, document_name: str, document_type: str, 
                            expected_processor: str, actual_processor: str,
                            extraction_result: Dict[str, Any]) -> Path:
        """Save routing decision analysis"""
        routing_data = {
            "document_name": document_name,
            "document_type": document_type,
            "expected_processor": expected_processor,
            "actual_processor": actual_processor,
            "routing_correct": expected_processor == actual_processor,
            "timestamp": datetime.now().isoformat(),
            "extraction_result": extraction_result
        }
        
        routing_file = self.current_run_dir / "document_routing" / f"{document_name}_routing.json"
        with open(routing_file, 'w') as f:
            json.dump(routing_data, f, indent=2, default=str)
        
        print(f"🚦 Saved routing decision for {document_name}")
        return routing_file
    
    def save_test_run_summary(self, summary_data: Dict[str, Any]) -> Path:
        """Save overall test run summary"""
        if not self.current_run_dir:
            raise RuntimeError("Must call start_test_run() first")
        
        summary_data["run_timestamp"] = self.run_timestamp
        summary_data["run_directory"] = str(self.current_run_dir)
        summary_data["summary_created"] = datetime.now().isoformat()
        
        summary_file = self.current_run_dir / "test_run_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        print(f"📊 Saved test run summary to: {summary_file}")
        return summary_file
    
    def get_extraction_stats(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic stats from extraction result"""
        stats = {
            "total_files_processed": 0,
            "total_fields_extracted": 0,
            "processing_time": 0,
            "processors_used": [],
            "file_details": {}
        }
        
        # Get metadata if available
        metadata = extraction_result.get('_metadata', {})
        if metadata:
            stats["processing_time"] = metadata.get('processing_time', 0)
            stats["total_files_processed"] = metadata.get('documents_processed', 0)
            stats["processors_used"] = [
                f"Excel: {metadata.get('excel_files_processed', 0)} files",
                f"DocAI: {metadata.get('docai_processed', 0)} files", 
                f"Claude: {metadata.get('claude_vision_processed', 0)} files"
            ]
        
        # Count fields in each file
        for key, value in extraction_result.items():
            if not key.startswith('_') and isinstance(value, dict):
                field_count = len([k for k in value.keys() if not k.startswith('_')])
                stats["file_details"][key] = {
                    "fields_extracted": field_count,
                    "has_metadata": "_metadata" in value
                }
                stats["total_fields_extracted"] += field_count
        
        return stats
    
    def print_results_location(self):
        """Print where results were saved"""
        if self.current_run_dir:
            print(f"\n📁 Test results saved in: {self.current_run_dir}")
            print(f"   • Backward compatibility: {self.current_run_dir / 'backward_compatibility'}")
            print(f"   • Document routing: {self.current_run_dir / 'document_routing'}")  
            print(f"   • Mixed processing: {self.current_run_dir / 'mixed_processing'}")
            print(f"   • Test run summary: {self.current_run_dir / 'test_run_summary.json'}")