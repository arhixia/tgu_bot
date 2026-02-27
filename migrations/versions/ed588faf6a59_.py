"""empty message

Revision ID: ed588faf6a59
Revises: 3126ab7cbbee
Create Date: 2026-02-27 16:21:07.382273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed588faf6a59'
down_revision: Union[str, Sequence[str], None] = '3126ab7cbbee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users WITHOUT the group_id FK first
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('TEACHER', 'STUDENT', name='userrole'), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=True),  # no FK yet
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # 2. Create groups (can now reference users)
    op.create_table('groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)

    # 3. Now add the FK from users.group_id → groups.id
    op.create_foreign_key(None, 'users', 'groups', ['group_id'], ['id'])

    # 4. Create themes
    op.create_table('themes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('llm_prompt', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_themes_id'), 'themes', ['id'], unique=False)

    # 5. Create tasks
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('theme_id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.Enum('TRAINING', 'TESTING', name='tasktype'), nullable=False),
        sa.Column('image_url', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)

    # 6. Create answers
    op.create_table('answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('student_response_image', sa.String(), nullable=True),
        sa.Column('llm_verdict', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('CORRECT', 'INCORRECT', 'SKIPPED', 'PENDING', name='answerstatus'), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_answers_id'), 'answers', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_answers_id'), table_name='answers')
    op.drop_table('answers')
    op.drop_index(op.f('ix_tasks_id'), table_name='tasks')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_themes_id'), table_name='themes')
    op.drop_table('themes')
    # Drop the FK before dropping groups
    op.drop_constraint('uq_users_group_id_fkey', 'users', type_='foreignkey')  # adjust constraint name if needed
    op.drop_index(op.f('ix_groups_id'), table_name='groups')
    op.drop_table('groups')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')