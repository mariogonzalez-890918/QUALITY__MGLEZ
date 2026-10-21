"""Ejemplos visuales independientes: no crea cuentas ni datos en la instalación."""
import io,json,copy
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from form_models import SERVICE_MODEL
from formal_pdf import render_pdf
root=Path(__file__).parent; output=root/'output'/'pdf'; output.mkdir(parents=True,exist_ok=True)
scratch=root/'test-data'/'pdf-preview'; (scratch/'files').mkdir(parents=True,exist_ok=True)
image=Image.new('RGBA',(400,180),'white'); draw=ImageDraw.Draw(image)
try: font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',45)
except OSError: font=ImageFont.load_default()
draw.rounded_rectangle((5,5,390,170),12,outline='#173454',width=5); draw.text((27,48),'EMPRESA',font=font,fill='#173454')
filename='branding-'+'a'*32+'.png'; image.save(scratch/'files'/filename)
company={'razon_social':'Empresa de demostración, S.A. de C.V.','nombre_comercial':'EMPRESA DE DEMOSTRACIÓN','domicilio':'Planta principal · México'}
branding={'logo':filename,'department':'GESTIÓN DE CALIDAD E INOCUIDAD','footer':'MODELO EDITABLE DE EJEMPLO | Documento controlado. Verifique la versión vigente.'}
schema=copy.deepcopy(SERVICE_MODEL['schema'])
for idx,f in enumerate(schema,1): f['id']='f'+str(idx)
data={'codigo':'FOR-SRV-001','area':'Mantenimiento y Calidad','proceso':'Atención de servicios internos','instrucciones':SERVICE_MODEL['instrucciones'],'schema':schema,'_brand':{'company':company,'branding':branding}}
row={'id':1,'module':'forms','code':'FOR-SRV-001','title':'SOLICITUD Y ATENCIÓN DE SERVICIO','version':1,'state':'borrador','data':json.dumps(data),'owner':1,'created':'2026-10-21T09:00:00'}
(output/'Modelo-solicitud-servicio.pdf').write_bytes(render_pdf([row],company,branding,scratch,{}, {1:'Responsable de elaboración'}))
data=copy.deepcopy(data); data.update(form_code='FOR-SRV-001',form_version=1,answers={'f1':'2026-10-21','f2':'09:00','f3':'Solicitante de ejemplo','f4':'Calidad','f5':'Planta principal','f6':'Normal','f7':'Mantenimiento','f8':'Equipo de inspección dimensional','f9':'Se solicita verificar el equipo de medición antes de la inspección de cajas terminadas. Registrar su condición, limpieza y funcionamiento.','f10':'Equipo verificado y disponible para inspección.','f11':'Responsable de mantenimiento','f12':'2026-10-22','f13':'Se revisó el estado general del equipo y los puntos de verificación definidos por la empresa.','f14':[['Inspección visual y limpieza','Técnico de ejemplo','21/10/2026'],['Prueba de funcionamiento','Calidad','21/10/2026']],'f15':'El equipo quedó disponible. La aceptación y el cierre requieren validación del responsable.','f16':'Programar la siguiente revisión conforme al plan de mantenimiento.','f17':'Revisor de ejemplo','f18':'2026-10-21'})
row.update(module='records',code='REG-2026-EJEMPLO',state='borrador',data=json.dumps(data))
(output/'Registro-servicio-ejemplo.pdf').write_bytes(render_pdf([row],company,branding,scratch,{}, {1:'Responsable de elaboración'}))
print('PDF de modelo y registro generados')
