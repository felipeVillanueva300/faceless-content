"""Pipeline diario: guion -> voz -> subtítulos -> video -> subir -> publicar."""
import os
import sys
 
from src import script_gen, tts, subtitles, video, uploader, publisher
 
BUILD = "build"
def main():
    os.makedirs(BUILD, exist_ok=True)
    niche = os.environ.get("NICHE", "tecnología y finanzas")
 
    print(f"[1/6] Generando guion sobre: {niche}")
    data = script_gen.generate_script(niche)
    narration = f"{data['hook']} {data['script']}"
    caption = data.get("caption") or data.get("title", "")
 
    print("[2/6] Sintetizando voz")
    audio = os.path.join(BUILD, "audio.mp3")
    boundaries = tts.synthesize(narration, audio)
 
    print("[3/6] Generando subtítulos")
    ass = os.path.join(BUILD, "subs.ass")
    subtitles.build_ass(narration, boundaries, ass, audio)
 
    print("[4/6] Armando video")
    out = os.path.join(BUILD, "reel.mp4")
    video.build_video(audio, ass, out)
 
    print("[5/6] Subiendo video a URL pública")
    url = uploader.upload_public(out)
    print("    URL:", url)
 
    print("[6/6] Publicando")
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
 
    if (ig or pg) and not results:
        sys.exit(1)
 
 
if __name__ == "__main__":
    main()