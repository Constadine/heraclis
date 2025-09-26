#!/usr/bin/env python3
"""
HeraCLIs app
A simple command-line tool for logging home workout exercises.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import print as rprint, box
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from database import WorkoutDB
from datetime import datetime
import time
import os
import subprocess
import shutil
import json
from pathlib import Path
import sys
import random


console = Console()
db = WorkoutDB()

# ---------- Settings (persistent) ----------
APP_NAME = "heraclis"
SETTINGS_DIR = Path(os.path.expanduser("~/.config")) / APP_NAME
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def load_settings() -> dict:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    # defaults
    default_sound = (_project_root() / "sounds" / "timer.wav")
    if not default_sound.exists():
        default_sound = _project_root() / "timer.wav"
    return {"timer_sound": str(default_sound)}


def save_settings(data: dict):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


app_settings = load_settings()


def show_today_goals():
    """Display today's schedule and progress."""
    # Get today's schedule
    schedule = db.get_todays_schedule()
    
    if not schedule:
        panel = Panel(
            "[yellow]No workout scheduled for today![/yellow]\n[yellow]Use 'Randomize today's workout' to create one.[/yellow]",
            title="🏋️ Today's Workout Schedule",
            border_style="yellow"
        )
        console.print(panel)
        return
    
    # Create a table for today's schedule
    table = Table(
        title="📊 Today's Workout", 
        box=box.ROUNDED, 
        show_lines=True, 
        style="cyan"
    )
    table.add_column("#", style="magenta", justify="center", width=3)
    table.add_column("Exercise", style="cyan", width=15)
    table.add_column("Goal", style="green", width=8)
    table.add_column("Done", style="blue", width=8)
    table.add_column("Left", style="red", width=8)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Tags", style="white", width=15)
    
    total_goal_reps = 0
    total_done_reps = 0
    completed_ex_count = 0

    for exercise in schedule:
        # Format tags for display
        tags_str = ""
        if exercise["tags"]:
            tag_display = []
            for tag in exercise["tags"]:
                tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
            tags_str = ", ".join(tag_display)
        
        # Get today's reps for this exercise
        goal_reps = exercise['suggested_reps'] or 0
        done_reps = db.get_todays_reps_for_exercise(exercise['exercise_name'])
        remaining_reps = max(0, goal_reps - done_reps)
        total_goal_reps += goal_reps
        total_done_reps += min(done_reps, goal_reps if goal_reps > 0 else done_reps)
        
        # Status display
        if goal_reps > 0 and done_reps >= goal_reps:
            status = "[green]✅ Done[/green]"
            completed_ex_count += 1
        elif done_reps > 0:
            status = "[yellow]🔄 In Progress[/yellow]"
        else:
            status = "[red]⏳ Not Started[/red]"
        
        # Format reps display
        unit = "sec" if "plank" in exercise['exercise_name'].lower() else "reps"
        goal_display = f"{goal_reps} {unit}" if goal_reps > 0 else "N/A"
        done_display = f"{done_reps} {unit}" if done_reps > 0 else f"0 {unit}"
        left_display = f"{remaining_reps} {unit}" if remaining_reps > 0 else f"0 {unit}"
        
        table.add_row(
            str(exercise['order_index']),
            exercise['exercise_name'],
            goal_display,
            done_display,
            left_display,
            status,
            tags_str
        )
    
    console.print(table)
    
    # Show compact overall reps progress bar and completion count
    if total_goal_reps > 0:
        pct = min(total_done_reps / total_goal_reps, 1.0)
        bar_len = 30
        filled = int(pct * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        console.print(f"[bold]Overall:[/bold] {total_done_reps}/{total_goal_reps} reps  [{bar}]  {pct*100:.0f}%  • Completed {completed_ex_count}/{len(schedule)}")


def show_menu():
    """Display the main menu."""
    table = Table(
        title=" -- HeraCLIs -- ",
        box=box.ROUNDED, 
        style="cyan"
    )
    table.add_column("Option", style="magenta", justify="center")
    table.add_column("Description", style="white")
    table.add_row("1", "Log Reps")
    table.add_row("2", "Randomize today's workout")
    table.add_row("3", "Add exercise to workout")
    table.add_row("4", "Remove exercise from workout")
    table.add_row("5", "Show Stats")
    table.add_row("6", "Manage Exercises")
    table.add_row("7", "Edit Today's Reps")
    table.add_row("8", "Timer")
    table.add_row("9", "Settings")
    table.add_row("q", "Exit")
    console.print(table)


def add_workout():
    """Log reps against today's scheduled exercises."""
    schedule = db.get_todays_schedule()
    if not schedule:
        console.print("[yellow]No workout scheduled for today. Use 'Randomize today's workout' first.[/yellow]")
        return

    table = Table(title="Log Reps - Today's Exercises", box=box.ROUNDED, show_lines=True, style="cyan")
    table.add_column("#", style="magenta", justify="center", width=3)
    table.add_column("Exercise", style="cyan", width=16)
    table.add_column("Goal", style="green", width=8)
    table.add_column("Done", style="yellow", width=8)
    table.add_column("Left", style="red", width=8)
    table.add_column("Muscles", style="white", width=20)

    rows = []
    for item in schedule:
        goal_reps = item['suggested_reps'] or 0
        done_reps = db.get_todays_reps_for_exercise(item['exercise_name'])
        left_reps = max(0, goal_reps - done_reps)

        tags_str = ""
        if item.get("tags"):
            tags_str = ", ".join([f"[{t['color']}]{t['name']}[/{t['color']}]" for t in item['tags']])

        unit = "sec" if "plank" in item['exercise_name'].lower() else "reps"
        table.add_row(
            str(item['order_index']),
            item['exercise_name'],
            f"{goal_reps} {unit}" if goal_reps else "N/A",
            f"{done_reps} {unit}",
            f"{left_reps} {unit}",
            tags_str
        )
        rows.append({
            "order": item['order_index'],
            "name": item['exercise_name'],
            "left": left_reps
        })

    console.print(table)
    try:
        order_choice = Prompt.ask("Select exercise (#, 0=Other, q=Cancel)", default="q")
        
        if order_choice == "0":
            # Let the user choose from all available exercises
            all_exercises = db.get_exercises()
            if not all_exercises:
                console.print("[red]No exercises available! Please add some exercises first.[/red]")
                return

            all_table = Table(title="All Exercises", box=box.ROUNDED, style="cyan")
            all_table.add_column("ID", style="magenta", justify="right")
            all_table.add_column("Exercise", style="cyan")
            all_table.add_column("Description", style="white")
            all_table.add_column("Tags", style="yellow")

            for ex in all_exercises:
                tags_str = ""
                if ex.get("tags"):
                    tags_str = ", ".join([f"[{t['color']}]{t['name']}[/{t['color']}]" for t in ex["tags"]])
                all_table.add_row(str(ex["id"]), ex["name"], ex.get("description", ""), tags_str)

            console.print(all_table)

            exercise_id = Prompt.ask("Select exercise (ID, q to cancel)", default="q")
            
            if exercise_id == "q":
                console.print("[yellow]Operation cancelled[/yellow]")
                return
                
            selected_exercise = db.get_exercise_by_id(int(exercise_id))
            if not selected_exercise:
                console.print("[red]Invalid exercise ID[/red]")
                return

            # Suggest reps based on goal/remaining if available
            goal = db.get_goal_by_exercise_id(selected_exercise["id"]) if selected_exercise else None
            today_done = db.get_todays_reps_for_exercise(selected_exercise["name"]) if selected_exercise else 0
            daily_target = goal["daily_target"] if goal else 0
            remaining = max(0, (daily_target or 0) - (today_done or 0))

            # Fallback sensible defaults
            if remaining > 0:
                default_reps = remaining
            elif daily_target > 0:
                default_reps = daily_target
            else:
                default_reps = 30 if "plank" in selected_exercise["name"].lower() else 20

            reps = IntPrompt.ask(f"How many {selected_exercise['name']}?", default=default_reps)

            if db.add_workout(selected_exercise["name"], int(reps)):
                console.print(f"[green]✅ Logged {reps} {selected_exercise['name']}[/green]")
            else:
                console.print("[red]❌ Failed to log workout[/red]")
                return

        else:
            selected = next((r for r in rows if r["order"] == int(order_choice)), None)
            if not selected:
                console.print("[red]Invalid choice[/red]")
                return

            default_reps = max(1, selected["left"]) or 1
            reps = Prompt.ask(f"How many {selected['name']}?", default=default_reps)

            if db.add_workout(selected["name"], int(reps)):
                console.print(f"[green]✅ Logged {reps} {selected['name']}[/green]")
            else:
                console.print("[red]❌ Failed to log workout[/red]")
                return

    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def random_workout():
    """Generate a random workout and save to today's schedule."""
    # Always get all available exercises for random selection
    all_exercises = db.get_exercises()
    
    if not all_exercises:
        console.print("[red]No exercises available! Please add some exercises first.[/red]")
        return
    
    # Ask user how many exercises they want
    panel = Panel(
        f"[yellow]Available exercises: {', '.join([ex['name'] for ex in all_exercises])}[/yellow]",
        title="🎲 Workout Randomizer",
        border_style="blue"
    )
    console.print(panel)
    
    # Get number of exercises from user
    max_exercises = len(all_exercises)    
    try:
        num_exercises_input = Prompt.ask(
            f"How many exercises do you want? (1-{max_exercises}, q to cancel)", 
            default="q"
        )
        
        if num_exercises_input.lower() == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
            
        num_exercises = int(num_exercises_input)
        
        # Validate input
        if num_exercises < 1 or num_exercises > max_exercises:
            console.print(f"[red]Please choose between 1 and {max_exercises} exercises.[/red]")
            return
            
    except ValueError:
        console.print("[red]Invalid number. Please enter a number between 1 and {max_exercises}.[/red]")
        return
    
    # Loop to allow retry/reroll before saving
    while True:
        # Select random exercises from all exercises
        selected_exercises = random.sample([ex['name'] for ex in all_exercises], num_exercises)
        
        console.print(f"\n[bold blue]🎲 Random Workout ({len(selected_exercises)} exercises)[/bold blue]")
        console.print("=" * 40)
        
        # Generate suggested reps based on goals for each exercise
        exercises_with_reps = []
        display_data = []
        
        for exercise_name in selected_exercises:
            # Get exercise details
            exercise_details = db.get_exercise_by_name(exercise_name)
            if exercise_details:
                # Get goal for this exercise
                goal = db.get_goal_by_exercise_id(exercise_details["id"])
                if goal and goal["daily_target"] > 0:
                    suggested_reps = goal["daily_target"]
                else:
                    # Fallback to default values if no goal set
                    if "plank" in exercise_name.lower():
                        suggested_reps = 30  # seconds
                    else:
                        suggested_reps = 20  # reps
                
                exercises_with_reps.append((exercise_details["id"], suggested_reps))
                
                # Format tags for display
                tags_str = ""
                if exercise_details.get("tags"):
                    tag_display = []
                    for tag in exercise_details["tags"]:
                        tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
                    tags_str = ", ".join(tag_display)
                
                reps_display = f"{suggested_reps} sec" if "plank" in exercise_name.lower() else f"{suggested_reps} reps"
                
                display_data.append({
                    'name': exercise_name,
                    'reps_display': reps_display,
                    'description': exercise_details.get('description', ''),
                    'tags_str': tags_str
                })
        
        # Display the random workout
        table = Table(
            title="🏋️ Your Random Workout", 
            box=box.ROUNDED, 
            show_lines=True, 
            style="green"
        )
        table.add_column("#", style="magenta", justify="center", width=3)
        table.add_column("Exercise", style="cyan", width=15)
        table.add_column("Goal Reps", style="green", width=12)
        table.add_column("Description", style="blue", width=20)
        table.add_column("Muscles", style="yellow", width=15)
        
        for i, data in enumerate(display_data, 1):
            table.add_row(
                str(i),
                data['name'],
                data['reps_display'],
                data['description'],
                data['tags_str']
            )
        
        console.print(table)
        
        action = Prompt.ask("[bold]Accept this selection?[/bold]", choices=["s","r","c"], default="s")
        # s = save, r = retry/reroll, c = cancel
        if action == "s":
            db.set_todays_schedule(exercises_with_reps)
            console.print("\n[bold green]✅ Today's workout schedule saved![/bold green]")
            console.print("[bold blue]You can now see your schedule on the main screen and log your progress.[/bold blue]")
            break
        elif action == "r":
            console.print("[yellow]Rerolling...[/yellow]")
            continue
        else:
            console.print("[yellow]Cancelled. Maybe next time! 💪[/yellow]")
            break


def show_stats():
    """Display workout statistics."""
    stats = db.get_stats()
    progress = db.get_progress_overview()
    daily = db.get_daily_reps(7)
    recent_workouts = db.get_recent_workouts(7)
    
    # Today's summary
    today_panel = Panel(
        f"[bold]Today:[/bold] {stats['today_reps'] or 0} reps\n"
        f"[bold]This Week:[/bold] {stats['week_reps'] or 0} reps",
        title="📊 Quick Stats",
        border_style="green"
    )
    # Weekly/Monthly progress panel
    def fmt_change(section: dict) -> str:
        sign = "+" if section["diff"] > 0 else ("" if section["diff"] == 0 else "-")
        color = "green" if section["diff"] > 0 else ("yellow" if section["diff"] == 0 else "red")
        pct = abs(section["pct"]) if section["pct"] is not None else 0
        return f"[bold]{section['current']}[/bold] ( [ {color} ]{sign}{abs(section['diff'])} ({pct:.0f}%)[/ {color} ] vs {section['previous']} )"

    progress_panel = Panel(
        f"Week: {progress['week']['current']} (Δ {progress['week']['diff']:+} / {progress['week']['pct']:.0f}%)\n"
        f"Month: {progress['month']['current']} (Δ {progress['month']['diff']:+} / {progress['month']['pct']:.0f}%)",
        title="📈 Progress (This vs Previous)",
        border_style="blue"
    )
    console.print(today_panel)
    console.print(progress_panel)
    
    # Top exercises this week
    if stats['top_exercises']:
        table = Table(
            title="🔥 Top Exercises This Week", 
            box=box.ROUNDED, 
            show_lines=True, 
            style="red"
        )
        table.add_column("Exercise", style="cyan")
        table.add_column("Total Reps", style="magenta")
        table.add_column("Sets", style="green")
        
        for exercise in stats['top_exercises']:
            table.add_row(
                exercise['name'],
                str(exercise['total_reps']),
                str(exercise['sets'])
            )
        
        console.print(table)
    
    # 7-day activity chart
    if daily:
        bar_len = 20
        max_val = max([d["total"] for d in daily]) or 1
        lines = []
        for d in daily:
            label = datetime.fromisoformat(d["date"]).strftime("%a")
            filled = int((d["total"] / max_val) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(f"{label:>3} {bar} {d['total']}")
        chart = "\n".join(lines)
        console.print(Panel(chart, title="📅 Last 7 Days", border_style="cyan"))
    
    # Monthly activity chart
    monthly_data = db.get_monthly_reps()
    if monthly_data:
        bar_len = 15
        max_val = max([m["total"] for m in monthly_data]) or 1
        lines = []
        for m in monthly_data:
            label = m["month"]
            filled = int((m["total"] / max_val) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(f"{label:>8} {bar} {m['total']}")
        monthly_chart = "\n".join(lines)
        console.print(Panel(monthly_chart, title="📅 Last 12 Months", border_style="blue"))

    # Recent workouts
    if recent_workouts:
        recent_table = Table(
            title="📅 Recent Logs (Last 7 Days)", 
            box=box.ROUNDED, 
            show_lines=True, 
            style="blue"
        )
        recent_table.add_column("Date", style="cyan")
        recent_table.add_column("Exercise", style="magenta")
        recent_table.add_column("Reps", style="green")
        
        for workout in recent_workouts[:10]:  # Show last 10
            date_str = datetime.fromisoformat(workout['date']).strftime("%m/%d %H:%M")
            recent_table.add_row(
                date_str,
                workout['exercise_name'],
                str(workout['reps']),
            )
        
        console.print(recent_table)
    else:
        no_workouts_panel = Panel(
            "[yellow]No recent workouts found[/yellow]",
            title="📅 Recent Logs",
            border_style="yellow"
        )
        console.print(no_workouts_panel)
    
    # Add a pause before returning to menu
    Prompt.ask("\nPress Enter to return to the menu")


def manage_exercises():
    """Manage available exercises and tags."""
    while True:
        console.print("\n[bold blue]Exercise Management[/bold blue]")
        console.print("1. View Exercises")
        console.print("2. Add Exercise")
        console.print("3. Manage Tags")
        console.print("4. Update Exercise Tags")
        console.print("5. Adjust Goals")
        console.print("q. Back to Main Menu")

        
        choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4", "5", "q"], default="q")
        
        if choice == "q":
            break
        elif choice == "1":
            exercises = db.get_exercises()
            if exercises:
                table = Table(title="Available Exercises")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Description", style="green")
                table.add_column("Muscles", style="yellow")
                
                for exercise in exercises:
                    # Format tags for display
                    tags_str = ""
                    if exercise["tags"]:
                        tag_display = []
                        for tag in exercise["tags"]:
                            tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
                        tags_str = ", ".join(tag_display)
                    
                    table.add_row(
                        str(exercise["id"]),
                        exercise["name"],
                        exercise["description"],
                        tags_str
                    )
                console.print(table)
            else:
                console.print("[yellow]No exercises found[/yellow]")
        
        elif choice == "2":
            name = Prompt.ask("Exercise name")
            description = Prompt.ask("Description (optional)", default="")
            
            # Ask for tags
            console.print("\n[bold]Add tags (comma-separated, or press Enter to skip):[/bold]")
            console.print("Available tags:", end=" ")
            all_tags = db.get_all_tags()
            if all_tags:
                tag_names = [tag["name"] for tag in all_tags]
                console.print(", ".join(tag_names))
            else:
                console.print("None")
            
            tags_input = Prompt.ask("Tags", default="")
            tag_names = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
            
            if db.add_exercise_with_tags(name, description, tag_names):
                console.print(f"[green]✅ Added exercise: {name}[/green]")
                if tag_names:
                    console.print(f"[green]   Tags: {', '.join(tag_names)}[/green]")
            else:
                console.print(f"[red]❌ Failed to add exercise: {name}[/red]")
        
        elif choice == "3":
            manage_tags()
        
        elif choice == "4":
            update_exercise_tags()
        elif choice == "5":
            adjust_goals()


def manage_tags():
    """Manage available tags."""
    while True:
        console.print("\n[bold blue]Tag Management[/bold blue]")
        console.print("1. View Tags")
        console.print("2. Add Tag")
        console.print("3. Edit Tag Color")
        console.print("q. Back to Exercise Management")

        
        choice = Prompt.ask("Choose option", choices=["1", "2", "3", "q"], default="q")
        
        if choice == "q":
            break
        elif choice == "1":
            tags = db.get_all_tags()
            if tags:
                table = Table(title="Available Tags")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Color", style="green")
                
                for tag in tags:
                    color_display = f"[{tag['color']}]●[/{tag['color']}] {tag['color']}"
                    table.add_row(str(tag["id"]), tag["name"], color_display)
                console.print(table)
            else:
                console.print("[yellow]No tags found[/yellow]")
        
        elif choice == "2":
            name = Prompt.ask("Tag name")
            color = Prompt.ask("Color (hex code, e.g., #ff0000)", default="#3498db")
            
            if db.add_tag(name, color):
                console.print(f"[green]✅ Added tag: {name}[/green]")
            else:
                console.print(f"[red]❌ Failed to add tag: {name}[/red]")
        
        elif choice == "3":
            edit_tag_color()


def edit_tag_color():
    """Edit the color of an existing tag."""
    tags = db.get_all_tags()
    if not tags:
        console.print("[red]No tags available![/red]")
        return
    
    # Display tags
    table = Table(title="Select Tag to Edit Color")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Current Color", style="green")
    
    for tag in tags:
        color_display = f"[{tag['color']}]●[/{tag['color']}] {tag['color']}"
        table.add_row(str(tag["id"]), tag["name"], color_display)
    
    console.print(table)    
    try:
        tag_id = IntPrompt.ask("Select tag ID to edit color (q to cancel)", default="q")
        
        if tag_id == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
            
        selected_tag = next((t for t in tags if t["id"] == tag_id), None)
        
        if not selected_tag:
            console.print("[red]Invalid tag ID![/red]")
            return
        
        console.print(f"\n[bold]Editing color for: {selected_tag['name']}[/bold]")
        console.print(f"Current color: [{selected_tag['color']}]●[/{selected_tag['color']}] {selected_tag['color']}")
        
        new_color = Prompt.ask("New color (hex code, e.g., #ff0000)", default=selected_tag['color'])
        
        if db.update_tag_color(tag_id, new_color):
            console.print(f"[green]✅ Updated color for {selected_tag['name']} to {new_color}[/green]")
        else:
            console.print("[red]❌ Failed to update tag color[/red]")
            
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def update_exercise_tags():
    """Update tags for an existing exercise."""
    exercises = db.get_exercises()
    if not exercises:
        console.print("[red]No exercises available![/red]")
        return
    
    # Display exercises
    table = Table(title="Select Exercise to Update")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Current Tags", style="yellow")
    
    for exercise in exercises:
        tags_str = ""
        if exercise["tags"]:
            tag_display = []
            for tag in exercise["tags"]:
                tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
            tags_str = ", ".join(tag_display)
        
        table.add_row(str(exercise["id"]), exercise["name"], tags_str)
    
    console.print(table)    
    try:
        exercise_id = IntPrompt.ask("Select exercise ID to update tags (q to cancel)", default="q")
        
        if exercise_id == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
            
        selected_exercise = db.get_exercise_by_id(exercise_id)
        
        if not selected_exercise:
            console.print("[red]Invalid exercise ID![/red]")
            return
        
        console.print(f"\n[bold]Updating tags for: {selected_exercise['name']}[/bold]")
        console.print("Current tags:", end=" ")
        if selected_exercise["tags"]:
            current_tags = [tag["name"] for tag in selected_exercise["tags"]]
            console.print(", ".join(current_tags))
        else:
            console.print("None")
        
        # Show available tags
        all_tags = db.get_all_tags()
        if all_tags:
            console.print("\nAvailable tags:", end=" ")
            tag_names = [tag["name"] for tag in all_tags]
            console.print(", ".join(tag_names))
        
        # Get new tags
        console.print("\n[bold]Enter new tags (comma-separated, or press Enter to clear all):[/bold]")
        tags_input = Prompt.ask("Tags", default="")
        tag_names = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []
        
        if db.update_exercise_tags(exercise_id, tag_names):
            console.print(f"[green]✅ Updated tags for {selected_exercise['name']}[/green]")
            if tag_names:
                console.print(f"[green]   New tags: {', '.join(tag_names)}[/green]")
            else:
                console.print("[green]   All tags removed[/green]")
        else:
            console.print("[red]❌ Failed to update tags[/red]")
            
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def adjust_goals():
    """Adjust daily/weekly goals for an exercise with smart suggestions."""
    exercises = db.get_exercises()
    if not exercises:
        console.print("[red]No exercises available![/red]")
        return

    # Show exercises with current goal snapshot
    table = Table(title="Adjust Goals", box=box.ROUNDED, style="cyan")
    table.add_column("ID", style="magenta")
    table.add_column("Exercise", style="cyan")
    table.add_column("Daily Target", style="green")
    table.add_column("Weekly Target", style="green")

    rows = []
    for ex in exercises:
        goal = db.get_goal_by_exercise_id(ex["id"]) if ex else None
        daily = goal["daily_target"] if goal else 0
        weekly = goal["weekly_target"] if goal else 0
        table.add_row(str(ex["id"]), ex["name"], str(daily), str(weekly))
        rows.append({"id": ex["id"], "name": ex["name"], "daily": daily, "weekly": weekly})

    console.print(table)

    try:
        ex_id = IntPrompt.ask("Select exercise ID to adjust (q to cancel)", default="q")
        
        if ex_id == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
            
        ex_row = next((r for r in rows if r["id"] == ex_id), None)
        if not ex_row:
            console.print("[red]Invalid exercise ID[/red]")
            return

        # Suggestion: if last week exceeded target by >10%, bump by 10%; if <60% achieved, reduce by 10%.
        progress = db.get_goal_progress(ex_id) if db.get_goal_by_exercise_id(ex_id) else None
        suggested_daily = ex_row["daily"] or 10
        suggested_weekly = ex_row["weekly"] or suggested_daily * 7
        if progress:
            daily_pct = progress["daily_progress"]
            if daily_pct >= 110:
                suggested_daily = int(max(ex_row["daily"], 1) * 1.1)
            elif daily_pct <= 60 and ex_row["daily"]:
                suggested_daily = max(int(ex_row["daily"] * 0.9), 1)
            # weekly suggestion mirrors daily
            suggested_weekly = max(int(suggested_daily * 7), 1)

        new_daily = IntPrompt.ask(
            f"New daily target for {ex_row['name']}?", default=suggested_daily
        )
        new_weekly = IntPrompt.ask(
            f"New weekly target for {ex_row['name']}?", default=suggested_weekly
        )

        if db.update_goal(ex_id, new_daily, new_weekly):
            console.print(
                f"[green]✅ Updated goals for {ex_row['name']}: daily {new_daily}, weekly {new_weekly}[/green]"
            )
        else:
            console.print("[red]❌ Failed to update goals[/red]")

    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def add_exercise_to_workout():
    """Add an exercise to today's active workout."""
    # Get available exercises (not already in schedule)
    available_exercises = db.get_available_exercises_for_schedule()
    
    if not available_exercises:
        console.print("[yellow]No exercises available to add! All exercises are already in today's workout.[/yellow]")
        return
    
    # Display available exercises
    table = Table(title="Add Exercise to Today's Workout", box=box.ROUNDED, style="cyan")
    table.add_column("ID", style="magenta", justify="center", width=3)
    table.add_column("Exercise", style="cyan", width=20)
    table.add_column("Description", style="white", width=25)
    table.add_column("Muscles", style="yellow", width=20)
    
    for exercise in available_exercises:
        # Format tags for display
        tags_str = ""
        if exercise.get("tags"):
            tag_display = []
            for tag in exercise["tags"]:
                tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
            tags_str = ", ".join(tag_display)
        
        table.add_row(
            str(exercise["id"]),
            exercise["name"],
            exercise.get("description", ""),
            tags_str
        )
    
    console.print(table)
    
    try:
        exercise_id = IntPrompt.ask("Select exercise ID to add (q to cancel)", default="q")
        
        if exercise_id == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        # Find the selected exercise
        selected_exercise = next((ex for ex in available_exercises if ex["id"] == exercise_id), None)
        if not selected_exercise:
            console.print("[red]Invalid exercise ID[/red]")
            return
        
        # Ask for suggested reps
        goal = db.get_goal_by_exercise_id(exercise_id)
        default_reps = goal['daily_target'] if goal and goal['daily_target'] > 0 else 20
        
        suggested_reps = IntPrompt.ask(
            f"Suggested reps for {selected_exercise['name']}?", 
            default=default_reps
        )
        
        if db.add_exercise_to_schedule(exercise_id, suggested_reps):
            console.print(f"[green]✅ Added {selected_exercise['name']} to today's workout![/green]")
            console.print(f"[green]   Suggested reps: {suggested_reps}[/green]")
        else:
            console.print("[red]❌ Failed to add exercise to workout[/red]")
    
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def remove_exercise_from_workout():
    """Remove an exercise from today's active workout."""
    # Get today's schedule
    schedule = db.get_todays_schedule()
    
    if not schedule:
        console.print("[yellow]No exercises in today's workout to remove![/yellow]")
        return
    
    # Display current schedule
    table = Table(title="Remove Exercise from Today's Workout", box=box.ROUNDED, style="cyan")
    table.add_column("#", style="magenta", justify="center", width=3)
    table.add_column("Exercise", style="cyan", width=20)
    table.add_column("Goal Reps", style="green", width=12)
    table.add_column("Description", style="white", width=25)
    table.add_column("Muscles", style="yellow", width=20)
    
    for exercise in schedule:
        # Format tags for display
        tags_str = ""
        if exercise.get("tags"):
            tag_display = []
            for tag in exercise["tags"]:
                tag_display.append(f"[{tag['color']}]{tag['name']}[/{tag['color']}]")
            tags_str = ", ".join(tag_display)
        
        # Format reps display
        unit = "sec" if "plank" in exercise['exercise_name'].lower() else "reps"
        goal_display = f"{exercise['suggested_reps']} {unit}" if exercise['suggested_reps'] else "N/A"
        
        table.add_row(
            str(exercise['order_index']),
            exercise['exercise_name'],
            goal_display,
            exercise.get('description', ''),
            tags_str
        )
    
    console.print(table)
    
    try:
        order_choice = IntPrompt.ask("Select exercise # to remove (q to cancel)", default="q")
        
        if order_choice == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        # Find the selected exercise
        selected_exercise = next((ex for ex in schedule if ex['order_index'] == order_choice), None)
        if not selected_exercise:
            console.print("[red]Invalid exercise number[/red]")
            return
        
        # Confirm removal
        if Confirm.ask(f"Remove {selected_exercise['exercise_name']} from today's workout?"):
            if db.remove_exercise_from_schedule(selected_exercise['exercise_id']):
                console.print(f"[green]✅ Removed {selected_exercise['exercise_name']} from today's workout![/green]")
            else:
                console.print("[red]❌ Failed to remove exercise from workout[/red]")
        else:
            console.print("[yellow]Operation cancelled[/yellow]")
    
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")


def edit_logged_reps():
    """Edit the number of reps for today's logged workouts."""
    # Get today's workout entries only
    today = datetime.now().strftime('%Y-%m-%d')
    entries = db.get_workout_entries(1)  # Only today
    
    # Filter to only today's entries
    today_entries = [entry for entry in entries if entry['date'].startswith(today)]
    
    if not today_entries:
        console.print("[yellow]No workout entries found for today to edit![/yellow]")
        return
    
    # Display today's workout entries with fresh sequential IDs
    table = Table(title="Edit Today's Logged Reps", box=box.ROUNDED, show_lines=True, style="cyan")
    table.add_column("#", style="magenta", justify="center", width=3)
    table.add_column("Time", style="cyan", width=8)
    table.add_column("Exercise", style="green", width=15)
    table.add_column("Reps", style="yellow", width=8)
    
    # Create a mapping from display ID to actual entry
    id_mapping = {}
    for i, entry in enumerate(today_entries, 1):
        # Format time for display (just the time part)
        date_obj = datetime.fromisoformat(entry['date'])
        time_str = date_obj.strftime("%H:%M")
        
        # Format reps display
        unit = "sec" if "plank" in entry['exercise_name'].lower() else "reps"
        reps_display = f"{entry['reps']} {unit}"
        
        table.add_row(
            str(i),
            time_str,
            entry['exercise_name'],
            reps_display,
        )
        
        # Map display ID to actual database entry
        id_mapping[i] = entry
    
    console.print(table)
    
    try:
        display_id = IntPrompt.ask("Select entry # to edit (q to cancel)", default="q")
        
        if display_id == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        
        # Find the selected entry using the mapping
        selected_entry = id_mapping.get(display_id)
        if not selected_entry:
            console.print("[red]Invalid entry number[/red]")
            return
        
        # Show current details
        console.print(f"\n[bold]Editing workout entry:[/bold]")
        console.print(f"Exercise: {selected_entry['exercise_name']}")
        console.print(f"Current reps: {selected_entry['reps']}")
        console.print(f"Date: {datetime.fromisoformat(selected_entry['date']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ask what to do
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("1. Edit reps")
        console.print("2. Delete entry")
        console.print("q. Cancel")
        
        action = Prompt.ask("Choose action", choices=["1", "2", "q"], default="q")
        
        if action == "q":
            console.print("[yellow]Operation cancelled[/yellow]")
            return
        elif action == "1":
            # Ask for new reps
            new_reps = IntPrompt.ask("Enter new number of reps", default=selected_entry['reps'])
            
            if new_reps == selected_entry['reps']:
                console.print("[yellow]No changes made[/yellow]")
                return
            
            # Confirm the change
            if Confirm.ask(f"Change {selected_entry['exercise_name']} from {selected_entry['reps']} to {new_reps} reps?"):
                if db.update_workout_reps(selected_entry['id'], new_reps):
                    console.print(f"[green]✅ Updated {selected_entry['exercise_name']} to {new_reps} reps[/green]")
                else:
                    console.print("[red]❌ Failed to update workout entry[/red]")
            else:
                console.print("[yellow]Operation cancelled[/yellow]")
        elif action == "2":
            # Confirm deletion
            if Confirm.ask(f"Delete {selected_entry['exercise_name']} entry with {selected_entry['reps']} reps?"):
                if db.delete_workout_entry(selected_entry['id']):
                    console.print(f"[green]✅ Deleted {selected_entry['exercise_name']} entry[/green]")
                else:
                    console.print("[red]❌ Failed to delete workout entry[/red]")
            else:
                console.print("[yellow]Operation cancelled[/yellow]")
    
    except (ValueError, KeyboardInterrupt):
        console.print("[yellow]Operation cancelled[/yellow]")

def main():
    """Main application loop."""
    console.clear()
    console.print("[bold green]νους υγιής εν σώματι υγιεί[/bold green]")
    
    # Always show today's goals first
    show_today_goals()
    
    while True:
        try:
            show_menu()
            choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "q"], default="q")
            
            if choice == "1":
                console.clear()
                add_workout()
                # Show updated goals after logging
                console.print("\n")
                show_today_goals()
            elif choice == "2":
                console.clear()
                random_workout()
                # Show updated goals after logging
                console.print("\n")
                show_today_goals()
            elif choice == "3":
                console.clear()
                add_exercise_to_workout()
                # Show updated goals after adding
                console.print("\n")
                show_today_goals()
            elif choice == "4":
                console.clear()
                remove_exercise_from_workout()
                # Show updated goals after removing
                console.print("\n")
                show_today_goals()
            elif choice == "5":
                console.clear()
                show_stats()
            elif choice == "6":
                console.clear()
                manage_exercises()
            elif choice == "7":
                console.clear()
                edit_logged_reps()
                # Show updated goals after editing
                console.print("\n")
                show_today_goals()
            elif choice == "8":
                console.clear()
                start_timer()
            elif choice == "9":
                console.clear()
                settings_menu()
            elif choice == "q":
                console.clear()
                console.print("[bold green]See you later chief 💪[/bold green]")
                break
                
        except KeyboardInterrupt:
            console.clear()
            console.print("[yellow]Goodbye! Keep moving! 💪[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")


@click.command()
@click.option('--stats', is_flag=True, help='Show stats and exit')
@click.option('--goals', is_flag=True, help='Show today\'s goals and exit')
@click.option('--random', is_flag=True, help='Generate random workout and exit')
@click.option('--add', help='Quick add workout: --add "pushups 20"')
def cli(stats, goals, random, add):
    """HeraCLIs - A simple CLI tool for logging workouts."""
    if stats:
        console.clear()
        show_stats()
    elif goals:
        console.clear()
        show_today_goals()
    elif random:
        console.clear()
        random_workout()
    elif add:
        # Quick add format: "exercise_name reps"
        try:
            parts = add.split()
            if len(parts) >= 2:
                exercise_name = parts[0]
                reps = int(parts[1])
                if db.add_workout(exercise_name, reps):
                    console.print(f"[green]✅ Logged {reps} {exercise_name}[/green]")
                else:
                    console.print("[red]❌ Failed to log workout[/red]")
            else:
                console.print("[red]Invalid format. Use: --add 'exercise_name reps'[/red]")
        except ValueError:
            console.print("[red]Invalid reps number[/red]")
    else:
        main()


def _play_sound(sound_path: str):
    """Attempt to play a sound file using common CLI tools."""
    if not os.path.exists(sound_path):
        return

    # Try aplay (ALSA), afplay (macOS), paplay (PulseAudio)
    player = None
    for cmd in ["aplay", "paplay", "afplay"]:
        if shutil.which(cmd):
            player = cmd
            break
    if player:
        try:
            subprocess.run([player, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def start_timer():
    """Simple countdown timer with 5s arm delay, progress bar, and sound."""
    console.print(Panel("Timer", border_style="green"))
    total_seconds = IntPrompt.ask("How many seconds?", default=60)

    # 5-second arm delay
    console.print("\nArming in 5 seconds...")
    for i in range(5, 0, -1):
        console.print(f"Starting in {i}...", end="\r")
        time.sleep(1)
    console.print("")

    # Countdown with progress
    with Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=40),
        TimeElapsedColumn(),
        TextColumn("remaining:"),
        TimeRemainingColumn(),
        transient=True,
        console=console,
    ) as progress:
        task_id = progress.add_task("Countdown", total=total_seconds)
        start = time.time()
        while not progress.finished:
            elapsed = int(time.time() - start)
            progress.update(task_id, advance=1)
            time.sleep(1)
            if elapsed >= total_seconds:
                break

    console.print("\n[bold green]⏰ Time's up![/bold green]")
    _play_sound(app_settings.get("timer_sound", "timer.wav"))


def settings_menu():
    """Settings: configure app preferences (persistent)."""
    while True:
        table = Table(title="Settings", box=box.ROUNDED, style="cyan")
        table.add_column("Option", style="magenta", justify="center")
        table.add_column("Name", style="white")
        table.add_column("Value", style="green")
        table.add_row("q", "Back to Main Menu", "")
        table.add_row("1", "Timer Sound", app_settings.get("timer_sound", "timer.wav"))
        console.print(table)

        choice = Prompt.ask("Select option", choices=["q", "1"], default="q")
        if choice == "q":
            return

        if choice == "1":
            # List available .wav files in sounds directory
            sounds_dir = _project_root() / "sounds"
            sound_files = []
            if sounds_dir.exists():
                sound_files = [p for p in sounds_dir.glob("*.wav")]
            # Fallback: also allow entering a custom path
            console.print("Available sounds:")
            if sound_files:
                for idx, p in enumerate(sound_files, 1):
                    console.print(f"  {idx}. {p.name}")
            else:
                console.print("  (No .wav files found in ./sounds)")

            raw = Prompt.ask("Choose by number or enter a path (blank to cancel)", default="")
            if not raw:
                continue
            selected_path = None
            if raw.isdigit() and sound_files:
                i = int(raw)
                if 1 <= i <= len(sound_files):
                    selected_path = str(sound_files[i - 1])
            else:
                # Treat as a path
                candidate = Path(raw).expanduser()
                if candidate.exists():
                    selected_path = str(candidate)

            if selected_path:
                app_settings["timer_sound"] = selected_path
                save_settings(app_settings)
                console.print(f"[green]Saved timer sound:[/green] {selected_path}")
            else:
                console.print("[red]Invalid selection[/red]")


def _sparkline(values):
    """Return a unicode sparkline for a list of numeric values."""
    if not values:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    max_val = max(values) or 1
    line = []
    for v in values:
        idx = int((v / max_val) * (len(blocks) - 1))
        idx = max(0, min(idx, len(blocks) - 1))
        # Use double-width characters for better alignment
        line.append(blocks[idx] + blocks[idx])
    return " ".join(line)


if __name__ == "__main__":
    cli()
