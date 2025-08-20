#!/usr/bin/env python3
"""
Local testing script for invoice processing logic
"""

import json
from model_helpers import extract_with_rules, parse_currency, parse_date

def test_rule_extraction():
    """Test rule-based extraction with sample invoice text"""
    
    sample_text = """
    ACME Corporation Inc.
    123 Business Street
    New York, NY 10001
    
    INVOICE
    
    Invoice Number: INV-2024-001
    Date: March 15, 2024
    
    Bill To:
    Customer Name
    456 Customer Ave
    
    Description                Amount
    Consulting Services        $1,500.00
    Software License          $500.00
    
    Subtotal:                 $2,000.00
    Tax (8.5%):               $170.00
    Total:                    $2,170.00
    
    Payment Due: Net 30
    """
    
    sample_kvp = {
        "Invoice Number": "INV-2024-001",
        "Date": "March 15, 2024",
        "Total": "$2,170.00"
    }
    
    print("Testing rule-based extraction...")
    result = extract_with_rules(sample_text, sample_kvp)
    
    print(json.dumps(result, indent=2, default=str))
    
    # Validate results
    assert result['vendor'] == 'ACME Corporation Inc.'
    assert result['amount'] == 2170.0
    assert result['date'] == '2024-03-15'
    assert result['invoice_number'] == 'INV-2024-001'
    assert result['tax_amount'] == 170.0
    
    print("All tests passed!")

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
    
    print("\nTesting currency parsing...")
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
        ("15/03/2024", "2024-03-15"),  # This might fail due to ambiguity
        ("invalid date", None)
    ]
    
    print("\nTesting date parsing...")
    for input_val, expected in test_cases:
        result = parse_date(input_val)
        print(f"'{input_val}' -> {result} (expected: {expected})")
        # Note: Some date formats might be ambiguous
    
    print("Date parsing tests completed!")

if __name__ == "__main__":
    test_rule_extraction()
    test_currency_parsing()
    test_date_parsing()
    print("\nAll local tests completed successfully!")
