# CLAUDE.md

## Regra obrigatória: documentar TODA mudança

Este projeto está recebendo patches de correção de bugs. **Toda alteração feita no repositório deve ser documentada em [`CHANGELOG.md`](CHANGELOG.md)** (raiz do projeto), na mesma tarefa em que a mudança é feita. Nenhuma mudança fica sem registro — código, testes, dependências, configs, scripts ou dados.

- Se `CHANGELOG.md` não existir, crie-o.
- Entradas mais recentes no topo.
- Uma entrada por mudança lógica (um bug corrigido = uma entrada). Se a mesma mudança for revisada na mesma tarefa, atualize a entrada existente em vez de duplicar.
- Mudança de dependência: registrar versão antiga → nova e o motivo.
- Não documentar artefatos gerados/ignorados (`.venv/`, `output/`, `__pycache__/`, `.coverage`).
- A tarefa só está concluída quando a entrada no `CHANGELOG.md` estiver escrita.

### Formato de cada entrada

```markdown
## [AAAA-MM-DD] Título curto da mudança

- **Tipo:** fix | deps | refactor | test | docs | config
- **Arquivos:** `caminho/arquivo.py` (funções/linhas afetadas)
- **Problema:** sintoma observado (mensagem de erro exata, se houver)
- **Causa:** causa raiz
- **Mudança:** o que foi alterado e por quê
- **Verificação:** comando executado e resultado (ex.: `uv run --no-project python -m unittest` → OK)
- **Impacto:** efeitos colaterais, compatibilidade, pendências
```

## Ambiente

- venv gerenciado com `uv` em `.venv/`, **Python 3.10** (os pins de `requirements.txt` — numpy 1.21.6, pandas 1.3.5 — não têm wheels para Python > 3.10).
- Não há `pyproject.toml`; usar `--no-project` com `uv run`.

```bash
uv venv --python 3.10 .venv                      # criar venv
uv pip install --python .venv -r requirements.txt  # instalar deps
uv run --no-project python miner.py -in <csv> -o <output_dir> -lang <python|typescript|java>
uv run --no-project python -m unittest           # testes
```
