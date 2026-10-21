# QualityLite 0.1 — arquitectura y alcance

Aplicación monolítica Flask, plantillas Jinja, CSS y JavaScript locales. Waitress atiende seis hilos; SQLite utiliza WAL, claves foráneas y consultas parametrizadas. Las mutaciones HTTP se serializan para mantener consistencia con el respaldo de archivos. Base de datos inicial sin empresa ni contraseñas: se genera con `--init`. El servicio pywin32 ejecuta el mismo binario congelado con PyInstaller, bajo LocalService. Inno Setup empaqueta el directorio completo, sin descargar dependencias durante la instalación.

Los datos se ubican en `%ProgramData%\QualityLite`, fuera de Program Files; ACL restringida a administradores, SYSTEM y LocalService. El instalador exige Windows 10/11 o Server compatible x64 y elevación. El host inicial es 127.0.0.1. La administración web permite seleccionar IPv4 y puerto; aplicar firewall/reinicio exige administración local. La regla se limita a subred local y perfiles privado/dominio.

Tablas: settings (empresa única/configuración), users (roles/hash scrypt), items (documentos, esquemas, registros y seguimiento), files (campo propietario, hash y metadatos), events (historial), attempts (bloqueo temporal). La versión de esquema SQLite es 1. Los esquemas de formatos se copian al registro; versiones vigentes/aprobadas no admiten sobrescritura. Cada versión tiene su propia fila. Un segundo superusuario debe aprobar documentos/formatos; Calidad no aprueba.

## Alcance real de la entrega

Implementado: alta inicial local con token, empresa, altas de usuarios por rol, cambio de contraseña, sesiones y CSRF, control documental y versiones, diseñador de campos sin código, registros y evidencias por campo, flujo de revisión/aprobación, cierre inmutable, auditorías y no conformidades básicas como fichas, acciones con eficacia para cerrar, PDF y Excel por módulo, respaldos completos con manifiesto SHA-256 y copia externa opcional, programación diaria, restauración local autenticada y recuperación local administrativa, servicio e instalador.

## Diferencias respecto del alcance solicitado

Esta entrega es una primera versión 0.1 y no cubre el pliego completo. No presentarla como versión final certificada para producción.

- La interfaz utiliza CSS propio; Bootstrap no está incluido. Todos los recursos funcionan sin Internet.
- Asistente inicial consolidado en una página; red y usuarios se completan después. Sin logotipo, prefijos configurables, fecha configurable ni carpetas independientes para documentos/evidencias.
- Roles fijos sin editor de permisos; falta desactivar/editar usuarios en interfaz. No hay permisos por área o registro. Todo rol autenticado consulta módulos operativos; Visor solo ve vigentes/cerrados.
- Campos calculados y firma electrónica no incluidos. Tabla es texto con filas separadas por saltos de línea; identificación del responsable es texto. No hay edición de esquema una vez creado ni ordenación por arrastre. Para cambiar estructura se crea otro formato con código distinto. Una nueva versión documental permite cambiar metadatos y archivos.
- Fotografías/documentos se descargan; no hay visor embebido ni miniaturas. Evidencias se agregan, nunca se sustituyen ni eliminan en esta versión. No hay borrado lógico de elementos.
- Auditorías: fichas con checklist textual y adjuntos generales, sin programa anual ni preguntas/hallazgos estructurados. Vínculos a auditorías/no conformidades son identificadores de texto, sin claves foráneas. Falta validación de relaciones y cronología.
- Informes generales PDF/Excel, búsqueda textual; sin filtros avanzados por periodo ni indicadores de cumplimiento, vencimientos o evidencias faltantes consolidados. PDF presenta datos en texto e índice de archivos, sin incrustar imágenes.
- Red: muestra dirección y valida bind local; no comprueba conectividad desde otros equipos. Firewall y reinicio se aplican con herramienta local elevada, no desde el proceso web. Nombre de servidor no configurable.
- Respaldos diarios o manuales, sin selector de hora, retención o interfaz de errores; errores automáticos se registran en logs. Restauración local con servicio detenido y respaldo previo; no dispone de transacción atómica entre base de datos y archivos ante corte eléctrico durante restauración. Conserva archivos adicionales como huérfanos; no son visibles sin metadatos.
- Validación de extensión/MIME/estructura Office; no incluye antivirus. Límite de 25 MB por petición. HTTP solo para LAN confiable; no incluye certificados TLS ni proxy HTTPS.
- Historial de aplicación sin edición web; no es registro criptográfico inviolable frente a administradores del servidor. Sin protección avanzada de sesiones concurrentes ni MFA.
- Instalador sin firma de editor. No se debe asumir prueba de servicio, reinicio, firewall, actualización/desinstalación ni Windows limpio hasta ejecutar esos escenarios con privilegios en un entorno dedicado.
