import json
import os
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config.logging_config import ses_logger as logger

SEND_THROTTLE_SECONDS = 0.1
LOG_PROGRESS_INTERVAL = 10


class AmazonSesClient:
    def __init__(self) -> None:
        self.client = boto3.client(
            "sesv2",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION"),
        )

    def get_contact_details(self, email_address: str) -> dict[str, Any]:
        try:
            response = self.client.get_contact(
                ContactListName="TravelNewsletter",
                EmailAddress=email_address,
            )
        except self.client.exceptions.NotFoundException:
            return {"found": False}
        except ClientError as err:
            return {"found": False, "error": str(err)}
        else:
            is_subscribed = not response.get("UnsubscribeAll", True)
            return {
                "found": True,
                "subscribed": is_subscribed,
                "details": response,
            }

    def _verify_contact_list(self) -> dict:
        return self.client.get_contact_list(
            ContactListName=os.environ.get("SES_CONTACT_LIST_NAME")
        )

    def create_contact_list(self) -> dict:
        self.client.create_contact_list(
            ContactListName=os.environ.get("SES_CONTACT_LIST_NAME"),
            Description="Subscribers for travel newsletter",
            Topics=[
                {
                    "TopicName": "newsletter",
                    "DisplayName": "Travel Newsletter",
                    "Description": "travel tips and deals",
                    "DefaultSubscriptionStatus": "OPT_OUT",
                }
            ],
        )
        return self._verify_contact_list()

    def _load_html_template(self, template_path: str) -> str:
        content = Path(template_path).read_text()
        logger.info(
            "Template loaded successfully from %s",
            template_path,
        )
        return content

    def update_html_template(self, template_name: str, template_path: str) -> dict:
        html_template_string = self._load_html_template(template_path)
        template = {
            "TemplateName": template_name,
            "TemplateContent": {
                "Subject": ("{{header.edition_title}} - {{author.date}}"),
                "Text": "Tuna Fish",
                "Html": html_template_string,
            },
        }
        try:
            response = self.client.create_email_template(**template)
            logger.info("Template created successfully")
        except self.client.exceptions.AlreadyExistsException:
            logger.info("Template already exists, updating it...")
            response = self.client.update_email_template(**template)
            logger.info("Template updated successfully")
        return response

    def _retrieve_all_contacts(
        self,
        contact_list_name: str,
        topic_name: str,
    ) -> list[dict]:
        contacts: list[dict] = []
        next_token = None

        while True:
            params: dict[str, Any] = {"ContactListName": contact_list_name}
            if topic_name:
                params["Filter"] = {
                    "FilteredStatus": "OPT_IN",
                    "TopicFilter": {"TopicName": topic_name},
                }
            if next_token:
                params["NextToken"] = next_token

            response = self.client.list_contacts(**params)
            contacts.extend(response.get("Contacts", []))

            next_token = response.get("NextToken")
            if not next_token:
                break

        logger.info(
            "Retrieved %d contacts from list '%s'",
            len(contacts),
            contact_list_name,
        )
        return contacts

    def _send_to_contact(
        self,
        contact: dict,
        template_name: str,
        content_json: dict,
        contact_list_name: str,
        topic_name: str,
    ) -> bool:
        email_addr = contact.get("EmailAddress")
        if not email_addr or contact.get("UnsubscribeAll", False):
            return False

        personalized_data = dict(content_json)
        if contact.get("AttributesData"):
            try:
                attributes = json.loads(contact["AttributesData"])
                personalized_data.update(attributes)
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid JSON in AttributesData for %s",
                    email_addr,
                )

        list_opts: dict[str, str] = {"ContactListName": contact_list_name}
        if topic_name:
            list_opts["TopicName"] = topic_name

        try:
            self.client.send_email(
                FromEmailAddress=os.environ.get("EMAIL_FROM_ADDRESS"),
                Destination={"ToAddresses": [email_addr]},
                Content={
                    "Template": {
                        "TemplateName": template_name,
                        "TemplateData": json.dumps(personalized_data),
                    }
                },
                ListManagementOptions=list_opts,
            )
        except ClientError:
            logger.exception("Error sending to %s", email_addr)
            return False
        else:
            return True

    def send_templated_email(
        self,
        contact_list_name: str,
        template_name: str,
        content_json: dict,
        topic_name: str = "newsletter",
    ) -> dict[str, int]:
        template_response = self.client.get_email_template(TemplateName=template_name)
        template_html = template_response.get("TemplateContent", {}).get("Html", "")

        if "{{amazonSESUnsubscribeUrl}}" not in template_html:
            logger.warning(
                "Template %s missing unsubscribe placeholder",
                template_name,
            )

        contacts = self._retrieve_all_contacts(contact_list_name, topic_name)

        total_sent = 0
        for contact in contacts:
            sent = self._send_to_contact(
                contact,
                template_name,
                content_json,
                contact_list_name,
                topic_name,
            )
            if sent:
                total_sent += 1
                if total_sent % LOG_PROGRESS_INTERVAL == 0:
                    logger.info(
                        "Progress: Sent %d/%d emails",
                        total_sent,
                        len(contacts),
                    )
                time.sleep(SEND_THROTTLE_SECONDS)

        logger.info(
            "Email campaign complete: Sent to %d recipients",
            total_sent,
        )
        return {"total_sent": total_sent}
