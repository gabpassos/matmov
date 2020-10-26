import sqlite3
import time
import os

import pandas as pd
from ortools.linear_solver import pywraplp

from matmov import erros
from matmov import presolver as ps
from matmov import funcoesmod as fm
from matmov import resultados as res

class modelo:
    """
    Modelo()
    --------
    Parametros de entrada:
    ----------------------
    - databasePath: caminho ate o arquivo SQLite que armazena o problema.
      O padrao e 'data/database.db'
    - tipoSolver: qual solver do ortools sera utilizado. O padrao e ```CP-SAT``` (prog.
      linear inteira). Para utilizar outros solvers, verificar documentacao do pywraplp.
    - tempoLimSolverSegundos: tempo de execucao limite do solver em segundos. O padrao e 3600 s (1 hora).
    - somenteTurmasObrig: se desejar exibir resultados somente das turmas atives,
      use ```somenteTurmasObrig = True```

    Variaveis:
    - databasePath: armazena o caminho ate o arquivo SQLite de entrada.
    - tabelaXYZ: armazena os dados da tabela XYZ do arquivo SQLite de entrada.
    - ordemUltimaSerie: armazena o maior valor 'ordem' de series ativas (ordem da ultima serie aberta).
    - custoBase: usto para abrir uma turma com um aluno.
    - parametros do problema: anoPlanejamento, otimizaNoAno, abreNovasTurmas,
      verba, custoAluno, custoProf, maxAlunos, qtdProfPedag, qtdProfAcd
    - tipoSolver: tipo do solver. Usou-se o solver ```CP-SAT``` pois ele e especifico
      para prog. linear inteira.
    - tempoLimiteSolver: tempo maximo de execucao do solver ortools.
    - aplicouSolver: True se o modelo foi resolvido, False caso contrario.
    - modelo: armazena o modelo (ortools) do problema.
    - status: status da solucao encontrada pelo solver ortools.
    - dadosParametrosConfigurados: True se os dados e parametros foram lidos.
    - tempoExecPreSolver: tempo de execucao do pre-solver.
    - tempoExecTotal: tempo total de execucao do metodo implementado.
    - x, y, p: armazena os resultados de cada etapa.
    - xSoma, ySoma, pSoma: armazena as somas dos valores de x, y e p respectivamente.

    Algumas estruturas importantes explicadas:
    ------------------------------------------
    - listaTurmas: listaTurmas e um dicionario com diversos niveis. O primeiro deles,
      acessa os dados de uma escola. O segundo nivel acesso os dados de uma serie na escola
      selecionada no primeiro nivel. listaTurmas[escola][serie] e um dicionario contendo
      as chaves: 'turmas', 'alunosPossiveis', 'demanda' e 'aprova'. A chave 'turma'
      fornece uma lista com todas as turmas associadas ao par (escola,serie) selecionada.
      A chave 'aprova' e um dicionario que informa quais turmas associadas ao par
      (escola,serie) serao aprovadas ou nao. 'alunospossiveis' retorna um dicionario que
      contem listas de todos os alunos de continuidade e de formulario que podem se
      matricular nas turmas associadas ao par (escola,serie). Finalmente, a entrada
      'demanda' fornece o total de alunos de formulario que desejam uma vaga nas turmas
      associadas ao par (escola,serie).

    - alunoCont: para cada aluno de continuidade, armazena as turmas que esse aluno pode
      ser matriculado.

    - alunoForm: para cada aluno de formulario, armazena as turmas que esse aluno pode
      ser matriculado.

    - mesmaTurma: dado um par (i,j) de alunos de continuidade, mesmaTurma[i][j] = True
      se i estudo com j, e False caso contrario. Por viabilidade, definimos
      mesmaTurma[i][i] = False

    - reprovou: para um aluno de continuidade, armazena se ele reprovou ou nao.
      Se otimizaNoAno, ninguem reprova.

    - ordemForm: dado um par (k,l) de alunos de formulario inscritos numa mesma escola
    e numa mesma serie, ordemForm[k][l]=True se k vem antes de l no formulario,
    False caso contrario.


    Obs 1: optamos por implementar na forma de classe a fim de facilitar o entendimento
    do codigo. Como existem diversas variaveis, a organizacao em classe permite reduzir
    o numero de argumentos das funcoes, facilitando a leitura alem de evitar variaveis
    'soltas', impedido conflitos de nomes e o bom entendimento do contexto em que cada
    variavel se aplica.

    Obs 2: tentamos deixar os nomes de funcoes e variaveis o mais expressiveis possivel
    a fim de evitar comentarios no meio do codigo. Tentamos explicar o objetivo de cada
    funcao de forma clara e o mais resumida possivel no inicio de cada funcao, evitando
    comentarios que atrapalhem a visualizacao.
    """

    def __init__(self, databasePath= 'data/database.db', somenteTurmasObrig = True,
                 tipoSolver= 'CBC', tempoLimSolverSegundos= 3600):
        #Arquivo de entrada
        self.databasePath = databasePath
        self.somenteTurmasObrig = somenteTurmasObrig

        #Dados do problema
        self.tabelaRegiao = None
        self.tabelaEscola = None
        self.tabelaTurma = None
        self.tabelaSerie = None
        self.tabelaAlunoCont = None
        self.tabelaAlunoForm = None

        self.ordemUltimaSerie = None
        self.custoBase = None

        #Parametros do problema
        self.anoPlanejamento = None
        self.otimizaNoAno = None
        self.abreNovasTurmas = None
        self.verba = None
        self.custoAluno = None
        self.custoProf = None
        self.maxAlunos = None
        self.qtdProfPedag = None
        self.qtdProfAcd = None

        self.dadosParametrosConfigurados = False

        #Config. Solver
        self.tipoSolver = tipoSolver
        self.tempoLimiteSolver = tempoLimSolverSegundos
        self.aplicouSolver = False

        #Variaveis Solver ortools
        self.solver = None
        self.status = None
        self.tempoSolverCPLEX = 0

        #Variaveis Auxiliares para Solver (definidas no pre-solver)
        self.listaTurmas = {}
        self.alunoCont = {}
        self.alunoForm = {}
        self.mesmaTurma = {}
        self.reprovou = {}
        self.ordemForm = {}

        #Estatiscas do metodo
        self.tempoExecPreSolver = None
        self.tempoExecTotal = None

        #Armazena solucoes
        self.x = {}
        self.xSoma = 0

        self.y = {}
        self.ySoma = 0

        self.p = {}
        self.pSoma = 0

        self.erroVerba = False
        self.verbaFalta = 0

    def leituraDadosParametros(self):
        '''
        LEITURA DE DADOS E PARAMETROS
        -----------------------------

        - Realiza a leitura de dados a partir das tabelas SQLite e os armazena no
          formato de pandas.DataFrame.
        - Configura os parametros do modelo.

        Obs: Verifica erros de CPF repetido e se existe alguma turma de continuidade
        com mais matriculados que o permitido.
        '''
        database = sqlite3.connect(self.databasePath)

        ##  Dados  ##
        self.tabelaRegiao = pd.read_sql_query('SELECT * FROM regiao',
                                               database, index_col= 'id')

        self.tabelaEscola = pd.read_sql_query('SELECT * FROM escola',
                                               database, index_col= 'id')

        self.tabelaTurma = pd.read_sql_query('SELECT * FROM turma',
                                              database, index_col= 'id')

        self.tabelaSerie = pd.read_sql_query('SELECT * FROM serie',
                                              database, index_col= 'id')

        self.tabelaAlunoCont = pd.read_sql_query('SELECT * FROM aluno',
                                                  database, index_col= 'id')

        self.tabelaAlunoForm = pd.read_sql_query('SELECT * FROM formulario_inscricao',
                                                  database, index_col= 'id')

        ##  Parametros - OBS: coluna valor da tabela parametro esta como VARCHAR  ##
        parametros = pd.read_sql_query('SELECT * FROM parametro',
                                        database, index_col= 'chave')

        self.anoPlanejamento = int(parametros['valor']['ano_planejamento'])
        self.otimizaNoAno = int(parametros['valor']['otimiza_dentro_do_ano'])
        self.abreNovasTurmas = int(parametros['valor']['possibilita_abertura_novas_turmas'])
        self.verba = int(parametros['valor']['limite_custo'])
        self.custoAluno = int(parametros['valor']['custo_aluno'])
        self.custoProf = int(parametros['valor']['custo_professor'])
        self.maxAlunos = int(parametros['valor']['qtd_max_alunos'])
        self.qtdProfPedag = int(parametros['valor']['qtd_professores_pedagogico'])
        self.qtdProfAcd = int(parametros['valor']['qtd_professores_acd'])

        database.close()

        ultimaSerie_id = self.tabelaSerie[(self.tabelaSerie['ativa'] == 1)]['ordem'].idxmax()
        self.ordemUltimaSerie = self.tabelaSerie['ordem'][ultimaSerie_id]

        self.custoBase = (self.custoAluno
                         + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd))

        erros.verificaCpfRepetido(self.tabelaAlunoCont, self.tabelaAlunoForm)
        erros.verificaTurmasContinuidade(self)

        self.dadosParametrosConfigurados = True

    def Solve(self):
        """
        SOLVER
        ------
        Solver escolhido para solucionar o problema de alocacao de alunos da ONG.
        Aqui, considera-se todas as restricoes impostas pela ONG e a priorizacao de
        turmas novas por demanda solicitada. Esse metodo e dividido em tres Etapas.
        - Etapa 1: aloca primeiro os alunos de continuidade, sem se preocupar com alunos
          de formulario.
        - Etapa 2: completa com alunos de formulario as turmas abertas para alunos de
          continuidade na Etapa 1.
        - Etapa 3: libera algumas turmas por vez, de forma a atender o criterio
          de demanda.

        Implementacao
        -------------
        Foram implementadas algumas estruturas auxiliares:
        - Tc: armazena as turmas de continuidade determinadas na etapa 1
        - turmasPermitidas: armaze as turmas que podem ou nao ser abertas
          (sao as turmas extraida pela ordem de prioridade).
        - demandaOrdenada: o mesmo que demanda, mas com os dados ordenados da maior
          para a menor demanda.
        - desempateEscola: armazena o total de alunos matriculados e o total de turmas
          abertas numa determinada escola.
        - vagasTc: vagas disponiveis em cada turma de continuidade.
        - verbaDisp: verba disponivel para ser utilizada apos execucao de uma etapa.
        """
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

        x = {}
        y = {}
        p = {}

        t_i = time.time()
        self.tempoExecPreSolver = ps.preSolver(self)

        self.solver = pywraplp.Solver.CreateSolver(self.tipoSolver)
        self.solver.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        totalAlunosCont = len(self.alunoCont)
        if totalAlunosCont > 0:
            ############################
            #####  PRIMEIRA ETAPA  #####
            ############################
            fm.addVariaveisDecisaoEtapa1(self, x, p)
            fm.addRestricoesEtapa1(self, x, p)
            fm.addObjetivoMinTurmas(self, p)

            self.solver.Solve()
            fm.armazenaSolucaoEtapa1(self, x, p)

            x, y, p = fm.limpaModelo(self)

            ###########################
            #####  SEGUNDA ETAPA  #####
            ###########################
            Tc, vagasTc, verbaDisp = fm.preparaEtapa2(self)
            if verbaDisp < 0:
                self.erroVerba = True
                self.verbaFalta = abs(verbaDisp)
            else:
                if verbaDisp >= self.custoBase:
                    fm.addVariaveisDecisaoEtapa2(self, y, Tc)
                    fm.addRestricoesEtapa2(self, y, Tc, vagasTc, verbaDisp)
                    fm.addObjetivoMaxAlunosForm(self, y)

                    self.solver.Solve()
                    fm.armazenaSolucaoEtapa2(self, y)

                    x, y, p = fm.limpaModelo(self)

        ############################
        #####  TERCEIRA ETAPA  #####
        ############################
        demandaOrdenada, desempateEscola = fm.preparaEtapa3(self)
        turmasPermitidas, verbaDisp = fm.avaliaTurmasPermitidas(self, demandaOrdenada,
                                                                   desempateEscola)

        while not turmasPermitidas is None:
            fm.addVariaveisDecisaoEtapa3(self, y, p, turmasPermitidas)
            fm.addRestricoesEtapa3(self, y, p, turmasPermitidas, verbaDisp)
            fm.addObjetivoMaxAlunosFormEtapa3(self, y, turmasPermitidas)

            self.solver.Solve()

            fm.armazenaSolucaoEtapa3(self, y, p, turmasPermitidas)

            demandaOrdenada, desempateEscola = fm.atualizaDemandaOrdenadaDesempate(
                                    self, y, p, turmasPermitidas,
                                    demandaOrdenada, desempateEscola
                                    )

            turmasPermitidas, verbaDisp = fm.avaliaTurmasPermitidas(
                                    self, demandaOrdenada, desempateEscola
                                    )

            x, y, p = fm.limpaModelo(self)

        t_f = time.time()
        self.tempoExecTotal = t_f - t_i

        self.aplicouSolver = True
        self.tempoSolverCPLEX = self.solver.WallTime()
        self.solver = None

        res.reorganizaVariaveisDecisao(self)

    def estatisticaProblema(self):
        """
        ESTATISTICAS DO PROBLEMA
        ------------------------
        Apresenta algumas das principais estatisticas da distribuicao de turmas e
        alunos da solucao final.

        O proposito principal dessas estatisticas e avaliar a qualidade da solucao
        geral encontrada, dessa forma, serao exibidos os dados de toda a solucao
        encontrada, inclusive das turmas que nao estao ativas obrigatoriamente.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        (mediaAlunosPorTurma, qtdMenorTurma, qtdMaiorTurma,
         qtdCompletas, qtdIncompletas)   =   res.estatisticasBasicasTurma(self)


        usoVerba = fm.verbaUtilizada(self)

        res.printbox('ESTATISTICAS DO PROBLEMA')
        print('~~~~~  ALUNOS  ~~~~~')
        print('\nAlunos de Continuidade:')
        print('- Atendidos:', self.xSoma)

        if len(self.tabelaAlunoForm.index) > 0:
            print('\nAlunos de Formulario:')
            print('- Total:', len(self.tabelaAlunoForm.index))
            print('- Atendidos:', self.ySoma)
            print('- Percentual atendido:', self.ySoma/len(self.tabelaAlunoForm.index))

        print('Dados gerais (continuidade e formulario):')
        print('- Alunos atendidos:', self.xSoma + self.ySoma)

        print('\n~~~~~  TURMAS  ~~~~~')
        print('Quantidade de turmas:')
        print('- Total de turmas abertas:', self.pSoma)
        print('- Turmas completas:', qtdCompletas)
        print('- Turmas incompletas:', qtdIncompletas)

        print('\nDistribuicao de alunos nas turmas:')
        print('- Media de alunos por turma:', mediaAlunosPorTurma)
        print('- Qtd de alunos na menor turma:', qtdMenorTurma)
        print('- Qtd de alunos na maior turma:', qtdMaiorTurma)

        print('\n~~~~~  VERBA  ~~~~~')
        print('- Verba disponibilizada:', self.verba)
        print('- Verba utilizada:', usoVerba)
        print('- Verba restante:', self.verba - usoVerba)

    def estatisticaSolver(self):
        """
        ESTATISTICAS DO SOLVER
        ----------------------
        Apresenta os tempos de execucao de cada etapa da otimizacao.

        Obs 1: os tempos de execucao sao medidos em segundos.

        Obs 2: o tempo de execucao do solver ortools representa o tempo total de uso,
        isto e, se mais de um modelo linear foi solucionado, o tempo de execucao
        representa a soma dos tempos para cada modelo.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        res.printbox('TEMPO DE EXECUCAO (s)')
        print('- Total: {:.4f}'.format(self.tempoExecTotal))
        print('- Pre-solver: {:.4f}'.format(self.tempoExecPreSolver))
        print('- Solver ortools: {:.4f}'.format(self.tempoSolverCPLEX*(10**(-3))))

    def analiseGrafica(self):
        """
        ANALISE GRAFICA
        ---------------
        Gera alguns graficos de barras que representam a solucao obtido.

        - Distribuicao de alunos por escola: gera um grafico de barras, onde as barras
          estao associadas a escola. Cada escola possui tres barras, uma para alunos de
          formulario, outra para alunos de continuidade e finalmente, uma que representa
          o total de alunos na escola.

        - Distribuicao de alunos por turma: gera um grafico para cada escola, e cada
          grafico contem barras associadas a cada turma da escola. Uma barra que
          representa o total de alunos na turma, uma que representa o total de alunos de
          formulario na turma e outra para o total de alunos de continuidade.

        - Distribuicao de turmas por escola: gera uma grafico para cada escola e cada
          barra representa o total de turmas de uma determinada serie abertas na escola.

        Obs ': para uso da ferramenta de analise grafica, a existencia da pasta 'fig' no
        diretorio em que o codigo esta sendo executado nao e mais necessaria. Se a pasta
        'fig' nao existir, o programa ira criar.

        Obs 2: as figuras geradas serao gravadas no formato '.jpg'.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        figPath = 'fig'
        if not os.path.exists(figPath):
            os.mkdir(figPath)

        identTurma = res.geraIdentTurma(self, self.tabelaSerie, self.tabelaEscola,
                                        self.tabelaRegiao)

        res.grafDistAlunosPorEscola(self)
        res.grafDistAlunosPorTurma(self, identTurma)
        res.grafDistTurmasPorEscola(self)

    def exportaSolucaoSQLite(self):
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        database = sqlite3.connect(self.databasePath)
        c = database.cursor()

        identTurma = res.geraIdentTurma(self, self.tabelaSerie, self.tabelaEscola,
                                        self.tabelaRegiao)

        ##  Atualiza tabelas de solucao
        res.attTabelaSolucao_sol_aluno(self, c, identTurma)
        res.attTabelaSolucao_sol_priorizacao_formulario(self, c, identTurma)
        res.attTabelaSolucao_sol_turma(self, c, identTurma)

        ##  Atualiza tabelas auxiliares
        colunaTurmas = res.criaColunasTurmas(self)
        res.tabelaDistribuicaoAlunos(self, c, identTurma)
        res.tabelaDistribuicaoTurmas(self, c, colunaTurmas)
        res.tabelaDistribuicaoGeral(self, c, colunaTurmas)

        database.commit()
        database.close()

        if self.erroVerba:
            msg = ('AVISO!!! Os alunos de continuidade foram alocados excedendo '
                   'a verba disponilizada em {}. Nenhum aluno de formulario '
                   'foi alocado por falta de verba.'
                  ).format(self.verbaFalta)

            print(msg)
            #raise erros.ErroVerbaInsufParaContinuidade(self.verbaFalta)
