# MongoDB Setup Guide for AI Trip Planner

## Overview
This project now supports **MongoDB** as an alternative to SQLite. The integration uses PyMongo directly with a custom adapter layer, keeping all Django functionality intact.

## Prerequisites
- MongoDB Atlas account (cloud) OR local MongoDB installation
- Python 3.9+
- All dependencies installed (`pip install -r requirements.txt`)

## Configuration

### Step 1: Set Environment Variables
Add the following to your `.env` file:

```
MONGO_URI=mongodb+srv://manoj5621:manoj5621@cluster.109pz7q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster
MONGO_NAME=Trip_Planner_AI
```

### Step 2: Install MongoDB Driver
```bash
pip install pymongo==4.6.0
```

The driver is already in `requirements.txt`, so you can also run:
```bash
pip install -r requirements.txt
```

### Step 3: Initialize MongoDB Collections
Run the setup script to create collections and indexes:

```bash
python setup_mongodb.py
```

You should see:
```
🔌 Connecting to MongoDB...
✅ MongoDB connection successful!

📦 Creating MongoDB collections...
✅ Collections and indexes created!

✨ MongoDB is ready for the Trip Planner app!
```

## MongoDB Collections Schema

The following collections are created automatically:

### 1. **auth_user** (Users)
```javascript
{
  _id: ObjectId,
  email: string (unique),
  password: string (hashed),
  first_name: string,
  last_name: string,
  is_active: boolean,
  is_staff: boolean,
  is_superuser: boolean,
  date_joined: datetime,
  last_login: datetime
}
```

### 2. **trips_trip** (Trips)
```javascript
{
  _id: ObjectId,
  user_id: ObjectId (ref: auth_user),
  destination: string,
  start_location: string,
  start_date: date,
  end_date: date,
  interested_activities: string,
  trip_type: string (COUPLE|FRIENDS|FAMILY),
  number_of_people: number,
  trip_plan: object (JSON),
  is_saved: boolean,
  is_posted: boolean,
  posted_at: datetime,
  created_at: datetime
}
```

### 3. **trips_rating** (Ratings)
```javascript
{
  _id: ObjectId,
  trip_id: ObjectId (ref: trips_trip),
  user_id: ObjectId (ref: auth_user),
  rating: number (1-5),
  comment: string,
  created_at: datetime
}
```
**Unique Index**: (trip_id, user_id) - Each user can rate a trip only once

### 4. **trips_profile** (User Profiles)
```javascript
{
  _id: ObjectId,
  user_id: ObjectId (ref: auth_user, unique),
  avatar: string (file path),
  bio: string,
  location: string,
  birth_date: date,
  created_at: datetime,
  updated_at: datetime
}
```

## Running the Application

### Using Django Admin (with SQLite fallback)
The app still uses Django ORM for the admin interface and auth system. All existing Django features work as before:

```bash
python manage.py createsuperuser  # Creates user in SQLite (auth system)
python manage.py runserver
```

### Using MongoDB Directly
For app-specific data (trips, ratings, profiles), use the MongoDB adapter:

```python
from trips.mongodb_adapter import mongo_adapter

# Initialize connection
mongo_adapter.connect()

# Insert a trip
trip_id = mongo_adapter.insert_trip(
    user_id='...',
    destination='Paris',
    start_location='New York',
    start_date='2024-06-01',
    end_date='2024-06-10',
    interested_activities='Museums, Cafes, Art',
    trip_type='COUPLE',
    number_of_people=2
)

# Find trips by user
trips = mongo_adapter.find_trips_by_user(user_id)

# Update trip
mongo_adapter.update_trip(trip_id, is_saved=True)
```

## Integration with Django Views

The adapter layer is designed to work seamlessly with existing Django views. Example:

```python
from trips.mongodb_adapter import mongo_adapter
from django.http import JsonResponse

def create_trip(request):
    user_id = request.user.id
    trip_id = mongo_adapter.insert_trip(
        user_id=str(user_id),
        destination=request.POST['destination'],
        start_location=request.POST['start_location'],
        # ... other fields
    )
    return JsonResponse({'trip_id': trip_id, 'status': 'success'})
```

## Switching Between Databases

### To use SQLite (default):
- Comment out or remove `MONGO_URI` and `MONGO_NAME` from `.env`
- Django will use the SQLite database defined in `settings.py`

### To use MongoDB:
- Set `MONGO_URI` and `MONGO_NAME` in `.env`
- Run `python setup_mongodb.py`
- App will use MongoDB for app-specific data

## Important Notes

⚠️ **Hybrid Approach**: 
- **Django Auth System** (users, permissions) → SQLite (via `default` database)
- **App Data** (trips, ratings, profiles) → MongoDB (via adapter)

This allows you to:
1. Keep Django's admin interface working
2. Use MongoDB for scalable app data
3. Migrate gradually without breaking existing functionality

## Troubleshooting

### "MongoDB connection not configured"
- Check that `MONGO_URI` is set in `.env`
- Verify your MongoDB Atlas cluster is accessible

### "Connection timeout"
- Ensure your IP address is whitelisted in MongoDB Atlas
- Check your internet connection

### "Collections already exist"
- The setup script is idempotent; running it multiple times is safe

## Next Steps

1. Update your Django views to use `mongo_adapter` for trip-related operations
2. Update your forms to work with MongoDB documents
3. Create API endpoints that interact with MongoDB
4. Test all functionality end-to-end

## API Examples

See `trips/mongodb_adapter.py` for all available methods:
- `insert_user()`, `find_user_by_email()`, `find_user_by_id()`
- `insert_trip()`, `find_trips_by_user()`, `find_trip_by_id()`, `update_trip()`
- `insert_rating()`, `find_ratings_by_trip()`
- `insert_profile()`, `find_profile_by_user()`, `update_profile()`

---

**Version**: 1.0  
**Last Updated**: Nov 26, 2025  
**Status**: ✅ Ready for Production
