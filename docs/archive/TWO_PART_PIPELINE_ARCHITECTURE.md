# Two-Part Pipeline Architecture - Comprehensive Guide

## Executive Summary

This document provides a comprehensive guide for the loan application document processing pipeline. The system processes uploaded documents to extract data ONCE, then maps that data to 9 different bank forms across 3 banks.

**CRITICAL CONCEPT**: Extract once, map to many. NOT extract many times.

## Business Logic & End Goal

### Business Context
- **Problem**: Loan applicants must submit the same information to multiple banks using different forms. Each applicant can choose which of the three banks they want to apply to. 
- **Documents**: Users upload various documents (PFS, tax returns, business documents, financial statements incrementally, etc.) of unknown formats across users. We will extract all data from each document as its incrementally uploaded and compile one large json of all data available for an applicant. 
- **Banks**: 3 banks (Live Oak, Huntington, Wells Fargo) each have their own set of forms in their own formats 
- **Forms**: 9 total forms needed (Live Oak: 3, Huntington: 4, Wells Fargo: 2) these will remain constant 
- **Goal**: Extract ALL data (fields) from documents ONCE, then fill all 9 forms automatically by mapping the large json consisting of all of an applicatns input data into each form individually (eg if they choose to apply to a bank, we then fill out the templates of their required forms)

### End Goal
1. User uploads documents incrementally over days/weeks
2. System extracts ALL available data from these documents as they are uploaded and keep a merged state of all data as well. 
3. System maps extracted data to 9 different bank forms
4. User reviews and submits completed forms to banks
5. Processing time reduced from 3-5 days to 2-4 hours

## CORRECT Architecture (What It Should Be)

### High-Level Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                   PART 1: DOCUMENT PROCESSING                    │
├─────────────────────────────────────────────────────────────────┤
│     Documents → Comprehensive Extraction → Master JSON Pool     │
│   (Incremental)      (Extract ONCE)         (All Data)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      PART 2: FORM MAPPING                        │
├─────────────────────────────────────────────────────────────────┤
│  Master JSON → Map to 9 Forms → Generate PDFs → Submit to Banks │
│  (One Source)   (Distribution)   (Final Output)    (3 Banks)    │
└─────────────────────────────────────────────────────────────────┘
```

### Part 1: Document Processing (Extract ONCE)

**Purpose**: Extract ALL data from uploaded documents into a single comprehensive data pool

**Process**:
1. User uploads document (e.g., PFS_2023.pdf)
2. System extracts ALL fields it can find:
   - Personal information (example: name, SSN, DOB, address)
   - Business information (company name, EIN, address, type)
   - Financial data (assets, liabilities, income, expenses)
   - Tax information (returns, transcripts, schedules)
   - Debt schedules (creditors, balances, terms)
3. Extracted data added to master JSON pool
4. Process repeats for each new document upload
5. Master JSON grows with each document

**Key Point**: We do NOT use 9 different extraction templates. We extract EVERYTHING we can find.

### Part 2: Form Mapping (Distribute to Many)

**Purpose**: Map the master JSON pool to 9 specific bank forms

**Process**:
1. Load master JSON from Part 1
2. For each of 9 forms:
   - Extract json form template (field requirements) for each document (and have it saved)
   - Map master JSON fields to form fields 
   - Apply bank-specific formatting rules 
   - Validate required fields
   - Generate filled PDF
3. Track completion status per form (FUTURE ENHANCMENT)
4. Enable bank submission when ready

**Forms to Generate**:
- Live Oak: SBA Application, Personal Financial Statement, Form 4506-T
- Huntington: Business Application, PFS, Tax Transcript Request, Debt Schedule
- Wells Fargo: Loan Application, Financial Statement

## CURRENT Architecture (What Was Built Wrong)

### What I Incorrectly Implemented

```
WRONG Implementation:
Documents → Extract with 9 Templates → Merge → Map to Same 9 Forms
           (9x redundant work!)              (Pointless remapping!)
