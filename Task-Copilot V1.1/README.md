# Task Copilot V1.1

Windows 本地学习、工作与生活管理应用。此版本保存于 UI 改版之前。

## 功能

- 今日概览、课程表、任务与子任务、DDL 时间轴、项目进度、数据分析。
- 专注计时（包含电脑睡眠和休眠时间，手动暂停除外）。
- 生活空间：日记手札、运动记录、咖啡时光。日记可设置访问密码，数据库未加密。
- 浅色、深色、跟随系统主题。
- 课程提醒、任务多时点提醒、可调整间隔的久坐提醒；独立后台进程与系统托盘。

## 首次启动

需要 Windows、Python 3.12 和 Microsoft Edge WebView2 Runtime。

1. 双击 `setup.cmd` 安装 Python 依赖，需要网络。
2. 双击 `启动 Task Copilot.vbs` 打开应用。

已包含构建后的前端，日常使用无需 Node.js。这是源码包，不是免安装 EXE。

## 数据

本包不含数据库、课程、任务、项目、专注历史、日记、运动、咖啡记录、昵称、头像、密码、日志或 Git 历史。
首次启动使用本包目录下的新 `.local-data`，不读取其他目录的旧数据。所有业务数据为空。
请勿上传 `.local-data`、数据库、日志或 `.venv`。

## 开发

前端开发需要 Node.js 20.19+。

```powershell
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe app.py
```

技术栈：React + Vite、Python + pywebview、SQLite。
