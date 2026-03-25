# app1.py
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_mail import Mail
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import Config
import certifi
import threading
import time
from datetime import datetime, timedelta
import os
from bson import ObjectId

# Get the correct paths
backend_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(backend_dir, '..', 'frontend')

# Initialize Flask app with frontend folder for static files
app = Flask(__name__, 
            static_folder=frontend_dir, 
            static_url_path='')
app.config.from_object(Config)

# Enable CORS
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Initialize JWT
jwt = JWTManager(app)

# Initialize Mail
mail = Mail(app)

# MongoDB Connection
try:
    client = MongoClient(Config.MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
    # Send a ping to confirm a successful connection
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB Atlas!")
    
    # Get database
    db = client[Config.MONGO_DB_NAME]
    
    # Create collections
    users_collection = db['users']
    pantry_items_collection = db['pantry_items']
    profiles_collection = db['profiles']
    otp_collection = db['otp_requests']
    consumption_history = db['consumption_history']
    
    # Create indexes for better performance
    users_collection.create_index('email', unique=True)
    users_collection.create_index('username', unique=True)
    pantry_items_collection.create_index([('user_id', 1), ('profile_id', 1), ('name', 1)])
    pantry_items_collection.create_index('expiry_date')
    pantry_items_collection.create_index([('user_id', 1), ('created_at', -1)])
    pantry_items_collection.create_index([('user_id', 1), ('status', 1), ('expiry_date', 1)])
    pantry_items_collection.create_index([('user_id', 1), ('name', 1), ('created_at', -1)])
    profiles_collection.create_index([('user_id', 1), ('profile_name', 1)], unique=True)
    
    print("✅ Database indexes created successfully!")
    
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    import sys
    sys.exit(1)

# Import routes
from routes.auth_routes import auth_bp
from routes.pantry_routes import pantry_bp
from routes.profile_routes import profile_bp
from routes.analytics_routes import analytics_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/user')
app.register_blueprint(pantry_bp, url_prefix='/api/pantry')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')

# Import email service functions
from services.email_service import send_expiry_alert, send_low_stock_alert
from services.smart_timing import init_smart_timing

# Initialize smart timing service
smart_timing_service = init_smart_timing(app)

# Background thread for expiry notifications
def check_expiry_notifications():
    """Background thread to check for expiring items and send notifications"""
    with app.app_context():  # Create application context for the thread
        while True:
            try:
                print("🔍 Checking for expired and expiring items...")
                # Get current time
                now = datetime.utcnow()
                
                # Find items expiring in next 3 days
                expiring_soon = list(pantry_items_collection.find({
                    'expiry_date': {
                        '$gte': now,
                        '$lte': now + timedelta(days=3)
                    },
                    'notification_sent': {'$ne': True}
                }))
                
                # Find expired items
                expired = list(pantry_items_collection.find({
                    'expiry_date': {'$lt': now},
                    'notification_sent': {'$ne': True}
                }))
                
                print(f"Found {len(expiring_soon)} expiring soon, {len(expired)} expired items")
                
                # Send notifications for expiring items
                for item in expiring_soon:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        try:
                            send_expiry_alert(user['email'], item, 'expiring')
                            pantry_items_collection.update_one(
                                {'_id': item['_id']},
                                {'$set': {'notification_sent': True}}
                            )
                            print(f"✅ Sent expiring notification for {item['name']} to {user['email']}")
                        except Exception as e:
                            print(f"❌ Failed to send expiring notification: {e}")
                
                # Send notifications for expired items
                for item in expired:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        try:
                            send_expiry_alert(user['email'], item, 'expired')
                            pantry_items_collection.update_one(
                                {'_id': item['_id']},
                                {'$set': {'notification_sent': True}}
                            )
                            print(f"✅ Sent expired notification for {item['name']} to {user['email']}")
                        except Exception as e:
                            print(f"❌ Failed to send expired notification: {e}")
                
                # Check for low stock items (quantity <= 2)
                low_stock = list(pantry_items_collection.find({
                    'quantity': {'$lte': 2, '$gt': 0},
                    'low_stock_notified': {'$ne': True}
                }))
                
                print(f"Found {len(low_stock)} low stock items")
                
                for item in low_stock:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        try:
                            send_low_stock_alert(user['email'], item)
                            pantry_items_collection.update_one(
                                {'_id': item['_id']},
                                {'$set': {'low_stock_notified': True}}
                            )
                            print(f"✅ Sent low stock notification for {item['name']} to {user['email']}")
                        except Exception as e:
                            print(f"❌ Failed to send low stock notification: {e}")
                
            except Exception as e:
                print(f"Error in notification thread: {e}")
            
            # Sleep for 1 hour before next check
            print("😴 Notification thread sleeping for 1 hour...")
            time.sleep(3600)

# Start background thread for notifications
notification_thread = threading.Thread(target=check_expiry_notifications, daemon=True)
notification_thread.start()
print("✅ Notification service started!")

# Serve HTML files from frontend folder
@app.route('/')
def serve_entry():
    return send_from_directory(frontend_dir, 'Entry.html')

@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path):
        return send_from_directory(frontend_dir, path)
    return "File not found", 404

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

