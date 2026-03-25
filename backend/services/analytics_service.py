# services/analytics_service.py
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from bson import ObjectId
from database import pantry_items_collection
import joblib
import os

class PantryAnalytics:
    def __init__(self):
        self.model = None
        self.model_path = 'models/expiry_predictor.pkl'
        
    def prepare_training_data(self, user_id):
        """Prepare data for training from user's pantry history"""
        items = list(pantry_items_collection.find({
            'user_id': ObjectId(user_id),
            'status': 'active'
        }))
        
        if len(items) < 10:
            return None, None  # Not enough data
        
        # Create features dataframe
        data = []
        for item in items:
            if item.get('expiry_date'):
                # Features
                days_since_added = (datetime.utcnow() - item['created_at']).days
                quantity = item['quantity']
                
                # Target: actual days until expiry
                days_to_expiry = (item['expiry_date'] - datetime.utcnow()).days if item['expiry_date'] > datetime.utcnow() else 0
                
                # Categorical encoding for item type (simplified)
                item_type = self.categorize_item(item['name'])
                
                data.append({
                    'days_since_added': days_since_added,
                    'quantity': quantity,
                    'item_type': item_type,
                    'days_to_expiry': days_to_expiry
                })
        
        if not data:
            return None, None
            
        df = pd.DataFrame(data)
        
        # One-hot encode item type
        df = pd.get_dummies(df, columns=['item_type'])
        
        X = df.drop('days_to_expiry', axis=1)
        y = df['days_to_expiry']
        
        return X, y
    
    def categorize_item(self, item_name):
        """Categorize item based on name"""
        item_name = item_name.lower()
        
        categories = {
            'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream'],
            'meat': ['chicken', 'beef', 'pork', 'fish', 'meat', 'steak'],
            'vegetables': ['lettuce', 'tomato', 'cucumber', 'carrot', 'broccoli', 'spinach'],
            'fruits': ['apple', 'banana', 'orange', 'grape', 'berry', 'fruit'],
            'frozen': ['frozen', 'ice cream', 'pizza'],
            'canned': ['can', 'canned', 'jar', 'soup'],
            'dry': ['rice', 'pasta', 'flour', 'sugar', 'cereal']
        }
        
        for category, keywords in categories.items():
            if any(keyword in item_name for keyword in keywords):
                return category
        
        return 'other'
    
    def train_model(self, user_id):
        """Train ML model for expiry prediction"""
        X, y = self.prepare_training_data(user_id)
        
        if X is None or len(X) < 10:
            return False, "Not enough data to train model (need at least 10 items)"
        
        # Train Random Forest model
        self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.model.fit(X, y)
        
        # Save model
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, f'models/model_{user_id}.pkl')
        
        # Calculate accuracy
        predictions = self.model.predict(X)
        accuracy = np.mean(np.abs(predictions - y) < 3)  # Within 3 days accuracy
        
        return True, {
            'accuracy': float(accuracy),
            'samples': len(y),
            'message': f'Model trained with {len(y)} items. Accuracy: {accuracy:.2%}'
        }
    
    def predict_expiry(self, user_id, item_name, quantity, storage_type):
        """Predict when an item will expire"""
        try:
            # Try to load existing model
            model_path = f'models/model_{user_id}.pkl'
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
            else:
                return None, "Model not trained yet"
            
            # Prepare features
            item_type = self.categorize_item(item_name)
            
            # Create feature vector with all possible one-hot encoded columns
            feature_dict = {
                'days_since_added': 0,
                'quantity': quantity
            }
            
            # Add one-hot encoded item type (assuming all possible types)
            all_types = ['dairy', 'meat', 'vegetables', 'fruits', 'frozen', 'canned', 'dry', 'other']
            for t in all_types:
                feature_dict[f'item_type_{t}'] = 1 if t == item_type else 0
            
            # Create dataframe with correct column order
            df = pd.DataFrame([feature_dict])
            
            # Ensure columns match training data
            expected_columns = self.model.feature_names_in_
            df = df.reindex(columns=expected_columns, fill_value=0)
            
            # Predict
            predicted_days = int(self.model.predict(df)[0])
            
            # Ensure prediction is reasonable
            predicted_days = max(1, min(predicted_days, 90))  # Between 1 and 90 days
            
            return predicted_days, None
            
        except Exception as e:
            return None, str(e)
    
    def suggest_purchase_quantity(self, user_id, item_name, consumption_rate=None):
        """Suggest optimal purchase quantity based on consumption patterns"""
        items = list(pantry_items_collection.find({
            'user_id': ObjectId(user_id),
            'name': {'$regex': item_name, '$options': 'i'},
            'status': 'active'
        }))
        
        if len(items) < 3:
            # Default suggestion based on item type
            item_type = self.categorize_item(item_name)
            defaults = {
                'dairy': 2,
                'meat': 3,
                'vegetables': 4,
                'fruits': 5,
                'frozen': 3,
                'canned': 4,
                'dry': 2,
                'other': 3
            }
            return defaults.get(item_type, 3), "Based on general recommendations"
        
        # Calculate average consumption rate
        total_consumed = 0
        total_days = 0
        
        for item in items:
            if item.get('expiry_date'):
                days_until_expiry = (item['expiry_date'] - item['created_at']).days
                if days_until_expiry > 0:
                    consumption_rate = item['quantity'] / days_until_expiry
                    total_consumed += consumption_rate
                    total_days += 1
        
        if total_days > 0:
            avg_consumption = total_consumed / total_days
            suggested_qty = int(avg_consumption * 7)  # Weekly consumption
            return max(1, min(suggested_qty, 10)), f"Based on your consumption: {avg_consumption:.2f} units/day"
        
        return 3, "Based on average recommendation"
    
    def get_consumption_patterns(self, user_id, profile_id=None):
        """Analyze consumption patterns over time"""
        query = {'user_id': ObjectId(user_id), 'status': 'active'}
        if profile_id:
            query['profile_id'] = profile_id
        
        items = list(pantry_items_collection.find(query))
        
        if not items:
            return None
        
        # Group by category
        categories = {}
        for item in items:
            category = self.categorize_item(item['name'])
            if category not in categories:
                categories[category] = {
                    'total_quantity': 0,
                    'items_count': 0,
                    'expired_count': 0
                }
            
            categories[category]['total_quantity'] += item['quantity']
            categories[category]['items_count'] += 1
            
            if item.get('expiry_date') and item['expiry_date'] < datetime.utcnow():
                categories[category]['expired_count'] += 1
        
        # Calculate waste rates
        for category in categories:
            if categories[category]['items_count'] > 0:
                categories[category]['waste_rate'] = categories[category]['expired_count'] / categories[category]['items_count']
            else:
                categories[category]['waste_rate'] = 0
        
        return categories

# Initialize analytics service
analytics = PantryAnalytics()