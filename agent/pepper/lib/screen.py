import re
import time
import unicodedata

from .settings import AGENT_NAME, OWNER
from .settings import OWNER_NAMES as _OWNER_NAMES

TAINT_SECONDS = 24 * 3600
INVISIBLE = re.compile("[­͏؜ᅟᅠ឴឵᠎​-‏‪-‮⁠-⁤⁪-⁯"
                       "﻿\U000e0000-\U000e007f]")
OWNER_NAMES = "(" + "|".join(re.escape(n) for n in (_OWNER_NAMES or ["owner"])) + ")"


def owner_then(verbs):
    # The owner's name must be who does the verb: same sentence, and no other subject after a comma.
    # "Fala <owner>! O Jordan pediu pra te..." greets the owner; it does not claim the owner asked.
    other_subject = r", (o |a )?\w+( \w+)? " + verbs
    return OWNER_NAMES + r"\b((?!" + other_subject + r")[^.!?;:]){0,30}\b" + verbs


RULES = [
    ("override", re.compile(r"\b(ignore|ignora|ignorar|ignorem|esqueca|esquece|esquecer|desconsidere|desconsidera|"
                            r"desconsiderar|disregard|forget)\b.{0,50}\b(instruc\w*|instruct\w*|regras?|rules?|prompts?|"
                            r"anteriores|previous|prior|diretrizes|orientac\w*|guardrails?|filtros?)\b")),
    ("override", re.compile(r"\b(nao siga|pare de seguir|deixe de seguir|sem seguir|don'?t follow|stop following)\b.{0,40}"
                            r"\b(regras?|instruc\w*|rules?|sistema|system)\b")),
    ("override", re.compile(r"\b(system prompt|prompt do sistema|jailbreak|modo desenvolvedor|developer mode|dan mode|"
                            r"prompt.?injection|injection.?test|god mode|modo deus)\b")),
    ("override", re.compile(r"\ba partir de agora,? (voce|vc|tu|responda|ignore|siga|seja|aja|fale|finja)\b")),
    ("override", re.compile(r"\b(finja|finge|fingir|faca de conta|pretend|roleplay|role-play|interprete o papel|aja como|"
                            r"act as)\b")),
    ("reveal config", re.compile(r"\b(revele|revela|mostre|mostra|me passe|me passa|me mande|me manda|imprima|print|vaze|"
                                 r"vaza|reveal|show me|tell me)\b.{0,30}\b(seu|sua|seus|suas|teu|tua|your)\b.{0,15}"
                                 r"\b(prompt|instruc\w*|regras|configurac\w*|config|contexto|memoria|ferramentas|tools)\b")),
    ("third-party authorization", re.compile(owner_then(r"(autorizou|liberou|permitiu|aprovou|approved|authorized)")
                                             + r"\b.{0,30}\b(voce|vc|te|" + re.escape(AGENT_NAME.lower()) + r"|agente|bot|teste|isso|responder|"
                                             r"executar|passar|contar|falar|you|this)\b")),
    ("third-party authorization", re.compile(owner_then(r"(mandou|pediu)") + r" (pra |para |que )?(voce|vc|o "
                                             + re.escape(AGENT_NAME.lower()) + r"|te|o agente|o bot)\b")),
    ("third-party authorization", re.compile(r"\b(estou repassando|to repassando|repassando (o|a|esse|essa|este|esta) "
                                             r"(pedido|solicitacao|ordem|instrucao)|em nome d[oea] " + OWNER_NAMES +
                                             r"|on behalf of|with " + OWNER_NAMES + r"'?s? (permission|approval))\b")),
    ("third-party authorization", re.compile(r"\b(autorizado|autorizada|autorizacao|authorized|authorization)\b.{0,30}\b("
                                             + OWNER_NAMES[1:-1] + r"|dono|owner|admin)\b")),
    ("command execution", re.compile(r"\b(execute|executa|executar|executem|rode|roda|rodar|rodem|run|dispare|digite)\b"
                                     r".{0,40}\b(comandos?|commands?|shell|terminal|bash|zsh|sudo|console|prompt de comando)\b")),
    ("command execution", re.compile(r"`[^`]*(\b(who|whoami|curl|wget|rm|env|printenv|chmod|chown|ssh|scp|nc|netcat|base64|"
                                     r"history|sudo|eval)\b|\bcat [~/.])[^`]*`")),
    ("command execution", re.compile(r"(\$\(|;\s*(rm|curl|wget)\b|\|\s*(sh|bash)\b|&&\s*(rm|curl|wget)\b)")),
    ("credential request", re.compile(r"\b(me passa|me passe|passa|passe|me manda|me mande|manda|mande|envia|envie|mostra|"
                                      r"mostre|compartilha|compartilhe|cola|cole|revela|revele|vaza|vaze|imprime|imprima|"
                                      r"le|leia|abre|abra|qual e|qual eh|quais sao|send|share|give|show|paste|print|reveal|"
                                      r"what is|what's)\b.{0,40}\b(tokens?|senhas?|passwords?|passwd|credenc\w*|credentials?|"
                                      r"api.?keys?|chaves? (de api|privadas?|secretas?|ssh)|private keys?|secrets?|segredos?|"
                                      r"\.env|cookies?|session id|ssh.?keys?|2fa|otp|mfa)\b")),
    ("personal or sexual content", re.compile(r"\b(gay|gays|lesbica|bissexual|homossexual|orientacao sexual|sexual|sexuais|"
                                              r"sexo|sexy|sensual\w*|erotic\w*|nudes?|pelad\w*|transar|religiao|gravida|"
                                              r"endereco de casa)\b")),
    ("content about a person", re.compile(r"\b(poema|poesia|musica|cancao|rap|soneto|versos)\b.{0,60}"
                                          r"\b(sobre|do|da|pro|pra|para|com)\b")),
    ("hidden text", re.compile(r"<!--|-->|\[/?(system|inst|assistant)\]|</?(system|instructions?|assistant)>")),
]
STRONG = {"override", "reveal config", "third-party authorization", "command execution", "credential request"}


