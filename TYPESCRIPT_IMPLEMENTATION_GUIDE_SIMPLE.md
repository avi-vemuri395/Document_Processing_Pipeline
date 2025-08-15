# TypeScript Implementation Guide: Two-Part Pipeline

## Core Concept

**The Problem**: Old approach extracted documents 9 times (once per bank form template)  
**The Solution**: Extract ONCE → Map to MANY forms

## Architecture

```
Part 1: Extract data ONCE from documents → Master JSON
Part 2: Map Master JSON → 9 bank forms + spreadsheets
```

---

## Part 1: Document Extraction

### 1.1 Core Extraction Service

```typescript
// services/ComprehensiveProcessor.ts
import { Anthropic } from '@anthropic-ai/sdk';

export class ComprehensiveProcessor {
  private anthropic: Anthropic;
  
  constructor() {
    this.anthropic = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY
    });
  }
  
  async processDocument(
    documentPath: string,
    applicationId: string
  ): Promise<MasterData> {
    // 1. Convert document to images
    const images = await this.documentToImages(documentPath);
    
    // 2. Extract ALL data with Claude Vision
    const extraction = await this.extractWithLLM(images);
    
    // 3. Structure the raw extraction
    const structured = this.structureData(extraction);
    
    // 4. Load existing master data from S3
    const existing = await this.loadMasterData(applicationId);
    
    // 5. Merge new data with existing (last wins)
    const merged = this.mergeData(existing, structured);
    
    // 6. Save back to S3
    await this.saveMasterData(applicationId, merged);
    
    return merged;
  }
  
  private async extractWithLLM(images: Buffer[]): Promise<any> {
    const prompt = `
      Extract ALL information from these financial documents.
      Focus on:
      - Personal info (name, SSN, DOB, address, phone, email)
      - Business info (name, EIN, type, ownership percentage)
      - Financial data (assets, liabilities, income, net worth)
      - Tax data (returns, AGI, schedules)
      - Debt information (creditors, balances, payments)
      
      Return as structured JSON.
    `;
    
    const response = await this.anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          ...images.map(img => ({
            type: 'image',
            source: {
              type: 'base64',
              media_type: 'image/png',
              data: img.toString('base64')
            }
          }))
        ]
      }]
    });
    
    return JSON.parse(response.content[0].text);
  }
  
  private structureData(raw: any): StructuredData {
    // Organize into categories
    const structured = {
      personalInfo: {},
      businessInfo: {},
      financialData: {},
      taxData: {},
      debtSchedules: [],
      metadata: {
        extractionDate: new Date().toISOString()
      }
    };
    
    // Simple categorization based on field names
    for (const [key, value] of Object.entries(raw)) {
      const keyLower = key.toLowerCase();
      
      if (keyLower.includes('name') || keyLower.includes('ssn') || 
          keyLower.includes('address') || keyLower.includes('phone')) {
        structured.personalInfo[key] = value;
      } else if (keyLower.includes('business') || keyLower.includes('ein') || 
                 keyLower.includes('company')) {
        structured.businessInfo[key] = value;
      } else if (keyLower.includes('asset') || keyLower.includes('liability') || 
                 keyLower.includes('income') || keyLower.includes('worth')) {
        structured.financialData[key] = value;
      } else if (keyLower.includes('tax') || keyLower.includes('return')) {
        structured.taxData[key] = value;
      } else if (keyLower.includes('debt') || keyLower.includes('loan')) {
        structured.debtSchedules.push(value);
      }
    }
    
    return structured;
  }
  
  private mergeData(existing: MasterData, newData: StructuredData): MasterData {
    // Simple merge - new values override old ones
    const merged = { ...existing };
    
    for (const category of Object.keys(newData)) {
      if (category === 'metadata') continue;
      
      if (Array.isArray(newData[category])) {
        // Append arrays (like debts)
        merged[category] = [...(existing[category] || []), ...newData[category]];
      } else {
        // Merge objects (last wins)
        merged[category] = { ...existing[category], ...newData[category] };
      }
    }
    
    // Update metadata
    merged.metadata.lastUpdated = new Date().toISOString();
    merged.metadata.documentsProcessed = [
      ...(existing.metadata?.documentsProcessed || []),
      newData.metadata.sourceDocument
    ];
    
    return merged;
  }
}
```

### 1.2 Master Data Structure

```typescript
// types/MasterData.ts
export interface MasterData {
  personalInfo: {
    name?: string;
    ssn?: string;
    dateOfBirth?: string;
    address?: string;
    phone?: string;
    email?: string;
  };
  
  businessInfo: {
    businessName?: string;
    ein?: string;
    businessType?: string;
    ownershipPercentage?: number;
    yearsInBusiness?: number;
  };
  
  financialData: {
    totalAssets?: number;
    totalLiabilities?: number;
    netWorth?: number;
    annualIncome?: number;
    monthlyExpenses?: number;
  };
  
  taxData: {
    [year: string]: {
      agi?: number;
      taxableIncome?: number;
      totalTax?: number;
    };
  };
  
  debtSchedules: Array<{
    creditor: string;
    originalAmount: number;
    currentBalance: number;
    monthlyPayment: number;
    interestRate: number;
  }>;
  
  metadata: {
    applicationId: string;
    lastUpdated: string;
    documentsProcessed: string[];
  };
}
```

