"""
MongoDB Setup Script
Initializes MongoDB collections and prepares the database for the Trip Planner app.
Run this after configuring MONGO_URI in .env
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trip_planner.settings')
django.setup()

from trips.mongodb_adapter import mongo_adapter

def setup_mongodb():
    """Initialize MongoDB collections and indexes."""
    try:
        if settings.MONGO_DB is None:
            print("⚠️  MongoDB not configured. Check MONGO_URI in .env")
            exit(1)
            
        print("🔌 Connecting to MongoDB...")
        mongo_adapter.connect()
        print("✅ MongoDB connection successful!")
        
        print("\n📦 Creating MongoDB collections...")
        mongo_adapter.create_collections()
        print("✅ Collections and indexes created!")
        
        print("\n✨ MongoDB is ready for the Trip Planner app!")
        print(f"Database: {settings.MONGODB_NAME}")
        print(f"URI: {settings.MONGODB_URI[:50]}..." if settings.MONGODB_URI else "No MongoDB URI")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == '__main__':
    setup_mongodb()
