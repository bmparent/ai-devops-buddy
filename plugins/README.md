# Plugin Marketplace

Each plugin must include a `plugin.py` with a `register()` function and a `manifest.json`:

```json
{
  "name": "demo",
  "skill": "example",
  "entrypoint": "plugin.py"
}
```
