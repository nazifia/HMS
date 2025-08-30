"""
Custom exceptions for HMS application
"""

class HMSException(Exception):
    """Base exception for HMS application"""
    pass

class PatientNotFoundException(HMSException):
    """Raised when a patient is not found"""
    pass

class InsufficientInventoryException(HMSException):
    """Raised when there's insufficient inventory for a request"""
    pass

class PaymentProcessingException(HMSException):
    """Raised when payment processing fails"""
    pass

class AuthorizationException(HMSException):
    """Raised when user lacks required authorization"""
    pass

class ValidationException(HMSException):
    """Raised when data validation fails"""
    pass

class BusinessLogicException(HMSException):
    """Raised when business logic constraints are violated"""
    pass

class IntegrationException(HMSException):
    """Raised when external service integration fails"""
    pass

class ConfigurationException(HMSException):
    """Raised when system configuration is invalid"""
    pass
