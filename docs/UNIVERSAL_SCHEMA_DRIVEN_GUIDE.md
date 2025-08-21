# Universal Schema-Driven Form Processing Guide

## Overview

This guide demonstrates how to implement **schema-driven form processing** using OpenAI's structured outputs to replace traditional string-based field mapping. This approach is ideal for low-volume, high-accuracy form processing scenarios (2-50 applications/month).

## When to Use Schema-Driven Extraction

### Perfect Use Cases ✅
- **Low Volume:** 2-50 applications per month
- **High Accuracy Requirements:** Need 85%+ field coverage with zero semantic errors
- **Multiple Forms:** 5-20 different form templates to fill
- **Semantic Complexity:** Forms have similar field names but different contexts
- **Manual Intervention Tolerance:** Can handle occasional review/correction

### Cost-Effectiveness Analysis
- **Break-even point:** ~10-15 applications/month
- **Optimal volume:** 2-50 applications/month  
- **Cost per application:** $0.25-0.50 (9 forms × $0.03-0.06 per API call)
- **ROI threshold:** Saves >1 hour of manual work per month

## Implementation Architecture

### High-Level Flow
```
Input Documents → Document Extraction → Master JSON → Schema-Driven Mapping → PDF Generation
                    (DocAI/Claude)      (Structured)   (OpenAI Structured     (PyPDF/FillPDF)
                                                        Outputs)
```

### Key Components

1. **Form Schema Extractor**: Converts PDF form fields to OpenAI JSON Schemas
2. **Schema-Driven Mapper**: Uses AI to semantically map data to specific schemas  
3. **Fallback System**: Falls back to string matching if AI extraction fails
4. **Validation Layer**: Ensures extracted data meets field requirements

## Step-by-Step Implementation

### Step 1: Form Schema Discovery

#### 1.1 Extract PDF Form Fields
```python
"""
PDF Form Field Extractor
Discovers all fillable fields in PDF forms
"""
import json
from pathlib import Path
from typing import Dict, List, Any

# Using PyPDFForm (recommended)
try:
    from PyPDFForm import PdfWrapper
    PDF_LIBRARY = "PyPDFForm"
except ImportError:
    from pypdf import PdfReader
    PDF_LIBRARY = "pypdf"

class PDFFormAnalyzer:
    """Extract form fields from PDF templates"""
    
    def analyze_form(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract all form fields from PDF"""
        
        if PDF_LIBRARY == "PyPDFForm":
            return self._analyze_with_pypdfform(pdf_path)
        else:
            return self._analyze_with_pypdf(pdf_path)
    
    def _analyze_with_pypdfform(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract fields using PyPDFForm"""
        try:
            pdf = PdfWrapper(str(pdf_path)).read()
            fields = []
            
            # Get all form fields
            form_fields = pdf.get_form_fields() if hasattr(pdf, 'get_form_fields') else {}
            
            for field_name, field_info in form_fields.items():
                field_data = {
                    "name": field_name,
                    "type": self._determine_field_type(field_name, field_info),
                    "required": self._is_required_field(field_name),
                    "page": 1,  # Default page
                    "description": self._generate_field_description(field_name)
                }
                fields.append(field_data)
            
            return {
                "form_name": pdf_path.stem,
                "total_fields": len(fields),
                "fields": fields,
                "extraction_method": "PyPDFForm"
            }
            
        except Exception as e:
            print(f"PyPDFForm extraction failed: {e}")
            return {"fields": [], "error": str(e)}
    
    def _determine_field_type(self, field_name: str, field_info: Any) -> str:
        """Determine field type from name and properties"""
        name_lower = field_name.lower()
        
        if "email" in name_lower:
            return "email"
        elif "date" in name_lower or "dob" in name_lower:
            return "date"
        elif "phone" in name_lower:
            return "phone"
        elif "ssn" in name_lower or "social" in name_lower:
            return "ssn"
        elif "ein" in name_lower or "tax id" in name_lower:
            return "ein"
        elif "amount" in name_lower or "income" in name_lower or "revenue" in name_lower:
            return "currency"
        elif "check" in name_lower or str(field_info).get("type") == "checkbox":
            return "checkbox"
        else:
            return "text"
    
    def _is_required_field(self, field_name: str) -> bool:
        """Determine if field is required based on name patterns"""
        name_lower = field_name.lower()
        required_patterns = ["name", "ssn", "ein", "address", "phone", "email", "date"]
        return any(pattern in name_lower for pattern in required_patterns)
    
    def _generate_field_description(self, field_name: str) -> str:
        """Generate semantic description for the field"""
        name_lower = field_name.lower()
        
        if "business" in name_lower or "company" in name_lower:
            return f"{field_name} - Business/company information only"
        elif "applicant" in name_lower or "personal" in name_lower:
            return f"{field_name} - Individual person information"
        elif "address" in name_lower:
            return f"{field_name} - Physical mailing address"
        elif "email" in name_lower:
            return f"{field_name} - Valid email address"
        else:
            return field_name

# Usage Example
analyzer = PDFFormAnalyzer()
form_data = analyzer.analyze_form(Path("bank_application.pdf"))
```

