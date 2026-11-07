# Pixora

Aplicativo desktop gratuito para Windows que baixa **imagens** de publicações e carrosséis **públicos** do Instagram a partir do link da publicação.

- Cole o link → **Analisar** → pré-visualize as imagens na ordem original → selecione → **Baixar**.
- Tema escuro (padrão) e claro, interface responsiva, nada de travamentos durante rede ou downloads.
- Funciona 100% localmente: sem servidor, sem conta, sem senha, sem telemetria.

> Use o Pixora apenas com conteúdo próprio ou cujo download e uso você esteja autorizado a fazer. Respeite os direitos autorais dos criadores.

---

## Funcionalidades

| Área | O que faz |
|---|---|
| Links | Aceita `instagram.com/p/<código>`, com ou sem `www`/`https`, `m.instagram.com`, `instagr.am`, `/<usuário>/p/<código>`, parâmetros de compartilhamento (`?igsh=…`, `?utm_source=…`, `?img_index=…`). Recusa outros domínios, IPs, portas, credenciais embutidas e esquemas não-HTTP, com mensagens específicas para Reels, Stories, perfis etc. |
| Análise | Identifica imagem única ou carrossel; ignora vídeos do carrossel (e avisa quantos); recusa posts de vídeo. Indicador de carregamento com opção de cancelar. |
| Pré-visualização | Grade responsiva na ordem original, miniaturas leves baixadas em paralelo (separadas do arquivo final), proporções preservadas, posição e resolução em cada cartão. |
| Seleção | Clique (ou Espaço) para marcar/desmarcar; *Selecionar todas*, *Limpar seleção*, contador "N imagens · M selecionadas". |
| Downloads | Maior resolução que o Instagram disponibiliza publicamente; nomes `instagram_<CÓDIGO>_01.jpg`; extensão definida pelo **conteúdo real** do arquivo (JPEG, PNG, WEBP, HEIC, AVIF, GIF); nunca sobrescreve (cópia numerada ou pular, configurável); barra de progresso; cancelamento; resumo de salvos/pulados/falhas; botão **Abrir pasta**. |
| Histórico | SQLite local com data, publicação, autor, pasta e arquivos. Rebaixar o mesmo post na mesma pasta atualiza o registro (sem duplicatas). Abrir pasta, abrir publicação, remover item, limpar tudo. Nenhuma imagem é armazenada no histórico. |
| Configurações | Pasta padrão, perguntar pasta a cada download, abrir pasta ao concluir, política de conflito, tema, colar automaticamente links copiados, ativar/desativar histórico. |
| Robustez | Erros traduzidos em mensagens claras; nenhum erro encerra o app; logs locais rotativos sem tokens/assinaturas; limites de tempo em toda requisição; uma operação por vez. |

Atalhos: `Enter` analisa · `Esc` cancela · `Ctrl+L` foca o link · `Ctrl+D` baixa · `Ctrl+Shift+A` seleciona todas · `Ctrl+H` histórico · `Ctrl+,` configurações.

---

## Instalação e uso (usuário final)

1. Baixe `Pixora-1.0.0-windows-x64.zip`, extraia e execute `Pixora\Pixora.exe`. Não é preciso instalar Python.
2. **Aviso do Windows SmartScreen:** o executável **não possui assinatura digital** (certificados de assinatura são pagos). Na primeira execução o Windows pode mostrar "O Windows protegeu o computador". Clique em **Mais informações → Executar assim mesmo** se confiar na origem do arquivo. Esse aviso é esperado e não foi ocultado.

Onde ficam os dados (fora da pasta do programa):

| Item | Local |
|---|---|
| Configurações | `%APPDATA%\Pixora\settings.json` |
| Histórico | `%APPDATA%\Pixora\history.db` |
| Logs | `%LOCALAPPDATA%\Pixora\logs\pixora.log` |
| Downloads (padrão) | `%USERPROFILE%\Pictures\Pixora` |

Diagnóstico (para suporte): `Pixora.exe --diagnose "https://www.instagram.com/p/<código>/"` testa validação → Instagram → prévia → download e grava o resultado em `%LOCALAPPDATA%\Pixora\logs\diagnostico.txt` (código de saída 0 = OK).

---

## Desenvolvimento

Requisitos: Windows 10/11, Python 3.10+ (validado com 3.12.10).

```powershell
# 1. Ambiente e dependências
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2. Executar o aplicativo
.\.venv\Scripts\python.exe run_pixora.py

# 3. Testes automatizados (sem rede e sem credenciais)
.\.venv\Scripts\python.exe -m pytest

# 4. Testes de integração REAIS com o Instagram (opcionais)
$env:PIXORA_NETWORK_TESTS = "1"; .\.venv\Scripts\python.exe -m pytest -m network

# 5. Gerar o executável (roda os testes, gera ícone, empacota, testa a inicialização e cria o ZIP)
.\build.ps1             # dist\Pixora\Pixora.exe + dist\Pixora-1.0.0-windows-x64.zip
.\build.ps1 -OneFile    # dist\Pixora.exe único (inicia mais devagar; mais alertas de antivírus)
```

Também é possível instalar como pacote: `pip install -e .[dev]` e executar `pixora` ou `python -m pixora`.

### Arquitetura

