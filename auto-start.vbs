Option Explicit
' Live Banner Studio auto-start (called at Windows logon)
' Starts the local server hidden. The site opens only when you launch it.
Dim fso, sh, base, url, up
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = base
url = "http://127.0.0.1:8090/index.html"

' already running?
up = False
On Error Resume Next
Dim http
Set http = CreateObject("MSXML2.XMLHTTP")
http.open "GET", url, False
http.send
If Err.Number = 0 And http.status = 200 Then up = True
Err.Clear
On Error GoTo 0

' start server hidden only if not already up
If Not up Then
  sh.Run "cmd /c python serve.py", 0, False
  WScript.Sleep 5000
End If
