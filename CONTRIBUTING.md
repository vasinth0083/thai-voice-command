# Contributing

Thanks for helping! Thai or English is fine in issues and pull requests.

## Easy first contributions
- Add a wake-word mis-hearing your ASR produces to `JARVIS_ALIASES` (with a test).
- Add a failing example of a Thai phrase that should (or should not) match.
- Improve docs or examples.

## Development
```bash
pip install -e .
python -m unittest discover -s tests -v
```

Every behaviour change needs a test. Keep the library dependency-free.
