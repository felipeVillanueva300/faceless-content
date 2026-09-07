"""Pipeline diario: guion -> voz -> subtítulos -> b-roll -> video -> subir -> publicar."""
import os
import sys

from src import script_gen, tts, subtitles, video, uploader, publisher, broll, notify

BUILD = "build"


def _write_summary(url, data, caption, publicado):
    """Escribe un resumen en la corrida de GitHub (visible en la web y en el correo)."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    estado = "PUBLICADO " if publicado else "BORRADOR (no publicado)"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"## {estado}\n\n")
            f.write(f"**Título:** {data.get('title','')}\n\n")
            f.write(f"**Video:** [ver/descargar]({url})\n\n")
            f.write(f"**Caption:**\n\n> {caption}\n\n")
            if not publicado:
                f.write("Para publicarlo, relanza el workflow con **PUBLISH = true**.\n")
    except Exception:
        pass


def _audio_dur(audio_path):
    try:
        return subtitles._audio_duration(audio_path)
    except Exception:
        return 40.0


def _place_cards(cards, duration):
    """Reparte 1-2 tarjetas en tramos del video (evita el arranque y el cierre)."""
    placed = []
    cards = (cards or [])[:2]
    if not cards:
        return placed
    tramos = [(0.25, 0.45), (0.60, 0.80)]
    for card, (a, b) in zip(cards, tramos):
        placed.append({
            "big": card.get("big", ""),
            "small": card.get("small", ""),
            "start": round(duration * a, 2),
            "end": round(duration * b, 2),
        })
    return placed


def main():
    os.makedirs(BUILD, exist_ok=True)
    niche = os.environ.get("NICHE", "tecnología y finanzas")

    print(f"[1/7] Generando guion sobre: {niche}")
    data = script_gen.generate_script(niche)
    narration = f"{data['hook']} {data['script']}"
    caption = data.get("caption") or data.get("title", "")

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
    dur = _audio_dur(audio)
    cards = _place_cards(data.get("cards"), dur)
    out = os.path.join(BUILD, "reel.mp4")
    video.build_video(audio, ass, out, bg_video=bg, cards=cards)

    print("[6/7] Subiendo video a URL pública")
    url = uploader.upload_public(out)
    print("    URL:", url)

    publicar = os.environ.get("PUBLISH", "true").strip().lower() not in ("false", "0", "no")
    if not publicar:
        print("=" * 60)
        print("MODO BORRADOR (no se publicó en redes).")
        print("Revisa el video aquí:")
        print("  ", url)
        print("Título:", data.get("title", ""))
        print("Caption:", caption)
        print("Si te gusta, lanza el workflow con PUBLISH=true para publicarlo.")
        print("=" * 60)
        _write_summary(url, data, caption, publicado=False)
        notify.notify_telegram(data.get("title", ""), caption, url, publicado=False)
        return

    print("[7/7] Publicando")
    ig = os.environ.get("IG_USER_ID")
    pg = os.environ.get("FB_PAGE_ID")
    results, errores = {}, {}

    if ig:
        try:
            results["instagram"] = publisher.publish_instagram(ig, url, caption)
            print("    Instagram OK:", results["instagram"])
        except Exception as e:
            errores["instagram"] = str(e)
            print("    Instagram FALLÓ:", e)

    if pg:
        try:
            results["facebook"] = publisher.publish_facebook(pg, url, caption)
            print("    Facebook OK:", results["facebook"])
        except Exception as e:
            errores["facebook"] = str(e)
            print("    Facebook FALLÓ:", e)

    if not ig and not pg:
        print("Aviso: no se definió IG_USER_ID ni FB_PAGE_ID; no se publicó nada.")

    print("Publicados:", results)
    if errores:
        print("Con errores:", errores)
    _write_summary(url, data, caption, publicado=bool(results))
    notify.notify_telegram(data.get("title", ""), caption, url, publicado=bool(results))

    if (ig or pg) and not results:
        sys.exit(1)


if __name__ == "__main__":
    main()