# Entrega QualityLite 0.1.0 — 21 de octubre de 2026

Primera versión funcional con alcance parcial del pliego. No es todavía una entrega final validada en producción.

## Archivos

- `release/QualityLite-Setup-0.1.0-x64.exe`: instalador compilado con Inno Setup; la instalación elevada y limpia no se ha ejecutado.
- `dist/QualityLite/QualityLite.exe`: ejecutable con dependencias incluidas en el mismo directorio; no distribuir el EXE solo.
- `release/QualityLite-fuentes-0.1.0.zip`: código, plantillas, recursos, pruebas, scripts, manuales, licencias y base inicial vacía. No incluye datos ni claves de las pruebas.
- `release/base-inicial.sqlite3`: esquema inicial, sin cuentas ni contraseñas. El instalador genera la base directamente cuando no existe.
- `release/SHA256.txt`: hash del instalador.
- `release/pruebas.xml`, `test-log.txt`: resultados de pytest.
- `release/prueba-ejecutable.json`: comprobaciones HTTP reales del ejecutable congelado.
- `release/asistente.png`: evidencia visual del asistente en navegador con ancho de tableta.
- `MANUAL.md`: instalación, administración, uso, respaldo/restauración, actualización y desinstalación.
- `ARQUITECTURA.md`: diseño y lista detallada de funciones no implementadas.
- `build.ps1`, `installer.iss`, `requirements-lock.txt`: compilación y dependencias efectivas.

## Funciones implementadas

Empresa y superusuario inicial con token local; contraseñas scrypt; roles con controles de backend; bloqueo de intentos; sesiones/CSRF; historial; documentos/versiones con aprobación separada; diseñador sin programación; registros con esquema congelado y evidencia por campo; archivos privados con hash y comprobación MIME; cierre inmutable; fichas básicas de auditoría, no conformidad y acciones; PDF/Excel; respaldo manual o diario con copia externa opcional; restauración local autenticada y recuperación administrativa; detección de IP/puertos; servicio Windows y scripts de instalación/administración.

## Pruebas aprobadas

26 pruebas automatizadas: páginas y CSRF, permisos Calidad/Auditor/Visor, separación de aprobación, conservación de versiones, formato dinámico y evidencia requerida, cierre inmutable, rechazo de archivo falso y código duplicado, PDF/Excel, respaldo íntegro, bloqueo por intentos, protección del token inicial, copia automática sin duplicación, auditorías/no conformidades/acciones, conflicto de puerto, restauración real del contenido SQLite con interfaz de entrada controlada y servicio declarado detenido en la prueba, restricción de documentos privados y descargas para Auditor/Visor.

El ejecutable congelado se probó con datos aislados y PATH limitado a System32: inicialización, Waitress por HTTP real, comando de salud, configuración inicial, login/tablero, plantillas/recursos, alta documental, PDF/Excel y respaldo. No utiliza el servidor de desarrollo Flask.

## Pendiente de prueba en entorno dedicado

La cuenta usada no tiene privilegios administrativos. No se instalaron servicios ni se alteró el firewall del equipo. Falta ejecutar: instalación limpia en Windows, inicio/paro y recuperación del servicio bajo LocalService, arranque después de reiniciar Windows, conexión desde otro equipo, aplicación de firewall, actualización conservando datos y desinstalación conservando datos. El compilador verificó sintaxis del instalador; esto no sustituye instalarlo.

## Limitaciones funcionales principales

Asistente consolidado; roles fijos sin editor; auditorías/checklists y referencias a hallazgos en texto; tablas como filas de texto; sin campos calculados ni firma electrónica; esquema de formato no editable después de crear; sin visor embebido de evidencias; reportes generales sin indicadores avanzados ni filtros por periodo; sin logotipo ni carpetas independientes para documentos y evidencias; red/firewall/reinicio requieren herramienta local; restauración no atómica frente a corte eléctrico. Lista completa en ARQUITECTURA.md.

El instalador no está firmado. El sistema no afirma conformidad ni certificación ISO automática. Las funciones pendientes están documentadas y no se representan mediante botones simulados.
