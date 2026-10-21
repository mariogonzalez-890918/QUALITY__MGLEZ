"""Modelos editables de ejemplo; nunca se publican como documentos aprobados."""
SERVICE_MODEL={'codigo':'FOR-SRV-001','titulo':'Solicitud y atención de servicio','descripcion':'Modelo editable para solicitar, atender y documentar un servicio interno.','instrucciones':'Complete la identificación, describa la necesidad y registre la atención. Adjunte evidencias cuando corresponda. La autorización se realiza conforme al procedimiento de la empresa.','schema':[]}
def field(label,typ,section,required=False,options=(),width='half'):
 return {'label':label,'type':typ,'section':section,'required':required,'options':list(options),'width':width}
SERVICE_MODEL['schema']=[
 field('Fecha de solicitud','fecha','Identificación de la solicitud',True),
 field('Hora de solicitud','hora','Identificación de la solicitud'),
 field('Solicitante','responsable','Identificación de la solicitud',True),
 field('Área / departamento','texto','Identificación de la solicitud',True),
 field('Proceso o ubicación','texto','Identificación de la solicitud'),
 field('Prioridad','lista','Identificación de la solicitud',True,['Normal','Alta','Urgente']),
 field('Tipo de servicio','lista','Identificación de la solicitud',True,['Mantenimiento','Calidad','Sistemas','Instalaciones','Otro']),
 field('Equipo / activo relacionado','texto','Descripción de la necesidad'),
 field('Descripción de la solicitud','texto_largo','Descripción de la necesidad',True,width='full'),
 field('Resultado esperado','texto_largo','Descripción de la necesidad',False,width='full'),
 field('Responsable de atención','responsable','Atención y seguimiento'),
 field('Fecha compromiso','fecha','Atención y seguimiento'),
 field('Diagnóstico / evaluación','texto_largo','Atención y seguimiento',False,width='full'),
 field('Actividades realizadas','tabla','Atención y seguimiento',False,['Actividad','Responsable','Fecha'],'full'),
 field('Resultado y observaciones','texto_largo','Cierre y validación',False,width='full'),
 field('Pendientes / recomendaciones','observaciones','Cierre y validación',False,width='full'),
 field('Responsable de revisión','responsable','Cierre y validación'),
 field('Fecha de revisión','fecha','Cierre y validación'),
 field('Evidencia de atención','fotografia','Evidencias',False,width='full')]

def schema_from_form(form,types):
 labels=form.getlist('label'); schema=[]
 for index,label in enumerate(labels):
  def value(key,default=''):
   values=form.getlist(key); return values[index] if index<len(values) else default
  if not label.strip(): continue
  typ=value('type'); section=value('section','Datos del formato').strip() or 'Datos del formato'
  if typ not in types: raise ValueError('Tipo de campo no autorizado')
  if len(label)>160 or len(section)>100 or len(schema)>=100: raise ValueError('Exceso de campos o longitud de etiquetas')
  options=[v.strip() for v in value('options').split(',') if v.strip()]
  if len(options)>30 or any(len(v)>160 for v in options): raise ValueError('Demasiadas opciones o etiquetas muy largas')
  if typ=='tabla' and len(options)>8: raise ValueError('Una tabla admite hasta ocho columnas')
  schema.append({'id':'f'+str(len(schema)+1),'label':label.strip(),'type':typ,'section':section,'required':value('required')=='si','options':options,'width':'full' if value('width')=='full' or typ in ('tabla','texto_largo','observaciones','comentarios','archivo','fotografia','evidencia') else 'half'})
 if not schema: raise ValueError('Agregue al menos un campo')
 return schema

def table_value(raw,columns):
 import json
 if not raw: return []
 try: rows=json.loads(raw)
 except (ValueError,TypeError): rows=[line.split('|') for line in raw.splitlines() if line.strip()]
 if not isinstance(rows,list) or len(rows)>100: raise ValueError('Tabla no válida: máximo cien filas')
 count=len(columns) or 3; result=[]
 for row in rows:
  if not isinstance(row,list) or len(row)>count: raise ValueError('Columnas de tabla no válidas')
  values=[str(v).strip() for v in row]+['']*(count-len(row))
  if any(len(v)>1000 for v in values): raise ValueError('Celda demasiado larga')
  if any(values): result.append(values)
 return result
