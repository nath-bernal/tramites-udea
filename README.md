# Trámite Claro

Prototipo académico de una plataforma web para radicar, rastrear y resolver en línea los trámites académicos del pregrado de la Universidad de Antioquia (UdeA), con certificados bilingües español–inglés.

Proyecto de curso de Ingeniería de Sistemas (grupo de 3 estudiantes). Nace de un diagrama de Ishikawa sobre el problema: **trámites académicos lentos, con mucho papeleo y documentos oficiales solo en español**.

> Es un **prototipo académico**, no un sistema oficial de la UdeA. No usar logos, sellos ni marcas oficiales de la universidad. Todo documento generado lleva la marca de agua "PROTOTIPO ACADÉMICO – SIN VALIDEZ OFICIAL". Solo se usan datos ficticios.

---

## 1. Problema que resuelve

Hoy los trámites de homologación, cancelación, certificados y reingreso:
- dependen de formularios en papel o PDF y firmas físicas;
- pasan por varias dependencias con aprobaciones manuales en cadena;
- no se pueden rastrear: el estudiante no sabe en qué dependencia está su solicitud ni cuánto falta;
- tienen requisitos poco claros, por lo que llegan documentos incompletos y se devuelven;
- generan documentos solo en español, y el estudiante paga una traducción oficial cuando los necesita en inglés (intercambio, doble titulación, becas, empleo en el exterior).

### Relación entre causas (Ishikawa) y funcionalidades

| Causa del diagrama | Funcionalidad que la ataca |
|---|---|
| Formularios en papel o PDF | Radicación 100 % en línea |
| Requisitos poco claros / documentos incompletos | Lista de requisitos por trámite y validación antes de enviar |
| Sin seguimiento del trámite en línea | Línea de tiempo del estado de cada solicitud |
| Sin avisos de cambio de estado | Notificaciones en la app y por correo |
| Aprobaciones manuales en cadena | Flujo de etapas configurable por tipo de trámite |
| Sin firma electrónica | Certificado digital con código de verificación y QR |
| Certificados solo en español / se exige traducción | Generación de certificados en español e inglés desde plantillas |
| Sin tiempos máximos de respuesta | Plazo (SLA) por etapa y alertas de vencimiento |
| Indicadores poco visibles | Tablero de tiempos promedio por trámite y por etapa |
| Información dispersa | Catálogo único de trámites con guía paso a paso |

---

## 2. Usuarios y roles

- **Estudiante**: consulta el catálogo, radica solicitudes, sube documentos, sigue su estado, corrige lo que le pidan, descarga certificados (ES / EN).
- **Funcionario**: pertenece a una dependencia (p. ej., Coordinación de programa, Comité de carrera, Admisiones y Registro). Ve la bandeja de solicitudes de su etapa, aprueba, rechaza o pide ajustes con comentario.
- **Administrador**: gestiona tipos de trámite, etapas, plazos, dependencias, usuarios y plantillas de certificados. Ve el tablero de indicadores.

En el prototipo el inicio de sesión es con usuario y contraseña locales. No se integra con el sistema de autenticación real de la universidad.

---

## 3. Trámites del alcance

Alcance: pregrado, sede Medellín, cuatro tipos de trámite. Los flujos de abajo son **supuestos del equipo** para el prototipo y deben quedar configurables desde el administrador, no fijos en el código.

| Trámite | Etapas supuestas | Documentos de ejemplo |
|---|---|---|
| Homologación | Coordinación de programa → Comité de carrera → Admisiones y Registro | Certificado de notas de origen, contenidos de los cursos |
| Cancelación de curso o semestre | Coordinación de programa → Admisiones y Registro | Justificación, soporte (opcional) |
| Certificado (estudios, notas, contenidos) | Admisiones y Registro | Ninguno; se elige idioma ES, EN o ambos |
| Reingreso | Coordinación de programa → Comité de carrera → Admisiones y Registro | Carta de motivos, historia académica |

### Estados de una solicitud

`BORRADOR → RADICADA → EN_REVISION → (REQUIERE_AJUSTES ↺) → APROBADA | RECHAZADA → FINALIZADA`

- `REQUIERE_AJUSTES` devuelve la solicitud al estudiante; al corregir vuelve a `EN_REVISION` en la misma etapa.
- Cada cambio de estado o de etapa se guarda en un historial (quién, cuándo, comentario). Ese historial alimenta la línea de tiempo y los indicadores.
- Cada solicitud tiene un número de radicado legible, por ejemplo `TC-2026-000123`.

