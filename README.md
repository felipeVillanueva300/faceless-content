# Contenido automático (FB + IG) — proyecto personal

Pipeline que cada día: genera un guion con Gemini → le pone voz (edge-tts) →
crea subtítulos sincronizados → arma un video vertical con FFmpeg → lo sube a una
URL pública → lo publica en tu Página de Facebook y tu Instagram. Corre solo con
**GitHub Actions** (cron diario). Costo: ~$0.

---

## ⚠️ Importante: mantenlo separado de tu empresa

Todo este proyecto debe nacer de identidad **personal**:

- Repo bajo tu **cuenta personal de GitHub** (no la de la empresa).
- API key de Gemini con un **Google account personal** (no tu correo de trabajo).
- Una **cuenta de Facebook** propia del proyecto (puede ser nueva).

No se usa GCP ni nada de la organización de tu empresa.

---

## Parte 1 — Cuentas (esto toma más tiempo que el código)

Hazlo en este orden:

1. **Página de Facebook.** Desde tu cuenta de FB del proyecto, crea una *Página*
   (no un perfil).
2. **Instagram profesional.** Convierte tu cuenta de IG a **Business** y
   **vincúlala a esa Página de Facebook** (Configuración de IG → Cuenta →
   Compartir en otras apps / vincular página). Sin esto, la API de publicación no
   funciona.
3. **App en Meta for Developers** (https://developers.facebook.com):
   - Crea una app tipo *Business*.
   - Agrega el producto **Instagram** (Graph API / Content Publishing).
   - Como publicas en **tus propias cuentas**, trabaja en **modo desarrollo** y
     agrégate como **Instagram Tester**. Así **no necesitas App Review**
     (el review de 2–4 semanas solo aplica si terceros conectan sus cuentas).
4. **Token de larga duración.** Genera un **System User token** en Meta Business
   Suite con estos permisos:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`, `pages_manage_posts`.
   Los tokens duran ~60 días; el de System User es el más estable.
5. **Obtén los IDs que necesitarás:**
   - `IG_USER_ID`: `GET /{page-id}?fields=instagram_business_account`
   - `FB_PAGE_ID`: es el ID de tu Página.

## Parte 2 — API de Gemini

1. Entra a Google AI Studio con tu Google **personal** y crea una **API key**.
2. Guárdala; irá en el secret `GEMINI_API_KEY`.

## Parte 3 — Subir el repo y configurar los Secrets

1. Crea un repo en tu GitHub. **Debe ser PÚBLICO** (así la URL del video en el
   Release es descargable por Meta). Si quieres repo privado, mira "Repo privado"
   más abajo.
2. Sube estos archivos.
3. En el repo → **Settings → Secrets and variables → Actions → New repository
   secret**, crea:
   - `GEMINI_API_KEY`
   - `META_ACCESS_TOKEN`
   - `IG_USER_ID`
   - `FB_PAGE_ID`

   (`GITHUB_TOKEN` se inyecta solo, no lo crees.)

## Parte 4 — Probar

- Ve a la pestaña **Actions** → *Publicar Reel diario* → **Run workflow**
  (esto es el `workflow_dispatch`, corre a mano sin esperar al cron).
- Revisa los logs. Si todo va bien, verás el Reel en tu IG y el video en tu Página.
- El cron ya está puesto a las **15:00 UTC (~9:00 CDMX)**. Cámbialo en
  `.github/workflows/publish.yml`.

---

## Probar en tu máquina (opcional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo apt-get install -y ffmpeg fonts-dejavu-core   # o brew install ffmpeg
cp .env.example .env    # llena los valores
export $(grep -v '^#' .env | xargs)
python main.py
```

---

## Ajustes rápidos

- **Nicho / voz:** variables `NICHE` y `TTS_VOICE` en el workflow.
  Voces MX: `es-MX-JorgeNeural`, `es-MX-DaliaNeural`.
- **Fondo con video en loop:** pon un `assets/fondo.mp4` y define `BG_VIDEO`.
- **Solo IG o solo FB:** deja vacío el secret que no quieras usar.
- **Frecuencia:** edita el `cron`.

## Repo privado (alternativa a Release público)

Si no quieres el repo público, cambia `src/uploader.py` para subir el mp4 a un
bucket público (Cloudflare R2 tiene free tier y es S3-compatible) y devolver esa
URL. El resto del pipeline no cambia.

## Notas honestas

- La **versión de Graph API** (`v23.0`) cambia cada trimestre; si un endpoint
  falla, sube el número en `GRAPH_VERSION`.
- `src/publisher.py` publica en FB como **video normal** (robusto). Para el flujo
  específico de *Reels* de Facebook (endpoint `video_reels`, 3 pasos) se puede
  migrar después.
- La **monetización directa** de Reels en Meta es lenta e inconsistente. El
  ingreso real, al principio, viene de afiliados o de llevar tráfico a algo tuyo.
  El contenido es el anzuelo.
