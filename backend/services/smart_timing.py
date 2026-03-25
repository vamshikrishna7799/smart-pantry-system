# services/smart_timing.py
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Message
from extensions import mail
from database import users_collection, pantry_items_collection
import requests

class SmartTimingService:
    def __init__(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.setup_schedules()
    
    def setup_schedules(self):
        """Setup scheduled jobs"""
        # Morning digest at 8 AM
        self.scheduler.add_job(
            func=self.send_morning_digest,
            trigger='cron',
            hour=8,
            minute=0,
            id='morning_digest'
        )
        
        # Evening reminders at 6 PM
        self.scheduler.add_job(
            func=self.send_evening_reminders,
            trigger='cron',
            hour=18,
            minute=0,
            id='evening_reminders'
        )
        
        # Weekly report on Sunday at 9 AM
        self.scheduler.add_job(
            func=self.send_weekly_report,
            trigger='cron',
            day_of_week='sun',
            hour=9,
            minute=0,
            id='weekly_report'
        )
        
        self.scheduler.start()
    
    def send_morning_digest(self):
        """Send morning digest of expiring items"""
        with self.app.app_context():
            # Get all users
            users = users_collection.find()
            
            for user in users:
                if not user.get('email'):
                    continue
                
                # Get expiring items
                now = datetime.utcnow()
                expiring_items = list(pantry_items_collection.find({
                    'user_id': user['_id'],
                    'expiry_date': {'$lte': now + timedelta(days=3), '$gt': now},
                    'status': 'active'
                }))
                
                if expiring_items:
                    self.send_digest_email(user['email'], expiring_items, 'morning')
    
    def send_evening_reminders(self):
        """Send evening reminders"""
        with self.app.app_context():
            users = users_collection.find()
            
            for user in users:
                if not user.get('email'):
                    continue
                
                # Get items to check
                low_stock = list(pantry_items_collection.find({
                    'user_id': user['_id'],
                    'quantity': {'$lte': 2, '$gt': 0},
                    'status': 'active'
                }))
                
                if low_stock:
                    self.send_reminder_email(user['email'], low_stock)
    
    def send_weekly_report(self):
        """Send weekly summary report"""
        with self.app.app_context():
            users = users_collection.find()
            
            for user in users:
                if not user.get('email'):
                    continue
                
                # Generate weekly stats
                now = datetime.utcnow()
                week_ago = now - timedelta(days=7)
                
                items_added = pantry_items_collection.count_documents({
                    'user_id': user['_id'],
                    'created_at': {'$gte': week_ago}
                })
                
                items_expired = pantry_items_collection.count_documents({
                    'user_id': user['_id'],
                    'expiry_date': {'$lt': now, '$gte': week_ago},
                    'status': 'active'
                })
                
                items_consumed = pantry_items_collection.count_documents({
                    'user_id': user['_id'],
                    'status': 'deleted',
                    'updated_at': {'$gte': week_ago}
                })
                
                self.send_weekly_email(user['email'], {
                    'items_added': items_added,
                    'items_expired': items_expired,
                    'items_consumed': items_consumed
                })
    
    def check_nearby_stores(self, user_location):
        """Check if user is near grocery stores"""
        # This would integrate with Google Maps API
        # For demo, return mock data
        stores = [
            {'name': 'Walmart', 'distance': 0.5},
            {'name': 'Target', 'distance': 1.2},
            {'name': 'Whole Foods', 'distance': 2.0}
        ]
        
        nearby = [store for store in stores if store['distance'] < 1.0]
        return nearby
    
    def send_digest_email(self, email, items, time_of_day):
        """Send digest email"""
        try:
            msg = Message(
                subject=f"🌅 Good Morning! {len(items)} items expiring soon",
                recipients=[email]
            )
            
            items_html = ""
            for item in items:
                days_left = (item['expiry_date'] - datetime.utcnow()).days
                items_html += f"""
                    <tr>
                        <td>{item['name']}</td>
                        <td>{item['quantity']}</td>
                        <td>{days_left} days</td>
                    </tr>
                """
            
            msg.html = f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>🌅 Morning Pantry Digest</h2>
                <p>Good morning! Here are items expiring soon:</p>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #667eea; color: white;">
                            <th>Item</th>
                            <th>Quantity</th>
                            <th>Days Left</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <p style="margin-top: 20px;">Plan your meals accordingly! 🍳</p>
            </div>
            """
            
            mail.send(msg)
            print(f"✅ Morning digest sent to {email}")
            
        except Exception as e:
            print(f"❌ Failed to send digest: {e}")
    
    def send_reminder_email(self, email, items):
        """Send reminder email"""
        try:
            msg = Message(
                subject="🌙 Evening Pantry Reminder",
                recipients=[email]
            )
            
            items_html = ""
            for item in items:
                items_html += f"• {item['name']} (Only {item['quantity']} left)\n"
            
            msg.body = f"""
            Good evening!
            
            Here are items running low:
            {items_html}
            
            Add them to your shopping list!
            """
            
            mail.send(msg)
            print(f"✅ Reminder sent to {email}")
            
        except Exception as e:
            print(f"❌ Failed to send reminder: {e}")
    
    def send_weekly_email(self, email, stats):
        """Send weekly report email"""
        try:
            msg = Message(
                subject="📊 Your Weekly Pantry Report",
                recipients=[email]
            )
            
            msg.html = f"""
            <div style="font-family: Arial, sans-serif;">
                <h2>📊 Weekly Pantry Report</h2>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0;">
                    <div style="text-align: center; padding: 20px; background: #e8f5e9; border-radius: 10px;">
                        <h3 style="color: #27ae60;">{stats['items_added']}</h3>
                        <p>Items Added</p>
                    </div>
                    <div style="text-align: center; padding: 20px; background: #ffebee; border-radius: 10px;">
                        <h3 style="color: #e74c3c;">{stats['items_expired']}</h3>
                        <p>Items Expired</p>
                    </div>
                    <div style="text-align: center; padding: 20px; background: #e3f2fd; border-radius: 10px;">
                        <h3 style="color: #3498db;">{stats['items_consumed']}</h3>
                        <p>Items Consumed</p>
                    </div>
                </div>
                
                <h3>💡 Tips for next week:</h3>
                <ul>
                    <li>Check expiry dates before shopping</li>
                    <li>Plan meals around items expiring soon</li>
                    <li>Buy only what you need</li>
                </ul>
            </div>
            """
            
            mail.send(msg)
            print(f"✅ Weekly report sent to {email}")
            
        except Exception as e:
            print(f"❌ Failed to send weekly report: {e}")

# Initialize service
smart_timing = None

def init_smart_timing(app):
    global smart_timing
    smart_timing = SmartTimingService(app)
    return smart_timing