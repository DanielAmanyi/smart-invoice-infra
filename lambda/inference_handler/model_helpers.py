import boto3
import json
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize Bedrock client (pay-per-use)
try:
    bedrock = boto3.client('bedrock-runtime')
    BEDROCK_AVAILABLE = True
except Exception as e:
    logger.warning(f"Bedrock not available: {e}")
    BEDROCK_AVAILABLE = False

def infer_invoice_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured invoice data using rule-based + AI approach
    """
    try:
        # Get text data
        full_text = extracted_data.get('raw_text', '')
        key_value_pairs = extracted_data.get('key_value_pairs', {})
        confidence_scores = extracted_data.get('confidence_scores', {})
        
        logger.info(f"Processing invoice with {len(full_text)} characters")
        
        # Start with rule-based extraction (fast and reliable)
        rule_result = extract_with_rules(full_text, key_value_pairs)
        
        # Enhance with AI if available and text quality is good
        if BEDROCK_AVAILABLE and len(full_text) > 50 and confidence_scores.get('overall', 0) > 70:
            try:
                ai_result = extract_with_bedrock(full_text)
                final_result = merge_extraction_results(rule_result, ai_result)
            except Exception as e:
                logger.warning(f"AI extraction failed, using rules only: {e}")
                final_result = rule_result
        else:
            final_result = rule_result
        
        # Add metadata
        final_result['textract_confidence'] = confidence_scores.get('overall', 0)
        final_result['text_length'] = len(full_text)
        
        logger.info(f"Extracted invoice data: vendor={final_result.get('vendor', 'N/A')}, amount={final_result.get('amount', 'N/A')}")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error in invoice inference: {str(e)}")
        # Return minimal fallback result
        return {
            'vendor': 'Unknown',
            'amount': 0.0,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'invoice_number': 'N/A',
            'extraction_method': 'fallback',
            'error': str(e)
        }

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
        'currency': extract_currency(text),
        'line_items': extract_line_items(text),
        'extraction_method': 'rule_based'
    }
    
    return result

def extract_with_bedrock(text: str) -> Dict[str, Any]:
    """
    Use Amazon Bedrock (Claude) for intelligent invoice extraction
    Only called for high-quality text extractions
    """
    try:
        # Limit text to avoid token limits and costs
        limited_text = text[:3000] if len(text) > 3000 else text
        
        prompt = f"""Extract invoice information from this text and return ONLY valid JSON:

{{
    "vendor": "company name that issued the invoice",
    "amount": 0.00,
    "date": "YYYY-MM-DD",
    "invoice_number": "invoice number",
    "tax_amount": 0.00,
    "currency": "USD"
}}

Text: {limited_text}"""

        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',  # Cheaper model
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 500,  # Limit tokens to control cost
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            ai_extracted = json.loads(json_match.group())
            ai_extracted['extraction_method'] = 'bedrock_ai'
            return ai_extracted
        else:
            logger.warning("No valid JSON found in Bedrock response")
            return {'extraction_method': 'bedrock_failed'}
        
    except Exception as e:
        logger.error(f"Bedrock extraction failed: {str(e)}")
        return {'extraction_method': 'bedrock_failed'}

def extract_vendor(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract vendor/company name"""
    # Check key-value pairs first
    vendor_keys = ['vendor', 'company', 'from', 'bill from', 'seller', 'billed by']
    for key in vendor_keys:
        for k, v in kvp.items():
            if any(vk in k.lower() for vk in [key]):
                if v and len(v.strip()) > 2:
                    return v.strip()
    
    # Rule-based extraction from text
    lines = text.split('\n')
    for i, line in enumerate(lines[:8]):  # Check first 8 lines
        line = line.strip()
        if len(line) > 3 and not re.match(r'^(invoice|bill|receipt|date|total)', line.lower()):
            # Look for company indicators
            if any(indicator in line.lower() for indicator in ['inc', 'llc', 'corp', 'ltd', 'company', 'co.']):
                return line
            # If it's the first substantial line, likely the vendor
            if i < 3 and len(line) > 5:
                return line
    
    return lines[0].strip() if lines and len(lines[0].strip()) > 2 else None

