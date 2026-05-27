"""SQLAlchemy models -- 8 Phase-1 tables.

Tables:
 1. user
 2. profile
 3. tax_year
 4. income_source
 5. deduction
 6. document
 7. tax_calculation
 8. tax_return
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


# ------ Enum types ------

class FilingStatus(str, PyEnum):
    SINGLE = "single"
    MARRIED_JOINT = "married_joint"
    MARRIED_SEPARATE = "married_separate"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"


class FilingFrequency(str, PyEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class Jurisdiction(str, PyEnum):
    US = "US"
    UK = "UK"


class DocumentStatus(str, PyEnum):
    UPLOADED = "uploaded"
    PARSE_REQUESTED = "parse_requested"
    PARSED = "parsed"
    FAILED = "failed"


class DocumentType(str, PyEnum):
    FORM_W2 = "w2"
    FORM_1099 = "1099"
    FORM_1098 = "1098"
    REIMBURSEMENT_RECEIPT = "reimbursement_receipt"
    OTHER = "other"


class CalculationStatus(str, PyEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class FormType(str, PyEnum):
    ITR_1 = "ITR-1"
    ITR_2 = "ITR-2"
    ITR_3 = "ITR-3"
    ITR_4 = "ITR-4"
    ITR_5 = "ITR-5"
    ITR_6 = "ITR-6"
    ITR_7 = "ITR-7"


class FiledStatus(str, PyEnum):
    DRAFT = "draft"
    FILED = "filed"


# ------ 1. USER ------
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    profile: Mapped["Profile | None"] = relationship(back_populates="user", uselist=False)
    income_sources: Mapped[list["IncomeSource"]] = relationship(back_populates="user")
    deductions: Mapped[list["Deduction"]] = relationship(back_populates="user")
    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    calculations: Mapped[list["TaxCalculation"]] = relationship(back_populates="user")
    returns: Mapped[list["TaxReturn"]] = relationship(back_populates="user")


# ------ 2. PROFILE ------
class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), unique=True, index=True)
    jurisdiction: Mapped[Jurisdiction] = mapped_column(Enum(Jurisdiction))
    filing_status: Mapped[FilingStatus] = mapped_column(Enum(FilingStatus))
    financial_year: Mapped[int] = mapped_column(Integer, index=True)
    frequency: Mapped[FilingFrequency] = mapped_column(Enum(FilingFrequency))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")


# ------ 3. TAX_YEAR ------
class TaxYear(Base):
    """Supported financial years and their rule-pack metadata."""

    __tablename__ = "tax_year"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    jurisdiction: Mapped[Jurisdiction] = mapped_column(Enum(Jurisdiction))
    rule_pack_version: Mapped[str] = mapped_column(String(50))
    brackets: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True)



# ------ 4. INCOME_SOURCE ------
class IncomeSource(Base):
    __tablename__ = "income_source"
    __table_args__ = (
        UniqueConstraint("user_id", "financial_year", "form_type", "source_label", name="uix_income"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    financial_year: Mapped[int] = mapped_column(Integer, index=True)
    form_type: Mapped[str] = mapped_column(String(50))  # w2, 1099-misc, ...
    source_label: Mapped[str] = mapped_column(String(200))  # employer name, platform
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="income_sources")


# ------ 5. DEDUCTION ------
class Deduction(Base):
    __tablename__ = "deduction"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    financial_year: Mapped[int] = mapped_column(Integer, index=True)
    category: Mapped[str] = mapped_column(String(100))  # charitable, mortgage_interest, ...
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_deduction_amount"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="deductions")


# ------ 6. DOCUMENT ------
class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    storage_filename: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )
    extracted_json: Mapped[dict] = mapped_column(JSON, default=dict)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")


# ------ 7. TAX_CALCULATION ------
class TaxCalculation(Base):
    __tablename__ = "tax_calculation"
    __table_args__ = (
        CheckConstraint("length(json(steps)) <= 65536", name="chk_calc_steps_size"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    financial_year: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[CalculationStatus] = mapped_column(
        Enum(CalculationStatus), default=CalculationStatus.DRAFT
    )
    inputs_snapshot: Mapped[dict] = mapped_column(JSON)
    steps: Mapped[list[dict]] = mapped_column(JSON)  # ordered calculation steps
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="calculations")


# ------ 8. TAX_RETURN ------
class TaxReturn(Base):
    __tablename__ = "tax_return"
    __table_args__ = (
        UniqueConstraint("user_id", "financial_year", name="uix_return_user_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    financial_year: Mapped[int] = mapped_column(Integer, index=True)
    form: Mapped[FormType] = mapped_column(Enum(FormType))
    pdf_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filed_status: Mapped[FiledStatus] = mapped_column(Enum(FiledStatus), default=FiledStatus.DRAFT)
    filed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="returns")
