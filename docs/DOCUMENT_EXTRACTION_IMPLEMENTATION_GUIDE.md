# Document Extraction Implementation Guide

## Executive Summary

This document provides comprehensive implementation details for the document extraction system (Part 1 of the two-part pipeline). This system extracts data ONCE from input documents using a hybrid approach: Google Document AI Form Parser for structured documents, Claude Vision for complex/large documents, and direct pandas extraction for Excel files.

## Architecture Overview

### Core Philosophy: Extract ONCE, Map to MANY

```
Input Documents → Intelligent Routing → Hybrid Extraction → Master JSON Pool
     ↓                    ↓                    ↓                ↓
Multiple PDFs      Document           Google DocAI     Comprehensive
Excel Files        Classification     Claude Vision    Data Structure
Various Types      Smart Routing      Excel Direct     (6 categories)
```

**Key Components:**

1. **Document Classification** - Intelligent document type detection
2. **Hybrid Extraction** - Multi-method extraction with fallbacks
3. **Data Categorization** - 6-category organization system
4. **Master JSON Creation** - Unified data pool for form mapping

## Core Implementation Components

### 1. Main Entry Point: ComprehensiveProcessor

**File**: `src/template_extraction/comprehensive_processor.py`

```python
class ComprehensiveProcessor:
    """
    Part 1: Extract data ONCE from documents comprehensively.
    Does NOT use form templates - extracts all available data.
    """
  
    def __init__(self):
        self._extractor = None  # Lazy initialization for BenchmarkExtractor
        self._classifier = None  # Lazy initialization for DocumentClassifier
        self.output_base = Path("outputs/applications")
  
    async def process_documents(
        self, 
        documents: List[Path], 
        application_id: str
    ) -> Dict[str, Any]:
        """
        Main entry point - processes multiple documents and creates master JSON.
      
        Flow:
        1. Initialize extraction state
        2. Process each document individually  
        3. Merge results into master data structure
        4. Save state and master JSON
        """
```

**Key Methods:**

- `process_documents()` - Main orchestration method (`line 151`)
- `process_document()` - Single document processing (`line 266`)
- `_merge_document_data()` - Merges individual extractions (`line 434`)
- `_categorize_extracted_data()` - Organizes into 6 categories (`line 548`)

### 2. Hybrid Extraction Engine: BenchmarkExtractor

**File**: `src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py`

```python
class BenchmarkExtractor:
    """
    Hybrid document extraction with intelligent routing:
    - Excel files: Direct pandas extraction (100% accuracy, 0 API calls)
    - PDF ≤15 pages: Google Document AI Form Parser ($30/1000 pages)
    - PDF >15 pages or fallback: Claude Vision API
    """
  
    def __init__(self, api_key: Optional[str] = None, use_files_api: bool = False):
        # Initialize all extraction methods
        self.client = AsyncAnthropic(api_key=api_key)
        self.preprocessor = UniversalPreprocessor()
        self.excel_extractor = HybridExcelExtractor()
        self.document_classifier = DocumentClassifier()
      
        # Initialize DocAI extractors (conditional)
        self.form_parser = FormParserExtractor() if DOCAI_AVAILABLE else None
        self.general_processor = GeneralProcessorExtractor() if DOCAI_AVAILABLE else None
```

**Intelligent Routing Logic** (`line 150-180`):

```python
async def extract(self, file_path: Path) -> Dict[str, Any]:
    """
    Smart routing based on file type and document characteristics.
    """
  
    # Route 1: Excel files → Direct pandas extraction
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        return await self._extract_excel_direct(file_path)
  
    # Route 2: Classify document for optimal processor selection
    doc_type = self.document_classifier.classify_document(file_path)
  
    # Route 3: Narrative documents → Skip DocAI, use Claude directly
    if doc_type in NARRATIVE_DOCUMENT_TYPES:
        return await self._extract_with_claude_vision(file_path)
  
    # Route 4: Structured documents → Try DocAI first, Claude fallback
    if self.form_parser and file_path.suffix.lower() == '.pdf':
        docai_result = await self._try_docai_extraction(file_path)
        if docai_result and docai_result.get('success'):
            return self._process_docai_result(docai_result, file_path)
  
    # Route 5: Fallback to Claude Vision
    return await self._extract_with_claude_vision(file_path)
```

