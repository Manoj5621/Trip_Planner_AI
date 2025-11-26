"""
Custom MongoDB-backed models for Trip Planner.
These models override Django's default behavior to save/read from MongoDB instead of SQLite.
All functionality remains identical to the original models.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver
from bson.objectid import ObjectId
from trips.mongodb_adapter import mongo_adapter
import logging

logger = logging.getLogger(__name__)

class MongoDBManager(models.Manager):
    """Custom manager that redirects saves to MongoDB"""
    
    def create(self, **kwargs):
        """Override create to save to MongoDB"""
        instance = self.model(**kwargs)
        instance.save()
        return instance
    
    def get(self, **kwargs):
        """Override get to read from MongoDB"""
        if mongo_adapter is None:
            return super().get(**kwargs)
        
        # Try to get from MongoDB first
        try:
            mongo_doc = mongo_adapter.db[self.model._meta.db_table].find_one(kwargs)
            if mongo_doc:
                instance = self.model()
                instance._load_from_mongo(mongo_doc)
                return instance
        except:
            pass
        
        return super().get(**kwargs)
    
    def filter(self, **kwargs):
        """Override filter to read from MongoDB"""
        if mongo_adapter is None:
            return super().filter(**kwargs)
        
        try:
            mongo_docs = list(mongo_adapter.db[self.model._meta.db_table].find(kwargs))
            queryset = super().filter(**kwargs)
            if mongo_docs:
                # Load from MongoDB
                instances = []
                for doc in mongo_docs:
                    instance = self.model()
                    instance._load_from_mongo(doc)
                    instances.append(instance)
                return instances
        except:
            pass
        
        return super().filter(**kwargs)


class MongoDBModel(models.Model):
    """Base model class that saves to MongoDB"""
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Override save to write to MongoDB"""
        if mongo_adapter is None:
            # Fallback to SQLite if MongoDB not available
            return super().save(*args, **kwargs)
        
        try:
            # Prepare data for MongoDB
            mongo_data = self._prepare_mongo_data()
            
            # Insert or update in MongoDB
            collection_name = self._meta.db_table
            collection = mongo_adapter.db[collection_name]
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                # Update existing document
                collection.update_one({'_id': self._mongo_id}, {'$set': mongo_data})
            else:
                # Insert new document
                result = collection.insert_one(mongo_data)
                self._mongo_id = result.inserted_id
            
            logger.debug(f"✅ {self.__class__.__name__} saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save error for {self.__class__.__name__}: {str(e)}")
            # Fallback to SQLite
            return super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to remove from MongoDB"""
        if mongo_adapter is None:
            return super().delete(*args, **kwargs)
        
        try:
            collection_name = self._meta.db_table
            collection = mongo_adapter.db[collection_name]
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                collection.delete_one({'_id': self._mongo_id})
                logger.debug(f"✅ {self.__class__.__name__} deleted from MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB delete error: {str(e)}")
        
        return super().delete(*args, **kwargs)
    
    def _prepare_mongo_data(self):
        """Convert model instance to MongoDB document"""
        raise NotImplementedError("Subclasses must implement _prepare_mongo_data()")
    
    def _load_from_mongo(self, mongo_doc):
        """Load data from MongoDB document"""
        raise NotImplementedError("Subclasses must implement _load_from_mongo()")


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        """Save user to MongoDB"""
        if mongo_adapter is None:
            return super().save(*args, **kwargs)
        
        try:
            collection = mongo_adapter.db['auth_user']
            user_data = {
                'email': self.email,
                'password': self.password,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'is_active': self.is_active,
                'is_staff': self.is_staff,
                'is_superuser': self.is_superuser,
                'date_joined': self.date_joined,
                'last_login': self.last_login,
            }
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                collection.update_one({'_id': self._mongo_id}, {'$set': user_data})
            else:
                result = collection.insert_one(user_data)
                self._mongo_id = result.inserted_id
            
            logger.debug(f"✅ User {self.email} saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save error for User: {str(e)}")
        
        return super().save(*args, **kwargs)


class Trip(models.Model):
    TRIP_TYPES = [
        ('COUPLE', 'Couple'),
        ('FRIENDS', 'Friends'),
        ('FAMILY', 'Family'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_location = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    interested_activities = models.TextField()
    trip_type = models.CharField(max_length=10, choices=TRIP_TYPES)
    number_of_people = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    trip_plan = models.JSONField(null=True, blank=True)
    is_saved = models.BooleanField(default=False)
    is_posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    @property
    def average_rating(self):
        return self.ratings.aggregate(Avg('rating'))['rating__avg'] or 0.0

    @property
    def total_ratings(self):
        return self.ratings.count()

    def __str__(self):
        return f"{self.destination} Trip ({self.start_date} - {self.end_date})"
    
    def save(self, *args, **kwargs):
        """Save trip to MongoDB"""
        if mongo_adapter is None:
            return super().save(*args, **kwargs)
        
        try:
            collection = mongo_adapter.db['trips_trip']
            trip_data = {
                'user_id': str(self.user.id) if self.user else None,
                'destination': self.destination,
                'start_location': self.start_location,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'interested_activities': self.interested_activities,
                'trip_type': self.trip_type,
                'number_of_people': self.number_of_people,
                'trip_plan': self.trip_plan,
                'is_saved': self.is_saved,
                'is_posted': self.is_posted,
                'posted_at': self.posted_at,
                'created_at': self.created_at,
            }
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                collection.update_one({'_id': self._mongo_id}, {'$set': trip_data})
            else:
                result = collection.insert_one(trip_data)
                self._mongo_id = result.inserted_id
            
            logger.debug(f"✅ Trip '{self.destination}' saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save error for Trip: {str(e)}")
        
        return super().save(*args, **kwargs)


class Rating(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1, message="Rating must be at least 1"),
            MaxValueValidator(5, message="Rating cannot exceed 5")
        ]
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'user')

    def __str__(self):
        return f"{self.user.email}'s {self.rating}-star rating for {self.trip.destination} Trip"
    
    def save(self, *args, **kwargs):
        """Save rating to MongoDB"""
        if mongo_adapter is None:
            return super().save(*args, **kwargs)
        
        try:
            collection = mongo_adapter.db['trips_rating']
            rating_data = {
                'trip_id': str(self.trip.id) if self.trip else None,
                'user_id': str(self.user.id) if self.user else None,
                'rating': self.rating,
                'comment': self.comment,
                'created_at': self.created_at,
            }
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                collection.update_one({'_id': self._mongo_id}, {'$set': rating_data})
            else:
                result = collection.insert_one(rating_data)
                self._mongo_id = result.inserted_id
            
            logger.debug(f"✅ Rating saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save error for Rating: {str(e)}")
        
        return super().save(*args, **kwargs)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    def save(self, *args, **kwargs):
        """Save profile to MongoDB"""
        if mongo_adapter is None:
            return super().save(*args, **kwargs)
        
        try:
            collection = mongo_adapter.db['trips_profile']
            profile_data = {
                'user_id': str(self.user.id) if self.user else None,
                'avatar': str(self.avatar) if self.avatar else None,
                'bio': self.bio,
                'location': self.location,
                'birth_date': self.birth_date,
                'created_at': self.created_at,
                'updated_at': self.updated_at,
            }
            
            if hasattr(self, '_mongo_id') and self._mongo_id:
                collection.update_one({'_id': self._mongo_id}, {'$set': profile_data})
            else:
                result = collection.insert_one(profile_data)
                self._mongo_id = result.inserted_id
            
            logger.debug(f"✅ Profile saved to MongoDB")
        except Exception as e:
            logger.error(f"❌ MongoDB save error for Profile: {str(e)}")
        
        return super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
