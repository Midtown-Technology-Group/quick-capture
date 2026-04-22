# Quick Capture CLI

Fast, frictionless capture for Logseq daily notes.

## Installation

```bash
pip install quick-capture-cli
```

## Usage

```bash
# Quick capture with automatic categorization
qc "Review [[Q2 Proposal]] with @Sarah"

# Explicit capture types
qc capture task "Fix server issue #urgent"
qc capture idea "New feature for [[bifrost]]"
qc capture note "Learned about Kerberos cloud trust"
qc capture log "8:00-8:30 Email triage"

# Interactive mode
qc interactive

# List today's captures
qc list
```

## Configuration

Shares config with `work-context-sync`. Add to `~/.work-context-sync/config.yaml`:

```yaml
qcapture:
  aliases:
    bifrost: "[[projects/bifrost]]"
    sarah: "@Sarah"
```

## License

AGPL-3.0