### 3. Google Document AI Integration

#### Configuration System

**File**: `src/config/docai_config.py`

```python
# Core configuration from environment variables
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us")

# Processing options with timeouts and retry logic
PROCESSING_CONFIG = {
    "timeout": int(os.getenv("DOCAI_TIMEOUT", "120")),
    "max_retries": int(os.getenv("DOCAI_MAX_RETRIES", "3")),
    "max_pages_per_request": int(os.getenv("DOCAI_MAX_PAGES_PER_REQUEST", "15")),
    "retry_initial": 1.0,
    "retry_maximum": 60.0,
    "retry_multiplier": 2.0
}

# Processor configurations
DOCAI_CONFIG = {
    "processors": {
        "form_parser": {
            "id": os.getenv("DOCAI_FORM_PARSER_ID", "").strip(),
            "type": "FORM_PARSER",
            "capabilities": {
                "key_value_extraction": True,
                "table_extraction": True,
                "entity_recognition": True,
                "checkbox_detection": True
            },
            "max_file_size_mb": 40,
            "page_limit": 15,  # Hard limit for non-allowlisted projects
            "pricing_per_1000": 30.00
        }
    }
}
```

#### Form Parser Implementation

**File**: `src/extraction_methods/docai_form_parser.py`

**Critical Implementation Details:**

1. **15-Page Limit Handling** (`line 114-126`):

```python
# Check file size and skip if too large for reliable processing
file_size_mb = file_path.stat().st_size / (1024 * 1024)

# Form Parser has a hard limit of 15 pages for non-allowlisted projects
# Rough estimate: 100KB per page average
if file_size_mb > 1.5:  # ~15 pages at 100KB/page
    return {
        "success": False,
        "error": f"File likely exceeds 15-page limit: {file_size_mb:.2f}MB (fallback to Claude Vision)"
    }
```

2. **Async Processing with Timeout** (`line 202-251`):

```python
async def _process_document_async_safe(self, file_path: Path) -> Optional[documentai.Document]:
    """
    Safely process document with proper async handling and timeout.
    Uses asyncio.wait_for to prevent indefinite hanging.
    """
    try:
        # Calculate appropriate timeout based on file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        base_timeout = 30  # seconds
        extra_timeout = int(file_size_mb * 10)
        timeout = min(base_timeout + extra_timeout, 60)  # Cap at 60s
      
        # Run sync method in executor with timeout
        loop = asyncio.get_running_loop()
        document = await asyncio.wait_for(
            loop.run_in_executor(None, self._process_document_sync, file_path),
            timeout=timeout
        )
        return document
      
    except asyncio.TimeoutError:
        print(f"  ⚠️ DocAI processing timeout for {file_path.name} (>{timeout}s)")
        return None  # Trigger fallback to Claude Vision
```

3. **Retry Logic with Exponential Backoff** (`line 253-259`):

```python
@retry.Retry(
    initial=PROCESSING_CONFIG["retry_initial"],     # 1.0 second
    maximum=PROCESSING_CONFIG["retry_maximum"],     # 60.0 seconds  
    multiplier=PROCESSING_CONFIG["retry_multiplier"], # 2.0x
    timeout=PROCESSING_CONFIG["timeout"],           # 120 seconds total
    predicate=_should_retry_docai_error_static      # Custom retry logic
)
def _process_document_sync(self, file_path: Path) -> Optional[documentai.Document]:
```

4. **Smart Retry Predicate** (`line 25-51`):

```python
def _should_retry_docai_error_static(exception: Exception) -> bool:
    """
    Determine if a DocAI error should be retried.
    Only retries transient errors, not validation failures.
    """
    if not isinstance(exception, GoogleAPICallError):
        return False
  
    error_code = getattr(exception, 'code', None)
  
    if error_code == 429:  # Rate limit - retry
        return True
    if 400 <= error_code < 500:  # Client errors - don't retry
        return False  
    if 500 <= error_code < 600:  # Server errors - retry
        return True
  
    return False  # Default: don't retry unknown errors
```

### 4. DocAI Response Processing

**Critical Methods in FormParserExtractor:**

1. **Form Fields Extraction** (`line 400-450`):