---

## 4. Funcionalidades

### MVP (prioridad)
1. Registro e inicio de sesión con roles.
2. Catálogo de trámites con requisitos, documentos y tiempo estimado.
3. Radicación en línea con carga de archivos (PDF, JPG, PNG; máx. 5 MB c/u) y validación de requisitos.
4. Página de seguimiento con línea de tiempo: etapa actual, dependencia, días transcurridos y comentarios.
5. Bandeja del funcionario filtrada por su dependencia, con acciones aprobar / rechazar / pedir ajustes.
6. Notificaciones en la app y por correo (en desarrollo, el correo sale por consola).
7. Generación de certificado en PDF en español y en inglés, con código de verificación, QR y marca de agua de prototipo.
8. Página pública de verificación: con el código o el QR muestra si el certificado existe y sus datos básicos.

### Después del MVP
9. Plazos por etapa y alertas de solicitudes vencidas o por vencer.
10. Tablero de indicadores: solicitudes por estado, tiempo promedio por tipo de trámite y por etapa, cuellos de botella.
11. Interfaz completa en inglés (selector de idioma).
12. Exportar indicadores a CSV.

---

## 5. Stack técnico

- **Python 3.12** y **Django 5.2 (LTS)**.
- Plantillas de Django + **HTMX** para interacciones sin recargar + **Tailwind CSS** por CDN (es un prototipo).
- **SQLite** en desarrollo; **PostgreSQL** si se despliega.
- PDF: **WeasyPrint** (plantillas HTML → PDF). QR: **qrcode**.
- Internacionalización: sistema i18n de Django (`gettext`), idiomas `es` (por defecto) y `en`.
- Pruebas: **pytest** + **pytest-django**. Estilo: **ruff** (lint y formato).
- Panel de Django (`/admin`) para que el administrador configure trámites, etapas y plantillas.

Si el equipo decide otro stack, actualizar esta sección antes de generar código.

---

## 6. Estructura del proyecto

```
tramite-claro/
├── CLAUDE.md
├── README.md
├── pyproject.toml          # dependencias y configuración de ruff/pytest
├── manage.py
├── config/                 # settings, urls, wsgi
├── apps/
│   ├── accounts/           # usuarios, roles, dependencias
│   ├── catalog/            # tipos de trámite, requisitos, etapas
│   ├── requests/           # solicitudes, documentos, historial, flujo de estados
│   ├── notifications/      # notificaciones en app y correo
│   ├── certificates/       # plantillas, generación PDF ES/EN, verificación
│   └── metrics/            # tablero de indicadores
├── templates/
├── static/
├── locale/                 # traducciones es / en
└── tests/
```

---

## 7. Modelo de datos (borrador)

- `Department`: nombre (Coordinación de programa, Comité de carrera, Admisiones y Registro…).
- `User` (personalizado): rol (`student`, `staff`, `admin`), documento, programa, `department` (solo funcionarios).
- `ProcedureType`: nombre ES/EN, descripción, requisitos, tiempo estimado, activo.
- `ProcedureStage`: tipo de trámite, orden, dependencia, plazo en días hábiles.
- `RequiredDocument`: tipo de trámite, nombre, obligatorio, formatos permitidos.
- `Request`: radicado, estudiante, tipo, estado, etapa actual, datos del formulario (JSON), fechas.
- `RequestDocument`: solicitud, documento requerido, archivo, fecha de carga.
- `RequestEvent`: solicitud, estado anterior/nuevo, etapa, actor, comentario, fecha. **Es la fuente de la línea de tiempo y de los indicadores.**
- `Notification`: usuario, solicitud, mensaje, leída.
- `CertificateTemplate`: tipo de certificado, idioma (`es`/`en`), HTML de la plantilla.
- `IssuedCertificate`: solicitud, idioma, código de verificación (único, no adivinable), archivo PDF, fecha.

---

## 8. Convenciones

