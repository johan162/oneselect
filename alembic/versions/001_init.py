"""Initial database schema

Revision ID: 001_init
Revises: 
Create Date: 2025-12-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_init'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema with all tables."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('role', sa.String(), nullable=True, server_default='user'),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('google_id', sa.String(), nullable=True),
        sa.Column('auth_provider', sa.String(), nullable=True, server_default='local'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('owner_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)
    
    # Create features table
    op.create_table(
        'features',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('complexity_mu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('complexity_sigma', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('value_mu', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('value_sigma', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_features_id'), 'features', ['id'], unique=False)
    op.create_index(op.f('ix_features_name'), 'features', ['name'], unique=False)
    
    # Create comparisons table
    op.create_table(
        'comparisons',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('feature_a_id', sa.String(), nullable=False),
        sa.Column('feature_b_id', sa.String(), nullable=False),
        sa.Column('choice', sa.String(), nullable=False),
        sa.Column('dimension', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['feature_a_id'], ['features.id'], ),
        sa.ForeignKeyConstraint(['feature_b_id'], ['features.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comparisons_id'), 'comparisons', ['id'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f('ix_comparisons_id'), table_name='comparisons')
    op.drop_table('comparisons')
    
    op.drop_index(op.f('ix_features_name'), table_name='features')
    op.drop_index(op.f('ix_features_id'), table_name='features')
    op.drop_table('features')
    
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
    
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
