import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

def lambda_handler(event, context):
    """
    Monitor daily costs and send alerts if thresholds are exceeded
    """
    ce_client = boto3.client('ce')
    sns_client = boto3.client('sns')
    
    daily_limit = float(os.environ['DAILY_COST_LIMIT'])
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    
    # Get yesterday's costs
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=1)
    
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        # Calculate costs by service
        service_costs = {}
        total_cost = 0
        
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                service_costs[service] = cost
                total_cost += cost
        
        # Check if we exceeded the daily limit
        if total_cost > daily_limit:
            message = f"""
            COST ALERT: Daily spending limit exceeded!
            
            Date: {start_date}
            Total Cost: ${total_cost:.2f}
            Daily Limit: ${daily_limit:.2f}
            Overage: ${total_cost - daily_limit:.2f}
            
            Cost Breakdown:
            """
            
            for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
                if cost > 0.01:  # Only show services with meaningful costs
                    message += f"- {service}: ${cost:.2f}\n"
            
            message += f"""
            
            Please review your usage and consider implementing cost controls.
            """
            
            # Send SNS notification
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject=f"Smart Invoice Pipeline - Cost Alert ({start_date})",
                Message=message
            )
            
            print(f"Cost alert sent: ${total_cost:.2f} > ${daily_limit:.2f}")
        else:
            print(f"Daily cost within limits: ${total_cost:.2f} <= ${daily_limit:.2f}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'total_cost': total_cost,
                'daily_limit': daily_limit,
                'alert_sent': total_cost > daily_limit,
                'service_costs': service_costs
            })
        }
        
    except Exception as e:
        print(f"Error monitoring costs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
