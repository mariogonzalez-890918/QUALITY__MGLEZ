import io,json,sqlite3,zipfile
import pytest
from app import create_app

@pytest.fixture
def env(tmp_path):
 app=create_app(tmp_path); app.config['TESTING']=True
 c=app.test_client(); c.get('/setup')
 def post(url,data=None):
  with c.session_transaction() as s:
   if 'csrf' not in s: s['csrf']='testtoken'
   token=s['csrf']
  return c.post(url,data={'_csrf':token,**(data or {})})
 assert post('/setup',{'token':(tmp_path/'setup-token.txt').read_text(),'razon_social':'Cartones de prueba','username':'admin','password':'Contraseña!123','confirm':'Contraseña!123'}).status_code==302
 assert post('/login',{'username':'admin','password':'Contraseña!123'}).status_code==302
 return app,c,post,tmp_path

def create(post,module='documents',**extra):
 response=post('/m/'+module+'/new',{'codigo':'DOC-001','titulo':'Inspección','area':'Calidad',**extra})
 assert response.status_code==302,response.data
 return int(response.location.rsplit('/',1)[1])

def test_health_and_csrf(env):
 app,c,p,root=env
 assert c.get('/health').json['status']=='ok'
 assert c.post('/m/documents/new',data={'titulo':'Ataque'}).status_code==400

@pytest.mark.parametrize('url',['/','/company','/users','/settings','/backups','/reports','/evidence','/events','/m/forms','/password'])
def test_pages(env,url): assert env[1].get(url).status_code==200

@pytest.mark.parametrize('role',['Calidad','Auditor','Visor'])
def test_roles(env,role):
 app,c,p,root=env
 assert p('/users',{'username':'other','name':'Otro','email':'test@example.com','password':'OtraClave!1234','role':role}).status_code==200
 p('/logout'); p('/login',{'username':'other','password':'OtraClave!1234'})
 assert c.get('/settings').status_code==403
 assert c.get('/users').status_code==403
 assert p('/backups').status_code==403
 response=p('/m/documents/new',{'codigo':'A','titulo':'Documento'})
 assert response.status_code==(302 if role=='Calidad' else 403)

def test_document_versions_and_approval(env):
 app,c,p,root=env; i=create(p)
 assert p(f'/item/{i}',{'op':'state','state':'en revisión'}).status_code==302
 assert p(f'/item/{i}',{'op':'state','state':'pendiente de aprobación'}).status_code==302
 assert p(f'/item/{i}',{'op':'state','state':'aprobado'}).status_code==403
 p('/users',{'username':'reviewer','password':'Revisor!123456','role':'Superusuario'})
 p('/logout'); p('/login',{'username':'reviewer','password':'Revisor!123456'})
 assert p(f'/item/{i}',{'op':'state','state':'aprobado'}).status_code==302
 assert p(f'/item/{i}',{'op':'state','state':'vigente'}).status_code==302
 assert p(f'/item/{i}',{'op':'edit','titulo':'Sobrescrito'}).status_code==409
 response=p(f'/item/{i}',{'op':'revision','motivo':'Mejora'})
 assert response.status_code==302
 with app.app_context():
  rows=app.db().execute('SELECT version,state FROM items ORDER BY id').fetchall()
  assert [tuple(r) for r in rows]==[(1,'vigente'),(2,'borrador')]

def test_form_record_required_evidence_and_closed_immutable(env):
 app,c,p,root=env
 i=create(p,'forms',label=['Lote','Foto'],type=['texto','fotografia'],required=['si','si'],options=['',''])
 with app.app_context(): app.db().execute("UPDATE items SET state='vigente' WHERE id=?",(i,)); app.db().commit()
 response=p('/m/records/new',{'form_id':str(i),'f1':'Lote 4'})
 assert response.status_code==302; r=int(response.location.rsplit('/',1)[1])
 assert p(f'/item/{r}',{'op':'state','state':'cerrado'}).status_code==409
 from PIL import Image
 b=io.BytesIO(); Image.new('RGB',(4,4),'red').save(b,'PNG'); b.seek(0)
 assert p(f'/item/{r}',{'op':'upload','f2':(b,'foto.png')}).status_code==302
 assert p(f'/item/{r}',{'op':'state','state':'cerrado'}).status_code==302
 assert p(f'/item/{r}',{'op':'upload','adjunto':(io.BytesIO(b'hello'),'a.txt')}).status_code==409
 assert c.get(f'/item/{r}/pdf').data.startswith(b'%PDF')

