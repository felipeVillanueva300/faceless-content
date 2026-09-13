"""Pipeline diario: guion -> voz -> subtítulos -> b-roll -> video -> subir -> publicar."""
import os
import sys

from src import script_gen, tts, subtitles, video, uploader, publisher, broll, notify, history, graphics

BUILD = "build"


def _write_summary(url, titulo, caption, publicado):
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
    return results


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
    results = _publicar_ig_youtube(url, caption, titulo)
    _write_summary(url, titulo, caption, publicado=bool(results))
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
    narration = f"{data['hook']} {data['script']}"
    caption = data.get("caption") or data.get("title", "")
    title = data.get("title", "")
    topic = data.get("topic") or title

    print("[2/7] Sintetizando voz")
    audio = os.path.join(BUILD, "audio.mp3")
    boundaries = tts.synthesize(narration, audio)

    print("[3/7] Generando subtítulos")
    ass = os.path.join(BUILD, "subs.ass")
    subtitles.build_ass(narration, boundaries, ass, audio)

    print("[4/7] Buscando b-roll de fondo")
    kw = (data.get("broll_keywords") or "money finance").strip()
    bg = broll.fetch_broll(kw, os.path.join(BUILD, "broll.mp4"))

    print("[5/7] Armando video")
    try:
        dur = subtitles._audio_duration(audio)
    except Exception:
        dur = 40.0
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
                      graphics=graphic_overlays, duration=dur)

    print("[6/7] Subiendo video a URL pública")
    url, tag = uploader.upload_public(out, caption=caption, title=title)
    print("    URL:", url)
    print("    ID :", tag)

    history.add(topic)

    publicar = os.environ.get("PUBLISH", "false").strip().lower() not in ("false", "0", "no")

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
    results = _publicar_ig_youtube(url, caption, title)
    _write_summary(url, title, caption, publicado=bool(results))
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