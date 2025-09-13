# HMS Session Management and Automatic Admission Charges Implementation

## Overview

This document outlines the comprehensive implementation of:
1. **Enhanced User Session Management** with timeout and security features
2. **Patient-Specific Session Tracking** for enhanced security
3. **Automatic Admission Charge Deduction** at 12:00 AM daily
4. **Admin Monitoring Interface** for system oversight

## 1. Session Management Implementation

### 1.1 Enhanced Session Settings

**File: `hms/settings.py`**

```python
# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1200  # 20 minutes default
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Patient-specific session settings
PATIENT_SESSION_TIMEOUT = 1200  # 20 minutes for patient portal
STAFF_SESSION_TIMEOUT = 1200   # 20 minutes for staff
SESSION_TIMEOUT_WARNING = 300  # 5 minutes warning before timeout
```

### 1.2 Session Middleware

**File: `core/middleware.py`**

#### SessionTimeoutMiddleware
- Automatically logs out users when sessions expire
- Supports different timeout periods for different user types
- Provides session information to templates for client-side warnings

#### PatientSessionMiddleware  
- Additional security for patient portal access
- Rate limiting and suspicious activity detection
- Enhanced logging for patient data access

### 1.3 Session Management Views

**File: `accounts/session_views.py`**

- **`extend_session()`**: AJAX endpoint to extend user sessions
- **`activity_ping()`**: Records user activity without full session extension
- **`session_status()`**: Returns current session status and time remaining

### 1.4 Client-Side Session Warning

**File: `templates/includes/session_timeout_warning.html`**

- Bootstrap modal with countdown timer
- Automatic session extension requests
- User activity tracking
- Graceful logout handling

## 2. Automatic Admission Charge Deduction

### 2.1 Management Command

**File: `inpatient/management/commands/daily_admission_charges.py`**

Features:
- Processes all active admissions daily at 12:00 AM
- Exempts NHIA patients from charges
- Prevents duplicate charges for the same date
- Comprehensive error handling and logging
- Dry-run mode for testing

Usage:
```bash
python manage.py daily_admission_charges
python manage.py daily_admission_charges --date 2025-01-15
python manage.py daily_admission_charges --dry-run
```

### 2.2 Celery Integration

**File: `hms/celery.py`**

Scheduled tasks:
- `daily-admission-charges`: Runs at 12:00 AM daily
- `session-cleanup`: Hourly expired session cleanup
- `wallet-balance-notifications`: Low balance alerts every 2 hours

**File: `inpatient/tasks.py`**

- **`process_daily_admission_charges()`**: Main Celery task
- **`process_single_admission_charge()`**: Individual admission processing
- **`send_low_balance_notifications()`**: Patient wallet alerts

### 2.3 Enhanced Wallet Integration

**Patient Wallet Features:**
- Automatic wallet creation during admission
- Negative balance support (prevents service interruption)
- Comprehensive transaction logging with admission links
- Balance warnings and notifications

### 2.4 Admission Process Enhancement

**File: `inpatient/views.py`**

Enhanced `create_admission()` view:
- Automatic wallet creation if needed
- Admission fee deduction with proper logging
- Clear messaging about daily charges
- NHIA exemption handling

## 3. Admin Monitoring Interface

### 3.1 Admin Dashboard Views

**File: `core/admin_views.py`**

#### Admission Charges Dashboard
- Daily charge processing statistics
- Active admissions monitoring
- Failed charge alerts (negative balances)
- Date range filtering

#### Session Monitoring Dashboard  
- Active/expired session statistics
- Suspicious activity detection
- User activity monitoring
- Security alerts

#### Manual Charge Processing
- Emergency charge processing interface
- Individual admission charge processing
- Bulk operation support

#### Wallet Management Dashboard
- Overall wallet statistics
- Low/negative balance monitoring
- Large transaction alerts
- Patient wallet health overview

#### System Health Check
- Database connectivity monitoring
- Stuck admission detection
- Session cleanup alerts
- Overall system status

### 3.2 URL Configuration

Admin monitoring URLs should be added to handle these views for authorized staff members.

## 4. Key Features and Benefits

### 4.1 Session Management Benefits

