"""migrate_user_roles_to_admin_member

Revision ID: db23781d1fd2
Revises: db22781d1fd1
Create Date: 2025-09-26 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'db23781d1fd2'
down_revision = '2ffad472666e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Consolidate user roles to only ADMIN and MEMBER.
    
    This migration uses a simpler approach that works with PostgreSQL enum constraints:
    1. Create new enum with desired values
    2. Map old values to new values during column type conversion
    3. Ensure single-user orgs have admin
    """
    
    # Create a connection to execute raw SQL
    connection = op.get_bind()
    
    # Step 1: Create the new enum with only ADMIN and MEMBER
    op.execute("CREATE TYPE userrole_new AS ENUM ('ADMIN', 'MEMBER')")
    
    # Step 2: Update the column to use the new enum with value mapping
    # This single operation maps all old values to new values:
    # ADMIN -> ADMIN, all others -> MEMBER
    connection.execute(text("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole_new 
        USING CASE 
            WHEN role = 'ADMIN' THEN 'ADMIN'::userrole_new
            ELSE 'MEMBER'::userrole_new
        END
    """))
    
    # Step 3: For organizations with only one user, make that user an ADMIN
    connection.execute(text("""
        WITH orgs_with_single_user AS (
            SELECT organization_id
            FROM users 
            WHERE organization_id IS NOT NULL 
              AND is_active = true 
              AND is_deleted = false
            GROUP BY organization_id
            HAVING COUNT(*) = 1
        )
        UPDATE users 
        SET role = 'ADMIN'
        WHERE organization_id IN (SELECT organization_id FROM orgs_with_single_user)
          AND is_active = true 
          AND is_deleted = false
          AND role = 'MEMBER'
    """))
    
    # Step 4: Drop the old enum and rename the new one
    op.execute("DROP TYPE userrole")
    op.execute("ALTER TYPE userrole_new RENAME TO userrole")
    
    # Step 5: Update the default value to 'MEMBER'
    op.alter_column('users', 'role',
                   existing_type=postgresql.ENUM('ADMIN', 'MEMBER', name='userrole'),
                   server_default='MEMBER')


def downgrade() -> None:
    """
    Downgrade: Restore the original UserRole enum with all values.
    Note: This will set all MEMBER users back to USER role.
    """
    
    # Create the old enum type with all original values (uppercase)
    op.execute("CREATE TYPE userrole_new AS ENUM ('ADMIN', 'MANAGER', 'AGENT', 'USER', 'API_USER')")
    
    # Convert 'MEMBER' back to 'USER' for the downgrade
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE users 
        SET role = 'USER' 
        WHERE role = 'MEMBER'
    """))
    
    # Update the column to use the old enum
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole_new USING role::text::userrole_new")
    
    # Drop the current enum and rename the new one
    op.execute("DROP TYPE userrole")
    op.execute("ALTER TYPE userrole_new RENAME TO userrole")
    
    # Restore the default value to 'USER'
    op.alter_column('users', 'role',
                   existing_type=postgresql.ENUM('ADMIN', 'MANAGER', 'AGENT', 'USER', 'API_USER', name='userrole'),
                   server_default='USER')