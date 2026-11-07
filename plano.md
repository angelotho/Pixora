# Desenvolvimento de aplicativo desktop para download de imagens do Instagram

Quero que você atue como um engenheiro de software sênior, especialista em Python, aplicações desktop para Windows, arquitetura de software, experiência do usuário (UX), design de interfaces (UI) e integração com serviços externos.

Nosso objetivo é desenvolver do zero um aplicativo desktop gratuito, moderno, intuitivo e funcional, capaz de baixar imagens de publicações e carrosséis do Instagram a partir de links fornecidos pelo usuário, respeitando as permissões de acesso, os direitos autorais e as restrições técnicas da plataforma.

Não quero apenas um protótipo visual. Quero um software real, com arquitetura organizada, tratamento adequado de erros, interface profissional e possibilidade de distribuição como executável para Windows.

## 1. Objetivo principal

O aplicativo deverá permitir que o usuário copie o link de uma publicação do Instagram, cole esse endereço em um campo específico e solicite a identificação das imagens disponíveis.

Quando a publicação estiver acessível por meios permitidos, o sistema deverá recuperar as informações necessárias e apresentar uma pré-visualização das imagens.

Se a publicação contiver somente uma imagem, o programa deverá permitir seu download. Se for um carrossel, deverá identificar as imagens disponíveis, apresentá-las na ordem original e permitir que o usuário escolha quais deseja baixar.

O aplicativo será dedicado exclusivamente a imagens. Não precisamos implementar download de vídeos, Reels, Stories, transmissões ao vivo ou conteúdo de perfis inteiros.

O projeto deve priorizar simplicidade, confiabilidade, bom desempenho e facilidade de manutenção.

## 2. Tecnologias e arquitetura

Minha preferência inicial é utilizar Python como linguagem principal, PySide6 para a interface gráfica e PyInstaller para gerar o executável do Windows.

Avalie tecnicamente essas escolhas antes de começar. Considere também a biblioteca Instaloader, desde que seu uso seja compatível com as permissões aplicáveis e com as restrições atuais do Instagram.

Se identificar alternativas gratuitas mais adequadas, apresente suas justificativas técnicas.

A arquitetura deverá separar claramente a interface gráfica, a lógica de negócio, o gerenciamento de downloads, a validação de URLs, o armazenamento de preferências e a integração com o Instagram.

Evite colocar toda a implementação em um único arquivo. Utilize uma estrutura modular, organizada e preparada para receber melhorias futuras.

O aplicativo deverá funcionar localmente, sem necessidade de hospedagem, servidor próprio, banco de dados remoto ou assinatura mensal.

## 3. Interface gráfica e experiência do usuário

A interface deverá apresentar uma identidade visual moderna, limpa, profissional e agradável, com aparência de um software desktop atual.

Não quero uma interface com aparência antiga ou uma simples janela Python contendo campos e botões básicos.

Utilize princípios modernos de UI/UX, incluindo hierarquia visual, espaçamento consistente, tipografia legível, ícones bem escolhidos, estados de interação e feedback visual.

O layout principal deverá apresentar um campo para inserir o link da publicação, um botão para analisar o conteúdo, uma área destinada à pré-visualização das imagens e controles para selecionar e baixar os arquivos.

Adicione indicadores de carregamento durante a análise da publicação, evitando que o usuário tenha a impressão de que o aplicativo travou.

A interface não poderá congelar durante requisições, processamento de imagens ou downloads. Utilize mecanismos adequados de execução em segundo plano, respeitando o modelo de threads do framework escolhido.

Implemente um tema escuro como padrão, com cores equilibradas, bom contraste, componentes bem desenhados e uma aparência elegante.

Considere também a responsividade da interface quando o usuário redimensionar a janela, mantendo uma boa experiência em resoluções comuns de computadores Windows.

## 4. Validação e análise dos links

O aplicativo deverá aceitar URLs válidas de publicações do Instagram, incluindo os formatos convencionais de posts e carrosséis.

Deverá reconhecer variações comuns dos links, como parâmetros adicionais de compartilhamento, sem comprometer a validação.

Antes de iniciar qualquer consulta, o sistema deverá verificar se o endereço realmente pertence ao Instagram e corresponde a um formato de publicação suportado.

Evite requisições para domínios arbitrários, redirecionamentos inseguros ou endereços locais.

