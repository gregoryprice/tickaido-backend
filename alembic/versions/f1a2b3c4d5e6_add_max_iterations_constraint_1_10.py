"""Add max_iterations constraint (1-10)

Revision ID: f1a2b3c4d5e6
Revises: efdfb7615061
Create Date: 2025-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CHECK constraint for max_iterations to be between 1 and 10
    op.create_check_constraint(
        'ck_agents_max_iterations_range',
        'agents', 
        'max_iterations >= 1 AND max_iterations <= 10'
    )


def downgrade() -> None:
    # Remove the CHECK constraint
    op.drop_constraint('ck_agents_max_iterations_range', 'agents', type_='check')