"""
Table extraction module for handling financial tables and debt schedules.
Part of Phase 3 implementation.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import json

import pdfplumber
import pandas as pd
import tabula

from .base import BaseExtractor, ExtractionResult
from ..models import FormSpec, FieldSpec, FieldExtractionResult, ExtractionCandidate


class TableStrategy(ABC):
    """Base strategy for table extraction."""
    
    @abstractmethod
    def extract_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables from PDF."""
        pass
    
    @abstractmethod
    def supports_document(self, pdf_path: Path) -> bool:
        """Check if strategy can handle this document."""
        pass


class PDFPlumberStrategy(TableStrategy):
    """Table extraction using PDFPlumber - best for digital PDFs."""
    
    def __init__(self):
        self.name = "pdfplumber"
        self.min_table_rows = 2
        self.min_table_cols = 2
    
    def supports_document(self, pdf_path: Path) -> bool:
        """Check if PDFPlumber can handle this document."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check if PDF has extractable text
                for page in pdf.pages[:3]:  # Check first 3 pages
                    text = page.extract_text()
                    if text and len(text.strip()) > 100:
                        return True
            return False
        except:
            return False
    
    def extract_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables using PDFPlumber."""
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract tables from page
                    page_tables = page.extract_tables()
                    
                    if not page_tables:
                        continue
                    
                    for table_idx, table_data in enumerate(page_tables):
                        if not table_data or len(table_data) < self.min_table_rows:
                            continue
                        
                        # Clean and structure table
                        cleaned_table = self._clean_table(table_data)
                        
                        if cleaned_table and len(cleaned_table) >= self.min_table_rows:
                            # Try to identify table type
                            table_type = self._identify_table_type(cleaned_table)
                            
                            # Convert to DataFrame for easier processing
                            df = self._table_to_dataframe(cleaned_table)
                            
                            table_info = {
                                'page': page_num,
                                'index': table_idx,
                                'type': table_type,
                                'rows': len(df),
                                'columns': len(df.columns),
                                'headers': df.columns.tolist(),
                                'data': df.to_dict('records'),
                                'raw_data': cleaned_table,
                                'strategy': self.name
                            }
                            
                            # Extract key financial values if applicable
                            if table_type in ['debt_schedule', 'asset_list', 'financial_summary']:
                                table_info['extracted_values'] = self._extract_financial_values(df, table_type)
                            
                            tables.append(table_info)
                            
        except Exception as e:
            print(f"  ⚠️  PDFPlumber extraction error: {e}")
        
        return tables
    
    def _clean_table(self, table_data: List[List]) -> List[List]:
        """Clean and normalize table data."""
        cleaned = []
        
        for row in table_data:
            # Skip empty rows
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            # Clean cells
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append('')
                else:
                    # Clean whitespace and normalize
                    cell_str = str(cell).strip()
                    cell_str = re.sub(r'\s+', ' ', cell_str)
                    cleaned_row.append(cell_str)
            
            cleaned.append(cleaned_row)
        
        return cleaned
    
    def _table_to_dataframe(self, table_data: List[List]) -> pd.DataFrame:
        """Convert table data to DataFrame with proper headers."""
        if not table_data:
            return pd.DataFrame()
        
        # Assume first row is header if it contains text
        first_row = table_data[0]
        if all(isinstance(cell, str) and not cell.replace('.', '').replace(',', '').replace('-', '').isdigit() 
               for cell in first_row if cell):
            df = pd.DataFrame(table_data[1:], columns=first_row)
        else:
            # No header, create generic columns
            df = pd.DataFrame(table_data, columns=[f'Column_{i+1}' for i in range(len(table_data[0]))])
        
        return df
    
    def _identify_table_type(self, table_data: List[List]) -> str:
        """Identify the type of financial table."""
        if not table_data:
            return 'unknown'
        
        # Convert to string for pattern matching
        table_text = ' '.join(' '.join(str(cell) for cell in row) for row in table_data).lower()
        
        # Check for debt schedule patterns
        if any(keyword in table_text for keyword in ['debt', 'loan', 'mortgage', 'credit', 'liability', 'payable']):
            return 'debt_schedule'
        
        # Check for asset patterns
        elif any(keyword in table_text for keyword in ['asset', 'property', 'investment', 'real estate', 'portfolio']):
            return 'asset_list'
        
        # Check for income statement patterns
        elif any(keyword in table_text for keyword in ['income', 'revenue', 'expense', 'profit', 'loss', 'earnings']):
            return 'income_statement'
        
        # Check for balance sheet patterns
        elif any(keyword in table_text for keyword in ['balance sheet', 'total assets', 'total liabilities', 'equity']):
            return 'balance_sheet'
        
        # Check for financial summary
        elif any(keyword in table_text for keyword in ['summary', 'total', 'net worth']):
            return 'financial_summary'
        
        return 'general'
    
    def _extract_financial_values(self, df: pd.DataFrame, table_type: str) -> Dict[str, Any]:
        """Extract key financial values from table."""
        values = {}
        
        try:
            if table_type == 'debt_schedule':
                # Look for total debt
                for col in df.columns:
                    if 'balance' in col.lower() or 'amount' in col.lower():
                        # Try to sum numeric values
                        numeric_col = pd.to_numeric(df[col].str.replace(r'[$,]', '', regex=True), errors='coerce')
                        total = numeric_col.sum()
                        if total > 0:
                            values['total_debt'] = float(total)
                            break
                
                # Count number of debts
                values['debt_count'] = len(df)
                
            elif table_type == 'asset_list':
                # Look for total assets
                for col in df.columns:
                    if 'value' in col.lower() or 'amount' in col.lower():
                        numeric_col = pd.to_numeric(df[col].str.replace(r'[$,]', '', regex=True), errors='coerce')
                        total = numeric_col.sum()
                        if total > 0:
                            values['total_assets'] = float(total)
                            break
                
                # Count number of assets
                values['asset_count'] = len(df)
                
            elif table_type in ['balance_sheet', 'financial_summary']:
                # Look for key financial metrics
                for idx, row in df.iterrows():
                    row_text = ' '.join(str(cell).lower() for cell in row.values)
                    
                    # Extract total assets
                    if 'total assets' in row_text:
                        for cell in row.values:
                            numeric_val = self._parse_currency(str(cell))
                            if numeric_val and numeric_val > 1000:  # Likely a real value
                                values['total_assets'] = numeric_val
                                break
                    
                    # Extract total liabilities
                    if 'total liabilities' in row_text:
                        for cell in row.values:
                            numeric_val = self._parse_currency(str(cell))
                            if numeric_val and numeric_val > 1000:
                                values['total_liabilities'] = numeric_val
                                break
                    
                    # Extract net worth
                    if 'net worth' in row_text or 'equity' in row_text:
                        for cell in row.values:
                            numeric_val = self._parse_currency(str(cell))
                            if numeric_val and numeric_val > 1000:
                                values['net_worth'] = numeric_val
                                break
                
        except Exception as e:
            print(f"    ⚠️  Value extraction error: {e}")
        
        return values
    
    def _parse_currency(self, value: str) -> Optional[float]:
        """Parse currency string to float."""
        if not value:
            return None
        
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$,]', '', value.strip())
            # Handle parentheses for negative values
            if '(' in cleaned and ')' in cleaned:
                cleaned = '-' + cleaned.replace('(', '').replace(')', '')
            
            return float(cleaned)
        except:
            return None


