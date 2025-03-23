from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import TripPlannerForm, ProfileForm
from .models import Trip, Rating
from .ai_service import AITripPlanner
import json
from django.utils import timezone
from django.db.models import Avg

def home(request):
    # Get a few recent posted trips to display on the home page
    recent_trips = Trip.objects.filter(is_posted=True).order_by('-posted_at')[:3]
    return render(request, 'trips/home.html', {'recent_trips': recent_trips})

@login_required
def dashboard(request):
    saved_trips = Trip.objects.filter(user=request.user, is_saved=True)
    posted_trips = Trip.objects.filter(user=request.user, is_posted=True)
    return render(request, 'trips/dashboard.html', {
        'saved_trips': saved_trips,
        'posted_trips': posted_trips
    })

@login_required
def plan_trip(request):
    if request.method == 'POST':
        form = TripPlannerForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.user = request.user
            
            # Generate AI trip plan using default provider
            try:
                planner = AITripPlanner()  # No provider specified, will use default from environment
                
                trip_data = {
                    'start_location': trip.start_location,
                    'destination': trip.destination,
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'interested_activities': trip.interested_activities,
                    'trip_type': trip.trip_type,
                    'number_of_people': trip.number_of_people
                }
                
                trip_plan = planner.generate_trip_plan(trip_data)
                if isinstance(trip_plan, str):
                    trip.trip_plan = json.loads(trip_plan)
                else:
                    trip.trip_plan = trip_plan
                
                if "error" in trip_plan:
                    raise ValidationError(trip_plan["error"])
                    
                trip.save()
                messages.success(request, 'Trip plan generated successfully!')
                return redirect('trips:view_trip', trip_id=trip.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error generating trip plan: {str(e)}")
    else:
        form = TripPlannerForm()
    
    return render(request, 'trips/plan_trip.html', {'form': form})

@login_required
def view_trip(request, trip_id):
    try:
        # First try to get user's own trip
        trip = Trip.objects.get(id=trip_id, user=request.user)
    except Trip.DoesNotExist:
        # If not found, check if it's a posted trip by another user
        try:
            trip = Trip.objects.get(id=trip_id, is_posted=True)
        except Trip.DoesNotExist:
            messages.error(request, "Trip not found or you don't have permission to view it.")
            return redirect('trips:dashboard')
    return render(request, 'trips/view_trip.html', {'trip': trip})

@login_required
def save_trip(request, trip_id):
    if request.method == 'POST':
        try:
            trip = Trip.objects.get(id=trip_id, user=request.user)
            if trip.is_saved:
                return JsonResponse({'status': 'error', 'message': 'Trip is already saved'})
            trip.is_saved = True
            trip.save()
            return JsonResponse({'status': 'success', 'message': 'Trip saved successfully'})
        except Trip.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Trip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def saved_trips(request):
    trips = Trip.objects.filter(user=request.user, is_saved=True)
    return render(request, 'trips/saved_trips.html', {'trips': trips})

@login_required
def explore_trips(request):
    # Get all posted trips ordered by most recent first, including average ratings
    posted_trips = Trip.objects.filter(is_posted=True).order_by('-posted_at')
    return render(request, 'trips/explore_trips.html', {'trips': posted_trips})

@login_required
def post_trip(request, trip_id):
    if request.method == 'POST':
        try:
            trip = Trip.objects.get(id=trip_id, user=request.user)
            if trip.is_posted:
                return JsonResponse({'status': 'error', 'message': 'Trip is already posted'})
            trip.is_posted = True
            trip.posted_at = timezone.now()
            trip.save()
            return JsonResponse({'status': 'success', 'message': 'Trip posted successfully'})
        except Trip.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Trip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def rate_trip(request, trip_id):
    if request.method == 'POST':
        try:
            trip = Trip.objects.get(id=trip_id)
            rating_value = int(request.POST.get('rating'))
            comment = request.POST.get('comment', '')

            if rating_value < 1 or rating_value > 5:
                return JsonResponse({'status': 'error', 'message': 'Rating must be between 1 and 5'})

            # Update or create the rating
            rating, created = Rating.objects.update_or_create(
                trip=trip,
                user=request.user,
                defaults={
                    'rating': rating_value,
                    'comment': comment
                }
            )

            # Get updated rating stats
            avg_rating = trip.average_rating
            total_ratings = trip.total_ratings

            return JsonResponse({
                'status': 'success',
                'message': 'Rating submitted successfully',
                'average_rating': round(avg_rating, 1),
                'total_ratings': total_ratings
            })

        except Trip.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Trip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def get_trip_ratings(request, trip_id):
    try:
        trip = Trip.objects.get(id=trip_id)
        ratings = Rating.objects.filter(trip=trip).order_by('-created_at')
        
        ratings_data = [{
            'user': rating.user.email,
            'rating': rating.rating,
            'comment': rating.comment,
            'created_at': rating.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_own_rating': rating.user == request.user
        } for rating in ratings]

        return JsonResponse({
            'status': 'success',
            'average_rating': round(trip.average_rating, 1),
            'total_ratings': trip.total_ratings,
            'ratings': ratings_data
        })

    except Trip.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Trip not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('trips:dashboard')
    else:
        form = ProfileForm(instance=request.user.profile)
    return render(request, 'trips/edit_profile.html', {'form': form})

def about(request):
    return render(request, 'trips/about.html')

def contact(request):
    if request.method == 'POST':
        # Handle form submission here
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Add your email sending logic here
        
        messages.success(request, 'Your message has been sent successfully!')
        return redirect('trips:contact')
        
    return render(request, 'trips/contact.html') 