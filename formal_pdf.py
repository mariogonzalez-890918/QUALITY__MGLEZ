"""Hojas controladas de calidad con identidad corporativa y paginación real."""
import io,json,re
from pathlib import Path
from xml.sax.saxutils import escape
from collections import OrderedDict
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,KeepTogether,Image
from reportlab.lib.utils import ImageReader

NAVY=colors.HexColor('#173454'); MUTED=colors.HexColor('#65788c'); LINE=colors.HexColor('#dce4ec'); PALE=colors.HexColor('#eaf0f6')
LABELS={'codigo':'Código','titulo':'Título','tipo':'Tipo documental','area':'Área / departamento','proceso':'Proceso','elaborador':'Elaboró','revisor':'Revisó','aprobador':'Aprobó','fecha_vigencia':'Entrada en vigor','proxima_revision':'Próxima revisión','motivo':'Motivo de revisión','responsable':'Responsable','descripcion':'Descripción','instrucciones':'Instrucciones de llenado','fecha':'Fecha','alcance':'Alcance','auditor':'Auditor responsable','lista_verificacion':'Lista de verificación','clasificacion':'Clasificación','auditoria':'Auditoría relacionada','fecha_compromiso':'Fecha compromiso','causa':'Análisis de causa','accion_inmediata':'Acción inmediata','no_conformidad':'No conformidad relacionada','accion_correctiva':'Acción correctiva','verificacion_eficacia':'Verificación de eficacia'}
MODULE_TITLES={'documents':'Control documental','forms':'Formato controlado','records':'Registro de calidad','audits':'Informe de auditoría','findings':'No conformidad','actions':'Acción correctiva'}
BODY=ParagraphStyle('body',fontName='Helvetica',fontSize=9.5,leading=13,textColor=NAVY,spaceAfter=2,wordWrap='CJK')
SMALL=ParagraphStyle('small',parent=BODY,fontSize=7.2,leading=10,textColor=MUTED)
CAPTION=ParagraphStyle('caption',parent=BODY,fontName='Helvetica-Bold',fontSize=7.5,leading=11,textColor=MUTED)

def text(value):
 if value is None or value=='': return '________________________'
 if isinstance(value,list): return ', '.join(str(v) for v in value)
 if isinstance(value,bool): return 'Sí' if value else 'No'
 return str(value)

def p(value,style=BODY):
 paragraph=Paragraph(escape(text(value)).replace('\n','<br/>'),style)
 if style is CAPTION: paragraph.keepWithNext=True
 return paragraph

def section(title):
 table=Table([[p(title.upper(),ParagraphStyle('section',parent=BODY,fontName='Helvetica-Bold',fontSize=9.5,leading=13))]],colWidths=[532])
 table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),0,PALE),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 table.keepWithNext=True; after=Spacer(1,8); after.keepWithNext=True
 return [Spacer(1,7),table,after]

def grid(pairs,columns=3):
 out=[]; width=532/columns
 for start in range(0,len(pairs),columns):
  row=pairs[start:start+columns]; cells=[]
  if any(len(text(value))>350 for label,value in row):
   for label,value in row: out.extend([p(label.upper(),CAPTION),p(value),Spacer(1,9)])
   continue
  for label,value in row: cells.append([p(label.upper(),CAPTION),p(value)])
  cells += ['']*(columns-len(cells))
  table=Table([cells],colWidths=[width]*columns,hAlign='LEFT')
  table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),15),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
  out.append(table)
 return out