class TabulaStrategy(TableStrategy):
    """Table extraction using Tabula - good for structured tables."""
    
    def __init__(self):
        self.name = "tabula"
    
    def supports_document(self, pdf_path: Path) -> bool:
        """Check if Tabula can handle this document."""
        try:
            # Try to read first page
            tables = tabula.read_pdf(str(pdf_path), pages=1, multiple_tables=True, silent=True)
            return len(tables) > 0
        except:
            return False
    
    def extract_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables using Tabula."""
        tables = []
        
        try:
            # Extract all tables from PDF
            dfs = tabula.read_pdf(
                str(pdf_path),
                pages='all',
                multiple_tables=True,
                lattice=True,  # Use lattice for better table detection
                silent=True
            )
            
            for idx, df in enumerate(dfs):
                if df.empty or len(df) < 2:
                    continue
                
                # Clean DataFrame
                df = df.dropna(how='all')
                df = df.reset_index(drop=True)
                
                # Identify table type
                table_text = ' '.join(df.astype(str).values.flatten()).lower()
                table_type = self._identify_table_type(table_text)
                
                table_info = {
                    'page': idx + 1,  # Approximate
                    'index': idx,
                    'type': table_type,
                    'rows': len(df),
                    'columns': len(df.columns),
                    'headers': df.columns.tolist(),
                    'data': df.to_dict('records'),
                    'strategy': self.name
                }
                
                # Extract financial values
                if table_type in ['debt_schedule', 'asset_list', 'financial_summary']:
                    table_info['extracted_values'] = self._extract_financial_values(df, table_type)
                
                tables.append(table_info)
                
        except Exception as e:
            print(f"  ⚠️  Tabula extraction error: {e}")
        
        return tables
    
    def _identify_table_type(self, table_text: str) -> str:
        """Identify table type from text content."""
        # Similar logic to PDFPlumber strategy
        if any(keyword in table_text for keyword in ['debt', 'loan', 'mortgage', 'liability']):
            return 'debt_schedule'
        elif any(keyword in table_text for keyword in ['asset', 'property', 'investment']):
            return 'asset_list'
        elif any(keyword in table_text for keyword in ['income', 'revenue', 'expense']):
            return 'income_statement'
        elif any(keyword in table_text for keyword in ['balance sheet', 'total assets']):
            return 'balance_sheet'
        return 'general'
    
    def _extract_financial_values(self, df: pd.DataFrame, table_type: str) -> Dict[str, Any]:
        """Extract key financial values from DataFrame."""
        values = {}
        
        try:
            # Similar extraction logic to PDFPlumber
            if table_type == 'debt_schedule':
                for col in df.columns:
                    if any(keyword in str(col).lower() for keyword in ['balance', 'amount', 'principal']):
                        numeric_col = pd.to_numeric(df[col], errors='coerce')
                        total = numeric_col.sum()
                        if total > 0:
                            values['total_debt'] = float(total)
                            break
            
            elif table_type == 'asset_list':
                for col in df.columns:
                    if any(keyword in str(col).lower() for keyword in ['value', 'amount', 'worth']):
                        numeric_col = pd.to_numeric(df[col], errors='coerce')
                        total = numeric_col.sum()
                        if total > 0:
                            values['total_assets'] = float(total)
                            break
                            
        except Exception as e:
            print(f"    ⚠️  Value extraction error: {e}")
        
        return values


class TableExtractor(BaseExtractor):
    """
    Specialized extractor for tables in financial documents.
    Handles debt schedules, asset lists, and financial statements.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "table"
        
        # Initialize extraction strategies
        self.strategies = [
            PDFPlumberStrategy(),  # Primary strategy
            TabulaStrategy(),       # Fallback strategy
        ]
        
        # Cache for extracted tables
        self.table_cache = {}
    
    def supports_field(self, field_spec: FieldSpec) -> bool:
        """Check if this extractor can handle the given field."""
        # Support fields that require table extraction
        if field_spec.type == 'table':
            return True
        
        # Support aggregate fields from tables
        if field_spec.id in ['total_debt', 'total_assets', 'debt_count', 'asset_count', 
                              'total_liabilities', 'net_worth']:
            return True
        
        return False
    
    def extract(self,
                pdf_path: Path,
                form_spec: FormSpec,
                field_ids: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract table data from the PDF.
        
        Args:
            pdf_path: Path to PDF file
            form_spec: Form specification
            field_ids: Optional list of field IDs to extract
            
        Returns:
            Extraction results with table data
        """
        print(f"\n📊 Table Extraction: {pdf_path.name}")
        print("-" * 50)
        
        # Create result
        result = ExtractionResult(
            doc_id=str(pdf_path.stem),
            doc_path=str(pdf_path),
            form_id=form_spec.form_id
        )
        
        # Check cache
        cache_key = str(pdf_path)
        if cache_key in self.table_cache:
            print("  📦 Using cached table data")
            tables = self.table_cache[cache_key]
        else:
            # Extract tables using strategies
            tables = self._extract_all_tables(pdf_path)
            self.table_cache[cache_key] = tables
        
        if not tables:
            print("  ⚠️  No tables found in document")
            return result
        
        print(f"  📋 Found {len(tables)} tables")
        
        # Store tables in result
        result.tables = tables
        
        # Extract field values from tables
        fields_to_extract = form_spec.fields
        if field_ids:
            fields_to_extract = [f for f in form_spec.fields if f.id in field_ids]
        
        table_fields = [f for f in fields_to_extract if self.supports_field(f)]
        
        if table_fields:
            print(f"  🔍 Extracting {len(table_fields)} table-related fields")
            
            for field in table_fields:
                value = self._extract_field_from_tables(field, tables)
                
                if value is not None:
                    field_result = FieldExtractionResult(
                        field_id=field.id,
                        field_name=field.field_name
                    )
                    
                    candidate = ExtractionCandidate(
                        value=value,
                        confidence=0.85,
                        source={'method': 'table_extraction', 'strategy': 'multi-strategy'}
                    )
                    
                    field_result.add_candidate(candidate)
                    field_result.select_best_candidate()
                    
                    result.add_field_result(field_result)
                    print(f"  📝 {field.field_name}: {value}")
                    
                    self.stats['fields_extracted'] += 1
                
                self.stats['fields_attempted'] += 1
        
        # Add table summary to metadata
        result.metadata['table_summary'] = {
            'total_tables': len(tables),
            'table_types': list(set(t.get('type', 'unknown') for t in tables)),
            'strategies_used': list(set(t.get('strategy', 'unknown') for t in tables))
        }
        
        # Extract aggregate financial values
        aggregate_values = self._extract_aggregate_values(tables)
        if aggregate_values:
            result.metadata['aggregate_values'] = aggregate_values
            print(f"\n  💰 Aggregate Values:")
            for key, value in aggregate_values.items():
                print(f"     {key}: ${value:,.2f}" if isinstance(value, (int, float)) else f"     {key}: {value}")
        
        print(f"\n  ✅ Extracted {len([f for f in result.fields.values() if f.selected_value])}/{len(table_fields)} table fields")
        
        return result
    
    def _extract_all_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables using all available strategies."""
        all_tables = []
        
        for strategy in self.strategies:
            try:
                if strategy.supports_document(pdf_path):
                    print(f"  🔧 Trying {strategy.name} strategy...")
                    tables = strategy.extract_tables(pdf_path)
                    
                    if tables:
                        print(f"    ✓ Found {len(tables)} tables")
                        all_tables.extend(tables)
                        # If primary strategy works well, we might not need fallback
                        if len(tables) >= 2 and strategy.name == 'pdfplumber':
                            break
                    else:
                        print(f"    ✗ No tables found")
                        
            except Exception as e:
                print(f"    ❌ Strategy failed: {e}")
        
        # Deduplicate tables if multiple strategies found the same ones
        all_tables = self._deduplicate_tables(all_tables)
        
        return all_tables
    
    def _deduplicate_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tables found by multiple strategies."""
        unique_tables = []
        seen_signatures = set()
        
        for table in tables:
            # Create signature based on headers and row count
            headers = tuple(table.get('headers', []))
            rows = table.get('rows', 0)
            signature = (headers, rows)
            
            if signature not in seen_signatures:
                unique_tables.append(table)
                seen_signatures.add(signature)
        
        return unique_tables
    
    def _extract_field_from_tables(self, field: FieldSpec, tables: List[Dict[str, Any]]) -> Any:
        """Extract a specific field value from tables."""
        
        # Handle aggregate fields
        if field.id == 'total_debt':
            for table in tables:
                if table.get('type') == 'debt_schedule':
                    values = table.get('extracted_values', {})
                    if 'total_debt' in values:
                        return values['total_debt']
        
        elif field.id == 'total_assets':
            for table in tables:
                if table.get('type') in ['asset_list', 'balance_sheet']:
                    values = table.get('extracted_values', {})
                    if 'total_assets' in values:
                        return values['total_assets']
        
        elif field.id == 'debt_count':
            for table in tables:
                if table.get('type') == 'debt_schedule':
                    return table.get('rows', 0)
        
        elif field.id == 'asset_count':
            for table in tables:
                if table.get('type') == 'asset_list':
                    return table.get('rows', 0)
        
        # Handle field extraction based on field name patterns
        field_name_lower = field.field_name.lower()
        
        # Look for values in tables based on field name
        for table in tables:
            # Try to find value based on field name
            if 'total' in field_name_lower and 'liabilities' in field_name_lower:
                values = table.get('extracted_values', {})
                if 'total_liabilities' in values:
                    return values['total_liabilities']
            
            elif 'net worth' in field_name_lower:
                values = table.get('extracted_values', {})
                if 'net_worth' in values:
                    return values['net_worth']
        
        return None
    
    def _table_matches_spec(self, table: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        """Check if table matches specification."""
        # Check by type
        if 'type' in spec and table.get('type') != spec['type']:
            return False
        
        # Check by headers
        if 'headers' in spec:
            table_headers = [h.lower() for h in table.get('headers', [])]
            for required_header in spec['headers']:
                if required_header.lower() not in table_headers:
                    return False
        
        return True
    
    def _extract_from_table_data(self, table: Dict[str, Any], spec: Dict[str, Any]) -> Any:
        """Extract specific value from table data."""
        data = table.get('data', [])
        
        if not data:
            return None
        
        # Extract by row/column indices
        if 'row' in spec and 'column' in spec:
            row_idx = spec['row']
            col_idx = spec['column']
            
            if row_idx < len(data):
                row = data[row_idx]
                if isinstance(row, dict):
                    columns = list(row.keys())
                    if col_idx < len(columns):
                        return row[columns[col_idx]]
        
        # Extract by column name and row pattern
        if 'column_name' in spec:
            col_name = spec['column_name']
            row_pattern = spec.get('row_pattern')
            
            for row in data:
                if col_name in row:
                    if row_pattern:
                        # Check if any cell in row matches pattern
                        row_text = ' '.join(str(v) for v in row.values())
                        if row_pattern.lower() in row_text.lower():
                            return row[col_name]
                    else:
                        # Return first non-empty value
                        if row[col_name]:
                            return row[col_name]
        
        return None
    
    def _extract_aggregate_values(self, tables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract aggregate financial values from all tables."""
        aggregates = {}
        
        # Collect all extracted values
        for table in tables:
            if 'extracted_values' in table:
                for key, value in table['extracted_values'].items():
                    if key not in aggregates or value > aggregates.get(key, 0):
                        aggregates[key] = value
        
        # Calculate net worth if we have assets and liabilities
        if 'total_assets' in aggregates and 'total_liabilities' in aggregates:
            aggregates['calculated_net_worth'] = aggregates['total_assets'] - aggregates['total_liabilities']
        
        # Count total tables by type
        table_types = {}
        for table in tables:
            table_type = table.get('type', 'unknown')
            table_types[table_type] = table_types.get(table_type, 0) + 1
        
        aggregates['table_counts'] = table_types
        
        return aggregates