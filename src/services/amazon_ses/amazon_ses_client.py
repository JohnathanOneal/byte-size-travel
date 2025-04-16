import json
import os
import boto3
from typing import Optional
from config.logging_config import ses_logger as logger

class AmazonSesClient:
    def __init__(self):
        """
        Initialize an Amazon SES Cleint
        
        Args:
            region_name: Optional Region Naem. If not provided, will default to us-east-1
        """
        self.client = boto3.client("sesv2",
                                   aws_access_key_id=os.get("AWS_ACCESS_KEY_ID"), 
                                   aws_secret_access_key=os.get("AWS_SECRET_ACCESS_KEY"),
                                   region_name=os.get("AWS_REGION"))

    
    def update_html_template(self, template_name, html_template_string):
        template = {
        'TemplateName': template_name,
        'SubjectPart': '{{subject}}',
        'TextPart': 'Tuna Fish',
        'HtmlPart': html_template_string}

        try:
            response = self.client.create_email_template(**template)
            logger.info("Template created successfully")
            return response
        except self.client.exceptions.AlreadyExistsException:
            logger.info("Template already exists, updating it...")
            response = self.client.update_email_template(**template)
            logger.info("Template updated successfully")
            return response
        

    def send_templated_email(self, template_name, content_json):

        params = {
            'FromEmailAddress': os.get("EMAIL_FROM_ADDRESS"),
            'Destination': {
                'ToAddresses': [os.get("TEST_SINGLE_EMAIL")]
            },
            'Template': template_name,
            'TemplateData': json.dumps(content_json)
        }
        
        try:
            response = self.client.send_email(**params)
            logger.info(f"Email sent successfully, message ID: {response['MessageId']}")
            return response
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise e
