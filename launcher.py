import sys, os, json, logging, socket, time, shutil, zipfile, hashlib, sqlite3
from contextlib import closing
from pathlib import Path
from logging.handlers import RotatingFileHandler
import win32serviceutil, win32service, win32event, servicemanager
from app import create_app

ROOT=Path(os.environ.get('QUALITYLITE_DATA',str(Path(os.environ.get('PROGRAMDATA','.'))/'QualityLite'))).resolve()

def config():
 ROOT.mkdir(parents=True,exist_ok=True)
 path=ROOT/'server.json'
 if not path.exists():
  available=None
  for candidate in range(8080,8181):
   try:
    with socket.socket() as probe: probe.bind(('127.0.0.1',candidate))
    available=candidate; break
   except OSError: continue
  if available is None: raise RuntimeError('No hay un puerto libre entre 8080 y 8180')
  path.write_text(json.dumps({'host':'127.0.0.1','port':available,'name':'QualityLite'}))
 return json.loads(path.read_text(encoding='utf-8'))

def server():
 from waitress import create_server
 cfg=config(); app=create_app(ROOT)
 (ROOT/'logs').mkdir(exist_ok=True)
 handler=RotatingFileHandler(ROOT/'logs'/'qualitylite.log',maxBytes=2_000_000,backupCount=5,encoding='utf-8')
 logging.basicConfig(level=logging.INFO,handlers=[handler])
 import threading
 def schedule():
  while True:
   try: app.scheduled_backup()
   except Exception: logging.exception('Error en respaldo automático')
   time.sleep(60)
 threading.Thread(target=schedule,daemon=True).start()
 return create_server(app,host=cfg['host'],port=cfg['port'],threads=6,clear_untrusted_proxy_headers=True)

class QualityLiteService(win32serviceutil.ServiceFramework):
 _svc_name_='QualityLite'
 _svc_display_name_='QualityLite - Calidad e inocuidad'
 _svc_description_='Aplicación local de gestión documental, formatos y evidencias.'
 if getattr(sys,'frozen',False):
  import subprocess
  _exe_args_=subprocess.list2cmdline(['--data-root',str(ROOT)])
 def __init__(self,args):
  super().__init__(args); self.stop_event=win32event.CreateEvent(None,0,0,None); self.http=None
 def SvcStop(self):
  self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
  if self.http: self.http.close()
  win32event.SetEvent(self.stop_event)
 def SvcDoRun(self):
  import threading
  self.http=server()
  t=threading.Thread(target=self.http.run,daemon=True); t.start()
  servicemanager.LogInfoMsg('QualityLite iniciado')
  while win32event.WaitForSingleObject(self.stop_event,1000)==win32event.WAIT_TIMEOUT:
   if not t.is_alive(): raise RuntimeError('Servidor HTTP detenido inesperadamente')
  t.join(timeout=10)

def verify_backup(path):
 with zipfile.ZipFile(path) as z:
  manifest=json.loads(z.read('manifest.json'))
  if 'qualitylite.db' not in manifest: raise ValueError('Respaldo sin base de datos')
  for name,digest in manifest.items():
   parts=Path(name).parts
   if name.startswith(('/', '\\')) or ':' in name or '..' in parts: raise ValueError('Ruta no autorizada')
   if name not in ('qualitylite.db','secret.key','server.json') and not (name.startswith('files/') and len(name.split('/'))==2): raise ValueError('Contenido no autorizado')
   if hashlib.sha256(z.read(name)).hexdigest()!=digest: raise ValueError('Respaldo alterado: '+name)
  return manifest

