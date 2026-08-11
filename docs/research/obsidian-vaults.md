# Implement Secure AI-Agent Access to an Obsidian Vault

## Objective

Configure this machine so that an AI agent can use an Obsidian vault while enforcing three filesystem access levels at the Docker boundary:

1. **READ_WRITE** — agent may read, search, create, edit, rename, and delete files.
2. **READ_ONLY** — agent may read and search files but cannot create, modify, rename, or delete them.
3. **PRIVATE** — agent must not be able to see the real contents of the directory at all.

Do not rely on prompt instructions as the security boundary. Enforce these permissions with Docker bind mounts.

Also:

* run agent shell/code execution inside Docker;
* put the vault under Git version control;
* create a baseline checkpoint before allowing agent modifications;
* configure the Obsidian skill to use the container-visible vault path;
* verify every permission boundary with explicit tests;
* do not expose unnecessary host directories, credentials, sockets, devices, or network access.

---

# Phase 1 — Discover the Environment

Before modifying anything, inspect the existing installation.

Determine:

```text
HERMES_HOME
Hermes config file path
current terminal backend
existing docker_volumes configuration
Obsidian vault host path
Docker availability
Git availability
current Obsidian vault Git status
```

Do not guess paths.

Resolve the actual absolute paths.

Define these logical variables:

```text
HOST_VAULT=<absolute path to Obsidian vault>

HOST_RW=<HOST_VAULT>/ReadWrite
HOST_RO=<HOST_VAULT>/ReadOnly
HOST_PRIVATE=<HOST_VAULT>/Private

HOST_MASK=<safe empty directory outside HOST_VAULT>

CONTAINER_VAULT=/workspace/obsidian
CONTAINER_RW=/workspace/obsidian/ReadWrite
CONTAINER_RO=/workspace/obsidian/ReadOnly
CONTAINER_PRIVATE=/workspace/obsidian/Private
```

If equivalent folders already exist under different names, preserve them rather than renaming user data without permission.

---

# Phase 2 — Back Up Existing Configuration

Before changing Hermes configuration:

1. copy the existing configuration to a timestamped backup;
2. record the current Docker configuration;
3. record existing volume mounts;
4. do not destroy or overwrite unrelated configuration.

Example conceptual backup:

```text
config.yaml
→
config.yaml.backup-YYYYMMDD-HHMMSS
```

When editing YAML, do not create duplicate keys.

If a `docker_volumes:` block already exists, merge the new entries into the existing list.

---

# Phase 3 — Prepare the Vault

Ensure these directories exist:

```text
ReadWrite/
ReadOnly/
Private/
```

Create the masking directory outside the vault:

```text
<HOST_MASK>
```

The masking directory must be empty.

Verify:

```text
HOST_MASK contains zero files
HOST_MASK is not inside HOST_PRIVATE
HOST_MASK is not a symlink into HOST_PRIVATE
```

Do not copy private data into the masking directory.

Its purpose is to present an empty filesystem view at the container path corresponding to `Private`.

---

# Phase 4 — Enable Docker Execution

Configure Hermes to use Docker for command execution:

```yaml
terminal:
  backend: docker
```

Do not enable the local backend for agent-controlled shell operations once this configuration is active.

Prefer:

```yaml
docker_mount_cwd_to_workspace: false
```

unless the current working directory has explicitly been approved for agent access.

The sandbox should only receive directories deliberately listed in `docker_volumes`.

Do not mount:

```text
/
~
/Users
/home
/etc
/var/run/docker.sock
Docker daemon sockets
SSH directories
cloud credential directories
unrelated source trees
password stores
browser profiles
```

unless explicitly required.

Do not use Docker privileged mode.

---

# Phase 5 — Create the Three-Layer Mount Structure

Configure the vault itself as the general read/write mount:

```yaml
terminal:
  backend: docker

  docker_volumes:
    - "<HOST_VAULT>:/workspace/obsidian"
```

This gives the agent general access to the vault.

Now overlay the ReadOnly directory with a second bind mount:

```yaml
    - "<HOST_RO>:/workspace/obsidian/ReadOnly:ro"
```

This creates an OS-enforced read-only subtree even though its parent mount is read/write.

Now hide the Private directory by mounting the empty masking directory over its container location:

```yaml
    - "<HOST_MASK>:/workspace/obsidian/Private:ro"
```

The resulting logical view must therefore be:

