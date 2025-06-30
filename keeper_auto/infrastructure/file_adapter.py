"""
File system adapter - isolates file I/O operations.
Provides clean interface for file operations.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import csv
import json
from dataclasses import dataclass

@dataclass
class CSVData:
    """Data structure for CSV file contents."""
    headers: List[str]
    rows: List[Dict[str, str]]

class FileAdapter:
    """Adapter for file system operations."""
    
    def read_csv(self, file_path: Path) -> Optional[CSVData]:
        """Read CSV file and return structured data."""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            
            return CSVData(headers=headers, rows=rows)
        except Exception:
            return None
    
    def write_csv(self, file_path: Path, data: CSVData) -> bool:
        """Write CSV data to file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if data.headers:
                    writer = csv.DictWriter(f, fieldnames=data.headers)
                    writer.writeheader()
                    writer.writerows(data.rows)
                else:
                    # If no headers, write rows as-is
                    if data.rows:
                        writer = csv.DictWriter(f, fieldnames=list(data.rows[0].keys()))
                        writer.writeheader()
                        writer.writerows(data.rows)
            
            return True
        except Exception:
            return False
    
    def read_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON file."""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def write_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Write JSON data to file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def write_text(self, file_path: Path, content: str) -> bool:
        """Write text content to file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception:
            return False
    
    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        return file_path.exists()
    
    def create_directory(self, dir_path: Path) -> bool:
        """Create directory if it doesn't exist."""
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    def list_files(self, dir_path: Path, pattern: str = "*") -> List[Path]:
        """List files in directory matching pattern."""
        try:
            if not dir_path.exists():
                return []
            return list(dir_path.glob(pattern))
        except Exception:
            return []

def create_file_adapter() -> FileAdapter:
    """Factory function to create file adapter."""
    return FileAdapter() 