#### 1.2 Convert to OpenAI Schema Format
```python
"""
OpenAI Schema Generator
Converts PDF form fields to OpenAI JSON Schema
"""

class OpenAISchemaGenerator:
    """Convert PDF form analysis to OpenAI JSON Schema"""
    
    def generate_schema(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAI JSON Schema from form analysis"""
        
        properties = {}
        required = []
        
        for field in form_data.get("fields", []):
            field_name = field["name"]
            field_type = field["type"]
            
            # Create property definition
            prop = self._create_property(field_name, field_type, field.get("description", ""))
            properties[field_name] = prop
            
            # Add to required if necessary
            if field.get("required", False):
                required.append(field_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
            "description": f"Schema for {form_data.get('form_name', 'Unknown Form')}"
        }
    
    def _create_property(self, field_name: str, field_type: str, description: str) -> Dict[str, Any]:
        """Create OpenAI property definition with validation"""
        
        prop = {
            "type": "string",
            "description": description or field_name
        }
        
        # Add format validation based on field type
        if field_type == "email":
            prop["format"] = "email"
        elif field_type == "date":
            prop["pattern"] = r"^\d{2}/\d{2}/\d{4}$"
        elif field_type == "ssn":
            prop["pattern"] = r"^\d{3}-\d{2}-\d{4}$|^XXX-XX-\d{4}$"
        elif field_type == "ein":
            prop["pattern"] = r"^\d{2}-\d{7}$"
        elif field_type == "phone":
            prop["description"] += " (Format: (555) 123-4567)"
        elif field_type == "currency":
            prop["pattern"] = r"^\$?[\d,]+\.?\d{0,2}$"
        elif field_type == "checkbox":
            prop["type"] = "boolean"
        
        return prop

# Usage Example  
schema_generator = OpenAISchemaGenerator()
openai_schema = schema_generator.generate_schema(form_data)
```

### Step 2: Document Processing Pipeline

