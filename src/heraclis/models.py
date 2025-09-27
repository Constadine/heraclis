#!/usr/bin/env python3
"""
SQLAlchemy models for the Heraclis project using SQLAlchemy 2.0 style with mapped_column and type hints.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Association table for many-to-many relationship between Exercise and Tag
exercise_tags = Table(
    "exercise_tags",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    exercise_name: Mapped[str] = mapped_column(String, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<Workout(id={self.id}, exercise_name={self.exercise_name}, reps={self.reps}, set_number={self.set_number})>"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Many-to-many relationship with Tag
    tags: Mapped[list[Tag]] = relationship(
        "Tag", secondary=exercise_tags, back_populates="exercises"
    )

    # One-to-many relationship with Goal
    goals: Mapped[list[Goal]] = relationship("Goal", back_populates="exercise")

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, name={self.name})>"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String, default="#3498db")

    # Back-reference for many-to-many relationship
    exercises: Mapped[list[Exercise]] = relationship(
        "Exercise", secondary=exercise_tags, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id"), nullable=False
    )
    daily_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weekly_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationship to Exercise
    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="goals")

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, exercise_id={self.exercise_id}, daily_target={self.daily_target}, weekly_target={self.weekly_target})>"


class TodaysSchedule(Base):
    __tablename__ = "todays_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exercises.id"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_reps: Mapped[int | None] = mapped_column(Integer)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Optionally, relationship to Exercise
    exercise: Mapped[Exercise] = relationship("Exercise")

    def __repr__(self) -> str:
        return f"<TodaysSchedule(id={self.id}, exercise_id={self.exercise_id}, order_index={self.order_index})>"
