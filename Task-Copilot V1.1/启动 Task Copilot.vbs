Option Explicit

Dim shell, files, root, pythonw, launcher, dataDir
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")

root = files.GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
launcher = root & "\start.pyw"
dataDir = root & "\.local-data"

If Not files.FileExists(pythonw) Then
  MsgBox "Python 环境不存在，请先按 README 安装依赖。", 16, "Task Copilot"
  WScript.Quit 1
End If

If Not files.FileExists(root & "\frontend\dist\index.html") Then
  MsgBox "前端尚未构建，请先在 frontend 目录运行 npm run build。", 16, "Task Copilot"
  WScript.Quit 1
End If

If Not files.FolderExists(dataDir) Then files.CreateFolder(dataDir)
shell.CurrentDirectory = root
shell.Environment("PROCESS")("TASK_COPILOT_DATA_DIR") = dataDir
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & launcher & Chr(34), 0, False