#### 2.1 Master Data Extraction
```python
"""
Universal Document Processor
Extracts comprehensive data from various document types
"""
import json
from pathlib import Path
from typing import Dict, Any, List

class UniversalDocumentProcessor:
    """Process various document types into master JSON structure"""
    
    def __init__(self):
        self.supported_types = [".pdf", ".xlsx", ".docx", ".png", ".jpg"]
    
    async def process_documents(self, document_paths: List[Path]) -> Dict[str, Any]:
        """Process all documents into master data structure"""
        
        master_data = {
            "personal_info": {},
            "business_info": {}, 
            "financial_data": {},
            "supporting_documents": {},
            "metadata": {
                "extraction_timestamp": datetime.now().isoformat(),
                "document_count": len(document_paths),
                "processing_methods": []
            }
        }
        
        for doc_path in document_paths:
            print(f"Processing: {doc_path.name}")
            
            try:
                # Determine processing method based on document type
                if doc_path.suffix.lower() == ".xlsx":
                    doc_data = await self._process_excel(doc_path)
                elif doc_path.suffix.lower() == ".pdf":
                    doc_data = await self._process_pdf(doc_path)
                else:
                    doc_data = await self._process_image(doc_path)
                
                # Merge into master data
                self._merge_document_data(master_data, doc_data, doc_path.name)
                
            except Exception as e:
                print(f"Failed to process {doc_path}: {e}")
                master_data["metadata"]["errors"] = master_data["metadata"].get("errors", [])
                master_data["metadata"]["errors"].append({
                    "document": doc_path.name,
                    "error": str(e)
                })
        
        return master_data
    
    async def _process_excel(self, file_path: Path) -> Dict[str, Any]:
        """Process Excel file with pandas"""
        import pandas as pd
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            processed_data = {}
            for sheet_name, df in excel_data.items():
                # Convert to dict and clean
                sheet_data = df.to_dict('records')
                processed_data[sheet_name] = sheet_data
            
            return {
                "extraction_method": "pandas_excel",
                "data": processed_data,
                "confidence": 1.0  # Perfect accuracy for Excel
            }
            
        except Exception as e:
            raise Exception(f"Excel processing failed: {e}")
    
    async def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Process PDF with DocAI or Claude Vision"""
        
        # Try DocAI first (if configured)
        try:
            return await self._process_with_docai(file_path)
        except:
            # Fallback to Claude Vision
            return await self._process_with_claude_vision(file_path)
    
    def _merge_document_data(self, master_data: Dict, doc_data: Dict, doc_name: str):
        """Merge document data into master structure"""
        
        # Add extraction metadata
        master_data["metadata"]["processing_methods"].append({
            "document": doc_name,
            "method": doc_data.get("extraction_method", "unknown"),
            "confidence": doc_data.get("confidence", 0.0)
        })
        
        # Merge actual data based on patterns
        data = doc_data.get("data", {})
        
        for key, value in data.items():
            if self._is_personal_info(key, value):
                master_data["personal_info"][key] = value
            elif self._is_business_info(key, value):
                master_data["business_info"][key] = value
            elif self._is_financial_data(key, value):
                master_data["financial_data"][key] = value
            else:
                master_data["supporting_documents"][key] = value
```

### Step 3: Schema-Driven Form Mapping

