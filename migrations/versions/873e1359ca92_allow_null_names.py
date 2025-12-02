# ...existing code...
"""allow null names

Revision ID: 873e1359ca92
Revises: 7328198b8781
Create Date: 2025-12-02 19:31:25.261484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '873e1359ca92'
down_revision = '7328198b8781'
branch_labels = None
depends_on = None


def upgrade():
    # Usuń indeks tylko dla DB, które go wspierają (np. PostgreSQL)
    with op.batch_alter_table('generated_plans', schema=None) as batch_op:
        if op.get_context().dialect.name != 'sqlite':
            try:
                batch_op.drop_index(batch_op.f('idx_generated_plans_user_id'))
            except Exception:
                pass

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('first_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.alter_column('last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.String(length=255),
               existing_nullable=False)

        # Operacje na indeksach/constraintach tylko poza SQLite
        if op.get_context().dialect.name != 'sqlite':
            try:
                batch_op.drop_index(batch_op.f('idx_users_auth_uuid'))
            except Exception:
                pass
            # Nadaj nazwę constraintowi — Alembic wymaga nazwy przy tworzeniu/droppingu
            batch_op.create_unique_constraint('uq_users_auth_uuid', ['auth_uuid'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Usuń nazwany constraint tylko jeśli istnieje (poza SQLite)
        if op.get_context().dialect.name != 'sqlite':
            try:
                batch_op.drop_constraint('uq_users_auth_uuid', type_='unique')
            except Exception:
                pass
            batch_op.create_index(batch_op.f('idx_users_auth_uuid'), ['auth_uuid'], unique=False)

        batch_op.alter_column('password_hash',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=128),
               existing_nullable=False)
        batch_op.alter_column('last_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        batch_op.alter_column('first_name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)

    with op.batch_alter_table('generated_plans', schema=None) as batch_op:
        if op.get_context().dialect.name != 'sqlite':
            try:
                batch_op.create_index(batch_op.f('idx_generated_plans_user_id'), ['user_id'], unique=False)
            except Exception:
                pass
# ...existing code...