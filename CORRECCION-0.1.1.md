# Corrección 0.1.1 — instalación de Windows

El usuario reportó que 0.1.0 detenía la instalación al ejecutar icacls sobre la carpeta de datos. Se reprodujo el mismo comando en una carpeta vacía real de Windows: procesó la carpeta, devolvió acceso denegado al intentar continuar el recorrido y terminó con código 5.

Cambios:

- Se sustituye icacls por la API Win32 SetNamedSecurityInfo. Se enumeran los destinos antes del cambio y se aplican ACL completas desde los hijos hacia el padre; no se atraviesan enlaces ni junctions.
- Se mantienen únicamente Administradores y SYSTEM con control total y LocalService con modificación. No se concede acceso a Todos ni se relajan los permisos para evitar el error.
- Los códigos de error de pywin32 se devuelven al instalador. Antes podían quedar ocultos porque HandleCommandLine retornaba un error que no se propagaba al proceso.
- Se espera hasta 30 segundos al detener/iniciar servicio. Las actualizaciones reconfiguran el servicio existente, sin eliminarlo antes de volver a registrarlo.
- Los comandos del servicio escriben logs/service-commands.log; el instalador activa su log propio y muestra códigos concretos. Si no se puede escribir en ProgramData, el error se registra en %TEMP%\QualityLite-install-error.log.

Las pruebas adicionales usan ACL reales sobre carpeta vacía y árbol con evidencia, verifican los tres SID exactos y comprueban que el archivo conserva su contenido. También verifican propagación de error del servicio y secuencia del instalador. Resultado local: 30 pruebas aprobadas y 9 comprobaciones HTTP del ejecutable congelado aprobadas.

La sesión local no dispone de elevación administrativa; las pruebas de ACL no sustituyen instalar el servicio bajo LocalService. El flujo CI de Windows permite ejecutar esa validación en un runner dedicado con administración. Hasta obtener resultado de CI, la instalación completa permanece pendiente de verificación.

Para reintentar, ejecutar el instalador 0.1.1 como administrador en la misma ruta. No eliminar la base de datos ni evidencias ni desactivar las protecciones de Windows.
