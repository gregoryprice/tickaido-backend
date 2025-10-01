#!/usr/bin/env python3
"""
Shared integration utilities
Common utilities used across different integration types
"""

from .attachment_service import BaseAttachmentService
from .field_mapping import CommonFieldMapper, StandardCategory, StandardPriority

__all__ = [
    "BaseAttachmentService",
    "CommonFieldMapper", 
    "StandardPriority",
    "StandardCategory"
]
