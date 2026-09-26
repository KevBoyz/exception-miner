# Changelog

## [2026-09-26] Não clonar de novo projeto já presente em `projects/<lang>`

- **Tipo:** fix
- **Arquivos:** `miner.py` (`fetch_repositories`), `README.md` (seção Parameters), `tests/test_miner.py` (novo, `TestFetchRepositories.test_skips_clone_when_repository_is_present`)
- **Problema:** numa nova execução, o miner rodava `git clone` para todo projeto do CSV, e a etapa `Receiving objects: 18% (7084/37423), 42.14 MiB | 8.33 MiB/s` aparecia de novo para repositórios que já tinham sido baixados.
- **Causa:** `fetch_repositories` chamava `git clone` sempre, sem olhar se o projeto já existia; ficava a cargo do git recusar (ou não) o destino.
- **Mudança:** se `projects/<lang>/<projeto>/.git` existe, o clone é pulado e o log registra `<projeto> already cloned in <caminho>, skipping clone`; os arquivos são listados do clone existente. Para baixar de novoVerificação, remover a pasta (ou `clear -p`).
- **:** `uv run --no-project python -m unittest tests.test_miner` → OK (o teste falha no código anterior: `call` era chamado). End-to-end com 2 repositórios locais (`file://`): 1ª execução clonou os dois; 2ª execução não chamou o git (`exploits already cloned ...`, `bup already cloned ...`) e gerou `_stats.csv` idênticos byte a byte aos da 1ª.
- **Impacto:** um projeto já clonado não é atualizado com a versão mais nova do remoto. Um clone cujo checkout falhou (ex.: `Filename too long` no Windows) também tem `.git` e é reaproveitado como está, igual a antes (o git recusava o destino não vazio).

## [2026-09-26] Clone raso (`--depth 1`) dos projetos

- **Tipo:** refactor
- **Arquivos:** `miner.py` (`fetch_repositories`), `README.md`, `tests/test_miner.py` (`test_clones_shallow_when_repository_is_missing`)
- **Problema:** o clone baixava todo o histórico de cada repositório (ex.: 37423 objetos), a etapa mais lenta para projetos novos.
- **Causa:** o miner só lê os arquivos do checkout (`Git(path).files()`); o histórico nunca é usado (conferido: nenhum uso de `Repository`/commits em `miner.py` ou `miner_pylint.py`).
- **Mudança:** `git clone --depth 1 <repo>.git --recursive <destino>`. Submódulos continuam clonados completos (sem `--shallow-submodules`, que falha em servidores que não permitem buscar um commit específico).
- **Verificação:** end-to-end com repositórios `file://`: `git rev-parse --is-shallow-repository` → `true` no clone e `_stats.csv` iguais aos gerados a partir de clones completos (caminhos normalizados).
- **Impacto:** os clones em `projects/` não têm histórico (`git log` mostra só o último commit). Nenhum efeito na saída.

## [2026-09-26] Corrida ao criar `<output_dir>/pytlint` com várias linguagens

- **Tipo:** fix
- **Arquivos:** `miner.py` (`fetch_repositories`)
- **Problema:** com `-lang python java`, um dos processos de linguagem morria logo no início com `FileExistsError: [WinError 183] Não é possível criar um arquivo já existente: 'out/pytlint'` e aquela linguagem não era processada (código de saída 0).
- **Causa:** os processos de linguagem começam juntos e faziam `if not os.path.exists(...): os.makedirs(...)`; os dois viam a pasta inexistente e o segundo `makedirs` falhava. Pré-existente; apareceu no teste multi-linguagem desta tarefa.
- **Mudança:** `os.makedirs(f"{output_dir}/pytlint/{project}", exist_ok=True)`.
- **Verificação:** end-to-end `miner.py -in in.csv -o out -lang python java -j 4` (antes: traceback acima e sem `out/parser/java`); depois: sem traceback, `java/movsim_stats.csv` e `py/exploits_stats.csv` gerados e iguais ao baseline.
- **Impacto:** nenhum.

## [2026-09-26] Clonar o próximo projeto enquanto o atual é analisado; call graph sem `os.chdir`

