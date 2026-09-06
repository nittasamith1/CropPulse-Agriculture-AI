"""
CropPulse – Auth Router
Handles JWT user registration, login, token refresh, logout, password reset, email verification, and profile/farm CRUD.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Request
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import settings
from backend.dependencies import get_current_user
from backend.models.user import (
    UserRegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserProfileResponse, UserUpdateRequest,
    MessageResponse, ChangePasswordRequest
)
from backend.models.farm import FarmCreateRequest, FarmResponse, FarmUpdateRequest
from backend.services.auth_service import AuthService
from backend.services.email_service import email_service
from backend.services.mongodb_service import MongoDBService
from backend.services.notification_service import notification_service
from backend.utils.helpers import generate_id, utc_now, sanitize_dict

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# MongoDB Services
_user_svc = MongoDBService(settings.COLLECTION_USERS, id_field="uid")
_farm_svc = MongoDBService(settings.COLLECTION_FARMS, id_field="farm_id")
_refresh_svc = MongoDBService(settings.COLLECTION_REFRESH_TOKENS, id_field="token")
_reset_svc = MongoDBService(settings.COLLECTION_RESET_TOKENS, id_field="token")


# ── Register ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, payload: UserRegisterRequest):
    """Register a new user, save in MongoDB and send verification email."""
    try:
        # Check if email already exists
        existing_user = await _user_svc.collection.find_one({"email": payload.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists."
            )

        uid = generate_id("user")
        hashed_password = AuthService.hash_password(payload.password)
        now = utc_now()

        user_doc = sanitize_dict({
            "uid": uid,
            "email": payload.email,
            "hashed_password": hashed_password,
            "name": payload.name,
            "role": payload.role,
            "phone": payload.phone,
            "state": payload.state,
            "district": payload.district,
            "profile_picture_url": None,
            "farm_ids": [],
            "is_email_verified": False,
            "is_active": True,
            "total_predictions": 0,
            "created_at": now,
            "updated_at": now,
        })

        await _user_svc.create(uid, user_doc)

        # Generate email verification token
        verify_token = str(uuid.uuid4())
        # Store verification token in db with expiration (24h)
        expire_at = now + timedelta(hours=24)
        await _reset_svc.create(verify_token, {
            "token": verify_token,
            "email": payload.email,
            "type": "verify_email",
            "expires_at": expire_at
        })

        # Send Email
        try:
            await email_service.send_verification_email(payload.email, verify_token)
        except Exception as e:
            logger.warning(f"Could not send verification email: {e}")

        # Welcome notification
        await notification_service.system_notification(
            user_id=uid,
            title="🌱 Welcome to CropPulse!",
            message="Your account has been created successfully. Verify your email to complete registration.",
        )

        logger.info(f"New user registered: {payload.email} (uid={uid})")
        return MessageResponse(message="Account created successfully. Please check your email for the verification link.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to a server error."
        )


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest):
    """Authenticate credentials and return JWT Access + Refresh tokens."""
    user = await _user_svc.collection.find_one({"email": payload.email})
    if not user or not AuthService.verify_password(payload.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact admin."
        )

    uid = user["uid"]
    role = user.get("role", "farmer")
    name = user.get("name", "")

    # Create Access & Refresh Tokens
    access_token = AuthService.create_access_token({"uid": uid, "email": user["email"], "role": role})
    refresh_token = AuthService.create_refresh_token({"uid": uid})

    # Save refresh token in DB
    now = utc_now()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await _refresh_svc.create(refresh_token, {
        "token": refresh_token,
        "user_id": uid,
        "expires_at": expires_at,
        "created_at": now
    })

    logger.info(f"User logged in: {user['email']} (uid={uid})")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=role,
        name=name
    )


# ── Refresh Token ─────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest):
    """Generate a new Access Token using a valid Refresh Token."""
    stored_token = await _refresh_svc.get(payload.refresh_token)
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )

    # Check expiration
    if stored_token.get("expires_at") and stored_token["expires_at"].replace(tzinfo=timezone.utc) < utc_now():
        await _refresh_svc.delete(payload.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired refresh token."
        )

    # Verify signature
    decoded = AuthService.verify_token(payload.refresh_token, expected_type="refresh")
    if not decoded:
        await _refresh_svc.delete(payload.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token signature."
        )

    uid = decoded.get("uid")
    user = await _user_svc.get(uid)
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated."
        )

    # Issue new tokens
    access_token = AuthService.create_access_token({"uid": uid, "email": user["email"], "role": user.get("role", "farmer")})
    new_refresh_token = AuthService.create_refresh_token({"uid": uid})

    # Delete old, save new refresh token
    await _refresh_svc.delete(payload.refresh_token)
    now = utc_now()
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await _refresh_svc.create(new_refresh_token, {
        "token": new_refresh_token,
        "user_id": uid,
        "expires_at": expires_at,
        "created_at": now
    })

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        role=user.get("role", "farmer"),
        name=user.get("name", "")
    )


# ── Logout ────────────────────────────────────────────────────────────────────
@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshTokenRequest):
    """Blacklist/remove the refresh token from DB."""
    await _refresh_svc.delete(payload.refresh_token)
    return MessageResponse(message="Logged out successfully.")


# ── Forgot Password ───────────────────────────────────────────────────────────
@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest):
    """Create reset password link and log/send email."""
    user = await _user_svc.collection.find_one({"email": payload.email})
    if not user:
        # Return success anyway to prevent email enumeration
        return MessageResponse(message="If this email is registered, a password reset link has been sent.")

    # Create token
    reset_token = str(uuid.uuid4())
    now = utc_now()
    expires_at = now + timedelta(hours=1)

    await _reset_svc.create(reset_token, {
        "token": reset_token,
        "email": payload.email,
        "type": "reset_password",
        "expires_at": expires_at
    })

    try:
        await email_service.send_password_reset_email(payload.email, reset_token)
    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")

    return MessageResponse(message="Password reset link generated. Check your email inbox.")


# ── Reset Password ────────────────────────────────────────────────────────────
@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest):
    """Verify reset token and update password."""
    stored = await _reset_svc.get(payload.token)
    if not stored or stored.get("type") != "reset_password":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    # Check expiry
    if stored.get("expires_at") and stored["expires_at"].replace(tzinfo=timezone.utc) < utc_now():
        await _reset_svc.delete(payload.token)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired."
        )

    email = stored["email"]
    user = await _user_svc.collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    hashed_password = AuthService.hash_password(payload.new_password)
    await _user_svc.update(user["uid"], {"hashed_password": hashed_password, "updated_at": utc_now()})
    
    # Delete reset token
    await _reset_svc.delete(payload.token)
    logger.info(f"Password reset completed for: {email}")
    return MessageResponse(message="Password reset successfully.")


# ── Verify Email ──────────────────────────────────────────────────────────────
@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str):
    """Mark user email as verified in database."""
    stored = await _reset_svc.get(token)
    if not stored or stored.get("type") != "verify_email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    email = stored["email"]
    user = await _user_svc.collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    await _user_svc.update(user["uid"], {"is_email_verified": True, "updated_at": utc_now()})
    await _reset_svc.delete(token)
    
    logger.info(f"Email verified: {email}")
    return MessageResponse(message="Email verified successfully. You can now log in.")


# ── Get Current Profile ───────────────────────────────────────────────────────
@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Return profile of authenticated user."""
    return UserProfileResponse(**current_user)