# Smart Timing Routes
@app.route('/api/smart-timing/check-alerts', methods=['GET'])
@jwt_required()
def check_alerts_timing():
    """Check if current time is optimal for sending alerts"""
    current_hour = datetime.now().hour
    
    # Morning alerts (8 AM)
    if 8 <= current_hour <= 9:
        return jsonify({
            'should_send': True, 
            'reason': 'Morning digest time',
            'optimal_time': '8:00 AM'
        }), 200
    # Evening alerts (6 PM)
    elif 18 <= current_hour <= 19:
        return jsonify({
            'should_send': True, 
            'reason': 'Evening reminder time',
            'optimal_time': '6:00 PM'
        }), 200
    else:
        return jsonify({
            'should_send': False, 
            'reason': 'Not optimal time',
            'optimal_times': ['8:00 AM', '6:00 PM']
        }), 200

@app.route('/api/smart-timing/near-store', methods=['POST'])
@jwt_required()
def location_based_alerts():
    """Simulate location-based alerts"""
    try:
        data = request.json
        user_location = data.get('location', 'unknown')
        
        # This would integrate with maps API in production
        nearby_stores = [
            {'name': 'Walmart', 'distance': 0.5, 'address': '123 Main St'},
            {'name': 'Target', 'distance': 1.2, 'address': '456 Oak Ave'},
            {'name': 'Whole Foods', 'distance': 2.0, 'address': '789 Pine Rd'}
        ]
        
        # Filter stores within 1 mile
        nearby = [store for store in nearby_stores if store['distance'] < 1.0]
        
        # Get user's shopping list items
        user_id = get_jwt_identity()
        shopping_items = list(pantry_items_collection.find({
            'user_id': ObjectId(user_id),
            '$or': [
                {'quantity': 0},
                {'quantity': {'$lte': 2}},
                {'expiry_date': {'$lt': datetime.utcnow()}}
            ],
            'status': 'active'
        }).limit(5))
        
        shopping_list = [{
            'name': item['name'],
            'quantity': item['quantity'],
            'reason': 'Expired' if item.get('expiry_date') and item['expiry_date'] < datetime.utcnow() else 'Low Stock'
        } for item in shopping_items]
        
        if nearby and shopping_list:
            return jsonify({
                'message': f"You're near {nearby[0]['name']}! You need {len(shopping_list)} items.",
                'stores': nearby,
                'shopping_items': shopping_list,
                'should_notify': True
            }), 200
        else:
            return jsonify({
                'message': 'No nearby stores or shopping needed',
                'stores': nearby,
                'shopping_items': [],
                'should_notify': False
            }), 200
            
    except Exception as e:
        print(f"Location alert error: {e}")
        return jsonify({'message': 'Error checking nearby stores'}), 500

