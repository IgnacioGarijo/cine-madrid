# Fuentes desbloqueadas: comprobación del 12 de noviembre de 2026

Lectores en `src/adapters_special.py`. Registrar `sala_equis`, `pequeno_cine` y `ocine_caleido` en `ADAPTERS`; el padre integra el registro y la configuración. No se ha ejecutado el pipeline en esta tarea.

| Cinema id | adapter | schedule_url |
| --- | --- | --- |
| `sala-equis` | `sala_equis` | `https://salaequis.es/taquilla/` |
| `peque-o-cine-estudio` | `pequeno_cine` | `https://www.pcineestudio.es/en-cartel` |
| `ocine-urban-caleido` | `ocine_caleido` | `https://tickets.ocineurbancaleido.es/?nocap=1` |
| `palacio-prensa` | `palacio_prensa` | `https://www.sensacine.com/cines/cine/E0559/` |

## Sala Equis

La taquilla oficial enlaza fichas de películas. Cada ficha enlaza a `https://kinetike.com:83/views/sesionesFuturas.aspx?idPelicula=…&cine=EQUIS`. Su GET muestra fechas completas. Para conocer las horas, se envía POST a la misma URL con campos ocultos del formulario y exclusivamente el botón de consulta de fecha, por ejemplo `01=SESIONES`. La respuesta publica las horas en `#PanelSesiones01`. No se envían los botones de hora, no se selecciona una sesión y no se compra ni reserva.

`Fetcher.post` comparte Session, cookies, User-Agent, comprobación robots por origen, pausa de 0,3 s, timeout de 35 s y decodificación con GET. Admite formulario o JSON. El lector rechaza botones de fechas sin fecha única, paneles ausentes y horas ambiguas; una fecha o un intervalo de ciclo nunca genera un pase por sí solo. Cada hora se vincula al panel de la fecha consultada. Dirección, duración y VOSE se leen de la ficha oficial cuando aparecen; la ausencia de VOSE no implica doblaje. La ficha oficial se conserva como `source_url` y Kinetike como `booking_url`.

Lectura real completa con fecha de referencia 2026-11-12: **43 pases, 31 películas**. Ejemplos: *La bola negra*, 13/11/2026 a las 19:15; *A paixâo segundo G.H.B.*, 16/11 a las 17:00. Trece fichas enlazadas devolvieron un Kinetike sin fechas verificables (entre ellas *Aftersun* y *Vidas pasadas*): se registran como lectura parcial y no como programación vacía confirmada. Por tanto, los 43 pases son verificables, pero no se afirma que la cobertura de esas trece fichas esté resuelta.

## Pequeño Cine Estudio

La segunda ruta oficial, `/en-cartel`, sí contiene bloques Wix de películas con horarios individuales, a diferencia de la portada. El lector mantiene la asociación entre horario y ficha dentro de `.wixui-repeater__item`. Lee título original, dirección y duración de las etiquetas explícitas y horarios como `J12/11-17.30h`; el año de los días sin año se resuelve con `parse_day`, igual que en otras fuentes. No toma el año de producción como año de sesión. Descarta los días anteriores a la fecha de lectura.

Lectura real: **2 pases futuros, 2 películas**, ambos 12/11/2026: *200 vidas, Paco Rabal* a las 17:30 y *Los ojos del diablo* a las 22:00. No se registra VOSE por la mera cabecera genérica «cine en versión original». Los enlaces de venta proceden del botón oficial y conducen a `https://feverup.com/m/95546`. La cobertura publicada en esta lectura es semanal y no garantiza fechas posteriores. Los monólogos y conciertos de portada no se convierten en películas.

## OCINE Urban Caleido

La aplicación oficial enlaza su taquilla en la respuesta pública `https://ocineurbancaleido.es/api/apps/6a97dfbd86e3ee5d479bffd5/entities/SiteSettings?sort=-updated_date&limit=1`. La comprobación confirmó nombre OCINE URBAN CALEIDO, dirección P.º de la Castellana, 259 y `ticketing_url` de `tickets.ocineurbancaleido.es`. No se conserva esa respuesta completa en fixtures.

El bundle público de la taquilla `/js/app.180e1b89.js` documenta la consulta pública POST `/api/v1/sessions` con JSON `{token: '', idioma: 'es', urlWeb: 'https://tickets.ocineurbancaleido.es/?nocap=1'}`. El lector exige el nombre de cine exacto normalizado. Las fichas GET `/api/v1/pelicula/{id}?lang=es` desglosan los grupos por variante y publican `sessions`, con `data`, `hora`, `planificacio` y sala. Consulta cartelera, estrenos y venta anticipada. No llama a `/seleccionarsessio`, asientos, precios o pagos. No guarda tokens.