# ── Update Profile ────────────────────────────────────────────────────────────
@router.put("/me", response_model=MessageResponse)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update profile fields."""
    uid = current_user["uid"]
    update_data = sanitize_dict({
        **payload.model_dump(exclude_none=True),
        "updated_at": utc_now(),
    })
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")
    
    await _user_svc.update(uid, update_data)
    logger.info(f"Profile updated for uid={uid}")
    return MessageResponse(message="Profile updated successfully.")


# ── Farm Management CRUD ──────────────────────────────────────────────────────
@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def add_farm(
    payload: FarmCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a new farm location for the authenticated user."""
    uid = current_user["uid"]
    farm_id = generate_id("farm")
    now = utc_now()

    farm_doc = sanitize_dict({
        "farm_id": farm_id,
        "user_id": uid,
        "name": payload.name,
        "latitude": payload.location.latitude,
        "longitude": payload.location.longitude,
        "area_acres": payload.area_acres,
        "crop_types": payload.crop_types,
        "soil_type": payload.soil_type,
        "district": payload.district,
        "state": payload.state,
        "irrigation_type": payload.irrigation_type,
        "notes": payload.notes,
        "total_predictions": 0,
        "created_at": now,
        "updated_at": now,
    })

    await _farm_svc.create(farm_id, farm_doc)

    # Update user's farm list
    current_farm_ids = current_user.get("farm_ids", [])
    current_farm_ids.append(farm_id)
    await _user_svc.update(uid, {"farm_ids": current_farm_ids, "updated_at": now})

    logger.info(f"Farm '{payload.name}' added for uid={uid}, farm_id={farm_id}")
    return FarmResponse(**farm_doc)


@router.get("/farms")
async def get_my_farms(current_user: dict = Depends(get_current_user)):
    """Return all farms belonging to the authenticated user."""
    uid = current_user["uid"]
    farms = await _farm_svc.query("user_id", "==", uid, order_by="created_at", limit=50)
    return {"farms": farms, "total": len(farms)}


@router.put("/farms/{farm_id}", response_model=FarmResponse)
async def update_farm(
    farm_id: str,
    payload: FarmUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update details of an existing farm."""
    farm = await _farm_svc.get(farm_id)
    if not farm or farm.get("user_id") != current_user["uid"]:
        raise HTTPException(status_code=404, detail="Farm not found.")

    update_data = payload.model_dump(exclude_none=True)
    if "location" in update_data and update_data["location"]:
        loc = update_data.pop("location")
        update_data["latitude"] = loc["latitude"]
        update_data["longitude"] = loc["longitude"]

    update_data["updated_at"] = utc_now()
    await _farm_svc.update(farm_id, update_data)
    
    updated_farm = await _farm_svc.get(farm_id)
    return FarmResponse(**updated_farm)


@router.delete("/farms/{farm_id}", response_model=MessageResponse)
async def delete_farm(
    farm_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a farm."""
    uid = current_user["uid"]
    farm = await _farm_svc.get(farm_id)
    if not farm or farm.get("user_id") != uid:
        raise HTTPException(status_code=404, detail="Farm not found.")

    await _farm_svc.delete(farm_id)

    # Remove farm_id from user profile
    farm_ids = current_user.get("farm_ids", [])
    if farm_id in farm_ids:
        farm_ids.remove(farm_id)
        await _user_svc.update(uid, {"farm_ids": farm_ids, "updated_at": utc_now()})

    logger.info(f"Farm deleted: farm_id={farm_id} for user={uid}")
    return MessageResponse(message="Farm deleted successfully.")


# ── Change Password (Authenticated) ──────────────────────────────────────────
@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change password for an authenticated user by verifying the current password first."""
    uid = current_user["uid"]
    stored_hash = current_user.get("hashed_password", "")

    if not AuthService.verify_password(payload.current_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    new_hash = AuthService.hash_password(payload.new_password)
    await _user_svc.update(uid, {"hashed_password": new_hash, "updated_at": utc_now()})
    logger.info(f"Password changed for uid={uid}")
    return MessageResponse(message="Password changed successfully.")

