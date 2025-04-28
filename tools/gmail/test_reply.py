from gmail_client import reply_to_email, read_emails


# fetch the latest email to reply to it
emails = read_emails(max_results=1)
email_id = emails[0]['id']
emails = reply_to_email(email_id=email_id, body='LOL')
print(emails)
