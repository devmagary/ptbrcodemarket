# -*- coding: utf-8 -*-
"""Tabelas de tradução EN/RU -> PT-BR para Code Market (resources.assets + 6 DLLs)."""

RESOURCE_PT_OVERRIDES = {
    "Sandbox": "Modo Livre",
    "Duck typing": "Duck typing (tipagem estrutural)",
    "Arrays: Array": "Arrays: Array (Vetores)",
    "bytes ({0})": "bytes ({0})",
    "bytes (str.encode)": "bytes (str.encode)",
    "bytes (int.to_bytes)": "bytes (int.to_bytes)",
    "bytes (int.from_bytes)": "bytes (int.from_bytes)",
    "iter(callable, sentinel)": "iter(chamável, sentinela)",
    "new T{.field = …}": "new T{.campo = …}",
    "metaclasses (metaclass=…)": "metaclasses (metaclass=…)",
    "the format has {{{0}}}, and there are only {1} arguments": "o formato usa o índice {{{0}}}, mas há apenas {1} argumento(s)",
    "\n```\nEntity e = robot.look(Direction.UP);\nif (e == null) {\n    print(\"Nothing above\");\n} else {\n    print(\"Above: \" + e);\n}\n```": "\n```\nEntity e = robot.look(Direction.UP);\nif (e == null) {\n    print(\"Nada acima\");\n} else {\n    print(\"Acima: \" + e);\n}\n```",
    "\n                Comments are notes for people; Python skips them. A comment starts with `#` and runs to the end of the line.\n\n                ```\n                # to the end of the line\n                robot.move(Direction.UP)  # can go after code too\n                \"\"\"And a string in triple quotes that isn't put anywhere\n                does nothing either: long explanations are written so.\"\"\"\n                ```": "\n                Comentários são anotações para pessoas; o Python os ignora. Um comentário começa com `#` e vai até o fim da linha.\n\n                ```\n                # até o fim da linha\n                robot.move(Direction.UP)  # também pode vir depois do código\n                \"\"\"E uma string entre aspas triplas que não é atribuída a nada\n                também não faz nada: explicações longas são escritas assim.\"\"\"\n                ```",
    "Burlap tied with a rope bow, soil and a young sprout inside. A seasonal good: it can only be ordered in spring. Out of season the delivery won't bring it, and the call costs a $10 fine for each sack.": "Saco de juta amarrado com um laço de corda, com terra e um broto novo dentro. Uma mercadoria sazonal: só pode ser encomendada na primavera. Fora da estação, a entrega não a traz, e a chamada custa uma multa de $10 por saco.",
    "request for member '{0}' is ambiguous: it is in '{1}' and in '{2}'": "o acesso ao membro '{0}' é ambíguo: ele está em '{1}' e em '{2}'",
    "request for member '{0}' in '{1}', which is of non-class type": "acesso ao membro '{0}' em '{1}', que é de um tipo que não é classe",
    "request for member '{0}' in an expression of pointer type '{1}' (maybe you meant to use '->' ?)": "acesso ao membro '{0}' em uma expressão do tipo ponteiro '{1}' (talvez você quisesse usar '->' ?)",
    "request for member '{0}' in an expression of non-class type '{1}'": "acesso ao membro '{0}' em uma expressão de tipo que não é classe '{1}'",
    "to the tomato table, and take one": "até a bancada de tomates e pegar um",
}

