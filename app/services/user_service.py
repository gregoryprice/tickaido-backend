#!/usr/bin/env python3
"""
User Service - Business logic for user management, authentication, and permissions
"""

import secrets
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*crypt.*")
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.models.user import User, UserRole
from app.models.ticket import Ticket
from app.schemas.user import (
    UserCreateRequest,
    UserUpdateRequest,
    UserPasswordChangeRequest,
    UserAPIKeyRequest,
    UserLoginRequest,
    UserPrivateResponse,
    UserLoginResponse,
    UserAPIKeyResponse,
    UserSearchParams,
    UserSortParams
)
from app.config.settings import get_settings


class UserService:
    """Service class for user operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = self.settings.secret_key
        self.algorithm = self.settings.algorithm
        self.algorithms = self.settings.algorithms
        self.access_token_expire_minutes = self.settings.access_token_expire_minutes
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=self.algorithms)
            return payload
        except JWTError:
            return None
    
    async def create_user(
        self,
        db: AsyncSession,
        user_request: UserCreateRequest
    ) -> User:
        """
        Create a new user
        
        Args:
            db: Database session
            user_request: User creation request data
            
        Returns:
            Created user record
        """
        # Check if email already exists
        existing_user = await self.get_user_by_email(db, user_request.email)
        if existing_user:
            raise ValueError(f"User with email {user_request.email} already exists")
        
        # Hash password
        hashed_password = self._hash_password(user_request.password)
        
        # Create user record
        db_user = User(
            email=user_request.email,
            password_hash=hashed_password,
            full_name=user_request.full_name,
            role=user_request.role or UserRole.USER,
            is_active=True,
            is_verified=False,  # Email verification required
            phone=user_request.phone,
            company=user_request.company,
            department=user_request.department,
            timezone=user_request.timezone or "UTC",
            language=user_request.language or "en",
            preferences=user_request.preferences or {},
            metadata=user_request.metadata or {}
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
    
    async def get_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        include_stats: bool = False
    ) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User ID
            include_stats: Whether to include user statistics
            
        Returns:
            User record if found
        """
        query = select(User).where(
            and_(User.id == user_id, User.is_deleted == False)
        )
        
        if include_stats:
            query = query.options(selectinload(User.tickets))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[User]:
        """
        Get user by email address
        
        Args:
            db: Database session
            email: User email address
            
        Returns:
            User record if found
        """
        query = select(User).where(
            and_(User.email == email, User.is_deleted == False)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        search_params: Optional[UserSearchParams] = None,
        sort_params: Optional[UserSortParams] = None,
        requesting_user_id: Optional[UUID] = None
    ) -> Tuple[List[User], int]:
        """
        List users with filtering and pagination
        
        Args:
            db: Database session
            offset: Number of records to skip
            limit: Maximum number of records to return
            search_params: Search parameters
            sort_params: Sort parameters
            requesting_user_id: ID of user making the request
            
        Returns:
            Tuple of (users list, total count)
        """
        # Base query
        query = select(User).where(User.is_deleted == False)
        count_query = select(func.count(User.id)).where(User.is_deleted == False)
        
        # Apply filters
        filters = []
        
        if search_params:
            if search_params.email:
                filters.append(User.email.ilike(f"%{search_params.email}%"))
            
            if search_params.full_name:
                filters.append(User.full_name.ilike(f"%{search_params.full_name}%"))
            
            if search_params.role:
                filters.append(User.role == search_params.role)
            
            if search_params.is_active is not None:
                filters.append(User.is_active == search_params.is_active)
            
            if search_params.is_verified is not None:
                filters.append(User.is_verified == search_params.is_verified)
            
            if search_params.company:
                filters.append(User.company.ilike(f"%{search_params.company}%"))
            
            if search_params.department:
                filters.append(User.department.ilike(f"%{search_params.department}%"))
            
            if search_params.created_after:
                filters.append(User.created_at >= search_params.created_after)
            
            if search_params.created_before:
                filters.append(User.created_at <= search_params.created_before)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        if sort_params:
            sort_field = getattr(User, sort_params.sort_by, User.created_at)
            if sort_params.sort_order == "desc":
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(User.created_at.desc())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute queries
        users_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        users = users_result.scalars().all()
        total = count_result.scalar()
        
        return list(users), total
    
    async def update_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        update_request: UserUpdateRequest,
        requesting_user_id: UUID
    ) -> Optional[User]:
        """
        Update user information
        
        Args:
            db: Database session
            user_id: User ID to update
            update_request: Update request data
            requesting_user_id: ID of user making the request
            
        Returns:
            Updated user record if found
        """
        db_user = await self.get_user(db, user_id)
        if not db_user:
            return None
        
        # Check permissions (self or admin)
        if user_id != requesting_user_id:
            requesting_user = await self.get_user(db, requesting_user_id)
            if not requesting_user or requesting_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise PermissionError("Insufficient permissions to update user")
        
        # Update fields
        update_data = update_request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_user, field):
                setattr(db_user, field, value)
        
        db_user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
    
    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        password_request: UserPasswordChangeRequest,
        requesting_user_id: UUID
    ) -> bool:
        """
        Change user password
        
        Args:
            db: Database session
            user_id: User ID
            password_request: Password change request
            requesting_user_id: ID of user making the request
            
        Returns:
            True if password changed successfully
        """
        db_user = await self.get_user(db, user_id)
        if not db_user:
            return False
        
        # Check permissions and current password
        if user_id == requesting_user_id:
            # User changing their own password - verify current password
            if not self._verify_password(password_request.current_password, db_user.password_hash):
                raise ValueError("Current password is incorrect")
        else:
            # Admin changing user password
            requesting_user = await self.get_user(db, requesting_user_id)
            if not requesting_user or requesting_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise PermissionError("Insufficient permissions to change password")
        
        # Update password
        db_user.password_hash = self._hash_password(password_request.new_password)
        db_user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        return True
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        login_request: UserLoginRequest
    ) -> Optional[UserLoginResponse]:
        """
        Authenticate user and generate access token
        
        Args:
            db: Database session
            login_request: Login request data
            
        Returns:
            Login response with token if successful
        """
        # Get user by email
        db_user = await self.get_user_by_email(db, login_request.email)
        if not db_user:
            return None
        
        # Verify password
        if not self._verify_password(login_request.password, db_user.password_hash):
            return None
        
        # Check if user is active
        if not db_user.is_active:
            raise ValueError("User account is deactivated")
        
        # Create access token
        token_data = {"sub": str(db_user.id), "email": db_user.email, "role": db_user.role.value}
        access_token = self._create_access_token(token_data)
        
        # Update last login
        db_user.last_login_at = datetime.now(timezone.utc)
        db_user.login_count = (db_user.login_count or 0) + 1
        await db.commit()
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=UserPrivateResponse.model_validate(db_user)
        )
    
    async def verify_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[User]:
        """
        Verify access token and get user
        
        Args:
            db: Database session
            token: Access token
            
        Returns:
            User record if token is valid
        """
        payload = self._verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        return await self.get_user(db, UUID(user_id))
    
    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        requesting_user_id: UUID
    ) -> bool:
        """
        Deactivate user account
        
        Args:
            db: Database session
            user_id: User ID to deactivate
            requesting_user_id: ID of user making the request
            
        Returns:
            True if deactivated successfully
        """
        db_user = await self.get_user(db, user_id)
        if not db_user:
            return False
        
        # Check permissions
        requesting_user = await self.get_user(db, requesting_user_id)
        if not requesting_user or requesting_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise PermissionError("Insufficient permissions to deactivate user")
        
        db_user.is_active = False
        db_user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        return True
    
    async def delete_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        requesting_user_id: UUID,
        hard_delete: bool = False
    ) -> bool:
        """
        Delete user account
        
        Args:
            db: Database session
            user_id: User ID to delete
            requesting_user_id: ID of user making the request
            hard_delete: Whether to permanently delete
            
        Returns:
            True if deleted successfully
        """
        db_user = await self.get_user(db, user_id)
        if not db_user:
            return False
        
        # Check permissions
        requesting_user = await self.get_user(db, requesting_user_id)
        if not requesting_user or requesting_user.role != UserRole.SUPER_ADMIN:
            raise PermissionError("Only super admins can delete users")
        
        if hard_delete:
            await db.delete(db_user)
        else:
            db_user.soft_delete()
        
        await db.commit()
        return True
    
    async def generate_api_key(
        self,
        db: AsyncSession,
        user_id: UUID,
        api_key_request: UserAPIKeyRequest,
        requesting_user_id: UUID
    ) -> Optional[UserAPIKeyResponse]:
        """
        Generate API key for user
        
        Args:
            db: Database session
            user_id: User ID
            api_key_request: API key request data
            requesting_user_id: ID of user making the request
            
        Returns:
            API key response if successful
        """
        db_user = await self.get_user(db, user_id)
        if not db_user:
            return None
        
        # Check permissions
        if user_id != requesting_user_id:
            requesting_user = await self.get_user(db, requesting_user_id)
            if not requesting_user or requesting_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                raise PermissionError("Insufficient permissions to generate API key")
        
        # Generate API key
        api_key = secrets.token_urlsafe(32)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Store API key info (in a real implementation, you'd have an api_keys table)
        api_key_data = {
            "name": api_key_request.name,
            "permissions": api_key_request.permissions or [],
            "expires_at": api_key_request.expires_at,
            "created_at": datetime.now(timezone.utc),
            "hash": api_key_hash
        }
        
        # Add to user's API keys (storing in metadata for now)
        if not db_user.metadata:
            db_user.metadata = {}
        if "api_keys" not in db_user.metadata:
            db_user.metadata["api_keys"] = []
        
        db_user.metadata["api_keys"].append(api_key_data)
        db_user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return UserAPIKeyResponse(
            api_key=api_key,
            name=api_key_request.name,
            permissions=api_key_request.permissions or [],
            expires_at=api_key_request.expires_at,
            created_at=api_key_data["created_at"]
        )
    
    async def get_user_stats(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get user statistics
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User statistics
        """
        db_user = await self.get_user(db, user_id, include_stats=True)
        if not db_user:
            return {}
        
        # Count user's tickets by status
        ticket_query = select(func.count(Ticket.id)).where(
            and_(
                Ticket.created_by == user_id,
                Ticket.is_deleted == False
            )
        )
        total_tickets = await db.execute(ticket_query)
        
        return {
            "total_tickets": total_tickets.scalar(),
            "login_count": db_user.login_count or 0,
            "last_login_at": db_user.last_login_at,
            "account_age_days": db_user.age_in_days,
            "is_verified": db_user.is_verified,
            "is_active": db_user.is_active,
            "role": db_user.role.value
        }