"""
Pytest configuration for the document processing pipeline tests.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the Python path so tests can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_documents():
    """Provide paths to sample test documents."""
    test_dir = project_root / "inputs" / "real" / "Brigham_dallas"
    
    if test_dir.exists():
        return list(test_dir.glob("*.pdf"))[:3]  # Return first 3 PDFs
    else:
        pytest.skip("Test documents not available")


@pytest.fixture
def output_dir():
    """Provide a clean output directory for tests."""
    output_path = project_root / "outputs" / "test_outputs"
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path