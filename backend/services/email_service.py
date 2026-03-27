import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_otp_email(recipient, otp_code):
    """Send OTP using Brevo SMTP"""
    try:
        smtp_server = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
        port = int(os.getenv('MAIL_PORT', 587))
        username = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "🔐 Password Reset OTP - Smart Pantry"
        
        # HTML content
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #667eea;">🔐 Password Reset Request</h2>
            <p>Your OTP for password reset is:</p>
            <div style="font-size: 36px; font-weight: bold; padding: 20px; background: #f5f5f5; text-align: center;">
                {otp_code}
            </div>
            <p>This OTP expires in 10 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr>
            <p style="font-size: 12px; color: #999;">Smart Pantry System</p>
        </div>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ OTP email sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False

def send_low_stock_alert(recipient, item):
    """Send low stock alert"""
    try:
        smtp_server = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
        port = int(os.getenv('MAIL_PORT', 587))
        username = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "📦 Low Stock Alert - Smart Pantry"
        
        html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>📦 Low Stock Alert</h2>
            <p><strong>Item:</strong> {item.get('name', 'Unknown')}</p>
            <p><strong>Quantity:</strong> {item.get('quantity', 0)}</p>
            <p><strong>Location:</strong> {item.get('profile_id', 'Unknown')}</p>
            <p>This item is running low. Add it to your shopping list!</p>
        </div>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Low stock alert sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Low stock alert error: {e}")
        return False

def send_shopping_list_email(recipient, items, profile_name):
    """Send shopping list"""
    try:
        smtp_server = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
        port = int(os.getenv('MAIL_PORT', 587))
        username = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        # Build items table
        items_html = ""
        for idx, item in enumerate(items, 1):
            items_html += f"""
            <tr>
                <td style="padding: 8px;">{idx}</td>
                <td><strong>{item['item_name']}</strong></td>
                <td>{item['quantity']}</td>
                <td>{item.get('expiry_date', 'N/A')}</td>
                <td>{item['status']}</td>
            </tr>
            """
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "🛒 Your Shopping List - Smart Pantry"
        
        html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>🛒 Shopping List - {profile_name}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #667eea; color: white;">
                        <th>#</th><th>Item</th><th>Qty</th><th>Expiry</th><th>Status</th>
                    </tr>
                </thead>
                <tbody>{items_html}</tbody>
            </table>
        </div>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Shopping list sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Shopping list error: {e}")
        return False