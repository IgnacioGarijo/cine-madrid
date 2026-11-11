# Cine Madrid · v0.6.0

Agenda personal de cine en Madrid capital y salas IMAX de la región, reposiciones y programación futura.

Web: https://ignaciogarijo.github.io/cine-madrid/

## Interfaz compacta en v0.6.0

- Cines en un desplegable personalizado, con selección múltiple, colores y orden por cercanía.
- El calendario es el único selector global de fecha, con botones explícitos para replegarlo. Se elimina el campo de fecha duplicado y los textos «Elige un día».
- Cada película muestra los pases de un día, con su propio selector. Por defecto se utiliza la fecha global seleccionada, o el día de su siguiente pase. El selector permite consultar otras fechas de esa película sin cambiar el calendario global.
- Mi origen ofrece direcciones reconocidas al escribir, mediante CartoCiudad (IGN/CNIG). Seleccionar una guarda sus coordenadas solo en ese navegador y repliega la sección. No se utiliza Nominatim para autocompletar.
- Sugerencias de todo TMDB preparadas mediante un pequeño Worker gratuito, con clave protegida, caché y límite de peticiones. **Pendientes de activar:** crear la cuenta de Cloudflare y configurar dos secretos en GitHub. El flujo conecta la web automáticamente después de comprobar el servicio. Consulta [los pasos de activación](docs/CLOUDFLARE.md). Hasta entonces permanece disponible la búsqueda mediante Actions; no se anuncia como búsqueda instantánea activa.

## Actualización v0.5.0

- Cartelera agrupada por película: una identidad TMDB verificada reúne sus títulos, cines y días. Las identidades pendientes se mantienen separadas para no mezclar homónimas. Cada horario conserva versión, formato, sala y calendario individual.
- Cines y programación siempre visibles, sin menús desplegables. Selección múltiple compartida con el calendario, colores por distancia y grupo de cines a 2 km o menos. El origen se guarda exclusivamente en cada navegador; hay que configurarlo una vez desde Mi origen. Los 20 cines con adaptador tienen coordenadas públicas.
- Orden por próxima sesión o por número de valoraciones de TMDB (no por nota media). Las cifras se actualizan diariamente y las películas sin dato quedan al final del orden por valoraciones.
- Reposiciones y eventos comparten categoría. Los pases con eventos explícitos se distinguen en naranja; otros pases de la misma película conservan su aspecto normal.
- Kinépolis Ciudad de la Imagen y ocho Cinesa (seis en Madrid capital, Parquesur y Heron City Las Rozas) leen Cinerama como fuente alternativa, con fechas explícitas y enlaces de compra de la cadena. Kinépolis devuelve 403 por bloqueo de IP y el proveedor de horarios de Cinesa devuelve errores de disponibilidad. No se han eludido controles. El origen alternativo aparece en Fuentes e incidencias. Solo se marca IMAX cuando la sesión lo indica.
- Añadir favoritas busca en todo TMDB mediante Actions, con paginación. No se limita al catálogo de cartelera. El usuario confirma Buscar en GitHub y vuelve a la web para elegir el resultado; esa búsqueda no añade películas por sí sola. Requiere iniciar sesión en la cuenta propietaria y esperar la publicación; no es búsqueda instantánea. La clave permanece en GitHub. Las consultas y sus resultados son públicos.
- La lista pública es la fuente de las alertas del bot privado. Telegram sigue necesitando sus credenciales y activación; conectar la lista no equivale a activar ni verificar la entrega de mensajes.

## Diseño móvil y aplicación instalable

Tres pestañas: Cartelera, Favoritas y Boletín. Las fuentes, la cobertura y las incidencias se consultan desde el pie. La cabecera muestra el nombre y «Una ciudad. Muchas pantallas.», sin portada promocional.

Cartelera incorpora un calendario mensual compacto que se amplía al pulsar. Comparte búsqueda, cine, tipo de programación, versión, formato y horas con la lista; el calendario conserva visibles las demás fechas compatibles aunque haya un día seleccionado. Seleccionar un día actualiza ambas vistas. Sus filtros también se pueden modificar desde el calendario ampliado. La descarga `.ics` sigue siendo del calendario completo, como indica su enlace.

La web incluye un manifiesto PWA con iconos para Android y Apple y apertura independiente. En Android, usar Instalar o el menú del navegador. En iPhone, abrir en Safari → Compartir → Añadir a pantalla de inicio. La instalación física en un teléfono requiere realizar ese paso en el propio dispositivo y todavía no ha sido comprobada en un teléfono real.

El service worker conserva la aplicación y la última cartelera pública para consultas sin conexión, dentro del ámbito `/cine-madrid/`. Los datos se solicitan primero a la red; si se recuperan de caché se indica en el pie y en Fuentes e incidencias. Las entradas y las actualizaciones requieren conexión. No se almacenan peticiones a TMDB, Telegram, geocodificación ni otros proyectos del mismo dominio. Favoritas carga una lista pública común. El origen sigue guardado solo en el navegador.

Verificación del calendario y la PWA: `node --test tests/calendar.test.mjs tests/pwa.test.mjs`.

## Estado real