#### 3.1 OpenAI Form Mapper
```python
"""
Schema-Driven Form Mapper
Maps master data to specific form schemas using OpenAI structured outputs
"""
import asyncio
from openai import AsyncOpenAI

class SchemaFormMapper:
    """Map master data to form schemas using OpenAI structured outputs"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Latest model for best accuracy
        
    async def map_to_form(
        self,
        master_data: Dict[str, Any],
        form_schema: Dict[str, Any],
        form_context: str = ""
    ) -> Dict[str, Any]:
        """Map master data to specific form using structured outputs"""
        
        # Create context-aware system prompt
        system_prompt = self._create_system_prompt(form_context)
        user_prompt = self._create_user_prompt(master_data, form_schema)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "form_extraction",
                        "schema": form_schema,
                        "strict": True
                    }
                },
                temperature=0.1  # Low temperature for consistency
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Validate and return
            return self._validate_extraction(extracted_data, form_schema)
            
        except Exception as e:
            raise Exception(f"OpenAI form mapping failed: {e}")
    
    def _create_system_prompt(self, form_context: str) -> str:
        """Create semantic system prompt"""
        return f"""You are an expert form filling specialist. Extract data from comprehensive master data and map it accurately to specific form fields.

CRITICAL MAPPING RULES:
1. **Semantic Accuracy**: 
   - Personal info (SSN, individual names) → Personal/Applicant fields ONLY
   - Business info (EIN, company names) → Business/Company fields ONLY
   - NEVER mix personal and business information

2. **Field Type Precision**:
   - Email fields → Email addresses ONLY (never physical addresses)
   - Address fields → Physical addresses ONLY (never email addresses) 
   - Phone fields → Phone numbers with proper formatting
   - Date fields → Valid dates in requested format
   - Currency fields → Dollar amounts with proper formatting

3. **Data Quality**:
   - Use EXACT values from master data - no inference
   - If field cannot be confidently mapped, return null
   - Prefer structured data over raw text when available
   - Maintain consistent formatting within field types

4. **Context**: {form_context}

Return only values that accurately correspond to each field's semantic meaning."""

    def _create_user_prompt(self, master_data: Dict, schema: Dict) -> str:
        """Create user prompt with master data and schema context"""
        return f"""Master Data for Form Extraction:

{json.dumps(master_data, indent=2)}

Schema Context:
{schema.get('description', 'Form extraction schema')}

Based on the master data above, extract values for the form fields defined in the schema. Use only data that semantically matches each field's purpose. Return null for fields where appropriate data cannot be found."""

    def _validate_extraction(self, extracted_data: Dict, schema: Dict) -> Dict[str, Any]:
        """Validate extracted data against schema and business rules"""
        validated_data = {}
        
        for field_name, value in extracted_data.items():
            # Skip empty values
            if value is None or str(value).strip() == "":
                continue
            
            # Basic validation
            if self._is_valid_field_value(field_name, value):
                validated_data[field_name] = value
            else:
                print(f"⚠️ Filtered invalid value for {field_name}: {value}")
        
        return validated_data
    
    def _is_valid_field_value(self, field_name: str, value: Any) -> bool:
        """Validate field value against field name patterns"""
        if not value or (isinstance(value, str) and len(value.strip()) < 1):
            return False
        
        field_lower = field_name.lower()
        
        # Email validation
        if "email" in field_lower:
            return "@" in str(value) and "." in str(value)
        
        # Address validation (should not be email)
        if "address" in field_lower:
            return "@" not in str(value)
        
        return True
```

### Step 4: PDF Generation Pipeline

#### 4.1 Form Filler
```python
"""
Universal PDF Form Filler
Fills PDF forms with extracted data
"""
from PyPDFForm import PdfWrapper

class UniversalFormFiller:
    """Fill PDF forms with mapped data"""
    
    def fill_form(
        self,
        template_path: Path,
        mapped_data: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """Fill PDF form with mapped data"""
        
        try:
            # Load PDF template
            pdf = PdfWrapper(str(template_path)).read()
            
            # Fill form fields
            filled_pdf = pdf.fill(mapped_data)
            
            # Save filled PDF
            with open(output_path, "wb") as f:
                f.write(filled_pdf.read())
            
            print(f"✅ Generated filled PDF: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            return False
    
    def get_form_fields(self, pdf_path: Path) -> List[str]:
        """Get list of fillable fields in PDF"""
        try:
            pdf = PdfWrapper(str(pdf_path)).read()
            return list(pdf.get_form_fields().keys())
        except:
            return []
```

### Step 5: Complete Pipeline Integration

