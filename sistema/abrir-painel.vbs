' Abre o Painel do Editor de PDF sem janela de console
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "pyw -3 """ & pasta & "\painel.py""", 0, False