```python
def _extract_form_fields(self, document) -> List[Dict[str, Any]]:
    """
    Extract key-value pairs from DocAI FormField objects.
  
    DocAI returns form_fields as key-value pairs with confidence scores.
    Each field has: field_name, field_value, confidence, bounding_poly
    """
    form_fields = []
  
    for page in document.pages:
        for form_field in page.form_fields:
            # Extract field name
            field_name = self._get_text_from_layout(
                form_field.field_name, document.text
            ).strip()
          
            # Extract field value  
            field_value = self._get_text_from_layout(
                form_field.field_value, document.text
            ).strip()
          
            # Get confidence score
            confidence = form_field.field_name.confidence
          
            form_fields.append({
                "field_name": field_name,
                "field_value": field_value, 
                "confidence": confidence,
                "page": page_num,
                "type": "form_field"
            })
  
    return form_fields
```

2. **Table Extraction** (`line 500-580`):

```python
def _extract_tables(self, document) -> List[Dict[str, Any]]:
    """
    Extract tables from DocAI Table objects.
  
    DocAI provides structured table data with:
    - Header/body row detection
    - Cell coordinates and spans
    - Merged cell handling
    """
    tables = []
  
    for page_num, page in enumerate(document.pages, 1):
        for table_num, table in enumerate(page.tables):
            table_data = {
                "table_id": f"page_{page_num}_table_{table_num}",
                "page": page_num,
                "headers": [],
                "rows": [],
                "confidence": getattr(table, 'confidence', 0.0)
            }
          
            # Process table structure
            for row_num, row in enumerate(table.header_rows + table.body_rows):
                row_data = []
                for cell in row.cells:
                    cell_text = self._get_text_from_layout(cell.layout, document.text)
                    row_data.append({
                        "text": cell_text.strip(),
                        "colspan": cell.col_span,
                        "rowspan": cell.row_span
                    })
              
                if row_num < len(table.header_rows):
                    table_data["headers"].append(row_data)
                else:
                    table_data["rows"].append(row_data)
          
            tables.append(table_data)
  
    return tables
```

3. **Entity Recognition** (`line 600-650`):

```python
def _extract_entities(self, document) -> List[Dict[str, Any]]:
    """
    Extract entities from DocAI Entity objects.
  
    DocAI identifies entities like:
    - PERSON, ORGANIZATION, LOCATION
    - DATE, MONEY, PERCENTAGE
    - Custom entities based on training
    """
    entities = []
  
    for entity in document.entities:
        entity_data = {
            "type": entity.type_,
            "text": entity.mention_text,
            "confidence": entity.confidence,
            "normalized_value": getattr(entity, 'normalized_value', None),
            "properties": {}
        }
      
        # Extract entity properties
        for prop in entity.properties:
            entity_data["properties"][prop.type_] = {
                "text": prop.mention_text,
                "confidence": prop.confidence
            }
      
        entities.append(entity_data)
  
    return entities
```

### 5. Data Categorization System

**File**: `src/template_extraction/comprehensive_processor.py` (`line 548-650`)

```python
def _categorize_extracted_data(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Organize extracted data into 6 standardized categories for form mapping.
  
    Categories:
    1. personal_info - Individual information (SSN, name, address)
    2. business_info - Company information (EIN, structure, ownership)  
    3. financial_data - Assets, liabilities, income, expenses
    4. tax_data - Tax returns, schedules, forms
    5. debt_schedules - Loans, mortgages, payment schedules
    6. other_data - Everything else not classified above
    """
  
    categorized = {
        "personal_info": {},
        "business_info": {},
        "financial_data": {},
        "tax_data": {},
        "debt_schedules": {},
        "other_data": {},
        "metadata": {
            "extraction_method": extraction_result.get("extraction_method", "unknown"),
            "confidence": extraction_result.get("confidence", 0.0),
            "document_type": extraction_result.get("document_type", "unknown")
        }
    }
  
    # Handle DocAI structured responses
    if self._is_docai_format(extraction_result):
        return self._process_docai_format(extraction_result, categorized)
  
    # Handle Claude Vision unstructured responses  
    if isinstance(extraction_result.get("extracted_data"), dict):
        return self._categorize_unstructured_data(
            extraction_result["extracted_data"], categorized
        )
  
    return categorized
```

**DocAI Format Processing** (`line 680-750`):