- **Código** (modelos, funciones, variables, URLs) en **inglés**. **Interfaz, comentarios de negocio, documentación y mensajes de commit** en **español**.
- Todo texto visible al usuario pasa por `gettext` / `{% translate %}` para poder traducirlo.
- La lógica de cambio de estado vive en un único servicio (`apps/requests/services.py`), nunca en las vistas. Cada transición valida que sea permitida y crea su `RequestEvent`.
- Permisos: un estudiante solo ve sus solicitudes; un funcionario solo las de su dependencia en su etapa actual. Probar esto siempre.
- Archivos subidos fuera de `static/`, con nombre aleatorio; validar tipo y tamaño.
- Fechas en zona horaria `America/Bogota`.
- Commits pequeños con mensajes en español en modo imperativo ("Agrega bandeja del funcionario").

### Datos y privacidad
- Solo datos ficticios en fixtures y semillas (`python manage.py seed_demo`). Nunca datos reales de estudiantes.
- Tener en cuenta la Ley 1581 de 2012 (protección de datos personales en Colombia) si algún día se usan datos reales.

---

## 9. Comandos

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py seed_demo          # crea dependencias, trámites, etapas y usuarios de prueba
python manage.py runserver
pytest                              # pruebas
ruff check . && ruff format .       # lint y formato
python manage.py makemessages -l en && python manage.py compilemessages
```

Usuarios de prueba que crea `seed_demo` (contraseña `demo1234`): `estudiante1`, `funcionario_coordinacion`, `funcionario_comite`, `funcionario_registro`, `admin`.

---

## 10. Plan de trabajo por fases

1. **Base**: proyecto Django, usuario personalizado con roles, dependencias, `seed_demo`, plantilla base con navegación por rol.
2. **Catálogo y radicación**: tipos de trámite, requisitos, formulario de radicación con carga de archivos.
3. **Flujo y seguimiento**: servicio de transiciones, bandeja del funcionario, línea de tiempo, historial.
4. **Notificaciones**: en app y por correo en cada cambio de estado.
5. **Certificados bilingües**: plantillas ES/EN, PDF con QR y marca de agua, página de verificación.
6. **Indicadores y plazos**: tablero, alertas de vencimiento, exportar CSV.
7. **Pulido**: interfaz en inglés, accesibilidad, README con capturas para la exposición.

Trabajar una fase a la vez. Al terminar cada fase: pruebas pasando, `ruff` limpio y una nota breve en el README de lo que quedó.

## 11. Definición de terminado

- La funcionalidad se puede usar de punta a punta con los usuarios de `seed_demo`.
- Tiene pruebas de la lógica principal y de permisos.
- Los textos de la interfaz están marcados para traducción.
- No rompe fases anteriores (`pytest` en verde).

---

## 12. Estado del proyecto

Las 7 fases del plan están implementadas. `pytest` pasa (63 pruebas) y `ruff` está limpio.

| Fase | Qué quedó |
|---|---|
| 1. Base | Usuario personalizado con roles (`student`, `staff`, `admin`), dependencias, registro abierto solo para estudiantes, navegación por rol, `seed_demo` idempotente. |
| 2. Catálogo y radicación | Catálogo con búsqueda (HTMX) y ficha paso a paso. Formulario dinámico según los campos y documentos configurados en `/admin`. Se puede guardar como borrador. Los archivos se validan por extensión, tamaño (5 MB) y contenido real, y se guardan con nombre aleatorio. |
| 3. Flujo y seguimiento | `apps/requests/services.py` concentra todas las transiciones y crea un `RequestEvent` en cada una. Bandeja del funcionario filtrada por dependencia y etapa. Línea de tiempo con indicador de etapas y radicado `TC-AAAA-NNNNNN`. |
| 4. Notificaciones | En la app (con contador que se actualiza cada 30 s) y por correo (en consola durante el desarrollo), en el idioma preferido de quien las recibe. |
| 5. Certificados bilingües | Plantillas ES/EN editables en `/admin`. PDF con WeasyPrint, código no adivinable, QR y marca de agua. Página pública `/certificados/verificar/`. |
| 6. Indicadores y plazos | Tablero con solicitudes por estado, tiempo promedio por trámite y por etapa, cuellos de botella y alertas, más exportación a CSV. Los plazos se cuentan en días hábiles. `python manage.py check_deadlines` avisa a las dependencias de las solicitudes vencidas (pensado para ejecutarse una vez al día). |
| 7. Pulido | La interfaz es en español siempre, sin importar el idioma del navegador. Traducción completa al inglés disponible solo desde el selector ES/EN (se guarda como preferencia del usuario), enlace "saltar al contenido", etiquetas accesibles y regiones `aria-live`. Faltan las capturas para la exposición. |

### Decisiones del equipo de desarrollo
- `APROBADA` y `RECHAZADA` pasan automáticamente a `FINALIZADA` en la misma operación. Si el trámite emite certificado, este se genera antes de finalizar. Si la generación falla, se revierte toda la aprobación. El resultado queda en `Request.outcome`.
- Los estados se guardan en inglés (`DRAFT`, `SUBMITTED`, `IN_REVIEW`, `NEEDS_CHANGES`, `APPROVED`, `REJECTED`, `FINALIZED`). En la interfaz se muestran en español o en inglés.
- Mientras una solicitud está en `REQUIERE_AJUSTES` no aparece en ninguna bandeja. Ese tiempo no cuenta para el plazo de la etapa ni para los indicadores por etapa.
- El administrador ve todas las solicitudes en modo de solo lectura. Solo los funcionarios de la dependencia de la etapa actual pueden decidir.
- Además de los campos del borrador del modelo de datos se agregó `ProcedureField`, para que los campos del formulario de cada trámite sean configurables.
- Los días hábiles no descuentan los festivos colombianos (simplificación del prototipo).
- Como el prototipo no se conecta a un sistema académico, los certificados de notas y de contenidos usan una historia académica simulada (`apps/certificates/academic.py`). Son materias ficticias con créditos, notas y contenidos en español e inglés. Cada estudiante recibe siempre la misma historia, y el PDF indica que es ficticia. Las plantillas por defecto están en `apps/certificates/defaults.py`.
- `seed_demo` crea además `estudiante2` y `estudiante3` (misma contraseña) y 7 solicitudes de ejemplo en distintos estados, con fechas pasadas para alimentar los indicadores. El certificado de `estudiante1` queda pendiente en Admisiones y Registro, para aprobarlo en vivo con `funcionario_registro`.

### Notas de instalación en macOS
- WeasyPrint necesita Pango: `brew install pango`. Si se usa el Python de python.org, hay que exportar `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` antes de `runserver`. Sin Pango la app funciona, pero no puede emitir certificados: la aprobación se revierte y se muestra un mensaje. Las pruebas reemplazan el PDF por uno falso, salvo una prueba de integración que se omite si falta Pango.
- Si el repositorio está en una carpeta sincronizada con iCloud (por ejemplo `~/Documents`), hay que crear el entorno virtual fuera de ella (`python -m venv ~/.venvs/tramite-claro`). Si no, la importación de paquetes se vuelve extremadamente lenta.

---

## 13. Despliegue en Render (gratis)

Servicio web gratuito de Render (Docker) más PostgreSQL gratuito de Neon. Los archivos subidos y los certificados se guardan en la base de datos (`apps/dbfiles`), porque el disco de Render se borra en cada reinicio.

Archivos que intervienen: `Dockerfile`, `render.yaml`, `bin/start.sh` (migraciones, `seed_demo` y Gunicorn) y `requirements.txt`.

1. **Base de datos en Neon**: crear una cuenta en https://neon.tech, crear un proyecto (región cercana, p. ej. AWS us-east) y copiar la *connection string* (`postgresql://…?sslmode=require`).
2. **Servicio en Render**: crear una cuenta en https://render.com con GitHub. Luego **New → Blueprint**, elegir el repositorio `tramites-udea` y Render leerá `render.yaml`.
3. **Variables** que pide el blueprint:
   - `DATABASE_URL`: la connection string de Neon.
   - `DEMO_ADMIN_PASSWORD`: contraseña del usuario `admin` (no usar `demo1234`; la app es pública).
   - `DJANGO_SECRET_KEY` la genera Render automáticamente.
4. **Deploy**. Al terminar, la app queda en `https://tramite-claro-XXXX.onrender.com` con los datos de demo cargados.

Notas:
- Plan gratis: el servicio se duerme tras 15 minutos sin visitas y tarda alrededor de 1 minuto en despertar. Abrir la URL un rato antes de la exposición.
- Cada push a `main` vuelve a desplegar (`autoDeploy`).
- Los correos salen por consola: se ven en **Logs** de Render. Las notificaciones en la app sí funcionan.
- Probar la imagen localmente: `docker build -t tramite-claro .` y luego `docker run -p 8000:8000 -e DJANGO_SECRET_KEY=x -e DJANGO_ALLOWED_HOSTS=localhost -e DATABASE_URL=postgres://… tramite-claro`.
