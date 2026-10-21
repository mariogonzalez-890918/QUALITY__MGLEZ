"""Entrada minima: captura errores antes de cargar Flask y extensiones nativas."""
import sys
import os
import json
import tempfile
import traceback
from pathlib import Path

VERSION='0.1.2'

def parse_options(args):
 remaining=[]; options={}; index=0
 while index<len(args):
  key=args[index]
  if key in ('--diagnostic-log','--data-root'):
   if index+1>=len(args): raise ValueError('Falta valor para '+key)
   options[key]=args[index+1]; index+=2
  else: remaining.append(key); index+=1
 return remaining,options

def public_connection(directory):
 path=Path(directory)/'connection.json'
 values=json.loads(path.read_text(encoding='utf-8-sig'))
 host=values.get('host','127.0.0.1'); port=int(values['port'])
 import ipaddress
 ipaddress.IPv4Address(host)
 if not 1024<=port<=65535: raise ValueError('Puerto de acceso invalido')
 if host=='0.0.0.0': host='127.0.0.1'
 return f'http://{host}:{port}'

def write_failure(error,path=None):
 text=f'QualityLite {VERSION}\nWindows: {sys.getwindowsversion() if os.name=="nt" else sys.platform}\n'+''.join(traceback.format_exception(type(error),error,error.__traceback__))
 destinations=[Path(path)] if path else []
 destinations.append(Path(tempfile.gettempdir())/'QualityLite-install-error.log')
 for target in destinations:
  try:
   with target.open('a',encoding='utf-8') as stream: stream.write(text+'\n')
   return str(target)
  except OSError: pass
 return ''

def run(args=None):
 original=sys.argv[:]
 options={}
 try:
  remaining,options=parse_options(list(sys.argv[1:] if args is None else args))
  if '--data-root' in options: os.environ['QUALITYLITE_DATA']=options['--data-root']
  sys.argv=[sys.argv[0]]+remaining
  if remaining in (['--open'],['--connection-url']):
   # No leer ni escribir carpetas privadas para abrir el navegador.
   directory=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
   url=public_connection(directory)
   if remaining==['--connection-url']:
    print(url)
    return 0
   from http.client import HTTPConnection
   from urllib.parse import urlsplit
   target=urlsplit(url); connection=HTTPConnection(target.hostname,target.port,timeout=5)
   try:
    connection.request('GET','/health'); response=connection.getresponse()
    if response.status!=200 or json.loads(response.read()).get('status')!='ok': raise RuntimeError('El servicio no responde correctamente')
   finally: connection.close()
   os.startfile(url)
   return 0
  import launcher
  result=launcher.main() or 0
  if result:
   details=''
   try: details=(launcher.ROOT/'logs'/'service-commands.log').read_text(encoding='utf-8')[-4500:]
   except (OSError,AttributeError): pass
   write_failure(RuntimeError('El comando termino con codigo Windows '+str(result)+'\n'+details),options.get('--diagnostic-log'))
  return result
 except Exception as error:
  path=write_failure(error,options.get('--diagnostic-log'))
  if '--open' in (sys.argv[1:]):
   import ctypes
   ctypes.windll.user32.MessageBoxW(None,'No se pudo abrir QualityLite. '+str(error)+'\nRegistro: '+path,'QualityLite',0x10)
  if sys.stderr: print(type(error).__name__+': '+str(error),file=sys.stderr)
  return 1
 finally: sys.argv=original

if __name__=='__main__': sys.exit(run())
