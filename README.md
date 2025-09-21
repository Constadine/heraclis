# HeraCLIs - Home Workout Logger

HeraCLIs is a sophisticated, yet easy-to-use, command-line tool for logging your home workout exercises. It's designed for quick and efficient logging, helping you track your daily movement and exercise habits with a beautiful and intuitive terminal interface.

## Features

-   🏋️ **Quick Workout Logging**: Log your workouts with a few keystrokes.
-   📊 **Statistics and Progress Tracking**: Visualize your progress with daily and weekly stats.
-   🎲 **Workout Randomizer**: Generate a random workout for the day based on your available exercises.
-   ⚙️ **Customizable Exercises**: Add your own exercises, and set daily/weekly goals.
-   💾 **SQLite Database**: All your data is stored locally in a SQLite database.
-   🎨 **Beautiful Terminal Interface**: A modern TUI built with Rich.
-   🖥️ **Desktop Integration**: For Linux users, an application launcher is created for easy access.
-   ⏲️ **Built-in Timer**: A countdown timer with sound.
-   ⚡ **Quick Commands**: Scriptable commands for quick actions like adding a workout or showing stats.

## Installation

### Prerequisites

-   Python 3.10+
-   `git`

### Recommended Installation (Linux)

For Linux users, the recommended way to install HeraCLIs is by using the provided script. This will create a command-line launcher and a desktop entry in your application menu.

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/heraclis.git
    cd heraclis
    ```

2.  Run the installation script:
    ```bash
    ./install_desktop.sh
    ```
    This script will create a launcher at `~/.local/bin/hw` and a desktop file. You can then run the application by typing `hw` in your terminal or by finding "HeraCLIs" in your application menu.

### Manual Installation (All Platforms)

You can also install the application manually. Using a virtual environment is highly recommended.

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/heraclis.git
    cd heraclis
    ```

2.  Create and activate a virtual environment. Using `uv` (if you have it) is fast:
    ```bash
    python3 -m venv .venv # or: uv venv
    source .venv/bin/activate
    ```

3.  Install the dependencies:
    ```bash
    pip install . # or: uv pip install -e .
    ```

4.  Now you can run the application:
    ```bash
    python3 hw.py
    ```
    To make it easier to run, you can create an alias or a symlink.

## Usage

### Interactive Mode

To start the interactive menu, simply run:

```bash
hw
```

This will present you with a menu to log workouts, view stats, manage exercises, and more.

### Quick Commands

HeraCLIs also provides commands for quick, non-interactive use.

| Command                | Description                                        |
| ---------------------- | -------------------------------------------------- |
| `hw --add "pushups 20"`| Quickly log 20 pushups.                            |
| `hw --stats`           | Show your workout statistics and exit.             |
| `hw --goals`           | Show your goals for today and exit.                |
| `hw --random`          | Generate a random workout for today and exit.      |

### Menu Options

1.  **Log Reps**: Log reps for your scheduled exercises.
2.  **Randomize today's workout**: Create a new random workout for the day.
3.  **Show Stats**: View detailed statistics of your workouts.
4.  **Manage Exercises**: Add, view, or manage your exercises and their goals.
5.  **Timer**: A simple countdown timer.
6.  **Settings**: Configure application settings like the timer sound.
7.  **Exit**: Quit the application.

## Configuration

-   **Database**: Your workout data is stored in `workouts.db` in the project's root directory.
-   **Settings**: Application settings are stored in `~/.config/heraclis/settings.json`.

## License

This project is licensed under the MIT License.
