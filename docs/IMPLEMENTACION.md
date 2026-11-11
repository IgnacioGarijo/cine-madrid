# Implementación acordada y estado

## Ampliación y favoritas públicas en v0.4.2

- Adaptadores independientes para Cine Paz, Palacio de Hielo, Verdi Madrid, Cines Princesa, Renoir Plaza de España, Renoir Retiro, Morasol, Capitol, Cineteca, Artistic Metropol y Cine Estudio del CBA. Cada fuente conserva su estado, fechas extremas leídas e incidencias; una caída no descarta las demás.
- Lectura de todos los días publicados por los selectores de Renoir y mk2, paginación y pases explícitos de Cineteca, eventos estructurados de Artistic, pestañas de Capitol y fechas de sesión de Morasol, incluidas sus notas de tarifa.
- Alcance ampliado para incluir IMAX fuera del municipio: Kinépolis Ciudad de la Imagen, Cinesa Parquesur y Heron City Las Rozas. Recintos confirmados; horarios pendientes de conectar por restricciones detectadas en sus fuentes. El filtro IMAX solo acepta sesiones etiquetadas expresamente, no todas las de esos complejos.
- Favoritas muestra únicamente la lista pública compartida y Añadir película. El diálogo de búsqueda se abre a petición. Las solicitudes confirmadas en GitHub por el propietario actualizan la lista mediante Actions; las homónimas requieren confirmar una ficha. Las solicitudes de visitantes no modifican datos.
- TMDB admite la dirección con nombre/apellido invertidos y créditos conjuntos. Si falta dirección, se exige título exacto o alias y año explícito de la película, con candidato único. Los sufijos de ciclos y música en directo se separan para buscar, conservando el título original.
- Las etiquetas de música en directo, coloquio, invitados y maratón se muestran en castellano. No se usa el pie de una web como evidencia de que todos sus pases tengan música en directo.
- La lista privada y la configuración de Telegram siguen separadas de las favoritas públicas; no se han publicado datos de configuración privados ni activado Telegram.

## Integración TMDB en v0.3.0

- Secretos configurados en ambos repositorios; la cartelera usa el secreto del repositorio público exclusivamente dentro de Actions.
- Búsqueda por títulos originales, traducciones y alias automáticos; verificación por dirección, con año/duración como evidencia adicional y control de homónimos.
- Caché persistente de metadatos públicos, errores de API y de identificación diferenciados y conservación de verificaciones anteriores ante fallos temporales.
- Identidad y clasificación por sesión independientes: las fechas de primeras salidas comerciales internacionales permiten reconocer reposiciones; los pases de festivales no bastan. Reglas iniciales configurables de 365 días para reposición automática y 180 días para continuidad del estreno actual, con revisión contextual en la zona intermedia.
- Enlaces a la ficha TMDB y año en la cartelera; alias incorporados a búsqueda y calendario. Favoritas ofrece las fichas identificadas en la cartelera.
- Copilot queda pendiente para ambigüedades e interpretación de eventos, sin bloquear las coincidencias claras de TMDB.

## Cambios de interfaz en v0.2.1

- Diseño orientado a móvil: cabecera con Cine Madrid en grande, filtros secundarios plegables y controles táctiles.
- Solo Cartelera, Favoritas y Boletín en navegación principal. Fuentes e incidencias y cobertura accesibles desde el pie.
- Calendario mensual real en Cartelera, compacto y ampliable. Misma búsqueda y filtros; selección de fechas compartida y navegación entre meses.
- Aplicación web instalable, iconos para Android/iOS y acceso a los últimos datos públicos guardados sin conexión. Instalación en teléfono real pendiente de comprobar con el usuario.
- Cuenta TMDB creada por el usuario; la credencial de API sigue pendiente. El nombre de usuario no sustituye al token.

## Alcance

Madrid capital y complejos IMAX del resto de la región. Todos los cines comerciales y espacios con cine regular como objetivo de cobertura, con actualización diaria, búsqueda uniforme, reposiciones, eventos especiales, ciclos futuros, calendario, pendientes y boletín privado por Telegram con archivo público.

## Entregado en v0.1.1

