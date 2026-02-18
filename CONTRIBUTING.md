# Contributing to TrendMaster-AI

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone repository
git clone https://github.com/litansh/TrendMaster-AI.git
cd TrendMaster-AI

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Testing tools

# Setup configuration
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your Prometheus URL and credentials
```

## Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test locally**
   ```bash
   pytest tests/ -v
   black .
   isort .
   flake8 --max-line-length=120
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- Follow PEP 8
- Use Black formatter (line length: 120)
- Use isort for import ordering
- Type hints for all functions
- Docstrings: Google style

## Testing

- Write tests for all new features
- Maintain >80% code coverage
- Use pytest fixtures
- Mock external services (Prometheus, OpenAI, Kubernetes)

## Architecture Guidelines

### Adding New Metrics
1. Add query to `config/config.yaml`
2. Update Prophet analyzer if custom seasonality needed
3. Add dashboard panel in Grafana
4. Document in README

### Modifying Thresholds
1. Update default in `config.example.yaml`
2. Add validation logic
3. Write tests for edge cases
4. Document in README

### Adding Integrations
1. Create new module in `integrations/`
2. Implement standard interface
3. Add tests
4. Document configuration

## Pull Request Guidelines

- **Title:** Use conventional commits (feat:, fix:, docs:, refactor:, test:)
- **Description:** Explain what, why, and how
- **Tests:** Include test coverage
- **Documentation:** Update README if needed
- **Breaking changes:** Clearly document

## Security

- Never commit credentials
- Use environment variables or config files (excluded from git)
- Validate all user inputs
- Review AI-generated insights before acting on them

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues and PRs first
