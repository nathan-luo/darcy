import os
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://mail.google.com/']

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_PATH = os.path.join(SCRIPT_DIR, 'secrets/client_secret.json')
TOKEN_PATH = os.path.join(SCRIPT_DIR, 'secrets/token.json')

def __authenticate():
    """Authenticate with Gmail API using OAuth2."""
    # Check if token.json exists
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # If credentials are not valid or don't exist, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_PATH, 
                    SCOPES,
                    redirect_uri='http://localhost:8080/'
                )
                creds = flow.run_local_server(port=8080)

        # Save credentials for future use
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def send_email(to: str, subject: str, body: Optional[str] = None, is_html: bool = False) -> bool:
    """
    Send an email using Gmail API.

    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body content
        is_html: Whether the body is HTML content
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """

    service = __authenticate()
    try:
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject

        if not body:
            body = ""

        # Attach body
        if is_html:
            msg = MIMEText(body, 'html')
        else:
            msg = MIMEText(body)
        message.attach(msg)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def read_emails(max_results: int = 10) -> list[dict]:
    """
    Read recent emails from the inbox.

    Args:
        max_results: Maximum number of emails to retrieve
        
    Returns:
        List of dictionaries containing email details
    """
    service = __authenticate()
    try:
        # Get a list of emails from recent inbox
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results
        ).execute()
        messages = results.get('messages', [])
        emails = []
        
        # Get the email details
        for message in messages:
            msg = service.users().messages().get(
                userId='me',
                id=message['id']
            ).execute()

            processed_email = __process_email(msg)
            emails.append(processed_email)
        
        return emails
    except Exception as e:
        print(f"Error reading emails: {str(e)}")
        return [] 

def __process_email(email: dict):
    """
    Process an email and extract relevant information.

    Args:
        email: raw dictionary containing email details sent from gmail api
        
    Returns:
        Dictionary containing processed email information
    """

    processed_email = {}

    # Get the id
    processed_email['id'] = email['id']

    # Get the main headers
    processed_email['headers'] = []
    for header in email['payload']['headers']:
        if not header['name'].startswith('X-'):
            processed_email['headers'].append(header)

    # Get message body
    if 'parts' in email['payload']:
        body = email['payload']['parts'][0]['body'].get('data', '')
    else:
        body = email['payload']['body'].get('data', '')
    # Decode the body
    if body:
        body = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8')

    processed_email['body'] = body
    return processed_email

