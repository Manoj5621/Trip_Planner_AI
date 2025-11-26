"""
MongoDB Adapter Layer
Provides a bridge between Django ORM and MongoDB for the Trip Planner app.
This allows the existing Django code to work with MongoDB without major changes.
"""

from django.conf import settings
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import json

class MongoDBAdapter:
    """
    Adapter class to handle MongoDB operations while keeping Django code unchanged.
    This translates between Django ORM and MongoDB operations.
    """
    
    def __init__(self):
        self.client = settings.MONGO_CLIENT
        self.db = settings.MONGO_DB
        
    def connect(self):
        """Verify MongoDB connection."""
        if self.client is None or self.db is None:
            raise ConnectionError("MongoDB connection not configured. Check MONGO_URI in .env")
        try:
            self.client.server_info()
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
    
    def create_collections(self):
        """Create MongoDB collections with appropriate indexes."""
        if self.db is None:
            raise ConnectionError("MongoDB not configured")
        
        # Create User collection with indexes
        if 'auth_user' not in self.db.list_collection_names():
            self.db.create_collection('auth_user')
            self.db['auth_user'].create_index('email', unique=True)
        
        # Create Trip collection
        if 'trips_trip' not in self.db.list_collection_names():
            self.db.create_collection('trips_trip')
            self.db['trips_trip'].create_index('user_id')
            self.db['trips_trip'].create_index('is_posted')
        
        # Create Rating collection
        if 'trips_rating' not in self.db.list_collection_names():
            self.db.create_collection('trips_rating')
            self.db['trips_rating'].create_index([('trip_id', 1), ('user_id', 1)], unique=True)
        
        # Create Profile collection
        if 'trips_profile' not in self.db.list_collection_names():
            self.db.create_collection('trips_profile')
            self.db['trips_profile'].create_index('user_id', unique=True)
    
    def insert_user(self, email, password_hash, first_name='', last_name='', **kwargs):
        """Insert a new user into MongoDB."""
        user_doc = {
            'email': email,
            'password': password_hash,
            'first_name': first_name,
            'last_name': last_name,
            'is_active': kwargs.get('is_active', True),
            'is_staff': kwargs.get('is_staff', False),
            'is_superuser': kwargs.get('is_superuser', False),
            'date_joined': datetime.utcnow(),
            'last_login': None,
        }
        result = self.db['auth_user'].insert_one(user_doc)
        return str(result.inserted_id)
    
    def find_user_by_email(self, email):
        """Find user by email."""
        return self.db['auth_user'].find_one({'email': email})
    
    def find_user_by_id(self, user_id):
        """Find user by ID."""
        try:
            return self.db['auth_user'].find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    def insert_trip(self, user_id, destination, start_location, start_date, end_date,
                   interested_activities, trip_type, number_of_people, **kwargs):
        """Insert a new trip into MongoDB."""
        trip_doc = {
            'user_id': ObjectId(user_id),
            'destination': destination,
            'start_location': start_location,
            'start_date': start_date,
            'end_date': end_date,
            'interested_activities': interested_activities,
            'trip_type': trip_type,
            'number_of_people': number_of_people,
            'trip_plan': kwargs.get('trip_plan'),
            'is_saved': kwargs.get('is_saved', False),
            'is_posted': kwargs.get('is_posted', False),
            'posted_at': kwargs.get('posted_at'),
            'created_at': datetime.utcnow(),
        }
        result = self.db['trips_trip'].insert_one(trip_doc)
        return str(result.inserted_id)
    
    def find_trips_by_user(self, user_id):
        """Find all trips by user."""
        try:
            return list(self.db['trips_trip'].find({'user_id': ObjectId(user_id)}))
        except:
            return []
    
    def find_trip_by_id(self, trip_id):
        """Find trip by ID."""
        try:
            return self.db['trips_trip'].find_one({'_id': ObjectId(trip_id)})
        except:
            return None
    
    def update_trip(self, trip_id, **updates):
        """Update trip document."""
        try:
            result = self.db['trips_trip'].update_one(
                {'_id': ObjectId(trip_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except:
            return False
    
    def insert_rating(self, trip_id, user_id, rating, comment=''):
        """Insert a rating into MongoDB."""
        rating_doc = {
            'trip_id': ObjectId(trip_id),
            'user_id': ObjectId(user_id),
            'rating': rating,
            'comment': comment,
            'created_at': datetime.utcnow(),
        }
        result = self.db['trips_rating'].insert_one(rating_doc)
        return str(result.inserted_id)
    
    def find_ratings_by_trip(self, trip_id):
        """Find all ratings for a trip."""
        try:
            return list(self.db['trips_rating'].find({'trip_id': ObjectId(trip_id)}))
        except:
            return []
    
    def insert_profile(self, user_id, **kwargs):
        """Insert user profile into MongoDB."""
        profile_doc = {
            'user_id': ObjectId(user_id),
            'avatar': kwargs.get('avatar'),
            'bio': kwargs.get('bio', ''),
            'location': kwargs.get('location', ''),
            'birth_date': kwargs.get('birth_date'),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        result = self.db['trips_profile'].insert_one(profile_doc)
        return str(result.inserted_id)
    
    def find_profile_by_user(self, user_id):
        """Find profile by user ID."""
        try:
            return self.db['trips_profile'].find_one({'user_id': ObjectId(user_id)})
        except:
            return None
    
    def update_profile(self, user_id, **updates):
        """Update user profile."""
        try:
            updates['updated_at'] = datetime.utcnow()
            result = self.db['trips_profile'].update_one(
                {'user_id': ObjectId(user_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except:
            return False


# Global MongoDB adapter instance
mongo_adapter = MongoDBAdapter() if settings.MONGO_DB is not None else None
