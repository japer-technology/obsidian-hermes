# Git Memory

Git is the shared episodic memory of this vault: it records what changed, who or
which agent changed it, why it changed, and how the change can be reviewed or
recovered. It complements Markdown's current semantic state.

## Attribution envelope

An agent-authored change should be traceable to:

- actor and runtime identity;
- task and run identity;
- trace ID;
- intent or plan hash;
- evidence and resulting receipt;
- commit, branch, and review decision.

Consequential or broad changes belong on a branch or equivalent proposal.
Conflicts preserve both candidates and block reconciliation until reviewed.

Claims, leases, heartbeats, transient queue order, and live checkpoints do not
belong in Git. Those are short-lived coordination state. Meaningful outcomes
must return to deterministic Markdown and attributed commits.

Git does not replace tested backups, but it is much more than one: it is the
review and provenance protocol shared by humans and agents.
