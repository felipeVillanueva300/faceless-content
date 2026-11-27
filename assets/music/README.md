# Música de fondo

`src/video.py` rota todas las pistas de esta carpeta (.mp3/.m4a/.wav/.ogg). Este README no se usa.

| Pista | Origen | Nota |
|---|---|---|
| bg1, bg2, bg4 | agregadas el 11 sep 2026 (origen sin anotar) | mismo lote que la bg3 retirada: confirmar de dónde salieron |
| bg5, bg7, bg8 | agregadas el 24-25 sep 2026; el archivo dice `encoder=Google` (probablemente Biblioteca de audio de YouTube) | confirmar |
| bg6 | agregada el 24 sep 2026 (origen sin anotar) | confirmar |
| bg9 | ORIGINAL, generada por código (`tools/musica_original.py`, semilla 7, 92 BPM): sin samples ni material de terceros | sin riesgo de Content ID |

Retiradas:
- **bg3** (26 nov 2026): YouTube la identificó como "Finance Music - Birthday PAPA" (Elite Alliance Music) y bloqueó en todo el mundo el Short de Afore 4/4. Se borró del repo.

Para una pista nueva original: `python tools/musica_original.py salida.wav <semilla>` y luego
`ffmpeg -i salida.wav -af "acompressor=threshold=-18dB:ratio=3:attack=10:release=200,loudnorm=I=-11:TP=-1.0:LRA=7" -b:a 256k bgN.mp3`.
Antes de agregar música de internet, anota aquí de dónde salió y su licencia.
