# QualityLite 0.2.1 — acceso denegado al respaldar permisos

## Problema y corrección

La captura recibida corresponde al preparador 0.1.2 incluido en el instalador 0.2.0. La instalación se detenía con código 5 al leer la DACL de `C:\ProgramData\QualityLite\logs\qualitylite.log`. Estar elevado no garantiza READ_CONTROL ni WRITE_DAC sobre un archivo creado por otra identidad o con una denegación explícita.

El preparador 0.2.1 habilita SeBackupPrivilege y SeRestorePrivilege únicamente en su proceso elevado y abre los objetos con FILE_FLAG_BACKUP_SEMANTICS. Respalda la DACL antes de modificarla y utiliza handles para leer, enumerar y aplicar permisos, incluso en carpetas restringidas. Al salir restaura el estado previo de sus privilegios. No toma posesión, no cambia el propietario, no modifica archivos ni elimina datos. Mantiene acceso limitado a SYSTEM, Administradores y LocalService, con restauración de las ACL tocadas si falla su aplicación. Rechaza enlaces/reparse points antes de aplicar cambios.

Referencia técnica: [Microsoft — seguridad de archivos y derechos de acceso](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights).

Si una política de dominio ha retirado estos privilegios, se intenta el acceso ordinario. Si también está denegado, la operación falla con un mensaje que identifica el objeto y los derechos requeridos; no modifica políticas de dominio ni concede acceso a Everyone.

## Uso

Ejecutar `QualityLite-Server-Setup-0.2.1-x64.exe` elevado, sobre la instalación anterior, conservando `C:\ProgramData\QualityLite`. Dejar IP/puerto vacíos para conservar la configuración. No es necesario desinstalar ni borrar bases, logs o evidencias. La edición Escritorio también incorpora la corrección. Se mantienen los formularios formales, logo y modelo de servicio de 0.2.0.

## Regresión reproducida

En Windows 11 Pro se crearon un archivo ficticio `logs\qualitylite.log` y su carpeta con propietario SYSTEM, herencia bloqueada y denegación explícita a Everyone. La lectura ordinaria y el preparador anterior devolvieron código 5; el nuevo terminó con código 0. Se verificaron hash del archivo, propietario original, ACL restringida y reaplicación. Un enlace en los datos se rechazó sin cambiar las ACL ni el destino externo. Informe: `release/prueba-acl-restringida-0.2.1.json`.

Esta reproducción verifica la causa del mensaje recibido, pero no es una prueba en el servidor del cliente. La validación del equipo destino y sus políticas sigue pendiente. Los instaladores aún no llevan firma digital de editor.