```text
HOST                              CONTAINER

Obsidian Vault                    /workspace/obsidian
│
├── ReadWrite ──────────────────> ReadWrite
│                                  READ + WRITE
│
├── ReadOnly ───────────────────> ReadOnly
│                                  READ ONLY
│
└── Private                       Private
                                   ↑
Empty Mask ───────────────────────┘
                                   EMPTY + READ ONLY
```

The agent must never receive a separate mount exposing `HOST_PRIVATE`.

---

# Phase 6 — Configure Obsidian Skill Path

The agent must use the container-visible path, not the host path.

Set:

```text
OBSIDIAN_VAULT_PATH=/workspace/obsidian
```

Ensure this variable is available to the Docker execution environment using Hermes' supported environment forwarding/configuration mechanism.

The Obsidian skill must resolve the variable to the concrete container path before using filesystem tools.

Never instruct file tools to access:

```text
$OBSIDIAN_VAULT_PATH
```

literally.

They should receive:

```text
/workspace/obsidian
```

or a concrete absolute child path.

---

# Phase 7 — Add Behavioural Policy as a Secondary Layer

Add or extend the agent/Obsidian skill instructions with the following policy:

```text
FILESYSTEM ACCESS POLICY

/workspace/obsidian/ReadWrite
    Access: READ + WRITE
    You may create, edit, append, rename, link and delete files when required.

/workspace/obsidian/ReadOnly
    Access: READ ONLY
    You may inspect and search these files.
    Never attempt to modify, delete, rename, move or replace them.

/workspace/obsidian/Private
    Access: NO ACCESS
    Treat this location as intentionally unavailable.
    Do not attempt to bypass, remount, inspect host paths, search alternate locations,
    or infer hidden contents.

All other host filesystem locations:
    Treat as unavailable unless explicitly mounted into the sandbox.
```

This policy is advisory.

Docker permissions remain the actual enforcement mechanism.

---

# Phase 8 — Git Version Control

At the root of the Obsidian vault, check whether Git is already initialized.

If not:

```bash
git init
```

Create an appropriate `.gitignore` that excludes machine-specific or unwanted generated files while preserving the user's Markdown knowledge base.

Do not blindly overwrite an existing `.gitignore`.

Review its current contents first.

Create a baseline commit before allowing autonomous modifications:

```bash
git add -A
git commit -m "Baseline before AI agent access"
```

If Git user identity is not configured, do not invent an identity. Report the issue.

If the repository already contains uncommitted changes, preserve them and determine whether they represent intentional user work before creating the baseline.

Never discard pre-existing user changes.

---

# Phase 9 — Agent Transaction Pattern

For substantial autonomous modifications, use this workflow:

```text
1. Inspect git status.
2. Ensure prior user changes are understood.
3. Create/checkpoint the current state if appropriate.
4. Perform the requested agent operation.
5. Inspect git diff.
6. Check for modifications outside permitted locations.
7. Run validation.
8. Commit only the intended changes.
```

Each logically independent task should preferably correspond to a comprehensible Git diff or commit.

Do not mix unrelated changes.

---

# Phase 10 — Security Hardening

Keep the container's capability set restricted.

Do not weaken existing Hermes Docker protections.

Do not add:

```text
--privileged
--cap-add=SYS_ADMIN
Docker socket mounts
host PID namespace
host filesystem root mounts
```

The agent must not have the ability to remount filesystems or control the Docker daemon.

Forward only environment variables genuinely needed for the task.

Do not forward entire host environments.

For example, if a token isn't required inside the execution sandbox, do not expose it.

If the agent does not require Internet access, configure:

```yaml
docker_network: false
```

If Internet access is required, leave networking enabled but document why.

---

# Phase 11 — Verify Docker Mount Configuration

After recreating/restarting the Hermes Docker sandbox, inspect the running container's mounts.

Confirm that the effective mount table contains:

```text
/workspace/obsidian
    RW = true

/workspace/obsidian/ReadOnly
    RW = false

/workspace/obsidian/Private
    source = HOST_MASK
    RW = false
```

Do not rely solely on the YAML configuration.

Verify the actual running container.

---

# Phase 12 — Permission Tests

Create harmless test files on the host before testing.

Example:

```text
ReadWrite/agent-rw-test-source.md

ReadOnly/agent-ro-test-source.md

Private/private-secret-test.md
```

Put a unique test value into the private file such as:

```text
PRIVATE_TEST_VALUE_<random-token>
```

Do not expose that token to the agent through the prompt.

## Test A — Read/write

Inside the agent container:

1. list `/workspace/obsidian/ReadWrite`;
2. read the test file;
3. create:

