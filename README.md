<div align="center">

<img src="src/pixora/assets/pixora.png" alt="Pixora" width="96" height="96">

# Pixora

**Baixe imagens e vídeos de publicações públicas do Instagram, direto no seu computador.**

[![Versão](https://img.shields.io/badge/versão-1.1.1-7c5cff)](https://github.com/angelotho/Pixora/releases)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows&logoColor=white)](#download-e-instalação)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#desenvolvimento)
[![Qt](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![Licença](https://img.shields.io/badge/licença-MIT-green)](LICENSE)

[Download](#download-e-instalação) · [Como usar](#como-usar) · [Solução de problemas](#solução-de-problemas) · [Desenvolvimento](#desenvolvimento)

</div>

---

O Pixora é um aplicativo desktop gratuito para Windows. Cole o link de uma publicação, Reel ou carrossel **público** do Instagram, veja as mídias na ordem original, escolha quais quer e salve na maior resolução disponível.

Tudo roda **100% no seu computador**: sem servidor, sem conta, sem senha e sem telemetria.

> [!IMPORTANT]
> Use o Pixora apenas com conteúdo próprio ou que você tenha autorização para baixar e usar. Respeite os direitos autorais dos criadores.

## Destaques

- **Imagens, vídeos e carrosséis**: publicações únicas, Reels e carrosséis mistos, sempre na ordem original.
- **Pré-visualização antes de baixar**: grade com miniaturas, posição e resolução de cada item; selecione só o que quiser.
- **Maior resolução pública**: o arquivo salvo é a maior versão que o Instagram entrega, sem recortes.
- **Formato à sua escolha**: imagens em **JPG** (padrão) ou **PNG**; vídeos em **MP4**, sem recodificação.
- **Nunca sobrescreve**: arquivos repetidos ganham uma cópia numerada ou são pulados, como você preferir.
- **Histórico local**: veja o que já baixou, abra a pasta ou a publicação de novo.
- **Interface fluida**: tema escuro e claro, atalhos de teclado, nada trava durante análises ou downloads.
- **Privado por padrão**: nenhum login, nenhum cookie do navegador, nenhum dado enviado a terceiros.

## Download e instalação

1. Baixe o arquivo `Pixora-1.1.1-windows-x64.zip` na página de [**Releases**](https://github.com/angelotho/Pixora/releases).
2. Extraia o ZIP para uma pasta de sua preferência.
3. Execute `Pixora\Pixora.exe`. Não é preciso instalar Python nem nada mais.

> [!NOTE]
> **Aviso do Windows SmartScreen:** o executável não tem assinatura digital (certificados de assinatura são pagos). Na primeira execução o Windows pode mostrar *"O Windows protegeu o computador"*. Se você confia na origem do arquivo, clique em **Mais informações → Executar assim mesmo**.

**Para atualizar**, feche o Pixora e substitua a pasta `Pixora` inteira pela nova versão. Suas configurações e seu histórico ficam em outra pasta e são preservados.

## Como usar

1. No Instagram, abra a publicação e copie o link (**⋯ → Copiar link**).
2. No Pixora, cole o link e clique em **Analisar**.
3. Marque as mídias que deseja (ou use **Selecionar todas**).
4. Escolha o formato das imagens (JPG ou PNG) e a pasta de destino no rodapé.
5. Clique em **Baixar**. Ao terminar, use **Abrir pasta** para ver os arquivos.

Os arquivos são salvos como `instagram_<CÓDIGO>_01.jpg`, `instagram_<CÓDIGO>_02.mp4`, e assim por diante.

### Links aceitos

| Tipo | Exemplo |
|---|---|
| Publicação | `https://www.instagram.com/p/ABC123xyz/` |
| Reel | `https://www.instagram.com/reel/ABC123xyz/` |
| IGTV | `https://www.instagram.com/tv/ABC123xyz/` |
| Com usuário | `https://www.instagram.com/usuario/p/ABC123xyz/` |
| Variações | sem `https`/`www`, `m.instagram.com`, `instagr.am` e parâmetros de compartilhamento (`?igsh=…`, `?img_index=…`) |

Stories, lives, perfis e páginas de explorar não são suportados, e o app avisa quando você cola um desses links.

### Atalhos de teclado

| Atalho | Ação |
|---|---|
| `Enter` | Analisar o link |
| `Esc` | Cancelar |
| `Ctrl+L` | Focar o campo de link |
| `Ctrl+D` | Baixar selecionadas |
| `Ctrl+Shift+A` | Selecionar todas |
| `Ctrl+H` | Histórico |
| `Ctrl+,` | Configurações |

### Configurações

Pasta padrão de downloads, perguntar a pasta a cada download, abrir a pasta ao concluir, o que fazer com arquivos repetidos, tema claro/escuro, colar automaticamente links copiados e ativar/desativar o histórico.

## Privacidade e segurança

- **Sem login**: o Pixora acessa apenas conteúdo público, de forma anônima. Não pede senha nem lê cookies do navegador.
- **Sem servidor e sem telemetria**: nenhuma informação sai do seu computador além das requisições ao próprio Instagram.
- **Acesso restrito**: o cliente HTTP só baixa arquivos do CDN oficial do Instagram (lista de domínios permitidos), com redirecionamentos validados e limite de tempo em toda requisição.
- **Links validados**: outros domínios, IPs, portas, credenciais embutidas e esquemas que não sejam HTTP(S) são recusados.
- **Logs limpos**: os logs locais não registram tokens nem assinaturas de URL.

### Onde ficam seus dados

| Item | Local |
|---|---|
| Configurações | `%APPDATA%\Pixora\settings.json` |
| Histórico | `%APPDATA%\Pixora\history.db` |
| Logs | `%LOCALAPPDATA%\Pixora\logs\pixora.log` |
| Downloads (padrão) | pasta **Imagens** do Windows `\Pixora` |

O histórico guarda apenas data, link, autor, pasta e nomes de arquivos. Nenhuma imagem fica armazenada nele.

## Solução de problemas

| Mensagem | O que significa | O que fazer |
|---|---|---|
| **Muitas solicitações** | O Instagram está limitando temporariamente as consultas do seu IP. | Aguarde alguns minutos (às vezes algumas horas) e tente de novo. |
| **Publicação indisponível** | A publicação foi removida, é de uma conta privada ou o link está errado. Para acesso anônimo, o Instagram responde igual nesses casos. | Confira o link e se a publicação abre numa janela anônima do navegador. |
| **Acesso restrito** | A publicação exige login (conta privada, restrição de idade ou região). | O Pixora não faz login nem contorna restrições, por decisão de projeto. |
| **Serviço incompatível** | O Instagram mudou o formato das respostas. | Verifique se há uma nova versão do Pixora. |
| **O link expirou** | Os links das mídias são temporários. | Analise a publicação novamente e baixe. |
| **Falha de conexão** | Sem internet ou o Instagram não respondeu a tempo. | Verifique sua conexão e tente de novo. |

**Diagnóstico para suporte.** Execute o comando abaixo: ele testa validação → Instagram → prévia → download e grava o resultado em `%LOCALAPPDATA%\Pixora\logs\diagnostico.txt` (código de saída `0` = tudo certo).

```powershell
Pixora.exe --diagnose "https://www.instagram.com/p/<código>/"
```

## Limitações conhecidas

- **Apenas conteúdo público.** Não há suporte a login, cookies, CAPTCHA ou qualquer forma de contornar bloqueios.
- **Depende do Instagram.** O acesso anônimo usa endpoints públicos que podem mudar ou ser limitados a qualquer momento; nesses casos é preciso uma nova versão do app.
- **Limite de requisições.** Muitas análises seguidas a partir do mesmo IP podem ser bloqueadas por um tempo. O app avisa e não fica tentando de novo sozinho.
- **Resolução.** O máximo é o que o Instagram entrega publicamente (normalmente 1080 px de largura). Não é possível obter o arquivo original enviado pelo autor.
- **Vídeos sem arquivo público** dentro de um carrossel são ignorados, com aviso.

---

## Desenvolvimento

**Requisitos:** Windows 10/11 e Python 3.10+ (validado com 3.12).

```powershell
# Ambiente e dependências
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Executar
.\.venv\Scripts\python.exe run_pixora.py

# Testes (sem rede e sem credenciais)
.\.venv\Scripts\python.exe -m pytest

# Testes de integração reais com o Instagram (opcionais)
$env:PIXORA_NETWORK_TESTS = "1"; .\.venv\Scripts\python.exe -m pytest -m network
```

Também é possível instalar como pacote com `pip install -e .[dev]` e executar `pixora` ou `python -m pixora`.

### Gerar o executável

```powershell
.\build.ps1             # dist\Pixora\Pixora.exe + dist\Pixora-1.1.1-windows-x64.zip
.\build.ps1 -OneFile    # dist\Pixora.exe único (inicia mais devagar; mais alertas de antivírus)
```

O script roda os testes, gera o ícone, empacota com PyInstaller, testa a inicialização do executável e cria o ZIP. Feche o Pixora antes de rodar o build, senão os arquivos de `dist\Pixora` ficam bloqueados.

### Arquitetura

```
src/pixora/
├── app.py                     # ponto de entrada, logs, tratamento global de exceções, --diagnose
├── core/                      # lógica de negócio, sem Qt e 100% testável
│   ├── url_validator.py       # validação e normalização segura dos links
│   ├── models.py              # PostInfo, ImageItem, DownloadReport…
│   ├── errors.py              # erros com mensagens amigáveis
│   ├── http.py                # cliente HTTP restrito ao CDN do Instagram
│   ├── downloader.py          # downloads atômicos (.part → final), progresso, cancelamento
│   ├── converter.py           # conversão JPG/PNG apenas quando necessária
│   ├── filenames.py           # nomes, detecção de formato, conflitos
│   ├── selection.py           # regras de seleção
│   ├── service.py             # fachada usada pela interface
│   └── logging_setup.py       # logs rotativos sem tokens
├── providers/                 # integração com o Instagram (substituível)
│   ├── base.py                # protocolo PostProvider
│   └── instaloader_provider.py
├── storage/                   # configurações (JSON) e histórico (SQLite)
└── ui/                        # PySide6: janela, tema, workers, widgets e diálogos
```

- **Threads:** rede, miniaturas e downloads rodam em `QThreadPool`. Os resultados voltam à interface só por sinais (`ui/workers.py`), e análises canceladas ou antigas são descartadas.
- **Trocar a integração com o Instagram:** implemente `PostProvider.fetch_post(shortcode) -> PostInfo` (levantando apenas `PixoraError`) e passe a nova classe para `PixoraService` em `app.py`.
- **Erros nunca encerram o app:** toda falha vira uma mensagem amigável definida em `core/errors.py`.

<details>
<summary><strong>Decisões técnicas</strong></summary>

| Escolha | Motivo |
|---|---|
| **Python + PySide6** (`PySide6-Essentials`) | Toolkit desktop maduro: widgets nativos com alto DPI, estilização completa, bom modelo de threads e licença LGPL. O pacote *Essentials* evita ~300 MB de WebEngine/PDF que o app não usa. |
| **PyInstaller** (modo pasta) | Gratuito e com bom suporte a PySide6. O modo pasta inicia mais rápido e gera menos falsos positivos de antivírus que o `--onefile`. UPX desativado pelo mesmo motivo. |
| **Instaloader, anônimo** | Obtém publicações públicas sem login. Configurado com uma tentativa por consulta, intervalo mínimo de 2,5 s entre consultas e falha imediata ao detectar limite de requisições, em vez de esperar minutos e parecer travado. |
| Alternativa descartada: **oEmbed oficial da Meta** | Exige app registrado e token, e não retorna as imagens individuais do carrossel. Inviável sem servidor e credenciais. |
| **JSON + SQLite** | Locais, gratuitos e já incluídos no Python. |

</details>

### Versionamento

A versão aparece em `pyproject.toml`, `src/pixora/__init__.py`, `build.ps1`, `scripts/version_info.txt` e neste README; atualize todos ao lançar. Depois de `X.Y.9` vem `X.(Y+1).0`.

## Novidades

**1.1.1**
- Corrigido: quando o Instagram limitava as consultas, o app mostrava "Publicação indisponível" por engano. Agora mostra **Muitas solicitações** e orienta a aguardar.

**1.1.0**
- Suporte a vídeos (publicações, Reels e carrosséis mistos), salvos em MP4 sem recodificação.
- Escolha do formato das imagens (JPG ou PNG), lembrada entre sessões.
- Links `/reel/`, `/reels/` e `/tv/` agora são aceitos.

## Licença

Distribuído sob a [licença MIT](LICENSE). O Pixora não tem nenhuma relação com o Instagram ou a Meta.
