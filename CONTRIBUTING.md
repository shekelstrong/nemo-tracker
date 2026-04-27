# Contributing to Nemo Tracker

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to Nemo Tracker. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## How Can I Contribute?

### Report Bugs
- Open a [GitHub Issue](https://github.com/shekelstrong/nemo-tracker/issues/new)
- Use the **Bug Report** template
- Include: steps to reproduce, expected behavior, actual behavior, screenshots if applicable

### Suggest Features
- Open a [GitHub Issue](https://github.com/shekelstrong/nemo-tracker/issues/new)
- Use the **Feature Request** template
- Describe the problem you're solving and your proposed solution

### Submit Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

```bash
git clone https://github.com/shekelstrong/nemo-tracker.git
cd nemo-tracker
cp .env.example .env
# Edit .env with your Marzban credentials
docker compose up -d
```

## Code Style

- **Python:** Follow PEP 8, use type hints
- **JavaScript:** 2-space indentation, semicolons
- **Commits:** Use clear, descriptive messages in English

## Areas We Need Help With

- 🌍 Translations (more languages)
- 📊 New chart types for analytics
- 🔌 Integrations with other VPN panels
- 📱 Mobile UI improvements
- 🧪 Test coverage

## Questions?

Open a [Discussion](https://github.com/shekelstrong/nemo-tracker/discussions) — happy to help!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
