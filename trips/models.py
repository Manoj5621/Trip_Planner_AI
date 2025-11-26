from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver
from trips.mongodb_adapter import mongo_adapter
import logging

logger = logging.getLogger(__name__)

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
        """Save user to both SQLite and MongoDB"""
        try:
            super().save(*args, **kwargs)
            if mongo_adapter is not None:
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
                existing = collection.find_one({'email': self.email})
                if existing:
                    collection.update_one({'email': self.email}, {'$set': user_data})
                else:
                    collection.insert_one(user_data)
                logger.info(f"✅ User '{self.email}' synced to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error saving user: {str(e)}")

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
        """Save trip to both SQLite and MongoDB"""
        try:
            super().save(*args, **kwargs)
            if mongo_adapter is not None:
                collection = mongo_adapter.db['trips_trip']
                trip_data = {
                    'user_id': str(self.user.id) if self.user else None,
                    'destination': self.destination,
                    'start_location': self.start_location,
                    'start_date': self.start_date.isoformat() if self.start_date else None,
                    'end_date': self.end_date.isoformat() if self.end_date else None,
                    'interested_activities': self.interested_activities,
                    'trip_type': self.trip_type,
                    'number_of_people': self.number_of_people,
                    'trip_plan': self.trip_plan,
                    'is_saved': self.is_saved,
                    'is_posted': self.is_posted,
                    'posted_at': self.posted_at.isoformat() if self.posted_at else None,
                    'created_at': self.created_at.isoformat() if self.created_at else None,
                }
                existing = collection.find_one({'destination': self.destination, 'user_id': str(self.user.id)})
                if existing:
                    collection.update_one({'_id': existing['_id']}, {'$set': trip_data})
                else:
                    collection.insert_one(trip_data)
                logger.info(f"✅ Trip '{self.destination}' synced to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error saving trip: {str(e)}")

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
        """Save rating to both SQLite and MongoDB"""
        try:
            super().save(*args, **kwargs)
            if mongo_adapter is not None:
                collection = mongo_adapter.db['trips_rating']
                rating_data = {
                    'trip_id': str(self.trip.id) if self.trip else None,
                    'user_id': str(self.user.id) if self.user else None,
                    'rating': self.rating,
                    'comment': self.comment,
                    'created_at': self.created_at,
                }
                existing = collection.find_one({'trip_id': str(self.trip.id), 'user_id': str(self.user.id)})
                if existing:
                    collection.update_one({'_id': existing['_id']}, {'$set': rating_data})
                else:
                    collection.insert_one(rating_data)
                logger.info(f"✅ Rating synced to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error saving rating: {str(e)}")

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
        """Save profile to both SQLite and MongoDB"""
        try:
            super().save(*args, **kwargs)
            if mongo_adapter is not None:
                collection = mongo_adapter.db['trips_profile']
                profile_data = {
                    'user_id': str(self.user.id) if self.user else None,
                    'avatar': str(self.avatar) if self.avatar else None,
                    'bio': self.bio,
                    'location': self.location,
                    'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                    'created_at': self.created_at.isoformat() if self.created_at else None,
                    'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                }
                existing = collection.find_one({'user_id': str(self.user.id)})
                if existing:
                    collection.update_one({'_id': existing['_id']}, {'$set': profile_data})
                else:
                    collection.insert_one(profile_data)
                logger.info(f"✅ Profile synced to MongoDB")
        except Exception as e:
            logger.error(f"❌ Error saving profile: {str(e)}")

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
