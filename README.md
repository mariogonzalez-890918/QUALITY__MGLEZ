# QualityLite

Aplicación local de calidad e inocuidad: Flask, Waitress, SQLite y servicio Windows.

## Descargar e instalar

La edición Servidor es `release/QualityLite-Server-Setup-0.2.1-x64.exe` (Server 2016/2019/2022/2025, objetivos de despliegue; revisar la validación real). La edición Escritorio es `release/QualityLite-Desktop-Setup-0.2.1-x64.exe`. Ejecutar como administrador. Esta revisión reemplaza el paso de permisos que fallaba en 0.1.0 y conserva los datos existentes. No requiere instalar Python en el equipo destino.

Los datos se guardan en `%ProgramData%\QualityLite`. El navegador se abre desde el acceso directo después de que el instalador comprueba la salud del servicio. La configuración inicial requiere el token local `setup-token.txt`.

## Desarrollo

En Windows x64 con Python 3.12, Visual C++ Build Tools (C++ x64 y Windows SDK) e Inno Setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
# Instalar Inno Setup oficial y colocar el compilador en tools\inno,
# o indicar su ubicación mediante QUALITYLITE_ISCC.
.\build.ps1
```

`build.ps1` ejecuta pruebas y compila aplicación e instalador. `smoke_frozen.py` comprueba el binario congelado mediante HTTP con datos aislados. Las pruebas de ACL usan las API reales de Windows sobre carpetas temporales y restauran sus permisos al terminar.

## Documentación

- [Manual de instalación, administración y usuario](MANUAL.md)
- [Arquitectura y limitaciones funcionales](ARQUITECTURA.md)
- [Informe original de entrega](ENTREGA.md)
- [Corrección del instalador 0.2.1](CORRECCION-0.2.1.md)

Versión inicial de alcance parcial. Consultar las limitaciones antes de usarla en producción. No otorga certificación ISO.

La revisión 0.2.0 incorpora logo configurable en Empresa, formularios corporativos por secciones, tablas de captura y un modelo editable de solicitud de servicio. Consulte las muestras en output/pdf.