1. Repositorios público y privado, copias locales en C:\Github.
2. Conector independiente de Cine Paz: fechas reales del selector, Hoy/Mañana, días explícitos, cambio de año y sesiones por su identificador de origen. No se reutilizan los días de mk2 general.
3. Interfaz adaptable al móvil, filtros, listado y agenda por día.
4. iCalendar público y Google Calendar por sesión cuando su duración es conocida.
5. Registro de incidencias público con pendientes y errores separados por gravedad/código; registro privado del bot.
6. Pendientes centrales privadas: Mad Max: Fury Road (2015, George Miller) e Interstellar (2014, Christopher Nolan).
7. Formulario privado de GitHub para gestionar pendientes desde el móvil y bot preparado para búsqueda/selección mediante botones. Nuevas películas requieren configurar TMDB.
8. Ejecución diaria y publicación semanal por plantilla preparadas; envío a Telegram pendiente de configuración.

## Hitos restantes

### A. Cobertura y geografía

- Contrastar inventario: municipio, cierres, duplicados, centros culturales y salas temporales. Eliminar falsos positivos de los directorios.
- Integrar fuentes por dominio, sin confundir la cartelera de mk2 Cine Paz con otros cines mk2.
- Obtener coordenadas verificadas y contratar o elegir un servicio de rutas peatonales antes de publicar minutos y colores por tiempo. Mientras tanto, distancias explícitas en km y coordenadas ausentes reconocidas.
- Validación por cine: fechas futuras, versión, hora, enlace de compra y cancelaciones explícitas. Detectar cambios de estructura y caída de volumen.

### B. Identidad y agente

- TMDB activado para títulos, alias, año, dirección y fechas internacionales; ampliar corroboración con reparto cuando una fuente lo publique.
- Generar candidatos y enviar al agente los casos ambiguos, sin aceptar una semejanza de título como identidad confirmada.
- El agente consulta fichas y contexto; devuelve candidatos, evidencia y decisión estructurada. Guardar equivalencias y correcciones persistentes.
- Definir «reposiciones» por recuperación de películas previamente estrenadas nacional o internacionalmente. Distinguir la continuidad del estreno actual y premières de festivales; no aplicar solo un umbral de antigüedad.
- Detectar eventos con música interpretada en la sala, coloquios, invitados o maratones. No confundir un concierto grabado con música en directo.
- Verificar Copilot Student, autenticación desatendida y consumo real. Límites por ejecución, reutilización de decisiones y cola de pendientes si se agota cuota.
- Por ahora las identidades sin confirmar se ven como pendientes y quedan fuera de las alertas personales.

### C. Experiencia personal

- Credencial TMDB configurada. Activar las credenciales de Telegram cuando el usuario cree su bot.
- Validar mensajes desde el móvil, bloqueo de otros usuarios, botones de selección, persistencia de pendientes y no repetición de avisos normales.
- Sincronización futura entre navegador y lista privada: requiere autenticación y un servicio accesible o una exportación/importación explícita. Nunca poner un token privado en la web pública.
- El bot usa sondeo cada 30 minutos; no garantiza respuesta instantánea. El sondeo permanece desactivado hasta configurar ENABLE_TELEGRAM=true para no consumir cuota sin utilidad. Si se necesita inmediatez, evaluar webhook y alojamiento adicional.
- Los avisos enviados por Telegram tienen entrega al menos una vez: un fallo entre envío y persistencia puede repetir un mensaje. No se garantiza exactamente una entrega ante interrupciones.

### D. Editorial y calendarios

- Completar boletín con eventos especiales y nuevos anuncios futuros, agrupado por película y cine.
- Agente redacta exclusivamente con sesiones verificadas; mantener versión por plantilla si no hay cuota.
- Calendarios por cine/ciclo y cancelaciones explícitas con UID estable. La descarga/importación individual es una copia; las suscripciones dependen del refresco del lector.
- Reintentos de lecturas y alertas de fallo; comprobación periódica de cobertura y actividad de Actions.

## Criterios de aceptación

- No afirmar cobertura completa hasta cerrar el inventario y validar cada fuente.
- La misma obra se reconoce bajo variantes no introducidas por el usuario, con pruebas de La La Land e In the Mood for Love y sus combinaciones; las pruebas actuales solo comprueban alias respaldados y homónimos. Falta probar el agente real.
- Fechas de Cine Paz proceden de su propia cartelera, no de textos de mk2 general.
- Un fallo conserva datos y produce una incidencia; no se traduce en «no hay sesiones».
- Ninguna dirección, token ni lista privada aparece en los archivos públicos. Las favoritas públicas se comparten por decisión expresa del propietario.
- Comprobar de extremo a extremo fuente, identidad, búsqueda, calendario y aviso recibido antes de declarar completa la automatización.