- **Tipo:** refactor
- **Arquivos:** `miner.py` (`process_language`), `miner_py_src/python/call_graph.py` (`generate_cfg`), `README.md`
- **Problema:** clone (rede) e análise (CPU) de cada projeto eram feitos em sequência: a CPU ficava parada durante o clone e vice-versa.
- **Causa:** laço sequencial em `process_language`.
- **Mudança:** um `ThreadPoolExecutor(max_workers=1)` roda `fetch_repositories` do projeto seguinte enquanto `collect_parser` roda no atual; a ordem de processamento e a saída não mudam. Como a thread de clone monta o destino com `os.getcwd()`, `generate_cfg` não troca mais o diretório do processo: lista os arquivos com `list_python_files(<pasta do projeto>)` (mesmos caminhos absolutos) e roda o PyCG com `subprocess.run(..., cwd=<pasta do projeto>)`. Isso também elimina a classe de bug dos clones aninhados causada por `chdir` não restaurado.
- **Verificação:** end-to-end com 2 projetos: o log mostra `Cloning into ...bup` entre o `before call graph...` e o `Before write to csv` do `exploits`; saídas iguais ao baseline. `tests.test_python_call_graph` → OK (`test_restores_cwd_on_error` e `test_non_ascii_identifiers` passam sem `chdir`).
- **Impacto:** a saída do `git clone` do próximo projeto aparece intercalada com a barra de progresso. Se o projeto não existir, `generate_cfg` agora levanta `CallGraphError("No python files found")` (tratado em `collect_parser`) em vez de `FileNotFoundError` no `chdir`.

## [2026-09-26] Multiprocessamento no parse dos arquivos (nova opção `-j/--jobs`)

- **Tipo:** refactor
- **Arquivos:** `miner.py` (novas `init_language`, `parse_file`, constante `PARSE_CHUNKSIZE`; `collect_parser` recebe `pool`; `process_language` recebe `jobs`; `__main__` divide os jobs entre as linguagens), `cli.py` (`cmdline_args`: `-j/--jobs`, padrão `os.cpu_count()`, recusa `< 1`), `README.md`, `tests/test_miner.py` (`TestCollectParser`, `TestJobsArgument`)
- **Problema:** cada projeto era analisado arquivo por arquivo num único processo por linguagem, usando um núcleo.
- **Causa:** laço sequencial em `collect_parser`.
- **Mudança:** o trabalho por arquivo (ler, `to_utf8`, parse, métricas de cada função) foi para `parse_file`, que devolve só dados simples (nós do tree-sitter não são serializáveis). `process_language` cria um `multiprocessing.Pool` por linguagem, reaproveitado em todos os projetos, e `collect_parser` usa `pool.imap(parse_file, files, chunksize=4)`, que mantém a ordem dos arquivos (saída determinística e igual à sequencial). `init_language` configura parser/funções da linguagem no processo principal e em cada worker (necessário no spawn do Windows). Com várias linguagens, `-j` é dividido entre elas; `-j 1` não cria pool.
- **Verificação:** `uv run --no-project python -m unittest tests.test_miner` → OK (`test_pool_writes_the_same_csv` compara o CSV com e sem pool byte a byte). Benchmark de `collect_parser` num diretório isolado, comparando com o código do `HEAD` (`git archive`): Python (Sick-Beard, bup, exploits, gpt_academic, linkchecker; 1055 arquivos) 35.9s → 9.5s com 1 processo → 3.8s com `-j 8` (contando a subida do pool); Java (vrapper, movsim; 729 arquivos) 24.0s → 1.3s; TypeScript (code-server, nest; 1999 arquivos) 4.8s → 1.4s. Os 9 `_stats.csv` são idênticos byte a byte aos do `HEAD`. End-to-end pela CLI (`-lang python -j 4` e `-lang python java -j 4`) → rc 0, saídas iguais ao baseline.
- **Impacto:** cada worker importa o `miner.py` (pandas, tree-sitter) e consome memória própria; o `FutureWarning: Language(path, name) is deprecated` do tree-sitter é impresso uma vez por worker. Uma exceção num worker (ex.: `FunctionDefNotFoundException`) continua abortando a linguagem, como antes.

## [2026-09-26] Pular as queries de métricas em funções sem nós de exceção

