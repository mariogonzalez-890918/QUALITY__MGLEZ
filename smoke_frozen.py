"""Prueba real HTTP del binario congelado, aislada de ProgramData y sin servicio."""
import subprocess,os,json,socket,time,re,secrets,urllib.request,urllib.parse,http.cookiejar
from pathlib import Path
from datetime import datetime

root=Path(__file__).parent.resolve()
data=root/'test-data'/('frozen-'+datetime.now().strftime('%Y%m%d%H%M%S')); data.mkdir(parents=True)
with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
(data/'server.json').write_text(json.dumps({'host':'127.0.0.1','port':port,'name':'QualityLite prueba'}))
exe=root/'dist'/'QualityLite'/'QualityLite.exe'
env=os.environ.copy(); env['QUALITYLITE_DATA']=str(data); env['PATH']=str(Path(os.environ['WINDIR'])/'System32')
env.pop('PYTHONHOME',None); env.pop('PYTHONPATH',None)
url=f'http://127.0.0.1:{port}'
results=[]
def record(name): results.append(name); print('OK',name,flush=True)
subprocess.run([str(exe),'--init'],env=env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
record('Ejecutable --init sin Python en PATH')
process=subprocess.Popen([str(exe),'--serve'],env=env,creationflags=subprocess.CREATE_NO_WINDOW)
try:
 for _ in range(45):
  try:
   with urllib.request.urlopen(url+'/health',timeout=2) as r: assert json.load(r)['status']=='ok'
   break
  except OSError:
   if process.poll() is not None: raise RuntimeError('Ejecutable terminó antes de responder')
   time.sleep(1)
 else: raise RuntimeError('Tiempo de arranque excedido')
 record('Waitress responde por HTTP real')
 subprocess.run([str(exe),'--health'],env=env,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 record('Comprobación de salud del ejecutable')
 jar=http.cookiejar.CookieJar(); client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
 def get(path):
  with client.open(url+path,timeout=15) as r: return r.read()
 def post(path,values):
  page=get(path).decode(); token=re.search(r'name="_csrf" value="([^"]+)"',page)[1]
  payload=urllib.parse.urlencode({'_csrf':token,**values},doseq=True).encode()
  with client.open(url+path,payload,timeout=20) as r: return r.url,r.read()
 get('/setup'); password=secrets.token_urlsafe(24)
 post('/setup',{'token':(data/'setup-token.txt').read_text(),'razon_social':'Empresa de prueba aislada','username':'prueba','password':password,'confirm':password})
 record('Asistente inicial HTTP y token local')
 post('/login',{'username':'prueba','password':password})
 assert 'Todo listo'.encode() in get('/')
 record('Inicio de sesión y tablero')
 for path in ['/company','/users','/settings','/backups','/m/documents','/m/forms/new','/reports','/evidence','/events','/static/style.css','/static/app.js']:
  assert get(path)
 record('Plantillas y recursos estáticos empaquetados')
 location,body=post('/m/documents/new',{'codigo':'DOC-SMOKE','titulo':'Documento de prueba','area':'Calidad'})
 assert '/item/' in location
 record('Creación documental persistente')
 assert get('/export/documents/pdf').startswith(b'%PDF')
 assert get('/export/documents/xlsx').startswith(b'PK')
 record('PDF y Excel desde binario congelado')
 post('/backups',{})
 assert list((data/'backups').glob('*.zip'))
 record('Respaldo completo desde HTTP real')
 result={'date':datetime.now().isoformat(),'result':'passed','checks':results,'data_directory':str(data),'port':port,'note':'Proceso de prueba, no servicio Windows. Instalador no ejecutado.'}
 (root/'release'/'prueba-ejecutable.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
 process.terminate(); process.wait(timeout=15)
