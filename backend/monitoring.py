"""
Local monitoring and logging system for ATeam
Provides performance monitoring, error tracking, and system health checks
"""

import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps
from collections import defaultdict, deque
import psutil
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ateam.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.max_metrics = 1000  # Keep last 1000 data points
        self.lock = threading.Lock()
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        with self.lock:
            metric_data = {
                'timestamp': datetime.now().isoformat(),
                'value': value,
                'tags': tags or {}
            }
            
            self.metrics[metric_name].append(metric_data)
            
            # Keep only the last max_metrics entries
            if len(self.metrics[metric_name]) > self.max_metrics:
                self.metrics[metric_name].popleft()
    
    def get_metric_stats(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for a metric over the last N minutes"""
        with self.lock:
            if metric_name not in self.metrics:
                return {}
            
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            recent_metrics = [
                m for m in self.metrics[metric_name]
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            if not recent_metrics:
                return {}
            
            values = [m['value'] for m in recent_metrics]
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1] if values else None
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self.lock:
            return {
                name: list(metrics) for name, metrics in self.metrics.items()
            }

class SystemHealthMonitor:
    def __init__(self):
        self.health_checks = {}
        self.last_check = None
        self.check_interval = 60  # seconds
    
    def register_health_check(self, name: str, check_func):
        """Register a health check function"""
        self.health_checks[name] = check_func
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        if (self.last_check and 
            datetime.now() - self.last_check < timedelta(seconds=self.check_interval)):
            return self.last_results
        
        results = {}
        
        # System-level health checks
        results['system'] = self._check_system_health()
        
        # Custom health checks
        for name, check_func in self.health_checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        self.last_check = datetime.now()
        self.last_results = results
        return results
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check system-level health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network connections
            connections = len(psutil.net_connections())
            
            return {
                'status': 'healthy',
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'network_connections': connections,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

class ErrorTracker:
    def __init__(self):
        self.errors = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
    
    def track_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Track an error occurrence"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.errors.append(error_data)
        self.error_counts[type(error).__name__] += 1
        
        logger.error(f"Error tracked: {error_data}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [
            e for e in self.errors
            if datetime.fromisoformat(e['timestamp']) > cutoff_time
        ]
        
        return {
            'total_errors': len(recent_errors),
            'error_types': dict(self.error_counts),
            'recent_errors': list(recent_errors[-10:])  # Last 10 errors
        }

# Global monitoring instances
performance_monitor = PerformanceMonitor()
health_monitor = SystemHealthMonitor()
error_tracker = ErrorTracker()

# Decorator for performance monitoring
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    metric_name, 
                    execution_time,
                    {'status': 'success'}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    metric_name, 
                    execution_time,
                    {'status': 'error', 'error_type': type(e).__name__}
                )
                error_tracker.track_error(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    metric_name, 
                    execution_time,
                    {'status': 'success'}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                performance_monitor.record_metric(
                    metric_name, 
                    execution_time,
                    {'status': 'error', 'error_type': type(e).__name__}
                )
                error_tracker.track_error(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                raise
        
        # Return the appropriate wrapper based on whether the function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

# Register default health checks
def check_llm_health():
    """Check LLM service availability"""
    try:
        from llm_interface import LLMInterface
        llm = LLMInterface()
        models = llm.get_available_models()
        return {
            'status': 'healthy', 
            'message': f'LLM service OK, {len(models)} models available'
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

# Register health checks
health_monitor.register_health_check('llm', check_llm_health)