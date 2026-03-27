from flask import Blueprint, request, jsonify
from database import users_collection, otp_collection, profiles_collection
from services.email_service import send_otp_email
import random
import string
import re
from datetime import datetime, timedelta
import bcrypt
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'message': 'All fields are required'}), 400
        
        if len(username) < 3:
            return jsonify({'message': 'Username must be at least 3 characters'}), 400
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({'message': 'Username can only contain letters, numbers, and underscores'}), 400
        
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return jsonify({'message': 'Please enter a valid email address'}), 400
        
        if len(password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters'}), 400
        
        existing_user = users_collection.find_one({
            '$or': [
                {'username': username},
                {'email': email}
            ]
        })
        
        if existing_user:
            if existing_user.get('username') == username:
                return jsonify({'message': 'Username already exists! Please login.'}), 409
            else:
                return jsonify({'message': 'Email already registered! Please login.'}), 409
        
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        new_user = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'preferences': {
                'notifications': True,
                'expiry_alert_days': 3
            }
        }
        
        result = users_collection.insert_one(new_user)
        
        default_profiles = [
            {'profile_name': 'home', 'display_name': 'Home Pantry', 'emoji': '🏠'},
            {'profile_name': 'office', 'display_name': 'Office Pantry', 'emoji': '🏢'},
            {'profile_name': 'factory', 'display_name': 'Factory Pantry', 'emoji': '🏭'},
            {'profile_name': 'lab', 'display_name': 'R&D Kitchen', 'emoji': '🍙'},
            {'profile_name': 'test', 'display_name': 'Test Lab', 'emoji': '🧆'}
        ]
        
        for profile in default_profiles:
            profiles_collection.insert_one({
                'user_id': result.inserted_id,
                'profile_name': profile['profile_name'],
                'display_name': profile['display_name'],
                'emoji': profile['emoji'],
                'created_at': datetime.utcnow()
            })
        
        return jsonify({
            'message': 'Registration successful! Please login.',
            'user_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'message': 'Server error during registration'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Username and password required'}), 400
        
        user = users_collection.find_one({'username': username})
        
        if not user:
            return jsonify({'message': 'Invalid username or password'}), 401
        
        stored_hash = user.get('password')
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            token = create_access_token(identity=str(user['_id']))
            
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user.get('email', '')
            }), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'Server error during login'}), 500

@auth_bp.route('/forgot-password/send-otp', methods=['POST'])
def send_otp():
    """Send OTP for password reset"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'message': 'Email required'}), 400
        
        user = users_collection.find_one({'email': email})
        if not user:
            return jsonify({'message': 'Email not registered'}), 404
        
        otp_collection.delete_many({'email': email})
        
        otp = ''.join(random.choices(string.digits, k=6))
        
        otp_data = {
            'email': email,
            'otp': otp,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'attempts': 0,
            'verified': False
        }
        otp_collection.insert_one(otp_data)
        
        if send_otp_email(email, otp):
            return jsonify({
                'message': 'OTP sent successfully',
                'email': email
            }), 200
        else:
            return jsonify({'message': 'Failed to send OTP. Check email configuration.'}), 500
            
    except Exception as e:
        print(f"Send OTP error: {e}")
        return jsonify({'message': 'Server error'}), 500

@auth_bp.route('/forgot-password/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP"""
    try:
        data = request.json
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'message': 'Email and OTP required'}), 400
        
        otp_record = otp_collection.find_one({
            'email': email,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        
        if not otp_record:
            return jsonify({'message': 'No valid OTP found. Please request again.'}), 400
        
        if otp_record.get('attempts', 0) >= 3:
            otp_collection.delete_one({'_id': otp_record['_id']})
            return jsonify({'message': 'Too many failed attempts. Please request new OTP.'}), 400
        
        if otp_record['otp'] != otp:
            otp_collection.update_one(
                {'_id': otp_record['_id']},
                {'$inc': {'attempts': 1}}
            )
            remaining = 3 - (otp_record.get('attempts', 0) + 1)
            return jsonify({
                'message': f'Invalid OTP. {remaining} attempts remaining.'
            }), 400
        
        otp_collection.update_one(
            {'_id': otp_record['_id']},
            {'$set': {'verified': True}}
        )
        
        return jsonify({'message': 'OTP verified successfully'}), 200
            
    except Exception as e:
        print(f"Verify OTP error: {e}")
        return jsonify({'message': 'Server error'}), 500

@auth_bp.route('/forgot-password/reset', methods=['POST'])
def reset_password():
    """Reset password after OTP verification"""
    try:
        data = request.json
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')
        
        if not email or not otp or not new_password:
            return jsonify({'message': 'All fields required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters'}), 400
        
        otp_record = otp_collection.find_one({
            'email': email,
            'otp': otp,
            'expires_at': {'$gt': datetime.utcnow()},
            'verified': True
        })
        
        if not otp_record:
            return jsonify({'message': 'Invalid or unverified OTP'}), 400
        
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
        
        result = users_collection.update_one(
            {'email': email},
            {'$set': {
                'password': hashed_password,
                'updated_at': datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            return jsonify({'message': 'User not found'}), 404
        
        otp_collection.delete_many({'email': email})
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'message': 'Server error'}), 500

@auth_bp.route('/recover-username', methods=['POST'])
def recover_username():
    """Recover username by email"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'message': 'Email required'}), 400
        
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return jsonify({'message': 'Please enter a valid email address'}), 400
        
        user = users_collection.find_one({'email': email})
        
        if not user:
            return jsonify({'message': 'Email not registered'}), 404
        
        return jsonify({
            'message': 'Username found',
            'username': user.get('username'),
            'email': email
        }), 200
        
    except Exception as e:
        print(f"Recover username error: {e}")
        return jsonify({'message': 'Server error'}), 500

@auth_bp.route('/update-username', methods=['PUT'])
def update_username():
    """Update username for a user"""
    try:
        data = request.json
        email = data.get('email')
        new_username = data.get('new_username')
        
        if not email or not new_username:
            return jsonify({'message': 'Email and new username required'}), 400
        
        if len(new_username) < 3:
            return jsonify({'message': 'Username must be at least 3 characters'}), 400
        
        if len(new_username) > 30:
            return jsonify({'message': 'Username must be less than 30 characters'}), 400
        
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            return jsonify({'message': 'Username can only contain letters, numbers, and underscores'}), 400
        
        existing_user = users_collection.find_one({'username': new_username})
        if existing_user:
            return jsonify({'message': 'Username already taken. Please choose another.'}), 409
        
        result = users_collection.update_one(
            {'email': email},
            {'$set': {
                'username': new_username,
                'updated_at': datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({'message': 'Username updated successfully'}), 200
        
    except Exception as e:
        print(f"Update username error: {e}")
        return jsonify({'message': 'Server error'}), 500