```

**Problems**:
1. Extracting each document 9 times with different templates
2. Then mapping that same data to those same forms again
3. This is 18x redundant work for no benefit
4. Completely misunderstood the architecture

### Current Code State

**Working Components**:
- `BenchmarkExtractor` - LLM-based comprehensive extraction (GOOD - use this!)
- `LLMFormFiller` - Maps data to forms and fills PDFs (GOOD)
- `PDFFormGenerator` - Generates filled PDFs (GOOD)
- Template specifications for 9 forms (GOOD - but misused)

**Broken Implementation**:
- `MultiTemplateProcessor` - Incorrectly extracts with 9 templates (WRONG)
- Part 1 extracts with each form's template (WRONG)
- Part 2 redundantly maps to same forms (UNNECESSARY)

## Production Intended Implementation -NOT THIS REPO 

### Technology Stack
- **Backend**: TypeScript/Node.js
- **Storage**: AWS S3
- **Queue**: SQS for document processing
- **Database**: PostgreSQL for metadata
- **API**: RESTful + GraphQL
- **Authentication**: JWT tokens

### Architecture
```typescript
// Part 1: Document Processing Service
class DocumentProcessor {
  async processDocument(applicationId: string, document: S3Object) {
    // 1. Download from S3
    const file = await s3.getObject(document);
    
    // 2. Extract EVERYTHING (comprehensive extraction)
    const extractedData = await comprehensiveExtractor.extract(file);
    
    // 3. Merge with existing master data
    const masterData = await getMasterData(applicationId);
    const updatedMaster = mergeData(masterData, extractedData);
    
    // 4. Save to S3
    await s3.putObject({
      Key: `applications/${applicationId}/master-data.json`,
      Body: updatedMaster
    });
    
    // 5. Trigger form mapping if threshold met
    if (updatedMaster.coverage > 0.7) {
      await sqs.sendMessage({ action: 'MAP_FORMS', applicationId });
    }
  }
}

// Part 2: Form Mapping Service (separate Lambda/service)
class FormMapper {
  async mapToForms(applicationId: string) {
    // 1. Load master data
    const masterData = await s3.getObject({
      Key: `applications/${applicationId}/master-data.json`
    });
    
    // 2. Map to each form
    for (const bank of ['live_oak', 'huntington', 'wells_fargo']) {
      for (const formId of BANK_FORMS[bank]) {
        const formData = mapDataToForm(masterData, formId);
        const pdf = await generatePDF(formData, formId);
        
        await s3.putObject({
          Key: `applications/${applicationId}/forms/${bank}/${formId}.pdf`,
          Body: pdf
        });
      }
    }
  }
}
```

### Storage Structure (S3)
```
s3://loan-applications/
├── applications/{applicationId}/
│   ├── documents/                  # Original uploads
│   │   └── {timestamp}_{filename}
│   ├── extractions/                # Part 1 output
│   │   ├── master-data.json       # Comprehensive extracted data
│   │   └── per-document/          # Individual document extractions
│   │       └── {documentId}.json
│   └── forms/                      # Part 2 output
│       ├── live_oak/
│       │   ├── sba_application.pdf
│       │   ├── pfs.pdf
│       │   └── 4506t.pdf
│       ├── huntington/
│       │   ├── business_application.pdf
│       │   ├── pfs.pdf
│       │   ├── tax_transcript.pdf
│       │   └── debt_schedule.pdf
│       └── wells_fargo/
│           ├── loan_application.pdf
│           └── financial_statement.pdf
```

## Test Repository Intended Implementation

### What Should Be Built (Python)

```python
# Part 1: Comprehensive Document Extraction
class DocumentProcessor:
    def __init__(self):
        # Use existing LLM extractor for comprehensive extraction
        self.extractor = BenchmarkExtractor()  # or similar comprehensive extractor
        
    async def process_document(self, document_path: Path, application_id: str):
        """Extract ALL data from document ONCE"""
        # 1. Extract everything we can find
        extracted_data = await self.extractor.extract_all([document_path])
        
        # 2. Structure into categories
        structured_data = self.structure_data(extracted_data)
        
        # 3. Merge with existing master data
        master_data = self.load_master_data(application_id)
        updated_master = self.merge_data(master_data, structured_data)
        
        # 4. Save master data
        self.save_master_data(application_id, updated_master)
        
        return updated_master
    
    def structure_data(self, raw_data):
        """Organize extracted data into categories"""
        return {
            "personal_info": {},    # Name, SSN, DOB, etc.
            "business_info": {},    # Company details
            "financial_data": {},   # Assets, liabilities, income
            "tax_data": {},        # Tax returns, schedules
            "debt_data": {}        # Loans, credit lines
        }

# Part 2: Form Mapping (uses templates correctly)
class FormMapper:
    def __init__(self):
        self.form_specs = load_all_form_specifications()  # 9 form templates
        self.pdf_generator = PDFFormGenerator()
        
    def map_to_all_forms(self, application_id: str):
        """Map master data to 9 forms"""
        # 1. Load master data from Part 1
        master_data = self.load_master_data(application_id)
        
        # 2. Map to each form
        results = {}
        for bank in ['live_oak', 'huntington', 'wells_fargo']:
            for form_id in BANK_FORMS[bank]:
                # Map master data to specific form fields
                form_data = self.map_to_form(master_data, form_id)
                
                # Generate PDF
                pdf_path = self.pdf_generator.generate(form_data, form_id)
                
                results[f"{bank}_{form_id}"] = {
                    "data": form_data,
                    "pdf": pdf_path,
                    "coverage": self.calculate_coverage(form_data, form_id)
                }
                
        return results
    
    def map_to_form(self, master_data: dict, form_id: str):
        """Map master data fields to specific form requirements"""
        form_spec = self.form_specs[form_id]
        mapped_data = {}
        
        for field in form_spec['fields']:
            # Find matching data in master
            value = self.find_field_value(master_data, field['name'])
            if value:
                mapped_data[field['name']] = value
                
        return mapped_data