#### 5.1 Main Processing Pipeline
```python
"""
Complete Schema-Driven Form Processing Pipeline
"""

class SchemaFormProcessor:
    """Complete pipeline for schema-driven form processing"""
    
    def __init__(self, openai_api_key: str):
        self.document_processor = UniversalDocumentProcessor()
        self.form_mapper = SchemaFormMapper(openai_api_key)
        self.form_filler = UniversalFormFiller()
        self.pdf_analyzer = PDFFormAnalyzer()
        self.schema_generator = OpenAISchemaGenerator()
        
    async def process_application(
        self,
        documents: List[Path],
        form_templates: Dict[str, Path],
        output_dir: Path
    ) -> Dict[str, Any]:
        """Process complete application through schema-driven pipeline"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {"processed_forms": [], "errors": []}
        
        print("🚀 Starting schema-driven form processing...")
        
        # Step 1: Extract master data from documents
        print("\n📄 Step 1: Processing documents...")
        master_data = await self.document_processor.process_documents(documents)
        
        # Save master data
        master_path = output_dir / "master_data.json"
        with open(master_path, 'w') as f:
            json.dump(master_data, f, indent=2)
        print(f"💾 Saved master data: {master_path}")
        
        # Step 2: Process each form template
        print(f"\n📝 Step 2: Processing {len(form_templates)} forms...")
        
        for form_name, template_path in form_templates.items():
            try:
                print(f"\n  🔄 Processing {form_name}...")
                
                # Analyze PDF form structure
                form_analysis = self.pdf_analyzer.analyze_form(template_path)
                
                # Generate OpenAI schema
                form_schema = self.schema_generator.generate_schema(form_analysis)
                
                # Map data to form schema
                mapped_data = await self.form_mapper.map_to_form(
                    master_data,
                    form_schema,
                    form_context=f"{form_name} form"
                )
                
                # Calculate coverage
                total_fields = len(form_analysis.get("fields", []))
                filled_fields = len([v for v in mapped_data.values() if v])
                coverage = (filled_fields / total_fields * 100) if total_fields > 0 else 0
                
                # Generate filled PDF
                output_pdf = output_dir / f"{form_name}_filled.pdf"
                success = self.form_filler.fill_form(template_path, mapped_data, output_pdf)
                
                # Save mapping results
                mapping_path = output_dir / f"{form_name}_mapping.json"
                with open(mapping_path, 'w') as f:
                    json.dump({
                        "form_name": form_name,
                        "mapped_data": mapped_data,
                        "coverage": round(coverage, 1),
                        "total_fields": total_fields,
                        "filled_fields": filled_fields
                    }, f, indent=2)
                
                results["processed_forms"].append({
                    "form_name": form_name,
                    "coverage": round(coverage, 1),
                    "pdf_generated": success,
                    "output_pdf": str(output_pdf) if success else None,
                    "mapping_file": str(mapping_path)
                })
                
                print(f"    ✅ {form_name}: {filled_fields}/{total_fields} fields ({coverage:.1f}%)")
                
            except Exception as e:
                error_msg = f"Failed to process {form_name}: {e}"
                print(f"    ❌ {error_msg}")
                results["errors"].append(error_msg)
        
        # Step 3: Generate summary report
        print(f"\n📊 Step 3: Generating summary report...")
        self._generate_summary_report(results, output_dir)
        
        return results
    
    def _generate_summary_report(self, results: Dict, output_dir: Path):
        """Generate processing summary report"""
        
        successful_forms = [f for f in results["processed_forms"] if f["pdf_generated"]]
        avg_coverage = sum(f["coverage"] for f in successful_forms) / len(successful_forms) if successful_forms else 0
        
        summary = {
            "processing_timestamp": datetime.now().isoformat(),
            "total_forms": len(results["processed_forms"]),
            "successful_forms": len(successful_forms),
            "failed_forms": len(results["errors"]),
            "average_coverage": round(avg_coverage, 1),
            "detailed_results": results
        }
        
        summary_path = output_dir / "processing_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📋 Processing Summary:")
        print(f"  ✅ Successful forms: {len(successful_forms)}")
        print(f"  ❌ Failed forms: {len(results['errors'])}")
        print(f"  📊 Average coverage: {avg_coverage:.1f}%")
        print(f"  💾 Summary saved: {summary_path}")

# Usage Example
async def main():
    """Example usage of schema-driven form processor"""
    
    processor = SchemaFormProcessor(openai_api_key="your-api-key")
    
    # Define input documents
    documents = [
        Path("documents/tax_return.pdf"),
        Path("documents/financial_statement.xlsx"),
        Path("documents/business_license.pdf")
    ]
    
    # Define form templates
    form_templates = {
        "bank_application": Path("templates/bank_app_form.pdf"),
        "personal_financial": Path("templates/pfs_form.pdf"),
        "business_info": Path("templates/business_form.pdf")
    }
    
    # Process application
    results = await processor.process_application(
        documents=documents,
        form_templates=form_templates,
        output_dir=Path("outputs/application_001")
    )
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
```