def main():
 command=sys.argv[1] if len(sys.argv)>1 else ''
 if command=='--serve': server().run()
 elif command=='--self-test':
  import magic,psutil,platform
  from PIL import Image
  import app as application_module
  if os.name!='nt' or sys.maxsize<2**32 or sys.getwindowsversion().major<10:
   raise RuntimeError('Se requiere Windows 10/11 o Server 2016/2019/2022/2025 de 64 bits')
  magic.from_buffer(b'QualityLite\n',mime=True)
  psutil.net_if_addrs()
  with closing(sqlite3.connect(':memory:')) as connection: connection.execute('SELECT 1').fetchone()
  if not (Path(application_module.__file__).parent/'templates'/'setup.html').is_file():
   raise RuntimeError('Instalacion incompleta: faltan plantillas')
 elif command=='--publish-connection':
  cfg=config()
  directory=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
  target=directory/'connection.json'; pending=target.with_suffix('.tmp')
  pending.write_text(json.dumps({k:cfg[k] for k in ('host','port','name')}),encoding='utf-8')
  os.replace(pending,target)
 elif command=='--data-status':
  import ctypes
  if not ctypes.windll.shell32.IsUserAnAdmin(): raise PermissionError('Diagnostico local exclusivo de administradores')
  with closing(sqlite3.connect((ROOT/'qualitylite.db').as_uri()+'?mode=ro',uri=True)) as connection:
   counts={table:connection.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('users','items','files','settings')}
   counts['integrity']=connection.execute('PRAGMA quick_check').fetchone()[0]
  print(json.dumps(counts))
 elif command=='--secure-data':
  import ctypes
  from windows_setup import secure_data
  if not ctypes.windll.shell32.IsUserAnAdmin():
   raise PermissionError('La configuración de permisos requiere un administrador de Windows')
  secure_data(ROOT)
 elif command=='--init':
  cfg=config(); create_app(ROOT)
  with socket.socket() as s: s.bind((cfg['host'],cfg['port']))
 elif command=='--open':
  import webbrowser
  cfg=config(); host='127.0.0.1' if cfg['host']=='0.0.0.0' else cfg['host']; webbrowser.open(f"http://{host}:{cfg['port']}")
 elif command=='--health':
  from http.client import HTTPConnection
  cfg=config(); host='127.0.0.1' if cfg['host']=='0.0.0.0' else cfg['host']
  last_error=''
  for _ in range(30):
   try:
    connection=HTTPConnection(host,cfg['port'],timeout=2)
    connection.request('GET','/health'); response=connection.getresponse()
    payload=json.loads(response.read()); connection.close()
    if response.status==200 and payload.get('status')=='ok': return
    last_error=str(payload)
   except Exception as exc: last_error=repr(exc)
   time.sleep(1)
  raise RuntimeError('El servicio no responde a la comprobación de salud: '+last_error)
 elif command=='--restore':
  import getpass
  if len(sys.argv)!=3: raise ValueError('Indique la ruta del respaldo')
  try:
   if win32serviceutil.QueryServiceStatus('QualityLite')[1]!=win32service.SERVICE_STOPPED: raise ValueError('Detenga el servicio antes de restaurar')
  except win32service.error as e:
   if e.winerror!=1060: raise
  user=input('Superusuario: '); password=getpass.getpass('Contraseña: ')
  from werkzeug.security import check_password_hash
  with closing(sqlite3.connect(ROOT/'qualitylite.db')) as db:
   row=db.execute("SELECT hash FROM users WHERE username=? AND role='Superusuario' AND active=1",(user,)).fetchone()
  if not row or not check_password_hash(row[0],password): raise ValueError('Credenciales inválidas')
  manifest=verify_backup(sys.argv[2])
  if input('Escriba RESTAURAR para confirmar: ')!='RESTAURAR': return
  app=create_app(ROOT)
  with app.app_context(): app.backup()
  stage=ROOT/'restore-stage'; stage.mkdir(exist_ok=False)
  try:
   with zipfile.ZipFile(sys.argv[2]) as z:
    for name in manifest:
     dest=stage/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(z.read(name))
   with closing(sqlite3.connect(stage/'qualitylite.db')) as db:
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Base de datos dañada')
   for suffix in ('-wal','-shm'): (ROOT/('qualitylite.db'+suffix)).unlink(missing_ok=True)
   for name in manifest:
    dest=ROOT/name; dest.parent.mkdir(parents=True,exist_ok=True); os.replace(stage/name,dest)
  finally: shutil.rmtree(stage)
  print('Restauración terminada. Inicie el servicio.')
 elif command=='--recover':
  import ctypes,getpass
  if not ctypes.windll.shell32.IsUserAnAdmin(): raise PermissionError('Recuperación exclusiva de administradores locales de Windows')
  name=input('Usuario superusuario existente: '); p=getpass.getpass('Nueva contraseña (12 caracteres): ')
  if len(p)<12 or p!=getpass.getpass('Confirme: '): raise ValueError('Contraseña inválida')
  from werkzeug.security import generate_password_hash
  with closing(sqlite3.connect(ROOT/'qualitylite.db')) as db:
   cur=db.execute("UPDATE users SET hash=? WHERE username=? AND role='Superusuario'",(generate_password_hash(p),name))
   if cur.rowcount!=1: raise ValueError('Superusuario no encontrado')
   db.execute("INSERT INTO events(action,detail,created) VALUES('recuperacion_local',?,datetime('now'))",(name,))
   db.commit()
 elif any(c in sys.argv[1:] for c in ('install','update','remove','start','stop','restart','debug')):
  (ROOT/'logs').mkdir(parents=True,exist_ok=True)
  from contextlib import redirect_stdout,redirect_stderr
  with (ROOT/'logs'/'service-commands.log').open('a',encoding='utf-8') as output:
   with redirect_stdout(output),redirect_stderr(output):
    result=win32serviceutil.HandleCommandLine(QualityLiteService)
  return result
 elif command=='--status': print(win32serviceutil.QueryServiceStatus('QualityLite'))
 elif not command:
  servicemanager.Initialize(); servicemanager.PrepareToHostSingle(QualityLiteService); servicemanager.StartServiceCtrlDispatcher()
 else: raise ValueError('Comando desconocido')

if __name__=='__main__':
 try: sys.exit(main() or 0)
 except Exception:
  import traceback,tempfile
  message=traceback.format_exc()
  for destination in (ROOT/'launcher-error.log',Path(tempfile.gettempdir())/'QualityLite-install-error.log'):
   try:
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('a',encoding='utf-8') as output: output.write(message+'\n')
    break
   except OSError: continue
  if sys.stderr: sys.stderr.write(message)
  sys.exit(1)
