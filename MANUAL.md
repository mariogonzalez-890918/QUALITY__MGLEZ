# QualityLite 0.2.1 — manual de instalación, administración y usuario

## Instalación

Ejecutar `QualityLite-Desktop-Setup-0.2.1-x64.exe` como administrador en Windows x64. No requiere Python, pip ni Node. Se instala en Program Files, crea el servicio automático QualityLite bajo LocalService, configura recuperación de fallos y verifica `/health`. Los datos permanecen en `C:\ProgramData\QualityLite`. En instalación inicial busca un puerto libre entre 8080 y 8180. Si ninguno está disponible o una configuración previa tiene conflicto, consultar `launcher-error.log`, modificar `server.json` con el servicio detenido y repetir instalación.

Abrir el acceso directo QualityLite en el servidor. Copiar el token de `setup-token.txt` desde ProgramData (requiere administrador local); completar empresa y superusuario con contraseña mínima de 12 caracteres. No hay clave universal. El token se elimina después. El asistente se bloquea tras finalizar.

## Red y servicio

En Configuración elegir IP disponible y puerto. `0.0.0.0` escucha en todas las interfaces. Guardar y usar el acceso directo **Administrar servicio**, opción 5, para actualizar firewall y reiniciar con elevación. La regla permite únicamente subred local en perfiles privado/dominio. Abrir `http://IP-REAL:PUERTO` desde otra computadora. No configurar redirecciones del router hacia Internet. Fuera de LAN confiable utilizar VPN o proxy HTTPS con certificado confiable, restringir el backend y configurar cookies Secure; requiere administración de infraestructura adicional.

Administrar servicio permite consultar, iniciar, detener, reiniciar y aplicar red. También se puede usar Servicios de Windows. Cerrar navegador no detiene el servicio. Logs rotativos en ProgramData\QualityLite\logs; errores de arranque en launcher-error.log. `/health` verifica acceso a SQLite.

## Usuarios y documentos

Superusuario crea usuarios Calidad, Auditor, Visor y otros superusuarios. Debe haber un segundo superusuario para aprobar documentos elaborados por el primero. Calidad crea documentos/formatos/registros y seguimiento; Auditor crea auditorías, no conformidades y registros; Visor consulta vigentes/cerrados. Todos cambian su contraseña desde el menú. Cinco fallos de acceso por IP bloquean quince minutos. Recuperación: administrador local ejecuta `QualityLite.exe --recover` desde una terminal elevada, proporciona un superusuario existente y confirma nueva contraseña; queda historial.

Crear documento, adjuntar archivo, editar borrador, pasar a en revisión y pendiente de aprobación. Un superusuario distinto al elaborador aprueba y pone vigente. Una versión aprobada no se edita: usar Nueva versión indicando motivo y nuevo adjunto. Publicar una versión vuelve obsoleta la anterior. Ningún documento se aprueba automáticamente.

## Formatos, registros y evidencias

Diseñador: indicar código, nombre y campos; añadir tipo, obligatoriedad y opciones separadas por comas. Guardar y someter a aprobación como documento. En Registros seleccionar formato vigente, capturar campos y archivos. El registro conserva código y versión del formato. Las tablas usan una fila por línea y `|` entre columnas. Responsable es identificación textual, no firma electrónica.

Se permiten PDF, JPEG, PNG, TXT, XLSX y DOCX sin macros, con comprobación de tipo. Límite conjunto de petición: 25 MB. No subir documentos de procedencia dudosa; se recomienda antivirus en el servidor. Los adjuntos se guardan fuera de la carpeta web, con nombre aleatorio y hash. Los permisos se verifican en cada descarga. Las evidencias obligatorias impiden cerrar sin adjunto por campo. Cerrado significa inmutable; esta versión no implementa correcciones de registros cerrados. Registrar un nuevo folio y referenciar al anterior en observaciones.

Auditorías, no conformidades y acciones son fichas básicas: llenar alcance, checklist textual, responsables, compromisos, causas y eficacia. Las relaciones son referencias escritas. Consultar `ARQUITECTURA.md` para funciones pendientes. Exportar módulos desde listado o Reportes; cada registro tiene PDF con datos e índice de evidencias.

## Respaldo y restauración

