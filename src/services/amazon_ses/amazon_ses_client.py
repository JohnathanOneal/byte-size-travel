import json
import re
import os
import boto3
import os
import time
from config.logging_config import ses_logger as logger


class AmazonSesClient:
    def __init__(self):
        """
        Initialize an Amazon SES Client
        """
        self.client = boto3.client("sesv2",
                                  aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), 
                                  aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                                  region_name=os.environ.get("AWS_REGION"))

    def _verify_contact_list(self):
        return self.client.get_contact_list(ContactListName=os.environ.get("SES_CONTACT_LIST_NAME"))

    def create_contact_list(self):
        response = self.client.create_contact_list(
            ContactListName=os.environ.get("SES_CONTACT_LIST_NAME"),
            Description='Subscribers for travel newsletter',
            Topics=[{
                'TopicName': 'newsletter',
                'DisplayName': 'Travel Newsletter',
                'Description': 'travel tips and deals',
                'DefaultSubscriptionStatus': 'OPT_OUT'
            }]
        )

        return self._verify_contact_list()
    
    def _load_html_template(self, template_path):
        """
        Load an HTML template file that contains Handlebars syntax
        
        Args:
            template_path: Path to the HTML template file
            
        Returns:
            The html template as a string
        """
        with open(template_path, 'r') as file:
            template_string = file.read()

        logger.info(f"Template loaded successfully from {template_path}")

        return template_string
    
    def update_html_template(self, template_name, template_path):
        """
        Update or create an SES template with Handlebars syntax
        
        Args:
            template_name: Name of the template in SES
            template_path: File path to an HTML template file with Handlebars syntax
            
        Returns:
            SES response
        """
        html_template_string = self._load_html_template(template_path)
        template = {
            'TemplateName': template_name,
            'TemplateContent': {
                'Subject': '{{header.edition_title}} - {{author.date}}',
                'Text': 'Tuna Fish',
                'Html': html_template_string
            }
        }
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
        # Check if template exists
        try:
            template_response = self.client.get_email_template(TemplateName=template_name)
            template_html = template_response.get('TemplateContent', {}).get('Html', '')
            
            # Send the email
            params = {
                'FromEmailAddress': os.environ.get("EMAIL_FROM_ADDRESS"),
                'Destination': {
                    'ToAddresses': [os.environ.get("TEST_SINGLE_EMAIL")]
                },
                'Content': {
                    'Template': {
                        'TemplateName': template_name,
                        'TemplateData': json.dumps(content_json)
                    }
                }
            }
            
            response = self.client.send_email(**params)
            logger.info(f"Email sent successfully, message ID: {response['MessageId']}")
            return response
                
        except self.client.exceptions.NotFoundException:
            logger.error(f"Template {template_name} does not exist")
            raise Exception(f"Template {template_name} does not exist. Create it first.")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise e