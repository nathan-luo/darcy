from gmail_client import GmailClient
import json
gmail_client = GmailClient()

emails = gmail_client.read_emails(max_results=1)
