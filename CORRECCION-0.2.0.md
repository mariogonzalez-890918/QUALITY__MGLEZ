# QualityLite 0.2.0 — ediciones de instalación e identidad documental

## Entregables

- `QualityLite-Server-Setup-0.2.0-x64.exe`: perfil Servidor para Windows Server 2016, 2019, 2022 y 2025 x64. Agrega páginas para elegir escucha IPv4/puerto y autorizar el acceso LAN. La regla solo permite la subred local en perfiles privado/dominio y el ejecutable de QualityLite. Una actualización sin cambios conserva la red anterior.
- `QualityLite-Desktop-Setup-0.2.0-x64.exe`: perfil Escritorio para Windows 10/11 x64. La primera instalación escucha localmente; la administración permite después configurar LAN.

Ambas ediciones usan el mismo motor, servicio, AppId y directorio persistente: son perfiles de instalación de un producto, no instancias paralelas ni binarios diferentes por cada año de Windows Server. No se crean cuatro copias del mismo EXE con nombres que impliquen validaciones distintas.

## Documentos formales

En **Empresa** se carga/reemplaza el logo PNG/JPEG y se configura la leyenda y el pie. Se valida contenido real, tamaño y dimensiones; se normaliza a PNG sin metadatos. No se admite SVG ni contenido ejecutable. La identidad de los nuevos documentos/registros queda asociada a su captura, de modo que los logos anteriores no se borran al reemplazar la imagen.

El PDF usa un encabezado corporativo repetido, código/versión, folio, fecha, estado, secciones numeradas, tablas y responsables con espacio de firma autógrafa. El pie incluye página actual y total. Los PDF de registro muestran etiquetas comprensibles, no estructuras JSON ni identificadores internos. Fotografías compatibles se insertan, conservando el archivo original y su índice/hash. Un espacio de firma no equivale a firma electrónica ni aprueba automáticamente un documento.

Las exportaciones Excel incorporan logo, encabezado, filtros, formato de impresión y una hoja de detalle con nombres de campos y respuestas legibles.

## Modelo de solicitud de servicio

En **Diseñador de formatos → Usar modelo editable**, se precargan 19 campos en cinco bloques: identificación, descripción de la necesidad, atención/seguimiento, cierre y evidencias. Se pueden cambiar etiquetas, obligatoriedad, opciones, secciones, anchura y columnas de tabla antes de guardar. La tabla de actividades permite agregar/quitar filas durante la captura. El modelo se guarda como borrador, no aprobado ni supuestamente oficial de ISO.

Los registros abiertos se pueden editar en **Editar el borrador**. El cierre sigue siendo inmutable y los controles de evidencia requerida se mantienen en el backend.

## Referencias y pruebas

Las muestras de `output/pdf` usan empresa y logo ficticios, tomando como referencia visual la hoja de servicio del proyecto local de servicios. No incluyen datos ni marcas de un cliente como plantilla universal. Se revisaron las páginas renderizadas para comprobar encabezados, tablas, saltos y numeración.

Las pruebas de cada instalador se documentan por separado. Los nombres de Windows anteriores son objetivos de despliegue; no se debe afirmar certificación o prueba satisfactoria en todas sus ediciones sin disponer de la matriz real. La firma digital de editor sigue pendiente de un certificado de la empresa.

## Validación local realizada

45 pruebas automatizadas y 11 comprobaciones HTTP del ejecutable superadas. Las actualizaciones de los perfiles Escritorio y Servidor se ejecutaron en Windows 11 Pro, con servicio automático LocalService, salud HTTP y conservación de conteos, clave y configuración. Esto valida ambos instaladores en ese equipo; no sustituye pruebas en Windows Server 2016/2019/2022/2025 ni Windows 10. Los informes están en release/prueba-instalacion-0.2.0.json y release/prueba-perfil-server-0.2.0.json.

Las limitaciones de la sección histórica 0.1 de ARQUITECTURA.md relativas a logo, tablas de captura y PDF de texto quedan sustituidas por esta entrega 0.2.0. El resto de limitaciones sigue vigente.