```python
def _process_docai_format(self, docai_result: Dict[str, Any], categorized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process structured DocAI response with form_fields, tables, entities.
    """
  
    # Process form fields with intelligent categorization
    for field in docai_result.get("form_fields", []):
        field_name = field.get("field_name", "").lower()
        field_value = field.get("field_value", "")
        confidence = field.get("confidence", 0.0)
      
        # Categorize using pattern matching
        category = self._determine_field_category(field_name, field_value)
      
        categorized[category][field_name] = {
            "value": field_value,
            "confidence": confidence,
            "type": "form_field",
            "source": "docai_form_parser"
        }
  
    # Process tables for financial data
    for table in docai_result.get("tables", []):
        table_category = self._categorize_table(table)
        table_key = f"table_{table.get('table_id', 'unknown')}"
      
        categorized[table_category][table_key] = {
            "headers": table.get("headers", []),
            "rows": table.get("rows", []),
            "confidence": table.get("confidence", 0.0),
            "type": "table",
            "source": "docai_form_parser"
        }
  
    # Process entities with type-based categorization
    for entity in docai_result.get("entities", []):
        entity_type = entity.get("type", "").lower()
        entity_category = self._categorize_entity(entity_type)
      
        entity_key = f"entity_{entity_type}_{len(categorized[entity_category])}"
        categorized[entity_category][entity_key] = {
            "text": entity.get("text", ""),
            "type": entity.get("type", ""),
            "confidence": entity.get("confidence", 0.0),
            "normalized_value": entity.get("normalized_value"),
            "source": "docai_form_parser"
        }
  
    return categorized
```

### 6. Pattern Matching for Categorization

**Field Categorization Logic** (`line 800-900`):

```python
def _determine_field_category(self, field_name: str, field_value: str) -> str:
    """
    Intelligent field categorization using financial domain patterns.
    """
  
    # Personal information patterns
    personal_patterns = [
        r'social.?security|ssn|tax.?id.*individual',
        r'first.?name|last.?name|full.?name.*person',
        r'date.?of.?birth|dob|birth.?date',
        r'personal.?address|home.?address|residence',
        r'personal.?phone|mobile|cell|home.?phone',
        r'personal.?email|individual.?email'
    ]
  
    # Business information patterns  
    business_patterns = [
        r'business.?name|company.?name|legal.?name',
        r'ein|employer.?id|federal.?tax.?id.*business',
        r'business.?structure|entity.?type|incorporation',
        r'ownership.?percentage|equity.?share',
        r'business.?address|principal.?place',
        r'business.?phone|company.?phone'
    ]
  
    # Financial data patterns
    financial_patterns = [
        r'total.?assets|asset.?value|bank.?balance',
        r'total.?liabilities|liability|debt.?amount',
        r'net.?worth|equity|financial.?position',
        r'annual.?income|gross.?income|revenue',
        r'monthly.?payment|loan.?payment'
    ]
  
    # Check patterns in order of specificity
    for pattern in personal_patterns:
        if re.search(pattern, field_name, re.IGNORECASE):
            return "personal_info"
  
    for pattern in business_patterns:
        if re.search(pattern, field_name, re.IGNORECASE):
            return "business_info"
  
    for pattern in financial_patterns:
        if re.search(pattern, field_name, re.IGNORECASE):
            return "financial_data"
  
    # Tax-related patterns
    if re.search(r'tax|1040|1065|1120|schedule|irs|form', field_name, re.IGNORECASE):
        return "tax_data"
  
    # Debt-related patterns
    if re.search(r'loan|mortgage|debt|credit|payment|liability', field_name, re.IGNORECASE):
        return "debt_schedules"
  
    return "other_data"  # Default fallback
```

## Environment Configuration

### Required Environment Variables

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us"  # or your preferred region
GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Document AI Processor IDs  
DOCAI_FORM_PARSER_ID="your-form-parser-processor-id"
DOCAI_GENERAL_PROCESSOR_ID="your-general-processor-id"

# Processing Configuration
DOCAI_TIMEOUT="120"                    # seconds
DOCAI_MAX_RETRIES="3" 
DOCAI_MAX_PAGES_PER_REQUEST="15"       # hard limit for non-allowlisted

