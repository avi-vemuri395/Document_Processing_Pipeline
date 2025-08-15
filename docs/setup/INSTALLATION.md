# Installation Guide

This guide provides step-by-step instructions for setting up the Document Processing Pipeline on your local machine.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Document_Processing_Pipeline
```

## Step 2: Set Up Virtual Environment (Recommended)

Using a virtual environment prevents conflicts with system packages:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt when activated.

## Step 3: Install Python Dependencies

Choose one of the following options:

### Option A: Minimal Installation (Recommended for most users)
```bash
pip install -r requirements-minimal.txt
```

### Option B: Full Installation (All features including testing)
```bash
pip install -r requirements.txt
```

### Option C: Manual Installation (If requirements files fail)
```bash
pip install anthropic pydantic python-dotenv pdfplumber pdf2image Pillow pandas openpyxl numpy
```

## Step 4: Install System Dependencies

### macOS
```bash
brew install poppler
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

### Windows
1. Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract the archive
3. Add the `bin` folder to your system PATH

## Step 5: Configure API Key

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Open `.env` in a text editor:
```bash
# macOS/Linux
nano .env

# or use any text editor
open .env  # macOS
```

3. Add your Anthropic API key:
```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-ACTUAL-KEY-HERE
```

4. Save and close the file

## Step 6: Verify Installation

Run the environment check to ensure everything is working:

```bash
# Check environment setup
python3 check_env.py
```

Expected output:
- ✅ Python version OK
- ✅ Anthropic API key found
- ✅ All required packages installed
- ✅ Poppler installed

## Quick Command Reference

Once installed, here are the main commands for the two-part pipeline:

```bash
# Run comprehensive test suite
python3 run_comprehensive_test.py

# Test the two-part pipeline architecture
python3 test_two_part_pipeline.py

# Test with incremental document processing
python3 test_incremental_processing.py

# Test spreadsheet generation
python3 test_spreadsheet_population.py

# Run full 4-phase test
python3 test_comprehensive_end_to_end.py

# Legacy tests (still useful)
python3 test_focused_end_to_end.py      # 2 documents, quick test
python3 test_optimized_end_to_end.py    # 5 documents, comprehensive
```

## Updating Dependencies

To update packages to their latest versions:

```bash
# Update minimal packages
pip install --upgrade -r requirements-minimal.txt

# Or update all packages
pip install --upgrade -r requirements.txt
```

## Uninstalling

To completely remove the installation:

```bash
# Deactivate virtual environment
deactivate

# Remove the project directory
cd ..
rm -rf Document_Processing_Pipeline
```

## Troubleshooting

If you encounter issues, see the [Troubleshooting section in README.md](README.md#troubleshooting) or create an issue on GitHub.

## Next Steps

1. Review the [README.md](README.md) for the two-part pipeline architecture
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design
3. Check [TEST_GUIDE.md](TEST_GUIDE.md) for comprehensive testing information
4. Review `inputs/real/` for sample documents (Brigham Dallas, Hello Sugar)
5. Run `python3 run_comprehensive_test.py` to validate the full pipeline
6. Explore the generated outputs in `outputs/` after running tests