SCRIPT_COMMENT_REPLACEMENTS = {
    # stocker (lib/stocker)
    "// ===================== Кладовщик (lib/stocker) =====================":
        "// ===================== Estoquista (lib/stocker) =====================",
    "// Остаток на любом стеллаже «Поиск» говорит издалека — store.getStock(x, y), — так что обходить стеллажи не надо:":
        "// A quantidade em qualquer estante a «Busca» informa de longe — store.getStock(x, y) — sem precisar percorrer todas:",
    "// кладовщик считает, чего сколько не хватает до полного, пишет это в свой список (robot.getList() — его видно":
        "// o estoquista calcula quanto falta para encher cada estante, anota na sua lista (robot.getList() — visível",
    "// на панели робота), заказывает доставку, встречает грузовик и раскладывает товар по полкам.":
        "// no painel do robô), pede a entrega, recebe o caminhão e organiza os produtos nas prateleiras.",
    "// Кладовщиков может быть несколько: товары делятся между ними по кругу, каждый заказывает и разгружает своё.":
        "// Pode haver vários estoquistas: os produtos são divididos em rodízio entre eles; cada um pede e descarrega os seus.",
    "// что надо заказать, чтобы все стеллажи стали полными":
        "// o que é preciso pedir para todas as estantes ficarem cheias",
    "// сколько влезает на стеллаж: видно только вплотную — запоминаем":
        "// quanto cabe na estante: só é visível de perto — memorizamos",
    "// грузовик вызвал он — ему и разгружать":
        "// ele chamou o caminhão — cabe a ele descarregar",
    "// в какой час он в последний раз пробовал разложить остатки из рук":
        "// em qual hora ele tentou pela última vez guardar o que sobrou nas mãos",
    "// сколько всего роботов в магазине — поменяй, когда купишь ещё":
        "// total de robôs na loja — altere quando comprar mais",
    "// какой я кладовщик по счёту (0, 1, …): первые номера — кассиры, кладовщики — следом":
        "// qual é o meu índice de estoquista (0, 1, …): os primeiros são caixas, os estoquistas vêm depois",
    "// мой ли это товар: товары делятся между кладовщиками по кругу":
        "// se este produto é meu: os itens são divididos entre os estoquistas em rodízio",
    "// сколько влезает на стеллаж этого товара: один раз подойти и посмотреть":
        "// quanto cabe na estante deste produto: basta ir uma vez até lá e verificar",
    "// уже посчитанная соседняя клетка с тем же остатком: полка с хлебом занимает две, и обе говорят один остаток":
        "// célula vizinha já contabilizada com o mesmo estoque: a prateleira de pão ocupa duas células e ambas informam o mesmo valor",
    "// пишет в список, чего сколько не хватает до полного (минус то, что уже едет в грузовике и что в руках),":
        "// anota na lista quanto falta para completar (menos o que já vem no caminhão e o que está nas mãos),",
    "// по одной штуке каждого товара по кругу: даже неполный грузовик привезёт всего понемногу.":
        "// uma unidade de cada produto em rodízio: mesmo um caminhão parcial trará um pouco de tudo.",
    "// true — какой-то стеллаж почти пуст (осталась четверть или меньше)":
        "// true — alguma estante está quase vazia (restou um quarto ou menos)",
    "// не в сезон его не привезут":
        "// fora de estação não entregam",
    "// вторая клетка той же полки — её не считаем":
        "// segunda célula da mesma prateleira — não contamos duas vezes",
    "// звонит в доставку, когда в списке набралось на полгрузовика — или сразу (hurry), если какой-то":
        "// chama a entrega quando a lista enche meio caminhão — ou na hora (hurry), se alguma",
    "// стеллаж почти пуст. Платят за товар, а не за поездку, так что грузовику незачем стоять.":
        "// estante estiver quase vazia. Você paga pelo produto, não pela viagem, então não há motivo para segurar o caminhão.",
    "// Берёт столько, на сколько хватает денег":
        "// Pega o máximo que o dinheiro permitir",
    "// заказано — вычёркиваем из списка":
        "// pedido feito — removemos da lista",
    "// разгружает приехавший грузовик и раскладывает товар по полкам":
        "// descarrega o caminhão que chegou e guarda os produtos nas prateleiras",
    "// ждём, пока откроют кузов":
        "// aguardamos abrirem a carroceria",
    "// руки полны тем, что некуда положить:":
        "// mãos cheias com itens sem espaço disponível:",
    "// остальное — обратно, деньги за него вернутся":
        "// o restante volta e o dinheiro é reembolsado",
    "// работа кладовщика: считает, чего не хватает, заказывает, а грузовик встречает, как только приехал":
        "// rotina do estoquista: calcula o que falta, faz o pedido e recebe o caminhão assim que chega",
    "// грузовик уже тут (программу перезапустили) — разгружает первый":
        "// o caminhão já está aqui (programa reiniciado) — o primeiro estoquista descarrega",
    "// разгрузили, уехал":
        "// descarregado, foi embora",
    "// осталось в руках — раз в час пробует разложить":
        "// sobrou nas mãos — tenta guardar uma vez por hora",

    # cashier (lib/cashier)
    "// ===================== Кассир (lib/cashier) =====================":
        "// ===================== Caixa (lib/cashier) =====================",
    "\"Робот \"":
        "\"Robô \"",
    "\": за экраном или пакетом кассы что-то стоит — переставь кассу\"":
        "\": há algo atrás da tela ou da sacola do caixa — reposicione o caixa\"",
    "// Стоит за СВОЕЙ кассой — робот №1 за первой, №2 за второй (в порядке store.findAll(Entity.REGISTER)) —":
        "// Fica no SEU próprio caixa — robô nº 1 no primeiro, nº 2 no segundo (na ordem de store.findAll(Entity.REGISTER)) —",
    "// и только торгует: принимает заказ, собирает его со стеллажей, кладёт в пакет.":
        "// e apenas atende: anota o pedido, busca os itens nas estantes e coloca na sacola.",
    "// Где за кассой встать и куда смотреть, каждый раз заново говорит «Карта»: переставят кассу — он и не заметит.":
        "// Onde parar atrás do caixa e para onde olhar é consultado sempre via «Mapa»: mesmo se moverem o caixa, ele continua funcionando.",
    "// уже сказали, что к кассе не подойти":
        "// já avisamos que não é possível alcançar o caixa",
    "// встаёт за свою кассу: к экрану (принять заказ) или к пакету":
        "// posiciona-se no seu caixa: diante da tela (receber pedido) ou da sacola",
    "// за кассой что-то стоит — её надо переставить":
        "// há algo bloqueando atrás do caixa — é preciso reposicioná-lo",
    "// можно ли сейчас продать этот товар этому покупателю":
        "// se é permitido vender este produto agora para este cliente",
    "// алкоголь с 22:00 до 6:00 нельзя":
        "// venda de álcool é proibida das 22:00 às 06:00",
    "// детям — ни алкоголя, ни сигарет":
        "// para menores — nem álcool nem cigarros",
    "// сколько ещё нести этого товара: заказано, минус то, что уже в руках":
        "// quanto ainda falta trazer deste produto: pedido menos o que já está nas mãos",
    "// ближайший (напрямик) стеллаж, с которого ещё надо взять для заказа; null — брать больше нечего":
        "// estante mais próxima (em linha reta) de onde ainda falta pegar para o pedido; null — não há mais o que pegar",
    "// несёт ли робот что-то, что ждёт этот покупатель":
        "// se o robô está carregando algo que este cliente espera",
    "// принимает заказ и собирает его: полный поднос за раз, стеллажи от ближнего к дальнему.":
        "// recebe o pedido e o coleta: enche a capacidade por vez, indo das estantes mais próximas às mais distantes.",
    "// false — у кассы никого нет":
        "// false — não há ninguém no caixa",
    "// стеллажи, где товар кончился или не подойти":
        "// estantes onde o produto acabou ou o acesso está bloqueado",
    "// в пакет не кладётся — не долбим его зря":
        "// não cabe/não entra na sacola — não insistimos à toa",
    "// чего нет — вычёркиваем, покупатель не ждёт зря":
        "// o que está em falta é riscado para o cliente não esperar à toa",
    "// работа кассира: торговать, а что осталось в руках (покупатель ушёл) — на полку":
        "// rotina do caixa: atender clientes e devolver às prateleiras o que sobrar nas mãos (caso o cliente desista)",

    # map (lib/map)
    "// ===================== Дорога (lib/map) =====================":
        "// ===================== Mapa / Rotas (lib/map) =====================",
    "// Общая для кассира и кладовщика: подключается строкой import lib.map;":
        "// Biblioteca compartilhada entre caixa e estoquista: importada via import lib.map;",
    "// Где что стоит, отвечают «Карта» и «Поиск»: клетки касс, стеллажей и гаража, остатки на полках.":
        "// «Mapa» e «Busca» informam onde tudo está: células dos caixas, estantes, garagem e estoque nas prateleiras.",
    "// Самим остаётся только дойти: шаг за шагом на соседнюю клетку, откуда до цели ближе, — без поиска в ширину.":
        "// Só resta caminhar até lá: passo a passo para a célula vizinha mais próxima do alvo — sem busca em largura.",
    "// на сколько шаг в эту сторону меняет x и y":
        "// quanto um passo nessa direção altera x e y",
    "// сколько шагов до клетки (x, y), если бы на пути ничего не стояло":
        "// quantos passos até a célula (x, y) se não houvesse obstáculos no caminho",
    "// идёт к клетке (x, y): каждый шаг — на свободную соседнюю клетку, откуда до цели ближе всего, только не назад.":
        "// caminha até a célula (x, y): cada passo vai para a célula vizinha livre mais próxima do destino, sem voltar atrás.",
    "// false — не дошёл: на цели кто-то стоит, тупик или слишком долго":
        "// false — não chegou: há alguém no destino, beco sem saída ou demorou demais",
    "// на цели кто-то стоит — попробуем в другой раз":
        "// há alguém ocupando o destino — tentaremos outra vez",
    "// клетки, откуда берут этот товар: свободные соседи его стеллажей, где «Поиск» знает, куда повернуться":
        "// células de onde se pega este produto: vizinhas livres das estantes onde a «Busca» sabe para onde virar",
    "// ближайшая (если идти напрямик) клетка из списка; null — список пуст":
        "// célula mais próxima (em linha reta) da lista; null — se a lista estiver vazia",
    "// встаёт к стеллажу товара лицом к нему: к ближайшему месту забора, а не дойти — к следующему":
        "// posiciona-se de frente para a estante do produto: no ponto de coleta mais próximo ou no seguinte se estiver bloqueado",
    "// стоит ли в магазине стеллаж этого товара":
        "// verifica se existe na loja uma estante para este produto",
    "// кладёт товар из рук на его полки; полная полка — идёт к следующей такой же":
        "// guarda o produto das mãos em suas prateleiras; se uma estiver cheia, vai para a próxima igual",
    "// раскладывает по полкам всё, что в руках":
        "// guarda nas prateleiras tudo o que estiver nas mãos",
    "// сколько раз товар есть в списке":
        "// quantas vezes o produto aparece na lista",
}

