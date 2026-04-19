"""
Pomodoro Productivity Tracker
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum, auto
import uuid
# Constants 
POMODORO_DURATION   = timedelta(minutes=25)
SHORT_BREAK         = timedelta(minutes=5)
LONG_BREAK_MIN      = timedelta(minutes=15)
LONG_BREAK_MAX      = timedelta(minutes=30)
SESSIONS_BEFORE_LONG_BREAK = 5

class SessionState(Enum):
    RUNNING   = auto()
    COMPLETED = auto()
    ABANDONED = auto()

class BreakType(Enum):
    SHORT = "Short break (5 min)"
    LONG  = "Long break (15–30 min)"

#PomodoroSession 
class PomodoroSession:
    """
    A single 25-minute focused work block tied to one task. """
    def __init__(self, task: "Task") -> None:
        self._id        = uuid.uuid4()
        self._task      = task
        self._started_at: datetime           = datetime.now()
        self._ended_at:   Optional[datetime] = None
        self._state:      SessionState       = SessionState.RUNNING
    @property
    def id(self) -> uuid.UUID:
        return self._id
    @property
    def task(self) -> "Task":
        return self._task
    @property
    def started_at(self) -> datetime:
        return self._started_at
    @property
    def ended_at(self) -> Optional[datetime]:
        return self._ended_at
    @property
    def state(self) -> SessionState:
        return self._state
    @property
    def is_running(self) -> bool:
        return self._state is SessionState.RUNNING
    @property
    def duration(self) -> timedelta:
        end = self._ended_at if self._ended_at else datetime.now()
        return end - self._started_at
    @property
    def duration_minutes(self) -> float:
        return self.duration.total_seconds() / 60

    #Lifecycle
    def complete(self) -> None:
        """Mark session as successfully completed."""
        if not self.is_running:
            raise ValueError("Cannot complete a session that is not running.")
        self._ended_at = datetime.now()
        self._state    = SessionState.COMPLETED
    def abandon(self) -> None:
        """Mark session as ended early)."""
        if not self.is_running:
            raise ValueError("Cannot end a session that is not running.")
        self._ended_at = datetime.now()
        self._state    = SessionState.ABANDONED
    def __repr__(self) -> str:
        return (
            f"PomodoroSession(task={self._task.name!r}, "
            f"state={self._state.name}, "
            f"duration={self.duration_minutes:.1f}m)"
        )

#Task
class Task:
    def __init__(self, name: str, description: str = "") -> None:
        if not name.strip():
            raise ValueError("Task name cannot be empty.")
        self._id          = uuid.uuid4()
        self._name        = name.strip()
        self._description = description.strip()
        self._sessions:   list[PomodoroSession] = []
        self._created_at: datetime = datetime.now()
    @property
    def id(self) -> uuid.UUID:
        return self._id
    @property
    def name(self) -> str:
        return self._name
    @property
    def description(self) -> str:
        return self._description
    @property
    def sessions(self) -> list[PomodoroSession]:
        return list(self._sessions)         
    @property
    def completed_sessions(self) -> list[PomodoroSession]:
        return [s for s in self._sessions if s.state is SessionState.COMPLETED]
    @property
    def pomodoro_count(self) -> int:
        return len(self.completed_sessions)
    @property
    def total_time(self) -> timedelta:
        """Sum of durations across all completed sessions."""
        return sum(
            (s.duration for s in self.completed_sessions),
            timedelta()
        )
    @property
    def total_minutes(self) -> float:
        return self.total_time.total_seconds() / 60
    @property
    def active_session(self) -> Optional[PomodoroSession]:
        for s in self._sessions:
            if s.is_running:
                return s
        return None
    @property
    def has_active_session(self) -> bool:
        return self.active_session is not None

    def start_session(self) -> PomodoroSession:
        """Begin a new pomodoro on this task."""
        if self.has_active_session:
            raise ValueError(f"Task '{self._name}' already has a running session.")
        session = PomodoroSession(task=self)
        self._sessions.append(session)
        return session
    def __repr__(self) -> str:
        return (
            f"Task(name={self._name!r}, "
            f"pomodoros={self.pomodoro_count}, "
            f"total={self.total_minutes:.0f}m)"
        )
    
#Tracker
class PomodoroTracker:
    """
    Responsibilities:
      - Own all tasks(no task exists outside a tracker).
      - Expose the currently active session(if any).
      - Track the global completed-session.
      - Generate the daily summary report.
    """
    def __init__(self, owner: str = "User") -> None:
        self._owner             = owner
        self._tasks:   list[Task] = []
        self._date:    datetime   = datetime.now()
        self._global_completed: int = 0   # across all tasks today

    #Task management 
    def add_task(self, name: str, description: str = "") -> Task:
        # Prevent exact duplicate names (case-insensitive)
        if any(t.name.lower() == name.strip().lower() for t in self._tasks):
            raise ValueError(f"A task named '{name}' already exists.")
        task = Task(name, description)
        self._tasks.append(task)
        return task
    def get_task(self, name: str) -> Optional[Task]:
        """Look up a task by name (case-insensitive)."""
        for t in self._tasks:
            if t.name.lower() == name.strip().lower():
                return t
        return None
    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks)
    @property
    def active_session(self) -> Optional[PomodoroSession]:
        for task in self._tasks:
            if task.has_active_session:
                return task.active_session
        return None

    def start_pomodoro(self, task: Task) -> PomodoroSession:
        """
        Start a new 25-minute session on the given task.
        """
        if self.active_session is not None:
            raise ValueError(
                f"Session already running on '{self.active_session.task.name}'. "
                "Complete or abandon it first."
            )
        session = task.start_session()
        print(f"▶  Pomodoro started  [{session.started_at:%H:%M:%S}]  →  {task.name}")
        return session

    def complete_pomodoro(self) -> tuple[PomodoroSession, BreakType]:
        """
        Returns the completed session and the recommended break type.
        """
        session = self.active_session
        if session is None:
            raise ValueError("No active session to complete.")
        session.complete()
        self._global_completed += 1
        break_type = (
            BreakType.LONG
            if self._global_completed % SESSIONS_BEFORE_LONG_BREAK == 0
            else BreakType.SHORT
        )
        print(
            f"✔  Pomodoro #{self._global_completed} completed  "
            f"[{session.ended_at:%H:%M:%S}]  "
            f"({session.duration_minutes:.1f} min)  →  {session.task.name}"
        )
        print(f"   Recommended break: {break_type.value}")
        return session, break_type

    def abandon_pomodoro(self) -> PomodoroSession:
        """Abandon the running session without counting it."""
        session = self.active_session
        if session is None:
            raise ValueError("No active session to abandon.")
        session.abandon()
        print(
            f"✘  Pomodoro abandoned  [{session.ended_at:%H:%M:%S}]  "
            f"→  {session.task.name}"
        )
        return session

    @property
    def total_pomodoros_today(self) -> int:
        return self._global_completed
    @property
    def total_time_today(self) -> timedelta:
        return sum((t.total_time for t in self._tasks), timedelta())

    #End-of-day summary 
    def end_of_day_summary(self) -> str:
        """
        Produce a formatted end-of-day report covering all tasks 
        """
        worked_tasks = [t for t in self._tasks if t.pomodoro_count > 0]
        total_min    = self.total_time_today.total_seconds() / 60
        lines: list[str] = []
        w = 60  # line width
        lines.append("═" * w)
        lines.append(f"  POMODORO DAILY SUMMARY  —  {self._owner}")
        lines.append(f"  {self._date:%A, %d %B %Y}")
        lines.append("═" * w)
        if not worked_tasks:
            lines.append("  No completed pomodoros recorded today.")
        else:
            lines.append(f"  {'Task':<30} {'Pomodoros':>10} {'Time (min)':>12}")
            lines.append("  " + "─" * (w - 2))
            for task in worked_tasks:
                lines.append(
                    f"  {task.name:<30} "
                    f"{'🍅 × ' + str(task.pomodoro_count):>10} "
                    f"{task.total_minutes:>11.0f}m"
                )
                if task.description:
                    lines.append(f"    ↳ {task.description}")
            lines.append("  " + "─" * (w - 2))
            lines.append(
                f"  {'TOTAL':<30} "
                f"{'🍅 × ' + str(self.total_pomodoros_today):>10} "
                f"{total_min:>11.0f}m"
            )
        lines.append("═" * w)
        return "\n".join(lines)

#Demo 
if __name__ == "__main__":
    import time

    tracker = PomodoroTracker(owner="Your Name")
    task1 = tracker.add_task("My Task", "description here")

    print("Pomodoro Tracker ready. Press Ctrl+C to quit.\n")

    while True:
        input(">> Press Enter to start a 25-min pomodoro...")
        session = tracker.start_pomodoro(task1)

        print(" Working... (25 minutes)")
        time.sleep(25 * 60)

        completed_session, break_type = tracker.complete_pomodoro()

        print()
        print(tracker.end_of_day_summary())
        print()

        # Determine break duration
        if break_type == BreakType.SHORT:
            break_secs = 5 * 60
            print(f"  Short break — 5 minutes. Relax!")
        else:
            break_secs = 20 * 60
            print(f" Long break — 20 minutes. Step away!")

        input(f">> Press Enter to start your break ({break_type.value})...")
        print(f"  Break started. See you in {break_secs // 60} minutes...")
        time.sleep(break_secs)
        print("  Break over! Ready for the next session.\n")
