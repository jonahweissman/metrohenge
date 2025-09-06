#!/usr/bin/env python3
"""
Quick test to verify the escalator CSV data is valid
"""

import csv
import sys

def test_csv_data(filename="src/data/dc_metro_escalators.csv"):
    """Test the CSV data structure and content."""
    print(f"Testing {filename}...")
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            
            print(f"✅ Found {len(rows)} rows")
            print(f"✅ Columns: {', '.join(reader.fieldnames)}")
            
            # Test some sample queries
            print("\n📊 Sample Analysis:")
            
            # Count by conveying type
            conveying_counts = {}
            incline_counts = {}
            level_counts = 0
            
            for row in rows:
                conveying = row.get('conveying', '')
                incline = row.get('incline', '')
                level = row.get('level', '')
                
                conveying_counts[conveying] = conveying_counts.get(conveying, 0) + 1
                if incline:
                    incline_counts[incline] = incline_counts.get(incline, 0) + 1
                if level:
                    level_counts += 1
            
            print(f"Conveying types: {dict(sorted(conveying_counts.items(), key=lambda x: x[1], reverse=True))}")
            print(f"Incline directions: {incline_counts}")
            print(f"Escalators with level info: {level_counts}")
            
            # Show first few rows
            print(f"\n📋 First 3 escalators:")
            for i, row in enumerate(rows[:3]):
                print(f"{i+1}. ID: {row['id']}, Conveying: {row['conveying']}, Location: {row['lat']},{row['lon']}")
                
            return True
            
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    success = test_csv_data()
    sys.exit(0 if success else 1)