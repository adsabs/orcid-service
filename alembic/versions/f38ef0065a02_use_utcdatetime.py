"""use_utcdatetime

Revision ID: f38ef0065a02
Revises: 07c3fe07309c
Create Date: 2018-11-07 15:24:02.414626

"""

# revision identifiers, used by Alembic.
revision = 'f38ef0065a02'
down_revision = '07c3fe07309c'

from alembic import op
import sqlalchemy as sa
from adsmutils import UTCDateTime, get_date
import datetime
                               


def upgrade():
    #with app.app_context() as c:
    #   db.session.add(Model())
    #   db.session.commit()

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name='created',
            type_=UTCDateTime)
        batch_op.alter_column(
            column_name='updated',
            type_=UTCDateTime)


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            column_name='created',
            type_=sa.DateTime())
        batch_op.alter_column(
            column_name='updated',
            type_=sa.DateTime())
