# Changelog

## [2026-09-25] Novo comando `clear` na CLI para limpar runs anteriores

- **Tipo:** feature
- **Arquivos:** `cli.py` (`cmdline_args` aceita `argv` e despacha `clear`; novas `clear_args`, `_contains`; removida a chamada `args = cmdline_args()` no nível do módulo), `utils.py` (novas `clear_directory`, `clear_projects`, `_remove_read_only`), `miner.py` (nova `clear`; `__main__` dividido: parse dos args e desvio do `clear` no topo, antes dos imports dos parsers), `README.md` (seção "Cleaning previous runs"), `tests/test_clear.py` (novo)
- **Problema:** não havia como preparar uma execução limpa pela CLI; era preciso apagar `output/` e os clones em `projects/<lang>/` à mão. Num run novo, `git clone` falha para projetos que já existem em `projects/<lang>/<projeto>` e os arquivos antigos do `output` se misturam aos novos.
- **Causa:** funcionalidade inexistente.
- **Mudança:** `python miner.py clear -o <output_dir> [-p]`. Remove todo o conteúdo de `<output_dir>` (padrão `output`), mantendo a pasta. Com `-p`, remove também os clones em `projects/<lang>/<projeto>` (só as sub-subpastas; `projects/<lang>` fica). Symlinks são removidos sem seguir o destino. Arquivos read-only (objetos do `.git`, que o Windows recusa apagar) têm a permissão ajustada antes da remoção. Por segurança, recusa (`exit 1`) um `-o` que contenha o diretório de trabalho ou o código do miner (ex.: `-o .`). O `clear` roda antes dos imports de pandas/pydriller/tree-sitter em `miner.py`: não precisa deles, e carregar os parsers imprimia `FutureWarning: Language(path, name) is deprecated. Use Language(ptr, name) instead.` a cada limpeza. O comando antigo `python miner.py -in ... -o ... -lang ...` continua igual (o dispatch só ocorre quando o 1º argumento é `clear`). A chamada `args = cmdline_args()` no fim de `cli.py` fazia parse do `sys.argv` ao importar o módulo (inclusive nos processos filhos e nos testes) e o resultado não era usado; foi removida para permitir testar a CLI.
- **Verificação:** `uv run --no-project python -m unittest tests.test_clear` → OK (11 testes, 1 pulado: `test_does_not_follow_symlinks` precisa de privilégio de symlink no Windows, rodar no Linux). Antes da implementação o módulo falhava ao importar (`error: the following arguments are required: -in/--input_path` e depois `ImportError: cannot import name 'clear_directory'`). `test_clear_command_does_not_load_parsers` (roda `miner.py clear` em subprocesso) falhava com o `FutureWarning` no stderr antes de mover o `clear` para o topo e passa depois. Confirmado que `shutil.rmtree`/`os.remove` sem o handler falham com `[WinError 5] Acesso negado` em arquivo read-only. End-to-end num diretório temporário: run completo com repositório git local (`-in in.csv -o out -lang python`) gerou `out/` e `projects/py/demo`; `clear -o out -p` removeu `out/call_graph`, `out/parser`, `out/pytlint` e `projects/py/demo`, mantendo `out/`, `projects/py` e `projects/ts`; `clear -o .` → `Refusing to clear .`, rc=1. Suíte completa: 122 testes, 1 erro pré-existente em `tests.test_call_graph.TestGenerateCFG.test_generate_cfg` (`CallGraphError: No python files found`), que também ocorre sem esta mudança.
- **Impacto:** `clear` apaga dados sem confirmação. `exception_miner.log` não é removido (e o `clear` não escreve mais nele, pois o logger é criado depois do desvio). O `FutureWarning` do tree-sitter continua aparecendo na mineração (pré-existente). `projects` é resolvido a partir do diretório de trabalho, igual ao `fetch_repositories`.

## [2026-09-25] Listagem de arquivos do call graph não segue mais symlinks

