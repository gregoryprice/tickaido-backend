#!/usr/bin/env python3
"""
Backfill script to populate organizations.domain from member emails.

Strategy:
- For each organization with domain IS NULL and not deleted, gather active users' email domains
- Choose the most common domain (case-insensitive)
- Set organization.domain to that domain (lowercased)

Usage:
  poetry run python scripts/backfill_org_domains.py [--dry-run]
"""

import asyncio
import sys
import logging
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User


logger = logging.getLogger("backfill_org_domains")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def infer_domain_for_org(session: AsyncSession, organization_id) -> Optional[str]:
    """Infer the most common email domain among active users of an organization."""
    # SELECT lower(split_part(email,'@',2)) AS domain, COUNT(*)
    # FROM users WHERE organization_id=:org_id AND is_active=true
    # GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 1
    domain_expr = func.lower(func.split_part(User.email, '@', 2))
    q = (
        select(domain_expr.label("domain"), func.count().label("cnt"))
        .where(and_(User.organization_id == organization_id, User.is_active == True))
        .group_by(domain_expr)
        .order_by(func.count().desc())
        .limit(1)
    )
    result = await session.execute(q)
    row = result.first()
    if not row:
        return None
    return (row[0] or "").strip().lower() or None


async def backfill(dry_run: bool = False) -> int:
    updated = 0
    async with AsyncSessionLocal() as session:
        # Find organizations with NULL domain and not deleted
        orgs_q = select(Organization).where(
            and_(Organization.domain.is_(None), Organization.is_deleted == False)
        )
        orgs_result = await session.execute(orgs_q)
        orgs = list(orgs_result.scalars().all())

        if not orgs:
            logger.info("No organizations with NULL domain found.")
            return 0

        logger.info(f"Found {len(orgs)} organizations with NULL domain.")

        for org in orgs:
            inferred = await infer_domain_for_org(session, org.id)
            if not inferred:
                logger.info(f"Skipping org {org.id} ('{org.name}') - no active user domains found.")
                continue

            logger.info(f"Org {org.id} ('{org.name}') -> inferred domain: {inferred}")
            if not dry_run:
                org.domain = inferred
                await session.commit()
                await session.refresh(org)
                updated += 1

        logger.info(f"Backfill complete. Updated {updated} organizations.")
    return updated


def parse_args() -> bool:
    return "--dry-run" in sys.argv


if __name__ == "__main__":
    try:
        dry_run_flag = parse_args()
        if dry_run_flag:
            logger.info("Running in DRY-RUN mode. No changes will be persisted.")
        asyncio.run(backfill(dry_run=dry_run_flag))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
    except Exception as exc:
        logger.exception(f"Backfill failed: {exc}")
        sys.exit(1)
    sys.exit(0)



