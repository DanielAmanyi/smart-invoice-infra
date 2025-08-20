import boto3
import json
import logging
from typing import Dict, List, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

textract = boto3.client('textract')
s3 = boto3.client('s3')

def extract_text_from_s3(bucket: str, key: str) -> Dict[str, Any]:
    """
    Extract text and structured data from invoice using AWS Textract
    """
    try:
        # Use Textract to analyze the document
        response = textract.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        # Extract different types of content
        extracted_data = {
            'raw_text': extract_raw_text(response),
            'key_value_pairs': extract_key_value_pairs(response),
            'tables': extract_tables(response),
            'lines': extract_lines(response)
        }
        
        logger.info(f"Successfully extracted text from {key}")
        return extracted_data
        
    except ClientError as e:
        logger.error(f"Textract error for {key}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting text from {key}: {str(e)}")
        raise

def extract_raw_text(textract_response: Dict) -> str:
    """Extract all text as a single string"""
    text_blocks = []
    for block in textract_response['Blocks']:
        if block['BlockType'] == 'LINE':
            text_blocks.append(block['Text'])
    return '\n'.join(text_blocks)

def extract_key_value_pairs(textract_response: Dict) -> Dict[str, str]:
    """Extract key-value pairs (forms) from Textract response"""
    key_map = {}
    value_map = {}
    block_map = {}
    
    # Create block map
    for block in textract_response['Blocks']:
        block_id = block['Id']
        block_map[block_id] = block
        
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block
    
    # Extract key-value relationships
    kvs = {}
    for key_block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map) if value_block else ""
        kvs[key] = val
    
    return kvs

def extract_tables(textract_response: Dict) -> List[List[str]]:
    """Extract table data from Textract response"""
    tables = []
    
    for block in textract_response['Blocks']:
        if block['BlockType'] == 'TABLE':
            table = extract_table_data(block, textract_response['Blocks'])
            if table:
                tables.append(table)
    
    return tables

def extract_lines(textract_response: Dict) -> List[str]:
    """Extract individual lines of text"""
    lines = []
    for block in textract_response['Blocks']:
        if block['BlockType'] == 'LINE':
            lines.append(block['Text'])
    return lines

def find_value_block(key_block: Dict, value_map: Dict) -> Dict:
    """Find the value block associated with a key block"""
    for relationship in key_block.get('Relationships', []):
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                return value_map.get(value_id)
    return None

def get_text(result: Dict, blocks_map: Dict) -> str:
    """Get text from a block"""
    text = ''
    if result:
        for relationship in result.get('Relationships', []):
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
    return text.strip()

def extract_table_data(table_block: Dict, all_blocks: List[Dict]) -> List[List[str]]:
    """Extract data from a table block"""
    # Implementation for table extraction
    # This is a simplified version - full implementation would handle cell relationships
    return []
