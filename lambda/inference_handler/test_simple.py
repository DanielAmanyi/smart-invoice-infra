#!/usr/bin/env python3
"""
Simple test without AWS dependencies
"""

import re
from datetime import datetime

def parse_currency(value: str):
    """Parse currency string to float"""
    if not value:
        return None
    
    # Remove currency symbols, spaces, and handle commas
    cleaned = re.sub(r'[$€£¥,\s]', '', str(value))
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def parse_date(date_str: str):
    """Parse date string to ISO format"""
    if not date_str:
        return None
    
    # Clean the date string
    date_str = date_str.strip()
    
    # Common date formats
    formats = [
        '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d',
        '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y',
        '%d %B %Y', '%d %b %Y', '%m/%d/%y', '%d/%m/%y'
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None

def test_currency_parsing():
    """Test currency parsing function"""
    test_cases = [
        ("$1,234.56", 1234.56),
        ("1234.56", 1234.56),
        ("$1,000", 1000.0),
        ("€500.00", 500.0),
        ("invalid", None),
        ("", None)
    ]
    
    print("Testing currency parsing...")
    for input_val, expected in test_cases:
        result = parse_currency(input_val)
        print(f"'{input_val}' -> {result} (expected: {expected})")
        assert result == expected, f"Failed for {input_val}"
    
    print("Currency parsing tests passed!")

def test_date_parsing():
    """Test date parsing function"""
    test_cases = [
        ("March 15, 2024", "2024-03-15"),
        ("03/15/2024", "2024-03-15"),
        ("2024-03-15", "2024-03-15"),
        ("Mar 15, 2024", "2024-03-15"),
    ]
    
    print("\nTesting date parsing...")
    for input_val, expected in test_cases:
        result = parse_date(input_val)
        print(f"'{input_val}' -> {result} (expected: {expected})")
        if expected:  # Only assert for cases we expect to work
            assert result == expected, f"Failed for {input_val}"
    
    print("Date parsing tests passed!")

def test_regex_patterns():
    """Test regex patterns for extraction"""
    sample_text = """
    ACME Corporation Inc.
    Invoice Number: INV-2024-001
    Total: $2,170.00
    Tax: $170.00
    """
    
    # Test amount extraction
    amount_pattern = r'total[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})'
    matches = re.findall(amount_pattern, sample_text, re.IGNORECASE)
    print(f"\nAmount matches: {matches}")
    assert '2,170.00' in matches
    
    # Test invoice number extraction
    inv_pattern = r'invoice\s+number[:\s]+([A-Z0-9\-]+)'
    matches = re.findall(inv_pattern, sample_text, re.IGNORECASE)
    print(f"Invoice number matches: {matches}")
    assert 'INV-2024-001' in matches
    
    print("Regex pattern tests passed!")

if __name__ == "__main__":
    test_currency_parsing()
    test_date_parsing()
    test_regex_patterns()
    print("\nAll simple tests completed successfully!")