- **Tipo:** refactor
- **Arquivos:** `miner_py_src/python/tree_sitter_py.py`, `miner_py_src/typescript/tree_sitter_ts.py`, `miner_py_src/java/tree_sitter_java.py` (nova `QUERY_EXCEPTION_NODES`), `miner_py_src/{python,typescript,java}/stats.py` (`FileStats.get_metrics`; corpo antigo movido para `_compute_metrics`), `tests/test_stats_fast_path.py` (novo)
- **Problema:** depois da troca do `pd.concat`, ~65% do tempo de `collect_parser` era `Query.captures` do tree-sitter: ~15 queries por função (27 colunas no Java), mesmo em funções sem nenhum tratamento de exceção.
- **Causa:** toda métrica parte de um nó `try_statement`, `except_clause`/`catch_clause`, `finally_clause` ou `raise_statement`/`throw_statement` (conferido query a query nas 3 linguagens); sem esses nós, todas as queries voltam vazias e o resultado é sempre o mesmo (0, `False`, `""`).
- **Mudança:** `get_metrics` roda uma única query de alternância com esses 4 tipos de nó; se não houver captura, devolve uma cópia do resultado de funções sem exceção, calculado uma vez com `_compute_metrics` (sem lista de chaves duplicada à mão). Funções com algum desses nós seguem o cálculo completo. Em ~11 mil funções Python, só 20% têm algum desses nós.
- **Verificação:** `uv run --no-project python -m unittest tests.test_stats_fast_path` → OK (para cada função, `get_metrics == _compute_metrics`, mesma ordem de chaves e mesmos tipos). Métricas de todas as funções dos corpora comparadas antes/depois: Python 10834, TypeScript 727, Java 4844 funções → 0 diferenças (valores, tipos, ordem). Tempo de `get_metrics`: Java 3.25s → 0.92s, TypeScript 0.43s → 0.20s, Python 6.42s → 3.58s.
- **Impacto:** quem adicionar uma métrica que não dependa desses nós precisa incluir o tipo de nó em `QUERY_EXCEPTION_NODES` (comentário no código aponta isso).

## [2026-09-26] Remover chamada a `FileStats.metrics` (resultado nunca usado)

- **Tipo:** refactor
- **Arquivos:** `miner.py` (`collect_parser`; removidos também a lista `func_defs`, os acumuladores `num_files`/`num_functions` e o import `List`)
- **Problema:** cada função rodava 2 queries extras mais 2 por `except`, e cada `except Exception` imprimia uma linha `<arquivo>:<id do nó>` no console.
- **Causa:** `FileStats.metrics` só preenche sets e contadores de classe que nada lê (o `__str__` que os usaria nunca é chamado); o `id` impresso é um endereço de memória, sem significado para o usuário.
- **Mudança:** a chamada foi removida; o método continua existindo nas classes `FileStats`.
- **Verificação:** perfil de `collect_parser` no Sick-Beard: chamadas a `Query.captures` 85675 → 72764; `_stats.csv` idênticos byte a byte (verificação junto da entrada abaixo).
- **Impacto:** as linhas de debug `<arquivo>:<id>` deixam de aparecer no console. Os sets de classe também deixam de crescer a cada função (vazamento de memória ao longo do run).

## [2026-09-26] `collect_parser`: montar o DataFrame uma vez em vez de `pd.concat` por função

- **Tipo:** refactor
- **Arquivos:** `miner.py` (`collect_parser`), `tests/test_miner.py` (`test_rows_are_newest_first`)
- **Problema:** a análise era lenta e piorava de forma quadrática com o tamanho do projeto: no Sick-Beard (367 arquivos, 5080 funções), 13 dos 18s de `collect_parser` eram `pd.concat`/`pd.DataFrame`.
- **Causa:** para cada função era criado um DataFrame de uma linha e concatenado ao DataFrame acumulado, copiando todas as linhas anteriores (O(n²)). O nome da função também era calculado duas vezes.
- **Mudança:** as linhas são acumuladas numa lista e o DataFrame é criado uma única vez com `pd.DataFrame(rows[::-1], columns=..., dtype=object)`. A inversão mantém a ordem antiga (a última função fica no topo, como no concat que inseria no início), da qual depende a busca do call graph (primeira ocorrência). `dtype=object` preserva os valores como retornados (o concat não convertia int em float).
- **Verificação:** `_stats.csv` de 5 projetos Python idênticos byte a byte (`cmp`) antes/depois. Sick-Beard 11.9s → 3.5s; bup 3.5s → 1.4s; gpt_academic 5.5s → 2.3s; linkchecker 4.9s → 1.5s (esta mudança e a remoção do `FileStats.metrics` juntas).
- **Impacto:** nenhum na saída.

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
