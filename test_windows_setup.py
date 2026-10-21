from pathlib import Path
import sys
import pytest
import win32security
import ntsecuritycon
from windows_setup import secure_data, DATA_PRINCIPALS

def test_acl_on_real_empty_directory(tmp_path):
 # Reproduce el caso vacío que fallaba con icacls /T, sin necesitar elevación.
 path=tmp_path/'datos'; path.mkdir()
 original=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
 try:
  assert secure_data(path)==1
  descriptor=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
  acl=descriptor.GetSecurityDescriptorDacl()
  assert acl.GetAceCount()==3
  actual={win32security.ConvertSidToStringSid(acl.GetAce(i)[2]):acl.GetAce(i)[1] for i in range(3)}
  assert actual==dict(DATA_PRINCIPALS)
  assert descriptor.GetSecurityDescriptorControl()[0] & win32security.SE_DACL_PROTECTED
 finally:
  win32security.SetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
   win32security.DACL_SECURITY_INFORMATION|win32security.UNPROTECTED_DACL_SECURITY_INFORMATION,
   None,None,original.GetSecurityDescriptorDacl(),None)

def test_acl_existing_files_preserve_contents(tmp_path):
 root=tmp_path/'datos'; root.mkdir(); folder=root/'evidencias'; folder.mkdir()
 file=folder/'original.txt'; file.write_text('Conservar evidencia',encoding='utf-8')
 targets=[root,folder,file]
 originals={p:win32security.GetNamedSecurityInfo(str(p),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION) for p in targets}
 try:
  assert secure_data(root)==3
  for p in targets:
   acl=win32security.GetNamedSecurityInfo(str(p),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl()
   assert acl.GetAceCount()==3
 finally:
  for p in targets:
   win32security.SetNamedSecurityInfo(str(p),win32security.SE_FILE_OBJECT,
    win32security.DACL_SECURITY_INFORMATION|win32security.UNPROTECTED_DACL_SECURITY_INFORMATION,
    None,None,originals[p].GetSecurityDescriptorDacl(),None)
 assert file.read_text(encoding='utf-8')=='Conservar evidencia'

def test_service_error_code_is_returned(tmp_path,monkeypatch):
 import launcher
 monkeypatch.setattr(launcher,'ROOT',tmp_path)
 monkeypatch.setattr(sys,'argv',['QualityLite.exe','start'])
 monkeypatch.setattr(launcher.win32serviceutil,'HandleCommandLine',lambda cls:5)
 assert launcher.main()==5

def test_installer_uses_native_acl_and_waits():
 text=(Path(__file__).parent/'installer.iss').read_text(encoding='utf-8')
 assert 'icacls.exe' not in text
 assert "'--secure-data'" in text
 assert "'--wait 30 start'" in text
 assert "'--wait 30 stop'" in text
 assert 'SetupLogging=yes' in text
