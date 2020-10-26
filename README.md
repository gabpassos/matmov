# matmov - educaMat
Projeto back-end do Desafio Unisoma - 2020

Gabriel Passos - IMECC - UNICAMP

Flávia C. Gachet - FCA - UNICAMP

## Instalação
Oferecemos duas maneiras para instalar o program. A primeira delas é manual e requer uma pasta com os arquivos do pacote desenvolvido no local em que o programa será executado, além de instalação ou atualização manual de pacotes de terceiros (descritos na seção Pacotes e Versões). Observamos que houve uma
atualização da versão do *ortools*.

O pacote desenvolvido também foi disponibilizado no *PyPI* para fácil instalação e execução. Nesse caso, se você possuir o *pip* instalado, basta executar:
```sh
$ pip install matmov
```
Algumas outras possibilidades para instalação através do *pip*:
```sh
$ phyton -m pip install matmov
$ pip3 install matmov
$ python3 -m pip install matmov
```

Obs: a opção a ser usada pode depender de como o Python 3 está instalado no seu computador.

Com a instalação executada pelo *PyPI*, basta descompactar o arquivo `instalacaoPip.zip` e executar o arquivo `main.py` como sera indicado posteriormente.

Caso seja preferível não usar o *PyPI*, mas sim rodar diretamente com os arquivos *.py* desenvolvidos, os arquivos necessários foram encaminhados por e-mail e estão disponíveis no repositório: [https://github.com/gabpassos/matmov](https://github.com/gabpassos/matmov).

Para rodar com os arquivos do pacote na pasta, sem instalar pelo *PyPI*, basta descompactar o arquivo `instalacaoLocal.zip` e executar o arquivo `main.py` como sera indicado posteriormente.

## Executando o programa
O conteúdo da pasta em que o programa será executado depende do método de instalação utilizado, entretanto, os anexos enviados contemplam as duas possibilidades de forma que facilite o processo de execução e avaliação. Destacamos que tudo o que esta descrito aqui sera enviado em anexo e está também disponível no [repositório do GitHub](https://github.com/gabpassos/matmov)

No local de sua preferência para executar nosso código deve existir a pasta `data`. Deve haver também um arquivo `main.py` com um conteúdo apropriado (arquivo que executa os metodos do pacote desenvolvido). A pasta `data` possui os arquivos *SQLite database* com os casos de teste.

Se a instalação for feita pelo *PyPI*, basta editar a main da forma que for desejável e então executar o arquivo `main.py`. Caso seja preferível rodar com os arquivos diretamente, sem instalar pelo *PyPI*, deve haver uma terceira pasta, com nome `matmov` que contém os arquivos do pacote (enviada em anexo). Em seguida, basta editar a main da forma que for desejável e então executar o arquivo `main.py`.

## Estrutura da `main.py`

```python
import matmov as mm

#Para selecionar o arquivo, basta comentar as linhas de forma adequada:
#arquivo = 'cenario_2.db'
#arquivo = 'cenario_5.db'
arquivo = 'original.db'
#arquivo = 'original2020.db'
#arquivo = 'otimizaNoAno.db'
#arquivo = 'reduzirVerba.db'
#arquivo = 'juntaTurmaCont.db'
#arquivo = 'addQuartoAnoEM.db'

############################################
# - Solver padrao: CP-SAT (CBC tambem pode ser utilizado)
# - somenteTurmasObrig: variavel binaria que exibe ou nao os dados de turmas nao
#   ativas
database = 'data/' + arquivo
MatMov = mm.modelo(databasePath= database, somenteTurmasObrig= True)

MatMov.leituraDadosParametros()

MatMov.Solve()

MatMov.exportaSolucaoSQLite()

############################################
##  Opcional  ##
MatMov.estatisticaSolver()

MatMov.estatisticaProblema()

MatMov.analiseGrafica()
```
Ao comentar ou "descomentar" as linhas que definem a variável `arquivo`, seleciona-se
qual conjunto de dados será executado e resolvido.

Removendo as linhas com `MatMov.estatisticaSolver()`, `MatMov.estatisticaProblema()` e
`MatMov.analiseGrafica()`, as suas respectivas informações irão para de ser exibidas na
tela e as figuras não serão mais geradas ou atualizadas. Os demais metodos devem ser
executados.

### Resumo de instalação e execução
- Instalação pelo *PyPI*: instalar pelo *pip* e então extrair os arquivos de
`instalacaoPip.zip` e executar `main.py`.

- Instalação pelo local: extrair os arquivos de `instalacaoLocal.zip` e executar `main.py`.

## Um pouco sobre os cenários testados
Os cenários testados:
- `cenario_2.db`: cenario enviado pela UniSoma em preparação para fase final.
- `cenario_5.db`: cenario enviado pela UniSoma em preparação para fase final.
- `original.db`: arquivo original.
- `original2020.db`: encontramos uma inconsistência no ano de referência em alguns alunos de formulário. O aluno se inscreveu em 2020 mas o ano de referência é 2019. Os dados em `original2020.db` corrigem essa inconsistência.
- `otimizaNoAno.db`: considera resolucao do problema no ano de 2020
- `reduzirVerba.db`: verba reduzida para 15000
- `juntaTurmaCont.db`: remoção de alguns alunos de continuidade para ver se o método realmente junta turmas de continuidade quando possível.
- `addQuartoAnoEM.db`: adição do 4º ano do ensino médio.

Obs: todos os cenários consideram a remoção dos CPF's repetidos e todos (exceto o `original.db`) tratam da inconsistência do ano de referência.

## Pacotes e versões
O pacote foi desenvolvido em Python 3 e testado nas versões Python 3.7.2 64-bit e Python 3.8.2 64-bit. Assim, espera-se que o pacote não encontre problemas em versões maiores que 3.7 do Python 3. Seguem os principais pacotes externos do Python utilizados nessa primeira versão do programa:

| Pacote | Versão |
| ------ | ------ |
| *numpy* | 1.19.2 |
| *pandas* | 1.1.2 |
| *matplotlib* | 3.3.2 |
| *ortools* |  8.0.8283 |

Foram utilizados alguns pacotes da biblioteca *standard* do Python 3: *math, sqlite3, time, datetime, string, os* e *statistics*. Esses pacotes não necessitam de instalação pois acompanham diretamente a instalação do Python 3.

Obs 1: o ortools requer que a versão do Python 3 instalada seja de 64-bit.

Obs 2: as funções utilizadas da biblioteca *os* são independentes de sistema operacional.
