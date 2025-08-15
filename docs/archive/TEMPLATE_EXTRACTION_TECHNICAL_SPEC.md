# Template-Based Extraction: Technical Specification

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Document  │  │Template  │  │Extraction│  │Result    │   │
│  │Classifier│→ │Registry  │→ │Pipeline  │→ │Processor │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     Extraction Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │AcroForm  │  │Checkbox  │  │Anchor    │  │OCR       │   │
│  │Extractor │  │Extractor │  │Extractor │  │Extractor │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Table     │  │Date      │  │Money     │  │Zone      │   │
│  │Extractor │  │Extractor │  │Extractor │  │Extractor │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Normalization Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Field     │  │LLM       │  │Validation│  │Confidence│   │
│  │Normalizer│  │Normalizer│  │Engine    │  │Scorer    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Cache     │  │Canonical │  │Audit     │  │Export    │   │
│  │Manager   │  │Store     │  │Trail     │  │Service   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Document Classifier

**Purpose**: Analyze documents and determine optimal extraction strategy.

```python
class DocumentClassifier:
    """
    Classifies documents for routing to appropriate extractors.
    """
    
    def classify(self, pdf_path: Path) -> DocumentClassification:
        """
        Returns:
            DocumentClassification with:
            - type: 'digital' | 'scanned' | 'mixed' | 'image'
            - has_text_layer: bool
            - has_form_fields: bool
            - has_tables: bool
            - page_types: List[PageType]
            - confidence: float
            - recommended_extractors: List[str]
        """
```

**Classification Logic**:
1. Check PDF for text layer
2. Count form fields (AcroForm)
3. Analyze image/text ratio
4. Detect tables
5. Identify page types (form, statement, letter)

### 2. Template Registry

**Purpose**: Manage form templates and match documents to templates.

```python
class TemplateRegistry:
    """
    Central registry for all form templates.
    """
    
    def match_document(self, pdf_path: Path) -> Optional[FormTemplate]:
        """
        Match a document to a template using:
        - Filename patterns
        - Page count
        - Text fingerprinting
        - Form field names
        - Visual layout matching
        """
    
    def get_template(self, template_id: str, version: str = 'latest') -> FormTemplate:
        """
        Retrieve a specific template with version control.
        """
```

**Template Matching Algorithm**:
1. Fast match: filename patterns
2. Structure match: page count, field count
3. Content match: text fingerprinting
4. Layout match: visual similarity
5. Confidence scoring

### 3. Extraction Pipeline

**Purpose**: Coordinate multiple extractors for optimal results.

```python
class ExtractionPipeline:
    """
    Manages the extraction process using multiple strategies.
    """
    
    def extract(self, 
                document: Document,
                template: FormTemplate,
                strategies: List[str] = None) -> ExtractionResult:
        """
        Execute extraction with:
        - Strategy selection based on document type
        - Parallel execution where possible
        - Result merging and conflict resolution
        - Confidence aggregation
        """
```

**Extraction Strategy Selection**:

| Document Type | Primary | Secondary | Fallback |
|--------------|---------|-----------|----------|
| Digital PDF with forms | AcroForm | Anchor | Zone |
| Digital PDF no forms | Anchor | Table | OCR |
| Scanned PDF | OCR | Zone | LLM |
| Image | OCR | Zone | LLM |
| Mixed | AcroForm + OCR | Anchor | LLM |

---

## Extractor Specifications

### AcroForm Extractor

**Capabilities**:
- Direct field value extraction
- Field type detection
- Option/choice extraction
- Field validation state

**Algorithm**:
```python
def extract_acroform(pdf: PdfReader, template: FormTemplate):
    fields = pdf.get_form_fields()
    results = {}
    
    for template_field in template.fields:
        # Try exact match
        if template_field.acroform_name in fields:
            results[template_field.id] = fields[template_field.acroform_name]
        # Try fuzzy match
        elif match := fuzzy_match(template_field, fields):
            results[template_field.id] = match.value
    
    return results
```

### OCR Extractor

**Capabilities**:
- Multi-language support
- Zone-based extraction
- Confidence scoring
- Image preprocessing

