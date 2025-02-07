import os
import re
import json
import pandas as pd
from datetime import datetime

def get_latest_report(reports_dir='server/reports'):
    """Find the most recent report file based on timestamp in filename"""
    try:
        files = [f for f in os.listdir(reports_dir) if f.endswith('.json')]
    except FileNotFoundError:
        raise ValueError(f"Reports directory not found: {reports_dir}")

    # Extract timestamps from filenames
    report_times = []
    pattern = r'_(\d{8}_\d{6})\.json$'
    
    for f in files:
        match = re.search(pattern, f)
        if match:
            timestamp_str = match.group(1)
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            report_times.append((dt, f))
    
    if not report_times:
        raise ValueError("No valid report files found")
    
    # Get most recent file
    latest = max(report_times, key=lambda x: x[0])
    return os.path.join(reports_dir, latest[1])

def save_as_csv(input_path=None, output_dir='user_saved_results'):
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    # Get input file path
    if input_path is None:
        input_path = get_latest_report()
    elif not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Load JSON data
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    # Convert to DataFrame (adjust based on your JSON structure)
    df = pd.DataFrame(data)
    
    # Create output filename
    base_name = os.path.basename(input_path)
    output_name = os.path.splitext(base_name)[0] + '.csv'
    output_path = os.path.join(output_dir, output_name)
    
    # Save as CSV
    df.to_csv(output_path, index=False)
    print(f"Saved results to: {output_path}")
    return output_path

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert Benchy reports to CSV')
    parser.add_argument('--input', '-i', help='Path to specific report file')
    parser.add_argument('--output-dir', '-o', default='user_saved_results',
                      help='Output directory for CSV files')
    
    args = parser.parse_args()
    
    try:
        save_as_csv(args.input, args.output_dir)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

