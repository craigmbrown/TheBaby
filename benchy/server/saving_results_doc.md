# Benchy Report to CSV Converter

## Features
- Auto-detects latest report if none specified
- Handles timestamps in format `YYYYMMDD_HHMMSS`
- Creates output directories automatically
- Preserves filenames with `.csv` extension
- Uses pandas for CSV conversion

## Usage

## Navigate to server folder
```bash
cd benchy_latest/benchy/server
```

## Activate virtual env

```bash
source venv/bin/activate
```

### Basic Use
```bash
python save_benchy.py
```

### Specify Input Report
```bash
python save_benchy.py -i path/to/report_20250103_121219.json
```

### Custom Output Directory
```bash
python save_benchy.py -o custom_output_dir
```

## Configuration
Default report location: `server/reports`  
To change, modify `reports_dir` in `get_latest_report()`

## Output
Generates CSV files with identical base names as source JSON files in specified directory.
