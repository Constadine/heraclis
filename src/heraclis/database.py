#!/usr/bin/env python3
"""
Database module for home workout logging app.
Handles SQLite database operations for workouts and exercises.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class WorkoutDB:
    def __init__(self, db_path: str = "workouts.db"):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the database and tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create workouts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    exercise_name TEXT NOT NULL,
                    reps INTEGER NOT NULL,
                    set_number INTEGER DEFAULT 1
                )
            """)
            
            # Create exercises table for configurable exercises
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT
                )
            """)
            
            # Create tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#3498db'
                )
            """)
            
            # Create exercise_tags junction table for many-to-many relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercise_tags (
                    exercise_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (exercise_id, tag_id),
                    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            # Create goals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id INTEGER NOT NULL,
                    daily_target INTEGER NOT NULL DEFAULT 0,
                    weekly_target INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
                )
            """)
            
            # Create todays_schedule table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todays_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id INTEGER NOT NULL,
                    order_index INTEGER NOT NULL,
                    suggested_reps INTEGER,
                    is_completed BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (exercise_id) REFERENCES exercises (id) ON DELETE CASCADE
                )
            """)
            
            # Insert default exercises if table is empty
            cursor.execute("SELECT COUNT(*) FROM exercises")
            if cursor.fetchone()[0] == 0:
                default_exercises = [
                    ("Pushups", "Upper body strength exercise"),
                    ("Squats", "Lower body strength exercise"),
                    ("Lunges", "Lower body strength exercise"),
                    ("Squat & Lunge", "Lower body strength exercise"),
                    ("Planks", "Core strength exercise"),
                    ("Dead Bugs", "Core strength exercise"),
                    ("Glute Bridges", "Lower body strength exercise"),
                    ("Crunches", "Core strength exercise")
                ]
                cursor.executemany(
                    "INSERT INTO exercises (name, description) VALUES (?, ?)",
                    default_exercises
                )
            
            
            # Insert default tags if table is empty
            cursor.execute("SELECT COUNT(*) FROM tags")
            if cursor.fetchone()[0] == 0:
                default_tags = [
                    ("Chest", "#e74c3c"),
                    ("Front Delts", "#f39c12"),
                    ("Triceps", "#DECE4E"),
                    ("Core", "#2ecc71"),
                    ("Glutes", "#1abc9c"),
                    ("Quads", "#68D9CD"),
                    ("Hamstrings", "#16a085"),
                    ("Calves", "#27ae60"),
                    ("Back", "#2980b9"),
                    ("Biceps", "#8e44ad")
                ]
                cursor.executemany(
                    "INSERT INTO tags (name, color) VALUES (?, ?)",
                    default_tags
                )
            
            # Set up default exercise-tag relationships
            self._setup_default_exercise_tags(cursor)
            
            # Set up default goals
            self._setup_default_goals(cursor)
            
            conn.commit()
    
    def _setup_default_exercise_tags(self, cursor):
        """Set up default exercise-tag relationships."""
        # Get exercise IDs
        cursor.execute("SELECT id, name FROM exercises")
        exercises = {name: id for id, name in cursor.fetchall()}
        
        # Get tag IDs
        cursor.execute("SELECT id, name FROM tags")
        tags = {name: id for id, name in cursor.fetchall()}
        
        # Define exercise-tag relationships
        exercise_tag_relationships = [
            ("Pushups", ["Chest", "Front Delts", "Triceps"]),
            ("Squats", ["Quads", "Glutes"]),
            ("Squat & Lunge", ["Quads", "Glutes"]),
            ("Planks", ["Core"]),
            ("Dead Bugs", ["Core"]),
            ("Glute Bridges", ["Glutes", "Hamstrings"]),
            ("Lunges", ["Quads", "Glutes"]),
            ("Crunches", ["Core"])
        ]
        
        # Insert relationships
        for exercise_name, tag_names in exercise_tag_relationships:
            if exercise_name in exercises:
                exercise_id = exercises[exercise_name]
                for tag_name in tag_names:
                    if tag_name in tags:
                        tag_id = tags[tag_name]
                        cursor.execute("""
                            INSERT OR IGNORE INTO exercise_tags (exercise_id, tag_id)
                            VALUES (?, ?)
                        """, (exercise_id, tag_id))
    
    def _setup_default_goals(self, cursor):
        """Set up default goals for exercises."""
        # Get exercise IDs
        cursor.execute("SELECT id, name FROM exercises")
        exercises = {name: id for id, name in cursor.fetchall()}
        
        # Define default goals for each exercise
        default_goals = [
            ("Pushups", 50, 300),
            ("Squats", 50, 200),
            ("Squat & Lunge", 20, 140),
            ("Planks", 3, 15),
            ("Dead Bugs", 60, 180),
            ("Glute Bridges", 30, 200),
            ("Lunges", 60, 140),
            ("Crunches", 50, 300),
        ]
        
        # Insert default goals
        for exercise_name, daily_target, weekly_target in default_goals:
            if exercise_name in exercises:
                exercise_id = exercises[exercise_name]
                cursor.execute("""
                    INSERT OR IGNORE INTO goals (exercise_id, daily_target, weekly_target)
                    VALUES (?, ?, ?)
                """, (exercise_id, daily_target, weekly_target))
    
    def add_workout(self, exercise_name: str, reps: int, set_number: int = 1) -> bool:
        """Add a new workout entry to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Use local timezone instead of UTC
                local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    INSERT INTO workouts (exercise_name, reps, set_number, date)
                    VALUES (?, ?, ?, ?)
                """, (exercise_name, reps, set_number, local_time))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error adding workout: {e}")
            return False
    
    def get_exercises(self) -> List[Dict]:
        """Get all available exercises with their tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.name, e.description, 
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM exercises e
                LEFT JOIN exercise_tags et ON e.id = et.exercise_id
                LEFT JOIN tags t ON et.tag_id = t.id
                GROUP BY e.id, e.name, e.description
                ORDER BY e.id
            """)
            exercises = []
            for row in cursor.fetchall():
                exercise = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "tags": []
                }
                if row[3]:  # if tags exist
                    tag_names = row[3].split(',')
                    tag_colors = row[4].split(',') if row[4] else []
                    exercise["tags"] = [
                        {"name": name, "color": color} 
                        for name, color in zip(tag_names, tag_colors)
                    ]
                exercises.append(exercise)
            return exercises
    
    def add_exercise(self, name: str, description: str = "") -> bool:
        """Add a new exercise to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO exercises (name, description) VALUES (?, ?)", (name, description))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print(f"Exercise '{name}' already exists!")
            return False
        except sqlite3.Error as e:
            print(f"Error adding exercise: {e}")
            return False
    
    def get_recent_workouts(self, days: int = 7) -> List[Dict]:
        """Get recent workouts from the last N days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Use local timezone for date comparison
            local_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT date, exercise_name, reps, set_number
                FROM workouts
                WHERE date >= datetime(?, '-{} days')
                ORDER BY date DESC
            """.format(days), (local_date,))
            return [{"date": row[0], "exercise_name": row[1], "reps": row[2], "set_number": row[3]} 
                   for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get workout statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total reps today (using local timezone)
            today_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT SUM(reps) FROM workouts
                WHERE date >= ?
            """, (today_date,))
            today_reps = cursor.fetchone()[0]
            
            # Total reps this week (using local timezone)
            week_ago = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT SUM(reps) FROM workouts
                WHERE date >= datetime(?, '-7 days')
            """, (week_ago,))
            week_reps = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT date(date)) as total_days
                FROM workouts
            """)
            total_days = cursor.fetchone()[0]

            # First day of the program
            cursor.execute("""
                SELECT MIN(date) as first_day
                FROM workouts
            """)
            first_day = cursor.fetchone()[0]

            # Total reps per exercise
            cursor.execute("""
                SELECT exercise_name, SUM(reps) as total_reps
                FROM workouts
                GROUP BY exercise_name
                ORDER BY total_reps DESC
            """)
            total_reps_per_exercise = [{"exercise_name": row[0], "total_reps": row[1]} for row in cursor.fetchall()]

            # Top exercises this week
            # Use local timezone for weekly stats
            week_ago = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT exercise_name, SUM(reps) as total_reps, COUNT(*) as sets
                FROM workouts
                WHERE date >= datetime(?, '-7 days')
                GROUP BY exercise_name
                ORDER BY total_reps DESC
                LIMIT 5
            """, (week_ago,))
            top_exercises = [{"name": row[0], "total_reps": row[1], "sets": row[2]} 
                           for row in cursor.fetchall()]
            

            return {
                "today_reps": today_reps,
                "week_reps": week_reps,
                "total_days": total_days,
                "first_day": first_day,
                "top_exercises": top_exercises,
                "total_reps_per_exercise": total_reps_per_exercise
            }

    def get_progress_overview(self) -> Dict:
        """Return weekly/monthly progress compared to previous periods.

        Uses rolling 7-day window for "this week" and the preceding 7 days for "last week".
        Uses calendar month for month comparisons.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Use local timezone for all date calculations
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            this_month = now.strftime('%Y-%m')
            last_month = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

            # This (rolling) week: last 7 days including today
            cursor.execute(
                """
                SELECT COALESCE(SUM(reps), 0)
                FROM workouts
                WHERE DATE(date) >= DATE(?, '-6 days')
                """, (today,)
            )
            this_week = cursor.fetchone()[0] or 0

            # Last week: the 7 days before that
            cursor.execute(
                """
                SELECT COALESCE(SUM(reps), 0)
                FROM workouts
                WHERE DATE(date) BETWEEN DATE(?, '-13 days') AND DATE(?, '-7 days')
                """, (today, today)
            )
            last_week = cursor.fetchone()[0] or 0

            # This month
            cursor.execute(
                """
                SELECT COALESCE(SUM(reps), 0)
                FROM workouts
                WHERE strftime('%Y-%m', date) = ?
                """, (this_month,)
            )
            this_month = cursor.fetchone()[0] or 0

            # Last month
            cursor.execute(
                """
                SELECT COALESCE(SUM(reps), 0)
                FROM workouts
                WHERE strftime('%Y-%m', date) = ?
                """, (last_month,)
            )
            last_month = cursor.fetchone()[0] or 0

            def change(a: int, b: int) -> Dict:
                diff = a - b
                pct = (diff / b * 100) if b > 0 else (100 if a > 0 else 0)
                return {"current": a, "previous": b, "diff": diff, "pct": pct}

            return {
                "week": change(this_week, last_week),
                "month": change(this_month, last_month),
            }

    def get_daily_reps(self, days: int = 7) -> List[Dict]:
        """Return a list of daily totals for the last N days (including today)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Use local timezone for daily reps
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                """
                SELECT DATE(date) AS d, COALESCE(SUM(reps),0) AS total
                FROM workouts
                WHERE DATE(date) >= DATE(?, ? || ' days')
                GROUP BY DATE(date)
                ORDER BY d
                """,
                (today, -(days - 1)),
            )
            raw = {row[0]: row[1] for row in cursor.fetchall()}

            # Build full sequence with zeros for missing days
            result: List[Dict] = []
            for i in range(days - 1, -1, -1):
                day = datetime.now().date().fromordinal(datetime.now().date().toordinal() - i)
                day_str = day.isoformat()
                result.append({"date": day_str, "total": int(raw.get(day_str, 0))})
            return result
    
    def get_exercise_by_id(self, exercise_id: int) -> Optional[Dict]:
        """Get exercise details by ID with tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.name, e.description,
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM exercises e
                LEFT JOIN exercise_tags et ON e.id = et.exercise_id
                LEFT JOIN tags t ON et.tag_id = t.id
                WHERE e.id = ?
                GROUP BY e.id, e.name, e.description
            """, (exercise_id,))
            row = cursor.fetchone()
            if row:
                exercise = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "tags": []
                }
                if row[3]:  # if tags exist
                    tag_names = row[3].split(',')
                    tag_colors = row[4].split(',') if row[4] else []
                    exercise["tags"] = [
                        {"name": name, "color": color} 
                        for name, color in zip(tag_names, tag_colors)
                    ]
                return exercise
            return None
    
    def get_exercise_by_name(self, exercise_name: str) -> Optional[Dict]:
        """Get exercise details by name with tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.name, e.description,
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM exercises e
                LEFT JOIN exercise_tags et ON e.id = et.exercise_id
                LEFT JOIN tags t ON et.tag_id = t.id
                WHERE e.name = ?
                GROUP BY e.id, e.name, e.description
            """, (exercise_name,))
            row = cursor.fetchone()
            if row:
                exercise = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "tags": []
                }
                if row[3]:  # if tags exist
                    tag_names = row[3].split(',')
                    tag_colors = row[4].split(',') if row[4] else []
                    exercise["tags"] = [
                        {"name": name, "color": color} 
                        for name, color in zip(tag_names, tag_colors)
                    ]
                return exercise
            return None
    
    def get_all_tags(self) -> List[Dict]:
        """Get all available tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, color FROM tags ORDER BY id")
            return [{"id": row[0], "name": row[1], "color": row[2]} for row in cursor.fetchall()]
    
    def add_tag(self, name: str, color: str = "#3498db") -> bool:
        """Add a new tag."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO tags (name, color) VALUES (?, ?)", (name, color))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print(f"Tag '{name}' already exists!")
            return False
        except sqlite3.Error as e:
            print(f"Error adding tag: {e}")
            return False
    
    def update_tag_color(self, tag_id: int, color: str) -> bool:
        """Update the color of an existing tag."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tags SET color = ? WHERE id = ?", (color, tag_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating tag color: {e}")
            return False
    
    def add_exercise_with_tags(self, name: str, description: str = "", tag_names: List[str] = None) -> bool:
        """Add a new exercise with tags."""
        if tag_names is None:
            tag_names = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add exercise
                cursor.execute("INSERT INTO exercises (name, description) VALUES (?, ?)", (name, description))
                exercise_id = cursor.lastrowid
                
                # Add tags if provided
                if tag_names:
                    for tag_name in tag_names:
                        # Get or create tag
                        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                        tag_row = cursor.fetchone()
                        if tag_row:
                            tag_id = tag_row[0]
                        else:
                            # Create new tag with default color
                            cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                            tag_id = cursor.lastrowid
                        
                        # Link exercise to tag
                        cursor.execute("""
                            INSERT OR IGNORE INTO exercise_tags (exercise_id, tag_id)
                            VALUES (?, ?)
                        """, (exercise_id, tag_id))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print(f"Exercise '{name}' already exists!")
            return False
        except sqlite3.Error as e:
            print(f"Error adding exercise: {e}")
            return False
    
    def update_exercise_tags(self, exercise_id: int, tag_names: List[str]) -> bool:
        """Update tags for an existing exercise."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Remove existing tags
                cursor.execute("DELETE FROM exercise_tags WHERE exercise_id = ?", (exercise_id,))
                
                # Add new tags
                for tag_name in tag_names:
                    # Get or create tag
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        # Create new tag with default color
                        cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                        tag_id = cursor.lastrowid
                    
                    # Link exercise to tag
                    cursor.execute("""
                        INSERT OR IGNORE INTO exercise_tags (exercise_id, tag_id)
                        VALUES (?, ?)
                    """, (exercise_id, tag_id))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error updating exercise tags: {e}")
            return False
    
    def get_exercises_by_tag(self, tag_name: str) -> List[Dict]:
        """Get all exercises that have a specific tag."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.name, e.description,
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM exercises e
                JOIN exercise_tags et ON e.id = et.exercise_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name = ?
                GROUP BY e.id, e.name, e.description
                ORDER BY e.id
            """, (tag_name,))
            exercises = []
            for row in cursor.fetchall():
                exercise = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "tags": []
                }
                if row[3]:  # if tags exist
                    tag_names = row[3].split(',')
                    tag_colors = row[4].split(',') if row[4] else []
                    exercise["tags"] = [
                        {"name": name, "color": color} 
                        for name, color in zip(tag_names, tag_colors)
                    ]
                exercises.append(exercise)
            return exercises
    # Goal management methods
    def get_goals(self) -> List[Dict]:
        """Get all active goals with exercise information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.exercise_id, e.name as exercise_name, 
                       g.daily_target, g.weekly_target, g.is_active,
                       g.created_at, g.updated_at
                FROM goals g
                JOIN exercises e ON g.exercise_id = e.id
                WHERE g.is_active = 1
                ORDER BY e.name
            """)
            goals = []
            for row in cursor.fetchall():
                goals.append({
                    "id": row[0],
                    "exercise_id": row[1],
                    "exercise_name": row[2],
                    "daily_target": row[3],
                    "weekly_target": row[4],
                    "is_active": bool(row[5]),
                    "created_at": row[6],
                    "updated_at": row[7]
                })
            return goals
    
    def get_goal_by_exercise_id(self, exercise_id: int) -> Optional[Dict]:
        """Get goal for a specific exercise."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.exercise_id, e.name as exercise_name,
                       g.daily_target, g.weekly_target, g.is_active,
                       g.created_at, g.updated_at
                FROM goals g
                JOIN exercises e ON g.exercise_id = e.id
                WHERE g.exercise_id = ? AND g.is_active = 1
            """, (exercise_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "exercise_id": row[1],
                    "exercise_name": row[2],
                    "daily_target": row[3],
                    "weekly_target": row[4],
                    "is_active": bool(row[5]),
                    "created_at": row[6],
                    "updated_at": row[7]
                }
            return None
    
    def update_goal(self, exercise_id: int, daily_target: int, weekly_target: int) -> bool:
        """Update or create a goal for an exercise."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if goal exists
                cursor.execute("SELECT id FROM goals WHERE exercise_id = ?", (exercise_id,))
                existing_goal = cursor.fetchone()
                
                if existing_goal:
                    # Update existing goal
                    cursor.execute("""
                        UPDATE goals 
                        SET daily_target = ?, weekly_target = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE exercise_id = ?
                    """, (daily_target, weekly_target, exercise_id))
                else:
                    # Create new goal
                    cursor.execute("""
                        INSERT INTO goals (exercise_id, daily_target, weekly_target)
                        VALUES (?, ?, ?)
                    """, (exercise_id, daily_target, weekly_target))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error updating goal: {e}")
            return False
    
    def get_goal_progress(self, exercise_id: int) -> Dict:
        """Get progress towards daily and weekly goals for an exercise."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get the goal
            goal = self.get_goal_by_exercise_id(exercise_id)
            if not goal:
                return {"error": "No goal found for this exercise"}
            
            # Get today's reps (using local timezone)
            today_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COALESCE(SUM(reps), 0) as today_reps
                FROM workouts
                WHERE exercise_name = (SELECT name FROM exercises WHERE id = ?)
                AND date >= ?
            """, (exercise_id, today_date))
            today_reps = cursor.fetchone()[0]
            
            # Get this week's reps (using local timezone)
            week_ago = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT COALESCE(SUM(reps), 0) as week_reps
                FROM workouts
                WHERE exercise_name = (SELECT name FROM exercises WHERE id = ?)
                AND date >= datetime(?, '-7 days')
            """, (exercise_id, week_ago))
            week_reps = cursor.fetchone()[0]
            
            # Calculate progress percentages
            daily_progress = (today_reps / goal['daily_target'] * 100) if goal['daily_target'] > 0 else 0
            weekly_progress = (week_reps / goal['weekly_target'] * 100) if goal['weekly_target'] > 0 else 0
            
            return {
                "exercise_name": goal['exercise_name'],
                "daily_target": goal['daily_target'],
                "weekly_target": goal['weekly_target'],
                "today_reps": today_reps,
                "week_reps": week_reps,
                "daily_progress": min(daily_progress, 100),  # Cap at 100%
                "weekly_progress": min(weekly_progress, 100),  # Cap at 100%
                "daily_remaining": max(goal['daily_target'] - today_reps, 0),
                "weekly_remaining": max(goal['weekly_target'] - week_reps, 0)
            }
    
    def get_all_goal_progress(self) -> List[Dict]:
        """Get progress for all active goals."""
        goals = self.get_goals()
        progress_list = []
        
        for goal in goals:
            progress = self.get_goal_progress(goal['exercise_id'])
            if 'error' not in progress:
                progress_list.append(progress)
        
        return progress_list
    
    # Today's schedule management methods
    def clear_todays_schedule(self):
        """Clear today's schedule."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM todays_schedule")
            conn.commit()
    
    def set_todays_schedule(self, exercises_with_reps: List[tuple]):
        """Set today's schedule with exercises and suggested reps.
        
        Args:
            exercises_with_reps: List of tuples (exercise_id, suggested_reps)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing schedule
            self.clear_todays_schedule()
            
            # Insert new schedule
            for i, (exercise_id, suggested_reps) in enumerate(exercises_with_reps):
                cursor.execute("""
                    INSERT INTO todays_schedule (exercise_id, order_index, suggested_reps)
                    VALUES (?, ?, ?)
                """, (exercise_id, i + 1, suggested_reps))
            
            conn.commit()
    
    def get_todays_schedule(self) -> List[Dict]:
        """Get today's schedule with exercise details."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ts.id, ts.exercise_id, e.name as exercise_name, e.description,
                       ts.order_index, ts.suggested_reps, ts.is_completed,
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM todays_schedule ts
                JOIN exercises e ON ts.exercise_id = e.id
                LEFT JOIN exercise_tags et ON e.id = et.exercise_id
                LEFT JOIN tags t ON et.tag_id = t.id
                GROUP BY ts.id, ts.exercise_id, e.name, e.description, 
                         ts.order_index, ts.suggested_reps, ts.is_completed
                ORDER BY ts.order_index
            """)
            
            schedule = []
            for row in cursor.fetchall():
                # Parse tags
                tags = []
                if row[7]:  # tags column
                    tag_names = row[7].split(',')
                    tag_colors = row[8].split(',') if row[8] else []
                    for i, tag_name in enumerate(tag_names):
                        if tag_name:  # Skip empty strings
                            color = tag_colors[i] if i < len(tag_colors) else 'white'
                            tags.append({"name": tag_name, "color": color})
                
                schedule.append({
                    "id": row[0],
                    "exercise_id": row[1],
                    "exercise_name": row[2],
                    "description": row[3],
                    "order_index": row[4],
                    "suggested_reps": row[5],
                    "is_completed": bool(row[6]),
                    "tags": tags
                })
            
            return schedule
    
    def mark_exercise_completed(self, schedule_id: int):
        """Mark an exercise in today's schedule as completed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE todays_schedule 
                SET is_completed = 1 
                WHERE id = ?
            """, (schedule_id,))
            conn.commit()
    
    def get_schedule_progress(self) -> Dict:
        """Get progress statistics for today's schedule."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_exercises,
                    SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_exercises
                FROM todays_schedule
            """)
            
            row = cursor.fetchone()
            total = row[0] or 0
            completed = row[1] or 0
            
            return {
                "total_exercises": total,
                "completed_exercises": completed,
                "completion_percentage": (completed / total * 100) if total > 0 else 0
            }
    
    def get_todays_reps_for_exercise(self, exercise_name: str) -> int:
        """Get total reps logged today for a specific exercise."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            cursor.execute("""
                SELECT COALESCE(SUM(reps), 0) as total_reps
                FROM workouts 
                WHERE exercise_name = ? AND DATE(date) = ?
            """, (exercise_name, today))
            
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def add_exercise_to_schedule(self, exercise_id: int, suggested_reps: int = None) -> bool:
        """Add an exercise to today's schedule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if exercise already exists in today's schedule
                cursor.execute("""
                    SELECT id FROM todays_schedule WHERE exercise_id = ?
                """, (exercise_id,))
                if cursor.fetchone():
                    print(f"Exercise already exists in today's schedule!")
                    return False
                
                # Get the next order index
                cursor.execute("""
                    SELECT COALESCE(MAX(order_index), 0) + 1 FROM todays_schedule
                """)
                next_order = cursor.fetchone()[0]
                
                # If no suggested reps provided, try to get from goal
                if suggested_reps is None:
                    goal = self.get_goal_by_exercise_id(exercise_id)
                    suggested_reps = goal['daily_target'] if goal and goal['daily_target'] > 0 else 20
                
                # Insert the exercise
                cursor.execute("""
                    INSERT INTO todays_schedule (exercise_id, order_index, suggested_reps)
                    VALUES (?, ?, ?)
                """, (exercise_id, next_order, suggested_reps))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error adding exercise to schedule: {e}")
            return False
    
    def remove_exercise_from_schedule(self, exercise_id: int) -> bool:
        """Remove an exercise from today's schedule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if exercise exists in schedule
                cursor.execute("""
                    SELECT id FROM todays_schedule WHERE exercise_id = ?
                """, (exercise_id,))
                if not cursor.fetchone():
                    print(f"Exercise not found in today's schedule!")
                    return False
                
                # Remove the exercise
                cursor.execute("""
                    DELETE FROM todays_schedule WHERE exercise_id = ?
                """, (exercise_id,))
                
                # Reorder remaining exercises
                cursor.execute("""
                    UPDATE todays_schedule 
                    SET order_index = (
                        SELECT COUNT(*) + 1 
                        FROM todays_schedule ts2 
                        WHERE ts2.order_index < todays_schedule.order_index
                    )
                """)
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Error removing exercise from schedule: {e}")
            return False
    
    def get_available_exercises_for_schedule(self) -> List[Dict]:
        """Get exercises that are not already in today's schedule."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.name, e.description,
                       GROUP_CONCAT(t.name, ',') as tags,
                       GROUP_CONCAT(t.color, ',') as tag_colors
                FROM exercises e
                LEFT JOIN exercise_tags et ON e.id = et.exercise_id
                LEFT JOIN tags t ON et.tag_id = t.id
                WHERE e.id NOT IN (
                    SELECT exercise_id FROM todays_schedule
                )
                GROUP BY e.id, e.name, e.description
                ORDER BY e.id
            """)
            
            exercises = []
            for row in cursor.fetchall():
                exercise = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "tags": []
                }
                if row[3]:  # if tags exist
                    tag_names = row[3].split(',')
                    tag_colors = row[4].split(',') if row[4] else []
                    exercise["tags"] = [
                        {"name": name, "color": color} 
                        for name, color in zip(tag_names, tag_colors)
                    ]
                exercises.append(exercise)
            return exercises
    
    def get_workout_entries(self, days: int = 7) -> List[Dict]:
        """Get workout entries with IDs for editing purposes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Use local timezone for date comparison
            local_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT id, date, exercise_name, reps, set_number
                FROM workouts
                WHERE date >= datetime(?, '-{} days')
                ORDER BY date DESC
            """.format(days), (local_date,))
            return [{"id": row[0], "date": row[1], "exercise_name": row[2], "reps": row[3], "set_number": row[4]} 
                   for row in cursor.fetchall()]
    
    def update_workout_reps(self, workout_id: int, new_reps: int) -> bool:
        """Update the number of reps for a specific workout entry."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE workouts 
                    SET reps = ? 
                    WHERE id = ?
                """, (new_reps, workout_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating workout reps: {e}")
            return False
    
    def delete_workout_entry(self, workout_id: int) -> bool:
        """Delete a specific workout entry."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting workout entry: {e}")
            return False
    
    def get_monthly_reps(self, months: int = 12) -> List[Dict]:
        """Get monthly totals for the last N months."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Get the last N months of data
            cursor.execute("""
                SELECT strftime('%Y-%m', date) as month, SUM(reps) as total
                FROM workouts
                WHERE date >= datetime('now', '-{} months')
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
                LIMIT ?
            """.format(months), (months,))
            
            results = []
            for row in cursor.fetchall():
                month_str = row[0]
                # Convert YYYY-MM to a more readable format
                year, month = month_str.split('-')
                month_name = datetime(int(year), int(month), 1).strftime('%b %Y')
                results.append({
                    "month": month_name,
                    "total": row[1] or 0
                })
            
            return results