- **Tipo:** fix
- **Arquivos:** `miner_py_src/python/call_graph.py` (nova função `list_python_files`, usada em `generate_cfg`), `tests/test_python_call_graph.py` (novo)
- **Problema:** no Linux, o run travava indefinidamente em `Generating call graph for...` (nunca chegava em `found N files`). Nenhum erro era emitido.
- **Causa:** `generate_cfg` listava arquivos com `glob.iglob("./**/*.py", recursive=True)`. O `**` do Python segue symlinks de diretório. Em repositórios que versionam symlinks auto-referentes (ex.: vários links `docs/manN -> .`), a travessia `man1/man2/man1/...` cresce exponencialmente (um ramo por link a cada nível) e na prática não termina. No Windows o git grava symlinks como arquivos texto (`core.symlinks=false`), logo nao reproduz o erro.
- **Mudança:** `list_python_files` usa `os.walk` (não segue symlinks de diretório), ignora diretórios/arquivos ocultos (como o glob fazia) e ignora arquivos que são symlink (mesmo critério de `fetch_repositories`). Removido `import glob`.
- **Verificação:** `uv run --no-project python -m unittest tests.test_python_call_graph` → OK. `test_lists_python_files_recursively` passa (comportamento preservado). `test_does_not_follow_symlinks` (9 links `manN -> .` + symlink de arquivo) é **pulado no Windows** por falta de privilégio para criar symlink (`WinError 1314`); precisa ser rodado no Linux para validar o caso.
- **Impacto:** a lista passada ao PyCG pode mudar de ordem em relação ao glob (ambos em pré-ordem, ordem do sistema de arquivos); como só os 4 primeiros arquivos são analisados (`python_src_files[0:4]`), os arquivos escolhidos podem variar.

## [2026-09-25] Falha do call graph não aborta mais o run nem deixa o cwd trocado

- **Tipo:** fix
- **Arquivos:** `miner_py_src/python/call_graph.py` (`generate_cfg`), `miner.py` (`collect_parser`), `tests/test_python_call_graph.py` (novo)
- **Problema:** qualquer `CallGraphError` (PyCG com erro, projeto sem `.py`) abortava o processo inteiro: projetos seguintes do CSV não eram processados e o `_stats.csv` do projeto atual não era gravado (a escrita vem depois do call graph). Além disso, `generate_cfg` fazia `os.chdir` para a pasta do projeto e só voltava no caminho de sucesso; se o erro fosse capturado acima, os clones seguintes iam para dentro do projeto anterior (ex.: `projects/py/<projeto_anterior>/projects/py/<projeto_seguinte>`, visto em log no Linux).
- **Causa:** exceção sem tratamento em `collect_parser`, e `chdir` de volta fora de `try/finally`.
- **Mudança:** `generate_cfg` restaura o diretório com `try/finally`; o stderr do PyCG é decodificado com `errors='replace'` ao montar o `CallGraphError` (evita `UnicodeDecodeError` escapar no lugar dele). `collect_parser` captura `CallGraphError`, registra `call graph failed for <projeto>, continuing without it: <erro>` e segue com call graph vazio (caminho `call_graph is None` que já existia).
- **Verificação:** `test_restores_cwd_on_error` falhava antes (cwd ficava na pasta do projeto) e passa depois. Integração: CSV com 2 repositórios git locais — o 1º só com `.py` oculto (dispara `No python files found` após o `chdir`), o 2º normal → 1º logou a falha e gravou seu `_stats.csv`; 2º foi clonado em `projects/py/<projeto>` (não aninhado) e processado. Artefatos do teste removidos depois.
- **Impacto:** projetos cujo call graph falha passam a ter a coluna `str_uncaught_exceptions` vazia em vez de interromper o run. A falha fica registrada no log (`exception_miner.log`).

## [2026-09-25] PyCG: pré-carregar unicodedata (crash com identificadores não-ASCII)

- **Tipo:** fix
- **Arquivos:** `miner_py_src/python/call_graph.py` (`PYCG_LAUNCHER`, `generate_cfg`), `tests/test_python_call_graph.py` (novo)
- **Problema:** no Linux, o call graph de projetos com identificadores não-ASCII falhava com `Failed creating mod : unicodedata` seguido de `AttributeError: module 'unicodedata' has no attribute 'normalize'` em `ast.parse` (dentro do PyCG).
- **Causa:** o import hook do PyCG (`pycg/machinery/imports.py`) limpa `sys.path_importer_cache` e carrega qualquer módulo importado durante a análise — inclusive extensões `.so`/`.pyd` — com um loader cujo `get_data()` retorna `""`, gerando um módulo vazio. Ao compilar um identificador não-ASCII (ex.: nomes de funções em chinês), o CPython importa `unicodedata` para normalizá-lo; com o hook ativo, recebe o módulo vazio. No Windows não aparecia porque o PyCG lê o fonte com o encoding do locale (cp1252) e o arquivo cai em `SyntaxError`, que o próprio PyCG engole (o arquivo é ignorado silenciosamente).
- **Mudança:** o PyCG passa a ser executado via `sys.executable -c PYCG_LAUNCHER`, que importa `unicodedata` antes de chamar `pycg.__main__.main()`. Com o módulo já em `sys.modules`, o hook não é consultado. Efeito colateral: o PyCG usa o mesmo interpretador do miner em vez do `pycg` encontrado no `PATH`.
- **Verificação:** reproduzido no Windows com `PYTHONUTF8=1` (lê fonte como UTF-8, igual ao Linux): `python -m pycg mod.py` com `def função()` → `AttributeError: module 'unicodedata' has no attribute 'normalize'`, rc=1; com o launcher → grafo gerado, rc=0. `test_non_ascii_identifiers` (com `PYTHONUTF8=1`) falhava com o mesmo `AttributeError` antes e passa depois.
- **Impacto:** nenhum na saída do PyCG. Outros módulos importados pela 1ª vez durante a análise continuam sujeitos ao hook do PyCG; só `unicodedata` foi observado causando falha.