## Cost Optimization Strategies

### 1. Batch Processing
```python
# Process multiple forms in single API call
async def batch_process_forms(self, master_data: Dict, forms: List[Dict]) -> Dict:
    """Process multiple forms in single OpenAI call"""
    
    # Combine all schemas into single request
    combined_schema = {
        "type": "object",
        "properties": {
            form["name"]: form["schema"] 
            for form in forms
        }
    }
    
    # Single API call for all forms
    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system", 
            "content": "Fill all requested forms with appropriate data"
        }, {
            "role": "user", 
            "content": f"Master data: {json.dumps(master_data)}"
        }],
        response_format={"type": "json_schema", "json_schema": {"schema": combined_schema}}
    )
    
    return json.loads(response.choices[0].message.content)
```

### 2. Caching and Reuse
```python
# Cache processed schemas
class SchemaCache:
    def __init__(self):
        self.cache = {}
    
    def get_schema(self, pdf_path: Path) -> Dict:
        """Get cached schema or generate new one"""
        cache_key = f"{pdf_path.stem}_{pdf_path.stat().st_mtime}"
        
        if cache_key not in self.cache:
            analyzer = PDFFormAnalyzer()
            generator = OpenAISchemaGenerator()
            
            form_data = analyzer.analyze_form(pdf_path)
            self.cache[cache_key] = generator.generate_schema(form_data)
        
        return self.cache[cache_key]
```

### 3. Smart Fallbacks
```python
# Fallback to cheaper extraction methods
async def smart_extraction(self, master_data: Dict, form_schema: Dict) -> Dict:
    """Use cheaper methods first, OpenAI as fallback"""
    
    # Try string matching first (free)
    string_result = self.string_matcher.map_fields(master_data, form_schema)
    coverage = self.calculate_coverage(string_result, form_schema)
    
    # Only use OpenAI if coverage is poor
    if coverage < 70:
        return await self.openai_mapper.map_to_form(master_data, form_schema)
    else:
        return string_result
```

## Error Handling and Quality Assurance

### 1. Validation Pipeline
```python
class ExtractionValidator:
    """Validate extraction quality and flag issues"""
    
    def validate_extraction(self, mapped_data: Dict, form_schema: Dict) -> Dict:
        """Comprehensive validation of mapped data"""
        
        validation_results = {
            "passed": True,
            "issues": [],
            "confidence": 0.0
        }
        
        for field_name, value in mapped_data.items():
            issues = self._validate_field(field_name, value, form_schema)
            if issues:
                validation_results["issues"].extend(issues)
                validation_results["passed"] = False
        
        # Calculate confidence score
        validation_results["confidence"] = self._calculate_confidence(
            mapped_data, form_schema, validation_results["issues"]
        )
        
        return validation_results
    
    def _validate_field(self, field_name: str, value: Any, schema: Dict) -> List[str]:
        """Validate individual field value"""
        issues = []
        field_lower = field_name.lower()
        
        # Type validation
        if "email" in field_lower and ("@" not in str(value) or "." not in str(value)):
            issues.append(f"Invalid email format for {field_name}: {value}")
        
        if "address" in field_lower and "@" in str(value):
            issues.append(f"Email found in address field {field_name}: {value}")
        
        if "business" in field_lower and self._looks_like_personal_name(value):
            issues.append(f"Personal name in business field {field_name}: {value}")
        
        return issues
```

