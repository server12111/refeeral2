"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("stars_balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("referrals_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referrer_id", sa.BigInteger(), nullable=True),
        sa.Column("referral_reward_given", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sponsors_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tasks_completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_bonus_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slots_777_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("darts_bullseye_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["referrer_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_type", sa.String(32), nullable=False),
        sa.Column("bet", sa.Numeric(14, 2), nullable=False),
        sa.Column("result", sa.String(8), nullable=False),
        sa.Column("payout", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("played_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "duels",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("joiner_id", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="waiting"),
        sa.Column("creator_roll", sa.Integer(), nullable=True),
        sa.Column("joiner_roll", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["creator_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["joiner_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lotteries",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("tickets_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_collected", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("prize_pool", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("ticket_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("ticket_limit", sa.Integer(), nullable=True),
        sa.Column("ref_required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("end_type", sa.String(16), nullable=False, server_default="tickets"),
        sa.Column("end_value", sa.Numeric(14, 2), nullable=False, server_default="100"),
        sa.Column("winner_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("drawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lottery_tickets",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("lottery_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("bought_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["lottery_id"], ["lotteries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "withdrawals",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("channel_message_id", sa.Integer(), nullable=True),
        sa.Column("admin_message_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("reward_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "promo_uses",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("code_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["code_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("task_type", sa.String(32), nullable=False, server_default="external_url"),
        sa.Column("reward", sa.Numeric(14, 2), nullable=False, server_default="0.3"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_completions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "task_completions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "content_items",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("photo_file_id", sa.String(256), nullable=True),
        sa.Column("video_file_id", sa.String(256), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("content_items")
    op.drop_table("task_completions")
    op.drop_table("tasks")
    op.drop_table("promo_uses")
    op.drop_table("promo_codes")
    op.drop_table("withdrawals")
    op.drop_table("lottery_tickets")
    op.drop_table("lotteries")
    op.drop_table("duels")
    op.drop_table("game_sessions")
    op.drop_table("bot_settings")
    op.drop_table("users")