Respaldos → Crear genera SQLite consistente mediante backup API y todos los adjuntos/configuración, con manifiesto SHA-256. Descargar a otro dispositivo. Configuración permite carpeta absoluta externa y respaldo diario: comprobar que LocalService tenga permisos de escritura en esa carpeta. El programador comprueba cada minuto si han pasado 24 horas desde la última copia. Fallos se registran en logs. No hay eliminación automática de copias.

Para restaurar: detener servicio, guardar una copia externa del directorio completo y ejecutar `QualityLite.exe --restore RUTA_COMPLETA.zip` en terminal elevada. Proporcionar usuario/contraseña de un superusuario actual y escribir RESTAURAR. Se validan manifiesto, rutas e integridad SQLite y se crea copia previa. No interrumpir el proceso. Iniciar servicio y validar registros/adjuntos. Si hay corte durante reemplazo, conservar archivos y recuperar desde copia previa con asistencia técnica. La restauración no es atómica ante cortes eléctricos.

## Actualización y desinstalación

Antes de actualizar crear y descargar respaldo. Ejecutar instalador en la misma ruta: detiene servicio y reemplaza binarios, conserva ProgramData y vuelve a registrar el servicio. Esta versión utiliza esquema 1, sin migraciones de esquemas posteriores. Verificar salud, empresa, usuarios y adjuntos después. Desinstalar desde Aplicaciones de Windows: elimina binarios, servicio y regla propia; conserva ProgramData con base de datos, evidencias, claves y copias. La eliminación definitiva de datos es una operación administrativa separada.

## Compilar y probar

Entorno de desarrollo Windows x64 con Python 3.12: crear `.venv`, instalar `requirements.txt`, `pytest` y `pyinstaller`, instalar Visual C++ Build Tools (C++ x64 y Windows SDK) e Inno Setup oficial en `tools\inno` o adaptar build.ps1. Ejecutar build.ps1: genera plantillas, ejecuta pytest, congela dependencias, compila binario y genera instalador. `requirements-lock.txt` conserva las versiones efectivas. Consultar licencias de dependencias y condiciones comerciales de Inno Setup antes de distribuir comercialmente.

No existe afirmación automática de conformidad ISO. La empresa debe revisar documentos y validar el sistema según sus necesidades.


## Instalación en servidores (revisión 0.2.1)

Consultar CORRECCION-0.2.1.md para la matriz de sistemas objetivo y resultados reales. Los fallos se diagnostican en ProgramData\QualityLite-SetupLogs. La preparación de permisos utiliza un binario nativo independiente y el acceso directo utiliza connection.json público de Program Files. No eliminar bases ni evidencias ni deshabilitar las protecciones del servidor.


## Ediciones Servidor y Escritorio 0.2.1

Para un servidor utilice QualityLite-Server-Setup-0.2.1-x64.exe. En el asistente indique IP y puerto; 0.0.0.0 significa todas las interfaces IPv4 y requiere marcar autorización LAN. Deje IP/puerto vacíos al actualizar para conservar los valores anteriores. No abre acceso a Internet. Para Windows 10/11 utilice QualityLite-Desktop-Setup-0.2.1-x64.exe. Ambas ediciones conservan los mismos datos y servicio.

## Logotipo y formularios corporativos

Empresa permite cargar su propio logo PNG/JPG (2 MB, 16-4096 píxeles), ajustar la leyenda y el pie de los documentos. Guarde la identidad antes de crear los formatos. Los documentos nuevos conservan esa identidad, incluso si después se reemplaza el logo.

Diseñador de formatos permite Usar modelo editable de solicitud de servicio. Ajuste sus campos, secciones y columnas de tabla. Se guarda en borrador y debe revisarse y aprobarse. En Registros la captura usa una hoja formal; las tablas permiten agregar filas. Editar el borrador permite continuar una atención pendiente. Descargar PDF formal genera una hoja con logo, código, versión, folio, datos y responsables; los espacios de firma son autógrafos, no firmas electrónicas.

## Reparacion de permisos 0.2.1

Reejecute el instalador 0.2.1 elevado sobre la instalacion anterior; conserve ProgramData\QualityLite. El preparador respalda y aplica las ACL mediante acceso administrativo de copia/restauracion, sin cambiar propietarios ni borrar archivos. Si una politica de dominio retira esos derechos y los permisos ordinarios tampoco permiten acceso, el registro indica los privilegios requeridos. Consulte CORRECCION-0.2.1.md.
