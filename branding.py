import io,secrets,re,warnings
from PIL import Image,UnidentifiedImageError

def normalize_logo(file):
 raw=file.read(2*1024*1024+1)
 if not raw or len(raw)>2*1024*1024: raise ValueError('El logotipo debe pesar como máximo 2 MB')
 if not file.filename.lower().endswith(('.png','.jpg','.jpeg')): raise ValueError('Use un logotipo PNG o JPEG')
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(raw)) as image:
    if image.format not in ('PNG','JPEG') or not 16<=image.width<=4096 or not 16<=image.height<=4096 or image.width*image.height>16_000_000:
     raise ValueError('Imagen inválida: dimensiones entre 16 y 4096 píxeles')
    image.load(); image.thumbnail((1200,1200)); clean=image.convert('RGBA')
    output=io.BytesIO(); clean.save(output,format='PNG'); return output.getvalue()
 except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as error: raise ValueError('El archivo no es una imagen válida') from error

def save_logo(root,file):
 raw=normalize_logo(file); name='branding-'+secrets.token_hex(16)+'.png'
 (root/'files'/name).write_bytes(raw)
 return name
