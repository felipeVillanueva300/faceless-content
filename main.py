"""Pipeline diario: guion -> voz -> subtítulos -> b-roll -> video -> subir -> publicar."""
import os
import sys

from src import script_gen, tts, subtitles, video, uploader, publisher, broll, notify, history, graphics

BUILD = "build"

CARD_DUR = float(os.environ.get("CARD_DUR", "4.5"))
GRAPHIC_DUR = float(os.environ.get("GRAPHIC_DUR", "4.0"))


def _compacto(texto: str) -> str:
    """minúsculas, sin acentos ni espacios/puntuación: 'Cetes Directo' == 'CETESDIRECTO',
    '$24,000' == '24000'. Sirve para encontrar en qué punto de la voz se dice algo."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t)


def _momento_mencion(claves, segmentos, beat=None):
    """Segundo en que la voz dice alguna de 'claves' (card o dato del gráfico).
    segmentos: [(texto, inicio, duración)] de cada bloque de voz.
    1) busca el texto dentro de los bloques y estima el segundo por la posición
       de la palabra en el bloque (la voz es de ritmo casi constante);
    2) si no aparece, usa el 'beat' que mandó Gemini (inicio de ese bloque);
    3) si tampoco, None (el que llama usa la posición fija de antes)."""
    for clave in claves:
        c = _compacto(str(clave))
        if len(c) < 3:
            continue
        for texto, t0, d in segmentos:
            comp = _compacto(texto)
            pos = comp.find(c)
            if pos >= 0 and comp:
                return t0 + d * (pos / len(comp))
    try:
        b = int(beat)
    except (TypeError, ValueError):
        b = 0
    if 1 <= b <= len(segmentos) and len(segmentos) > 1:
        return segmentos[b - 1][1] + 0.3
    return None


def _ventanas(items, dur, minimo=1.5):
    """items: [(inicio, dict)] -> ajusta inicio/fin: sin tapar el hook ni el cierre
    'SÍGUEME', sin encimarse entre sí y con una duración mínima legible."""
    from src.video import HOOK_DUR, OUTRO_DUR
    limite = dur - OUTRO_DUR - 0.1
    out, prev_fin = [], 0.0
    for st, largo, it in sorted(items, key=lambda x: x[0]):
        st = max(st - 0.6, HOOK_DUR + 0.1, prev_fin + 0.05)   # entra un poquito antes de oírse
        en = min(st + largo, limite)
        if en - st < minimo:
            continue
        it["start"], it["end"] = round(st, 2), round(en, 2)
        out.append(it)
        prev_fin = en
    return out


def _write_summary(url, titulo, caption, publicado, errores=None):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    estado = "PUBLICADO" if publicado else "BORRADOR (no publicado)"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"## {estado}\n\n")
            f.write(f"**Título:** {titulo}\n\n")
            f.write(f"**Video:** [ver/descargar]({url})\n\n")
            f.write(f"**Caption:**\n\n> {caption}\n\n")
            if errores:
                f.write("### ⚠️ Errores al publicar (revisa aquí PRIMERO)\n\n")
                for red, det in errores.items():
                    f.write(f"- **{red}**: {det}\n")
                f.write("\n")
    except Exception:
        pass


def _publicar_ig_youtube(url, caption, titulo):
    results, errores = {}, {}

    ig = os.environ.get("IG_USER_ID")
    if ig:
        try:
            results["instagram"] = publisher.publish_instagram(ig, url, caption)
            print("    Instagram OK:", results["instagram"])
        except Exception as e:
            errores["instagram"] = str(e)
            print("    Instagram FALLÓ:", e)

    if os.environ.get("YT_REFRESH_TOKEN"):
        try:
            from src import youtube_upload
            vid = youtube_upload.upload_short_from_url(url, titulo, description=caption)
            results["youtube"] = vid
            print("    YouTube OK:", vid)
        except Exception as e:
            errores["youtube"] = str(e)
            print("    YouTube FALLÓ:", e)

    print("Publicados:", results)
    if errores:
        print("Con errores:", errores)
    return results, errores


def publicar_por_id(publish_id: str):
    repo = os.environ["GITHUB_REPOSITORY"]
    print(f"[Publicar por ID] Buscando video del release: {publish_id}")
    url, caption, titulo = uploader.get_release_info(repo, publish_id)

    override = os.environ.get("PUBLISH_CAPTION", "").strip()
    if override:
        caption = override
    if not titulo:
        titulo = f"(publicación manual de {publish_id})"

    print("    URL:", url)
    print("    Caption:", (caption[:80] + "…") if len(caption) > 80 else caption or "(vacío)")
    print("[Publicar por ID] Publicando en Instagram y YouTube (Facebook es manual)")
    results, errores = _publicar_ig_youtube(url, caption, titulo)
    _write_summary(url, titulo, caption, publicado=bool(results), errores=errores)
    notify.notify_telegram(titulo, caption or "(sin caption)", url, publicado=bool(results))
    algo_configurado = os.environ.get("IG_USER_ID") or os.environ.get("YT_REFRESH_TOKEN")
    if algo_configurado and not results:
        sys.exit(1)


def generar_borrador():
    os.makedirs(BUILD, exist_ok=True)
    niche = os.environ.get("NICHE", "tecnología y finanzas")

    rehacer = os.environ.get("REHACER_ID", "").strip()
    if rehacer:
        print(f"[1/7] Rehaciendo con el guion guardado en: {rehacer}")
        data = uploader.leer_guion(os.environ["GITHUB_REPOSITORY"], rehacer)
    else:
        print(f"[1/7] Generando guion sobre: {niche}")
        recientes = history.load_recent(60)
        if recientes:
            print(f"    ({len(recientes)} temas recientes a evitar)")
        data = script_gen.generate_script(niche, avoid=recientes)
    import json
    with open(os.path.join(BUILD, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    caption = data.get("caption") or data.get("title", "")
    title = data.get("title", "")
    topic = data.get("topic") or title
    hook_card = (data.get("hook_card") or title or "").strip()

    # --- Guion por BLOQUES (beats): sincronía exacta voz <-> fondo ---
    beats = [b for b in (data.get("beats") or [])
             if isinstance(b, dict) and (b.get("narration") or "").strip()]
    seg_on = os.environ.get("SEGMENTED_BG", "1").strip().lower() in ("1", "true", "yes")
    usar_bloques = seg_on and len(beats) >= 2

    audio = os.path.join(BUILD, "audio.mp3")
    ass = os.path.join(BUILD, "subs.ass")
    seg_dur = None
    escenas = []
    dur = 40.0
    segmentos = [] 

    if usar_bloques:
        textos = []
        for i, b in enumerate(beats):
            n = (b.get("narration") or "").strip()
            if i == 0:
                hook_txt = data.get('hook', '').strip()
                if hook_txt and hook_txt[-1] not in ".?!…":
                    hook_txt += "."
                n = f"{hook_txt} {n}".strip()
            textos.append(n)
        escenas = [(b.get("scene") or "").strip() for b in beats]

        print("[2/7] Sintetizando voz (por bloques)")
        audio_seg, seg_dur = tts.synthesize_segments(textos, BUILD)
        if audio_seg and seg_dur:
            audio = audio_seg
            dur = sum(seg_dur)
            print("[3/7] Generando subtítulos (por bloque)")
            subs_seg, t = [], 0.0
            for txt, d in zip(textos, seg_dur):
                subs_seg.append((txt, t, t + d))
                segmentos.append((txt, t, d))
                t += d
            subtitles.build_ass_segments(subs_seg, ass)
        else:
            usar_bloques = False   # síntesis por bloques falló -> camino normal

    if not usar_bloques:
        resto = data.get("script") or " ".join((b.get("narration") or "") for b in beats)
        narration = f"{data['hook']} {resto}".strip()
        print("[2/7] Sintetizando voz")
        boundaries = tts.synthesize(narration, audio)
        try:
            dur = subtitles._audio_duration(audio)
        except Exception:
            dur = 40.0
        print("[3/7] Generando subtítulos")
        subtitles.build_ass(narration, boundaries, ass, audio)
        segmentos = [(narration, 0.0, dur)]

    print("[4/7] Buscando b-roll de fondo")
    # Escenas del fondo: de los beats (si hay), o de broll_scenes/keywords (respaldo).
    if not escenas:
        bs = data.get("broll_scenes") or []
        if isinstance(bs, str):
            bs = [bs]
        escenas = [s.strip() for s in bs if s and s.strip()]
    escenas = [e for e in escenas if e] or [(data.get("broll_keywords") or "personal finance").strip()]
    # Nunca pedir efectivo al banco de video ni a la IA (billetes de otros países).
    escenas = [broll.limpiar_escena(e) for e in escenas]

    from src import ai_image
    modo_ia = os.environ.get("AI_IMAGE_MODE", "off").strip().lower()

    def _clip_stock(esc, i):
        return broll.fetch_broll(esc, os.path.join(BUILD, f"broll_{i}.mp4"))

    def _clip_ia(esc, i):
        if not ai_image.ENABLED:
            return None
        img = ai_image.generate_image(esc, os.path.join(BUILD, f"ia_{i}.png"))
        return video.image_to_clip(img, os.path.join(BUILD, f"ia_{i}.mp4")) if img else None

    clips = []
    if modo_ia == "mix" and ai_image.ENABLED:
        # escena par -> video real primero; impar -> IA primero. Respaldo cruzado.
        for i, esc in enumerate(escenas):
            if i % 2 == 0:
                clip = _clip_stock(esc, i) or _clip_ia(esc, i)
            else:
                clip = _clip_ia(esc, i) or _clip_stock(esc, i)
            if clip:
                clips.append(clip)
    elif modo_ia == "always" and ai_image.ENABLED:
        for i, esc in enumerate(escenas):
            clip = _clip_ia(esc, i) or _clip_stock(esc, i)
            if clip:
                clips.append(clip)
    else:
        clips = broll.fetch_broll_scenes(escenas, BUILD)
        if not clips and modo_ia == "fallback" and ai_image.ENABLED:
            for i, esc in enumerate(escenas):
                clip = _clip_ia(esc, i)
                if clip:
                    clips.append(clip)

    if not clips:   # último recurso: el fetch de un solo clip como antes
        kw = broll.limpiar_escena((data.get("broll_keywords") or "personal finance").strip())
        uno = broll.fetch_broll(kw, os.path.join(BUILD, "broll.mp4"))
        clips = [uno] if uno else []

    print("[5/7] Armando video")
    bg = None
    if len(clips) >= 2:
        durs = seg_dur if (usar_bloques and seg_dur and len(seg_dur) == len(clips)) else None
        bg = video.build_multi_background(clips, dur, os.path.join(BUILD, "bg_combined.mp4"),
                                          durations=durs)
    elif len(clips) == 1:
        bg = clips[0]
    pendientes = []
    for ci, c in enumerate([c for c in (data.get("cards") or []) if isinstance(c, dict)][:2]):
        st = _momento_mencion([c.get("big", "")], segmentos, c.get("beat"))
        if st is None:
            st = dur * (0.25, 0.60)[ci]
        pendientes.append((st, CARD_DUR, {"big": c.get("big", ""), "small": c.get("small", "")}))
    cards = _ventanas(pendientes, dur)
    for c in cards:
        print(f"    card '{c['big']}' de {c['start']}s a {c['end']}s")

    graphic_overlays = []
    pend_g = []
    for gi, g in enumerate([g for g in (data.get("graphics") or []) if isinstance(g, dict)][:2]):
        claves = []
        for k in (g.get("value"), g.get("b_value"), g.get("a_value"), g.get("label", "")):
            if isinstance(k, float) and k.is_integer():
                k = int(k)
            claves.append(k)
        st = _momento_mencion([k for k in claves if k not in (None, "")], segmentos, g.get("beat"))
        if st is None:
            st = dur * (0.28, 0.62)[gi]
        pend_g.append((st, GRAPHIC_DUR, {"spec": g, "gi": gi}))
    for it in _ventanas(pend_g, dur):
        st, en, gi = it["start"], it["end"], it["gi"]
        gdir = os.path.join(BUILD, f"g{gi}")
        pattern, _n, fps = graphics.render_frames(it["spec"], en - st, gdir)
        graphic_overlays.append({"pattern": pattern, "start": st, "end": en, "fps": fps})
        print(f"    gráfico {gi + 1} de {st}s a {en}s")

    if graphic_overlays:
        cards = []

    out = os.path.join(BUILD, "reel.mp4")
    video.build_video(audio, ass, out, bg_video=bg, cards=cards,
                      graphics=graphic_overlays, duration=dur, hook=hook_card)

    print("[6/7] Subiendo video a URL pública")
    url, tag = uploader.upload_public(out, caption=caption, title=title)
    print("    URL:", url)
    print("    ID :", tag)
    uploader.adjuntar(os.environ["GITHUB_REPOSITORY"], tag, os.path.join(BUILD, "script.json"))

    if not rehacer:
        history.add(topic, categoria=data.get("categoria"), formato=data.get("formato"))

    publicar = os.environ.get("PUBLISH", "false").strip().lower() not in ("false", "0", "no")

    if data.get("publicar_borrador"):
        # Golpe de 'reacción' post-fecha: nunca se autopublica; requiere tu OK.
        if publicar:
            print("    Día de 'reacción' post-fecha: se fuerza BORRADOR (revisión humana).")
        publicar = False

    if not publicar:
        print("=" * 60)
        print("MODO BORRADOR (no se publicó).")
        print("ID para publicar:", tag)
        print("Video:", url)
        print("=" * 60)
        _write_summary(url, title, caption, publicado=False)
        notify.notify_telegram(title, caption, url,
                               publicado=False, publish_id=tag)
        return

    print("[7/7] Publicando (cron directo)")
    results, errores = _publicar_ig_youtube(url, caption, title)
    _write_summary(url, title, caption, publicado=bool(results), errores=errores)
    notify.notify_telegram(title, caption, url, publicado=bool(results))
    if (os.environ.get("IG_USER_ID") or os.environ.get("YT_REFRESH_TOKEN")) and not results:
        sys.exit(1)


def main():
    publish_id = os.environ.get("PUBLISH_ID", "").strip()
    if publish_id:
        publicar_por_id(publish_id)
    else:
        generar_borrador()


if __name__ == "__main__":
    main()