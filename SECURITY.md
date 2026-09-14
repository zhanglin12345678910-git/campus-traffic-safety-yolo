# Security and privacy

Do not commit API keys, access tokens, passwords, private datasets, uploaded media,
model weights, training outputs, or local editor/agent configuration.

Copy `.env.example` to `.env` for local use. Keep real values only in `.env` or a
secret manager. The `.env` file and common credential formats are ignored by Git.

If a credential is ever committed, revoke and rotate it immediately. Removing it
from the latest revision is not sufficient because Git history retains old blobs.

