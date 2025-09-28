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
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


NOW = datetime.now()

# Association table for many-to-many relationship between Exercise and Tag
exercise_tags = Table(
    "exercise_tags",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String)
    # New relationships for user-specific workouts and goals
    workouts: Mapped[list["Workout"]] = relationship("Workout", back_populates="user")
    goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=NOW)
    exercise_name: Mapped[str] = mapped_column(String)
    reps: Mapped[int] = mapped_column(Integer)
    set_number: Mapped[int] = mapped_column(Integer, default=1)
    # New user-specific column and relationship
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped[User] = relationship("User", back_populates="workouts")

    def __repr__(self) -> str:
        return f"<Workout(id={self.id}, exercise_name={self.exercise_name}, reps={self.reps}, set_number={self.set_number})>"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
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
    name: Mapped[str] = mapped_column(String, unique=True)
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
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"))
    daily_target: Mapped[int] = mapped_column(Integer, default=0)
    weekly_target: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=NOW)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=NOW, onupdate=NOW)
    # New user-specific column and relationship
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped[User] = relationship("User", back_populates="goals")
    # Relationship to Exercise remains unchanged
    exercise: Mapped[Exercise] = relationship("Exercise", back_populates="goals")

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, exercise_id={self.exercise_id}, daily_target={self.daily_target}, weekly_target={self.weekly_target})>"


class TodaysSchedule(Base):
    __tablename__ = "todays_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    suggested_reps: Mapped[int | None] = mapped_column(Integer)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=NOW)

    # Optionally, relationship to Exercise
    exercise: Mapped[Exercise] = relationship("Exercise")

    def __repr__(self) -> str:
        return f"<TodaysSchedule(id={self.id}, exercise_id={self.exercise_id}, order_index={self.order_index})>"


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite:///heraclis.db")

    def init_default_tags():
        with Session(engine) as session:
            # Create default Tag object entities
            tags = [
                Tag(name="Chest", color="#e74c3c"),
                Tag(name="Front Delts", color="#f39c12"),
                Tag(name="Triceps", color="#DECE4E"),
                Tag(name="Core", color="#2ecc71"),
                Tag(name="Glutes", color="#1abc9c"),
                Tag(name="Quads", color="#68D9CD"),
                Tag(name="Hamstrings", color="#16a085"),
                Tag(name="Calves", color="#27ae60"),
                Tag(name="Back", color="#2980b9"),
                Tag(name="Biceps", color="#8e44ad"),
            ]
            session.add_all(tags)
            session.commit()
        return tags

    def init_default_exercises():
        with Session(engine) as session:
            # Get tags
            tags = session.scalars(select(Tag)).all()

            # Create Exercise objects upfront
            exercises = [
                Exercise(
                    name="Pushups",
                    description="Upper body strength exercise",
                ),
                Exercise(
                    name="Squats",
                    description="Lower body strength exercise",
                ),
                Exercise(
                    name="Lunges",
                    description="Lower body strength exercise",
                ),
                Exercise(
                    name="Squat & Lunge",
                    description="Lower body strength exercise",
                ),
                Exercise(
                    name="Planks",
                    description="Core strength exercise",
                ),
                Exercise(
                    name="Dead Bugs",
                    description="Core strength exercise",
                ),
                Exercise(
                    name="Glute Bridges",
                    description="Lower body strength exercise",
                ),
                Exercise(
                    name="Crunches",
                    description="Core strength exercise",
                ),
            ]

            # Define exercise-to-tag relationships
            tags_dict = {tag.name: tag for tag in tags}
            exercise_to_tagnames = {
                "Pushups": ["Chest", "Front Delts", "Triceps", "Biceps"],
                "Squats": ["Quads", "Glutes", "Calves", "Back"],
                "Lunges": ["Quads", "Glutes"],
                "Squat & Lunge": ["Quads", "Glutes"],
                "Planks": ["Core"],
                "Dead Bugs": ["Core"],
                "Glute Bridges": ["Glutes", "Hamstrings"],
                "Crunches": ["Core"],
            }
            for ex in exercises:
                ex.tags = [
                    tags_dict[tag_name]
                    for tag_name in exercise_to_tagnames.get(ex.name, [])
                ]

            session.add_all(exercises)
            session.commit()

    def main():
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        init_default_tags()
        init_default_exercises()
        print("Database created successfully with initial tags and exercises")

    main()