**OCR Pipeline**:
```python
def extract_ocr(image: Image, template: FormTemplate):
    # Preprocess
    image = enhance_image(image)  # Deskew, denoise, contrast
    
    # Run OCR
    ocr_results = easyocr.readtext(image)
    
    # Extract by zones
    for field in template.fields:
        if field.zone:
            zone_text = extract_zone(ocr_results, field.zone)
            results[field.id] = zone_text
    
    # Extract by anchors
    for field in template.fields:
        if field.anchor:
            anchor_text = find_anchor(ocr_results, field.anchor)
            value = extract_near_anchor(ocr_results, anchor_text, field.strategy)
            results[field.id] = value
    
    return results
```

### Table Extractor

**Capabilities**:
- Multiple table detection strategies
- Header recognition
- Cell merging handling
- Multi-page tables

**Table Extraction Strategies**:

```python
class TableExtractor:
    strategies = [
        PDFPlumberStrategy(),    # Best for digital PDFs
        CamelotStrategy(),       # Good for complex tables
        OCRTableStrategy(),      # For scanned tables
        LlamaParseStrategy()     # Fallback for complex cases
    ]
    
    def extract_table(self, document: Document, table_spec: TableSpec):
        for strategy in self.strategies:
            if strategy.can_handle(document):
                table = strategy.extract(document, table_spec)
                if table.confidence > threshold:
                    return table
        
        return None
```

---

## Field Types & Normalization

### Supported Field Types

| Type | Extraction | Normalization | Validation |
|------|------------|---------------|------------|
| text | Direct/OCR | Trim, case | Length, pattern |
| number | Direct/OCR | Parse, format | Range, precision |
| date | Pattern match | Parse, standardize | Format, range |
| email | Pattern match | Lowercase, trim | RFC compliance |
| phone | Pattern match | Format, country code | Length, format |
| money | Pattern match | Parse, currency | Range, format |
| percentage | Pattern match | Parse, decimal | 0-100 range |
| ssn | Pattern match | Mask, format | Checksum |
| ein | Pattern match | Format | Checksum |
| address | Multi-line | Parse components | USPS validation |
| checkbox | State detection | Boolean | Required |
| radio | Group detection | Enum value | Options |
| signature | Image detection | Presence | Required |

### Normalization Pipeline

```python
class FieldNormalizer:
    def normalize(self, value: Any, field_spec: FieldSpec) -> NormalizedValue:
        # Step 1: Type conversion
        value = self.convert_type(value, field_spec.type)
        
        # Step 2: Format normalization
        value = self.apply_format(value, field_spec.format)
        
        # Step 3: Business rules
        value = self.apply_rules(value, field_spec.rules)
        
        # Step 4: Validation
        errors = self.validate(value, field_spec.validation)
        
        return NormalizedValue(
            value=value,
            original=original_value,
            errors=errors,
            confidence=confidence
        )
```

---

## Template Specification Format

