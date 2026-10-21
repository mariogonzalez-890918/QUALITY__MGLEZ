"""Valida los recursos versionados; nunca sobrescribe cambios de interfaz."""
from pathlib import Path
from jinja2 import Environment
root=Path(__file__).parent
for path in (root/'templates').glob('*.html'):
 Environment().parse(path.read_text(encoding='utf-8'))
for name in ('base.html','edit.html','detail.html','company.html','form_macros.html','paper_header.html'):
 if not (root/'templates'/name).is_file(): raise SystemExit('Falta plantilla: '+name)
for name in ('style.css','app.js'):
 if not (root/'static'/name).is_file(): raise SystemExit('Falta recurso: '+name)
print('Plantillas y recursos validados')
