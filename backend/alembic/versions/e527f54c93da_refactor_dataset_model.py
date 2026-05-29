"""refactor dataset model

Revision ID: e527f54c93da
Revises: 40c10dfcadb4
Create Date: 2026-05-29 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e527f54c93da'
down_revision: Union[str, Sequence[str], None] = '40c10dfcadb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('datasets', sa.Column('dataset_id', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('original_filename', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('cleaned_filename', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('storage_url', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('cleaned_storage_url', sa.String(), nullable=True))
    op.add_column('datasets', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('datasets', sa.Column('session_id', sa.String(), nullable=True))
    
    # Create foreign key for user_id
    op.create_foreign_key('fk_datasets_users', 'datasets', 'users', ['user_id'], ['id'])
    
    # Create index for dataset_id
    op.create_index('ix_datasets_dataset_id', 'datasets', ['dataset_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_datasets_dataset_id', table_name='datasets')
    op.drop_constraint('fk_datasets_users', 'datasets', type_='foreignkey')
    op.drop_column('datasets', 'session_id')
    op.drop_column('datasets', 'user_id')
    op.drop_column('datasets', 'cleaned_storage_url')
    op.drop_column('datasets', 'storage_url')
    op.drop_column('datasets', 'cleaned_filename')
    op.drop_column('datasets', 'original_filename')
    op.drop_column('datasets', 'dataset_id')
