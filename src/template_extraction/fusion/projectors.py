"""
Projection layers for multimodal fusion.

These projectors align different data modalities (visual, structured) into 
a shared embedding space where they can interact effectively.
"""

import numpy as np
from typing import Dict, Any, Optional, List
import json
import hashlib


class VisualProjector:
    """
    Projects visual features from Claude Vision into LLM embedding space.
    
    Visual features include:
    - Layout information
    - Table structures
    - Form field positions
    - Visual relationships
    """
    
    def __init__(self, output_dim: int = 4096):
        """
        Initialize visual projector.
        
        Args:
            output_dim: Target dimension for projected embeddings
        """
        self.output_dim = output_dim
        self.feature_extractors = {
            'layout': self._extract_layout_features,
            'tables': self._extract_table_features,
            'fields': self._extract_field_features,
            'relationships': self._extract_relationship_features
        }
    
    def project(self, vision_result: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Project visual extraction results to shared semantic space.
        
        Args:
            vision_result: Raw extraction from Claude Vision
            
        Returns:
            Projected embeddings or None if extraction failed
        """
        if not vision_result or vision_result.get('error'):
            return None
        
        # Extract features from different visual aspects
        feature_vectors = []
        
        for feature_type, extractor in self.feature_extractors.items():
            features = extractor(vision_result)
            if features is not None:
                feature_vectors.append(features)
        
        if not feature_vectors:
            return None
        
        # Combine features and project to target dimension
        combined = np.concatenate(feature_vectors)
        
        # Simple projection using hash-based pseudo-random projection
        # This maintains consistency while being computationally efficient
        projected = self._hash_project(combined, self.output_dim)
        
        return projected
    
    def _extract_layout_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract layout-based features."""
        features = []
        
        # Check for addresses (indicates form structure)
        if 'addresses' in result:
            features.append(len(result['addresses']))
        
        # Check for business structure
        if 'business' in result:
            features.append(1.0)
        else:
            features.append(0.0)
        
        # Check for financial data presence
        if 'financials' in result:
            financials = result['financials']
            features.extend([
                1.0 if 'assets' in str(financials).lower() else 0.0,
                1.0 if 'liabilities' in str(financials).lower() else 0.0,
                1.0 if 'income' in str(financials).lower() else 0.0
            ])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        return np.array(features, dtype=np.float32) if features else None
    
    def _extract_table_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract table structure features."""
        features = []
        
        # Count table-like structures in financials
        if 'financials' in result and isinstance(result['financials'], dict):
            # Count structured financial entries
            for key, value in result['financials'].items():
                if isinstance(value, (dict, list)):
                    features.append(1.0)
                else:
                    features.append(0.5)
        
        # Pad or truncate to fixed size
        target_size = 10
        if len(features) < target_size:
            features.extend([0.0] * (target_size - len(features)))
        else:
            features = features[:target_size]
        
        return np.array(features, dtype=np.float32) if features else None
    
    def _extract_field_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract form field features."""
        features = []
        
        # Count different field types
        field_counts = {
            'personal': 0,
            'business': 0,
            'financial': 0,
            'tax': 0,
            'debt': 0
        }
        
        # Analyze personal fields
        if 'personal' in result:
            field_counts['personal'] = self._count_fields(result['personal'])
        
        # Analyze business fields
        if 'business' in result:
            field_counts['business'] = self._count_fields(result['business'])
        
        # Analyze financial fields
        if 'financials' in result:
            field_counts['financial'] = self._count_fields(result['financials'])
        
        # Analyze tax fields
        if 'tax_information' in result or 'tax_data' in result:
            tax_data = result.get('tax_information') or result.get('tax_data')
            field_counts['tax'] = self._count_fields(tax_data)
        
        # Analyze debt fields
        if 'debt_details' in result or 'liabilities' in result:
            debt_data = result.get('debt_details') or result.get('liabilities')
            field_counts['debt'] = self._count_fields(debt_data)
        
        features = list(field_counts.values())
        
        return np.array(features, dtype=np.float32) if features else None
    
    def _extract_relationship_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract relationship features between fields."""
        features = []
        
        # Check for co-applicants (indicates relationships)
        has_coapplicants = 0.0
        if 'personal' in result and isinstance(result['personal'], dict):
            if 'co_applicants' in result['personal']:
                has_coapplicants = 1.0
        features.append(has_coapplicants)
        
        # Check for ownership percentages (indicates business relationships)
        has_ownership = 0.0
        if 'business' in result and isinstance(result['business'], dict):
            business_str = str(result['business']).lower()
            if 'ownership' in business_str or 'percentage' in business_str:
                has_ownership = 1.0
        features.append(has_ownership)
        
        # Check for multiple entities
        has_multiple_entities = 0.0
        if 'business' in result and isinstance(result['business'], dict):
            if 'entities' in result['business'] and isinstance(result['business']['entities'], list):
                if len(result['business']['entities']) > 1:
                    has_multiple_entities = 1.0
        features.append(has_multiple_entities)
        
        return np.array(features, dtype=np.float32) if features else None
    
    def _count_fields(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> int:
        """Recursively count non-empty fields."""
        if current_depth >= max_depth:
            return 0
        
        count = 0
        if isinstance(data, dict):
            for value in data.values():
                if value not in [None, "", [], {}]:
                    count += 1
                    if isinstance(value, (dict, list)):
                        count += self._count_fields(value, max_depth, current_depth + 1)
        elif isinstance(data, list):
            count = len(data)
        elif data not in [None, "", [], {}]:
            count = 1
        
        return count
    
    def _hash_project(self, features: np.ndarray, target_dim: int) -> np.ndarray:
        """
        Project features to target dimension using hash-based projection.
        This is deterministic and doesn't require learned parameters.
        """
        # Ensure we have enough features
        if len(features) < target_dim:
            # Pad with zeros if needed
            padded = np.zeros(target_dim, dtype=np.float32)
            padded[:len(features)] = features
            features = padded
        
        # Create deterministic projection matrix using hash
        projection = np.zeros((len(features), target_dim), dtype=np.float32)
        
        for i in range(len(features)):
            for j in range(target_dim):
                # Create deterministic random value using hash
                hash_input = f"{i}:{j}:projection".encode()
                hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
                
                # Convert to Gaussian-like value
                normalized = (hash_value % 10000) / 10000.0
                projection[i, j] = np.sqrt(2) * (normalized - 0.5)
        
        # Project features
        projected = np.dot(features, projection)
        
        # Apply non-linearity (tanh for bounded output)
        projected = np.tanh(projected / np.sqrt(target_dim))
        
        return projected.astype(np.float32)


class DocAIProjector:
    """
    Projects DocAI structured data into LLM embedding space.
    
    DocAI features include:
    - Form fields (key-value pairs)
    - Tables with headers and rows
    - Entities (names, dates, amounts)
    - Confidence scores
    """
    
    def __init__(self, output_dim: int = 4096):
        """
        Initialize DocAI projector.
        
        Args:
            output_dim: Target dimension for projected embeddings
        """
        self.output_dim = output_dim
        self.feature_extractors = {
            'form_fields': self._extract_form_field_features,
            'tables': self._extract_table_features,
            'entities': self._extract_entity_features,
            'confidence': self._extract_confidence_features
        }
    
    def project(self, docai_result: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Project DocAI extraction results to shared semantic space.
        
        Args:
            docai_result: Raw extraction from DocAI
            
        Returns:
            Projected embeddings or None if extraction failed
        """
        if not docai_result or not docai_result.get('success'):
            return None
        
        # Extract features from different DocAI components
        feature_vectors = []
        
        for feature_type, extractor in self.feature_extractors.items():
            features = extractor(docai_result)
            if features is not None:
                feature_vectors.append(features)
        
        if not feature_vectors:
            return None
        
        # Combine features and project to target dimension
        combined = np.concatenate(feature_vectors)
        
        # Project using hash-based method (same as visual for consistency)
        projected = self._hash_project(combined, self.output_dim)
        
        return projected
    
    def _extract_form_field_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract features from form fields."""
        features = []
        
        form_fields = result.get('form_fields', {})
        
        # Categorize fields
        field_categories = {
            'personal': 0,
            'business': 0,
            'financial': 0,
            'tax': 0,
            'debt': 0,
            'other': 0
        }
        
        for field_name, field_data in form_fields.items():
            field_lower = field_name.lower()
            
            # Simple categorization based on keywords
            if any(kw in field_lower for kw in ['ssn', 'name', 'address', 'phone', 'email', 'dob']):
                field_categories['personal'] += 1
            elif any(kw in field_lower for kw in ['business', 'company', 'ein', 'entity', 'ownership']):
                field_categories['business'] += 1
            elif any(kw in field_lower for kw in ['asset', 'liability', 'income', 'revenue', 'expense']):
                field_categories['financial'] += 1
            elif any(kw in field_lower for kw in ['tax', '1040', '1065', 'irs', 'return']):
                field_categories['tax'] += 1
            elif any(kw in field_lower for kw in ['loan', 'debt', 'mortgage', 'credit', 'payment']):
                field_categories['debt'] += 1
            else:
                field_categories['other'] += 1
        
        # Add counts as features
        features.extend(list(field_categories.values()))
        
        # Add total field count
        features.append(len(form_fields))
        
        return np.array(features, dtype=np.float32) if features else None
    
    def _extract_table_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract features from tables."""
        features = []
        
        tables = result.get('tables', [])
        
        # Table statistics
        features.append(len(tables))  # Number of tables
        
        if tables:
            # Average rows per table
            avg_rows = np.mean([len(t.get('rows', [])) for t in tables])
            features.append(avg_rows)
            
            # Average columns (from headers)
            avg_cols = np.mean([len(t.get('headers', [[]])[0]) if t.get('headers') else 0 for t in tables])
            features.append(avg_cols)
            
            # Check for financial tables
            financial_tables = 0
            for table in tables:
                headers_str = str(table.get('headers', [])).lower()
                if any(kw in headers_str for kw in ['amount', 'balance', 'total', 'asset', 'liability']):
                    financial_tables += 1
            features.append(financial_tables)
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Pad to fixed size
        target_size = 10
        if len(features) < target_size:
            features.extend([0.0] * (target_size - len(features)))
        else:
            features = features[:target_size]
        
        return np.array(features, dtype=np.float32)
    
    def _extract_entity_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract features from entities."""
        features = []
        
        entities = result.get('entities', [])
        
        # Entity type counts
        entity_types = {
            'PERSON': 0,
            'ORGANIZATION': 0,
            'LOCATION': 0,
            'DATE': 0,
            'MONEY': 0,
            'PERCENTAGE': 0,
            'OTHER': 0
        }
        
        for entity in entities:
            entity_type = entity.get('type', 'OTHER')
            if entity_type in entity_types:
                entity_types[entity_type] += 1
            else:
                entity_types['OTHER'] += 1
        
        features.extend(list(entity_types.values()))
        
        # Total entity count
        features.append(len(entities))
        
        return np.array(features, dtype=np.float32)
    
    def _extract_confidence_features(self, result: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract confidence-related features."""
        features = []
        
        # Overall confidence
        features.append(result.get('confidence', 0.0))
        
        # Form field confidence statistics
        form_fields = result.get('form_fields', {})
        if form_fields:
            confidences = []
            for field_data in form_fields.values():
                if isinstance(field_data, dict) and 'confidence' in field_data:
                    confidences.append(field_data['confidence'])
            
            if confidences:
                features.extend([
                    np.mean(confidences),
                    np.min(confidences),
                    np.max(confidences),
                    np.std(confidences)
                ])
            else:
                features.extend([0.0, 0.0, 0.0, 0.0])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Processing metadata
        features.append(1.0 if result.get('pages', 0) > 0 else 0.0)
        features.append(result.get('pages', 0) / 100.0)  # Normalized page count
        
        return np.array(features, dtype=np.float32)
    
    def _hash_project(self, features: np.ndarray, target_dim: int) -> np.ndarray:
        """
        Project features to target dimension using hash-based projection.
        Same implementation as VisualProjector for consistency.
        """
        # Ensure we have enough features
        if len(features) < target_dim:
            padded = np.zeros(target_dim, dtype=np.float32)
            padded[:len(features)] = features
            features = padded
        
        # Create deterministic projection matrix
        projection = np.zeros((len(features), target_dim), dtype=np.float32)
        
        for i in range(len(features)):
            for j in range(target_dim):
                hash_input = f"{i}:{j}:docai_projection".encode()
                hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
                normalized = (hash_value % 10000) / 10000.0
                projection[i, j] = np.sqrt(2) * (normalized - 0.5)
        
        # Project and apply non-linearity
        projected = np.dot(features, projection)
        projected = np.tanh(projected / np.sqrt(target_dim))
        
        return projected.astype(np.float32)