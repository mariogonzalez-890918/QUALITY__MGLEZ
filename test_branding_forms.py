import io,json
from pathlib import Path
from PIL import Image
from test_app import env
from form_models import SERVICE_MODEL,table_value

def logo(color='navy'):
 out=io.BytesIO(); Image.new('RGB',(220,90),color).save(out,format='PNG'); out.seek(0); return out

def service_payload():
 schema=SERVICE_MODEL['schema']
 return {'codigo':'FOR-SRV-001','titulo':SERVICE_MODEL['titulo'],'descripcion':SERVICE_MODEL['descripcion'],'instrucciones':SERVICE_MODEL['instrucciones'],'label':[f['label'] for f in schema],'type':[f['type'] for f in schema],'section':[f['section'] for f in schema],'width':[f['width'] for f in schema],'required':['si' if f['required'] else 'no' for f in schema],'options':[', '.join(f['options']) for f in schema]}

def test_logo_rejected_if_not_real_image(env):
 app,c,p,root=env
 assert p('/company',{'logo':(io.BytesIO(b'not an image'),'logo.png')}).status_code==400
 assert p('/company',{'logo':(io.BytesIO(b'<svg/>'),'logo.svg')}).status_code==400

def test_logo_upload_and_snapshot_preserved(env):
 app,c,p,root=env
 assert p('/company',{'razon_social':'Empresa formal','logo':(logo(),'logo.png'),'brand_department':'Departamento de Calidad'}).status_code==200
 result=p('/m/documents/new',{'codigo':'DOC-LOGO','titulo':'Procedimiento formal'})
 i=int(result.location.rsplit('/',1)[1])
 with app.app_context(): old=json.loads(app.db().execute('SELECT data FROM items WHERE id=?',(i,)).fetchone()[0])['_brand']['branding']['logo']
 assert c.get('/branding/'+old).status_code==200
 p('/company',{'logo':(logo('green'),'nuevo.png')})
 with app.app_context(): saved=json.loads(app.db().execute('SELECT data FROM items WHERE id=?',(i,)).fetchone()[0])
 assert saved['_brand']['branding']['logo']==old
 assert (root/'files'/old).exists()
 assert c.get(f'/item/{i}/pdf').data.startswith(b'%PDF')
 assert c.get('/branding/../secret.key').status_code==404

def test_service_model_and_formal_capture(env):
 app,c,p,root=env
 page=c.get('/m/forms/new?model=service')
 assert page.status_code==200 and 'Descripción de la solicitud'.encode() in page.data
 response=p('/m/forms/new',service_payload()); assert response.status_code==302
 i=int(response.location.rsplit('/',1)[1])
 with app.app_context():
  data=json.loads(app.db().execute('SELECT data FROM items WHERE id=?',(i,)).fetchone()[0]); assert len(data['schema'])==19
  app.db().execute("UPDATE items SET state='vigente' WHERE id=?",(i,)); app.db().commit()
 capture=c.get('/m/records/new?form_id='+str(i))
 assert capture.status_code==200
 assert capture.data.index('Identificación de la solicitud'.encode())<capture.data.index('Cierre y validación'.encode())
 assert b'table-capture' in capture.data
 values={'form_id':str(i),'f1':'2026-10-21','f3':'Solicitante de ejemplo','f4':'Calidad','f6':'Normal','f7':'Calidad','f9':'Revisión de equipo','f14':json.dumps([['Inspección','Responsable','2026-10-21']])}
 result=p('/m/records/new',values); assert result.status_code==302
 record=int(result.location.rsplit('/',1)[1]); pdf=c.get(f'/item/{record}/pdf')
 from pypdf import PdfReader
 reader=PdfReader(io.BytesIO(pdf.data)); text='\n'.join(page.extract_text() for page in reader.pages)
 assert 'Solicitante de ejemplo' in text and 'Actividades realizadas' in text and 'RESPONSABLES Y VALIDACIÓN' in text
 assert 'schema:' not in text and '_brand' not in text
 assert all(f'Página {n+1} de {len(reader.pages)}' in reader.pages[n].extract_text() for n in range(len(reader.pages)))
 assert c.get(f'/item/{record}').status_code==200
 result=p(f'/item/{record}',{'op':'edit',**values,'f9':'Solicitud actualizada'})
 assert result.status_code==302
 assert c.get(f'/item/{record}/pdf').data.startswith(b'%PDF')

def test_table_validation():
 assert table_value('Actividad | Persona | 2026-10-21',[])==[['Actividad','Persona','2026-10-21']]
 import pytest
 with pytest.raises(ValueError): table_value('[1,2]',[])

def test_company_restricted_to_superuser(env):
 app,c,p,root=env
 p('/users',{'username':'viewer','password':'VisorSeguro!123','role':'Visor'})
 p('/logout'); p('/login',{'username':'viewer','password':'VisorSeguro!123'})
 assert p('/company',{'logo':(logo(),'logo.png')}).status_code==403
