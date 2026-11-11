# Cine Madrid · v0.3.0

Agenda personal de cine en Madrid capital, reposiciones y programación futura.

Web: https://ignaciogarijo.github.io/cine-madrid/

## Diseño móvil y aplicación instalable

Tres pestañas: Cartelera, Favoritas y Boletín. Las fuentes, la cobertura y las incidencias se consultan desde el pie. La cabecera muestra el nombre y «Una ciudad. Muchas pantallas.», sin portada promocional.

Cartelera incorpora un calendario mensual compacto que se amplía al pulsar. Comparte búsqueda, cine, tipo de programación, versión y horas con la lista; el calendario conserva visibles las demás fechas compatibles aunque haya un día seleccionado. Seleccionar un día actualiza ambas vistas. Sus filtros también se pueden modificar desde el calendario ampliado. La descarga `.ics` sigue siendo del calendario completo, como indica su enlace.

La web incluye un manifiesto PWA con iconos para Android y Apple y apertura independiente. En Android, usar Instalar o el menú del navegador. En iPhone, abrir en Safari → Compartir → Añadir a pantalla de inicio. La instalación física en un teléfono requiere realizar ese paso en el propio dispositivo y todavía no ha sido comprobada en un teléfono real.

El service worker conserva la aplicación y la última cartelera pública para consultas sin conexión, dentro del ámbito `/cine-madrid/`. Los datos se solicitan primero a la red; si se recuperan de caché se indica en el pie y en Fuentes e incidencias. Las entradas y las actualizaciones requieren conexión. No se almacenan peticiones a TMDB, Telegram, geocodificación ni otros proyectos del mismo dominio. Favoritas y origen conservan las claves locales de la versión anterior.

Verificación del calendario y la PWA: `node --test tests/calendar.test.mjs tests/pwa.test.mjs`.

## Estado real

- **Integrado:** cartelera propia de mk2 Cine Paz, incluidos los días futuros ocultos por el selector de su web.
- **Disponible:** búsqueda, filtros, agenda, enlaces de entradas, exportación iCalendar y Google Calendar por sesión, inventario e incidencias.
- **TMDB:** consulta desatendida desde Actions con `TMDB_READ_TOKEN`. Los alias se descargan automáticamente; se contrastan con la dirección y, en casos dudosos, año y duración. Se conservan el título y la duración publicados por el cine. Los resultados se reutilizan desde una caché de metadatos públicos.
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

Las actualizaciones programadas, las ejecuciones manuales y los cambios de código recogen las fuentes, consultan TMDB y vuelven a publicar. Los datos se conservan en `data/public.json`; las ediciones, en `data/newsletters/`. Los fallos se registran, conservando la última lectura válida. Una caída brusca de volumen preserva las sesiones ausentes como no verificadas. La ausencia de una sesión en una lectura **no confirma su cancelación**.

## Identidad y clasificación

El secreto se utiliza solo en el proceso Python de Actions, nunca en el navegador ni en los archivos publicados. `data/tmdb_cache.json` contiene exclusivamente metadatos públicos y consultas por títulos públicos. Caché de búsquedas: un día; fichas: siete días; límite inicial: 300 solicitudes por ejecución, con reintentos acotados. Si falla la API se conservan las identidades verificadas que siguen correspondiendo a la misma ficha de origen y se registra el problema.

La identificación automática exige título/alias y dirección compatibles. Las erratas leves necesitan corroboración por duración. Las homónimas con la misma dirección no se aceptan sin otra evidencia discriminante. Los casos sin dirección, sin resultados o contradictorios se distinguen en las incidencias; no se atribuyen todos a una supuesta necesidad de Copilot.

Las reglas de clasificación están en `config/classification.json`: una identidad confirmada con estreno comercial en salas (tipos 2/3 de TMDB) al menos 365 días antes de la sesión es una reposición. Se usa el primer estreno comercial nacional o internacional, aunque exista un reestreno reciente en España. Una première de festival (tipo 1) no basta. Las sesiones dentro de los primeros 180 días del estreno comercial se clasifican como estreno actual. Entre ambas ventanas se revisa el contexto, conservando las etiquetas explícitas del cine. El ciclo de clásicos es evidencia independiente. Estos umbrales son reglas iniciales del proyecto, no categorías oficiales de TMDB.

La búsqueda y el calendario incorporan los títulos originales y alias de las fichas identificadas. Favoritas permite buscar las fichas ya identificadas además de las dos iniciales. La búsqueda global de películas ajenas a la cartelera sigue disponible a través del gestor privado con la credencial configurada.

## Modelo y privacidad

Películas, sesiones, cines y fuentes tienen identificadores independientes. Los títulos originales de cada cine se conservan. Solo una coincidencia respaldada por metadatos se confirma. La lista de pendientes no exige introducir alias manualmente.

No publicar claves, tokens, dirección personal ni lista privada. La dirección del formulario de proximidad se guarda en el navegador y se envía a Nominatim únicamente cuando se pulsa Guardar origen. Por ahora se muestran distancias en línea recta, no tiempos andando. Los calendarios públicos contienen exclusivamente sesiones públicas; el aviso personal no se publica.

## Incidencias

Cada incidencia tiene código, fuente, entidad, primera y última detección, gravedad, estado y enlace. Una comprobación correcta posterior puede resolverla; una fuente no comprobada no se marca como resuelta. Los pendientes de integración y de agente se distinguen de los errores reales. Las incidencias privadas del bot solo se guardan en el repositorio privado.

## Fuentes y atribución

- Programación y entradas: cada cine conserva su enlace original; mk2 Cine Paz: https://www.cinepazmadrid.es/es/cartelera
- Inventario inicial comercial: https://www.fiestadelcine.com/salas-adheridas/ (candidatos por contrastar y completar con centros culturales).
- Fichas: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB. El logo oficial y el aviso se muestran en Fuentes e incidencias.

Se consulta robots.txt y no se eluden controles de acceso. Incorporar cada nueva fuente requiere revisar acceso, estructura, condiciones y pruebas con datos reales. No se redistribuyen carteles ni sinopsis.

## Próximos hitos

Consultar `docs/IMPLEMENTACION.md`. La cobertura parcial es explícita en todas las vistas y boletines. No publicar un boletín sin advertir de las fuentes e identidades pendientes.