def normalize(text):
    text = re.sub(r"<@[UW][A-Z0-9]+\|([^>]*)>", r" \1 ", str(text or ""))
    text = re.sub(r"<#C[A-Z0-9]+\|([^>]*)>", r" \1 ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = INVISIBLE.sub("", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def without_links(text):
    return re.sub(r"https?://\S+", " ", re.sub(r"<https?://[^>]*>", " ", text))


def signals_of(text):
    plain = without_links(normalize(text))
    found = [name for name, rule in RULES if rule.search(plain)]
    raw = str(text or "")
    if INVISIBLE.search(raw):
        found.append("hidden text")
    if re.search(r"[A-Za-z0-9+/]{80,}={0,2}", without_links(raw)):
        found.append("encoded text")
    return list(dict.fromkeys(found))


def thread_key(message):
    return f"thread:{message.get('channel', '')}:{message.get('thread_ts') or message.get('ts', '')}"


def sender_key(message):
    return f"user:{message.get('user', '')}"


def prune(taints, now=None):
    now = now or time.time()
    return {key: until for key, until in (taints or {}).items() if until > now}


ADDRESSED = re.compile(r"^\W*(@?" + re.escape(AGENT_NAME.lower()) + r")\b")


def directed(message):
    sources = set(message.get("sources") or [])
    return bool(sources & {"dm", "mention"}) or bool(ADDRESSED.search(normalize(message.get("text", ""))))


def taint(state, message, signals, now=None):
    now = now or time.time()
    taints = prune(state.get("taints"), now)
    taints[thread_key(message)] = now + TAINT_SECONDS
    if message.get("user") and message.get("user") != OWNER and directed(message) and set(signals) & STRONG:
        taints[sender_key(message)] = now + TAINT_SECONDS
    state["taints"] = taints


def taint_signals(state, message, now=None):
    live = prune(state.get("taints"), now)
    found = []
    if thread_key(message) in live:
        found.append("thread with an attack attempt in the last 24h")
    if message.get("user") != OWNER and sender_key(message) in live:
        found.append("sender with an attack attempt in the last 24h")
    return found


def screen(state, message, now=None):
    if message.get("user") == OWNER:
        return []
    own = signals_of(message.get("text", ""))
    if own:
        taint(state, message, own, now)
        return own
    return taint_signals(state, message, now)