```

### Current Test Repository Structure
```
Document_Processing_Pipeline/
├── src/
│   ├── extraction_methods/
│   │   └── multimodal_llm/
│   │       └── providers/
│   │           ├── benchmark_extractor.py    # ✓ Use for Part 1
│   │           ├── form_filler.py           # ✓ Adapt for Part 2
│   │           └── pdf_form_generator.py    # ✓ Use for PDF generation
│   └── template_extraction/
│       ├── multi_template_processor.py      # ✗ WRONG - needs complete rewrite
│       └── orchestrator.py                  # ✓ Can be adapted
└── templates/
    └── form_specs/                          # ✓ Use for Part 2 mapping
        ├── live_oak_*.json   (3 files)
        ├── huntington_*.json (4 files)
        └── wells_fargo_*.json (2 files)
```

## Detailed Refactor Plan

### Phase 1: Fix Part 1 (Document Processing)

**Goal**: Extract data ONCE comprehensively, not with 9 templates

**Steps**:
1. **DELETE or rename** `multi_template_processor.py` - it's fundamentally wrong
2. **CREATE** new `comprehensive_processor.py`:
   ```python
   class ComprehensiveProcessor:
       def __init__(self):
           self.extractor = BenchmarkExtractor()  # Use existing LLM extractor
           
       async def process_document(self, doc_path, app_id):
           # Extract EVERYTHING once
           data = await self.extractor.extract_all([doc_path])
           # Save to master JSON
           return self.update_master_data(app_id, data)
   ```

3. **STRUCTURE** master data properly:
   ```json
   {
     "personal_info": {
       "name": "John Doe",
       "ssn": "XXX-XX-1234",
       "dob": "1980-01-01"
     },
     "business_info": {
       "name": "Acme Corp",
       "ein": "12-3456789",
       "type": "LLC"
     },
     "financial_data": {
       "total_assets": 4397552,
       "total_liabilities": 2044663,
       "net_worth": 2352889
     }
   }
   ```

### Phase 2: Fix Part 2 (Form Mapping)

**Goal**: Map master data to 9 forms (distribution)

**Steps**:
1. **CREATE** new `form_mapping_service.py`:
   ```python
   class FormMappingService:
       def __init__(self):
           self.form_specs = load_9_form_specifications()
           
       def map_all_forms(self, app_id):
           master_data = load_master_data(app_id)
           
           for form_id in ALL_9_FORMS:
               form_data = self.map_to_form(master_data, form_id)
               pdf = self.generate_pdf(form_data, form_id)
               self.save_form(app_id, form_id, form_data, pdf)
   ```

2. **USE** form specifications correctly:
   - Templates define what fields each form needs
   - Map master data fields to form field requirements
   - Handle field name variations (e.g., "SSN" → "Social Security Number")

### Phase 3: Integration

**Steps**:
1. **UPDATE** test scripts to use correct flow:
   ```python
   # Part 1: Process all documents
   processor = ComprehensiveProcessor()
   for doc in documents:
       await processor.process_document(doc, app_id)
   
   # Part 2: Map to forms (separate step)
   mapper = FormMappingService()
   forms = mapper.map_all_forms(app_id)
   ```

2. **VALIDATE** output:
   - Check master data has comprehensive extraction
   - Verify 9 PDFs generated
   - Ensure no redundant extraction

### Phase 4: Documentation

**Update**:
1. CLAUDE.md - Document correct workflow
2. README.md - Fix architecture description
3. Test documentation - Update test descriptions

## Common Pitfalls to Avoid

1. **DO NOT** extract documents multiple times with different templates
2. **DO NOT** confuse extraction templates with form templates
3. **DO NOT** map data to the same form it was extracted with
4. **REMEMBER**: Extract once, map to many

## Success Metrics

### Part 1 Success
- Each document extracted ONCE
- Master JSON contains ALL available data
- 85-97% field extraction accuracy
- Incremental updates work correctly

### Part 2 Success
- 9 PDFs generated from single master JSON
- Each form has 70%+ field coverage
- Bank-specific formatting applied
- No redundant processing

## Summary

### What This Architecture IS:
- **Part 1**: Comprehensive extraction into master data pool (extract ONCE)
- **Part 2**: Distribution of master data to 9 different forms (map to MANY)

### What This Architecture IS NOT:
- NOT extracting with 9 templates
- NOT extracting multiple times
- NOT redundant mapping to same forms

### Key Principle:
**Extract Once, Map to Many** - This is the fundamental concept that drives efficiency and reduces processing from 3-5 days to 2-4 hours.