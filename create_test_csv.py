#!/usr/bin/env python3
"""
Create a test CSV with random permissions for testing the CLI functionality.
"""

import csv
import random

# Permission levels according to the design
PERMISSIONS = ['ro', 'rw', 'rws', 'mgr', 'admin', '']  # Empty means no access

def create_test_csv() -> None:
    """Create a test CSV with random permissions."""
    
    # Read the template with proper names and paths
    with open('test_new_template.csv', 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if headers is None:
            print("❌ Error: Could not read headers from template CSV")
            return
        rows = list(reader)
    
    # Take only first 5 records for testing
    test_rows = rows[:5]
    
    # Add random permissions to each record
    for row in test_rows:
        # Get team columns (skip the first 3 required columns)
        team_columns = [col for col in headers if col not in ['record_uid', 'title', 'folder_path']]
        
        # Randomly assign permissions to 1-3 teams per record
        num_teams = random.randint(1, min(3, len(team_columns)))
        selected_teams = random.sample(team_columns, num_teams)
        
        for team_col in selected_teams:
            # Don't assign empty permissions (we want to test actual permissions)
            permission = random.choice(PERMISSIONS[:-1])  # Exclude empty string
            row[team_col] = permission
    
    # Write the test CSV
    with open('test_permissions_fixed.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_rows)
    
    print("✅ Created test_permissions_fixed.csv with 5 records")
    print("\n📋 Test data preview:")
    for i, row in enumerate(test_rows, 1):
        print(f"  Record {i}: {row['title']} -> {row['folder_path']}")
        permissions = []
        for col, val in row.items():
            if col not in ['record_uid', 'title', 'folder_path'] and val:
                # Extract team name from "TeamName (uid)" format
                team_name = col.split(' (')[0] if ' (' in col else col
                permissions.append(f"{team_name}={val}")
        print(f"    Permissions: {', '.join(permissions) if permissions else 'None'}")

if __name__ == "__main__":
    create_test_csv() 