def extract_amount(text: str, kvp: Dict[str, str]) -> Optional[float]:
    """Extract total amount"""
    # Check key-value pairs
    amount_keys = ['total', 'amount', 'balance', 'due', 'grand total', 'amount due']
    for key in amount_keys:
        for k, v in kvp.items():
            if key.lower() in k.lower():
                amount = parse_currency(v)
                if amount and amount > 0:
                    return amount
    
    # Rule-based extraction with multiple patterns
    amount_patterns = [
        r'total[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'amount[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'balance[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'due[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'\$(\d{1,3}(?:,\d{3})*\.?\d{0,2})'
    ]
    
    found_amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            amount = parse_currency(match)
            if amount and amount > 0:
                found_amounts.append(amount)
    
    # Return the largest reasonable amount (likely the total)
    if found_amounts:
        # Filter out very small amounts (likely not totals)
        significant_amounts = [a for a in found_amounts if a >= 1.0]
        return max(significant_amounts) if significant_amounts else max(found_amounts)
    
    return None

def extract_date(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract invoice date"""
    # Check key-value pairs
    date_keys = ['date', 'invoice date', 'bill date', 'issued', 'created']
    for key in date_keys:
        for k, v in kvp.items():
            if key.lower() in k.lower():
                parsed_date = parse_date(v)
                if parsed_date:
                    return parsed_date
    
    # Rule-based extraction with comprehensive patterns
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})',
        r'(\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            parsed_date = parse_date(match)
            if parsed_date:
                return parsed_date
    
    return None

def extract_invoice_number(text: str, kvp: Dict[str, str]) -> Optional[str]:
    """Extract invoice number"""
    # Check key-value pairs
    number_keys = ['invoice', 'invoice number', 'number', 'ref', 'reference', 'inv']
    for key in number_keys:
        for k, v in kvp.items():
            if key.lower() in k.lower() and v.strip():
                # Clean up the value
                cleaned = re.sub(r'[^\w\-]', '', v.strip())
                if len(cleaned) > 2:
                    return cleaned
    
    # Rule-based extraction
    patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9\-]+)',
        r'#\s*([A-Z0-9\-]{3,})',
        r'ref\s*:?\s*([A-Z0-9\-]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match) >= 3:  # Reasonable invoice number length
                return match
    
    return None

def extract_tax_amount(text: str) -> Optional[float]:
    """Extract tax amount"""
    tax_patterns = [
        r'tax[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'vat[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'gst[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})',
        r'sales tax[:\s]+\$?(\d{1,3}(?:,\d{3})*\.?\d{0,2})'
    ]
    
    for pattern in tax_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            amount = parse_currency(matches[0])
            if amount and amount > 0:
                return amount
    
    return None

def extract_currency(text: str) -> str:
    """Extract currency code"""
    # Look for currency symbols and codes
    if '$' in text:
        return 'USD'
    elif '€' in text:
        return 'EUR'
    elif '£' in text:
        return 'GBP'
    elif '¥' in text:
        return 'JPY'
    
    # Look for currency codes
    currency_match = re.search(r'\b(USD|EUR|GBP|JPY|CAD|AUD)\b', text, re.IGNORECASE)
    if currency_match:
        return currency_match.group().upper()
    
    return 'USD'  # Default

def extract_line_items(text: str) -> List[Dict[str, Any]]:
    """Extract line items (basic implementation)"""
    lines = text.split('\n')
    items = []
    
    for line in lines:
        line = line.strip()
        # Look for lines with descriptions and amounts
        if '$' in line and len(line) > 15:
            amount_match = re.search(r'\$(\d{1,3}(?:,\d{3})*\.?\d{0,2})', line)
            if amount_match:
                # Remove amount from description
                description = re.sub(r'\$\d{1,3}(?:,\d{3})*\.?\d{0,2}', '', line).strip()
                # Clean up description
                description = re.sub(r'^\d+\s*', '', description)  # Remove leading numbers
                
                if description and len(description) > 3:
                    items.append({
                        'description': description[:100],  # Limit length
                        'amount': parse_currency(amount_match.group(1))
                    })
    
    return items[:5]  # Limit to 5 items to keep response manageable

def parse_currency(value: str) -> Optional[float]:
    """Parse currency string to float"""
    if not value:
        return None
    
    # Remove currency symbols, spaces, and handle commas
    cleaned = re.sub(r'[$€£¥,\s]', '', str(value))
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def parse_date(date_str: str) -> Optional[str]:
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

def merge_extraction_results(rule_result: Dict, ai_result: Dict) -> Dict[str, Any]:
    """Merge rule-based and AI extraction results"""
    if ai_result.get('extraction_method') == 'bedrock_failed':
        return rule_result
    
    merged = rule_result.copy()
    
    # Prefer AI results for certain fields if they seem valid
    for key, value in ai_result.items():
        if key == 'extraction_method':
            merged[key] = 'hybrid_ai_rules'
            continue
            
        if value and str(value).strip():
            # Validate AI results before using them
            if key == 'amount' and isinstance(value, (int, float)) and value > 0:
                merged[key] = float(value)
            elif key == 'tax_amount' and isinstance(value, (int, float)) and value >= 0:
                merged[key] = float(value)
            elif key == 'date' and isinstance(value, str) and len(value) >= 8:
                # Validate date format
                if re.match(r'\d{4}-\d{2}-\d{2}', value):
                    merged[key] = value
            elif key in ['vendor', 'invoice_number', 'currency'] and isinstance(value, str) and len(value.strip()) > 1:
                merged[key] = value.strip()
    
    # Add confidence based on method used
    merged['confidence'] = 'high' if ai_result.get('extraction_method') == 'bedrock_ai' else 'medium'
    
    return merged
