"""QualityLite: servidor local y almacenamiento persistente."""
import os, json, sqlite3, secrets, hashlib, io, zipfile, threading, socket
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, abort, send_file, g, flash, has_request_context
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
from branding import save_logo
from form_models import SERVICE_MODEL,schema_from_form,table_value
from formal_pdf import render_pdf
from formal_excel import export_excel

MODULES = {'documents':'Documentos','forms':'Diseñador de formatos','records':'Registros','audits':'Auditorías','findings':'No conformidades','actions':'Acciones correctivas'}
ROLES = ('Superusuario','Calidad','Auditor','Visor')
FIELDS = {
 'documents':['codigo','titulo','tipo','area','proceso','elaborador','revisor','aprobador','fecha_vigencia','proxima_revision','motivo'],
 'forms':['codigo','titulo','area','responsable','descripcion','instrucciones'],
 'audits':['titulo','fecha','alcance','proceso','auditor','lista_verificacion'],
 'findings':['titulo','area','proceso','descripcion','clasificacion','auditoria','responsable','fecha_compromiso','causa','accion_inmediata'],
 'actions':['titulo','no_conformidad','responsable','fecha_compromiso','accion_correctiva','verificacion_eficacia']}
TYPES = ['texto','texto_largo','fecha','hora','numero','lista','multiple','casilla','si_no_na','responsable','tabla','fotografia','archivo','evidencia','comentarios','observaciones']
LOCK = threading.RLock()

