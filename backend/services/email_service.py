import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def get_smtp_connection():
    """Create and return an SMTP connection"""
    smtp_server = os.getenv('MAIL_SERVER', 'smtp-relay.brevo.com')
    port = int(os.getenv('MAIL_PORT', 587))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    if not username or not password:
        raise Exception("Email credentials not configured")
    
    server = smtplib.SMTP(smtp_server, port, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(username, password)
    return server

def send_otp_email(recipient, otp_code):
    """Send OTP using Brevo SMTP"""
    try:
        username = os.getenv('MAIL_USERNAME')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "Password Reset OTP - Smart Pantry"
        
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
        
        msg.attach(MIMEText(html, 'html'))
        
        server = get_smtp_connection()
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        
        print(f"✅ OTP email sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False

def send_expiry_alert(recipient, item, status):
    """Send expiry notification email"""
    try:
        username = os.getenv('MAIL_USERNAME')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "Item Expiring Soon! - Smart Pantry" if status == 'expiring' else "Item Expired! - Smart Pantry"
        
        color = '#e67e22' if status == 'expiring' else '#e74c3c'
        icon = 'Expiring Soon' if status == 'expiring' else 'Expired'
        
        expiry_date = item.get('expiry_date', 'Unknown')
        if hasattr(expiry_date, 'strftime'):
            expiry_date = expiry_date.strftime('%Y-%m-%d')
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; padding: 30px; border-radius: 10px; border: 1px solid #eee;">
                <h2 style="color: {color};">Pantry Alert - {icon}</h2>
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
        
        msg.attach(MIMEText(html, 'html'))
        
        server = get_smtp_connection()
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        
        print(f"✅ Expiry alert sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send expiry alert: {e}")
        return False

def send_low_stock_alert(recipient, item):
    """Send low stock notification email"""
    try:
        username = os.getenv('MAIL_USERNAME')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "Low Stock Alert - Smart Pantry"
        
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
        
        msg.attach(MIMEText(html, 'html'))
        
        server = get_smtp_connection()
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        
        print(f"✅ Low stock alert sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Low stock alert error: {e}")
        return False

def send_shopping_list_email(recipient, items, profile_name):
    """Send shopping list as email"""
    try:
        username = os.getenv('MAIL_USERNAME')
        sender = os.getenv('MAIL_DEFAULT_SENDER', username)
        
        items_html = ""
        for idx, item in enumerate(items, 1):
            reason_icon = {
                'Expired': 'Expired',
                'Low Stock': 'Low Stock',
                'Out of Stock': 'Out of Stock'
            }.get(item.get('status', ''), 'Unknown')
            
            items_html += f"""
            <tr style="background: {'#f9f9f9' if idx % 2 == 0 else '#ffffff'};">
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{idx}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item.get('item_name', 'Unknown')}</strong></td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('quantity', 0)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('expiry_date', 'N/A')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{reason_icon}</td>
            </tr>
            """
        
        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = "Your Shopping List - Smart Pantry"
        
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
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                <hr>
                <p style="color: #999; font-size: 12px; text-align: center;">Smart Pantry System</p>
            </div>
        </div>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = get_smtp_connection()
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        
        print(f"✅ Shopping list sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Shopping list error: {e}")
        return False