```
src/pixora/
├── app.py                     # ponto de entrada, logs, tratamento global de exceções, --diagnose
├── core/                      # lógica de negócio — sem Qt, 100% testável
│   ├── url_validator.py       # validação/normalização segura dos links
│   ├── models.py              # PostInfo, ImageItem, DownloadReport…
│   ├── errors.py              # erros com mensagens amigáveis
│   ├── http.py                # cliente HTTP restrito ao CDN do Instagram (allowlist, timeouts, redirecionamentos validados)
│   ├── downloader.py          # downloads atômicos (.part → final), progresso, cancelamento
│   ├── filenames.py           # nomes, detecção de formato, conflitos
│   ├── selection.py           # regras de seleção
│   ├── service.py             # fachada usada pela interface
│   └── logging_setup.py       # logs rotativos com remoção de tokens
├── providers/                 # integração com o Instagram (substituível)
│   ├── base.py                # protocolo PostProvider
│   └── instaloader_provider.py
├── storage/                   # persistência local
│   ├── paths.py · settings.py (JSON) · history.py (SQLite)
└── ui/                        # PySide6
    ├── main_window.py · theme.py · icons.py · workers.py
    ├── widgets/ (common.py, gallery.py)
    └── dialogs/ (settings_dialog.py, history_dialog.py)
```

- **Threads:** rede, decodificação de miniaturas e downloads rodam em `QThreadPool`. Resultados voltam à interface apenas por sinais entregues na thread principal (`ui/workers.py`). Análises antigas/canceladas são descartadas por um contador de geração.
- **Trocar a biblioteca do Instagram:** implemente `PostProvider.fetch_post(shortcode) -> PostInfo` (levantando apenas `PixoraError`) e passe a nova classe para `PixoraService` em `app.py`. Nada mais muda.

### Decisões técnicas

| Escolha | Motivo |
|---|---|
| **Python + PySide6** (`PySide6-Essentials`) | Qt é o toolkit desktop mais maduro em Python: widgets nativos de alto DPI, estilização completa, modelo de threads robusto, licença LGPL. O pacote *Essentials* evita ~300 MB de WebEngine/PDF que o app não usa. |
| **PyInstaller** (modo pasta) | Gratuito, maduro, bom suporte a PySide6. O modo pasta inicia mais rápido e gera menos falsos positivos de antivírus que o `--onefile` (também disponível). UPX desativado pelo mesmo motivo. |
| **Instaloader 4.16, anônimo** | Validado em 07/11/2026: obtém posts públicos (imagem única, carrossel, vídeo, inexistente) **sem login**. Configurado com uma única tentativa por consulta, intervalo mínimo de 2,5 s entre consultas e falha imediata ao detectar limite de requisições (em vez de esperar minutos, o que pareceria travamento). |
| Alternativa avaliada: **oEmbed oficial da Meta** | Exige app registrado na Meta + token e não retorna as imagens individuais do carrossel — inviável sem servidor/credenciais. |
| JSON + SQLite | Locais, gratuitos e já incluídos no Python. |

---

## Limitações conhecidas

- **Apenas conteúdo público.** Contas privadas, posts restritos por idade/região ou que exijam login mostram "Acesso restrito". O Pixora **não** faz login, não usa cookies do navegador, não resolve CAPTCHA e não contorna bloqueios — por decisão de projeto.
- **Dependência do Instagram.** O acesso anônimo usa endpoints públicos que o Instagram pode alterar ou limitar a qualquer momento. Se isso ocorrer, o app mostra "Serviço incompatível" ou "Muitas solicitações"; a correção típica é atualizar o Instaloader (`requirements.txt`) e gerar nova versão.
- **Limite de requisições.** Muitas análises seguidas a partir do mesmo IP podem ser limitadas temporariamente pelo Instagram. O app avisa e pede para aguardar; não há novas tentativas automáticas.
- **Resolução.** O arquivo salvo é a maior versão que o Instagram entrega publicamente (normalmente 1080 px de largura; às vezes maior). Não há como obter o original enviado pelo autor.
- **Links das imagens expiram.** As URLs do CDN são assinadas e temporárias; se um download falhar com "link expirou", basta analisar a publicação novamente.
- **Posts inexistentes e privados** retornam a mesma resposta do Instagram para acesso anônimo; por isso a mensagem cobre ambos os casos ("removida, privada ou com acesso restrito").
- Vídeos, Reels, Stories, lives e perfis inteiros estão fora do escopo.

## Validação realizada (07/11/2026)

- 131 testes automatizados offline (links, normalização, nomes, formatos, seleção, downloads com HTTP simulado — parciais, interrompidos, truncados, cancelados, redirecionamentos, hosts bloqueados —, tradução de erros, configurações, histórico, logs e fluxos da interface em modo offscreen).
- 4 testes reais contra o Instagram (`-m network`): imagem única com download, carrossel, vídeo recusado, post inexistente.
- Fluxo completo na interface com o Instagram real: link inválido, Reel, vídeo, inexistente, carrossel, seleção parcial, download, conflito de nomes e histórico.
- Executável gerado com PyInstaller: teste de inicialização e `--diagnose` (Instagram → prévia → download) aprovados no `.exe` empacotado.
- **Não validado:** posts de contas privadas e restritos por idade (exigiriam contas de teste); comportamento sob bloqueio prolongado do Instagram (não é possível provocar com segurança). A tradução desses casos é coberta por testes com exceções simuladas.
