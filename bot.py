import os
import sys
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Clean, unfiltered URL to fetch all current BC wildfire data
URL = "https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/BCWS_ActiveFires_PublicView/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
MEMORY_FILE = "known_fires.txt"

# 🔐 SECURE ENVIRONMENT LOADING
# Pulls credentials safely out of the hidden vault first
RAW_SENDER = os.environ.get('SENDER_EMAIL')
RAW_PASSWORD = os.environ.get('EMAIL_PASSWORD')
RAW_RECEIVERS = os.environ.get('RECEIVER_EMAILS')

# Guard fail-safe: Ensure nothing is blank before processing strings
if not all([RAW_SENDER, RAW_PASSWORD, RAW_RECEIVERS]):
    print("❌ Critical configuration fault: Missing values in GitHub Secrets vault.")
    sys.exit(1)

# Safe string cleaning to strip any accidental hidden newlines (\n) or spaces
SENDER_EMAIL = RAW_SENDER.strip()
SENDER_PASSWORD = RAW_PASSWORD.strip()
RECEIVER_DATA = RAW_RECEIVERS.strip()

# Dynamically splits the comma-separated string back into a clean list
RECEIVER_EMAILS = [email.strip() for email in RECEIVER_DATA.split(',')]


def send_email_alert(fire_id, name, status, size):
    """Sends a professionally formatted HTML email notification to multiple recipients."""
    
    # Construct the container
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚠️ WILDFIRE ALERT: New Incident Detected [{fire_id}]"
    msg["From"] = f"BC Wildfire Monitor <{SENDER_EMAIL}>"
    msg["To"] = ", ".join(RECEIVER_EMAILS)

    # Professional HTML Body Content
    html_content = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #333333; line-height: 1.6; padding: 20px; background-color: #f9f9f9;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            
            <div style="background-color: #d32f2f; color: #ffffff; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px;">NEW WILDFIRE DETECTED</h2>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Southeast Fire Centre Tracking Node</p>
            </div>
            
            <div style="padding: 24px;">
                <p style="margin-top: 0; font-size: 15px; color: #555555;">
                    The automated tracking node has intercepted a newly dispatched active incident fitting target protocols. Details are outlined below:
                </p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 15px;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: #666666; width: 35%; border-bottom: 1px solid #eeeeee;">Fire Number:</td>
                        <td style="padding: 10px 0; font-weight: bold; color: #111111; border-bottom: 1px solid #eeeeee;">{fire_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: #666666; border-bottom: 1px solid #eeeeee;">Incident Name:</td>
                        <td style="padding: 10px 0; color: #333333; border-bottom: 1px solid #eeeeee;">{name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: #666666; border-bottom: 1px solid #eeeeee;">Current Status:</td>
                        <td style="padding: 10px 0; color: #333333; border-bottom: 1px solid #eeeeee;">
                            <span style="background-color: #fff3e0; color: #e65100; padding: 3px 8px; border-radius: 4px; font-size: 13px; font-weight: bold;">{status}</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; color: #666666; border-bottom: 1px solid #eeeeee;">Estimated Size:</td>
                        <td style="padding: 10px 0; color: #333333; border-bottom: 1px solid #eeeeee;">{size} Hectares</td>
                    </tr>
                </table>
                
                <p style="font-size: 13px; color: #888888; margin-bottom: 0;">
                    * This is an automated generation pipeline compiled directly from live operational data fields. Do not reply directly to this transmission.
                </p>
            </div>
            
            <div style="background-color: #f1f1f1; padding: 15px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 12px; color: #777777;">
                Perimeter Solutions Monitoring Gateway | Cranbrook Node
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_string())
        print(f"✉️ Professional alert successfully transmitted to all {len(RECEIVER_EMAILS)} nodes!")
    except Exception as e:
        print(f"❌ Transmission pipeline breakdown: {e}")


def load_known_fires():
    if not os.path.exists(MEMORY_FILE):
        return set()
    with open(MEMORY_FILE, "r") as f:
        return set(line.strip() for line in f)


def save_new_fires(new_fires):
    with open(MEMORY_FILE, "a") as f:
        for fire_id in new_fires:
            f.write(f"{fire_id}\n")


def check_fires():
    print("Initiating scans for active Southeast Fire Centre anomalies...")
    try:
        response = requests.get(URL)
        data = response.json()
        all_fires = data.get('features', [])
        
        known_fires = load_known_fires()
        new_fires_detected = []

        for fire in all_fires:
            attributes = fire['attributes']
            fire_id = attributes.get('FIRE_NUMBER', '')
            name = attributes.get('INCIDENT_NAME', 'Unnamed Fire')
            status = attributes.get('FIRE_STATUS', 'Unknown Status')
            size = attributes.get('CURRENT_SIZE', 'Unknown')

            # Filter logic matching Southeast 'N' entries that are active
            if fire_id.upper().startswith('N') and status.lower() != "out":
                if fire_id not in known_fires:
                    print(f"Tracking Event: Found new local anomaly [{fire_id}]")
                    
                    # Fire the HTML Email Engine
                    send_email_alert(fire_id, name, status, size)
                    new_fires_detected.append(fire_id)

        if new_fires_detected:
            save_new_fires(new_fires_detected)
            print(f"Data sync complete. Logged {len(new_fires_detected)} occurrences.")
        else:
            print("System Scan Complete: No state shifts or additions found.")

    except Exception as e:
        print(f"Critical query fault: {e}")


if __name__ == "__main__":
    check_fires()