def test_invalid_file_and_duplicate(env):
 app,c,p,root=env; i=create(p)
 assert p(f'/item/{i}',{'op':'upload','adjunto':(io.BytesIO(b'MZ executable'),'fake.pdf')}).status_code==400
 assert p('/m/documents/new',{'codigo':'DOC-001','titulo':'Duplicado'}).status_code==409

def test_exports_backup(env):
 app,c,p,root=env; create(p)
 assert c.get('/export/documents/pdf').data.startswith(b'%PDF')
 raw=c.get('/export/documents/xlsx').data
 assert zipfile.is_zipfile(io.BytesIO(raw))
 assert p('/backups').status_code==200
 from launcher import verify_backup
 archive=next((root/'backups').glob('*.zip'))
 assert 'qualitylite.db' in verify_backup(archive)
 with zipfile.ZipFile(archive) as z:
  temp=root/'copy.db'; temp.write_bytes(z.read('qualitylite.db'))
 with sqlite3.connect(temp) as connection: assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_login_lockout(env):
 app,c,p,root=env; p('/logout')
 for n in range(5): assert p('/login',{'username':'admin','password':'bad'}).status_code==200
 assert p('/login',{'username':'admin','password':'Contraseña!123'}).status_code==403

def test_setup_requires_token_and_no_reentry(tmp_path):
 app=create_app(tmp_path); app.config['TESTING']=True; c=app.test_client(); c.get('/setup')
 with c.session_transaction() as s: token=s['csrf']
 assert c.post('/setup',data={'_csrf':token,'token':'incorrecto'}).status_code==403

def test_scheduled_backup(env):
 app,c,p,root=env
 with app.app_context():
  app.db().execute('INSERT INTO settings VALUES(?,?)',('backup_daily','true')); app.db().commit()
 app.scheduled_backup()
 assert len(list((root/'backups').glob('*.zip')))==1
 app.scheduled_backup()
 assert len(list((root/'backups').glob('*.zip')))==1

def test_audits_findings_actions(env):
 app,c,p,root=env
 for module in ['audits','findings','actions']:
  i=create(p,module,codigo=module,verificacion_eficacia='Eficacia comprobada')
  assert c.get(f'/item/{i}').status_code==200
  assert p(f'/item/{i}',{'op':'state','state':'cerrado'}).status_code==302

def test_port_conflict(env):
 import socket
 app,c,p,root=env
 with socket.socket() as s:
  s.bind(('127.0.0.1',0)); s.listen()
  assert p('/settings',{'host':'127.0.0.1','port':str(s.getsockname()[1])}).status_code==409

def test_restore_offline(env,monkeypatch):
 import launcher,sys,getpass,win32service
 app,c,p,root=env; create(p)
 with app.app_context(): archive=root/'backups'/app.backup()
 create(p,codigo='DOC-002')
 monkeypatch.setattr(launcher,'ROOT',root)
 monkeypatch.setattr(launcher.win32serviceutil,'QueryServiceStatus',lambda name:(0,win32service.SERVICE_STOPPED))
 monkeypatch.setattr(sys,'argv',['QualityLite.exe','--restore',str(archive)])
 answers=iter(['admin','RESTAURAR'])
 monkeypatch.setattr('builtins.input',lambda *args:next(answers))
 monkeypatch.setattr(getpass,'getpass',lambda *args:'Contraseña!123')
 launcher.main()
 with sqlite3.connect(root/'qualitylite.db') as connection:
  assert connection.execute('SELECT count(*) FROM items').fetchone()[0]==1
  assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

@pytest.mark.parametrize('role',['Auditor','Visor'])
def test_private_document_files(env,role):
 app,c,p,root=env; i=create(p)
 p(f'/item/{i}',{'op':'upload','adjunto':(io.BytesIO(b'Confidential text'),'private.txt')})
 with app.app_context(): f=app.db().execute('SELECT id FROM files').fetchone()[0]
 p('/users',{'username':'reader','password':'Reader!123456','role':role})
 p('/logout'); p('/login',{'username':'reader','password':'Reader!123456'})
 assert c.get(f'/item/{i}').status_code==403
 assert c.get(f'/file/{f}').status_code==403
 assert b'DOC-001' not in c.get('/m/documents').data
