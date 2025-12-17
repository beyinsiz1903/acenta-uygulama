#!/usr/bin/env python3
"""
Test CSV parsing to see what values are being extracted
"""

import csv
import io

csv_content = """room_number,room_type,floor,capacity,base_price,view,bed_type,amenities
C101,deluxe,1,2,150,sea,king,wifi|balcony
C102,standard,1,2,90,city,queen,wifi"""

print("🔍 Testing CSV parsing...")
print(f"CSV Content:\n{csv_content}")

decoded = csv_content
reader = csv.DictReader(io.StringIO(decoded))

print(f"\nFieldnames: {reader.fieldnames}")

for idx, row in enumerate(reader, start=2):
    print(f"\nRow {idx}: {dict(row)}")
    
    room_number = (row.get('room_number') or '').strip()
    room_type = (row.get('room_type') or 'standard').strip() or 'standard'
    floor = int((row.get('floor') or '1').strip() or 1)
    capacity = int((row.get('capacity') or '2').strip() or 2)
    base_price = float((row.get('base_price') or '0').strip() or 0)
    
    view = (row.get('view') or '').strip() or None
    bed_type = (row.get('bed_type') or '').strip() or None
    
    amenities_raw = (row.get('amenities') or '').strip()
    amenities = [a.strip() for a in amenities_raw.split('|') if a.strip()] if amenities_raw else []
    
    print(f"  Parsed values:")
    print(f"    room_number: '{room_number}'")
    print(f"    room_type: '{room_type}'")
    print(f"    floor: {floor}")
    print(f"    capacity: {capacity}")
    print(f"    base_price: {base_price}")
    print(f"    view: '{view}'")
    print(f"    bed_type: '{bed_type}'")
    print(f"    amenities_raw: '{amenities_raw}'")
    print(f"    amenities: {amenities}")