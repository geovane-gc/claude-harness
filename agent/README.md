# Hermes, o agente do Slack

O Hermes trabalha no Slack em seu nome. Ele lê o que chega a você (DMs, menções, threads em que você está, PRs
anunciados pelo CI), responde o que confirmou na fonte, pergunta a você o que só você decide, cuida dos seus PRs no
GitHub e revisa os PRs em que pedem a sua review. Tudo o que muda de uma pessoa para outra (workspace do Slack,
organizações do GitHub, canais, nomes de serviço no Datadog) vem do `pepper/config.json`, nunca do código.

O nome e o emoji são escolhidos na instalação: o padrão é Hermes 🪽. O código mora em `pepper/`.

## Onde você fala com ele

No **canal de controle**: um canal privado só seu com o agente, que você cria antes de instalar. Por ali:

- ele te pergunta o que só você decide, e você responde na thread;
- uma mensagem sua sem o prefixo dele é uma ordem; um pedido maior vira item do backlog;
- um rascunho chega com ✅ (envia exatamente aquele texto), ✏️ (você responde) e ❌ (descarta): a sua reação decide;
- às 19h vem a revisão do dia, e você responde "1 sim, 2 não, 3 depois";
- às 8h vêm os achados do Datadog e os lembretes do dia.

**Respostas sem rascunho** (`"draft_only": false`, o padrão): ele pesquisa no `knowledge/`, no código (origin/main) e
no GitHub, e responde sozinho o que confirmou na fonte. O que compromete você (data, escopo, prioridade, opinião), mexe
em acesso, prod ou dinheiro, ou chega a um cliente ou parceiro vira pergunta no canal de controle, com o rascunho que
ele sugere. Nos seus PRs, ele tira do draft quando o CI fica verde, corrige CI vermelho em PR aberto pelo Claude e
responde comentário de revisor; quando pedem review a você, ele revisa e comenta no GitHub. O merge começa desligado
(`pr_minder_merge`). Para o modo só rascunhos, em que nada sai sozinho e toda resposta espera o seu ✅, mude para `true`
em `pepper/config.json` e faça commit na pasta do agente (o monitor de integridade restaura o que não está commitado).

Se você definir `panel_canvas_id`, um canvas do Slack mostra o que espera você (perguntas, rascunhos, PRs que precisam
de você, itens do backlog que pedem uma sessão), o que está em andamento, a saúde do agente e o custo do dia.

## O que ele faz

| Peça | Comportamento |
|---|---|
| Triagem | DMs, DMs em grupo, menções a você ou ao seu grupo, e os posts de "PR criado" do CI. Um filtro sem modelo põe em quarentena o que parece injeção; a triagem (haiku) separa o que ignorar, anotar ou fazer. Anexos são lidos em quarentena antes de chegar a qualquer resposta. |
| Respostas a pessoas e a bots | O que ele confirmou na fonte (`knowledge/`, código, GitHub). Decisão, prazo, opinião, acesso, dinheiro, prod e cliente vêm para você, com rascunho. Respostas automáticas além disso são conquistadas por categoria, pelo histórico dos seus ✅. |
| Review de PR | Quando pedem review a você, num repo das organizações em `github_orgs`. Sonnet ou opus conforme o tamanho e o risco. Lê o `CLAUDE.md`, o `AGENTS.md`, o `REVIEW.md` e o `.claude/rules/` do próprio repo, confere a outra ponta de uma integração nos clones, e comenta no GitHub em inglês. Um scan de código procura texto escrito para revisores automáticos antes da review. |
| PR minder | Seus PRs: CI vermelho → roda de novo os jobs falhos e tenta corrigir; verde e draft aberto pelo Claude → pronto para review; comentário novo → responde e pede review de novo. Merge só com `pr_minder_merge` ligado, nunca nos `no_merge_repos`. |
| Build | Um item do backlog que você aprovou vira um commit no próprio agente ou um PR draft num repo seu, seguindo as regras do repo e os playbooks do `/geovane:engage`. |
| Backlog, compromissos e conhecimento | O backlog guarda os seus pedidos maiores; os compromissos são as promessas que você fez no dia, lembradas no prazo; o conhecimento são fatos das conversas, guardados em `knowledge/` só depois do seu ✅. |
| Linear | Com `linear` ligado: nas respostas a pessoas e nos builds ele lê cards (estado, responsável, comentários) como fonte; só uma ordem sua no canal de controle cria um card, atualiza um ou comenta. Card novo vai para o time que você disser, senão para `linear_team`. Nada é apagado: o guard do Linear recusa. |
| Revisão do dia (19h) e Datadog (8h) | O resumo do dia com próximos passos numerados; as últimas 24h dos serviços em que você mais commita, com os nomes e ambientes de `datadog_service_names` e `datadog_envs`. |
| Auditoria e red team | Toda sexta uma auditoria lê uma área do agente e vira itens do backlog; todo dia um corpus de ataques conhecidos roda contra os guards. |
| Segurança | Guard de envio, guard de Bash, guard de leitura, segredos só no Keychain. As regras e onde cada uma é aplicada estão em `knowledge/security-policy.md`; os testes, em `pepper/guard/test_guards.py`. |

## Instalar

Precisa de macOS, `claude` logado com o conector do Slack (e o do Datadog e o do Linear, se quiser usá-los), `gh` logado, e o canal
de controle criado. Com o plugin instalado (`/plugin install geovane@geovane-harness`), rode o `install.sh` desta
pasta, de um clone de geovane-gc/claude-harness:

```bash
bash agent/install.sh
```

Ele pergunta os seus valores (nome e emoji do agente, workspace do Slack, organização do GitHub, canal de controle...)
e copia tudo para `~/<pasta>`. Em seguida, ele:

- preenche o `pepper/config.json`;
- põe `AGENT_HOME` no `~/.zshenv`;
- clona geovane-gc/claude-harness em `repos/` e liga `plugin/` a esse clone (só leitura);
- gera o plist do launchd.

## Depois

1. Revise o `pepper/config.json`: mais organizações em `github_orgs`, os hosts que podem aparecer em links em
   `allowed_link_hosts`, os nomes dos serviços no Datadog, os repos que nunca são mergeados (`no_merge_repos`), o time do Linear para cards novos (`linear_team`) ou `linear: false` se não usa Linear.
2. Segredos no Keychain com `bin/secret set <nome>`, nunca no config.
3. `python3 pepper/watch.py --dry --since 240` e leia o que ele faria.
4. Carregue o plist do launchd (`pepper/launchd/watch.plist`).

`knowledge/` começa só com as regras: o agente e as suas sessões o enchem. Para melhorar o agente numa sessão, use a
skill `geovane:agent-evolve`.

## Atualizar

O agente roda da sua pasta, nunca daqui: um merge neste repo não muda o agente que está rodando. As atualizações vêm
deste repo, geovane-gc/claude-harness. Para trazer uma mudança, compare com `diff -r` esta pasta e a sua, leia hooks,
`bin/` e qualquer chamada de rede nova, e traga o que quiser.
