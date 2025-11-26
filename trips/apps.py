from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class TripsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trips'
    
    def ready(self):
        """
        Initialize MongoDB when Django app is ready.
        """
        try:
            from django.conf import settings
            if hasattr(settings, 'MONGO_DB') and settings.MONGO_DB is not None:
                from trips.mongodb_adapter import mongo_adapter
                if mongo_adapter is not None:
                    try:
                        mongo_adapter.connect()
                        mongo_adapter.create_collections()
                        logger.info("[MongoDB] Connected and collections initialized")
                    except Exception as e:
                        logger.warning(f"[MongoDB] Initialization warning: {str(e)}")
            else:
                logger.debug("[MongoDB] Not configured - using SQLite only")
        except Exception as e:
            logger.debug(f"[MongoDB] Adapter not available: {str(e)}")
