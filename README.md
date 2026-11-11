# Cine Madrid · v0.1.1

Agenda personal de cine en Madrid capital, reposiciones y programación futura.

Web: https://ignaciogarijo.github.io/cine-madrid/

## Estado real

- **Integrado:** cartelera propia de mk2 Cine Paz, incluidos los días futuros ocultos por el selector de su web.
- **Disponible:** búsqueda, filtros, agenda, enlaces de entradas, exportación iCalendar y Google Calendar por sesión, inventario e incidencias.
- **Parcial:** inventario de cines y espacios. No es todavía un censo validado de todos los cines de Madrid. El listado de Fiesta del Cine es una fuente inicial, no una garantía de exhaustividad ni de municipio correcto.
- **Pendiente:** resto de conectores, rutas andando, agente Copilot y clasificación editorial completa. Las películas no identificadas se muestran sin confirmar y no originan falsas coincidencias con pendientes.
- **Privado:** lista central de pendientes, dirección y bot en `cine-madrid-personal`. La lista local del navegador es independiente; exportar/importar permite trasladarla entre navegadores.

## Ejecutar en Windows

Doble clic en `ABRIR.cmd`. Primera instalación: Python 3.12 o posterior y acceso a Internet.

```powershell
cd C:\Github\cine-madrid
.venv\Scripts\python.exe -m src.pipeline
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La web es estática y no requiere Node ni un servidor permanente. Se ha elegido HTML/CSS/JS directo para el primer buscador, reduciendo dependencias; se puede adoptar Astro cuando crezca el archivo editorial.

## Actualizaciones

GitHub Actions recoge la fuente a las 06:17 UTC (07:17 en invierno y 08:17 en verano en Madrid). El boletín se genera los jueves a las 17:17 UTC. Son horarios objetivo; GitHub puede retrasar o perder ejecuciones programadas y suspenderlas en repositorios públicos sin actividad durante 60 días. Una ejecución manual permite actualizar.

Los cambios de código publican los últimos datos válidos. Las actualizaciones programadas recogen fuentes y vuelven a publicar. Los datos se conservan en `data/public.json`; las ediciones, en `data/newsletters/`. Los fallos se registran, conservando la última lectura válida. Una caída brusca de volumen preserva las sesiones ausentes como no verificadas. La ausencia de una sesión en una lectura **no confirma su cancelación**.

## Modelo y privacidad

Películas, sesiones, cines y fuentes tienen identificadores independientes. Los títulos originales de cada cine se conservan. Solo una coincidencia respaldada por metadatos se confirma. La lista de pendientes no exige introducir alias manualmente.

No publicar claves, tokens, dirección personal ni lista privada. La dirección del formulario de proximidad se guarda en el navegador y se envía a Nominatim únicamente cuando se pulsa Guardar origen. Por ahora se muestran distancias en línea recta, no tiempos andando. Los calendarios públicos contienen exclusivamente sesiones públicas; el aviso personal no se publica.

## Incidencias

Cada incidencia tiene código, fuente, entidad, primera y última detección, gravedad, estado y enlace. Una comprobación correcta posterior puede resolverla; una fuente no comprobada no se marca como resuelta. Los pendientes de integración y de agente se distinguen de los errores reales. Las incidencias privadas del bot solo se guardan en el repositorio privado.

## Fuentes y atribución

- Programación y entradas: cada cine conserva su enlace original; mk2 Cine Paz: https://www.cinepazmadrid.es/es/cartelera
- Inventario inicial comercial: https://www.fiestadelcine.com/salas-adheridas/ (candidatos por contrastar y completar con centros culturales).
- Fichas: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB. El uso de la API queda pendiente de la credencial y de completar su atribución conforme a sus requisitos antes de activarla.

Se consulta robots.txt y no se eluden controles de acceso. Incorporar cada nueva fuente requiere revisar acceso, estructura, condiciones y pruebas con datos reales. No se redistribuyen carteles ni sinopsis.

## Próximos hitos

Consultar `docs/IMPLEMENTACION.md`. La cobertura parcial es explícita en todas las vistas y boletines. No publicar un boletín sin advertir de las fuentes e identidades pendientes.
