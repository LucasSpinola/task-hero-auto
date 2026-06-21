<div align="center" markdown="1">

# task-hero-auto

**Deixa as tarefas repetitivas do _Task Hero_ no automático, guardar no baú, abrir os baús e sintetizar no cubo, sem você ficar clicando.**

É um programa de Windows com uma janelinha simples, você marca o que quer que ele faça e ele cuida do
resto, olhando a tela do jogo e clicando nos lugares certos na hora certa. Não precisa instalar nada,
não precisa configurar nada, é só abrir o jogo, abrir o programa e marcar as caixinhas.

<img src="docs/janela.png" alt="Janela do Task Hero Auto" width="430">

[![Baixar o programa](https://img.shields.io/badge/%E2%AC%87%20Baixar%20o%20programa-.exe-2ea44f?style=for-the-badge)](https://github.com/LucasSpinola/task-hero-auto/releases/latest/download/TaskHeroAutoStash.exe)

![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6)
![Python](https://img.shields.io/badge/feito%20em-Python-3776AB)
![Status](https://img.shields.io/badge/status-funcionando-brightgreen)

[O que faz](#o-que-faz) · [O que você precisa](#o-que-você-precisa) · [Como usar](#como-usar) · [Se não funcionar](#se-não-funcionar) · [Para quem programa](#para-quem-programa)

</div>

---

No _Task Hero_ o inventário enche o tempo todo, os baús ficam dropando e ainda dá pra ir sintetizando
item no cubo, e isso vira aquela repetição chata de abrir o baú, guardar tudo, clicar nas caixinhas e
voltar pro cubo. Esse programa faz tudo isso por você, ele fica olhando a tela do jogo, reconhece os
botões por imagem e clica sozinho, então você liga só o que quiser e pode deixar rodando enquanto faz
outra coisa, inclusive minimizado perto do relógio.

Ele não mexe no jogo por dentro, não acessa a internet e não pede login, só lê a imagem da tela e move
o mouse, igual você faria na mão, mas sem cansar.

## O que faz

- **Guardar no baú,** quando aparece o aviso de inventário cheio, ele abre o baú e guarda tudo, em todas
  as abas que você tiver (1, 2 e também a 3, que ele percebe sozinho se você comprou).
- **Abrir os baús,** aquelas caixinhas azul e marrom que aparecem no combate ele clica assim que surgem.
- **Sintetizar no cubo,** de tempos em tempos ele abre o cubo, usa o preenchimento automático e cria,
  repetindo até acabar os itens (o intervalo vem em 10 minutos e dá pra mudar).
- **Funciona sem ajuste,** ele se vira com a janela do jogo em qualquer lugar e tamanho, e em qualquer
  monitor, porque reconhece tudo por imagem.
- **Fácil de controlar,** uma janelinha com caixinhas pra ligar e desligar, com o status e um histórico
  do que ele fez.
- **Fica no seu canto,** quando você fecha no X ele vai pra bandeja do Windows (perto do relógio) e
  continua rodando, e dá pra marcar pra abrir junto com o computador.
- **Seguro,** começa tudo desligado, e se você jogar o mouse no canto superior esquerdo da tela ele para
  qualquer clique na hora.

## Como funciona

A cada instante ele tira uma foto da tela, acha os elementos do jogo por comparação de imagem, e executa
o que você deixou ligado, sempre só na região do monitor onde o jogo está, pra não clicar em nada por
engano.

```mermaid
flowchart LR
    A[Foto da tela] --> B[Reconhece o jogo<br/>por imagem]
    B --> C{O que está ligado?}
    C -->|inventário cheio| D[Abre o baú e<br/>guarda tudo]
    C -->|baú na tela| E[Clica e abre o baú]
    C -->|de tempos em tempos| F[Sintetiza no cubo]
```

## O que você precisa

Bem pouca coisa, só isto:

- Um computador com **Windows 10 ou 11**.
- O jogo **Task Hero** aberto e **à mostra** na tela, ele roda como uma janelinha em cima da área de
  trabalho, então é só deixar essa janelinha visível, sem minimizar e sem cobrir com outra janela.
- O arquivo **`TaskHeroAutoStash.exe`**, que você baixa pronto, sem instalar nada e sem precisar de
  Python.

## Como usar

1. Baixe o programa no botão **Baixar o programa** lá no topo desta página, ou pela seção **Releases**
   do repositório, e salve onde quiser.
2. Abra o **Task Hero** e deixe a tela do jogo visível.
3. Dê **dois cliques** no `TaskHeroAutoStash.exe`, vai abrir a janelinha do programa.
4. Marque o que você quer no automático:
   - **Guardar no baú quando o inventário encher**
   - **Abrir os baús que aparecem**
   - **Sintetizar no cubo de tempos em tempos**
   - **Iniciar junto com o Windows** (opcional, se quiser que ele abra sozinho ao ligar o PC)
5. Pronto, pode deixar rolando, e se quiser tirar da frente é só fechar no **X**, que ele continua
   trabalhando lá na bandeja, perto do relógio. Pra encerrar de vez, clique no ícone da bandeja e
   escolha **Sair** (ou aperte **F9**).

Se preferir o teclado, dá pra ligar e desligar por atalho a qualquer momento, **F8** guarda, **F7**
abre os baús, **F6** sintetiza e **F9** sai.

> **Importante,** enquanto alguma coisa estiver ligada o programa mexe no mouse, então é melhor não usar
> o computador ao mesmo tempo, e se precisar parar na hora, jogue o mouse no canto superior esquerdo da
> tela, que ele aborta o clique.

### O Windows mostrou um aviso azul?

Como o programa não é assinado digitalmente, na primeira vez o Windows pode mostrar uma tela azul de
proteção (SmartScreen), isso é normal com programas pequenos, é só clicar em **Mais informações** e
depois em **Executar assim mesmo**.

## Se não funcionar

- **Diz que está procurando o jogo,** deixe a tela de combate visível e não coberta por outra janela.
- **Não guarda quando enche,** abra pelo Prompt de Comando com `TaskHeroAutoStash.exe --debug`, que ele
  mostra um número de confiança, e ajuste o `trigger_threshold` no arquivo `config.json` que fica ao
  lado do programa.
- **Clicou no lugar errado,** rode `TaskHeroAutoStash.exe --once`, que ele faz um ciclo só e salva
  imagens de cada passo na pasta `%TEMP%\th_shots`, daí dá pra ver onde ele clicou.
- **As teclas não respondem,** abra o programa como administrador.

O arquivo `config.json` é criado sozinho na primeira vez, e nele dá pra mudar coisas como em quais abas
guardar, o intervalo da síntese e os atalhos, mas no uso normal você não precisa mexer em nada.

## Para quem programa

O projeto é Python puro, e o `.exe` é empacotado com o [PyInstaller](https://pyinstaller.org/).

```bash
pip install -r requirements.txt    # dependencias
python src\main.py                 # abre a janela
python src\main.py --console       # modo terminal (F8/F7/F6/F9)
python src\main.py --debug         # so mostra a confianca, nao clica
python src\main.py --once          # testa um ciclo de guardar e sai
python tests\test_actions_flow.py  # teste do fluxo, nao toca no jogo
build.bat                          # gera o TaskHeroAutoStash.exe na raiz
```

A detecção é por comparação de imagem em várias escalas, ancorada nos letreiros grandes (STASH, HERO e
CUBE), e os botões pequenos são calculados por deslocamento a partir desses letreiros, o que é bem mais
confiável do que tentar achar cada iconezinho, e alguns estados, como o botão de criar pronto ou a
existência da terceira aba, são lidos pela cor.

## Estrutura

```
task-hero-auto/
├── README.md
├── requirements.txt          dependencias para rodar
├── requirements-dev.txt      e o pyinstaller, para gerar o .exe
├── build.bat                 gera o .exe
├── config.example.json       exemplo do config
├── docs/                     imagens do README
├── templates/ui/             imagens de referencia (embutidas no .exe) e o layout.json
└── src/
    ├── main.py     abre a janela ou os modos de terminal
    ├── gui.py      a janelinha (caixinhas, status, historico, bandeja)
    ├── engine.py   o motor que fica olhando a tela e agindo
    ├── actions.py  os passos de guardar, abrir bau e sintetizar
    ├── vision.py   tira a foto da tela e compara as imagens
    ├── assets.py   carrega as imagens de referencia e o layout
    ├── config.py   cria e le o config.json
    └── ui.py       deixa o texto do historico bonitinho
```

## Aviso

É uma ferramenta pessoal pra automatizar uma tarefa repetitiva, que só lê a tela e move o mouse, sem
alterar o jogo e sem rede. Use por sua conta, lembrando que automação pode ir contra as regras de algum
serviço.

## Licença

MIT, veja o arquivo [LICENSE](LICENSE).

---

<div align="center" markdown="1">

feito por **Lucas Spinola**

</div>
