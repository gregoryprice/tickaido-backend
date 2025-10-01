#!/usr/bin/env python3
"""
Common Field Mapping Utilities
Shared utilities for mapping internal fields to external integration fields
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class FieldMappingError(Exception):
    """Raised when field mapping fails"""
    pass


class StandardPriority(Enum):
    """Standard priority levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class StandardCategory(Enum):
    """Standard ticket categories"""
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    GENERAL = "general"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USER_ACCESS = "user_access"


class CommonFieldMapper:
    """
    Common utilities for field mapping between internal and external systems
    """
    
    @staticmethod
    def normalize_priority(priority: Optional[str]) -> str:
        """
        Normalize priority to standard format.
        
        Args:
            priority: Input priority string
            
        Returns:
            Standardized priority string
        """
        if not priority:
            return StandardPriority.MEDIUM.value
        
        priority_lower = priority.lower().strip()
        
        # Map common variations
        priority_map = {
            "1": StandardPriority.LOW.value,
            "2": StandardPriority.MEDIUM.value,
            "3": StandardPriority.HIGH.value,
            "4": StandardPriority.URGENT.value,
            "5": StandardPriority.CRITICAL.value,
            "lowest": StandardPriority.LOW.value,
            "minor": StandardPriority.LOW.value,
            "normal": StandardPriority.MEDIUM.value,
            "major": StandardPriority.HIGH.value,
            "blocker": StandardPriority.CRITICAL.value,
            "p1": StandardPriority.CRITICAL.value,
            "p2": StandardPriority.HIGH.value,
            "p3": StandardPriority.MEDIUM.value,
            "p4": StandardPriority.LOW.value,
            "p5": StandardPriority.LOW.value
        }
        
        return priority_map.get(priority_lower, priority_lower)
    
    @staticmethod
    def normalize_category(category: Optional[str]) -> str:
        """
        Normalize category to standard format.
        
        Args:
            category: Input category string
            
        Returns:
            Standardized category string
        """
        if not category:
            return StandardCategory.GENERAL.value
        
        category_lower = category.lower().strip()
        
        # Map common variations
        category_map = {
            "tech": StandardCategory.TECHNICAL.value,
            "technical_issue": StandardCategory.TECHNICAL.value,
            "support": StandardCategory.TECHNICAL.value,
            "bill": StandardCategory.BILLING.value,
            "billing_issue": StandardCategory.BILLING.value,
            "payment": StandardCategory.BILLING.value,
            "invoice": StandardCategory.BILLING.value,
            "enhancement": StandardCategory.FEATURE_REQUEST.value,
            "feature": StandardCategory.FEATURE_REQUEST.value,
            "request": StandardCategory.FEATURE_REQUEST.value,
            "issue": StandardCategory.BUG.value,
            "defect": StandardCategory.BUG.value,
            "error": StandardCategory.BUG.value,
            "problem": StandardCategory.BUG.value,
            "other": StandardCategory.GENERAL.value,
            "misc": StandardCategory.GENERAL.value,
            "question": StandardCategory.GENERAL.value,
            "api": StandardCategory.INTEGRATION.value,
            "integration_issue": StandardCategory.INTEGRATION.value,
            "slow": StandardCategory.PERFORMANCE.value,
            "performance_issue": StandardCategory.PERFORMANCE.value,
            "timeout": StandardCategory.PERFORMANCE.value,
            "security_issue": StandardCategory.SECURITY.value,
            "vulnerability": StandardCategory.SECURITY.value,
            "auth": StandardCategory.USER_ACCESS.value,
            "login": StandardCategory.USER_ACCESS.value,
            "permission": StandardCategory.USER_ACCESS.value,
            "access": StandardCategory.USER_ACCESS.value
        }
        
        return category_map.get(category_lower, category_lower)
    
    @staticmethod
    def build_description_with_metadata(
        description: str,
        custom_fields: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        include_divider: bool = True
    ) -> str:
        """
        Build enhanced description with metadata.
        
        Args:
            description: Base description text
            custom_fields: Additional custom fields to include
            attachments: List of attachment references
            include_divider: Whether to include visual dividers
            
        Returns:
            Enhanced description with metadata
        """
        parts = [description.strip()]
        
        # Add custom fields if provided
        if custom_fields:
            if include_divider:
                parts.append("\n---\n**Additional Information:**")
            else:
                parts.append("\n**Additional Information:**")
            
            for key, value in custom_fields.items():
                if value is not None:
                    # Format field name nicely
                    field_name = key.replace('_', ' ').title()
                    parts.append(f"• **{field_name}:** {value}")
        
        # Add attachment references if provided
        if attachments and len(attachments) > 0:
            if include_divider:
                parts.append("\n---\n**Attachments:**")
            else:
                parts.append("\n**Attachments:**")
            
            for attachment in attachments:
                filename = attachment.get('filename', 'Unknown file')
                parts.append(f"• {filename}")
        
        return "\n".join(parts)
    
    @staticmethod
    def extract_labels_from_fields(
        category: Optional[str] = None,
        priority: Optional[str] = None,
        department: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Extract meaningful labels from ticket fields.
        
        Args:
            category: Ticket category
            priority: Ticket priority
            department: Department/team
            custom_fields: Additional custom fields
            
        Returns:
            List of label strings
        """
        labels = []
        
        # Add category as label
        if category:
            labels.append(f"category:{category.lower()}")
        
        # Add priority as label
        if priority:
            normalized_priority = CommonFieldMapper.normalize_priority(priority)
            labels.append(f"priority:{normalized_priority}")
        
        # Add department as label  
        if department:
            labels.append(f"team:{department.lower().replace(' ', '-')}")
        
        # Extract labels from custom fields
        if custom_fields:
            for key, value in custom_fields.items():
                if value and isinstance(value, str) and len(value.strip()) > 0:
                    # Convert to label format
                    label_key = key.lower().replace('_', '-')
                    label_value = str(value).lower().replace(' ', '-')
                    # Limit label length
                    if len(label_value) <= 50:
                        labels.append(f"{label_key}:{label_value}")
        
        return labels[:10]  # Limit to reasonable number of labels