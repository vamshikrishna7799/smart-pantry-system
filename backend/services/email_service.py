import os
import requests
from datetime import datetime

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

def get_api_key():
    return os.getenv('BREVO_API_KEY')

def send_email(recipient, subject, html_content):
    """Send email using Brevo HTTP API"""
    api_key = get_api_key()
    sender_email = os.getenv('MAIL_DEFAULT_SENDER', 'kucharakantivamshikrishna@gmail.com')
    
    if not api_key:
        print("❌ BREVO_API_KEY not set")
        return False
    
    payload = {
        "sender": {"name": "Smart Pantry", "email": sender_email},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html_content
    }
    
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 201:
            print(f"✅ Email sent to {recipient}")
            return True
        else:
            print(f"❌ Brevo API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def send_otp_email(recipient, otp_code):
    subject = "Password Reset OTP - Smart Pantry"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 30px; border-radius: 10px; border: 1px solid #eee;">
            <h2 style="color: #333; text-align: center;">Password Reset Request</h2>
            <p style="color: #666;">Your OTP for password reset is:</p>
            <div style="text-align: center; margin: 30px 0;">
                <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #667eea; background: #f5f5f5; padding: 15px; border-radius: 8px;">
                    {otp_code}
                </div>
            </div>
            <p style="color: #999;">This OTP expires in 10 minutes.</p>
            <p style="color: #999;">If you didn't request this, please ignore this email.</p>
            <hr>
            <p style="color: #999; font-size: 12px;">Smart Pantry System</p>
        </div>
    </div>
    """
    return send_email(recipient, subject, html)

def send_expiry_alert(recipient, item, status):
    subject = "Item Expiring Soon! - Smart Pantry" if status == 'expiring' else "Item Expired! - Smart Pantry"
    color = '#e67e22' if status == 'expiring' else '#e74c3c'
    label = 'Expiring Soon' if status == 'expiring' else 'Expired'
    expiry_date = item.get('expiry_date', 'Unknown')
    if hasattr(expiry_date, 'strftime'):
        expiry_date = expiry_date.strftime('%Y-%m-%d')
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 30px; border-radius: 10px; border: 1px solid #eee;">
            <h2 style="color: {color};">Pantry Alert - {label}</h2>
            <div style="background: #f9f9f9; padding: 20px; border-radius: 10px;">
                <h3 style="color: #333;">Item: {item.get('name', 'Unknown')}</h3>
                <p><strong>Quantity:</strong> {item.get('quantity', 0)}</p>
                <p><strong>Expiry Date:</strong> {expiry_date}</p>
                <p><strong>Location:</strong> {item.get('profile_id', 'Unknown')}</p>
            </div>
            <p>Please check your pantry and take necessary action.</p>
            <hr>
            <p style="color: #999; font-size: 12px;">Smart Pantry System</p>
        </div>
    </div>
    """
    return send_email(recipient, subject, html)

def send_low_stock_alert(recipient, item):
    subject = "Low Stock Alert - Smart Pantry"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 30px; border-radius: 10px; border: 1px solid #eee;">
            <h2 style="color: #e67e22;">Low Stock Alert</h2>
            <div style="background: #f9f9f9; padding: 20px; border-radius: 10px;">
                <h3 style="color: #333;">Item: {item.get('name', 'Unknown')}</h3>
                <p><strong>Quantity:</strong> {item.get('quantity', 0)}</p>
                <p><strong>Location:</strong> {item.get('profile_id', 'Unknown')}</p>
            </div>
            <p>This item is running low. Consider adding it to your shopping list!</p>
            <hr>
            <p style="color: #999; font-size: 12px;">Smart Pantry System</p>
        </div>
    </div>
    """
    return send_email(recipient, subject, html)

def send_shopping_list_email(recipient, items, profile_name):
    subject = "Your Shopping List - Smart Pantry"
    items_html = ""
    for idx, item in enumerate(items, 1):
        items_html += f"""
        <tr style="background: {'#f9f9f9' if idx % 2 == 0 else '#ffffff'};">
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{idx}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item.get('item_name', 'Unknown')}</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('quantity', 0)}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('expiry_date', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('status', 'Unknown')}</td>
        </tr>
        """
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
        <div style="background: white; padding: 30px; border-radius: 10px; border: 1px solid #eee;">
            <h2 style="color: #333; text-align: center;">Your Shopping List</h2>
            <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p><strong>Profile:</strong> {profile_name}</p>
                <p><strong>Total Items:</strong> {len(items)}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #667eea; color: white;">
                        <th style="padding: 12px;">#</th>
                        <th style="padding: 12px;">Item Name</th>
                        <th style="padding: 12px;">Quantity</th>
                        <th style="padding: 12px;">Expiry Date</th>
                        <th style="padding: 12px;">Status</th>
                    </tr>
                </thead>
                <tbody>{items_html}</tbody>
            </table>
            <hr>
            <p style="color: #999; font-size: 12px; text-align: center;">Smart Pantry System</p>
        </div>
    </div>
    """
    return send_email(recipient, subject, html)