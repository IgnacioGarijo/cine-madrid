# Cobertura de cines independientes

Comprobación efectuada el 12 de noviembre de 2026. El lector `publicine_embajadores` utiliza `Reader.soup` y, por tanto, `Fetcher`, incluida la comprobación de robots.txt. La fuente de horarios es Publicine, no la página oficial. El año se infiere de la fecha de ejecución para fechas sin año mediante `parse_day` (incluido cambio de año); no se expande ningún intervalo como si fueran sesiones. Se conserva el enlace de Publicine a la ficha como `source_url` y su enlace de venta como `booking_url`. VOSE se registra cuando la fuente lo indica; DIGITAL no significa doblada. Dirección y duración proceden de Publicine. El lector verifica nombre y dirección antes de aceptar sesiones, y rechaza una sede equivocada.

| ID existente | Adapter propuesto | schedule_url | Dirección verificada |
|---|---|---|---|
| `cines-embajadores` | `publicine_embajadores` | `https://www.publicine.net/cartelera-cine/madrid/cines-embajadores` | Glorieta Santa María de la Cabeza, 5 |
| `cines-embajadores-r-o` | `publicine_embajadores` | `https://www.publicine.net/cartelera-cine/madrid/cines-embajadores-rio` | Calle Ercilla, 53 |

Para integrar: importar la función en `src/adapters.py`, añadirla al registro de `read_cinema` conforme a la estructura existente, y añadir a cada configuración `adapter: publicine_embajadores` y el `schedule_url` de la tabla. Mantener la URL oficial en `url`; marcar el estado solo tras validar integración. No se han modificado los archivos compartidos. Publicine cubría únicamente del 12 al 18 de noviembre en la lectura; no se garantiza cobertura de venta anticipada fuera de ese periodo. Las etiquetas especiales solo se aplican ante señales explícitas en el título, y no se pretende que detecten todos los eventos especiales.

Evidencia de ejecución real con `Reader` y `Fetcher`, fecha de referencia 2026-11-12:

- Embajadores: 51 sesiones, 10 películas, 12/11 16:00 a 18/11 22:30. Ejemplo: *El gato con sombrero*, 12/11 a las 16:00.
- Embajadores Río: 35 sesiones, 10 películas, 12/11 17:25 a 18/11 22:30. Ejemplo: *Bahía de sangre*, 15/11 a las 12:00, y *El hombre elefante*, 12/11 a las 22:15.
- La URL oficial de Embajadores falló al comprobar `robots.txt` por `SSLCertVerificationError`, tanto en el dominio sin `www` como con él; no se desactivó la verificación TLS.

## Sala Equis: pendiente

No se propone activar adaptador para `sala-equis`. La [taquilla oficial](https://salaequis.es/taquilla/) enlaza fichas, pero no publica horarios en el HTML leído. Por ejemplo, la ficha oficial de [La bola negra](https://salaequis.es/ciclos/la-bola-negra/) enlaza a Kinetike: su respuesta GET mostraba el 13, 15, 24, 26 y 29 de noviembre de 2026, pero solo botones «SESIONES», sin horas. No cabe construir pases con esas fechas solas. Además se probó la ruta pública de Publicine para Sala Equis y devolvió el índice general de cines, no una ficha de la sala. Una prueba adicional mostró una vía viable: robots permite el endpoint Kinetike; un POST a la misma URL con los campos ocultos del formulario y `01=SESIONES` devuelve el panel de la fecha 13/11 con hora 19:15. Se trata de seleccionar una fecha, sin seleccionar ni comprar entradas. La integración queda pendiente porque `Fetcher` solo expone GET y debe ampliarse para permitir esta consulta POST con robots, cookies, límites y timeouts. No se generaron sesiones inventadas.

Pruebas: `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_independent.py -v` (3 superadas). Fixtures recortadas de respuestas públicas, sin información personal.