Lectura real: **291 pases, 18 películas**, desde 12/11/2026 15:45 hasta 07/01/2027 22:15, sin incidencias del lector. Ejemplo: *Clayface*, 12/11 a las 15:45, VOSE, SALA 4, id de sesión 37596, dirección James Watkins, 108 minutos. VOSE y formatos proceden de cada variante; no se heredan del grupo que puede mezclar versiones. `source_url` y `booking_url` apuntan a la ficha humana `https://tickets.ocineurbancaleido.es/#/DetallPelicula/{id}`; las APIs consultadas quedan en `result.pages`.

## Límites y pruebas

### Palacio de la Prensa: cobertura parcial en SensaCine

Tras las rutas oficiales y los índices candidatos documentados en `COBERTURA_COMERCIALES.md`, se comprobó un máximo de dos fuentes alternativas. eCartelera, `https://www.ecartelera.com/cines/38,0,1.html`, identifica Plaza Callao 4, pero declara «Este cine no tiene sesiones ahora mismo». No se usa para afirmar cartelera vacía porque SensaCine publica pases verificables.

SensaCine, `https://www.sensacine.com/cines/cine/E0559/`, permite la lectura mediante Fetcher. Su JSON-LD identifica Cines Palacio De La Prensa, **3 salas**, Plaza del Callao 4, Madrid. El lector `palacio_prensa` valida esos cuatro atributos antes de aceptar películas de `.movie-card-theater`; no recoge los eventos ajenos al cine de la web oficial. Cada pase incluye `data-showtime-time` ISO con zona horaria e identificador nativo. Dirección y doblaje se conservan cuando la ficha los indica; duración queda vacía si no aparece. No se utiliza el año de estreno como fecha de pase.

Lectura real del 12/11/2026: **6 pases, 3 películas**, todos ese día: *Ruega por nosotras* (15:30, 18:00, 21:00), *Esta soledad* (15:30, 21:00) y *La Bola Negra* (18:00), con indicación explícita de versión doblada. El calendario anuncia además 13, 14, 15 y 18 de noviembre y 4 de diciembre, pero sin publicar sus horas en el HTML leído. Se registra `partial_read` por esas fechas y no se crean sesiones a partir del calendario.

El bundle público de SensaCine permite observar que la actualización de fechas depende de una ruta interna registrada como `internal_api_showtimes_theater_filtered`. La solicitud de su configuración `https://www.sensacine.com/_/js/routing?callback=AC.setRouting` queda rechazada por Fetcher: robots contiene `Disallow: /_/`. No se accede a esa ruta ni se elude la restricción; no se afirma cobertura de las fechas pendientes.

Integración: id `palacio-prensa`, adapter `palacio_prensa`, `schedule_url` exacta de SensaCine arriba, `schedule_label: "SensaCine · fuente alternativa"`, `reading_note: "Horarios parciales de SensaCine; otras fechas anunciadas requieren consulta manual. Entradas desde su ficha de cine."`. Este lector propio no requiere `source_names` ni `booking_origins`, ya que valida la identidad estructurada exacta y conserva la propia ficha de SensaCine como `source_url` y `booking_url`. No se inventa un enlace individual de compra. Registrar el lector mediante el mecanismo de adaptadores adicionales del padre.

Las dos alternativas GuíaMadrid investigadas anteriormente seguían sin ser necesarias: sus errores TLS no se eluden ni se desactiva la validación de certificados. Todos los accesos de esta implementación pasan por Fetcher y respetan robots, sin evasión de bloqueos.

Pruebas: `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_special.py -v`: **10 pruebas superadas**. Cubren unión de fecha-panel, ausencia de horas, prohibición de enviar controles de sesión, metadatos y días individuales de Pequeño, variantes VOSE de OCINE, recinto incorrecto, robots y POST, además de horarios ISO, fechas sin horas y recinto de Palacio de la Prensa. La suite Python completa pasó **83 pruebas** tras añadir Palacio de la Prensa y las pruebas incorporadas paralelamente por el padre. Fixtures recortadas, sin tokens reales ni sinopsis completas. Las cifras anteriores son lecturas reales de los lectores; no son una comprobación posterior de despliegue.