---

## Part 2: Form Mapping

### 2.1 Form Mapping Service

```typescript
// services/FormMappingService.ts
export class FormMappingService {
  // Define the 9 forms
  private readonly BANK_FORMS = {
    live_oak: ['application', 'pfs', '4506t'],
    huntington: ['business_app', 'pfs', 'tax_transcript', 'debt_schedule'],
    wells_fargo: ['loan_app', 'financial']
  };
  
  async mapAllForms(applicationId: string): Promise<FormResults> {
    // 1. Load master data from S3
    const masterData = await this.loadMasterData(applicationId);
    
    const results: FormResults = {};
    
    // 2. Process each bank's forms
    for (const [bank, forms] of Object.entries(this.BANK_FORMS)) {
      results[bank] = {};
      
      for (const formType of forms) {
        // 3. Map master data to this specific form
        const mappedData = await this.mapToForm(masterData, bank, formType);
        
        // 4. Save mapped JSON to S3
        await this.saveMappedForm(applicationId, bank, formType, mappedData);
        
        // 5. Generate PDF if template exists
        if (this.hasPdfTemplate(bank, formType)) {
          const pdfPath = await this.generatePdf(
            mappedData,
            bank,
            formType,
            applicationId
          );
          results[bank][formType] = { mappedData, pdfPath };
        } else {
          results[bank][formType] = { mappedData };
        }
      }
    }
    
    return results;
  }
  
  private async mapToForm(
    masterData: MasterData,
    bank: string,
    formType: string
  ): Promise<any> {
    // Load form field specification
    const formSpec = await this.loadFormSpec(bank, formType);
    
    const mapped = {};
    
    // Map each required field
    for (const field of formSpec.fields) {
      // Try direct mapping
      let value = this.findFieldValue(masterData, field.sourcePath);
      
      // Try aliases if no direct match
      if (!value && field.aliases) {
        for (const alias of field.aliases) {
          value = this.findFieldValue(masterData, alias);
          if (value) break;
        }
      }
      
      // Apply transformation if needed
      if (value && field.transform) {
        value = this.applyTransform(value, field.transform);
      }
      
      // Use default if still no value
      if (!value && field.defaultValue) {
        value = field.defaultValue;
      }
      
      if (value) {
        mapped[field.id] = value;
      }
    }
    
    return mapped;
  }
  
  private findFieldValue(data: any, path: string): any {
    // Simple path resolution (e.g., "personalInfo.name")
    const parts = path.split('.');
    let current = data;
    
    for (const part of parts) {
      if (current && typeof current === 'object') {
        current = current[part];
      } else {
        return undefined;
      }
    }
    
    return current;
  }
  
  private applyTransform(value: any, transform: string): any {
    switch (transform) {
      case 'ssn_format':
        // Format SSN as XXX-XX-XXXX
        return value.replace(/(\d{3})(\d{2})(\d{4})/, '$1-$2-$3');
      
      case 'currency':
        // Format as currency
        return parseFloat(value).toFixed(2);
      
      case 'percentage':
        // Convert decimal to percentage
        return (parseFloat(value) * 100).toFixed(2) + '%';
      
      default:
        return value;
    }
  }
}
```

### 2.2 Form Specifications

```typescript
// config/formSpecs/liveOakApplication.ts
export const liveOakApplicationSpec = {
  bankName: 'live_oak',
  formType: 'application',
  fields: [
    {
      id: 'applicant_name',
      sourcePath: 'personalInfo.name',
      aliases: ['personalInfo.fullName', 'personalInfo.applicantName'],
      required: true
    },
    {
      id: 'ssn',
      sourcePath: 'personalInfo.ssn',
      transform: 'ssn_format',
      required: true
    },
    {
      id: 'business_name',
      sourcePath: 'businessInfo.businessName',
      aliases: ['businessInfo.companyName', 'businessInfo.dba'],
      required: true
    },
    {
      id: 'ein',
      sourcePath: 'businessInfo.ein',
      required: true
    },
    {
      id: 'total_assets',
      sourcePath: 'financialData.totalAssets',
      transform: 'currency',
      required: false
    },
    {
      id: 'net_worth',
      sourcePath: 'financialData.netWorth',
      transform: 'currency',
      required: false
    }
    // ... additional fields
  ]
};
```

---

## Part 3: PDF Generation

### 3.1 PDF Generator

