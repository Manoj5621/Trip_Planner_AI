from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Trip

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('email', 'is_staff', 'is_active',)
    list_filter = ('is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email',)
    ordering = ('email',)

class TripAdmin(admin.ModelAdmin):
    list_display = ('destination', 'user', 'start_date', 'end_date', 'trip_type', 'is_saved')
    list_filter = ('trip_type', 'is_saved', 'start_date')
    search_fields = ('destination', 'start_location', 'user__email')
    date_hierarchy = 'start_date'

admin.site.register(User, CustomUserAdmin)
admin.site.register(Trip, TripAdmin) 