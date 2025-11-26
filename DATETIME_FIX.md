# MongoDB DateTime Serialization Fix

## Issue
MongoDB's JSON encoder cannot serialize Python native `datetime.date` and `datetime.datetime` objects, causing errors like:
```
Error saving trip: cannot encode object: datetime.date(2025, 11, 26), of type: <class 'datetime.date'>
```

This error occurred when the Trip and Profile models tried to save data to MongoDB.

## Solution
Converted all datetime fields to ISO 8601 format strings before storing in MongoDB.

### Changes Made

#### 1. Trip Model (`trips/models.py`)
Modified the `save()` method to convert datetime fields to ISO strings:
```python
'start_date': self.start_date.isoformat() if self.start_date else None,
'end_date': self.end_date.isoformat() if self.end_date else None,
'posted_at': self.posted_at.isoformat() if self.posted_at else None,
'created_at': self.created_at.isoformat() if self.created_at else None,
```

#### 2. Profile Model (`trips/models.py`)
Modified the `save()` method to convert datetime fields to ISO strings:
```python
'birth_date': self.birth_date.isoformat() if self.birth_date else None,
'created_at': self.created_at.isoformat() if self.created_at else None,
'updated_at': self.updated_at.isoformat() if self.updated_at else None,
```

#### 3. Django Settings (`trip_planner/settings.py`)
Updated allauth configuration to use recommended settings:
- Changed from deprecated `ACCOUNT_AUTHENTICATION_METHOD = 'email'`
- To new `ACCOUNT_LOGIN_METHODS = {'email'}`
- Removed unused `ACCOUNT_USER_MODEL_USERNAME_FIELD` and `ACCOUNT_SIGNUP_FIELDS`

## Testing
Created `test_mongodb_datetime.py` to verify:
- ✅ MongoDB connection works
- ✅ Date/datetime objects convert to ISO strings correctly
- ✅ Trip model saves with datetime fields to MongoDB without errors
- ✅ Date fields are stored as strings in MongoDB

## Verification
Run: `python test_mongodb_datetime.py`

Expected output:
```
Testing MongoDB datetime serialization...
============================================================
✅ MongoDB connected
Date/Datetime ISO conversion test:
  date object: 2025-11-26 -> ISO: 2025-11-26
  datetime object: 2025-11-26 12:30:45 -> ISO: 2025-11-26T12:30:45
...
✅ Trip created and synced: Test Destination
✅ Found in MongoDB: Test Destination
   start_date type: <class 'str'> = 2025-11-26
   end_date type: <class 'str'> = 2025-11-30
```

## Impact
- ✅ No breaking changes to Django ORM or SQLite functionality
- ✅ All datetime data properly stored in both SQLite and MongoDB
- ✅ MongoDB data is queryable with string date comparisons
- ✅ All model saves now sync successfully to MongoDB

## Migration Notes
- Existing data in SQLite remains unchanged
- Existing data in MongoDB may have datetime objects from before this fix - consider migration if needed
- New saves will use ISO string format automatically
