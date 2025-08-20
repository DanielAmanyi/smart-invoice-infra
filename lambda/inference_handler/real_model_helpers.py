import boto3
import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

bedrock = boto3.client('bedrock-runtime')

def infer_invoice_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Amazon Bedrock to extract structured invoice data
    """
    try:
        # Combine different text sources
        full_text = extracted_data.get('raw_text', '')
        key_value_pairs = extracted_data.get('key_value_pairs', {})
        
        # First try rule-based extraction for common fields
        rule_based_result = extract_with_rules(full_text, key_value_pairs)
        
        # Then use Bedrock for more complex extraction
        ai_result = extract_with_bedrock(full_text)
        
        # Combine and validate results
        final_result = merge_extraction_results(rule_based_result, ai_result)
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error in invoice inference: {str(e)}")
        # Fallback to rule-based only
        return extract_with_rules(full_text, key_value_pairs)

def extract_with_rules(text: str, key_value_pairs: Dict[str, str]) -> Dict[str, Any]:
    """
    Rule-based extraction for common invoice fields
    """
    result = {
        'vendor': extract_vendor(text, key_value_pairs),
        'amount': extract_amount(text, key_value_pairs),
        'date': extract_date(text, key_value_pairs),
        'invoice_number': extract_invoice_number(text, key_value_pairs),
        'tax_amount': extract_tax_amount(text),
        'line_items': extract_line_items(text),
        'extraction_method': 'rule_based'
    }
    
    return result

def extract_with_bedrock(text: str) -> Dict[str, Any]:
    """
    Use Amazon Bedrock (Claude) for intelligent invoice extraction
    """
    try:
        prompt = f"""
        Extract the following information from this invoice text. Return only valid JSON:

        {{
            "vendor": "company name that issued the invoice",
            "amount": "total amount as number",
            "date": "invoice date in YYYY-MM-DD format",
            "invoice_number": "invoice or reference number",
            "tax_amount": "tax amount as number",
            "currency": "currency code (USD, EUR, etc.)",
            "line_items": [
                {{"description": "item description", "amount": "item amount as number"}}
            ]
        }}

        Invoice text:
        {text[:4000]}  # Limit text to avoid token limits
        """

        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        ai_extracted = json.loads(response_body['content'][0]['text'])
        ai_extracted['extraction_method'] = 'bedrock_ai'
        
        return ai_extracted
        
    except Exception as e:
        logger.error(f"Bedrock extraction failed: {str(e)}")
        return {'extraction_method': 'bedrock_failed'}

def extract_vendor(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract vendor/company name"""
    # Check key-value pairs first
    for key in ['vendor', 'company', 'from', 'bill from', 'seller']:
        if key.lower() in [k.lower() for k in kvp.keys()]:
            return kvp[key]
    
    # Rule-based extraction from text
    lines = text.split('\n')
    # Often the vendor is in the first few lines
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 3 and not re.match(r'^(invoice|bill|receipt)', line.lower()):
            # Skip common headers and look for company-like names
            if any(word in line.lower() for word in ['inc', 'llc', 'corp', 'ltd', 'company']):
                return line
    
    return lines[0].strip() if lines else None

def extract_amount(text: str, kvp: Dict[str, str]) -> Optional[float]:
    """Extract total amount"""
    # Check key-value pairs
    for key in ['total', 'amount', 'balance', 'due', 'grand total']:
        for k, v in kvp.items():
            if key.lower() in k.lower():
                amount = parse_currency(v)
                if amount:
                    return amount
    
    # Rule-based extraction
    amount_patterns = [
        r'total[:\s]+\$?(\d+[,.]?\d*\.?\d*)',
        r'amount[:\s]+\$?(\d+[,.]?\d*\.?\d*)',
        r'balance[:\s]+\$?(\d+[,.]?\d*\.?\d*)',
        r'\$(\d+[,.]?\d*\.?\d*)'
    ]
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the largest amount found (likely the total)
            amounts = [parse_currency(match) for match in matches]
            amounts = [a for a in amounts if a is not None]
            if amounts:
                return max(amounts)
    
    return None

def extract_date(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract invoice date"""
    # Check key-value pairs
    for key in ['date', 'invoice date', 'bill date', 'issued']:
        for k, v in kvp.items():
            if key.lower() in k.lower():
                parsed_date = parse_date(v)
                if parsed_date:
                    return parsed_date
    
    # Rule-based extraction
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            parsed_date = parse_date(matches[0])
            if parsed_date:
                return parsed_date
    
    return None

def extract_invoice_number(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract invoice number"""
    # Check key-value pairs
    for key in ['invoice', 'invoice number', 'number', 'ref', 'reference']:
        for k, v in kvp.items():
            if key.lower() in k.lower() and v.strip():
                return v.strip()
    
    # Rule-based extraction
    patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'#\s*([A-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    
    return None

def extract_tax_amount(text: str) -> Optional[float]:
    """Extract tax amount"""
    tax_patterns = [
        r'tax[:\s]+\$?(\d+[,.]?\d*\.?\d*)',
        r'vat[:\s]+\$?(\d+[,.]?\d*\.?\d*)',
        r'gst[:\s]+\$?(\d+[,.]?\d*\.?\d*)'
    ]
    
    for pattern in tax_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return parse_currency(matches[0])
    
    return None

def extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Extract line items (simplified)"""
    # This is a basic implementation - real-world would be more complex
    lines = text.split('\n')
    items = []
    
    for line in lines:
        # Look for lines with descriptions and amounts
        if '$' in line and len(line.strip()) > 10:
            amount_match = re.search(r'\$(\d+[,.]?\d*\.?\d*)', line)
            if amount_match:
                description = re.sub(r'\$\d+[,.]?\d*\.?\d*', '', line).strip()
                if description:
                    items.append({
                        'description': description,
                        'amount': parse_currency(amount_match.group(1))
                    })
    
    return items[:10]  # Limit to 10 items

def parse_currency(value: str) -> Optional[float]:
    """Parse currency string to float"""
    if not value:
        return None
    
    # Remove currency symbols and spaces
    cleaned = re.sub(r'[$€£¥,\s]', '', str(value))
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def parse_date(date_str: str) -> Optional[str]:
    """Parse date string to ISO format"""
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d',
        '%m-%d-%Y', '%d-%m-%Y', '%B %d, %Y', '%b %d, %Y',
        '%d %B %Y', '%d %b %Y'
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None

def merge_extraction_results(rule_result: Dict, ai_result: Dict) -> Dict[str, Any]:
    """Merge rule-based and AI extraction results"""
    # Prefer AI results for most fields, but use rules as fallback
    merged = rule_result.copy()
    
    for key, value in ai_result.items():
        if value and value != 'bedrock_failed':
            # Validate AI results before using them
            if key == 'amount' and isinstance(value, (int, float)) and value > 0:
                merged[key] = value
            elif key == 'date' and value and len(str(value)) >= 8:
                merged[key] = value
            elif key in ['vendor', 'invoice_number'] and value and len(str(value)) > 1:
                merged[key] = value
            elif key == 'line_items' and isinstance(value, list):
                merged[key] = value
            else:
                merged[key] = value
    
    # Add confidence score based on extraction method
    if ai_result.get('extraction_method') == 'bedrock_ai':
        merged['confidence'] = 'high'
    elif rule_result.get('extraction_method') == 'rule_based':
        merged['confidence'] = 'medium'
    else:
        merged['confidence'] = 'low'
    
    return merged
