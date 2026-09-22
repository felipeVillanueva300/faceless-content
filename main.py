"""Pipeline diario: guion -> voz -> subtítulos -> b-roll -> video -> subir -> publicar."""
import os
import sys

from src import script_gen, tts, subtitles, video, uploader, publisher, broll, notify, history, graphics

BUILD = "build"


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

    print(f"[1/7] Generando guion sobre: {niche}")
    recientes = history.load_recent(60)
    if recientes:
        print(f"    ({len(recientes)} temas recientes a evitar)")
    data = script_gen.generate_script(niche, avoid=recientes)
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

    if usar_bloques:
        textos = []
        for i, b in enumerate(beats):
            n = (b.get("narration") or "").strip()
            if i == 0:
                n = f"{data.get('hook', '').strip()} {n}".strip()
            textos.append(n)
        escenas = [(b.get("scene") or "").strip() for b in beats]

        print("[2/7] Sintetizando voz (por bloques)")
        audio_seg, seg_dur = tts.synthesize_segments(textos, BUILD)
        if audio_seg and seg_dur:
            audio = audio_seg
            dur = sum(seg_dur)
            print("[3/7] Generando subtítulos (por bloque)")
            segmentos, t = [], 0.0
            for txt, d in zip(textos, seg_dur):
                segmentos.append((txt, t, t + d)); t += d
            subtitles.build_ass_segments(segmentos, ass)
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

    print("[4/7] Buscando b-roll de fondo")
    # Escenas del fondo: de los beats (si hay), o de broll_scenes/keywords (respaldo).
    if not escenas:
        bs = data.get("broll_scenes") or []
        if isinstance(bs, str):
            bs = [bs]
        escenas = [s.strip() for s in bs if s and s.strip()]
    escenas = [e for e in escenas if e] or [(data.get("broll_keywords") or "money finance").strip()]

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
        kw = (data.get("broll_keywords") or "money finance").strip()
        uno = broll.fetch_broll(kw, os.path.join(BUILD, "broll.mp4"))
        clips = [uno] if uno else []

    print("[5/7] Armando video")
    # Fondo: si el guion fue por bloques, alinea las duraciones del fondo a las de la voz
    # (cada escena dura lo que dura su bloque hablado) -> cambia en el momento exacto.
    bg = None
    if len(clips) >= 2:
        durs = seg_dur if (usar_bloques and seg_dur and len(seg_dur) == len(clips)) else None
        bg = video.build_multi_background(clips, dur, os.path.join(BUILD, "bg_combined.mp4"),
                                          durations=durs)
    elif len(clips) == 1:
        bg = clips[0]
    cards = []
    for c, (a, b) in zip((data.get("cards") or [])[:2], [(0.25, 0.45), (0.60, 0.80)]):
        cards.append({"big": c.get("big", ""), "small": c.get("small", ""),
                      "start": round(dur * a, 2), "end": round(dur * b, 2)})

    graphic_overlays = []
    for gi, g in enumerate((data.get("graphics") or [])[:2]):
        st = round(dur * (0.28 if gi == 0 else 0.62), 2)
        en = round(min(st + 4.0, dur - 0.5), 2)
        if en - st < 1.5:
            continue
        gdir = os.path.join(BUILD, f"g{gi}")
        pattern, _n, fps = graphics.render_frames(g, en - st, gdir)
        graphic_overlays.append({"pattern": pattern, "start": st, "end": en, "fps": fps})

    if graphic_overlays:
        cards = []

    out = os.path.join(BUILD, "reel.mp4")
    video.build_video(audio, ass, out, bg_video=bg, cards=cards,
                      graphics=graphic_overlays, duration=dur, hook=hook_card)

    print("[6/7] Subiendo video a URL pública")
    url, tag = uploader.upload_public(out, caption=caption, title=title)
    print("    URL:", url)
    print("    ID :", tag)

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