# QualityLite 0.1.2 — robustez del despliegue en Windows

Objetivo: Windows 10/11 y Windows Server 2016/2019/2022/2025, x64, con instalación administrativa y datos en volumen local NTFS/ReFS. Las ediciones y políticas de servidor requieren validación por sistema; no se afirma compatibilidad comercial certificada por compilar el instalador.

El reporte del servidor indica código 1 en el paso --secure-data, sin traceback. No identifica la excepción original. Esta revisión elimina ese paso de Python del instalador y mejora el diagnóstico, sin atribuir una causa no demostrada a ese servidor.

## Cambios

- Preparador nativo C++ /MT que solo importa ADVAPI32 y KERNEL32. Prepara permisos usando SID, sin Python, .NET, paquetes de Visual C++ instalados ni nombres de cuentas dependientes del idioma.
- Enumeración previa, rechazo de enlaces/junctions, comprobación de permisos persistentes del volumen y conservación del contenido. Ante error al aplicar ACL, intenta restaurar exclusivamente los descriptores que cambió y registra cualquier fallo de reversión.
- La parada del servicio previo usa el SCM de Windows desde el preparador nativo, sin depender de que funcione el ejecutable de la versión anterior.
- Entrada bootstrap mínima que captura errores de importación y DLL antes de cargar Flask/pywin32. Comprobación --self-test antes de preparar los datos.
- El servicio conserva una ruta de datos explícita en su ImagePath; no depende de variables de entorno distintas entre instalador y LocalService.
- El acceso directo lee connection.json en Program Files: solo IP/puerto/nombre, sin secretos. No necesita leer ni crear la configuración privada de ProgramData con un usuario sin elevar.
- Registros persistentes en ProgramData\QualityLite-SetupLogs, fuera de la carpeta cuyo permiso se cambia. Se muestra detalle del fallo y código de Windows; una configuración fallida devuelve código 20 y no ofrece abrir la aplicación como si hubiese terminado correctamente.
- Validación CI configurada para Windows Server 2022 y 2025. Las ejecuciones deben revisarse antes de afirmar resultados. Windows 10, Server 2016 y Server 2019 requieren equipos/VM adicionales; Windows 11 es el equipo de desarrollo actual.

## Distribución comercial

El objetivo de compatibilidad no equivale a haber probado todas las ediciones. Publicar un candidato solo después de registrar instalación limpia, actualización con datos, servicio bajo LocalService, reinicio completo, LAN, respaldo/restauración y desinstalación conservando información en la matriz declarada. Este repositorio conserva también las limitaciones funcionales de la versión Lite.

El instalador sigue sin firma digital de editor: no se dispone del certificado de la empresa. Para distribución comercial deben completarse firma, identidad del editor y condiciones de distribución; no se incorporan certificados inventados ni se recomienda deshabilitar antivirus o políticas del servidor. Revisar las condiciones comerciales de Inno Setup en su [sitio oficial](https://jrsoftware.org/isinfo.php).

Si falla un destino, consultar los registros nuevos en ProgramData\QualityLite-SetupLogs. No borrar bases de datos, no conceder acceso a Todos y no deshabilitar protecciones para continuar.

## Resultados reales de esta revisión

- Suite final: 40 pruebas aprobadas.
- Preparador nativo con elevación: cinco comprobaciones aprobadas (ACL reales, SID restringidos, contenido intacto, rutas con espacios/acentos e idempotencia).
- Ejecutable empaquetado sin Python en PATH: once comprobaciones aprobadas, incluidas self-test y publicación/lectura de URL sin abrir configuración privada.
- Actualización local de 0.1.1 a 0.1.2 en Windows 11 Pro: instalador terminó con código 0; servicio Running/Auto bajo LocalService; SQLite con integridad ok; mismos conteos de usuarios/documentos/archivos/configuración; clave y configuración originales conservadas. Esta instalación local todavía muestra el asistente inicial, por lo que no representa una prueba con datos de producción.
- El comando público del ejecutable instalado devolvió la URL con una sesión sin elevar. El servicio conserva --data-root en su ImagePath.

| Sistema objetivo x64 | Estado comprobado |
|---|---|
| Windows 10 | Pendiente de VM/equipo |
| Windows 11 Pro | Preparador y actualización local aprobados; pendiente instalación limpia 0.1.2, reinicio completo y LAN |
| Windows Server 2016 | Pendiente de VM/equipo |
| Windows Server 2019 | Pendiente de VM/equipo |
| Windows Server 2022 | CI configurada; no equivale a una ejecución aprobada |
| Windows Server 2025 | CI configurada; no equivale a una ejecución aprobada |

El instalador se comprobó como NotSigned. No se declara listo para distribución comercial general mientras falten la matriz de pruebas y la firma del editor.
