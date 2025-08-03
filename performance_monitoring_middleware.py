
"""
Performance Monitoring Middleware for HMS
"""
import time
import logging
from django.db import connection

logger = logging.getLogger('hms.performance')

class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        query_count = len(connection.queries) - initial_queries
        
        # Log performance metrics
        if response_time > 1000:  # Log slow requests
            logger.warning(f"Slow request: {request.path} took {response_time:.2f}ms with {query_count} queries")
        
        # Add performance headers
        response['X-Response-Time'] = f"{response_time:.2f}ms"
        response['X-Query-Count'] = str(query_count)
        
        return response
