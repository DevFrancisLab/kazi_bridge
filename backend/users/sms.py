"""Africa's Talking SMS integration for KaziLink platform."""
import logging
import json
from typing import Dict, Optional

import africastalking
from africastalking.Service import AfricasTalkingException
from django.conf import settings

from .sms_utils import normalize_number

logger = logging.getLogger(__name__)

# Initialize Africa's Talking
if settings.AT_USERNAME and settings.AT_API_KEY:
    try:
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY
        )
        sms = africastalking.SMS
        logger.info("Africa's Talking SMS initialized successfully")
    except Exception as e:
        sms = None
        logger.error(f"Failed to initialize Africa's Talking: {str(e)}")
else:
    sms = None
    logger.warning("Africa's Talking credentials not configured in settings")


def send_sms(phone_number: str, message: str) -> Dict:
    """
    Send SMS using Africa's Talking API.
    
    Args:
        phone_number: Phone number in any format (will be normalized to E.164)
        message: SMS message content
        
    Returns:
        dict: Response containing:
            - success (bool): Whether SMS was sent successfully
            - messageId (str): Message ID if successful
            - phone (str): Normalized phone number
            - message (str): Message sent
            - error (str): Error message if failed
            - details (str): Additional error details
    """
    try:
        # Validate inputs
        if not phone_number or not isinstance(phone_number, str):
            logger.error(f"Invalid phone number: {phone_number}")
            return {
                "success": False,
                "error": "Invalid phone number provided",
                "details": "Phone number must be a non-empty string",
            }
        
        if not message or not isinstance(message, str):
            logger.error(f"Invalid message: {message}")
            return {
                "success": False,
                "error": "Invalid message provided",
                "details": "Message must be a non-empty string",
            }
        
        # Normalize phone number
        normalized_phone = normalize_number(phone_number)
        logger.info(f"Normalized phone: {phone_number} -> {normalized_phone}")
        
        # Check if Africa's Talking is configured
        if not sms or not settings.AT_USERNAME or not settings.AT_API_KEY:
            logger.error("Africa's Talking credentials not configured")
            return {
                "success": False,
                "error": "SMS service not configured",
                "details": "Africa's Talking credentials are missing",
            }
        
        # Send SMS via Africa's Talking
        logger.info(f"Sending SMS to {normalized_phone}: {message[:50]}...")
        response = sms.send(message, [normalized_phone], sender_id=settings.AT_SENDER_ID)
        
        logger.info(f"Africa's Talking Response: {response}")
        
        # Process response
        if response.get("SMSMessageData", {}).get("Recipients"):
            recipient = response["SMSMessageData"]["Recipients"][0]
            status = recipient.get("status", "Unknown")
            message_id = recipient.get("messageId", "")
            
            if status == "Success":
                logger.info(f"SMS sent successfully to {normalized_phone}, ID: {message_id}")
                return {
                    "success": True,
                    "messageId": message_id,
                    "phone": normalized_phone,
                    "message": message[:50] + "..." if len(message) > 50 else message,
                    "cost": recipient.get("cost", ""),
                }
            elif status == "InvalidPhoneNumber":
                logger.error(f"Invalid phone number: {normalized_phone}")
                return {
                    "success": False,
                    "error": "Invalid phone number",
                    "details": f"Phone number {normalized_phone} is not valid",
                    "phone": normalized_phone,
                }
            elif status == "UserInBlacklist":
                logger.warning(f"Phone number is blacklisted: {normalized_phone}")
                return {
                    "success": False,
                    "error": "Phone number is blacklisted",
                    "details": f"Cannot send SMS to blacklisted number {normalized_phone}",
                    "phone": normalized_phone,
                }
            else:
                logger.error(f"SMS sending failed with status: {status}")
                return {
                    "success": False,
                    "error": f"SMS sending failed",
                    "details": f"Status: {status}",
                    "phone": normalized_phone,
                }
        else:
            logger.error("No recipients in Africa's Talking response")
            return {
                "success": False,
                "error": "Invalid response from SMS provider",
                "details": "No recipients data in response",
            }
    
    except AfricasTalkingException as e:
        error_msg = str(e)
        logger.error(f"Africa's Talking Exception: {error_msg}")
        return {
            "success": False,
            "error": "SMS delivery failed",
            "details": error_msg,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error sending SMS: {error_msg}")
        return {
            "success": False,
            "error": "SMS delivery failed",
            "details": error_msg,
        }


def safe_send_sms(phone_number: str, message: str) -> bool:
    """
    Safe wrapper for sending SMS that never raises exceptions.
    
    Used for sending SMS in business logic where we want to ensure
    SMS failures don't interrupt the main workflow.
    
    Args:
        phone_number: Phone number in any format
        message: SMS message content
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        result = send_sms(phone_number, message)
        success = result.get("success", False)
        
        if success:
            logger.info(f"📱 SMS SENT: {result.get('phone')} -> {result.get('messageId')}")
            print(f"✅ SMS Sent: {result.get('phone')} (ID: {result.get('messageId')})")
        else:
            logger.warning(f"⚠️ SMS FAILED: {result.get('error')} - {result.get('details')}")
            print(f"❌ SMS Failed: {result.get('error')}")
        
        return success
    
    except Exception as e:
        # Log error but never raise
        logger.error(f"SAFE_SMS_WRAPPER - Critical error: {str(e)}")
        print(f"🚨 SAFE_SMS_WRAPPER: {str(e)}")
        return False


def send_job_notification_to_freelancers(job) -> Dict:
    """
    Send job notification SMS to relevant freelancers.
    
    Filters freelancers based on skills matching job requirements,
    otherwise limits to first 5 freelancers.
    
    Args:
        job: Job instance that was just created
        
    Returns:
        dict: Statistics about SMS sending
            - total: Total freelancers targeted
            - sent: Number of successful SMS
            - failed: Number of failed SMS
            - errors: List of errors encountered
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Try to find freelancers with matching skills
    job_keywords = job.title.lower().split() + job.description.lower().split()
    
    # Look for freelancers whose skills match job keywords
    skill_matching_freelancers = []
    all_freelancers = User.objects.filter(role='FREELANCER')
    
    for freelancer in all_freelancers:
        if freelancer.skills:
            freelancer_skills = [skill.strip().lower() for skill in freelancer.skills.split(',')]
            # Check if any job keyword matches freelancer skills
            if any(keyword in freelancer_skills for keyword in job_keywords):
                skill_matching_freelancers.append(freelancer)
    
    # If we found skill-matched freelancers, use them; otherwise limit to first 5
    if skill_matching_freelancers:
        freelancers = skill_matching_freelancers[:5]  # Limit even matched freelancers to 5
        logger.info(f"Found {len(skill_matching_freelancers)} skill-matched freelancers, sending to {len(freelancers)}")
    else:
        freelancers = list(all_freelancers[:5])  # Limit to first 5 freelancers
        logger.info(f"No skill matches found, sending to first {len(freelancers)} freelancers")
    
    total = len(freelancers)
    sent = 0
    failed = 0
    errors = []
    
    # Prepare message
    message = f"New job posted: {job.title}. Budget: KES {job.budget}. Login to KaziLink to bid."
    
    # Send SMS to each freelancer
    for freelancer in freelancers:
        if not freelancer.phone_number:
            logger.warning(f"Freelancer {freelancer.email} has no phone number")
            failed += 1
            errors.append(f"{freelancer.email}: No phone number")
            continue
        
        try:
            result = send_sms(freelancer.phone_number, message)
            
            if result.get("success"):
                sent += 1
                logger.info(f"Job notification sent to {freelancer.email} ({result.get('messageId')})")
            else:
                failed += 1
                error_msg = f"{freelancer.email}: {result.get('error')}"
                errors.append(error_msg)
                logger.warning(f"Failed to send job notification to {freelancer.email}: {result.get('details')}")
        
        except Exception as e:
            failed += 1
            error_msg = f"{freelancer.email}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error sending SMS to freelancer {freelancer.email}: {str(e)}")
    
    stats = {
        'total': total,
        'sent': sent,
        'failed': failed,
        'errors': errors,
    }
    
    logger.info(f"Job notification sending complete: {stats}")
    return stats



