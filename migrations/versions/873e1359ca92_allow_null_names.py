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
    # Bezpiecznie dodaj kolumnę auth_uuid (jeśli nie istnieje)
    try:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('auth_uuid', sa.String(length=255), nullable=True))
    except Exception:
        # jeśli kolumna już istnieje lub DB nie pozwala, pomijamy
        pass

    # Dostosuj pola first_name/last_name/password_hash
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

    # Operacje na indeksach/constraintach tylko dla DB obsługujących je (np. PostgreSQL)
    if op.get_context().dialect.name != 'sqlite':
        with op.batch_alter_table('generated_plans', schema=None) as batch_op:
            try:
                batch_op.drop_index(batch_op.f('idx_generated_plans_user_id'))
            except Exception:
                pass

        with op.batch_alter_table('users', schema=None) as batch_op:
            try:
                batch_op.drop_index(batch_op.f('idx_users_auth_uuid'))
            except Exception:
                pass
            # Nadaj jawnie nazwę constraintowi
            try:
                batch_op.create_unique_constraint('uq_users_auth_uuid', ['auth_uuid'])
            except Exception:
                pass


def downgrade():
    # Cofnięcie zmian; zachowujemy ostrożność
    if op.get_context().dialect.name != 'sqlite':
        with op.batch_alter_table('users', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('uq_users_auth_uuid', type_='unique')
            except Exception:
                pass
            try:
                batch_op.create_index(batch_op.f('idx_users_auth_uuid'), ['auth_uuid'], unique=False)
            except Exception:
                pass

        with op.batch_alter_table('generated_plans', schema=None) as batch_op:
            try:
                batch_op.create_index(batch_op.f('idx_generated_plans_user_id'), ['user_id'], unique=False)
            except Exception:
                pass

    with op.batch_alter_table('users', schema=None) as batch_op:
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
# ...existing code...