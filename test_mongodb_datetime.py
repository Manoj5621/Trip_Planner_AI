#!/usr/bin/env python
"""Test MongoDB datetime serialization fix"""
import os
import django
from datetime import date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trip_planner.settings')
django.setup()

from trips.models import Trip, Profile, User
from trips.mongodb_adapter import mongo_adapter

print("Testing MongoDB datetime serialization...")
print("=" * 60)

# Check if MongoDB is connected
if mongo_adapter is None:
    print("❌ MongoDB adapter not initialized")
elif mongo_adapter.db is None:
    print("❌ MongoDB not connected")
else:
    print("✅ MongoDB connected")

# Test date/datetime conversion
test_date = date(2025, 11, 26)
test_datetime = datetime(2025, 11, 26, 12, 30, 45)

print("\nDate/Datetime ISO conversion test:")
print(f"  date object: {test_date} -> ISO: {test_date.isoformat()}")
print(f"  datetime object: {test_datetime} -> ISO: {test_datetime.isoformat()}")

# Test Trip model save with dates
print("\n" + "=" * 60)
print("Testing Trip model save with datetime fields...")

try:
    user = User.objects.first()
    if user:
        trip = Trip.objects.create(
            user=user,
            destination="Test Destination",
            start_location="Test Location",
            start_date=date(2025, 11, 26),
            end_date=date(2025, 11, 30),
            interested_activities="hiking",
            trip_type="Adventure",
            number_of_people=2,
            trip_plan="Test plan",
            is_saved=False,
            is_posted=False,
        )
        print(f"✅ Trip created and synced: {trip.destination}")
        
        # Check MongoDB
        if mongo_adapter:
            mongo_trip = mongo_adapter.db['trips_trip'].find_one({'destination': 'Test Destination'})
            if mongo_trip:
                print(f"✅ Found in MongoDB: {mongo_trip['destination']}")
                print(f"   start_date type: {type(mongo_trip['start_date'])} = {mongo_trip['start_date']}")
                print(f"   end_date type: {type(mongo_trip['end_date'])} = {mongo_trip['end_date']}")
            else:
                print("❌ Not found in MongoDB")
        
        trip.delete()
    else:
        print("⚠️  No users found - skipping Trip test")
except Exception as e:
    print(f"❌ Error testing Trip: {e}")

print("\n" + "=" * 60)
print("Test complete!")