1. **Enhanced Security**: Different timeout periods for different user types
2. **User Experience**: Warning notifications before timeout
3. **Activity Tracking**: Comprehensive logging of user sessions
4. **Automatic Cleanup**: Regular removal of expired sessions
5. **Patient Protection**: Extra security layers for patient data access

### 4.2 Automatic Charging Benefits

1. **Automation**: No manual intervention required for daily charges
2. **Accuracy**: Prevents double charging and handles exemptions
3. **Transparency**: Complete transaction logging and audit trails
4. **Flexibility**: Support for different ward rates and patient types
5. **Reliability**: Retry mechanisms and comprehensive error handling

### 4.3 Admin Monitoring Benefits

1. **Real-time Oversight**: Live monitoring of system operations
2. **Proactive Alerts**: Early warning for potential issues
3. **Manual Controls**: Emergency override capabilities
4. **Comprehensive Reporting**: Detailed statistics and analytics
5. **System Health**: Overall system status monitoring

## 5. Installation and Setup

### 5.1 Required Dependencies

Add to `requirements.txt`:
```
celery>=5.3.0
redis>=4.5.0  # For Celery broker
django-celery-beat>=2.5.0
```

### 5.2 Redis Setup (for Celery)

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 5.3 Environment Variables

Add to your environment:
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
WALLET_LOW_BALANCE_THRESHOLD=100.00
SESSION_TIMEOUT_WARNING=300
PATIENT_SESSION_TIMEOUT=1200
STAFF_SESSION_TIMEOUT=1200
```

### 5.4 Database Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5.5 Celery Services

Start Celery worker:
```bash
celery -A hms worker --loglevel=info
```

Start Celery beat (scheduler):
```bash
celery -A hms beat --loglevel=info
```

## 6. Testing

### 6.1 Session Management Testing

1. Test different user types with different timeout periods
2. Verify session warning functionality
3. Test activity tracking and session extension
4. Verify automatic logout on expiration

### 6.2 Automatic Charges Testing

1. Run dry-run mode to verify charge calculations
2. Test NHIA patient exemptions
3. Verify duplicate charge prevention
4. Test manual charge processing interface

### 6.3 Admin Interface Testing

1. Verify dashboard statistics accuracy
2. Test manual processing functions
3. Validate health check alerts
4. Test notification systems

## 7. Production Deployment

### 7.1 Cron Job Alternative

If Celery is not available, set up a cron job:
```
# Add to crontab: Run daily admission charges at 12:00 AM
0 0 * * * cd /path/to/hms && python manage.py daily_admission_charges >> /var/log/hms/admission_charges.log 2>&1
```

### 7.2 Monitoring and Logging

1. Set up log rotation for charge processing logs
2. Configure alerts for failed charge processing
3. Monitor Celery worker health
4. Set up database backup before daily processing

### 7.3 Security Considerations

1. Ensure Redis is secured (authentication, firewall)
2. Monitor session activity for unusual patterns
3. Regular security audits of patient data access
4. Implement proper SSL/TLS for all communications

## 8. Troubleshooting

### 8.1 Common Issues

1. **Celery not running**: Verify Redis connection and worker status
2. **Duplicate charges**: Check unique constraints and date filtering
3. **Session timeouts too aggressive**: Adjust timeout settings
4. **Wallet creation failures**: Verify patient model integrity

### 8.2 Log Locations

- Celery logs: Check worker output
- Django logs: Configured in `settings.py` LOGGING
- Admission charges: Management command output
- Session activity: Middleware logging

## 9. Future Enhancements

### 9.1 Potential Improvements

1. **SMS Notifications**: Low balance alerts via SMS
2. **Email Reporting**: Daily charge processing summaries
3. **Advanced Analytics**: Predictive analytics for wallet balances
4. **Mobile App Integration**: Push notifications for session warnings
5. **Audit Trail Enhancements**: More detailed activity logging

### 9.2 Scalability Considerations

1. **Database Optimization**: Indexes for frequently queried fields
2. **Celery Scaling**: Multiple workers for high-volume processing
3. **Caching Strategy**: Redis caching for frequent queries
4. **Load Balancing**: Session management across multiple servers

This implementation provides a robust, scalable solution for session management and automatic admission charge processing while maintaining all existing HMS functionalities.