def table_answer(value,columns):
 if isinstance(value,str):
  try: value=json.loads(value)
  except (ValueError,TypeError): value=[line.split('|') for line in value.splitlines() if line.strip()]
 if not isinstance(value,list): value=[]
 headers=columns or ['Descripción','Responsable','Fecha']
 rows=[[p(h,CAPTION) for h in headers]]
 for row in value:
  if isinstance(row,dict): row=[row.get(h,'') for h in headers]
  if isinstance(row,list): rows.append([p(row[i] if i<len(row) else '') for i in range(len(headers))])
 if len(rows)==1: rows.extend([[p(' ') for h in headers] for _ in range(3)])
 table=Table(rows,colWidths=[532/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
 table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('GRID',(0,0),(-1,-1),.5,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
 return table

class NumberedCanvas(canvas.Canvas):
 def __init__(self,*args,footer='',**kwargs):
  super().__init__(*args,**kwargs); self.pages=[]; self.footer=footer
 def showPage(self): self.pages.append(dict(self.__dict__)); self._startPage()
 def save(self):
  count=len(self.pages)
  for state in self.pages:
   self.__dict__.update(state)
   self.setStrokeColor(LINE); self.line(40,42,572,42)
   self.setFont('Helvetica',7); self.setFillColor(MUTED)
   self.drawString(40,29,self.footer[:92]); self.drawRightString(572,29,f'Página {self._pageNumber} de {count}')
   canvas.Canvas.showPage(self)
  canvas.Canvas.save(self)

def brand_logo(root,brand):
 filename=brand.get('logo','')
 if not re.fullmatch(r'branding-[a-f0-9]{32}\.png',filename): return None
 path=Path(root)/'files'/filename
 return path if path.is_file() else None

def render_pdf(rows,company,branding,root,files_by_item,users,report_title=None):
 output=io.BytesIO(); rows=[dict(row) for row in rows]
 if len(rows)==1 and not report_title:
  first=rows[0]; data=json.loads(first['data']); snapshot=data.get('_brand',{})
  company=snapshot.get('company',company); branding=snapshot.get('branding',branding)
 else: first=None
 name=company.get('nombre_comercial') or company.get('razon_social') or 'SU EMPRESA'
 title=report_title or first['title']; logo=brand_logo(root,branding)
 def header(c,doc):
  c.saveState(); c.setFillColor(NAVY); c.rect(0,784,612,8,fill=1,stroke=0)
  if logo: c.drawImage(ImageReader(str(logo)),40,701,width=70,height=65,preserveAspectRatio=True,anchor='c',mask='auto')
  else:
   c.setStrokeColor(LINE); c.rect(40,704,70,58,fill=0,stroke=1); c.setFont('Helvetica-Bold',7); c.setFillColor(MUTED); c.drawCentredString(75,735,'LOGOTIPO'); c.setFont('Helvetica',6); c.drawCentredString(75,722,'DE SU EMPRESA')
  name_style=ParagraphStyle('company',parent=BODY,fontName='Helvetica-Bold',fontSize=17,leading=20)
  label=p(name,name_style); _,h=label.wrap(315,50); label.drawOn(c,124,764-h)
  subtitle=branding.get('department') or 'SISTEMA DE GESTIÓN DE CALIDAD E INOCUIDAD'
  sub=p(subtitle,SMALL); _,h=sub.wrap(315,35); sub.drawOn(c,124,714-h)
  t=p(title[:120],ParagraphStyle('title',parent=BODY,fontName='Helvetica-Bold',fontSize=12,leading=15)); _,h=t.wrap(448,40); t.drawOn(c,124,686-h)
  metadata=[['CÓDIGO',(data.get('form_code') or first['code']) if first else 'REPORTE'],['VERSIÓN',str(data.get('form_version') or first['version']) if first else '1']]
  mt=Table([[p(k,SMALL),p(v,SMALL)] for k,v in metadata],colWidths=[48,75]); mt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4)])); _,h=mt.wrap(123,70); mt.drawOn(c,449,765-h)
  c.setStrokeColor(LINE); c.line(40,638,572,638)
  if first:
   line=f"Folio: {first['code']}    |    Fecha: {first['created'][:10]}    |    Estado: {first['state']}"
   c.setFont('Helvetica',8); c.setFillColor(MUTED); c.drawString(40,647,line[:125])
  c.restoreState()
 story=[]
 if report_title:
  story+=section('01  Relación de documentos y registros')
  values=[[p(t,CAPTION) for t in ['Código','Título','Versión','Estado','Fecha']]]
  for row in rows: values.append([p(row['code']),p(row['title']),p(row['version']),p(row['state']),p(row['created'][:10])])
  table=Table(values,colWidths=[92,223,44,89,84],repeatRows=1)
  table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('GRID',(0,0),(-1,-1),.4,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); story.append(table)
 else:
  row=first; data=json.loads(row['data']); author=users.get(row['owner'],'Responsable por identificar')
  story+=section('01  Identificación y control')
  story+=grid([('Área / departamento',data.get('area')),('Proceso',data.get('proceso')),('Responsable de captura',author)])
  if data.get('instrucciones'): story+=[p('INSTRUCCIONES DE LLENADO',CAPTION),p(data['instrucciones']),Spacer(1,6)]
  schema=data.get('schema'); n=2
  if schema:
   groups=OrderedDict()
   for field in schema: groups.setdefault(field.get('section') or 'Datos del formato',[]).append(field)
   for group,fields in groups.items():
    story+=section(f'{n:02}  {group}'); n+=1; pairs=[]
    for f in fields:
     value=data.get('answers',{}).get(f['id'],'')
     label=f['label']+(' *' if f.get('required') else '')
     if f['type'] in ('tabla','texto_largo','comentarios','observaciones','archivo','fotografia','evidencia') or f.get('width')=='full':
      if pairs: story+=grid(pairs); pairs=[]
      story.append(p(label,CAPTION))
      if f['type']=='tabla': story.append(table_answer(value,f.get('options',[])))
      elif f['type'] in ('archivo','fotografia','evidencia'): story.append(p('Adjuntar al registro y consultar la relación de evidencias.',SMALL))
      else: story.append(p(value)); story.append(Spacer(1,12))
     else: pairs.append((label,value))
    if pairs: story+=grid(pairs)
  else:
   story+=section('02  Contenido del documento'); n=3
   for key,value in data.items():
    if key.startswith('_') or key in ('state_dates','closed_by','closed_at','motivo'): continue
    story.extend([p(LABELS.get(key,key.replace('_',' ').capitalize()),CAPTION),p(value),Spacer(1,8)])
  evidence=list(files_by_item.get(row['id'],[]))
  if evidence:
   story+=section(f'{n:02}  Relación de evidencias'); n+=1
   for idx,f in enumerate(evidence,1):
    fields={field['id']:field['label'] for field in schema or []}
    story+=grid([('Archivo',f['name']),('Campo asociado',fields.get(f['field'],'Adjunto general')),('Cargó',users.get(f['owner'],'Usuario registrado'))])
    story+=[p('Fecha: '+f['created'][:19]+' | SHA-256: '+f['sha256'],SMALL),Spacer(1,8)]
    if f['mime'] in ('image/jpeg','image/png'):
     path=Path(root)/'files'/f['path']
     if path.is_file():
      try:
       image=Image(str(path)); scale=min(500/image.imageWidth,200/image.imageHeight,1); image.drawWidth=image.imageWidth*scale; image.drawHeight=image.imageHeight*scale
       story.extend([image,Spacer(1,12)])
      except (OSError,ValueError): story.append(p('Vista previa no disponible. El archivo original se conserva por separado.',SMALL))
  story+=section(f'{n:02}  Responsables y validación')
  signatures=[]
  for label,person in [('ELABORÓ / REGISTRÓ',data.get('elaborador') or author),('REVISÓ',data.get('revisor')),('AUTORIZÓ',data.get('aprobador') or users.get(data.get('closed_by'),'') )]:
   signatures.append([p(label,CAPTION),Spacer(1,32),p('________________________________',SMALL),p(person,SMALL)])
  signature_table=Table([signatures],colWidths=[532/3]*3); signature_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOX',(0,0),(-1,-1),.5,LINE),('INNERGRID',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
  story.extend([signature_table,Spacer(1,8),p('Espacios de firma autógrafa, si aplica. La emisión de este PDF no sustituye la aprobación interna ni constituye una firma electrónica.',SMALL)])
 footer=branding.get('footer') or 'QualityLite | Documento controlado. Verifique la versión vigente antes de su uso.'
 document=SimpleDocTemplate(output,pagesize=letter,leftMargin=40,rightMargin=40,topMargin=164,bottomMargin=57,title=title,author=name)
 document.build(story,onFirstPage=header,onLaterPages=header,canvasmaker=lambda *args,**kwargs:NumberedCanvas(*args,footer=footer,**kwargs))
 return output.getvalue()
