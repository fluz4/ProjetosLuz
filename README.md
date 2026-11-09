# ProjetosLuz

## 🎬 watch — dê ao Claude a capacidade de "assistir" vídeos

Skill para o [Claude Code](https://claude.com/claude-code). Mande um link (YouTube,
Instagram, TikTok, X, Vimeo…) ou um arquivo de vídeo e peça:

> assiste esse vídeo e me faz um resumo: https://youtu.be/...
>
> o que ele faz no minuto 3 desse tutorial?

### Como funciona

1. **Baixa** o vídeo com `yt-dlp` (até 720p) e as legendas, se houver.
2. **Extrai quadros** com `ffmpeg`, distribuídos ao longo do vídeo, com o tempo no nome.
3. **Transcreve** o áudio: usa a legenda do site ou, se não houver, o Whisper local
   (`faster-whisper`), sem precisar de API paga.
4. O Claude lê a transcrição e olha os quadros, e responde citando os momentos `[mm:ss]`.

### Instalação

```bash
git clone https://github.com/fluz4/ProjetosLuz.git
cd ProjetosLuz
./install.sh
```

Ou, de dentro do Claude Code: *"instala essa skill pra mim: github.com/fluz4/ProjetosLuz"*.

Requer `ffmpeg` e Python 3.9+.

### Uso direto do script

```bash
python3 skills/watch/scripts/watch.py "https://youtu.be/XXXX" --out ./saida --max-frames 30 --lang pt
```

| Opção | Padrão | Para quê |
|---|---|---|
| `--max-frames` | 30 | Quantidade de quadros |
| `--interval` | auto | Segundos entre quadros (substitui o automático) |
| `--width` | 768 | Largura máxima dos quadros |
| `--lang` | detectar | Idioma do áudio |
| `--model` | small | Modelo do Whisper |
| `--no-transcript` | — | Só quadros |

Saída: `frames/*.jpg`, `transcript.txt` e `manifest.json`.
