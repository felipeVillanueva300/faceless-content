
import os
import sys

from src import image_script, image_gen, image_render, image_post, uploader, notify

BUILD = "build"


def _publicar(url, caption):
    """Publica la imagen en IG y FB. Tolerante a fallos: si una red falla, la otra sigue."""
    ig = os.environ.get("IG_USER_ID")
    pg = os.environ.get("FB_PAGE_ID")
    results, errores = {}, {}
    if ig:
        try:
            results["instagram"] = image_post.publish_instagram_image(ig, url, caption)
            print("    Instagram OK:", results["instagram"])
        except Exception as e:
            errores["instagram"] = str(e)
            print("    Instagram FALLÓ:", e)
    if pg:
        try:
            results["facebook"] = image_post.publish_facebook_photo(pg, url, caption)
            print("    Facebook OK:", results["facebook"])
        except Exception as e:
            errores["facebook"] = str(e)
            print("    Facebook FALLÓ:", e)
    print("Publicados:", results)
    if errores:
        print("Con errores:", errores)
    return results


def _avisar(url, titulo, caption, publicado, publish_id=None):
    """Escribe el resumen del job (si aplica) y manda el aviso de Telegram."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        estado = "PUBLICADO (imagen)" if publicado else "BORRADOR imagen (no publicado)"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"## {estado}\n\n**Título:** {titulo}\n\n")
                f.write(f"**Imagen:** [ver/descargar]({url})\n\n**Caption:**\n\n> {caption}\n\n")
        except Exception:
            pass
    notify.notify_telegram(titulo, caption or "(sin caption)", url,
                           publicado=publicado, publish_id=publish_id)


def publicar_por_id(publish_id: str):
    repo = os.environ["GITHUB_REPOSITORY"]
    print(f"[Imagen · publicar por ID] {publish_id}")
    url, caption, titulo = uploader.get_release_info(repo, publish_id)

    override = os.environ.get("PUBLISH_CAPTION", "").strip()
    if override:
        caption = override
    if not titulo:
        titulo = f"(publicación manual de {publish_id})"

    print("    URL:", url)
    results = _publicar(url, caption)
    _avisar(url, titulo, caption, publicado=bool(results))
    if (os.environ.get("IG_USER_ID") or os.environ.get("FB_PAGE_ID")) and not results:
        sys.exit(1)


def generar_borrador():
    os.makedirs(BUILD, exist_ok=True)
    niche = os.environ.get("NICHE", "tecnología y finanzas")

    print(f"[1/4] Generando guion de imagen sobre: {niche}")
    data = image_script.generate_image_post(niche)
    caption = data.get("caption") or data.get("title", "")
    title = data.get("title", "")

    print("[2/4] Generando fondo con IA")
    bg = image_gen.fetch_background(data.get("image_prompt", ""), os.path.join(BUILD, "bg.png"))

    print("[3/4] Armando imagen")
    out = os.path.join(BUILD, "post.jpg")
    image_render.render_image(data.get("big", ""), data.get("small", ""), out, bg_path=bg)

    print("[4/4] Subiendo imagen a URL pública")
    url, tag = uploader.upload_public(out, caption=caption, title=title,
                                      content_type="image/jpeg", prefix="img-")
    print("    URL:", url)
    print("    ID :", tag)

    publicar = os.environ.get("PUBLISH", "false").strip().lower() not in ("false", "0", "no")
    if not publicar:
        print("=" * 60)
        print("MODO BORRADOR (imagen, no se publicó).")
        print("ID para publicar:", tag)
        print("=" * 60)
        _avisar(url, title, caption, publicado=False, publish_id=tag)
        return

    results = _publicar(url, caption)
    _avisar(url, title, caption, publicado=bool(results))
    if (os.environ.get("IG_USER_ID") or os.environ.get("FB_PAGE_ID")) and not results:
        sys.exit(1)


def main():
    publish_id = os.environ.get("PUBLISH_ID", "").strip()
    if publish_id:
        publicar_por_id(publish_id)
    else:
        generar_borrador()


if __name__ == "__main__":
    main()