def create_app(data_dir=None):
 root = Path(data_dir or os.environ.get('QUALITYLITE_DATA', str(Path(os.environ.get('PROGRAMDATA','.'))/'QualityLite'))).resolve()
 root.mkdir(parents=True,exist_ok=True)
 for folder in ('files','backups','logs'): (root/folder).mkdir(exist_ok=True)
 secret = root/'secret.key'
 if not secret.exists(): secret.write_text(secrets.token_hex(32))
 app=Flask(__name__)
 app.config.update(SECRET_KEY=secret.read_text(),MAX_CONTENT_LENGTH=25*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),ROOT=root)
 def db():
  if 'db' not in g:
   g.db=sqlite3.connect(root/'qualitylite.db',timeout=30)
   g.db.row_factory=sqlite3.Row
   g.db.execute('PRAGMA foreign_keys=ON')
  return g.db
 app.db=db
 with app.app_context():
  db().executescript('''PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,name TEXT,email TEXT,hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY,module TEXT NOT NULL,code TEXT NOT NULL,title TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,state TEXT NOT NULL DEFAULT 'borrador',data TEXT NOT NULL,owner INTEGER NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL,UNIQUE(module,code,version));
  CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY,item INTEGER NOT NULL REFERENCES items(id),field TEXT,name TEXT,path TEXT UNIQUE,mime TEXT,sha256 TEXT,owner INTEGER,created TEXT);
  CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,user INTEGER,action TEXT,item INTEGER,detail TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS attempts(ip TEXT PRIMARY KEY,count INTEGER,last TEXT);
  PRAGMA user_version=1;''')
  db().commit()
  db().close(); g.pop('db',None)
 def setting(k,default=None):
  row=db().execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone()
  return json.loads(row[0]) if row else default
 def setval(k,v): db().execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,json.dumps(v,ensure_ascii=False)))
 def event(action,item=None,detail=''):
  db().execute('INSERT INTO events(user,action,item,detail,created) VALUES(?,?,?,?,?)',(session.get('uid') if has_request_context() else None,action,item,detail,datetime.now().isoformat(timespec='seconds')))
 def brand_snapshot(): return {'company':setting('company',{}),'branding':setting('branding',{})}
 def update_branding():
  values=setting('branding',{})
  values.update(department=request.form.get('brand_department',values.get('department',''))[:160],footer=request.form.get('brand_footer',values.get('footer',''))[:220])
  file=request.files.get('logo')
  if file and file.filename:
   try: values['logo']=save_logo(root,file)
   except ValueError as error: abort(400,str(error))
  setval('branding',values)
 def allowed(module,write=False):
  role=g.user['role'] if g.get('user') else ''
  return role=='Superusuario' or (not write and module not in ('users','settings','backups','events','company')) or (role=='Calidad' and module in MODULES) or (role=='Auditor' and module in ('audits','findings','records'))
 def require(module,write=False):
  if not allowed(module,write): abort(403)
 def item(i):
  row=db().execute('SELECT * FROM items WHERE id=?',(i,)).fetchone()
  if not row: abort(404)
  require(row['module'])
  if g.user['role']=='Visor' and row['state'] not in ('vigente','cerrado'): abort(403)
  if g.user['role']=='Auditor' and row['module'] in ('documents','forms') and row['state'] not in ('vigente','aprobado'): abort(403)
  return dict(row)
 def csrf():
  if 'csrf' not in session: session['csrf']=secrets.token_hex(32)
  return session['csrf']
 app.jinja_env.globals.update(csrf=csrf,modules=MODULES,allowed=allowed,fields=FIELDS,types=TYPES,loads=json.loads,company_brand=lambda:setting('branding',{}),company_data=lambda:setting('company',{}),field_labels=__import__('formal_pdf').LABELS)
 def ordered_sections(schema):
  groups={}
  for field in schema: groups.setdefault(field.get('section') or 'Datos del formato',[]).append(field)
  return [{'grouper':key,'list':value} for key,value in groups.items()]
 app.jinja_env.filters['sections']=ordered_sections
 @app.teardown_appcontext
 def close(exc):
  connection=g.pop('db',None)
  if connection: connection.close()
  if g.pop('mutation_lock',False): LOCK.release()
 @app.before_request
 def guard():
  if request.method=='POST': LOCK.acquire(); g.mutation_lock=True
  g.user=db().execute('SELECT * FROM users WHERE id=? AND active=1',(session.get('uid'),)).fetchone()
  if request.method=='POST' and not secrets.compare_digest(session.get('csrf','!'),request.form.get('_csrf','')): abort(400,'Token CSRF inválido')
  if request.endpoint in ('static','health'): return
  if not setting('initialized'):
   if request.endpoint!='setup': return redirect(url_for('setup'))
  elif request.endpoint=='setup': return redirect(url_for('home'))
  elif not g.user and request.endpoint!='login': return redirect(url_for('login'))
 @app.after_request
 def headers(response):
  response.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data: blob:; frame-ancestors 'none'",'Cache-Control':'no-store'})
  return response
 @app.errorhandler(400)
 @app.errorhandler(403)
 @app.errorhandler(404)
 @app.errorhandler(409)
 @app.errorhandler(413)
 def error(e): return render_template('error.html',error=e),e.code
 @app.get('/health')
 def health():
  db().execute('SELECT 1').fetchone()
  return {'status':'ok','application':'QualityLite'}
 @app.route('/setup',methods=['GET','POST'])
 def setup():
  # El asistente solamente se puede completar desde el servidor y con token local.
  tokenfile=root/'setup-token.txt'
  if not tokenfile.exists(): tokenfile.write_text(secrets.token_urlsafe(24))
  if request.method=='POST':
   if request.remote_addr not in ('127.0.0.1','::1') or not secrets.compare_digest(request.form.get('token',''),tokenfile.read_text().strip()): abort(403,'Se requiere acceso local y el token de instalación')
   password=request.form.get('password','')
   if len(password)<12 or password!=request.form.get('confirm'): abort(400,'Contraseña: mínimo 12 caracteres y confirmación idéntica')
   if not request.form.get('razon_social') or not request.form.get('username'): abort(400)
   with LOCK:
    if setting('initialized'): abort(409)
    update_branding()
    db().execute('INSERT INTO users(username,name,email,hash,role) VALUES(?,?,?,?,?)',(request.form['username'],request.form.get('nombre'),request.form.get('email'),generate_password_hash(password),'Superusuario'))
    setval('company',{k:request.form.get(k,'') for k in ('razon_social','nombre_comercial','rfc','domicilio','telefono','email','responsable_calidad','responsable_inocuidad','giro','productos','alcance','normas','areas')})
    setval('initialized',True); event('configuracion_inicial'); db().commit()
   tokenfile.unlink(missing_ok=True)
   flash('Empresa y superusuario creados. Inicie sesión.'); return redirect(url_for('login'))
  return render_template('setup.html',token_path=str(tokenfile))
 @app.route('/login',methods=['GET','POST'])
 def login():
  if request.method=='POST':
   ip=request.remote_addr
   attempt=db().execute('SELECT * FROM attempts WHERE ip=?',(ip,)).fetchone()
   if attempt and attempt['count']>=5 and datetime.fromisoformat(attempt['last'])>datetime.now()-timedelta(minutes=15): abort(403,'Espere 15 minutos antes de volver a intentar')
   user=db().execute('SELECT * FROM users WHERE username=? AND active=1',(request.form.get('username'),)).fetchone()
   if user and check_password_hash(user['hash'],request.form.get('password','')):
    session.clear(); session['uid']=user['id']; session.permanent=True
    db().execute('DELETE FROM attempts WHERE ip=?',(ip,)); event('inicio_sesion'); db().commit(); return redirect(url_for('home'))
   count=attempt['count']+1 if attempt and datetime.fromisoformat(attempt['last'])>datetime.now()-timedelta(minutes=15) else 1
   db().execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(ip,count,datetime.now().isoformat())); event('acceso_denegado'); db().commit(); flash('Credenciales incorrectas')
  return render_template('login.html')
 @app.post('/logout')
 def logout(): session.clear(); return redirect(url_for('login'))
 @app.route('/password',methods=['GET','POST'])
 def password():
  if request.method=='POST':
   p=request.form.get('password','')
   if not check_password_hash(g.user['hash'],request.form.get('current','')) or len(p)<12 or p!=request.form.get('confirm'): abort(400,'Revise la contraseña actual y la nueva confirmación (12 caracteres mínimo)')
   db().execute('UPDATE users SET hash=? WHERE id=?',(generate_password_hash(p),g.user['id'])); event('cambio_contrasena'); db().commit(); session.clear(); return redirect(url_for('login'))
  return render_template('password.html')
 @app.get('/')
 def home():
  counts={k:db().execute('SELECT count(*) FROM items WHERE module=?',(k,)).fetchone()[0] for k in MODULES}
  return render_template('home.html',counts=counts,company=setting('company',{}))
 @app.get('/m/<module>')
 def listing(module):
  if module not in MODULES: abort(404)
  require(module)
  q=request.args.get('q','')
  rows=db().execute('SELECT * FROM items WHERE module=? AND (title LIKE ? OR code LIKE ? OR data LIKE ?) ORDER BY id DESC',(module,*(['%'+q+'%']*3))).fetchall()
  if g.user['role']=='Visor': rows=[r for r in rows if r['state'] in ('vigente','cerrado')]
  if g.user['role']=='Auditor' and module in ('documents','forms'): rows=[r for r in rows if r['state'] in ('vigente','aprobado')]
  return render_template('listing.html',module=module,rows=rows,q=q)
 @app.route('/m/<module>/new',methods=['GET','POST'])
 def new(module):
  if module not in MODULES: abort(404)
  require(module,True)
  forms=db().execute("SELECT * FROM items WHERE module='forms' AND state='vigente'").fetchall()
  form=None
  if module=='records' and request.values.get('form_id'):
   form=item(int(request.values['form_id']))
   if form['module']!='forms' or form['state']!='vigente': abort(400)
  if request.method=='POST':
   data={k:request.form.get(k,'') for k in FIELDS.get(module,[])}
   if module=='forms':
    try: data['schema']=schema_from_form(request.form,TYPES)
    except ValueError as error: abort(400,str(error))
   if module=='records':
    if not form: abort(400,'Seleccione formato vigente')
    data={'form_id':form['id'],'form_code':form['code'],'form_version':form['version'],'schema':json.loads(form['data'])['schema'],'answers':{}}
    for f in data['schema']:
     value=request.form.getlist(f['id']) if f['type']=='multiple' else request.form.get(f['id'],'')
     if f['type']=='tabla':
      try: value=table_value(value,f.get('options',[]))
      except ValueError as error: abort(400,str(error))
     if f['required'] and f['type'] not in ('archivo','fotografia','evidencia') and not value: abort(400,'Campo obligatorio: '+f['label'])
     if f['type']=='numero' and value:
      try: float(value)
      except ValueError: abort(400,'Número inválido')
     data['answers'][f['id']]=value
   data['_brand']=brand_snapshot()
   now=datetime.now().isoformat(timespec='seconds')
   code=request.form.get('codigo','').strip() or module.upper()+'-'+secrets.token_hex(5).upper()
   title=request.form.get('titulo','').strip() or (form['title'] if form else '')
   if not title: abort(400,'Título obligatorio')
   if len(title)>160 or len(code)>80: abort(400,'Título o código demasiado largo')
   try:
    cur=db().execute('INSERT INTO items(module,code,title,data,owner,created,updated) VALUES(?,?,?,?,?,?,?)',(module,code,title,json.dumps(data,ensure_ascii=False),g.user['id'],now,now))
    upload(cur.lastrowid,data.get('schema',[])); event('creacion',cur.lastrowid); db().commit()
   except sqlite3.IntegrityError: abort(409,'Código ya existente')
   return redirect(url_for('detail',i=cur.lastrowid))
  return render_template('edit.html',module=module,forms=forms,form=form,model=SERVICE_MODEL if module=='forms' and request.args.get('model')=='service' else None)
 def upload(i,schema=()):
  import magic
  for field in request.files:
   for f in request.files.getlist(field):
    if not f.filename: continue
    raw=f.read(); name=secure_filename(f.filename); ext=Path(name).suffix.lower()
    mime=magic.from_buffer(raw,mime=True)
    good={'.pdf':{'application/pdf'},'.png':{'image/png'},'.jpg':{'image/jpeg'},'.jpeg':{'image/jpeg'},'.xlsx':{'application/zip','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},'.docx':{'application/zip','application/vnd.openxmlformats-officedocument.wordprocessingml.document'},'.txt':{'text/plain'}}
    if ext not in good or mime not in good[ext] or not raw: abort(400,'Tipo real de archivo no autorizado')
    if ext in ('.xlsx','.docx'):
     try:
      with zipfile.ZipFile(io.BytesIO(raw)) as z:
       prefix='xl/' if ext=='.xlsx' else 'word/'
       if '[Content_Types].xml' not in z.namelist() or not any(n.startswith(prefix) for n in z.namelist()) or any('vbaProject' in n for n in z.namelist()): abort(400,'Documento Office no válido o con macros')
     except zipfile.BadZipFile: abort(400)
    filename=secrets.token_hex(24)+ext; (root/'files'/filename).write_bytes(raw)
    db().execute('INSERT INTO files(item,field,name,path,mime,sha256,owner,created) VALUES(?,?,?,?,?,?,?,?)',(i,field,name,filename,mime,hashlib.sha256(raw).hexdigest(),g.user['id'],datetime.now().isoformat()))
    event('carga_evidencia',i,name)
 @app.route('/item/<int:i>',methods=['GET','POST'])
 def detail(i):
  row=item(i); data=json.loads(row['data'])
  if request.method=='POST':
   require(row['module'],True)
   with LOCK:
    row=item(i)
    if row['state'] in ('cerrado','obsoleto'): abort(409,'Registro inmutable')
    op=request.form.get('op')
    if op=='upload':
     if row['state'] in ('aprobado','vigente'): abort(409,'Cree una nueva versión para cambiar adjuntos')
     upload(i)
    elif op=='revision':
     if row['module'] not in ('documents','forms') or row['state'] not in ('vigente','aprobado'): abort(409)
     reason=request.form.get('motivo','').strip()
     if not reason: abort(400,'Indique el motivo')
     data['motivo']=reason
     for key in FIELDS[row['module']]:
      if key in request.form: data[key]=request.form[key]
     version=db().execute('SELECT max(version)+1 FROM items WHERE module=? AND code=?',(row['module'],row['code'])).fetchone()[0]
     now=datetime.now().isoformat()
     cur=db().execute('INSERT INTO items(module,code,title,version,data,owner,created,updated) VALUES(?,?,?,?,?,?,?,?)',(row['module'],row['code'],request.form.get('titulo') or row['title'],version,json.dumps(data,ensure_ascii=False),g.user['id'],now,now))
     upload(cur.lastrowid); event('nueva_version',cur.lastrowid,reason); db().commit(); return redirect(url_for('detail',i=cur.lastrowid))
    elif op=='state':
     target=request.form.get('state')
     transitions={'borrador':['en revisión','cerrado'],'en revisión':['pendiente de aprobación','borrador'],'pendiente de aprobación':['aprobado','borrador'],'aprobado':['vigente'],'vigente':['obsoleto']}
     if target not in transitions.get(row['state'],[]): abort(409,'Transición no permitida')
     if row['module'] in ('documents','forms') and target=='cerrado': abort(409)
     if row['module'] not in ('documents','forms') and target!='cerrado': abort(409)
     if target in ('aprobado','vigente','obsoleto'):
      if g.user['role']!='Superusuario' or row['owner']==g.user['id']: abort(403,'Aprobación requiere otro superusuario distinto al elaborador')
     if target=='cerrado':
      if g.user['role']=='Visor': abort(403)
      for f in data.get('schema',[]):
       if f['required'] and f['type'] in ('fotografia','archivo','evidencia') and not db().execute('SELECT 1 FROM files WHERE item=? AND field=?',(i,f['id'])).fetchone(): abort(409,'Falta evidencia: '+f['label'])
      if row['module']=='actions' and not data.get('verificacion_eficacia'): abort(409,'Falta verificación de eficacia')
      data['closed_by']=g.user['id']; data['closed_at']=datetime.now().isoformat()
     if target=='vigente': db().execute("UPDATE items SET state='obsoleto' WHERE module=? AND code=? AND state='vigente'",(row['module'],row['code']))
     data['state_dates']={**data.get('state_dates',{}),target:datetime.now().isoformat()}
     db().execute('UPDATE items SET state=?,data=?,updated=? WHERE id=?',(target,json.dumps(data,ensure_ascii=False),datetime.now().isoformat(),i)); event('estado',i,target)
    elif op=='edit':
     if row['state']!='borrador': abort(409,'Solo se editan borradores')
     for k in FIELDS.get(row['module'],[]): data[k]=request.form.get(k,data.get(k,''))
     if row['module']=='records':
      for f in data.get('schema',[]):
       if f['type'] not in ('fotografia','archivo','evidencia'):
        value=request.form.get(f['id'],'')
        if f['type']=='multiple': value=request.form.getlist(f['id'])
        if f['type']=='tabla':
         try: value=table_value(value,f.get('options',[]))
         except ValueError as error: abort(400,str(error))
        if f['required'] and not value: abort(400,'Campo obligatorio: '+f['label'])
        data['answers'][f['id']]=value
     db().execute('UPDATE items SET title=?,data=?,updated=? WHERE id=?',(request.form.get('titulo') or row['title'],json.dumps(data,ensure_ascii=False),datetime.now().isoformat(),i)); event('edicion',i)
     upload(i,data.get('schema',[]))
    else: abort(400)
    db().commit()
   return redirect(url_for('detail',i=i))
  files=db().execute('SELECT * FROM files WHERE item=?',(i,)).fetchall()
  events=db().execute('SELECT * FROM events WHERE item=? ORDER BY id',(i,)).fetchall()
  snapshot=data.get('_brand') or brand_snapshot()
  return render_template('detail.html',row=row,data=data,files=files,events=events,brand=snapshot.get('branding',{}),company=snapshot.get('company',{}))
 @app.get('/file/<int:f>')
 def file(f):
  row=db().execute('SELECT * FROM files WHERE id=?',(f,)).fetchone()
  if not row: abort(404)
  item(row['item']); event('descarga',row['item'],row['name']); db().commit()
  return send_file(root/'files'/row['path'],download_name=row['name'],as_attachment=True,mimetype=row['mime'])
 @app.get('/evidence')
 def evidence():
  rows=db().execute('SELECT files.*,items.title,items.state,items.module FROM files JOIN items ON items.id=files.item ORDER BY files.id DESC').fetchall()
  if g.user['role']=='Visor': rows=[r for r in rows if r['state'] in ('vigente','cerrado')]
  if g.user['role']=='Auditor': rows=[r for r in rows if r['module'] not in ('documents','forms') or r['state'] in ('vigente','aprobado')]
  return render_template('evidence.html',rows=rows)
 @app.get('/export/<module>/<kind>')
 def export(module,kind):
  if module not in MODULES: abort(404)
  require(module)
  rows=db().execute('SELECT * FROM items WHERE module=? ORDER BY id',(module,)).fetchall()
  if g.user['role']=='Visor': rows=[r for r in rows if r['state'] in ('vigente','cerrado')]
  if g.user['role']=='Auditor' and module in ('documents','forms'): rows=[r for r in rows if r['state'] in ('vigente','aprobado')]
  return make_export(rows,kind,module)
 def make_export(rows,kind,name):
  out=io.BytesIO()
  if kind=='xlsx':
   users={r['id']:r['name'] or r['username'] for r in db().execute('SELECT id,name,username FROM users')}
   out.write(export_excel(rows,setting('company',{}),setting('branding',{}),root,users,'Reporte de '+MODULES.get(name,name)))
  elif kind=='pdf':
   users={r['id']:r['name'] or r['username'] for r in db().execute('SELECT id,name,username FROM users')}
   files={r['id']:[dict(f) for f in db().execute('SELECT * FROM files WHERE item=?',(r['id'],))] for r in rows}
   out.write(render_pdf(rows,setting('company',{}),setting('branding',{}),root,files,users,report_title=('Reporte de '+MODULES.get(name,name)) if not name.startswith('registro-') else None))
  else: abort(404)
  out.seek(0); return send_file(out,download_name=f'{name}.{kind}',as_attachment=True)
 @app.get('/item/<int:i>/pdf')
 def record_pdf(i): return make_export([item(i)],'pdf','registro-'+str(i))
 @app.route('/company',methods=['GET','POST'])
 def company():
  require('company',True)
  values=setting('company',{})
  if request.method=='POST':
   update_branding()
   values={k:request.form.get(k,'') for k in values}; setval('company',values); event('empresa'); db().commit(); flash('Empresa actualizada')
  return render_template('company.html',values=values,brand=setting('branding',{}))
 @app.get('/branding/<filename>')
 def logo(filename):
  import re
  if not re.fullmatch(r'branding-[a-f0-9]{32}\.png',filename): abort(404)
  return send_file(root/'files'/filename,mimetype='image/png')
 @app.route('/users',methods=['GET','POST'])
 def users():
  require('users',True)
  if request.method=='POST':
   role=request.form.get('role'); p=request.form.get('password','')
   if role not in ROLES or len(p)<12: abort(400,'Rol o contraseña inválidos')
   try: db().execute('INSERT INTO users(username,name,email,hash,role) VALUES(?,?,?,?,?)',(request.form['username'],request.form.get('name'),request.form.get('email'),generate_password_hash(p),role))
   except sqlite3.IntegrityError: abort(409,'Usuario existente')
   event('alta_usuario',detail=request.form['username']); db().commit()
  return render_template('users.html',rows=db().execute('SELECT id,username,name,role,active FROM users').fetchall(),roles=ROLES)
 @app.get('/events')
 def events():
  require('events',True)
  return render_template('events.html',rows=db().execute('SELECT * FROM events ORDER BY id DESC LIMIT 1000').fetchall())
 @app.get('/reports')
 def reports(): return render_template('reports.html')
 @app.route('/settings',methods=['GET','POST'])
 def settings():
  require('settings',True)
  import psutil
  ips=sorted({a.address for values in psutil.net_if_addrs().values() for a in values if a.family==socket.AF_INET})
  cfgpath=root/'server.json'; cfg=json.loads(cfgpath.read_text()) if cfgpath.exists() else {'host':'127.0.0.1','port':8080,'name':'QualityLite'}
  if request.method=='POST':
   host=request.form.get('host'); port=int(request.form.get('port','0'))
   if host not in ips+['0.0.0.0'] or not 1024<=port<=65535: abort(400,'IP o puerto inválidos')
   if (host,port)!=(cfg['host'],cfg['port']):
    try:
     with socket.socket() as s: s.bind((host,port))
    except OSError:
     alternative=None
     for candidate in range(8080,8181):
      try:
       with socket.socket() as probe: probe.bind((host,candidate))
       alternative=candidate; break
      except OSError: continue
     abort(409,'Puerto ocupado o reservado. '+('Puerto alternativo disponible: '+str(alternative) if alternative else 'No se encontró alternativa entre 8080 y 8180'))
   cfg.update(host=host,port=port,name=request.form.get('name','QualityLite'))
   backup_dir=request.form.get('backup_dir','').strip()
   if backup_dir:
    destination=Path(backup_dir)
    if not destination.is_absolute(): abort(400,'Carpeta de respaldo debe ser absoluta')
    destination.mkdir(parents=True,exist_ok=True)
   setval('backup_dir',backup_dir); setval('backup_daily',request.form.get('backup_daily')=='on')
   pending=cfgpath.with_suffix('.tmp'); pending.write_text(json.dumps(cfg),encoding='utf-8'); os.replace(pending,cfgpath)
   event('configuracion_red',detail=json.dumps(cfg)); db().commit(); flash('Guardado. Un administrador local debe aplicar firewall y reiniciar el servicio mediante Administrar servicio.')
  return render_template('settings.html',cfg=cfg,ips=ips,backup_dir=setting('backup_dir',''),backup_daily=setting('backup_daily',False))
 def backup():
  with LOCK:
   filename='QualityLite-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)+'.zip'
   target=root/'backups'/filename; snapshot=root/'backups'/(filename+'.db')
   dest=sqlite3.connect(snapshot); db().backup(dest); dest.close()
   manifest={}
   with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    sources=[(snapshot,'qualitylite.db')]+[(p,'files/'+p.name) for p in (root/'files').iterdir() if p.is_file()]+[(p,p.name) for p in (root/'secret.key',root/'server.json') if p.exists()]
    for p,name in sources:
     raw=p.read_bytes(); manifest[name]=hashlib.sha256(raw).hexdigest(); z.writestr(name,raw)
    z.writestr('manifest.json',json.dumps(manifest))
   snapshot.unlink()
   with zipfile.ZipFile(target) as z:
    for name,digest in manifest.items():
     if hashlib.sha256(z.read(name)).hexdigest()!=digest: raise ValueError('Respaldo no verificable')
   external=setting('backup_dir','')
   if external:
    import shutil
    shutil.copy2(target,Path(external)/filename)
   setval('last_backup',datetime.now().isoformat()); event('respaldo',detail=filename); db().commit(); return filename
 app.backup=backup
 def scheduled_backup():
  with app.app_context():
   last=setting('last_backup','')
   if setting('backup_daily',False) and (not last or datetime.fromisoformat(last)<datetime.now()-timedelta(days=1)): backup()
 app.scheduled_backup=scheduled_backup
 @app.route('/backups',methods=['GET','POST'])
 def backups():
  require('backups',True)
  if request.method=='POST': backup(); flash('Respaldo consistente generado y verificado por manifiesto SHA-256')
  return render_template('backups.html',rows=sorted(p.name for p in (root/'backups').glob('*.zip')),last=setting('last_backup','Nunca'))
 @app.get('/backup/<name>')
 def download_backup(name):
  require('backups',True)
  if Path(name).name!=name or not name.endswith('.zip'): abort(404)
  return send_file(root/'backups'/name,as_attachment=True)
 return app
