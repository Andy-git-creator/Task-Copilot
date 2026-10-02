# Task Copilot

Windows 本地学习、任务与生活记录桌面应用。

技术栈：React + Vite、Python + pywebview、SQLite。支持 Windows 系统通知和独立托盘提醒进程。

## 功能

- 主页：今日概览、时间、下一节课、任务统计、最近 DDL、本周专注时长。
- 工作空间：任务、DDL 时间轴、周课表和今日课表、项目、自由专注计时、数据分析。
- 课表支持多时段、单双周、周次与临时调课。临时调课中的“取消”撤销调整；“删除”仅移除记录，保留课表调整。
- 生活空间：日记手札、运动记录、咖啡时光，支持记录的新增、编辑和删除。
- 日记可选择密码打开。密码保护应用内访问，数据库未加密。离开日记页面或打开30分钟后自动锁定。
- 关闭主窗口隐藏至托盘，提醒进程继续运行；托盘可打开主窗口、暂停提醒、完全退出。

## 首次运行

需要 Windows、Python 3.12 和 Microsoft Edge WebView2 Runtime。

1. 下载或克隆本仓库到一个新的文件夹。
2. 双击 `setup.cmd`，创建 Python 虚拟环境并安装依赖（需要网络）。
3. 双击 `启动 Task Copilot.vbs` 打开应用。启动异常时可使用 `run.cmd`。

已附带构建好的 `frontend/dist`，正常启动无需安装 Node.js。
这是源码发布包，未包含 Python 运行时，也不是免安装 EXE。

## 数据与隐私

发布包不包含数据库、个人昵称或头像、课程、任务、日记、运动、咖啡记录、密码或日志，也不包含原仓库 Git 历史。
首次启动会在本发布包的 `.local-data` 下创建空白数据库，不会读取其他目录的旧数据。
若自行设置 `TASK_COPILOT_DATA_DIR`，应用将使用指定目录。

`.gitignore` 已排除数据库、日志、个人数据目录和运行环境。不要手动上传这些文件。
备份前请从托盘退出应用，再复制 `.local-data/taskcopilot.db`。

## 前端开发

需要 Node.js 20.19+。

```powershell
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe app.py
```

构建后提交 `frontend/dist`，让下载仓库的用户可直接安装 Python 依赖后运行。

## 结构

- `frontend/src`：界面与交互；`frontend/dist`：构建产物。
- `backend`：本地 API、数据持久化、IPC。
- `app.py`：桌面主窗口；`agent.py`：独立提醒与托盘进程。
- `tests`：基础测试；`docs`：架构和 MVP 规划。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