- **Conectores:** Cine Paz, Palacio de Hielo, Verdi Madrid, Cines Princesa, Renoir Plaza de España, Renoir Retiro, Cineteca, Artistic Metropol, Cine Estudio (CBA), Capitol y Morasol. También se leen Kinépolis Ciudad de la Imagen y ocho Cinesa mediante Cinerama. El estado de cada lectura y su última fecha publicada se muestran en Fuentes e incidencias. El horizonte depende de lo que publique cada fuente; no se inventan fechas a partir de rangos de ciclos.
- **Disponible:** búsqueda, filtros, agenda, enlaces de entradas, exportación iCalendar y Google Calendar por sesión, inventario e incidencias.
- **TMDB:** consulta desatendida desde Actions con `TMDB_READ_TOKEN`. Los alias se descargan automáticamente; se contrastan con la dirección y, en casos dudosos, año y duración. Se conservan el título y la duración publicados por el cine. Los resultados se reutilizan desde una caché de metadatos públicos.
- **Parcial:** inventario de cines y espacios. No es todavía un censo validado de todos los cines de Madrid. El listado de Fiesta del Cine es una fuente inicial, no una garantía de exhaustividad ni de municipio correcto.
- **Pendiente:** los demás conectores del inventario, rutas andando, agente Copilot y clasificación editorial completa. Las películas no identificadas se muestran sin confirmar y no originan falsas coincidencias con pendientes.
- **Favoritas públicas:** `config/favorites.json` contiene la lista compartida, inicialmente Mad Max: Fury Road e Interstellar. La web muestra solo una lista y el botón Añadir. El diálogo consulta todo TMDB a través de una búsqueda confirmada en GitHub. La confirmación se realiza mediante una solicitud de GitHub; únicamente la cuenta propietaria puede modificar la lista. Las ambigüedades generan candidatos para confirmar. Las solicitudes de visitantes no ejecutan el proceso.
- **IMAX:** Kinépolis Ciudad de la Imagen (Pozuelo), Cinesa Parquesur (Leganés) y Heron City Las Rozas están en el inventario con evidencia del recinto. Tener una sala IMAX no convierte todas sus sesiones en IMAX. El filtro de formato utiliza solo etiquetas explícitas de sesión. Sus horarios se leen mediante la fuente alternativa indicada en el registro de fuentes.
- **Privado:** dirección y bot en `cine-madrid-personal`. La lista pública no expone la configuración del bot ni su lista privada; los avisos siguen utilizando la lista privada hasta conectar ambas expresamente.

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

El secreto se utiliza solo en el proceso Python de Actions, nunca en el navegador ni en los archivos publicados. `data/tmdb_cache.json` contiene exclusivamente metadatos públicos y consultas por títulos públicos. Caché de búsquedas: un día; fichas: siete días; límite: 1.000 solicitudes por ejecución, con reintentos acotados. Si falla la API se conservan las identidades verificadas que siguen correspondiendo a la misma ficha de origen y se registra el problema.

La identificación automática exige título/alias y dirección compatibles, o título exacto/alias y año de la película explícito si falta la dirección. Si hay varios candidatos con el mismo título y año no se confirma ninguno. Las erratas leves necesitan corroboración por duración. Las homónimas con la misma dirección no se aceptan sin otra evidencia discriminante. Los casos sin evidencia independiente, sin resultados o contradictorios se distinguen en las incidencias; no se atribuyen todos a una supuesta necesidad de Copilot.

Las reglas de clasificación están en `config/classification.json`: una identidad confirmada con estreno comercial en salas (tipos 2/3 de TMDB) al menos 365 días antes de la sesión es una reposición. Se usa el primer estreno comercial nacional o internacional, aunque exista un reestreno reciente en España. Una première de festival (tipo 1) no basta. Las sesiones dentro de los primeros 180 días del estreno comercial se clasifican como estreno actual. Entre ambas ventanas se revisa el contexto, conservando las etiquetas explícitas del cine. El ciclo de clásicos es evidencia independiente. Estos umbrales son reglas iniciales del proyecto, no categorías oficiales de TMDB.

La búsqueda y el calendario incorporan los títulos originales y alias de las fichas identificadas. Añadir una favorita permite buscar fichas identificadas o enviar cualquier título y año al proceso de TMDB en Actions. No se requiere introducir alias.

## Modelo y privacidad

Películas, sesiones, cines y fuentes tienen identificadores independientes. Los títulos originales de cada cine se conservan. Solo una coincidencia respaldada por metadatos se confirma. La lista de pendientes no exige introducir alias manualmente.

No publicar claves, tokens, dirección personal ni lista privada. La lista pública de favoritas sí se publica por decisión del propietario. La dirección del formulario de proximidad se guarda en el navegador y se envía a Nominatim únicamente cuando se pulsa Guardar origen. Por ahora se muestran distancias en línea recta, no tiempos andando. Los calendarios públicos contienen exclusivamente sesiones públicas; el aviso personal no se publica.

## Incidencias

Cada incidencia tiene código, fuente, entidad, primera y última detección, gravedad, estado y enlace. Una comprobación correcta posterior puede resolverla; una fuente no comprobada no se marca como resuelta. Los pendientes de integración y de agente se distinguen de los errores reales. Las incidencias privadas del bot solo se guardan en el repositorio privado.

## Fuentes y atribución

- Programación y entradas: cada cine conserva su enlace original; mk2 Cine Paz: https://www.cinepazmadrid.es/es/cartelera
- Inventario inicial comercial: https://www.fiestadelcine.com/salas-adheridas/ (candidatos por contrastar y completar con centros culturales).
- Fichas: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB. El logo oficial y el aviso se muestran en Fuentes e incidencias.

Se consulta robots.txt y no se eluden controles de acceso. Incorporar cada nueva fuente requiere revisar acceso, estructura, condiciones y pruebas con datos reales. No se redistribuyen carteles ni sinopsis.

## Próximos hitos

Consultar `docs/IMPLEMENTACION.md`. La cobertura parcial se detalla en Fuentes e incidencias y en los boletines. No publicar un boletín sin advertir de las fuentes e identidades pendientes.