def send_sms(phone_number: str, message: str) -> Dict:
    """
    Send SMS using Africa's Talking API.
    
    Args:
        phone_number: Phone number in any format (will be normalized to E.164)
        message: SMS message content
        
    Returns:
        dict: Response containing:
            - success (bool): Whether SMS was sent successfully
            - messageId (str): Message ID if successful
            - phone (str): Normalized phone number
            - message (str): Message sent
            - error (str): Error message if failed
            - details (str): Additional error details
    """
    try:
        # Validate inputs
        if not phone_number or not isinstance(phone_number, str):
            logger.error(f"Invalid phone number: {phone_number}")
            return {
                "success": False,
                "error": "Invalid phone number provided",
                "details": "Phone number must be a non-empty string",
            }
        
        if not message or not isinstance(message, str):
            logger.error(f"Invalid message: {message}")
            return {
                "success": False,
                "error": "Invalid message provided",
                "details": "Message must be a non-empty string",
            }
        
        # Normalize phone number
        normalized_phone = normalize_number(phone_number)
        logger.info(f"Normalized phone: {phone_number} -> {normalized_phone}")
        
        # Check if Africa's Talking is configured
        if not sms or not settings.AT_USERNAME or not settings.AT_API_KEY:
            logger.error("Africa's Talking credentials not configured")
            return {
                "success": False,
                "error": "SMS service not configured",
                "details": "Africa's Talking credentials are missing",
            }
        
        # Send SMS via Africa's Talking
        logger.info(f"Sending SMS to {normalized_phone}: {message[:50]}...")
        response = sms.send(message, [normalized_phone], sender_id=settings.AT_SENDER_ID)
        
        logger.info(f"Africa's Talking Response: {response}")
        
        # Process response
        if response.get("SMSMessageData", {}).get("Recipients"):
            recipient = response["SMSMessageData"]["Recipients"][0]
            status = recipient.get("status", "Unknown")
            message_id = recipient.get("messageId", "")
            
            if status == "Success":
                logger.info(f"SMS sent successfully to {normalized_phone}, ID: {message_id}")
                return {
                    "success": True,
                    "messageId": message_id,
                    "phone": normalized_phone,
                    "message": message[:50] + "..." if len(message) > 50 else message,
                    "cost": recipient.get("cost", ""),
                }
            elif status == "InvalidPhoneNumber":
                logger.error(f"Invalid phone number: {normalized_phone}")
                return {
                    "success": False,
                    "error": "Invalid phone number",
                    "details": f"Phone number {normalized_phone} is not valid",
                    "phone": normalized_phone,
                }
            elif status == "UserInBlacklist":
                logger.warning(f"Phone number is blacklisted: {normalized_phone}")
                return {
                    "success": False,
                    "error": "Phone number is blacklisted",
                    "details": f"Cannot send SMS to blacklisted number {normalized_phone}",
                    "phone": normalized_phone,
                }
            else:
                logger.error(f"SMS sending failed with status: {status}")
                return {
                    "success": False,
                    "error": f"SMS sending failed",
                    "details": f"Status: {status}",
                    "phone": normalized_phone,
                }
        else:
            logger.error("No recipients in Africa's Talking response")
            return {
                "success": False,
                "error": "Invalid response from SMS provider",
                "details": "No recipients data in response",
            }
    
    except AfricasTalkingException as e:
        logger.error(f"Africa's Talking Exception: {str(e)}")
        return {
            "success": False,
            "error": "SMS delivery failed",
            "details": str(e),
        }
    except ImportError:
        logger.error("africastalking package not installed")
        return {
            "success": False,
            "error": "SMS service unavailable",
            "details": "africastalking package not installed",
        }
    except Exception as e:
        logger.error(f"Unexpected error sending SMS: {str(e)}")
        return {
            "success": False,
            "error": "Unexpected error",
            "details": str(e),
        }


