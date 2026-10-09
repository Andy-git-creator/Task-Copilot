# Task Copilot
### Clear your plans. Capture your days.

**Task Copilot** 为学习、工作与生活留出各自的空间。打开主页，看看今天要做什么、下一节课在哪里、哪个截止日期正在临近。

忙碌之外，也留一点时间给自己：写一篇日记，记下运动后的畅快，收藏一杯喜欢的咖啡。值得记录的，不只有完成了多少任务，还有你怎样度过这一天。

**让重要的事有安排，让平凡的日子有记忆。**

---

**Task Copilot** gives study, work, and everyday life their own space. Open your home page to see what’s ahead, where your next class is, and which deadline is approaching. Then start with one small step and move at your own pace.

Leave some room for yourself, too. Write a diary entry, capture the feeling after a workout, or remember a coffee you loved. A day is worth recording for more than the tasks you finished.

---

## Features

### Home
- Current date and time
- Upcoming class
- Daily task statistics
- Nearest deadline
- Weekly focus time

### Workspace
- **Tasks:** Manage general tasks, assignments, exam preparation, and project tasks with priorities, deadlines, and subtasks.
- **Class Schedule:** Weekly and daily views, multiple sessions per course, teaching weeks, alternate-week schedules, and temporary adjustments.
- **Deadline Timeline:** View upcoming task and project deadlines over the next 7 or 30 days.
- **Projects:** Organize related tasks and track progress.
- **Focus Tracking:** Start, pause, and save focus sessions.
- **Analytics:** Review completion rates, recent trends, project progress, and accumulated focus time.

### Life Space
- **Diary:** Write personal entries with optional password protection.
- **Exercise:** Record activities, duration, and notes.
- **Coffee:** Keep a log of coffees, ratings, and tasting notes.

### Desktop Integration
- Windows system notifications
- A separate background reminder process
- Minimize to the system tray when closing the main window
- Tray controls to reopen the app, pause reminders, or exit

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React + Vite |
| Backend | Python |
| Desktop Window | pywebview |
| Database | SQLite |
| Tray & Notifications | pystray + winotify |

## Getting Started

### Requirements
- Windows
- Python 3.12
- Microsoft Edge WebView2 Runtime

### Installation
1. Download or clone this repository.
2. Run `setup.cmd` to create the Python environment and install dependencies.
3. Double-click `启动 Task Copilot.vbs` to launch the app.

The repository includes the built frontend. Node.js is only required when modifying and rebuilding the interface.

This is a source distribution, not a standalone executable.

## Local Data & Privacy

All application records are stored locally in `.local-data/taskcopilot.db`.

The distribution contains no personal records or prefilled schedules. A fresh installation starts with an empty database.

Optional diary passwords restrict access within the application. The database itself is **not encrypted**.

To back up your data, exit the app through the system tray before copying the database file.

## Development

Requires Node.js 20.19 or later.

```powershell
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe app.py
```

### Project Structure

```text
Task Copilot/
├── frontend/
│   ├── src/          # Interface and interactions
│   └── dist/         # Built frontend
├── backend/          # Local API and persistence
├── docs/             # Architecture and planning
├── tests/            # Basic tests
├── app.py            # Desktop window
├── agent.py          # Background reminders and tray
├── setup.cmd         # Dependency installation
└── requirements.txt
```

## Project Status

Task Copilot is an evolving MVP. The current version focuses on local desktop use, practical daily organization, and a modular foundation for future improvements.
