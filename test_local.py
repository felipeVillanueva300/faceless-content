"""Prueba LOCAL: genera guion (o usa uno de ejemplo), voz, subtítulos y video.

NO sube nada ni publica. Sirve para confirmar que tu equipo arma bien el mp4.

- Sin GEMINI_API_KEY: usa un guion de ejemplo (no necesitas ninguna cuenta).
- Con GEMINI_API_KEY: genera un guion real con Gemini.
"""
import os

from src import tts, subtitles, video

BUILD = "build"

SAMPLE = {
    "hook": "Tu dinero pierde valor mientras duermes.",
    "script": (
        "Cada peso parado se lo come la inflacion. "
        "Si guardas diez mil pesos bajo el colchon, en un ano compran menos. "
        "La regla simple: el dinero que no vas a usar pronto, ponlo a trabajar. "
        "Un instrumento a plazo, un fondo indexado, algo que le gane a la inflacion. "
        "No es arriesgar todo, es dejar de perder por no hacer nada."
    ),
}


def main():
    os.makedirs(BUILD, exist_ok=True)

    if os.environ.get("GEMINI_API_KEY"):
        from src import script_gen
        print("Generando guion con Gemini...")
        data = script_gen.generate_script(
            os.environ.get("NICHE", "tecnología y finanzas")
        )
    else:
        print("Sin GEMINI_API_KEY: uso un guion de ejemplo.")
        data = SAMPLE

    narration = f"{data['hook']} {data['script']}"

    print("Sintetizando voz...")
    audio = os.path.join(BUILD, "audio.mp3")
    boundaries = tts.synthesize(narration, audio)
    print(f"  -> {len(boundaries)} tiempos de edge-tts" + ("" if boundaries else " (vacío: se usará timing estimado)"))

    print("Generando subtítulos...")
    ass = os.path.join(BUILD, "subs.ass")
    subtitles.build_ass(narration, boundaries, ass, audio)

    print("Armando video...")
    out = os.path.join(BUILD, "reel.mp4")
    video.build_video(audio, ass, out)

    full = os.path.abspath(out)
    print("\nListo. Video en:", full)
    try:
        os.startfile(full)  # abre el video en Windows
    except Exception:
        pass


if __name__ == "__main__":
    main()