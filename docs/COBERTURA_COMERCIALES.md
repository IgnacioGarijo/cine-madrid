# Cobertura comercial: comprobación del 12 de noviembre de 2026

## Fuentes oficiales con lector nuevo

Registrar `from .adapters_commercial import odeon, golem` después de definir las utilidades de `adapters.py`, y `ADAPTERS.update({'odeon': odeon, 'golem': golem})`. Los lectores requieren el campo `schedule_url`.

- `golem-madrid`: `adapter: golem`, `schedule_url: https://golem.es/golem/golem-madrid/`, dirección C/ Martín de los Heros, 14. La página diaria de la propia cadena publica enlaces a otras fechas. Lectura directa: 101 pases del 12 al 17 de noviembre; 37 marcados VOSE. El título y horario se leen juntos en cada bloque; la versión solo se indica cuando la fuente la hace explícita.
- `odeon-multicines-alcala-norte`: `adapter: odeon`, `schedule_url: https://odeonmulticines.com/odeon-alcala-norte/peliculas`, dirección C/ Alcalá, 414. Lectura directa: 338 pases futuros, 29 VOSE. Los bloques contienen fecha completa, formato y enlace individual de venta. No se infiere doblaje por ausencia de versión original.

Ambos se verificaron mediante `Reader`/`Fetcher`, sin ejecutar el pipeline; `python -X utf8 -m unittest tests.test_commercial` pasa dos pruebas con fixtures.

## Yelmo: alternativa Cinerama ya compatible

El lector existente `cinerama` puede utilizarse con `booking_origins: ["https://cineyelmo.com/"]`, `schedule_label: "Cinerama · fuente alternativa"` y `reading_note: "Horarios de Cinerama (fuente alternativa); entradas enlazadas a la cadena original."`. Se comprobó cada cabecera, fechas completas, enlaces de compra y número de enlaces el 12 de noviembre. Los resultados y formatos se atribuyen a Cinerama; no se atribuye IMAX a pases sin indicación explícita.

| id | schedule_url | source_names | enlaces comprobados |
| --- | --- | --- | ---: |
| cine-yelmo-ideal | https://cinerama.es/cartelera/cine/yelmo-cines-ideal-madrid-v-o/ | ["Yelmo Ideal"] | 225 |
| cine-yelmo-islazul | https://cinerama.es/cartelera/cine/yelmo-cines-islazul/ | ["Yelmo Islazul"] | 222 |
| cine-yelmo-palafox | https://cinerama.es/cartelera/cine/yelmo-cines-luxury-palafox/ | ["Yelmo Palafox"] | 135 |
| cine-yelmo-plenilunio | https://cinerama.es/cartelera/cine/yelmo-cines-plenilunio/ | ["Yelmo Plenilunio"] | 278 |
| cine-yelmo-la-vaguada | https://cinerama.es/cartelera/cine/la-vaguada/ | ["Yelmo La Vaguada"] | 264 |

## Fuentes pendientes

- `ocine-urban-caleido`: https://ocineurbancaleido.es/ sirve una aplicación JavaScript sin sesiones en HTML inicial; https://guiamadrid.app/cine/ocine-urban-caleido-madrid/ muestra horarios en buscador, pero `Fetcher` no puede comprobar robots.txt por error de certificado TLS. No se ha eludido el error ni configurado un lector.
- `peque-o-cine-estudio`: https://www.pcineestudio.es/ publica eventos y una cabecera semanal, pero no se han identificado en el HTML sesiones de cine estructuradas con título y hora; https://guiamadrid.app/cine/pequeno-cine-estudio-madrid/ falla por el mismo certificado al comprobar robots.txt. Sigue pendiente.

## Palacio de la Prensa: pendiente de API verificable

El recinto oficial es https://palaciodelaprensa.com/, Plaza del Callao, 4. La ruta oficial `/categoria/cine` y la variante `/es/categoria/cine` entregan una aplicación SPA sin sesiones ni JSON-LD en el HTML. La configuración pública `https://apiw5.janto.es/v5/configuration` responde al enviar el encabezado `Origin: https://palaciodelaprensa.com`, pero contiene configuración, no programación. Para descubrir las llamadas de la aplicación se intentó consultar su bundle en `cdn.janto.es`; Fetcher detiene la operación al recibir 403 en la comprobación de robots.txt de ese dominio. No se ha eludido este control. La página oficial mezcla cine con teatro, música y monólogos; no se ha creado un lector ni propuesta de activación sin comprobar el origen de las fechas y la categoría de cada evento.

### Búsqueda alternativa acotada

El 12 de noviembre se consultaron dos URL candidatas: `https://www.publicine.net/cartelera-cine/madrid/cines-palacio-de-la-prensa` devuelve el índice general de Publicine, sin sesiones ni enlace identificable a este cine; `https://cinerama.es/cartelera/cine/palacio-de-la-prensa/` devuelve la cartelera general, sin sesiones de un recinto identificado. La búsqueda dirigida en Publicine tampoco localizó una ficha del Palacio de la Prensa. No se ha activado una fuente alternativa ni creado lector a partir de esos resultados.