Quando um link for inválido, apresente uma mensagem clara e objetiva, explicando o problema.

O processo de análise deverá verificar se é possível acessar o conteúdo utilizando métodos permitidos.

Se uma publicação exigir autenticação não disponível, estiver privada, tiver sido removida ou apresentar bloqueios de acesso, o programa deverá informar a situação sem tentar contornar essas restrições.

Não implemente técnicas de evasão de bloqueios, resolução de CAPTCHA, falsificação de sessões, utilização de cookies extraídos do navegador ou mecanismos destinados a ultrapassar controles de acesso do Instagram.

O aplicativo não deverá solicitar ou armazenar senhas do Instagram.

## 5. Identificação e pré-visualização das imagens

Depois de analisar um link válido e acessível, o programa deverá apresentar as imagens identificadas.

Para publicações individuais, mostre a imagem em uma área de pré-visualização com proporções preservadas.

Para carrosséis, apresente as imagens em uma grade organizada, mantendo a mesma sequência exibida na publicação original.

Cada imagem deverá possuir uma opção de seleção individual.

Também deverão existir comandos para selecionar todas as imagens e remover todas as seleções.

Mostre a quantidade de imagens encontradas e quantas estão selecionadas.

As miniaturas deverão carregar de maneira eficiente, evitando consumo excessivo de memória.

Sempre que possível, separe a obtenção das miniaturas do download dos arquivos finais, para que a interface permaneça rápida e responsiva.

## 6. Gerenciamento dos downloads

O usuário deverá conseguir baixar uma única imagem, várias imagens selecionadas ou todas as imagens disponíveis em um carrossel.

Antes de iniciar o download, permita selecionar a pasta de destino.

Adicione uma configuração para definir uma pasta padrão, evitando que o usuário precise escolher o mesmo diretório repetidamente.

O aplicativo deverá tentar preservar a melhor resolução disponibilizada pelo método de acesso permitido, sem prometer uma qualidade superior à fornecida pela origem.

Os arquivos deverão receber nomes organizados e consistentes, preferencialmente utilizando o identificador da publicação e a posição da imagem no carrossel.

Exemplo:

instagram_POSTID_01.jpg

instagram_POSTID_02.jpg

instagram_POSTID_03.jpg

O sistema deverá preservar o formato real do arquivo recebido e utilizar uma extensão compatível com seu conteúdo.

Implemente tratamento para arquivos já existentes, evitando substituições acidentais.

Durante o download, apresente feedback visual de progresso quando essa informação estiver disponível.

Ao finalizar, informe quantos arquivos foram salvos com sucesso e quantos apresentaram falhas.

Também deverá existir uma opção para abrir diretamente a pasta onde os arquivos foram salvos.

## 7. Histórico e configurações

Implemente um histórico local simples, contendo os downloads realizados, a data, o identificador ou link da publicação e a pasta utilizada.

O histórico não deverá armazenar imagens duplicadas desnecessariamente.

Permita ao usuário consultar operações anteriores, abrir a pasta correspondente e limpar o histórico quando desejar.

As configurações deverão permitir definir a pasta padrão de downloads, selecionar o tema visual caso um tema claro seja implementado e controlar preferências básicas do aplicativo.

Utilize uma solução local e gratuita para persistência, como SQLite ou um arquivo de configuração apropriado.

Não utilize serviços externos de telemetria ou coleta de dados pessoais.

## 8. Tratamento de erros e estabilidade

O aplicativo deverá lidar corretamente com falhas de conexão, links inválidos, conteúdo indisponível, limitações de acesso, erros de leitura, permissões insuficientes na pasta de destino e falhas durante o download.

Nenhum desses problemas deverá provocar o encerramento inesperado do programa.

As mensagens de erro precisam ser compreensíveis para usuários comuns, evitando apresentar rastreamentos técnicos diretamente na interface.

Implemente logs locais para facilitar a identificação de problemas durante o desenvolvimento, tomando cuidado para não registrar credenciais, tokens ou informações sensíveis.

Utilize limites de tempo para operações de rede, cancelamento quando viável e mecanismos adequados para evitar múltiplas operações conflitantes.

Respeite limites de requisições e não implemente tentativas agressivas ou repetidas de acesso.

## 9. Segurança e conformidade

O aplicativo deverá funcionar somente com publicações que possam ser acessadas por métodos autorizados.

