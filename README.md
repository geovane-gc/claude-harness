# geovane

Minha harness pessoal do Claude Code, empacotada como plugin. O centro é o `/geovane:engage`, que leva
uma mudança de um card do Linear (ou de um pedido em texto) até um pull request aprovado, seguindo um
playbook por tipo de trabalho.

## Instalação

```
/plugin marketplace add geovane-gc/claude-harness
/plugin install geovane@geovane
/geovane:setup
```

No diálogo de enable, ou depois em `/config` no plugin geovane, defina:

| Opção | Para quê | Padrão |
|---|---|---|
| Repos folder (`workspace`) | A pasta com os seus repos. As runs guardam as notas em `<workspace>/.runs/`. | `~/projects` |
| Slack channel for review requests (`review_channel`) | Onde o playbook de merge lista os PRs que só esperam aprovação. Vazio: a lista vai na resposta. | vazio |

O `/geovane:setup` confere o que falta nesta máquina e pode rodar quantas vezes quiser. Ele verifica
os conectores (Linear, Slack), a chave do Linear no Keychain, a pasta dos repos e o CLI (`git`, `gh`,
`jq`, `python3`, `docker`).

## Como usar cada coisa

### Engine

**`/geovane:engage <card ou pedido>`** é o comando do dia a dia. Exemplos:

```
/geovane:engage ENG-512
/geovane:engage o PR https://github.com/<owner>/<repo>/pull/750 tá com comentários, resolve
/geovane:engage revisa o PR 760 antes de eu pedir aprovação
/geovane:engage mergeia meus PRs aprovados
/geovane:engage como implementar rate limiting nessa API? quais os padrões de mercado e as opções
```

Ele escolhe o playbook, cria uma task por passo e roda. Com um card do Linear, o
`start-task.sh` grava o card em `<workspace>/.runs/ENG-512/task.md` e move o card para In Progress.
No fim, a resposta traz o que mudou e para quem, a prova, as decisões, os princípios usados e o custo
da run.

| Playbook | Quando ele entra |
|---|---|
| Bug fix | Algo quebrado: erro, fluxo travado, CI vermelho na main. Reproduz primeiro. |
| Feature | Comportamento novo. |
| Refactoring | A estrutura muda e o comportamento não. Fixa o comportamento com testes antes. |
| Discovery | Como algo pode ser construído, antes de pedir a mudança: padrões de mercado, como outros implementam, as opções e seus trade-offs. Para na recomendação; construir é outro pedido. |
| PR babysit | PR aberto com comentários, conflito ou CI vermelho. Vigia em background e corrige até aprovar. |
| PR review | Revisar um PR, seu ou de outra pessoa, com as lentes de efeitos colaterais, padrão, escopo e companions. |
| Merge and deploy | Mergear na ordem certa e fazer deploy do jeito que o repo faz. Produção sempre volta para você. |
| Harness change | Mudar uma skill, um agente, um hook ou um princípio. Mostra cenários antes de aplicar. |

Antes de um playbook de código, o engine lê as regras do próprio repo (`CLAUDE.md`, `REVIEW.md`,
`.claude/rules/`) e decide se outro repo (infra, deploy, lib compartilhada) precisa mudar junto.

**`/geovane:request <pedido>`** transforma um pedido em card do Linear com sub-issues. Ele lê
tudo que já responde antes de perguntar, pergunta em rodadas (você responde só os números de que
discorda), passa o card pelo `judge` e publica.

**`trail`** e **`spec`** são usados pelo engine: o `trail` grava decisões e fatos em
`.runs/<card>/trail.md`, e o `spec` escreve no `docs/` do repo o que o código não diz.

### Ferramentas

| Comando | Para quê |
|---|---|
| `/geovane:how como funciona a autenticação nesse repo?` | Explicação de um subsistema, escrita por um coordenador que manda exploradores ler o código. |
| `/geovane:architect` | Esboça tipos e assinaturas antes do código, comparando pelo menos duas formas. |
| `/geovane:commit` | Commita, faz push e abre o PR. Escolhe o branch, um PR por coisa. |
| `/geovane:what` | Reescreve a última resposta em palavras simples. |
| `/geovane:catchup` | Onde o trabalho está, o que mudou e qual decisão espera você. |
| `/geovane:recall <tema>` | Reconstrói um tema a partir das conversas e memórias passadas e confere PRs e cards hoje. |
| `/geovane:reflect` | Revisa a run: o que deu certo, o que foi contornado. |

### Agentes

| Agente | Papel |
|---|---|
| `geovane:engineer` | Escreve teste e código num worktree (`<repo>/.claude/worktrees/`). Teste vermelho, depois verde. Não commita: quem commita é a skill `commit`. |
| `geovane:judge` (+ `judge-finder`, `judge-verifier`) | Julga um artefato contra uma rubrica. Só ficam os achados que sobrevivem à verificação. |
| `geovane:cleaner` | Revisa texto de harness (skill, agente, doc) cortando ruído para quem lê. |
| `geovane:atlas-agent` | Delegado genérico. Quem chama precisa dizer o modelo (sonnet/opus) e o effort. |

## Hooks

Cada hook age só dentro dos agentes do plugin (`geovane:*`), menos o `commit-opened-watch`, que age
depois da skill `geovane:commit`. Fora deles, a sua sessão fica como está.

- `git-safety`: bloqueia force push, `rm -r`, `git reset --hard` e outros comandos que jogam
  trabalho fora, e diz o caminho recuperável. Também bloqueia o `git commit` do `engineer`.
- `agent-model-cap`: um spawn do `atlas-agent` precisa dizer o modelo e o effort.
- `agent-spawn-check`: recusa no spawn o que falharia dentro do agente.
- `agent-wait`: depois de um spawn em background, quem chamou espera a resposta.
- `commit-opened-watch`: quando a `/geovane:commit` abre um PR, a sessão começa a vigiá-lo.

## Mudanças

Para mudar algo, edite este repo e atualize o plugin (`/plugin marketplace update geovane`). Uma
edição feita direto no cache do plugin some no próximo update.