DLL_US_TRANSLATIONS = {
    "JavaMarket.dll": {
        "{0} does not fit at {1}": "{0} não cabe em {1}",
        "SOON IN DLC": "EM BREVE NO DLC",
        "[Save] {0} object(s) no longer fit in the store and went to the inventory": "[Save] {0} objeto(s) não couberam mais na loja e foram para o inventário",
        "[Save] kept {0} entries of unknown types unchanged": "[Save] {0} registro(s) de tipos desconhecidos mantidos sem alteração",
        "[Save] can't read ": "[Save] não foi possível ler ",
        "[Save] can't read the old PlayerPrefs save: ": "[Save] não foi possível ler o save antigo de PlayerPrefs: ",
        "Steam didn't start: ": "A Steam não iniciou: ",
        "Steam didn't take the stats": "A Steam não aceitou as estatísticas",
    },
    "JavaMarket.Cpp.dll": {
        "<unresolved overloaded function type>": "<tipo de função sobrecarregada não resolvido>",
        "<brace-enclosed initializer list>": "<lista inicializadora entre chaves>",
        "terminate called after throwing an instance of '": "execução encerrada após lançar uma instância de '",
    },
    "JavaMarket.CSharp.dll": {
        "Attempted to divide by zero.": "Tentativa de divisão por zero.",
        "Arithmetic operation resulted in an overflow.": "A operação aritmética resultou em estouro (overflow).",
        "Value was either too large or too small for a Decimal.": "O valor era grande ou pequeno demais para um Decimal.",
        "Nullable object must have a value.": "O objeto anulável (Nullable) precisa ter um valor.",
        "Format specifier was invalid.": "O especificador de formato é inválido.",
        "conditional group": "grupo condicional",
        "parameters": "parâmetros",
        "parameter": "parâmetro",
    },
    "JavaMarket.Java.dll": {
        "Java exception": "Exceção Java",
        "No enum constant ": "Constante de enum inexistente: ",
        "For input string: \"": "Para a string de entrada: \"",
        " under radix {0}": " na base {0}",
        "Cannot parse null string: null": "Não é possível converter string nula: null",
        "greater than Character.MAX_RADIX": "maior que Character.MAX_RADIX",
        "less than Character.MIN_RADIX": "menor que Character.MIN_RADIX",
        "For input string: \"\" under radix {0}": "Para a string de entrada \"\" na base {0}",
        "For input string: \"\"": "Para a string de entrada: \"\"",
        "empty String": "String vazia",
        "unknown binary operator ": "operador binário desconhecido ",
        "Zero length BigInteger": "BigInteger de comprimento zero",
        "BigInteger divide by zero": "Divisão por zero em BigInteger",
        "BigInteger: modulus not positive": "BigInteger: módulo não positivo",
        "Negative exponent": "Expoente negativo",
        "Negative BigInteger": "BigInteger negativo",
        "BigInteger out of int range": "BigInteger fora do intervalo de int",
        "BigInteger out of long range": "BigInteger fora do intervalo de long",
        "Infinite or NaN": "Infinito ou NaN",
        "Rounding necessary": "Arredondamento necessário",
    },
    "JavaMarket.JavaScript.dll": {
        " method called on incompatible receiver ": " método chamado em receptor incompatível ",
        "Iterator result ": "Resultado do iterador ",
        " is not an object": " não é um objeto",
        "game: the game answered with ": "jogo: o jogo respondeu com ",
        " where a list was expected": " onde uma lista era esperada",
        "game: the game takes no lists back (JsHost.StoreList)": "jogo: o jogo não aceita listas de volta (JsHost.StoreList)",
        "Chaining cycle detected for promise #<Promise>": "Ciclo de encadeamento detectado na promise #<Promise>",
        "Maximum call stack size exceeded": "Tamanho máximo da pilha de chamadas excedido",
        "Class constructor ": "Construtor de classe ",
        " cannot be invoked without 'new'": " não pode ser invocado sem 'new'",
        "(intermediate value)": "(valor intermediário)",
        "Generator is already running": "O generator já está em execução",
        "Assignment to constant variable.": "Atribuição a variável constante.",
        "Cannot use 'in' operator to search for '": "Não é possível usar o operador 'in' para buscar '",
        "Super constructor may only be called once": "O construtor super só pode ser chamado uma vez",
        "Must call super constructor in derived class before accessing 'this' or returning from derived constructor": "É necessário chamar o construtor super na classe derivada antes de acessar 'this' ou retornar do construtor derivado",
        "Derived constructors may only return object or undefined": "Construtores derivados só podem retornar um objeto ou undefined",
        "Invalid string length": "Comprimento de string inválido",
        " is not a function": " não é uma função",
        " is not a constructor": " não é um construtor",
        "Cannot convert undefined or null to object": "Não é possível converter undefined ou null em objeto",
        "Cannot convert a BigInt value to a number": "Não é possível converter um valor BigInt em número",
        "Cannot mix BigInt and other types, use explicit conversions": "Não é possível misturar BigInt com outros tipos; use conversões explícitas",
        "Right-hand side of 'instanceof' is not callable": "O lado direito de 'instanceof' não é chamável",
        "Spread syntax requires ...iterable[Symbol.iterator] to be a function": "A sintaxe spread exige que ...iterable[Symbol.iterator] seja uma função",
        "This error originated either by throwing inside of an async function without a catch block, or by rejecting a promise which was not handled with .catch(). The promise rejected with the reason \"": "Este erro ocorreu ao lançar uma exceção dentro de uma função async sem bloco catch ou ao rejeitar uma promise não tratada com .catch(). A promise foi rejeitada com o motivo \"",
    },
    "JavaMarket.Python.dll": {
        ". Did you mean '": ". Você quis dizer '",
        "() takes exactly one argument (": "() recebe exatamente um argumento (",
        "() got an unexpected keyword argument '": "() recebeu um argumento nomeado inesperado '",
        " expected at least 1 argument, got 0": " esperava pelo menos 1 argumento, mas recebeu 0",
        "Cannot specify a default for ": "Não é possível especificar um valor padrão para ",
        "() with multiple positional arguments": "() com múltiplos argumentos posicionais",
        "() iterable argument is empty": "() recebeu um argumento iterável vazio",
        "sum() can't sum strings [use ''.join(seq) instead]": "sum() não soma strings [use ''.join(seq) em vez disso]",
        "super() takes at most 2 arguments (": "super() aceita no máximo 2 argumentos (",
        "super() argument 1 must be a type, not ": "o argumento 1 de super() deve ser um tipo, não ",
        "super(type, obj): obj (instance of ": "super(type, obj): obj (instância de ",
        ") is not an instance or subtype of type (": ") não é uma instância nem subtipo de (",
        " has no getter": " não possui getter",
        "'super' object has no attribute '": "o objeto 'super' não possui o atributo '",
        "type 'bool' is not an acceptable base type": "o tipo 'bool' não é um tipo base aceitável",
        "duplicate base class ": "classe base duplicada ",
        "type __qualname__ must be a str, not ": "__qualname__ do tipo deve ser str, não ",
        "Cannot create a consistent method resolution order (MRO) for bases ": "Não foi possível criar uma ordem de resolução de métodos (MRO) consistente para as bases ",
        "() takes from 1 to 2 positional arguments but ": "() aceita de 1 a 2 argumentos posicionais, mas ",
        " were given": " foram fornecidos",
        "slice indices must be integers or None or have an __index__ method": "os índices de slice devem ser inteiros, None ou possuir o método __index__",
    },
}
