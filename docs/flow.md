# Flow, phase by phase

Lane colors: gray is the runtime, purple is agents (they spend LLM tokens), and teal is the context layer (zero LLM tokens).

## 1. Session start

Context loads before the first prompt.

```mermaid
sequenceDiagram
    autonumber
    box rgba(136,135,128,0.12) Runtime
        actor U as You
        participant CC as Claude Code<br/>hooks
    end
    box rgba(127,119,221,0.14) Agent
        participant C as Coder
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    U->>CC: claude
    CC->>X: hook-start
    alt no .ctx/ in this repo
        X-->>CC: one-line hint (/ctx-harness:build)
    else CTXH_DISABLED=1
        X-->>CC: nothing (baseline run)
    else harness on
        X->>F: read protocol, map, card anchors
        opt code changed since last index
            X-)X: re-index in background
        end
        X-->>CC: protocol + map + stale cards
    end
    CC-->>C: injected into context
```

## 2. Prompt and plan

By default the prompt hook adds nothing and the coder starts working; the plan step is for a user-requested plan or a design with no reasonable default, and `CTXH_PLAN_GATE=1` makes it a rule for 3+ file changes.

```mermaid
sequenceDiagram
    autonumber
    box rgba(136,135,128,0.12) Runtime
        actor U as You
        participant CC as Claude Code<br/>hooks
    end
    box rgba(127,119,221,0.14) Agents
        participant C as Coder
        participant P as Planner
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    U->>CC: prompt
    CC->>X: hook-prompt
    X-->>C: nothing by default (a gate's rule when CTXH_PLAN_GATE / CTXH_REVIEW_GATE is on)
    opt plan requested, or design open with no reasonable default
        C->>+P: plan this (foreground)
        P->>X: q impact / cochange / tests
        X-->>P: affected files + co-change partners
        P->>F: write tasks/active.md
        P-->>-C: what, why, acceptance criteria
        C-->>U: plan, waiting for approval only on choices the request left open
        U->>C: decided
    end
```

## 3. Explore

The cheapest source is tried first. This is where the token saving comes from.

```mermaid
sequenceDiagram
    autonumber
    box rgba(127,119,221,0.14) Agents
        participant C as Coder
        participant S as Scout
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    C->>X: q find / tests / module
    X-->>C: a few lines with file:line
    C->>F: read card of touched module
    opt index cannot answer
        C->>+S: where is X decided?
        S->>X: q rdeps / impact
        S->>S: targeted grep, line ranges
        S-->>-C: answer + file:line
    end
```

## 4. Implement and review

The coder implements alone by default. The review below runs when you ask for it, when a change touches 6+ files or a fragile file, or when `CTXH_REVIEW_GATE=1` makes it a rule. The reviewer gets a fresh context.

```mermaid
sequenceDiagram
    autonumber
    box rgba(136,135,128,0.12) Runtime
        actor U as You
    end
    box rgba(127,119,221,0.14) Agents
        participant C as Coder
        participant R as Reviewer
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    loop until verified commands pass
        C->>C: edit code, run tests
        C->>F: progress log in tasks/active.md
    end
    loop at most 2 rounds
        C->>+R: review diff
        R->>X: q impact / cochange
        R->>F: check card invariants
        R-->>-C: findings + context drift
        C->>C: fix in scope, reject the rest
    end
    C->>F: notes.md, move plan to tasks/done/
    C->>X: stale
    C-->>U: result + stale cards to curate
```

## 5. Stop hook

The Stop hook runs after every turn. It handles measurement plus two opt-in, one-time gates (`CTXH_PLAN_GATE=1`, `CTXH_REVIEW_GATE=1`): a plan gate for changes that spread over 3+ code files, then the review gate. Each blocks at most once per state, so neither can loop.

```mermaid
sequenceDiagram
    autonumber
    box rgba(136,135,128,0.12) Runtime
        participant CC as Claude Code<br/>hooks
    end
    box rgba(127,119,221,0.14) Agent
        participant C as Coder
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    CC->>X: hook-stop (transcript path)
    X->>X: sum tokens, count steps
    X->>F: metrics/ + traces/
    alt 3+ code files changed, no plan in tasks/active.md (first time)
        X-->>CC: block: call the planner
        CC-->>C: continue with a plan
    else code edited after the last reviewer run (first time)
        X-->>CC: block: run the reviewer
        CC-->>C: continue with review
    else planned and reviewed, or already blocked once
        X-->>CC: allow stop
    end
```

## 6. Curation

Curation runs after merges. You can trigger it manually, from CI, or on a schedule.

```mermaid
sequenceDiagram
    autonumber
    box rgba(136,135,128,0.12) Runtime
        actor U as You or CI
    end
    box rgba(127,119,221,0.14) Agents
        participant C as Curator
        participant W as Card-writer
    end
    box rgba(29,158,117,0.14) Context layer
        participant X as ctxh
        participant F as .ctx files
    end
    U->>C: /ctx-harness:curate
    C->>X: build-index --verify, stale
    X-->>C: stale cards
    par refresh
        C->>+W: per stale module
        W->>F: rewrite card
        W->>X: anchor (stamp hashes)
        W-->>-C: done
    and learn
        C->>X: signals over traces
        X-->>C: recurring patterns
        C->>F: promote notes to learned.md
    end
    C->>X: check budgets
```

In step 6, the Curator is the main session running the curate skill. It is not a separate agent.