### Complete Template Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["form_id", "version", "fields"],
  "properties": {
    "form_id": {
      "type": "string",
      "pattern": "^[a-z_]+$"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d{4}\\.\\d{2}$"
    },
    "form_title": {
      "type": "string"
    },
    "fingerprint": {
      "type": "object",
      "properties": {
        "pages": {"type": "integer"},
        "fields_count": {"type": "integer"},
        "text_hash": {"type": "string"},
        "layout_hash": {"type": "string"}
      }
    },
    "fields": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/field"
      }
    },
    "tables": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/table"
      }
    },
    "validation_rules": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/validation_rule"
      }
    }
  },
  "definitions": {
    "field": {
      "type": "object",
      "required": ["id", "field_name", "type"],
      "properties": {
        "id": {"type": "string"},
        "field_name": {"type": "string"},
        "type": {"enum": ["text", "number", "date", "email", "phone", "money", "percentage", "ssn", "ein", "address", "checkbox", "radio", "signature"]},
        "required": {"type": "boolean"},
        "page": {"type": "integer"},
        "extraction": {
          "type": "object",
          "properties": {
            "acroform": {"type": "array", "items": {"type": "string"}},
            "anchors": {"type": "array", "items": {"$ref": "#/definitions/anchor"}},
            "zones": {"type": "array", "items": {"$ref": "#/definitions/zone"}},
            "patterns": {"type": "array", "items": {"type": "string"}}
          }
        },
        "normalize": {
          "type": "object"
        },
        "validate": {
          "type": "object"
        }
      }
    },
    "anchor": {
      "type": "object",
      "required": ["text", "strategy"],
      "properties": {
        "text": {"type": "string"},
        "strategy": {"enum": ["right", "below", "above", "left", "right_aligned", "in_box"]},
        "offset": {"type": "integer"},
        "page_hint": {"type": "integer"},
        "occurrence": {"type": "integer"}
      }
    },
    "zone": {
      "type": "object",
      "required": ["page", "bbox"],
      "properties": {
        "page": {"type": "integer"},
        "bbox": {
          "type": "array",
          "items": {"type": "number"},
          "minItems": 4,
          "maxItems": 4
        },
        "strategy": {"enum": ["ocr", "text", "hybrid"]}
      }
    },
    "table": {
      "type": "object",
      "required": ["id", "pages"],
      "properties": {
        "id": {"type": "string"},
        "pages": {"type": "array", "items": {"type": "integer"}},
        "columns": {"type": "array", "items": {"$ref": "#/definitions/column"}},
        "header_row": {"type": "integer"},
        "total_row": {"type": "integer"}
      }
    },
    "column": {
      "type": "object",
      "required": ["name", "type"],
      "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "synonyms": {"type": "array", "items": {"type": "string"}},
        "required": {"type": "boolean"}
      }
    },
    "validation_rule": {
      "type": "object",
      "required": ["id", "type", "fields"],
      "properties": {
        "id": {"type": "string"},
        "type": {"enum": ["sum", "match", "range", "dependency", "exclusive"]},
        "fields": {"type": "array", "items": {"type": "string"}},
        "condition": {"type": "string"},
        "message": {"type": "string"}
      }
    }
  }
}
```

---

## Performance Specifications

### Latency Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Document classification | 100ms | 500ms |
| Template matching | 50ms | 200ms |
| AcroForm extraction | 200ms | 1s |
| OCR per page | 500ms | 2s |
| Table extraction | 300ms | 1s |
| Full document (digital) | 1s | 3s |
| Full document (scanned) | 3s | 10s |

### Throughput Targets

| Scenario | Target | Hardware |
|----------|--------|----------|
| Single document | 1 doc/sec | 4 CPU, 8GB RAM |
| Batch (digital) | 10 docs/sec | 8 CPU, 16GB RAM |
| Batch (mixed) | 5 docs/sec | 8 CPU, 16GB RAM |
| Batch (scanned) | 2 docs/sec | 8 CPU, GPU, 32GB RAM |

### Resource Limits

```yaml
resources:
  cpu:
    request: 2
    limit: 4
  memory:
    request: 4Gi
    limit: 8Gi
  storage:
    cache: 10Gi
    temp: 5Gi
  
ocr_settings:
  max_image_size: 10MB
  max_pages_per_doc: 100
  timeout_per_page: 5s
  
cache_settings:
  ttl: 24h
  max_size: 10Gi
  eviction: LRU
```

---

## Error Handling & Recovery

### Error Categories

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| Extraction Failure | OCR failure, timeout | Fallback extractor, manual review |
| Validation Error | Invalid format, range | Return with error, request correction |
| Template Mismatch | Wrong form version | Try other versions, manual selection |
| System Error | Out of memory, crash | Restart, queue retry |
| External Service | API down, rate limit | Cache, exponential backoff |

### Retry Strategy

```python
class RetryStrategy:
    def __init__(self):
        self.max_retries = 3
        self.backoff_multiplier = 2
        self.max_backoff = 30
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        
        if isinstance(error, (TimeoutError, ConnectionError)):
            return True
        
        if isinstance(error, ExtractionError) and error.recoverable:
            return True
        
        return False
    
    def get_backoff(self, attempt: int) -> float:
        backoff = min(
            self.backoff_multiplier ** attempt,
            self.max_backoff
        )
        return backoff + random.uniform(0, 1)
```

---

## Security Considerations

### Data Protection

```python
class SecurityManager:
    def sanitize_input(self, pdf_path: Path) -> Path:
        """Validate and sanitize input files."""
        # Check file size
        if pdf_path.stat().st_size > MAX_FILE_SIZE:
            raise SecurityError("File too large")
        
        # Check file type
        if not self.is_valid_pdf(pdf_path):
            raise SecurityError("Invalid PDF")
        
        # Scan for malicious content
        if self.contains_scripts(pdf_path):
            raise SecurityError("PDF contains scripts")
        
        return pdf_path
    
    def mask_sensitive_data(self, data: Dict) -> Dict:
        """Mask PII in extracted data."""
        for field_id, value in data.items():
            if field_id in SENSITIVE_FIELDS:
                data[field_id] = self.mask_value(value, field_id)
        
        return data