## [2026-09-25] Normalizar encoding dos arquivos-fonte para UTF-8 antes do parse

- **Tipo:** fix
- **Arquivos:** `utils.py` (nova função `to_utf8`), `miner.py` (`collect_parser`), `tests/test_utils.py` (novo)
- **Problema:** projetos com arquivos-fonte que não são UTF-8 abortavam todo o run com `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xdf in position 294: invalid continuation byte` em `miner.py` (`"func_body": child.text.decode("utf-8")`). Projetos seguintes do CSV não eram processados.
- **Causa:** os bytes do arquivo eram passados ao tree-sitter sem normalização, e todo texto de nó é decodificado como UTF-8 depois. Arquivos Python 2 com declaração PEP 263 (ex.: `# -*- coding: iso-8859-1 -*-`) não são UTF-8.
- **Mudança:** `to_utf8` re-encoda o conteúdo para UTF-8 antes do `parser.parse`: mantém conteúdo que já é UTF-8; senão usa a codificação declarada (`tokenize.detect_encoding`); se não houver declaração válida, decodifica com `errors="replace"` (bytes inválidos viram U+FFFD). Offsets do tree-sitter ficam consistentes porque o parse é feito sobre os bytes já normalizados.
- **Verificação:** `uv run --no-project python -m unittest tests.test_utils` → OK (3 testes novos de `to_utf8`); `uv run --no-project python miner.py -in <entrada.csv> -o output -lang python` → projeto com arquivos `iso-8859-1` processado e `_stats.csv` gerado.
- **Impacto:** vale para todas as linguagens (código compartilhado em `collect_parser`). Arquivos sem declaração e com bytes inválidos passam a ser processados com caracteres substituídos em vez de abortar o run.

## [2026-09-25] Aceitar CSV de entrada sem linha de cabeçalho

- **Tipo:** fix
- **Arquivos:** `utils.py` (nova função `read_projects`), `miner.py` (`process_language`), `tests/test_utils.py` (novo)
- **Problema:** `python miner.py -in <entrada.csv> -lang python` com CSV sem cabeçalho falhava com `KeyError: 'name'` em `process_language` (`row['name']`). O processo filho morria e o processo principal terminava com código 0, sem processar nada.
- **Causa:** `pd.read_csv` assume que a primeira linha é o cabeçalho. Sem cabeçalho (`,name,repo,source` como em `projects_py.csv`), a primeira linha de dados virava nome de coluna e não existiam as colunas `name`/`repo`. O primeiro projeto também seria descartado.
- **Mudança:** `read_projects` lê o CSV normalmente; se as colunas `name` e `repo` não existirem, relê com `header=None` e colunas `owner,name,repo,source`. CSVs com cabeçalho continuam funcionando como antes.
- **Verificação:** `uv run --no-project python -m unittest tests.test_utils` → OK (2 testes novos de `read_projects`); run com CSV sem cabeçalho processou o projeto da primeira linha.
- **Impacto:** nenhum para CSVs existentes com cabeçalho.

## [2026-09-25] Declarar setuptools<81 como dependência (PyCG precisa de pkg_resources)

- **Tipo:** deps
- **Arquivos:** `requirements.txt`
- **Problema:** geração do call graph falhava já no primeiro projeto com `CallGraphError` contendo `ModuleNotFoundError: No module named 'pkg_resources'` (import em `pycg/formats/fasten.py`). A exceção abortava o run inteiro.
- **Causa:** `pycg` importa `pkg_resources`, que vem do `setuptools`, mas `setuptools` não estava em `requirements.txt`. Venvs criados com `uv venv` não incluem setuptools, e o `setuptools` 81+ (atual 84.0.0) removeu `pkg_resources`.
- **Mudança:** adicionado `setuptools<81` (instala 80.10.2) ao `requirements.txt`.
- **Verificação:** `.venv/Scripts/pycg.exe --help` → funciona (só emite `UserWarning` de depreciação do `pkg_resources`); run com o CSV → call graph gerado sem erro.
- **Impacto:** pycg emite um `UserWarning` de depreciação no stderr, sem efeito no resultado.
