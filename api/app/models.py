import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass



class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    transaction_hash: Mapped[str] = mapped_column(String(64), nullable = False, unique = True, index = True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    category: Mapped[str] = mapped_column(String(64), nullable=False, default="Uncategorized")
    account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)