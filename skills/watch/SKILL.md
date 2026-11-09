---
name: watch
description: Assiste a um vídeo (link do YouTube, Instagram, TikTok, X, Vimeo ou arquivo local) extraindo quadros com timestamp e a transcrição do áudio, para resumir, responder perguntas, descrever cenas ou tirar passo a passo. Use quando o usuário enviar um vídeo ou link de vídeo e pedir para assistir, ver, resumir, analisar ou explicar o conteúdo.
---

# Watch — assistir vídeos

Você não reproduz vídeo diretamente, mas consegue ver imagens e ler texto. Esta skill
transforma o vídeo em **quadros (JPG) com timestamp** + **transcrição com timestamp**.

## Passo a passo

1. Rode o script (ajuste o caminho se a skill estiver em outro lugar):

   ```bash
   python3 ~/.claude/skills/watch/scripts/watch.py "<URL ou arquivo>" --out /tmp/watch_job
   ```

   Opções úteis:
   - `--max-frames N` (padrão 30). Vídeos curtos/Reels: 15–30. Aulas longas: 40–60.
   - `--interval S` para fixar um quadro a cada S segundos (ex.: zoom numa parte).
   - `--lang pt` se souber o idioma (acelera o Whisper).
   - `--model tiny|base|small|medium|large-v3` — qualidade da transcrição (padrão `small`).
   - `--no-transcript` se só interessar a parte visual.

   O script imprime um JSON com `out_dir`, `frames_dir` e `transcript`.

2. Leia `transcript.txt` (se existir) para entender a fala.
3. Abra os quadros de `frames/` com a ferramenta Read. O nome traz o tempo
   (`0007_01m24s.jpg` = 1:24). Em vídeos longos, comece por uma amostra espaçada e
   abra mais quadros nos trechos relevantes.
4. Para detalhar um trecho, rode de novo com `--interval` menor sobre o mesmo arquivo
   (`manifest.json` → `video_file`), em outra pasta `--out`.
5. Responda combinando o que foi **dito** (transcrição) e o que foi **mostrado**
   (quadros), citando timestamps `[mm:ss]`. Deixe claro quando algo vem só da imagem
   ou só do áudio, e que entre quadros pode haver coisas não vistas.

## Requisitos

- `ffmpeg` / `ffprobe` (obrigatório)
- `yt-dlp` para links (`pip install yt-dlp`)
- `faster-whisper` para transcrever quando não há legenda (`pip install faster-whisper`)

Se faltar algo, avise o usuário e sugira o comando de instalação. Se a transcrição
falhar, o script segue só com os quadros — informe isso na resposta. Conteúdo privado
ou com login (ex.: alguns Reels) pode exigir `--cookies-from-browser` no yt-dlp.

Ao final, se o usuário não precisar mais dos arquivos, apague a pasta `--out`.