def safe_send_sms(phone_number: str, message: str) -> bool:
    """
    Safe wrapper for sending SMS that never raises exceptions.
    
    Used for sending SMS in business logic where we want to ensure
    SMS failures don't interrupt the main workflow.
    
    Args:
        phone_number: Phone number in any format
        message: SMS message content
        
    Returns:
        bool: True if SMS sent successfully, False otherwise
    """
    try:
        result = send_sms(phone_number, message)
        success = result.get("success", False)
        
        if success:
            logger.info(f"📱 SMS SENT: {result.get('phone')} -> {result.get('messageId')}")
            print(f"✅ SMS Sent: {result.get('phone')} (ID: {result.get('messageId')})")
        else:
            logger.warning(f"⚠️ SMS FAILED: {result.get('error')} - {result.get('details')}")
            print(f"❌ SMS Failed: {result.get('error')}")
        
        return success
    
    except Exception as e:
        # Log error but never raise
        logger.error(f"SAFE_SMS_WRAPPER - Critical error: {str(e)}")
        print(f"🚨 SAFE_SMS_WRAPPER: {str(e)}")
        return False


def send_job_notification_to_freelancers(job) -> Dict:
    """
    Send job notification SMS to relevant freelancers.
    
    Filters freelancers based on skills matching job requirements,
    otherwise limits to first 5 freelancers.
    
    Args:
        job: Job instance that was just created
        
    Returns:
        dict: Statistics about SMS sending
            - total: Total freelancers targeted
            - sent: Number of successful SMS
            - failed: Number of failed SMS
            - errors: List of errors encountered
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Try to find freelancers with matching skills
    job_keywords = job.title.lower().split() + job.description.lower().split()
    
    # Look for freelancers whose skills match job keywords
    skill_matching_freelancers = []
    all_freelancers = User.objects.filter(role='FREELANCER')
    
    for freelancer in all_freelancers:
        if freelancer.skills:
            freelancer_skills = [skill.strip().lower() for skill in freelancer.skills.split(',')]
            # Check if any job keyword matches freelancer skills
            if any(keyword in freelancer_skills for keyword in job_keywords):
                skill_matching_freelancers.append(freelancer)
    
    # If we found skill-matched freelancers, use them; otherwise limit to first 5
    if skill_matching_freelancers:
        freelancers = skill_matching_freelancers[:5]  # Limit even matched freelancers to 5
        logger.info(f"Found {len(skill_matching_freelancers)} skill-matched freelancers, sending to {len(freelancers)}")
    else:
        freelancers = list(all_freelancers[:5])  # Limit to first 5 freelancers
        logger.info(f"No skill matches found, sending to first {len(freelancers)} freelancers")
    
    total = len(freelancers)
    sent = 0
    failed = 0
    errors = []
    
    # Prepare message
    message = f"New job posted: {job.title}. Budget: KES {job.budget}. Login to KaziLink to bid."
    
    # Send SMS to each freelancer
    for freelancer in freelancers:
        if not freelancer.phone_number:
            logger.warning(f"Freelancer {freelancer.email} has no phone number")
            failed += 1
            errors.append(f"{freelancer.email}: No phone number")
            continue
        
        try:
            result = send_sms(freelancer.phone_number, message)
            
            if result.get("success"):
                sent += 1
                logger.info(f"Job notification sent to {freelancer.email} ({result.get('messageId')})")
            else:
                failed += 1
                error_msg = f"{freelancer.email}: {result.get('error')}"
                errors.append(error_msg)
                logger.warning(f"Failed to send job notification to {freelancer.email}: {result.get('details')}")
        
        except Exception as e:
            failed += 1
            error_msg = f"{freelancer.email}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error sending SMS to freelancer {freelancer.email}: {str(e)}")
    
    stats = {
        'total': total,
        'sent': sent,
        'failed': failed,
        'errors': errors,
    }
    
    logger.info(f"Job notification sending complete: {stats}")
    return stats
