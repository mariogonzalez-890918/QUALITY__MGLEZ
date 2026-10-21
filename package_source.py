"""Empaqueta fuentes y licencias sin claves ni datos de prueba."""
from pathlib import Path
import tempfile,zipfile,importlib.metadata,shutil
from app import create_app
root=Path(__file__).parent
release=root/'release'; release.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='qualitylite-seed-') as directory:
 app=create_app(directory)
 shutil.copy2(Path(directory)/'qualitylite.db',release/'base-inicial.sqlite3')
notices=[]
for name in ['Flask','waitress','reportlab','openpyxl','pywin32','psutil','python-magic-bin','Werkzeug','Jinja2','itsdangerous','click','blinker','MarkupSafe','Pillow','charset-normalizer','et-xmlfile']:
 dist=importlib.metadata.distribution(name)
 notices.append(f'\n## {name} {dist.version}\n{dist.metadata.get("License-Expression") or dist.metadata.get("License") or "Consultar archivos de licencia"}\n{dist.metadata.get("Home-page", "")}\n')
 for path in dist.files or []:
  if ('license' in str(path).lower() or 'copying' in str(path).lower()) and Path(str(path)).suffix.lower() in ('.txt','.md','.rst',''):
   try: notices.append(Path(dist.locate_file(path)).read_text(encoding='utf-8',errors='replace'))
   except OSError: pass
(root/'THIRD_PARTY_NOTICES.txt').write_text('\n'.join(notices),encoding='utf-8')
with zipfile.ZipFile(release/'QualityLite-fuentes-0.1.1.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in root.iterdir():
  if p.is_file() and (p.suffix in ('.py','.ps1','.iss','.md','.txt','.ini') or p.name=='.gitignore') and p.name not in ('build-log.txt','freeze-log.txt','installer-log.txt'): z.write(p,p.name)
 for directory in ('templates','static','.github'):
  for p in (root/directory).rglob('*'):
   if p.is_file(): z.write(p,p.relative_to(root))
 z.write(release/'base-inicial.sqlite3','base-inicial.sqlite3')
print('Fuentes, base inicial y licencias empaquetadas')