### 2. Human Review Integration
```python
class ReviewQueue:
    """Manage forms requiring human review"""
    
    def check_review_needed(self, validation_results: Dict, coverage: float) -> bool:
        """Determine if form needs human review"""
        
        # Auto-approve high quality extractions
        if coverage > 90 and validation_results["confidence"] > 0.95:
            return False
        
        # Require review for poor coverage or validation issues
        if coverage < 70 or not validation_results["passed"]:
            return True
        
        # Middle ground - spot check
        import random
        return random.random() < 0.1  # 10% spot check rate
    
    def create_review_task(self, form_data: Dict, issues: List[str]) -> Dict:
        """Create human review task"""
        
        return {
            "form_name": form_data["form_name"],
            "coverage": form_data["coverage"],
            "issues": issues,
            "priority": "high" if form_data["coverage"] < 50 else "medium",
            "review_url": f"/review/{form_data['form_name']}"
        }
```

## Deployment and Monitoring

### 1. Health Checks
```python
class HealthMonitor:
    """Monitor system health and performance"""
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        
        health = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check OpenAI API
        try:
            test_response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            health["checks"]["openai"] = "healthy"
        except Exception as e:
            health["checks"]["openai"] = f"error: {e}"
            health["status"] = "degraded"
        
        # Check file system access
        try:
            test_path = Path("temp_health_check.txt")
            test_path.write_text("test")
            test_path.unlink()
            health["checks"]["filesystem"] = "healthy"
        except Exception as e:
            health["checks"]["filesystem"] = f"error: {e}"
            health["status"] = "degraded"
        
        return health
```

### 2. Performance Metrics
```python
class MetricsCollector:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "processing_times": [],
            "coverage_scores": [],
            "api_costs": [],
            "error_rates": []
        }
    
    def record_processing(self, duration: float, coverage: float, cost: float, errors: int):
        """Record processing metrics"""
        
        self.metrics["processing_times"].append(duration)
        self.metrics["coverage_scores"].append(coverage)
        self.metrics["api_costs"].append(cost)
        self.metrics["error_rates"].append(errors)
    
    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary"""
        
        if not self.metrics["processing_times"]:
            return {"status": "no_data"}
        
        return {
            "avg_processing_time": statistics.mean(self.metrics["processing_times"]),
            "avg_coverage": statistics.mean(self.metrics["coverage_scores"]),
            "total_api_cost": sum(self.metrics["api_costs"]),
            "avg_error_rate": statistics.mean(self.metrics["error_rates"]),
            "total_processed": len(self.metrics["processing_times"])
        }
```

## Best Practices and Recommendations

### 1. Prompt Engineering
- **Be Specific**: Include detailed field descriptions and context
- **Use Examples**: Provide good/bad mapping examples in prompts
- **Set Constraints**: Clearly define what should NOT be mapped
- **Iterate**: Continuously improve prompts based on results

### 2. Schema Design
- **Semantic Descriptions**: Add rich descriptions to help AI understand context
- **Validation Patterns**: Include regex patterns for format validation
- **Required Fields**: Mark critical fields as required
- **Enumeration**: Use enums for fields with limited valid values

### 3. Error Handling
- **Graceful Degradation**: Fall back to simpler methods if AI fails
- **Comprehensive Logging**: Log all extraction attempts and results
- **Human Review**: Implement review workflows for low-confidence extractions
- **Continuous Learning**: Use review feedback to improve prompts

### 4. Cost Management
- **Batch Processing**: Combine multiple forms in single API calls when possible
- **Smart Fallbacks**: Use cheaper methods first, AI only when needed
- **Caching**: Cache schemas and reuse across similar forms
- **Monitor Usage**: Track API costs and optimize based on usage patterns

This guide provides a complete framework for implementing schema-driven form processing that can achieve 85%+ accuracy while maintaining cost-effectiveness for low to medium volume applications.