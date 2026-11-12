# Cobertura cultural: propuesta de integración

Los adaptadores están en `src/adapters_cultural.py` y usan `Reader`/`Fetcher`, con comprobación de robots. Los resultados vacíos solo deben aceptarse con `result.empty_confirmed`; el reconocimiento conservador puede dejar un vacío sin confirmar, por ejemplo si hay fichas ambiguas. Fechas y horas se leen de sesiones individuales; nunca se expanden rangos de ciclos.

| id propuesto | adapter | url | nombre y dirección | estado sugerido |
|---|---|---|---|---|
| cine-dore | filmoteca | https://entradasfilmoteca.sacatuentrada.es/es | Cine Doré - Filmoteca Española; Calle de Santa Isabel, 3 | active |
| casa-america | casa_america | https://www.casamerica.es/cine | Casa de América; Plaza de Cibeles, s/n | active |
| instituto-frances | instituto_frances | https://www.institutfrancais.es/madrid/eventos/ | Instituto Francés de Madrid; Calle del Marqués de la Ensenada, 12 | active |
| academia-cine | academia_cine | https://entradas.apps.academiadecine.com/actividades | Academia de Cine; Calle de Zurbano, 3 | active |

Campos adicionales propuestos para todos: `municipality: Madrid`, `inventory_status: verified_source`, `provenance: url`; coordenadas pendientes de verificación por el integrador. Para Doré, provenance institucional: https://www.cultura.gob.es/cultura/areas/cine/mc/fe/programacion-actividades/proyecciones.html, que enlaza a «Sesiones».

Comprobación en vivo el 12-11-2026:

- Doré: 6 páginas, 39 pases; Fin de jornada (1939), 13-11 17:30, sala 1. El filtro exige año y director; omite programas de cortos y películas sin esos campos.
- Casa de América: 13 páginas, 3 pases: Las Poquianchis 12-11 18:00, El tres de copas 18-11 18:00 y Chicogrande 25-11 18:00. Exige ficha con proyección, sinopsis, fecha y hora explícitas y sede Casa de América; otras variantes pueden omitirse.
- Instituto Francés: 4 páginas, 2 pases: Les chansons d’amour 13-11 20:00 y Les matins merveilleux 16-11 20:00. Exige título de proyección entre comillas y sede Instituto Francés; omite cortometrajes, ciclos, títulos con otra redacción y otras sedes.
- Academia: 5 páginas, 3 pases: Siempre soy tu animal materno 12-11 16:00, 20 años de... El laberinto del fauno 12-11 19:00 y Neurótica anónima 13-11 16:00. La tabla de ficha cinematográfica con duración, nacionalidad y sinopsis distingue películas del podcast publicado en la misma agenda. Títulos como el aniversario se conservan como los publica la fuente.

Las agendas pueden limitar lo publicado y no se garantiza exhaustividad. Fallos de lectura de fichas producen incidencias y no confirman un vacío.

## Fundación Japón, Madrid: pendiente

La portada oficial https://md.jpf.go.jp/es/ publica actividades en línea y en otras ciudades. El ciclo actual de cine japonés https://md.jpf.go.jp/es/Actividades/Arte-y-Cultura/evento/558/ciclo-de-cine-keisuke-kinoshita-una-mirada-desde-la-emocion identifica Cine Doré como sede madrileña y ya queda cubierto por su adaptador; no debe asociarse a una sala de Fundación Japón ni duplicarse. Se revisaron además búsquedas de proyecciones en Palacio de Cañete y otras actividades, que llevan a otros recintos; no se ha encontrado una agenda estructurada fiable de pases en su sede. Por ello no se propone activar un adaptador ni confirmar vacío, y es posible que existan otras sesiones no localizadas.

## Auditoría adicional de recintos culturales (12-11-2026)

En la revisión del inventario de 37 registros disponible al comenzar esta auditoría no figuraban las siguientes sedes; las altas en curso de otros colaboradores pueden haber modificado ya el inventario.

- **Museo Reina Sofía, Cine del Edificio Sabatini**, Calle de Santa Isabel 52. La fuente oficial https://www.museoreinasofia.es/cine-nuevos-medios/ confirma programación estable y ofrece fichas con agenda. Existe el lector `reina_sofia`, con id propuesto `museo-reina-sofia`, url la anterior, `status: active`, `inventory_status: verified_source`, `municipality: Madrid` y coordenadas pendientes. Verificación real: 11 páginas y 4 sesiones individuales: Sean eternxs, 13-11 19:00; Los delincuentes, 14-11 18:00; Algo viejo, algo nuevo, algo prestado, 10-12 19:00; Las mil y una, 11-12 19:00. Los programas múltiples sin hora separada quedan fuera y generan incidencia. No se asignan como películas actos de inauguración ni una hora de intervalo a cada obra. Programación de actividades no equivalentes a fichas de películas, y sedes distintas del Cine Sabatini, quedan fuera.
- **Instituto Italiano de Cultura de Madrid**: el https://iicmadrid.esteri.it/es/gli_eventi/calendario/ mezcla tipos de actividades. El archivo oficial https://iicmadrid.esteri.it/es/gli_eventi/archivio-eventi/ confirma una proyección presencial de Pinocchio el 19-10-2026 a las 20:00. La agenda no presenta ahora una ficha cinematográfica futura inequívoca en su sede para verificar un lector reutilizable. Candidato, no alta automática.
- **Casa Asia**: https://www.casaasia.es/actividad/programa-de-cine-nuevas-miradas-del-cine-asiatico-2026/ sitúa su ciclo de Madrid en Cine Paz; es organizador, no otra sede, y no debe duplicarse allí. Otro acceso ensayado a `/actividad/` devolvió 404. No se ha comprobado un cine propio para registrar.
- **Fundación Casa de México en España**: lector `casa_mexico`, id propuesto `casa-mexico`, nombre Fundación Casa de México en España, dirección Calle de Alberto Aguilera, 20, Madrid; url y provenance https://www.casademexico.es/cine-en-casa-de-mexico/; status active, inventory_status verified_source; coordenadas pendientes. La lectura comprueba sede, fechas de ciclo y líneas individuales de película, día y hora; conserva fechas múltiples separadas y no expande rangos. En vivo 12-11-2026: 9 pases, entre ellos No dejes a los niños solos 13-11 19:00 y Estela 19 y 28-11 a las 19:00. Los ciclos con texto libre no desglosable (MEXES) generan incidencia y pueden omitirse pases; no es cobertura exhaustiva.
- **Fundación Juan March**: https://www2.march.es/invitaciones/?sede=madrid confirma Cine en la March y El pan nuestro de cada día con presentación; candidato para examinar la hora concreta de la película frente a la del acto, antes de alta.
- **Goethe-Institut Madrid**: https://www.goethe.de/ins/es/es/sta/mad.html y https://www.goethe.de/ins/es/es/sta/mad/ueb/prs.html acreditan actividad y muestras de cine; candidato para estudiar programación y diferenciar eventos en su sede de colaboraciones externas.
- **Museo Arqueológico Nacional**: https://www.man.es/man/actividades/cine-enel-museo/ciclo-cine-museo-presentacion-2026.html y la ficha https://www.man.es/man/actividades/cine-enel-museo/20261120-misterio-cometas.html dan título y acto el 20-11 a las 18:00. El ciclo anuncia coloquio previo, por lo que esa hora no acredita el inicio del documental. Candidato sin lector hasta disponer de hora inequívoca.

Otros centros culturales municipales que exhiben ocasionalmente películas quedan como candidatos para una auditoría posterior; no se ha intentado un inventario exhaustivo de sus actos.