# Anthropic Configuration
ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Smart Routing Options
ENABLE_SMART_ROUTING="true"
SKIP_DOCAI_FOR_NARRATIVE="true"        # Skip DocAI for narrative documents
ENABLE_RATE_LIMITING="true"
RATE_LIMIT_DOCAI_RPS="10"             # 10 requests/second
RATE_LIMIT_CLAUDE_RPS="5"             # 5 requests/second
```

### Google Cloud Setup

1. **Create Document AI Processors**:

```bash
# Enable Document AI API
gcloud services enable documentai.googleapis.com

# Create Form Parser processor (for structured forms)
gcloud documentai processors create \
  --location=us \
  --type=FORM_PARSER_PROCESSOR \
  --display-name="Loan Application Form Parser"

# Create General Processor (for complex documents) 
gcloud documentai processors create \
  --location=us \
  --type=GENERAL_PROCESSOR \
  --display-name="General Document Processor"
```

2. **Service Account Setup**:

```bash
# Create service account
gcloud iam service-accounts create docai-extractor \
  --description="Document AI Extraction Service" \
  --display-name="DocAI Extractor"

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:docai-extractor@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/documentai.apiUser"

# Download key file
gcloud iam service-accounts keys create key.json \
  --iam-account=docai-extractor@PROJECT_ID.iam.gserviceaccount.com
```

## Processing Flow Examples

### Example 1: PDF Financial Statement Processing

```python
# Input: 3-page PDF financial statement
file_path = Path("inputs/Brigham_Dallas_PFS.pdf")

# Step 1: Classification
doc_type = classifier.classify_document(file_path)
# Result: "PERSONAL_FINANCIAL_STATEMENT" (structured document)

# Step 2: Size check
file_size = 0.8 MB  # Under 1.5MB threshold

# Step 3: DocAI Form Parser processing
docai_result = await form_parser.extract(file_path)
# Success: Extracts 47 form fields, 3 tables, 12 entities

# Step 4: Categorization
categorized_data = {
    "personal_info": {
        "applicant_name": {"value": "John Doe", "confidence": 0.95},
        "ssn": {"value": "123-45-6789", "confidence": 0.98},
        "address": {"value": "123 Main St", "confidence": 0.90}
    },
    "financial_data": {
        "total_assets": {"value": "$250,000", "confidence": 0.93},
        "total_liabilities": {"value": "$150,000", "confidence": 0.91},
        "net_worth": {"value": "$100,000", "confidence": 0.89}
    },
    "tables": {
        "assets_table": {
            "headers": [["Asset Type", "Value"]],
            "rows": [["Checking Account", "$15,000"], ["Home Value", "$200,000"]]
        }
    }
}
```

### Example 2: Large PDF Fallback to Claude

```python
# Input: 25-page PDF tax return
file_path = Path("inputs/Large_Tax_Return_2023.pdf") 

# Step 1: Size check
file_size = 2.8 MB  # Exceeds 1.5MB threshold

# Step 2: Skip DocAI due to 15-page limit
docai_result = {"success": False, "error": "File likely exceeds 15-page limit"}

# Step 3: Fallback to Claude Vision
claude_result = await claude_extractor.extract(file_path)
# Process: PDF → Images → Claude Vision API → Unstructured JSON

# Step 4: Parse unstructured response
extracted_data = {
    "business_name": "ABC Corp",
    "ein": "12-3456789", 
    "total_income": "$500,000",
    "tax_year": "2023"
}

# Step 5: Categorization using pattern matching
categorized_data = categorize_unstructured_data(extracted_data)
```

### Example 3: Excel File Direct Processing

```python
# Input: Excel financial statements
file_path = Path("inputs/Financial_Statements.xlsx")

# Step 1: Excel detection (no DocAI/Claude needed)
extraction_method = "excel_direct"

# Step 2: Pandas extraction (100% accuracy, 0 API calls)
excel_result = await excel_extractor.extract(file_path)
# Result: Structured DataFrames with numeric precision

# Step 3: Financial data identification
financial_data = {
    "revenue_2023": 450000,
    "expenses_2023": 320000,
    "net_income_2023": 130000,
    "current_assets": 180000,
    "current_liabilities": 95000
}

