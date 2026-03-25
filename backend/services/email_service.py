from flask_mail import Message
from extensions import mail
from datetime import datetime
import os

def send_otp_email(recipient, otp_code):
    """Send OTP for password reset"""
    try:
        msg = Message(
            subject="🔐 Password Reset OTP - Smart Pantry",
            recipients=[recipient]
        )
        msg.body = f"""
        Hello,
        
        Your OTP for password reset is: {otp_code}
        
        This OTP is valid for 10 minutes.
        
        If you didn't request this, please ignore this email.
        
        - Smart Pantry Team
        """
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
            <div style="background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #333; text-align: center; margin-bottom: 20px;">🔐 Password Reset Request</h2>
                <p style="color: #666; font-size: 16px;">Hello,</p>
                <p style="color: #666; font-size: 16px;">You requested to reset your password. Use the following OTP to proceed:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #667eea; background: #f5f5f5; padding: 15px; border-radius: 8px; border: 2px dashed #667eea;">
                        {otp_code}
                    </div>
                </div>
                <p style="color: #999; font-size: 14px;">This OTP will expire in 10 minutes.</p>
                <p style="color: #999; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">Smart Pantry System - Keep your pantry organized!</p>
            </div>
        </div>
        """
        mail.send(msg)
        print(f"✅ OTP email sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP email: {e}")
        return False

def send_expiry_alert(recipient, item, status):
    """Send expiry notification email"""
    try:
        subject = "⚠️ Item Expiring Soon!" if status == 'expiring' else "❌ Item Expired!"
        item_name = item.get('name', 'Unknown')
        expiry_date = item.get('expiry_date', datetime.now()).strftime('%Y-%m-%d')
        quantity = item.get('quantity', 0)
        profile = item.get('profile_id', 'Unknown')
        
        msg = Message(
            subject=f"{subject} - Smart Pantry",
            recipients=[recipient]
        )
        
        color = '#e67e22' if status == 'expiring' else '#e74c3c'
        icon = '⚠️' if status == 'expiring' else '❌'
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
            <div style="background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: {color};">{icon} Pantry Alert</h2>
                
                <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333;">Item: {item_name}</h3>
                    <p><strong>Quantity:</strong> {quantity}</p>
                    <p><strong>Expiry Date:</strong> {expiry_date}</p>
                    <p><strong>Location:</strong> {profile}</p>
                    <p><strong>Status:</strong> {'Expiring Soon' if status == 'expiring' else 'Expired'}</p>
                </div>
                
                <p style="color: #666;">Please check your pantry and take necessary action.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">- Smart Pantry System</p>
            </div>
        </div>
        """
        mail.send(msg)
        print(f"✅ Expiry alert sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send expiry alert: {e}")
        return False

def send_low_stock_alert(recipient, item):
    """Send low stock notification email"""
    try:
        msg = Message(
            subject="📦 Low Stock Alert - Smart Pantry",
            recipients=[recipient]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
            <div style="background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #e67e22;">📦 Low Stock Alert</h2>
                
                <div style="background: #f9f9f9; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333;">Item: {item.get('name', 'Unknown')}</h3>
                    <p><strong>Current Quantity:</strong> {item.get('quantity', 0)} {item.get('unit', 'pcs')}</p>
                    <p><strong>Location:</strong> {item.get('profile_id', 'Unknown')}</p>
                </div>
                
                <p style="color: #666;">This item is running low. Consider adding it to your shopping list!</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">- Smart Pantry System</p>
            </div>
        </div>
        """
        mail.send(msg)
        print(f"✅ Low stock alert sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send low stock alert: {e}")
        return False

def send_shopping_list_email(recipient, items, profile_name):
    """Send shopping list as email"""
    try:
        msg = Message(
            subject="🛒 Your Shopping List - Smart Pantry",
            recipients=[recipient]
        )
        
        # Generate shopping list HTML
        items_html = ""
        total_items = len(items)
        
        for idx, item in enumerate(items, 1):
            reason_icon = {
                'Expired': '🔴',
                'Low Stock': '🟡',
                'Out of Stock': '⚫'
            }.get(item['status'], '📦')
            
            items_html += f"""
            <tr style="background: {'#f9f9f9' if idx % 2 == 0 else '#ffffff'};">
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{idx}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{item['item_name']}</strong></td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{item['quantity']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{item.get('expiry_date', 'N/A')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{reason_icon} {item['status']}</td>
            </tr>
            """
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
            <div style="background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #333; text-align: center; margin-bottom: 20px;">🛒 Your Shopping List</h2>
                
                <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="margin: 5px 0;"><strong>Profile:</strong> {profile_name}</p>
                    <p style="margin: 5px 0;"><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                    <p style="margin: 5px 0;"><strong>Total Items:</strong> {total_items}</p>
                </div>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead>
                        <tr style="background: #667eea; color: white;">
                            <th style="padding: 12px; text-align: left;">#</th>
                            <th style="padding: 12px; text-align: left;">Item Name</th>
                            <th style="padding: 12px; text-align: left;">Quantity</th>
                            <th style="padding: 12px; text-align: left;">Expiry Date</th>
                            <th style="padding: 12px; text-align: left;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding: 20px; background: #f5f5f5; border-radius: 8px;">
                    <h3 style="color: #333; margin-bottom: 10px;">Shopping Tips:</h3>
                    <ul style="color: #666; line-height: 1.6;">
                        <li>🔴 Red items are expired - replace immediately</li>
                        <li>🟡 Yellow items are running low - restock soon</li>
                        <li>⚫ Black items are out of stock - add to cart</li>
                        <li>Check expiry dates before purchasing</li>
                    </ul>
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">- Smart Pantry System - Keep your pantry organized!</p>
            </div>
        </div>
        """
        
        msg.body = f"Shopping List for {profile_name}\nTotal Items: {total_items}\n\nDownload the HTML version for better formatting."
        
        mail.send(msg)
        print(f"✅ Shopping list email sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send shopping list email: {e}")
        return False