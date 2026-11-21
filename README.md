# Code Market — Tradução PT-BR

Projeto de localização completa (**Inglês / Russo → Português do Brasil**) para o jogo **Code Market** (*Unity Mono*, PC/Windows), com preservação total do avaliador de código, palavras-chave das linguagens (**C++**, **C#**, **Java**, **JavaScript** e **Python**), tags de formatação e sistema automático de backup/restauração.

---

## O que a tradução cobre

- **Interface, tutoriais, loja, melhorias e catálogo de referência (`resources.assets`):**
  - Completa as entradas pendentes da tabela `pt` nativa (`3.119` itens verificados), corrige concordância e alinha termos recorrentes ao `glossary.json` (`Loja`, `Caixa`, `Prateleira`, `Bancada`, `Entrega`, `Robô`, `Cliente`, `Pedido`, `Ranking`, `Modo Livre`, etc.).
  - Traduz para PT-BR todos os comentários explicativos e avisos dos scripts de biblioteca embutidos (`lib/stocker`, `lib/cashier` e `lib/map`), mantendo 100% do código executável intacto.
- **Mensagens diretas de runtime e compiladores/VMs (6 DLLs gerenciadas):**
  - Patch seguro na tabela `#US` (*User Strings*) e referências `ldstr`/`FieldRVA` das DLLs `JavaMarket.dll`, `JavaMarket.Cpp.dll`, `JavaMarket.CSharp.dll`, `JavaMarket.Java.dll`, `JavaMarket.JavaScript.dll` e `JavaMarket.Python.dll`, traduzindo mensagens de erro, exceções e avisos de interface que não passavam pela tabela de localização.
- **Integridade garantida:**
  - Palavras-chave de programação, identificadores de API, nomes internos de cena/objetos Unity e padrões de diagnóstico permanecem inalterados.
  - Suporte completo à acentuação em PT-BR (`á, é, í, ó, ú, â, ê, ô, ã, õ, ç, à`) validado nas fontes `Nunito` do jogo.

---

## Pré-requisitos

- **Windows 10 / 11 (64-bit)** com o jogo **Code Market** instalado via Steam.
- **Python 3.10+** instalado no sistema (`python` no `PATH` ou em `C:\Python314\python.exe`).
- **.NET Framework 4.x** (já nativo no Windows 10/11, usado apenas na primeira execução para compilar `DllStringPatcher.exe` a partir de `tools/DllStringPatcher/DllStringPatcher.cs`).

---

## Como Instalar (1 Clique)

1. Baixe ou clone este repositório:
   ```bash
   git clone https://github.com/devmagary/ptbrcodemarket.git
   cd ptbrcodemarket
   ```
2. Execute o instalador **`instalar_ptbr.bat`** (duplo-clique).
3. O instalador detectará automaticamente sua pasta Steam (`C:\Program Files (x86)\Steam\steamapps\common\Code Market` ou `*\SteamLibrary\steamapps\common\Code Market`). Caso o jogo esteja em outro diretório, basta informar o caminho quando solicitado.
4. No menu, escolha:
   - **`[1]` Instalar Traducao PT-BR**: compila o patch localmente a partir dos seus arquivos originais, cria backup automático (`.bak` + manifesto SHA-256 em `trabalho/backups/`) e aplica a tradução.
   - **`[2]` Restaurar Jogo Original (Ingles)**: restaura os arquivos originais e valida a integridade via SHA-256.
   - **`[3]` Verificar Status da Instalacao e Integridade**: mostra se cada arquivo do jogo está com o patch PT-BR ou no estado original.
5. Abra o **Code Market** na Steam e confirme que o idioma **Português** está selecionado nas configurações do jogo.

> **Nota:** Caso a pasta do jogo esteja em `C:\Program Files (x86)\Steam\...` e o Windows bloqueie a gravação, execute o `instalar_ptbr.bat` como **Administrador**.

---

## Uso via Linha de Comando (Desenvolvimento)

```bash
# Instalar, restaurar ou checar status direto pelo instalador
instalar_ptbr.bat --apply
instalar_ptbr.bat --restore
instalar_ptbr.bat --status

# Ou usar o pipeline Python completo
python pipeline.py extract
python pipeline.py translate
python pipeline.py build
python pipeline.py verify
python pipeline.py apply
python pipeline.py restore
```

---

## Estrutura do Projeto

- `instalar_ptbr.bat` — Instalador/desinstalador interativo para Windows.
- `pipeline.py` — Orquestrador CLI (`extract`, `translate`, `build`, `verify`, `apply`, `restore`, `status`, `test-e2e`).
- `translations_ptbr.py` — Dicionários de tradução PT-BR para `resources.assets`, scripts de biblioteca e DLLs.
- `glossary.json` — Glossário técnico EN → PT-BR e lista de palavras-chave preservadas.
- `tools/DllStringPatcher/DllStringPatcher.cs` — Utilitário C# para extração e reescrita segura de `#US`, `ldstr` e `FieldRVA` em assemblies Unity Mono.