@app.route('/api/smart-timing/weekly-digest', methods=['GET'])
@jwt_required()
def weekly_digest():
    """Generate weekly digest of expiring items"""
    try:
        user_id = get_jwt_identity()
        profile_id = request.args.get('profile_id')
        
        # Get items expiring in next 7 days
        now = datetime.utcnow()
        week_later = now + timedelta(days=7)
        
        query = {
            'user_id': ObjectId(user_id),
            'expiry_date': {'$gte': now, '$lte': week_later},
            'status': 'active'
        }
        
        if profile_id:
            query['profile_id'] = profile_id
        
        expiring_items = list(pantry_items_collection.find(query))
        
        digest = {
            'total_expiring': len(expiring_items),
            'items': []
        }
        
        for item in expiring_items:
            days_left = (item['expiry_date'] - now).days
            digest['items'].append({
                'name': item['name'],
                'quantity': item['quantity'],
                'expires_in': days_left,
                'profile': item.get('profile_id', 'Unknown'),
                'storage': item.get('storage_type', 'Unknown')
            })
        
        # Sort by days left (soonest first)
        digest['items'].sort(key=lambda x: x['expires_in'])
        
        # Add summary statistics
        digest['urgent'] = len([i for i in digest['items'] if i['expires_in'] <= 2])
        digest['soon'] = len([i for i in digest['items'] if 2 < i['expires_in'] <= 5])
        digest['later'] = len([i for i in digest['items'] if i['expires_in'] > 5])
        
        return jsonify(digest), 200
        
    except Exception as e:
        print(f"Weekly digest error: {e}")
        return jsonify({'message': 'Error generating digest'}), 500