Não desenvolva recursos para acessar perfis privados, contornar autenticação, recuperar conteúdo protegido ou burlar mecanismos de segurança.

Considere as regras aplicáveis do Instagram ao escolher a estratégia de integração.

Se uma biblioteca deixar de funcionar por mudanças na plataforma, o aplicativo deverá apresentar uma mensagem apropriada.

O programa será uma ferramenta de gerenciamento de imagens para conteúdos próprios ou cujo download e utilização sejam autorizados.

Não apresente funcionalidades como garantidas sem antes validar sua viabilidade técnica.

Se alguma capacidade não puder ser implementada legalmente ou de maneira confiável, explique a limitação e proponha uma alternativa compatível, sem comprometer o restante do software.

## 10. Distribuição para Windows

Quero que o resultado seja um aplicativo que possa ser executado no Windows sem exigir que o usuário instale manualmente Python ou execute comandos no terminal.

Configure o projeto para gerar um executável utilizando PyInstaller ou outra solução gratuita tecnicamente adequada.

Inclua corretamente as dependências, os recursos visuais e os arquivos necessários ao funcionamento.

Sempre que possível, faça com que as configurações e o histórico sejam armazenados em um diretório apropriado do perfil do usuário, e não na pasta interna do executável.

Prepare instruções para compilar o projeto e gerar uma versão distribuível.

Considere que executáveis sem assinatura digital podem apresentar avisos de segurança do Windows. Não tente ocultar essa condição.

## 11. Qualidade do código e testes

Quero uma base de código organizada, legível, tipada quando apropriado e de fácil manutenção.

Implemente testes automatizados para validação de URLs, normalização de links, nomes de arquivos, tratamento de erros e regras de seleção.

Sempre que possível, utilize mocks para testar o mecanismo de download sem depender de requisições reais ao Instagram.

Crie uma camada de integração independente para facilitar a substituição da biblioteca responsável pelo acesso às publicações, caso isso seja necessário futuramente.

Verifique cenários de publicações individuais, carrosséis, links inválidos, conteúdos inacessíveis, interrupção de conexão e downloads parciais.

Os testes não deverão depender de credenciais reais.

Documente os comandos necessários para instalar as dependências, executar o aplicativo, rodar os testes e gerar o executável.

## 12. Metodologia de desenvolvimento

Antes de começar a programar, analise os requisitos e elabore um plano técnico coerente.

Verifique quais bibliotecas gratuitas são mais apropriadas e quais funcionalidades realmente podem ser implementadas dentro das restrições atuais do Instagram.

Não presuma que uma solução funciona apenas porque existem exemplos antigos na internet.

Se você tiver acesso a ferramentas de pesquisa, documentação e execução de comandos, utilize-as para validar as decisões técnicas.

Estruture o desenvolvimento em etapas lógicas, começando pela arquitetura e pela integração responsável por identificar as imagens.

Depois implemente a interface gráfica, a pré-visualização, o gerenciamento de downloads, as configurações, o histórico e os testes.

Evite complexidade desnecessária e dependências que não tragam benefícios reais.

Durante o desenvolvimento, não substitua funcionalidades reais por dados simulados sem deixar isso claramente identificado.

Ao concluir, apresente um resumo das funcionalidades implementadas, eventuais limitações técnicas, resultados dos testes e instruções para executar e compilar o programa.

## 13. Critérios de conclusão

O projeto somente poderá ser considerado concluído quando o aplicativo iniciar corretamente, validar links, identificar imagens de publicações acessíveis pelos métodos escolhidos, apresentar as prévias, permitir a seleção e realizar os downloads correspondentes.

Também deverá conseguir tratar falhas sem travamentos, preservar as configurações do usuário e gerar um executável funcional para Windows.

Se não for possível testar diretamente alguma integração por limitações do ambiente de desenvolvimento, informe exatamente o que foi validado e o que ainda depende de testes reais.

O resultado precisa ser um software utilizável, e não apenas uma demonstração visual.

**Orientação final:** priorize qualidade, simplicidade, boa arquitetura e experiência do usuário. Quero que você pense no aplicativo como um produto desktop de verdade, que poderá receber novas funcionalidades futuramente, mas sem fugir do escopo inicial: baixar imagens individuais e imagens de carrosséis do Instagram por link, gratuitamente e respeitando as permissões de acesso.