```

### Access Control

```yaml
roles:
  viewer:
    - read:documents
    - read:templates
  
  operator:
    - read:documents
    - write:documents
    - read:templates
    - execute:extraction
  
  admin:
    - all:documents
    - all:templates
    - all:configuration
    - read:audit
  
  developer:
    - all:*
```

---

## Integration Specifications

### API Endpoints

```yaml
openapi: 3.0.0
paths:
  /extract:
    post:
      summary: Extract data from document
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                template_id:
                  type: string
                options:
                  type: object
      responses:
        200:
          description: Extraction successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExtractionResult'
  
  /templates:
    get:
      summary: List available templates
    post:
      summary: Create new template
  
  /templates/{id}:
    get:
      summary: Get template details
    put:
      summary: Update template
    delete:
      summary: Delete template
```

### Event Stream

```python
class ExtractionEventStream:
    events = [
        'extraction.started',
        'extraction.classified',
        'extraction.template_matched',
        'extraction.extractor_started',
        'extraction.extractor_completed',
        'extraction.normalized',
        'extraction.validated',
        'extraction.completed',
        'extraction.failed'
    ]
    
    def emit(self, event: str, data: Dict):
        message = {
            'event': event,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        self.stream.publish(message)
```

---

## Testing Strategy

### Test Categories

| Category | Coverage Target | Tools |
|----------|----------------|-------|
| Unit Tests | 90% | pytest |
| Integration Tests | 80% | pytest + fixtures |
| E2E Tests | 70% | pytest + real docs |
| Performance Tests | Key paths | locust |
| Security Tests | All inputs | OWASP ZAP |

### Test Data Requirements

```yaml
test_documents:
  digital_pdfs:
    - clean: 10 documents
    - noisy: 5 documents
    - complex: 5 documents
  
  scanned_pdfs:
    - high_quality: 10 documents
    - medium_quality: 5 documents
    - poor_quality: 5 documents
  
  edge_cases:
    - rotated: 3 documents
    - multi_language: 3 documents
    - handwritten: 3 documents
    - mixed_format: 3 documents
  
  forms:
    - live_oak: 5 variations
    - huntington: 5 variations
    - third_bank: 5 variations
```

---

## Monitoring & Observability

### Metrics

```python
metrics = {
    # Performance
    'extraction_duration_seconds': Histogram(),
    'extraction_fields_total': Counter(),
    'extraction_coverage_ratio': Gauge(),
    
    # Quality
    'extraction_confidence_score': Histogram(),
    'validation_errors_total': Counter(),
    'manual_review_required_total': Counter(),
    
    # System
    'cache_hit_ratio': Gauge(),
    'ocr_pages_processed_total': Counter(),
    'memory_usage_bytes': Gauge(),
    
    # Business
    'documents_processed_total': Counter(),
    'forms_completed_total': Counter(),
    'processing_time_saved_hours': Counter()
}
```

### Logging

```python
logging_config = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json',
            'filename': 'extraction.log',
            'maxBytes': 10485760,
            'backupCount': 5
        }
    },
    'loggers': {
        'extraction': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
}
```

---

## Deployment Architecture

### Container Structure

```dockerfile
# Base image with Python and system dependencies
FROM python:3.11-slim as base
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1-mesa-glx

# Builder stage
FROM base as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM base
COPY --from=builder /root/.local /root/.local
COPY src/ /app/src/
COPY templates/ /app/templates/
WORKDIR /app
CMD ["python", "-m", "src.api"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: template-extractor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: template-extractor
  template:
    metadata:
      labels:
        app: template-extractor
    spec:
      containers:
      - name: extractor
        image: template-extractor:latest
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        env:
        - name: CACHE_REDIS_URL
          value: redis://redis:6379
        - name: LOG_LEVEL
          value: INFO
```

---

## Conclusion

This technical specification provides the detailed implementation blueprint for the template-based extraction system. It covers all architectural components, algorithms, data structures, and operational considerations necessary for successful implementation.