# Cine Madrid

Cartelera de Madrid, reposiciones, favoritas personales y boletín. Web estática en [GitHub Pages](https://ignaciogarijo.github.io/cine-madrid/), lectura diaria con Python/GitHub Actions y servicio de TMDB/cuentas en Cloudflare Workers.

## Cobertura (v0.11.0)

El inventario ampliado contiene 42 recintos y 41 lectores configurados. Es un inventario contrastado, todavía no un censo exhaustivo de cualquier espacio que proyecte cine en Madrid. Incluye Madrid capital y los tres recintos IMAX acordados del entorno: Kinépolis Ciudad de la Imagen, Cinesa Parquesur y Cinesa Heron City Las Rozas. El formato IMAX se aplica solo a sesiones que lo indican expresamente.

Fuentes oficiales: Cine Paz, Palacio de Hielo, Verdi, Princesa y Renoir, Golem, Odeon Alcalá Norte, Capitol, Morasol, Cineteca, Artistic Metropol, Cine Estudio (CBA), Cine Doré, Sala Equis, Pequeño Cine Estudio, OCINE Caleido, Callao, Sala Berlanga, Casa de América, Instituto Francés, Academia de Cine, Museo Reina Sofía y Casa de México.

Fuentes alternativas atribuidas: Cinerama para Cinesa, Kinépolis y las cinco salas Yelmo (cuyo lector oficial está preparado, pero GitHub recibe un 403 al comprobar su robots.txt); Publicine complementa metadatos de las dos sedes de Embajadores, cuyas sesiones se leen de su taquilla ReservaEntradas; SensaCine para Palacio de la Prensa. Se conserva la atribución y no se presenta una alternativa como lectura de la web oficial.

FilmAgenda complementa los lectores para las salas identificadas en `config/filmagenda_cinemas.json`. La credencial se guarda en el secreto de GitHub `FILMAGENDA_API_KEY`; el flujo verifica las sumas del manifiesto y de los datos, y nunca envía la credencial al enlace temporal de descarga. Se conservan la atribución CC BY 4.0, los enlaces de FilmAgenda y su fecha de publicación. La fuente es complementaria, puede tener un horizonte de fechas más corto y no confirma por sí sola la identidad en TMDB.

Límites relevantes:

- Palacio de la Prensa: la alternativa ofrece en HTML horarios del día; otras fechas sin horas generan incidencia, no sesiones inventadas.
- Sala Equis: algunas fichas de Kinetike devuelven formularios vacíos sin confirmar si existen sesiones. Se mantienen como lectura parcial.
- Agendas culturales: los programas múltiples o con fechas/horas ambiguas generan incidencia y pueden quedar sin desglosar.
- Odeon: algunas fichas oficiales tienen director vacío y carecen de año de producción; sus horarios se publican, pero la identidad y clasificación quedan pendientes cuando faltan pruebas.
- Fundación Japón: el programa localizado se celebra en otros recintos, como Cine Doré. No se duplica como una sala propia. Sigue pendiente una agenda propia verificable.
- Instituto Italiano, Juan March, Goethe y Museo Arqueológico son candidatos documentados; no se han dado por integrados. Otros espacios municipales ocasionales requieren una auditoría posterior.

El estado y el horizonte de cada lectura se consultan en **Fuentes e incidencias**, al pie de la web. Las cifras de lectores configurados no equivalen a lecturas completas o correctas de la última ejecución.

Detalles reproducibles y comprobaciones reales:

- [Comerciales](docs/COBERTURA_COMERCIALES.md)
- [Independientes](docs/COBERTURA_INDEPENDIENTES.md)
- [Fuentes desbloqueadas](docs/COBERTURA_BLOQUEOS.md)
- [Culturales y auditoría adicional](docs/COBERTURA_CULTURALES.md)

## Uso de la web

Navegación inferior: Cartelera, Favoritas, Boletín y Cuenta. Cartelera agrupa por película, con fechas/horarios por recinto, calendario mensual, selección múltiple de cines y programación, formatos/versiones y orden por próxima sesión o número de valoraciones TMDB. Los enlaces de cada pase permiten consultar entradas y añadirlo a Google Calendar; también hay exportación iCalendar.

Cuenta permite entrar con Google mediante Supabase y guardar un origen. Favoritas busca en todo TMDB mientras se escribe; la selección guarda una identidad estable, no solo un título. La lista y el origen de cada cuenta se sincronizan en un Durable Object independiente de Cloudflare. No se publican en Pages ni en GitHub. Cada persona puede activar avisos Web Push en su dispositivo; los detalles de funcionamiento están en `docs/NOTIFICACIONES.md`. La antigua lista pública permanece de solo lectura para importación y compatibilidad del bot anterior. Los avisos personales de Telegram todavía requieren enlazar cuenta y chat.

Sin sesión, el origen se guarda en ese navegador. Al buscar direcciones se consulta CartoCiudad (IGN/CNIG); las distancias son en línea recta. Las coordenadas de recintos tienen su fuente en el inventario. Un recinto sin coordenadas verificadas no se inventa como cercano.

La PWA se puede instalar desde Chrome en Android o Safari → Compartir → Añadir a pantalla de inicio en iPhone. Su service worker conserva solo recursos públicos dentro de `/cine-madrid/`; nunca intercepta las APIs privadas ni las compras. La última cartelera guardada se identifica cuando se consulta sin conexión. No se ha comprobado esta entrega en todos los modelos de teléfono.

## Ejecutar y comprobar

Windows: doble clic en `ABRIR.cmd`, o:

```powershell
cd C:\Github\cine-madrid
.venv\Scripts\python.exe -X utf8 -m src.pipeline
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
node --test tests/calendar.test.mjs tests/pwa.test.mjs tests/posters.test.mjs services/tmdb/*.test.mjs
```

`python -m src.pipeline --build-only` publica los datos guardados sin releer carteleras. La lectura completa requiere `TMDB_READ_TOKEN` para enriquecer identidades. Las credenciales se guardan en Secrets de Actions, nunca en código o argumentos. [Cloudflare](docs/CLOUDFLARE.md) y [cuentas](docs/CUENTAS.md) documentan la configuración.

## Actualización y fallos

Actions intenta leer diariamente a las 06:17 UTC; GitHub puede retrasar las ejecuciones. Los jueves a las 17:17 UTC se prepara el boletín. Un lanzamiento manual permite actualizar. La programación se guarda en `data/public.json`; cada fuente conserva su fecha de lectura y enlaces.

Las fuentes se consultan respetando robots.txt, pausas y límites. Algunos canales públicos usan POST para consultar fechas o carteleras: no se envían controles que seleccionen sesiones, reserven, compren o paguen.

Un fallo conserva las sesiones futuras de la última lectura como no verificadas. Una caída brusca del número de sesiones genera incidencia y evita interpretar ausencias como cancelaciones. Una agenda vacía solo se acepta cuando el lector reconoce su estructura y puede confirmar ese resultado; se muestra «Sin sesiones anunciadas». Cada incidencia conserva primera/última detección, estado, código y evidencia. Fuentes no comprobadas no se dan por resueltas.

## Identidad, clasificación y carteles

TMDB proporciona alias automáticos, dirección, estrenos comerciales, valoraciones y el cartel común de cada identidad. Se conservan también los títulos originales del cine. Una coincidencia necesita título/alias y dirección compatible, o título exacto/alias con año explícito de la película; el año del calendario no vale como año de producción. Las homónimas ambiguas quedan pendientes y no provocan coincidencias falsas con favoritas.

Los jueves Copilot revisa un máximo de 20 identidades pendientes y sus candidatos de TMDB. Sus propuestas solo se aplican si la ficha del cine coincide con un único candidato proporcionado por TMDB en título o alias y duración (hasta cinco minutos de diferencia); los posibles homónimos sin pruebas siguen pendientes. La revisión se aplica en la siguiente actualización de cartelera. La ejecución consume la cuota de Copilot del propietario del repositorio.

Reglas en `config/classification.json`: la primera distribución comercial reciente en España de una obra reciente se muestra como estreno. Para sesiones todavía sin clasificar, se usa provisionalmente la fecha comercial conocida: con dos años o más se muestran como reposiciones, y con menos como estrenos. Si solo se conoce el año, se usa la diferencia entre años como aproximación. Las sesiones sin fecha ni año fiables siguen en «Por clasificar». Una première de festival no basta. Música en directo, coloquios y otros eventos especiales necesitan señales explícitas de la fuente; un estreno con coloquio sigue apareciendo como estreno.

El cartel procede de TMDB únicamente cuando la identidad está verificada; una película sin cartel usa un marcador discreto. La caché guarda metadatos públicos y tiene reintentos y límites; no se publica la clave.

## Trabajo pendiente

Completar las variantes de programas que figuran como parciales, validar los candidatos culturales y ampliar el censo. Copilot sigue pendiente como apoyo para ambigüedades editoriales; no es necesario para ejecutar diariamente los lectores ya implementados. El bot de Telegram está separado en el repositorio privado y sus credenciales/direcciones no se publican aquí.

Programación y entradas se atribuyen a cada fuente. Identificación y carteles: TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.
