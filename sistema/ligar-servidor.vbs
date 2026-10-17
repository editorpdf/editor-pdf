' Liga o servidor do Editor de PDF (se estiver desligado), sem janela
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "pyw -3 """ & pasta & "\painel.py"" --ligar", 0, False