```text
/workspace/obsidian/ReadWrite/agent-write-test.md
```

4. modify it;
5. confirm the host sees the modification.

Expected result:

```text
PASS — read and write succeed.
```

---

## Test B — Read-only

Inside the agent container:

1. list `/workspace/obsidian/ReadOnly`;
2. read the existing test note;
3. attempt to create:

```text
/workspace/obsidian/ReadOnly/SHOULD-NOT-EXIST.md
```

4. attempt to modify the existing test note.

Expected result:

```text
Reading succeeds.
Writing fails with a read-only filesystem/permission error.
No host file is changed.
```

If writing succeeds, stop immediately and treat the configuration as insecure.

---

## Test C — Private mask

Inside the agent container:

1. list:

```text
/workspace/obsidian/Private
```

2. recursively search it;
3. confirm the real private test file is not visible;
4. attempt to create a file there.

Expected result:

```text
Directory appears empty.
Real private files are absent.
Writing is denied.
```

On the host, separately confirm:

```text
HOST_PRIVATE/private-secret-test.md
```

still exists.

The private test token must never appear in container search results.

If it appears, stop immediately and report a privacy-boundary failure.

---

# Phase 13 — Adversarial Verification

Test common accidental bypass paths.

From inside the container, verify the agent cannot obtain the private contents through:

```text
../ path traversal
absolute host paths
symlink traversal
alternate vault paths
environment variables
duplicate mounts
Git metadata containing the private content
temporary files
backup directories
editor caches
Docker socket access
```

Important:

Hiding `/Private` does not automatically remove copies of the same sensitive information stored elsewhere.

Search the accessible vault for obvious duplicates of the private test token.

If duplicates exist in accessible locations, report them as data-layout leakage rather than a Docker mount failure.

---

# Phase 14 — Profile-Based Capabilities

If Hermes profiles are in use, apply mounts independently per profile.

Recommended pattern:

```text
PROFILE: LOCAL-TRUSTED

ReadWrite   RW
ReadOnly    RO
Private     optionally RO or hidden according to user policy


PROFILE: CLOUD-STANDARD

ReadWrite   RW
ReadOnly    RO
Private     HIDDEN


PROFILE: RESEARCH

Knowledge   RO
Research    RW
Private     HIDDEN


PROFILE: UNTRUSTED

Only explicit task workspace mounted.
Vault not mounted.
```

The principle is:

```text
grant the minimum filesystem capability necessary for the profile's job
```

Do not expose the complete vault merely because another profile requires it.

---

# Phase 15 — Final Validation Report

When implementation is finished, provide a concise report containing:

```text
Docker backend: PASS/FAIL

Vault host path:
<path>

Vault container path:
/workspace/obsidian

ReadWrite:
source=<path>
destination=/workspace/obsidian/ReadWrite
effective access=RW
test=PASS/FAIL

ReadOnly:
source=<path>
destination=/workspace/obsidian/ReadOnly
effective access=RO
read test=PASS/FAIL
write-denial test=PASS/FAIL

Private:
real source=<path>
mask source=<path>
destination=/workspace/obsidian/Private
visible real entries=0
write-denial test=PASS/FAIL
private-token search=PASS/FAIL

Git:
repository initialized=YES/NO
baseline commit=<commit hash or reason unavailable>

OBSIDIAN_VAULT_PATH:
/workspace/obsidian

Network:
ENABLED/DISABLED

Unexpected mounts:
NONE or list

Credentials forwarded:
NONE or list variable NAMES ONLY
Never print secret values.
```

---

# Non-Negotiable Rules

1. Never delete existing user files merely to simplify configuration.
2. Never move private data into a location accessible to the agent.
3. Never use prompt instructions as a substitute for filesystem enforcement.
4. Never mount the Docker daemon socket into the agent sandbox.
5. Never enable privileged Docker execution.
6. Never silently expose additional host directories.
7. Never reveal credential values in logs or reports.
8. Never discard existing Git changes.
9. Never declare the setup secure until RW, RO and PRIVATE have each been tested.
10. If any test fails, stop modifying the knowledge base and report the exact failed boundary.

The target security model is:

```text
                AI AGENT
                    │
             behavioural policy
                    │
             filesystem tools
                    │
             Docker sandbox
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
   READ/WRITE    READ ONLY      PRIVATE
       RW           RO             Ø
       │            │              │
       └────────────┴──────────────┘
                    │
                 Git
                    │
             rollback/history
```

Success means the agent can be useful without needing to be trusted to voluntarily obey access restrictions.