# Step 4: Automatic categorization to "financial_data"
```

## Error Handling and Fallbacks

### DocAI Error Scenarios

1. **15-Page Limit Exceeded**:

```python
# Error: "PAGE_LIMIT_EXCEEDED: Input document has too many pages."
# Fallback: Automatic Claude Vision processing
# Cost: $30/1000 pages → $0.01-0.02 per document
```

2. **Processing Timeout**:

```python
# Error: asyncio.TimeoutError after 60 seconds
# Fallback: Return None, trigger Claude Vision
# Reason: Complex document or service latency
```

3. **Rate Limiting**:

```python
# Error: 429 Too Many Requests
# Retry: Exponential backoff (1s → 2s → 4s → 8s)
# Max retries: 3 attempts over 15 seconds
```

4. **Service Unavailable**:

```python
# Error: 503 Service Unavailable
# Retry: Yes (server error)
# Fallback: Claude Vision after max retries
```

### Strategies

1. **Smart Document Routing** (`benchmark_extractor.py:150-180`):

   - Excel files: $0 (direct pandas)
   - Narrative documents: Skip DocAI, use Claude
   - Structured forms <15 pages: DocAI preferred
   - Large documents: Claude fallback

## Monitoring and Logging

### Key Metrics to Track

```python
# Processing success rates by method
docai_success_rate = successful_docai_calls / total_docai_attempts
claude_fallback_rate = claude_calls / total_processing_attempts  
excel_direct_rate = excel_extractions / total_excel_files

# Cost tracking
monthly_docai_cost = docai_pages_processed * 0.03  # $30/1000 pages
monthly_claude_cost = claude_api_calls * 0.015     # ~$0.015/call average
total_extraction_cost = monthly_docai_cost + monthly_claude_cost

# Quality metrics  
average_field_extraction = total_fields_extracted / documents_processed
categorization_accuracy = correctly_categorized_fields / total_fields
processing_time_avg = total_processing_time / documents_processed
```

### Error Monitoring

```python
# Critical errors to alert on
PAGE_LIMIT_EXCEEDED_rate = page_limit_errors / docai_attempts
TIMEOUT_rate = timeout_errors / total_processing_attempts  
API_ERROR_rate = api_errors / total_api_calls
FALLBACK_RATE = claude_fallbacks / total_documents

# Alert thresholds
if PAGE_LIMIT_EXCEEDED_rate > 0.3:  # >30% hitting page limits
    alert("DocAI page limits too frequent - review file size filtering")
  
if TIMEOUT_rate > 0.1:  # >10% timeouts  
    alert("DocAI processing timeouts high - check service status")
```

## Best Practices and Recommendations

### 1. DocAI Optimization

- **File Size Filtering**: Implement aggressive pre-filtering at 1.5MB
- **Timeout Management**: Use 60-second timeouts for fast fallback
- **Smart Routing**: Skip DocAI for narrative document types
- **Retry Logic**: Only retry transient errors (429, 5xx)

### 2. Claude Vision Fallback

- **Image Quality**: Use 300 DPI for PDF→image conversion
- **Prompt Optimization**: Financial domain-specific prompts
- **Context Management**: Stay within 200k token context limits
- **Rate Limiting**: Respect 30k tokens/minute limits

### 3. Excel Processing

- **Direct Extraction**: Always use pandas for Excel files (100% accuracy)
- **Sheet Detection**: Process all sheets for comprehensive data
- **Numeric Precision**: Preserve decimal precision for financial data
- **Formula Evaluation**: Extract calculated values, not formulas

### 4. Data Quality

- **Confidence Tracking**: Monitor extraction confidence scores
- **Validation**: Implement field format validation (SSN, EIN patterns)
- **Completeness**: Track field coverage across document types
- **Consistency**: Validate data consistency across related fields

This implementation guide provides the complete technical foundation for building the document extraction system. The hybrid approach ensures optimal cost/accuracy balance while providing reliable fallbacks for edge cases and service limitations.

## Code Pointers Summary

**Main Entry Points:**

- `src/template_extraction/comprehensive_processor.py:151` - `process_documents()`
- `src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py:150` - Smart routing logic

**DocAI Integration:**

- `src/extraction_methods/docai_form_parser.py:91` - Main extraction method
- `src/extraction_methods/docai_form_parser.py:202` - Async processing with timeout
- `src/config/docai_config.py:41` - Configuration system

**Data Categorization:**

- `src/template_extraction/comprehensive_processor.py:548` - 6-category organization
- `src/template_extraction/comprehensive_processor.py:680` - DocAI format processing
- `src/template_extraction/comprehensive_processor.py:800` - Pattern matching logic