@app.route('/api/smart-timing/update-preferences', methods=['POST'])
@jwt_required()
def update_notification_preferences():
    """Update user notification preferences"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        preferences = {
            'morning_digest': data.get('morning_digest', True),
            'evening_reminders': data.get('evening_reminders', True),
            'weekly_report': data.get('weekly_report', True),
            'location_alerts': data.get('location_alerts', False),
            'preferred_time_morning': data.get('preferred_time_morning', '08:00'),
            'preferred_time_evening': data.get('preferred_time_evening', '18:00')
        }
        
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'notification_preferences': preferences}}
        )
        
        return jsonify({
            'message': 'Preferences updated successfully',
            'preferences': preferences
        }), 200
        
    except Exception as e:
        print(f"Update preferences error: {e}")
        return jsonify({'message': 'Error updating preferences'}), 500

# Test endpoint to manually trigger notifications
@app.route('/api/test/check-expiry')
def force_expiry_check():
    try:
        # Run the check in a separate thread with app context
        def run_check():
            with app.app_context():
                # Call the check function directly
                now = datetime.utcnow()
                
                # Find items expiring in next 3 days
                expiring_soon = list(pantry_items_collection.find({
                    'expiry_date': {
                        '$gte': now,
                        '$lte': now + timedelta(days=3)
                    },
                    'notification_sent': {'$ne': True}
                }))
                
                # Find expired items
                expired = list(pantry_items_collection.find({
                    'expiry_date': {'$lt': now},
                    'notification_sent': {'$ne': True}
                }))
                
                # Send notifications for expiring items
                for item in expiring_soon:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        send_expiry_alert(user['email'], item, 'expiring')
                        pantry_items_collection.update_one(
                            {'_id': item['_id']},
                            {'$set': {'notification_sent': True}}
                        )
                
                # Send notifications for expired items
                for item in expired:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        send_expiry_alert(user['email'], item, 'expired')
                        pantry_items_collection.update_one(
                            {'_id': item['_id']},
                            {'$set': {'notification_sent': True}}
                        )
                
                # Check for low stock items
                low_stock = list(pantry_items_collection.find({
                    'quantity': {'$lte': 2, '$gt': 0},
                    'low_stock_notified': {'$ne': True}
                }))
                
                for item in low_stock:
                    user = users_collection.find_one({'_id': item['user_id']})
                    if user and user.get('email'):
                        send_low_stock_alert(user['email'], item)
                        pantry_items_collection.update_one(
                            {'_id': item['_id']},
                            {'$set': {'low_stock_notified': True}}
                        )
        
        thread = threading.Thread(target=run_check)
        thread.start()
        return jsonify({'message': 'Expiry check triggered in background'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Test endpoint to check email configuration
@app.route('/api/test/email')
def test_email():
    """Test endpoint to verify email configuration"""
    try:
        # Create a test item
        test_item = {
            'name': 'Test Item',
            'quantity': 1,
            'expiry_date': datetime.now(),
            'profile_id': 'test'
        }
        
        # Send test email to yourself
        result = send_expiry_alert(app.config['MAIL_USERNAME'], test_item, 'expiring')
        
        if result:
            return jsonify({'message': 'Test email sent successfully! Check your inbox.'}), 200
        else:
            return jsonify({'error': 'Failed to send test email. Check your email configuration.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to get notification status
@app.route('/api/notifications/status', methods=['GET'])
@jwt_required()
def notification_status():
    """Get notification status for current user"""
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        preferences = user.get('notification_preferences', {
            'morning_digest': True,
            'evening_reminders': True,
            'weekly_report': True,
            'location_alerts': False,
            'preferred_time_morning': '08:00',
            'preferred_time_evening': '18:00'
        })
        
        # Get today's notification count
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        notifications_sent = pantry_items_collection.count_documents({
            'user_id': ObjectId(user_id),
            'updated_at': {'$gte': today_start},
            '$or': [
                {'notification_sent': True},
                {'low_stock_notified': True}
            ]
        })
        
        return jsonify({
            'preferences': preferences,
            'notifications_today': notifications_sent,
            'email_configured': bool(app.config.get('MAIL_USERNAME'))
        }), 200
        
    except Exception as e:
        print(f"Notification status error: {e}")
        return jsonify({'message': 'Error getting notification status'}), 500

# Endpoint to manually trigger digest
@app.route('/api/notifications/send-digest', methods=['POST'])
@jwt_required()
def send_digest_now():
    """Manually trigger digest email"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        digest_type = data.get('type', 'morning')  # morning, evening, or weekly
        
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user or not user.get('email'):
            return jsonify({'message': 'No email address found'}), 400
        
        # Get relevant items
        now = datetime.utcnow()
        
        if digest_type == 'morning':
            # Get expiring items
            items = list(pantry_items_collection.find({
                'user_id': ObjectId(user_id),
                'expiry_date': {'$lte': now + timedelta(days=3), '$gt': now},
                'status': 'active'
            }))
            
        elif digest_type == 'evening':
            # Get low stock items
            items = list(pantry_items_collection.find({
                'user_id': ObjectId(user_id),
                'quantity': {'$lte': 2, '$gt': 0},
                'status': 'active'
            }))
            
        else:  # weekly
            # Get weekly stats
            items = list(pantry_items_collection.find({
                'user_id': ObjectId(user_id),
                'status': 'active'
            }))
        
        # Send email
        if items:
            return jsonify({
                'message': f'Digest would be sent with {len(items)} items',
                'type': digest_type,
                'items': [{'name': i['name'], 'quantity': i['quantity']} for i in items[:5]]
            }), 200
        else:
            return jsonify({'message': 'No items to notify'}), 200
            
    except Exception as e:
        print(f"Send digest error: {e}")
        return jsonify({'message': 'Error sending digest'}), 500

if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        host=Config.HOST,
        port=Config.PORT
    )