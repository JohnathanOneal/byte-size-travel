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

    def get_contact_details(self, email):
        try:
            response = self.client.get_contact(
                ContactListName='TravelNewsletter',
                EmailAddress=email
            )
            # UnsubscribeAll=False means the contact is subscribed
            is_subscribed = not response.get('UnsubscribeAll', True)
            return {
                'found': True,
                'subscribed': is_subscribed,
                'details': response
            }
        except self.client.exceptions.NotFoundException:
            return {
                'found': False
            }
        except Exception as e:
            print(f"Error retrieving contact: {str(e)}")
            return {
                'found': False,
                'error': str(e)
            }

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

    def send_templated_email(self, contact_list_name, template_name, content_json, topic_name='newsletter'):
        """
        Send a templated email to all subscribers in a contact list.
        
        This implementation retrieves all subscribers and sends emails individually 
        with unsubscribe functionality enabled.
        """
        try:
            # Verify template exists and contains required unsubscribe placeholder
            template_response = self.client.get_email_template(TemplateName=template_name)
            template_html = template_response.get('TemplateContent', {}).get('Html', '')
            
            if "{{amazonSESUnsubscribeUrl}}" not in template_html:
                logger.warning(f"Template {template_name} missing {{amazonSESUnsubscribeUrl}} placeholder")
            
            # Manually get all contacts
            contacts = []
            next_token = None
            
            while True:
                # Prepare parameters for list_contacts call
                params = {'ContactListName': contact_list_name}
                
                # Add filter for topic if specified
                if topic_name:
                    params['Filter'] = {
                        'FilteredStatus': 'OPT_IN',
                        'TopicFilter': {
                            'TopicName': topic_name
                        }
                    }
                
                # Add pagination token if we have one
                if next_token:
                    params['NextToken'] = next_token
                    
                # Get a batch of contacts
                response = self.client.list_contacts(**params)
                
                # Add contacts from this batch
                batch_contacts = response.get('Contacts', [])
                contacts.extend(batch_contacts)
                
                # Check if there are more contacts to fetch
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            logger.info(f"Retrieved {len(contacts)} contacts from list '{contact_list_name}'")
            
            total_sent = 0
            
            # Process contacts individually to enable unsubscribe functionality
            for i, contact in enumerate(contacts):
                email = contact.get('EmailAddress')
                
                # Skip if no email or unsubscribed
                if not email or contact.get('UnsubscribeAll', False):
                    continue
                
                # Get contact attributes for personalization
                personalized_data = dict(content_json)  # Create a copy
                
                if contact.get('AttributesData'):
                    try:
                        attributes = json.loads(contact.get('AttributesData'))
                        personalized_data.update(attributes)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in AttributesData for {email}")
                
                # Send individual email with ListManagementOptions
                try:
                    response = self.client.send_email(
                        FromEmailAddress=os.environ.get("EMAIL_FROM_ADDRESS"),
                        Destination={
                            'ToAddresses': [email]
                        },
                        Content={
                            'Template': {
                                'TemplateName': template_name,
                                'TemplateData': json.dumps(personalized_data)
                            }
                        },
                        ListManagementOptions={
                            'ContactListName': contact_list_name,
                            **({"TopicName": topic_name} if topic_name else {})
                        }
                    )
                    
                    total_sent += 1
                    
                    # Log progress every 10 emails
                    if total_sent % 10 == 0:
                        logger.info(f"Progress: Sent {total_sent}/{len(contacts)} emails")
                    
                    # Short pause to avoid throttling
                    time.sleep(0.1)
                    
                except Exception as email_error:
                    logger.error(f"Error sending to {email}: {str(email_error)}")
                    # Continue with next contact instead of failing entire process
            
            logger.info(f"Email campaign complete: Sent to {total_sent} recipients")
            return {"total_sent": total_sent}
            
        except self.client.exceptions.NotFoundException:
            logger.error(f"Template {template_name} does not exist")
            raise Exception(f"Template {template_name} does not exist. Create it first.")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise e
