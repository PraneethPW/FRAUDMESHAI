"""Add labels, portable trained models and causal-query indexes without changing existing data."""

from alembic import op
import sqlalchemy as sa
from app.models.domain import TransactionLabel, ModelArtifact, PasswordReset

revision = "20260913_0002"
down_revision = "20260827_0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    TransactionLabel.__table__.create(bind, checkfirst=True)
    ModelArtifact.__table__.create(bind, checkfirst=True)
    PasswordReset.__table__.create(bind, checkfirst=True)
    for name, fields in [
        ("ix_tx_workspace_time", ["workspace_id", "occurred_at"]),
        ("ix_tx_workspace_account_time", ["workspace_id", "account_id", "occurred_at"]),
        ("ix_tx_workspace_device_time", ["workspace_id", "device_id", "occurred_at"]),
        ("ix_tx_workspace_ip_time", ["workspace_id", "ip_address", "occurred_at"]),
        ("ix_tx_workspace_merchant_time", ["workspace_id", "merchant_id", "occurred_at"]),
    ]:
        if name not in {i["name"] for i in sa.inspect(bind).get_indexes("transactions")}:
            op.create_index(name, "transactions", fields)


def downgrade():
    for name in [
        "ix_tx_workspace_time",
        "ix_tx_workspace_account_time",
        "ix_tx_workspace_device_time",
        "ix_tx_workspace_ip_time",
        "ix_tx_workspace_merchant_time",
    ]:
        op.drop_index(name, table_name="transactions")
    PasswordReset.__table__.drop(op.get_bind(), checkfirst=True)
    ModelArtifact.__table__.drop(op.get_bind(), checkfirst=True)
    TransactionLabel.__table__.drop(op.get_bind(), checkfirst=True)
