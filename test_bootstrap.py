import json,sys,types
from pathlib import Path
import pytest
import bootstrap

def test_options_paths_with_spaces_and_non_ascii():
 args,options=bootstrap.parse_options(['--data-root','C:\\Datos Calidad\\área','--diagnostic-log','C:\\Temp\\error.log','--wait','30','start'])
 assert args==['--wait','30','start']
 assert options['--data-root']=='C:\\Datos Calidad\\área'

def test_missing_option_value():
 with pytest.raises(ValueError): bootstrap.parse_options(['--data-root'])

def test_public_connection_does_not_access_private_data(tmp_path):
 (tmp_path/'connection.json').write_text(json.dumps({'host':'0.0.0.0','port':8082,'name':'QualityLite'}))
 assert bootstrap.public_connection(tmp_path)=='http://127.0.0.1:8082'

@pytest.mark.parametrize('values',[{'host':'example.com','port':8080},{'host':'127.0.0.1','port':80}])
def test_public_connection_validation(tmp_path,values):
 (tmp_path/'connection.json').write_text(json.dumps(values))
 with pytest.raises(ValueError): bootstrap.public_connection(tmp_path)

def test_import_failure_logged_before_application_load(tmp_path,monkeypatch):
 import builtins
 original=builtins.__import__
 def importing(name,*args,**kwargs):
  if name=='launcher': raise ImportError('DLL de prueba ausente')
  return original(name,*args,**kwargs)
 monkeypatch.setattr(builtins,'__import__',importing)
 target=tmp_path/'boot.log'
 assert bootstrap.run(['--diagnostic-log',str(target),'--self-test'])==1
 assert 'DLL de prueba ausente' in target.read_text(encoding='utf-8')

def test_exit_code_is_preserved(tmp_path,monkeypatch):
 monkeypatch.setitem(sys.modules,'launcher',types.SimpleNamespace(main=lambda:1060,ROOT=tmp_path))
 log=tmp_path/'service.log'
 assert bootstrap.run(['--diagnostic-log',str(log),'--status'])==1060
 assert '1060' in log.read_text(encoding='utf-8')

def test_open_as_regular_user_uses_only_public_connection(tmp_path,monkeypatch):
 import http.client,os
 (tmp_path/'connection.json').write_text(json.dumps({'host':'127.0.0.1','port':8082}))
 monkeypatch.setattr(sys,'frozen',True,raising=False)
 monkeypatch.setattr(sys,'executable',str(tmp_path/'QualityLite.exe'))
 opened=[]; monkeypatch.setattr(os,'startfile',lambda url:opened.append(url))
 class HTTP:
  def __init__(self,*args,**kwargs): pass
  def request(self,*args): pass
  def getresponse(self): return types.SimpleNamespace(status=200,read=lambda:b'{"status":"ok"}')
  def close(self): pass
 monkeypatch.setattr(http.client,'HTTPConnection',HTTP)
 monkeypatch.setitem(sys.modules,'launcher',None)
 assert bootstrap.run(['--open'])==0
 assert opened==['http://127.0.0.1:8082']

def test_native_helper_has_no_external_runtime():
 import pefile
 path=Path(__file__).parent/'build'/'native'/'QualityLiteSetupHelper.exe'
 assert path.exists(),'Compile el ayudante nativo antes de probar'
 pe=pefile.PE(str(path))
 imports={module.dll.decode().lower() for module in pe.DIRECTORY_ENTRY_IMPORT}
 assert pe.FILE_HEADER.Machine==0x8664
 assert not any('vcruntime' in name or 'python' in name or 'msvcp' in name or 'mscoree' in name for name in imports)

def test_native_helper_reports_elevation(tmp_path):
 import ctypes,subprocess
 if ctypes.windll.shell32.IsUserAnAdmin(): pytest.skip('Esta prueba corresponde al usuario sin elevar')
 helper=Path(__file__).parent/'build'/'native'/'QualityLiteSetupHelper.exe'
 log=tmp_path/'helper.log'; target=tmp_path/'datos'; target.mkdir(); (target/'conservar.txt').write_text('original')
 result=subprocess.run([str(helper),'--root',str(target),'--log',str(log)],capture_output=True)
 assert result.returncode==740
 assert 'elevacion' in log.read_text(encoding='utf-8') or 'elevada' in log.read_text(encoding='utf-8')
 assert (target/'conservar.txt').read_text()=='original'