```typescript
// services/PDFGenerator.ts
import { PDFDocument } from 'pdf-lib';

export class PDFGenerator {
  async generatePdf(
    mappedData: any,
    templatePath: string,
    outputPath: string
  ): Promise<string> {
    // Load PDF template
    const templateBytes = await fs.readFile(templatePath);
    const pdfDoc = await PDFDocument.load(templateBytes);
    
    // Get form
    const form = pdfDoc.getForm();
    
    // Fill fields
    for (const [fieldId, value] of Object.entries(mappedData)) {
      try {
        const field = form.getField(fieldId);
        
        if (field.constructor.name === 'PDFTextField') {
          field.setText(String(value));
        } else if (field.constructor.name === 'PDFCheckBox') {
          if (value) field.check();
        }
      } catch (e) {
        console.log(`Field ${fieldId} not found in PDF`);
      }
    }
    
    // Save
    const pdfBytes = await pdfDoc.save();
    await fs.writeFile(outputPath, pdfBytes);
    
    return outputPath;
  }
}
```

---

## Part 4: Spreadsheet Generation

### 4.1 Excel Generator

```typescript
// services/SpreadsheetGenerator.ts
import ExcelJS from 'exceljs';

export class SpreadsheetGenerator {
  async generateDebtSchedule(
    masterData: MasterData,
    applicationId: string
  ): Promise<string> {
    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Debt Schedule');
    
    // Headers
    worksheet.addRow(['Debt Schedule']);
    worksheet.addRow(['Applicant:', masterData.personalInfo.name]);
    worksheet.addRow([]);
    worksheet.addRow(['Creditor', 'Original Amount', 'Current Balance', 'Monthly Payment', 'Interest Rate']);
    
    // Add debt rows
    for (const debt of masterData.debtSchedules) {
      worksheet.addRow([
        debt.creditor,
        debt.originalAmount,
        debt.currentBalance,
        debt.monthlyPayment,
        debt.interestRate
      ]);
    }
    
    // Add totals
    const lastRow = worksheet.lastRow.number;
    worksheet.addRow([
      'TOTAL',
      { formula: `SUM(B5:B${lastRow})` },
      { formula: `SUM(C5:C${lastRow})` },
      { formula: `SUM(D5:D${lastRow})` },
      ''
    ]);
    
    // Save
    const outputPath = `outputs/${applicationId}_debt_schedule.xlsx`;
    await workbook.xlsx.writeFile(outputPath);
    
    return outputPath;
  }
}
```

---

## Implementation Order (PRs)

### PR 1: Form Specifications
- Create JSON specs for all 9 forms
- Define field mappings and transformations
- No code changes, just configuration

### PR 2: Document Extraction
- Implement ComprehensiveProcessor
- Add Anthropic SDK integration
- Create master data structure
- Save/load from S3

### PR 3: Form Mapping
- Implement FormMappingService
- Add field mapping logic
- Generate mapped JSON for all forms
- Calculate coverage metrics

### PR 4: PDF Generation
- Add PDF template filling
- Handle different field types
- Generate PDFs for Live Oak and Huntington

### PR 5: Spreadsheet Generation
- Implement Excel generation
- Add Debt Schedule template
- Preserve formulas

### PR 6: Testing & Validation
- Add data validation
- Create integration tests
- Add error handling

---

## Key Implementation Notes

1. **S3 Structure**:
   ```
   s3://bucket/
   ├── applications/
   │   ├── {app-id}/
   │   │   ├── master_data.json
   │   │   ├── documents/
   │   │   ├── mapped_forms/
   │   │   │   ├── live_oak_application.json
   │   │   │   ├── huntington_business_app.json
   │   │   │   └── ...
   │   │   └── generated_pdfs/
   ```

2. **Incremental Processing**:
   - Documents can be added at any time
   - Master data is merged (last wins)
   - Forms regenerated after each update

3. **Error Handling**:
   - LLM extraction failures → retry with backoff
   - Missing fields → use defaults or skip
   - PDF generation failures → save JSON only

4. **Performance**:
   - Single LLM call extracts all data (~$0.02)
   - Mapping is deterministic and fast
   - PDF generation is synchronous

---

## Testing Approach

```typescript
// tests/integration/pipeline.test.ts
describe('Two-Part Pipeline', () => {
  it('should extract once and map to many', async () => {
    // Part 1: Extract
    const processor = new ComprehensiveProcessor();
    const masterData = await processor.processDocument(
      'test-doc.pdf',
      'test-app-001'
    );
    
    expect(masterData.personalInfo).toBeDefined();
    expect(masterData.financialData).toBeDefined();
    
    // Part 2: Map
    const mapper = new FormMappingService();
    const forms = await mapper.mapAllForms('test-app-001');
    
    expect(forms.live_oak).toHaveProperty('application');
    expect(forms.live_oak).toHaveProperty('pfs');
    expect(forms.live_oak).toHaveProperty('4506t');
    expect(forms.huntington).toHaveLength(4);
    expect(forms.wells_fargo).toHaveLength(2);
  });
});
```

---

## Summary

This implementation replicates the Python two-part pipeline in TypeScript:

1. **Extract ONCE**: Use Claude Vision to extract all data from documents
2. **Structure**: Organize into master JSON with categories
3. **Map**: Transform master data to 9 bank-specific forms
4. **Generate**: Create PDFs and Excel files from mapped data

The key is separation: extraction doesn't know about forms, and form mapping doesn't know about extraction. This allows adding new forms without re-extracting documents.