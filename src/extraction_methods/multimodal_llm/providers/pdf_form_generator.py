"""
PDF Form Generator - Fills actual PDF forms with extracted data.
Uses deterministic PDF library for AcroForm manipulation.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

# Try different PDF libraries in order of preference
PDF_LIBRARY = None
try:
    from PyPDFForm import PdfWrapper  # Correct import for PyPDFForm
    PDF_LIBRARY = "PyPDFForm"
except ImportError:
    try:
        import fillpdf
        from fillpdf import fillpdfs
        PDF_LIBRARY = "fillpdf"
    except ImportError:
        try:
            from pypdf import PdfReader, PdfWriter
            PDF_LIBRARY = "pypdf"
        except ImportError:
            try:
                from PyPDF2 import PdfReader, PdfWriter
                PDF_LIBRARY = "PyPDF2"
            except ImportError:
                print("WARNING: No PDF library available. Install with:")
                print("  pip install PyPDFForm  # Recommended")
                print("  pip install fillpdf    # Alternative")
                print("  pip install pypdf      # Basic support")


class AcroFormFiller:
    """
    Deterministic PDF form filler using AcroForm fields.
    Maps extracted data to PDF fields using a mapping registry.
    """
    
    def __init__(self, mapping_path: Optional[Union[str, Path]] = None):
        """
        Initialize with optional mapping file.
        
        Args:
            mapping_path: Path to field mapping JSON file
        """
        self.mapping = None  # None = no mapping (use direct match), {} = empty mapping
        self.template_version = None
        if mapping_path:
            self.load_mapping(mapping_path)
        
        self.pdf_library = PDF_LIBRARY
        print(f"Using PDF library: {self.pdf_library or 'None available'}")
    
    def load_mapping(self, mapping_path: Union[str, Path]) -> None:
        """
        Load field mapping from JSON file.
        
        Intelligently handles two file formats:
        1. Standard _mapping.json: Contains explicit field mappings
           Structure: {"mappings": {"pdf_field": {"source_field": "data_field", "type": "text"}}}
        2. Dynamic _dynamic.json: Contains field definitions from PDF extraction
           Structure: {"fields": {"field_name": {"field_type": "text", ...}}}
           
        When a _dynamic.json is found, it auto-generates 1:1 mappings.
        
        Args:
            mapping_path: Path to mapping file or base path for auto-discovery
        """
        mapping_path = Path(mapping_path)
        
        # First try exact path if it exists
        if mapping_path.exists() and mapping_path.suffix == '.json':
            with open(mapping_path, 'r') as f:
                data = json.load(f)
                
                # Check if it's a standard mapping file
                if 'mappings' in data:
                    self.mapping = data.get('mappings', {})
                    self.template_version = data.get('version', '1.0')
                    print(f"Loaded {len(self.mapping)} field mappings from standard mapping")
                    return
                
                # Check if it's a dynamic form structure file
                elif 'fields' in data:
                    self._convert_dynamic_to_mapping(data)
                    return
        
        # If not found or not a full path, try auto-discovery
        # Remove .json extension if present to get base name
        base_name = mapping_path.stem if mapping_path.suffix == '.json' else str(mapping_path)
        base_dir = mapping_path.parent if mapping_path.parent != Path('.') else Path('outputs/form_mappings')
        
        # Try standard _mapping.json file
        standard_path = base_dir / f"{base_name}_mapping.json"
        if standard_path.exists():
            with open(standard_path, 'r') as f:
                data = json.load(f)
                self.mapping = data.get('mappings', {})
                self.template_version = data.get('version', '1.0')
                print(f"Loaded {len(self.mapping)} field mappings from {standard_path.name}")
                return
        
        # Try dynamic _dynamic.json file
        dynamic_path = base_dir / f"{base_name}_dynamic.json"
        if dynamic_path.exists():
            with open(dynamic_path, 'r') as f:
                data = json.load(f)
                if 'fields' in data:
                    self._convert_dynamic_to_mapping(data)
                    print(f"Generated mappings from {dynamic_path.name}")
                    return
        
        # No mapping found - set to None for direct pass-through
        self.mapping = None
        print("No mapping file found - will use direct field name matching")
    
    def _convert_dynamic_to_mapping(self, dynamic_data: Dict[str, Any]) -> None:
        """
        Convert dynamic form structure to mapping format.
        
        Creates 1:1 mappings where source_field equals pdf_field name.
        This is used when we have a _dynamic.json file from DynamicFormMapper.
        
        Args:
            dynamic_data: Data from _dynamic.json file containing 'fields' key
        """
        self.mapping = {}
        for field_name, field_info in dynamic_data.get('fields', {}).items():
            self.mapping[field_name] = {
                "source_field": field_name,
                "type": field_info.get('field_type', 'text'),
                "required": field_info.get('required', False)
            }
        print(f"Generated {len(self.mapping)} field mappings from dynamic structure")
    
    def fill_pdf(
        self,
        template_path: Union[str, Path],
        data: Dict[str, Any],
        output_path: Union[str, Path],
        flatten: bool = False
    ) -> bool:
        """
        Fill a PDF template with data.
        
        Args:
            template_path: Path to PDF template
            data: Data to fill (from extraction)
            output_path: Where to save filled PDF
            flatten: Whether to flatten form (make non-editable)
            
        Returns:
            True if successful
        """
        template_path = Path(template_path)
        output_path = Path(output_path)
        
        if not template_path.exists():
            print(f"Template not found: {template_path}")
            return False
        
        # Map extracted data to PDF fields
        fill_data = self._map_data_to_fields(data)
        
        print(f"Filling {len(fill_data)} fields in PDF")
        
        # Use appropriate library
        if self.pdf_library == "PyPDFForm":
            return self._fill_with_pypdfform(template_path, fill_data, output_path, flatten)
        elif self.pdf_library == "fillpdf":
            return self._fill_with_fillpdf(template_path, fill_data, output_path, flatten)
        elif self.pdf_library in ["pypdf", "PyPDF2"]:
            return self._fill_with_pypdf(template_path, fill_data, output_path)
        else:
            print("No PDF library available")
            return False
    
    def _map_data_to_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted data to PDF field names.
        
        Three modes of operation:
        1. If self.mapping is a dict with mappings: Use explicit field mappings
        2. If self.mapping is None: Direct pass-through (field names already match PDF)
        3. If self.mapping is empty dict: Use pattern matching fallback
        
        Args:
            data: Extracted data dictionary with field names as keys
            
        Returns:
            Flat dictionary mapping PDF field names to values
        """
        fill_data = {}
        
        # Case 1: We have explicit mappings (from _mapping.json or _dynamic.json)
        if self.mapping is not None and self.mapping:
            for pdf_field, mapping_info in self.mapping.items():
                source_field = mapping_info.get('source_field')
                if source_field and source_field in data:
                    value = data[source_field]
                    
                    # Apply transformation if specified
                    transform = mapping_info.get('transform')
                    value = self._apply_transform(value, transform, mapping_info.get('type'))
                    
                    fill_data[pdf_field] = value
        
        # Case 2: No mapping file found - use direct pass-through
        # This happens when form_filler.py already matched field names correctly
        elif self.mapping is None:
            for key, value in data.items():
                if value is not None:  # Only include non-null values
                    fill_data[key] = self._format_value(value)
        
        # Case 3: Empty mapping dict - use pattern matching as fallback
        # This is for backward compatibility
        else:
            for key, value in data.items():
                if value is None:
                    continue
                    
                # Try pattern matching for common fields
                key_lower = key.lower()
                
                # Direct match first
                if key not in fill_data:
                    fill_data[key] = self._format_value(value)
                
                # Pattern matching for common variations (legacy support)
                elif 'name' in key_lower and 'Name' not in fill_data:
                    fill_data['Name'] = self._format_value(value)
                elif 'ssn' in key_lower and 'Social Security Number' not in fill_data:
                    fill_data['Social Security Number'] = self._format_value(value)
                elif 'phone' in key_lower and 'Mobile Telephone Number' not in fill_data:
                    fill_data['Mobile Telephone Number'] = self._format_value(value)
                elif 'email' in key_lower and 'Email address' not in fill_data:
                    fill_data['Email address'] = self._format_value(value)
        
        return fill_data
    
    def _apply_transform(self, value: Any, transform: Optional[str], field_type: str) -> Any:
        """Apply transformation to value based on field type."""
        if value is None:
            return ""
        
        # Handle checkboxes
        if field_type == "/'Btn":
            # Convert to checkbox value
            if isinstance(value, bool):
                return "Yes" if value else "Off"
            elif str(value).lower() in ['true', 'yes', '1', 'checked']:
                return "Yes"
            else:
                return "Off"
        
        # Handle text fields
        if transform == "uppercase":
            return str(value).upper()
        elif transform == "lowercase":
            return str(value).lower()
        elif transform == "date":
            # Format as MM/DD/YYYY
            if isinstance(value, str) and len(value) >= 8:
                # Try to parse and reformat
                return value  # Keep as is for now
        
        return self._format_value(value)
    
    def _format_value(self, value: Any) -> str:
        """Format value for PDF field."""
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, (int, float)):
            # Remove decimals for whole numbers
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)
        else:
            return str(value)
    
    def _fill_with_pypdfform(
        self,
        template_path: Path,
        data: Dict[str, Any],
        output_path: Path,
        flatten: bool
    ) -> bool:
        """Fill PDF using PyPDFForm library."""
        try:
            from PyPDFForm import PdfWrapper  # Correct import
            
            # Create form object
            pdf = PdfWrapper(str(template_path))
            
            # Filter data for PyPDFForm:
            # - Only include checkboxes that should be checked (true values)
            # - Keep all text fields
            filtered_data = {}
            for key, value in data.items():
                # Check if this is a boolean-like value (checkbox)
                if isinstance(value, bool):
                    # Only include if True (checkbox should be checked)
                    if value:
                        filtered_data[key] = value
                    # Skip False values - PyPDFForm shouldn't touch unchecked boxes
                elif isinstance(value, str) and value.lower() in ['true', 'false']:
                    # String boolean value (from form_filler.py)
                    if value.lower() == 'true':
                        filtered_data[key] = True  # Convert to actual boolean
                    # Skip 'false' values - don't include them
                else:
                    # Include all other values (text fields)
                    filtered_data[key] = value
            
            # Debug: Show what was filtered
            removed_count = len(data) - len(filtered_data)
            if removed_count > 0:
                removed_fields = [k for k in data if k not in filtered_data]
                print(f"  • Filtered {len(data)} fields to {len(filtered_data)} for PyPDFForm")
                print(f"    Removed {removed_count} false checkbox values:")
                for field in removed_fields[:5]:  # Show first 5
                    print(f"      - {field}: {data[field]}")
            else:
                print(f"  • Using all {len(data)} fields (no false checkboxes to remove)")
            
            # Fill the form with filtered data
            pdf.fill(filtered_data)
            
            # Save - use read() method for PyPDFForm 3.x
            with open(output_path, 'wb') as f:
                f.write(pdf.read())
            
            print(f"✅ PDF saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error filling PDF with PyPDFForm: {e}")
            return False
    
    def _fill_with_fillpdf(
        self,
        template_path: Path,
        data: Dict[str, Any],
        output_path: Path,
        flatten: bool
    ) -> bool:
        """Fill PDF using fillpdf library."""
        try:
            from fillpdf import fillpdfs
            
            # Fill and save
            fillpdfs.write_fillable_pdf(
                str(template_path),
                str(output_path),
                data,
                flatten=flatten
            )
            
            print(f"✅ PDF saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error filling PDF with fillpdf: {e}")
            return False
    
    def _fill_with_pypdf(
        self,
        template_path: Path,
        data: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """Fill PDF using pypdf/PyPDF2 library with checkbox support."""
        try:
            if self.pdf_library == "pypdf":
                from pypdf import PdfReader, PdfWriter
            else:
                from PyPDF2 import PdfReader, PdfWriter
            
            # Read template
            reader = PdfReader(str(template_path))
            writer = PdfWriter()
            
            # Clone the reader to preserve form fields
            writer.clone_reader_document_root(reader)
            
            # First, handle text fields using the standard method
            text_data = {}
            checkbox_data = {}
            
            # Separate text fields from checkbox fields
            if "/AcroForm" in reader.trailer["/Root"]:
                acroform = reader.trailer["/Root"]["/AcroForm"]
                if "/Fields" in acroform:
                    for field_ref in acroform["/Fields"]:
                        field = field_ref.get_object()
                        if "/T" in field:
                            field_name = field["/T"]
                            if isinstance(field_name, bytes):
                                field_name = field_name.decode('utf-8', errors='ignore')
                            
                            if field_name in data:
                                field_type = field.get("/FT", "")
                                if field_type == "/Btn":  # Checkbox field
                                    checkbox_data[field_name] = data[field_name]
                                else:  # Text field
                                    text_data[field_name] = data[field_name]
            
            # Update text fields on all pages
            if text_data and writer.get_form_text_fields():
                for page in writer.pages:
                    writer.update_page_form_field_values(page, text_data)
            
            # Handle checkbox fields specially
            if checkbox_data:
                self._update_checkboxes(writer, reader, checkbox_data)
            
            # Set NeedAppearances to ensure fields render
            try:
                if "/AcroForm" in reader.trailer["/Root"]:
                    writer._root_object["/AcroForm"] = reader.trailer["/Root"]["/AcroForm"]
                    writer._root_object["/AcroForm"].update({
                        "/NeedAppearances": True
                    })
            except:
                pass  # Some PDFs don't have AcroForm
            
            # Save
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            print(f"✅ PDF saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error filling PDF with pypdf: {e}")
            return False
    
    def _update_checkboxes(self, writer, reader, checkbox_data: Dict[str, Any]) -> None:
        """
        Update checkbox fields with proper state values.
        
        Checkboxes in PDFs have specific state names (e.g., /Yes, /On, /Off)
        that must be used instead of boolean values.
        
        Args:
            writer: PdfWriter object
            reader: PdfReader object  
            checkbox_data: Dictionary of checkbox field names to values
        """
        # Import NameObject for creating proper PDF name objects
        try:
            from pypdf.generic import NameObject
        except ImportError:
            from PyPDF2.generic import NameObject
            
        if "/AcroForm" not in reader.trailer["/Root"]:
            return
            
        acroform = reader.trailer["/Root"]["/AcroForm"]
        if "/Fields" not in acroform:
            return
        
        # Process each field in the AcroForm
        for field_ref in writer._root_object["/AcroForm"]["/Fields"]:
            field = field_ref.get_object()
            
            if "/T" not in field:
                continue
                
            field_name = field["/T"]
            if isinstance(field_name, bytes):
                field_name = field_name.decode('utf-8', errors='ignore')
            
            # Skip if not a checkbox we're updating
            if field_name not in checkbox_data:
                continue
            
            # Get the value to set
            value = checkbox_data[field_name]
            
            # Determine the checkbox state to use
            checkbox_state = self._get_checkbox_state(field, value)
            
            if checkbox_state:
                # Set the checkbox value with NameObject keys
                field.update({
                    NameObject("/V"): checkbox_state, 
                    NameObject("/AS"): checkbox_state
                })
                
                # Also update any Kids (for radio button groups)
                if "/Kids" in field:
                    for kid_ref in field["/Kids"]:
                        kid = kid_ref.get_object()
                        kid.update({NameObject("/AS"): checkbox_state})
    
    def _get_checkbox_state(self, field, value):
        """
        Determine the appropriate checkbox state based on the field and value.
        
        Args:
            field: PDF field object
            value: The value to set (bool, string, etc.)
            
        Returns:
            The appropriate state name object or None
        """
        # Import Name from pypdf to create proper name objects
        try:
            from pypdf.generic import NameObject
        except ImportError:
            from PyPDF2.generic import NameObject
        
        # Convert value to boolean
        is_checked = False
        if isinstance(value, bool):
            is_checked = value
        elif isinstance(value, str):
            is_checked = value.lower() in ['true', 'yes', '1', 'checked', 'on']
        
        # Get available states from the field's appearance dictionary
        states = []
        if "/AP" in field and "/N" in field["/AP"]:
            appearance = field["/AP"]["/N"]
            if hasattr(appearance, 'keys'):
                states = list(appearance.keys())
        
        # If we found states, use them
        if states:
            if is_checked:
                # Find the "checked" state (not /Off)
                for state in states:
                    state_str = str(state) if not isinstance(state, str) else state
                    if state_str != "/Off":
                        # Return as NameObject
                        return NameObject(state_str) if isinstance(state_str, str) else state
            else:
                return NameObject("/Off")
        
        # Fallback to common checkbox states
        if is_checked:
            # Try common checked states
            return NameObject("/Yes")  # Most common
        else:
            return NameObject("/Off")
    
    def verify_template_hash(self, template_path: Union[str, Path]) -> bool:
        """
        Verify template hasn't changed by checking hash.
        Prevents misaligned fills when banks update forms.
        """
        template_path = Path(template_path)
        
        # Calculate current hash
        with open(template_path, 'rb') as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
        
        # Check against stored hash (would be in mapping file)
        # For now, just return True
        return True


class PDFFormGenerator:
    """
    High-level interface for generating filled PDFs from extracted data.
    Integrates with the existing extraction pipeline.
    """
    
    def __init__(self):
        """Initialize with default settings."""
        self.filler = AcroFormFiller()
        self.mappings_dir = Path("outputs/form_mappings")
    
    def generate_filled_pdf(
        self,
        template_name: str,
        extracted_data: Dict[str, Any],
        output_dir: Union[str, Path] = "outputs/filled_pdfs"
    ) -> Optional[Path]:
        """
        Generate a filled PDF from extracted data.
        
        Args:
            template_name: Name of template (e.g., "Live Oak Express")
            extracted_data: Data extracted from documents
            output_dir: Where to save filled PDFs
            
        Returns:
            Path to filled PDF if successful
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find template and mapping
        if "Live Oak" in template_name:
            template_path = Path("templates/Live Oak Express - Application Forms.pdf")
            mapping_base = self.mappings_dir / "Live Oak Express - Application Forms"
        elif "Huntington" in template_name:
            template_path = Path("templates/Huntington Bank Personal Financial Statement.pdf")
            mapping_base = self.mappings_dir / "Huntington Bank Personal Financial Statement"
        else:
            print(f"Unknown template: {template_name}")
            return None
        
        if not template_path.exists():
            print(f"Template not found: {template_path}")
            return None
        
        # Load mapping - the enhanced load_mapping will try both _mapping.json and _dynamic.json
        self.filler.load_mapping(mapping_base)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{template_path.stem}_filled_{timestamp}.pdf"
        
        # Fill the PDF
        success = self.filler.fill_pdf(
            template_path,
            extracted_data,
            output_file,
            flatten=False  # Keep editable for now
        )
        
        if success:
            return output_file
        return None