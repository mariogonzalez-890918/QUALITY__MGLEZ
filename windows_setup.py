"""Configuración de ACL mediante Win32, sin icacls ni shell."""
import os
import stat
from pathlib import Path
import ntsecuritycon
import win32security

DATA_PRINCIPALS = (
 ('S-1-5-32-544', ntsecuritycon.FILE_ALL_ACCESS),
 ('S-1-5-18', ntsecuritycon.FILE_ALL_ACCESS),
 ('S-1-5-19', ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE
  | ntsecuritycon.FILE_GENERIC_EXECUTE | ntsecuritycon.DELETE
  | ntsecuritycon.FILE_DELETE_CHILD),
)

def data_acl(directory):
 acl=win32security.ACL()
 flags=(win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE) if directory else 0
 for sid,mask in DATA_PRINCIPALS:
  acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,flags,mask,win32security.ConvertStringSidToSid(sid))
 return acl

def secure_data(path):
 """Enumera primero; aplica ACL completas sin atravesar enlaces ni junctions."""
 root=Path(path).absolute()
 root.mkdir(parents=True,exist_ok=True)
 def check(target):
  info=target.lstat()
  if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
   raise ValueError('No se permiten enlaces ni junctions en los datos: '+str(target))
  return target.is_dir()
 targets=[(root,check(root))]
 def failed(error): raise error
 for directory,folders,files in os.walk(root,followlinks=False,onerror=failed):
  for name in folders+files:
   target=Path(directory)/name
   targets.append((target,check(target)))
 for target,directory in reversed(targets):
  win32security.SetNamedSecurityInfo(
   str(target),win32security.SE_FILE_OBJECT,
   win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
   None,None,data_acl(directory),None)
 return len(targets)
