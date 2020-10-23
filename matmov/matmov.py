import sqlite3
import time

import pandas as pd
from ortools.linear_solver import pywraplp

from matmov import erros
from matmov import presolver as ps
from matmov import funcoesmod as fm
from matmov import funcoesmodopt as fmOpt
from matmov import resultados as res

class modelo:
    """
    ***  Modelo()   ***
    --------
    Parametros de entrada:
    ----------------------
    - databasePath: caminho ate o arquivo SQLite que armazena o problema. O padrao e 'data/database.db'
    - tipoSolver: qual solver do ortools sera utilizado. O padrao e 'CBC'. Para utilizar outros solvers, verificar documentacao do pywraplp.
    - tempoLimSolverSegundos: tempo de execucao limite do solver em segundos. O padra e 3600 s (1 hora).

    Variaveis:
    - databasePath: armazena o caminho ate o arquivo SQLite de entrada.
    - tabelaXYZ: armazena os dados da tabela XYZ do arquivo SQLite de entrada.
    - ordemUltimaSerie: armazena o maior valor 'ordem' de series ativas (ordem da ultima serie aberta).
    - custoBase: usto para abrir uma turma com um aluno.
    - parametros do problema: anoPlanejamento, otimizaNoAno, abreNovasTurmas, verba, custoAluno, custoProf, maxAlunos, qtdProfPedag, qtdProfAcd
    - tipoSolver: tipo do solver (recomenda-se por enquanto manter o padra 'CBC').
    - tempoLimiteSolver: tempo maximo de execucao do solver ortools.
    - aplicouSolver: True se o modelo foi resolvido, False caso contrario.
    - modelo: armazena o modelo (ortools) do problema.
    - status: status da solucao encontrada pelo solver ortools.
    - dadosParametrosConfigurados: True se os dados e parametros foram lidos.
    - tempoExecPreSolver: tempo de execucao do pre-solver.
    - tempoExecTotal: tempo total de execucao do metodo implementado.
    - x, y, p: aramzena as variaveis de decisao (ortools).

    Algumas estruturas importantes explicadas:
    ------------------------------------------
    listaTurmas: listaTurmas e um dicionario com diversos niveis. O primeiro deles, acessa os dados de uma escola. O segundo nivel
    acesso os dados de uma serie na escola selecionada no primeiro nivel. listaTurmas[escola][serie] e um dicionario contendo
    as chaves: 'turmas', 'alunosPossiveis', 'demanda' e 'aprova'. A chave 'turma' fornece uma lista com todas
    as turmas associadas ao par (escola,serie) selecionada. A chave 'aprova' e um dicionario que informa quais turmas
    associadas ao par (escola,serie) serao aprovadas ou nao. 'alunospossiveis' retorna um dicionario que contem
    listas de todos os alunos de continuidade e de formulario que podem se matricular nas turmas associadas ao par (escola,serie).
    Finalmente, a entrada 'demanda' fornece o total de alunos de formulario que desejam uma vaga nas turmas associadas ao par (escola,serie).

    alunoCont: para cada aluno de continuidade, armazena as turmas que esse aluno pode ser matriculado.

    alunoForm: para cada aluno de formulario, armazena as turmas que esse aluno pode ser matriculado.

    mesmaTurma: dado um par (i,j) de alunos de continuidade, mesmaTurma[i][j] = True se i estudo com j, e False caso contrario.
    Por viabilidade, definimos mesmaTurma[i][i] = False

    reprovou: para um aluno de continuidade, armazena se ele reprovou ou nao. Se otimizaNoAno, ninguem reprova.

    ordemForm: dado um par (k,l) de alunos de formulario inscritos numa mesma escola e numa mesma serie, ordemForm[k][l]=True
    se k vem antes de l no formulario, False caso contrario.


    Obs 1: optamos por implementar na forma de classe a fim de facilitar o entendimento do codigo.
    Como existem diversas variaveis, a organizacao em classe permite reduzir o numero de argumentos das funcoes,
    facilitando a leitura alem de evitar variaveis 'soltas', impedido conflitos de nomes e o bom entendimento
    do contexto em que cada variavel se aplica.

    Obs 2: tentamos deixar os nomes de funcoes e variaveis o mais expressiveis possivel a fim de evitar comentarios
    no meio do codigo. Tentamos explicar o objetivo de cada funcao de forma clara e o mais resumida possivel no inicio
    de cada funcao, evitando comentarios que atrapalhem a visualizacao.
    """

    def __init__(self, databasePath= 'data/database.db', tipoSolver= 'CBC', tempoLimSolverSegundos= 3600):
        #Arquivo de entrada
        self.databasePath = databasePath

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
        self.modelo = None
        self.status = None

        #Variaveis de decisao
        self.x = {}
        self.y = {}
        self.p = {}

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
        self.xSol = {}
        self.xSolTotalMatric = 0

        self.ySol = {}
        self.ySolTotalMatric = 0

        self.pSol = {}
        self.pSolTotalAbertas = 0

    def leituraDadosParametros(self):
        '''
        LEITURA DE DADOS E PARAMETROS
        -----------------------------

        - Realiza a leitura de dados a partir das tabelas SQLite e os armazena no formato de pandas.DataFrame.
        - Configura os parametros do modelo.

        Obs: Verifica erros de CPF repetido e se existe alguma turma de continuidade com mais matriculados
        que o permitido.
        '''
        database = sqlite3.connect(self.databasePath)

        ##  Dados  ##
        self.tabelaRegiao = pd.read_sql_query('SELECT * FROM regiao', database, index_col= 'id')
        self.tabelaEscola = pd.read_sql_query('SELECT * FROM escola', database, index_col= 'id')
        self.tabelaTurma = pd.read_sql_query('SELECT * FROM turma', database, index_col= 'id')
        self.tabelaSerie = pd.read_sql_query('SELECT * FROM serie', database, index_col= 'id')
        self.tabelaAlunoCont = pd.read_sql_query('SELECT * FROM aluno', database, index_col= 'id')
        self.tabelaAlunoForm = pd.read_sql_query('SELECT * FROM formulario_inscricao', database, index_col= 'id')

        ##  Parametros - OBS: coluna valor da tabela parametro esta como VARCHAR (por isso a conversao para int) ##
        parametros = pd.read_sql_query('SELECT * FROM parametro', database, index_col= 'id')
        self.anoPlanejamento = int(parametros['valor'][1])
        self.otimizaNoAno = int(parametros['valor'][2])
        self.abreNovasTurmas = int(parametros['valor'][3])
        self.verba = int(parametros['valor'][4])
        self.custoAluno = int(parametros['valor'][5])
        self.custoProf = int(parametros['valor'][6])
        self.maxAlunos = int(parametros['valor'][7])
        self.qtdProfPedag = int(parametros['valor'][8])
        self.qtdProfAcd = int(parametros['valor'][9])

        database.close()

        ultimaSerie_id = self.tabelaSerie[(self.tabelaSerie['ativa'] == 1)]['ordem'].idxmax()
        self.ordemUltimaSerie = self.tabelaSerie['ordem'][ultimaSerie_id]

        self.custoBase = self.custoAluno + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)

        erros.verificaCpfRepetido(self.tabelaAlunoCont, self.tabelaAlunoForm)
        erros.verificaTurmasContinuidade(self)

        self.dadosParametrosConfigurados = True

    def Solve(self):
        """
        SOLVER
        ------
        Solver escolhido para solucionar o problema de alocacao de alunos da ONG. Aqui, considera-se TODAS
        as restricoes impostas pela ONG e a priorizacao de turmas novas por demanda solicitada. Esse metodo
        e dividido em tres Etapas.
        - Etapa 1: aloca primeiro os alunos de continuidade, sem se preocupar com alunos de formulario.
        - Etapa 2: completa com alunos de formulario as turmas abertas para alunos de continuidade na Etapa 1.
        - Etapa 3: libera algumas turmas por vez, de forma a atender o criterio de demanda.

        Implementacao
        -------------
        Foram implementadas algumas estruturas auxiliares:
        - alunoTurmaCont: lista que armazena a tupla (i,t) se o aluno de continuidade i esta matriculado na turma t.
        - turmasAbertas: lista que armazena a tupla (k,t) se o aluno de formulario k esta matriculado na turma t.
        - turmasFechadas: armazena as turmas que devem ser fechadas (utilizada para para gerar as restricoes adicionais).
        - turmasPermitidas: armaze as turmas que podem ou nao ser abertas (sao as turmas extraida pela ordem de prioridade).
        - demanda: armazena a demanda de uma serie 's' na escola 'e'.
        - demandaOrdenada: o mesmo que demanda, mas com os dados ordenados da maior para a menor demanda.
        - desempateEscola: armazena o total de alunos matriculados e o total de turmas abertas numa determinada escola.

        Obs: como os erros tratados aqui garantem que a distribuicao de alunos de continuidade esteja bem definida,
        se a Etapa 1 resultar em um modelo infactivel, isso e sinal de que a verba disponibilizada nao e suficiente
        para atender os alunos de continuidade.
        """
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

        t_i = time.time()
        self.tempoExecPreSolver = ps.preSolver(self)

        self.modelo = pywraplp.Solver.CreateSolver('MatMov_Solver', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        ##########################################################
        #####  PRIMEIRA ETAPA (aloca alunos de continuidade) #####
        ##########################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.addRestricoesEtapaContinuidade(self)

        ##  Funcao Objetivo  ##
        fm.objMinSomaTurmas(self)

        ## Resolve para alunos de continuidade  ##
        self.status = self.modelo.Solve()

        if self.status == pywraplp.Solver.INFEASIBLE:
            raise erros.ErroVerbaInsufParaContinuidade()

        #####  PREPARA PARA SEGUNDA ETAPA  #####
        alunoTurmaCont, turmasAbertas, turmasFechadas, desempateEscola = fm.armazenaSolContInicTurmasAbertasFechadas(self)
        self.modelo.Clear()

        ###############################################################
        #####  SEGUNDA ETAPA (preenche com alunos de formulario)  #####
        ###############################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelAlunoForm_y(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.addRestricoesModeloBase(self)
        fm.addRestricoesAdicionaisEtapa2(self, alunoTurmaCont, turmasFechadas)

        ##  Funcao Objetivo  ##
        fm.objMaxSomaAlunosForm(self)

        ##  Resolve completando as turmas de alunos de continuidade  ##
        self.status = self.modelo.Solve()

        ### PREPARA PARA TERCEIRA ETAPA  ###
        demandaOrdenada, alunoTurmaForm = fm.iniciaDemandaOrdenadaAlunoTurmaForm(self, desempateEscola)
        turmasPermitidas = fm.avaliaTurmasPermitidas(self, turmasFechadas, demandaOrdenada, desempateEscola)

        ################################################################################################
        #####  TERCEIRA ETAPA (abre turmas novas priorizando a demanda com criterio de desempate)  #####
        ################################################################################################
        while not turmasPermitidas is None:
            self.modelo.Clear()

            ##  Variaveis  ##
            fm.defineVariavelAlunoCont_x(self)
            fm.defineVariavelAlunoForm_y(self)
            fm.defineVariavelTurma_p(self)

            ##  Restricoes  ##
            fm.addRestricoesModeloBase(self) #Restricoes modelo padrao
            fm.addRestricoesAdicionaisEtapa3(self, alunoTurmaCont, alunoTurmaForm, turmasFechadas)

            ##  Funcao Objetivo  ##
            fm.objMaxSomaAlunosForm(self)

            ## Resolve ##
            self.status = self.modelo.Solve()

            demandaOrdenada = fm.atualizaDadosTurmas(self, alunoTurmaForm, turmasAbertas, turmasPermitidas,
                                                     turmasFechadas, demandaOrdenada, desempateEscola)

            turmasPermitidas = fm.avaliaTurmasPermitidas(self, turmasFechadas,
                                                         demandaOrdenada, desempateEscola)

        t_f = time.time()
        self.tempoExecTotal = t_f - t_i

        self.aplicouSolver = True

    def SolveOpt(self):
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

        t_i = time.time()
        self.tempoExecPreSolver = ps.preSolver(self)

        self.modelo = pywraplp.Solver.CreateSolver('MatMov_Solver', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        if True: ##Existem alunos de continuidade
            ############################
            #####  PRIMEIRA ETAPA  #####
            ############################
            fmOpt.addVariaveisDecisaoEtapa1(self)
            fmOpt.addRestricoesEtapa1(self)
            fmOpt.addObjetivoMinTurmas(self)

            self.modelo.Solve()
            fmOpt.armazenaSolucaoEtapa1(self)

            self.modelo.Clear()
            fmOpt.limpaModelo(self)

            ###########################
            #####  SEGUNDA ETAPA  #####
            ###########################
            Tc, vagasTc, verbaDisp = fmOpt.preparaEtapa2(self)
            if verbaDisp < 0:
                erros.ErroVerbaInsufParaContinuidadeNOVO(abs(verbaDisp))

            if verbaDisp >= self.custoBase:
                fmOpt.addVariaveisDecisaoEtapa2(self, Tc)
                fmOpt.addRestricoesEtapa2(self, Tc, vagasTc, verbaDisp)
                fmOpt.addObjetivoMaxAlunosForm(self)

                self.modelo.Solve()
                fmOpt.armazenaSolucaoEtapa2(self)

                self.modelo.Clear()
                fmOpt.limpaModelo(self)

        ############################
        #####  TERCEIRA ETAPA  #####
        ############################
        demandaOrdenada, desempateEscola = fmOpt.preparaEtapa3(self)
        turmasPermitidas, verbaDisp = fmOpt.avaliaTurmasPermitidas(self, demandaOrdenada,
                                                                   desempateEscola)

        while not turmasPermitidas is None:
            fmOpt.addVariaveisDecisaoEtapa3(self, turmasPermitidas)
            fmOpt.addRestricoesEtapa3(self, turmasPermitidas, verbaDisp)
            fmOpt.addObjetivoMaxAlunosFormEtapa3(self, turmasPermitidas)

            self.modelo.Solve()
            fmOpt.armazenaSolucaoEtapa3(self, turmasPermitidas)

            demandaOrdenada, desempateEscola = fmOpt.atualizaDemandaOrdenadaDesempate(
                                    self, turmasPermitidas,
                                    demandaOrdenada, desempateEscola
                                    )

            turmasPermitidas, verbaDisp = fmOpt.avaliaTurmasPermitidas(
                                    self, demandaOrdenada, desempateEscola
                                    )

            self.modelo.Clear()
            fmOpt.limpaModelo(self)

        t_f = time.time()
        self.tempoExecTotal = t_f - t_i

        fmOpt.reorganizaSol(self)
        self.aplicouSolver = True

    def estatisticaProblema(self):
        """
        ESTATISTICAS DO PROBLEMA
        ------------------------
        Apresenta algumas das principais estatisticas da distribuicao de turmas e alunos da solucao final.
        O proposito principal dessas estatisticas e avaliar a qualidade da solucao encontrada, mas tambem
        auxilia a ONG a analisar a viabilidade da solucao.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        totalAtendidoCont= res.matriculasCont(self)
        totalAlunosForm, totalAtendidoForm, fracForm = res.matriculasForm(self)
        totalAlunosAtend = totalAtendidoCont + totalAtendidoForm

        qtdTurmasAbertas = res.qtdTurmasAbertas(self)
        mediaAlunosPorTurma, dpPorTurma, qtdMenorTurma, qtdMaiorTurma, qtdCompletas, qtdIncompletas = res.estatisticasBasicasTurma(self)
        verbaTotal, verbaUtilizada, verbaRestante = res.estatisticasVerba(self, totalAlunosAtend, qtdTurmasAbertas)

        res.printbox('ESTATISTICAS DO PROBLEMA')
        print('~~~~~  ALUNOS  ~~~~~')
        print('Dados gerais (continuidade e formulario):')
        print('- Alunos atendidos:', totalAlunosAtend)

        print('\nAlunos de Continuidade:')
        print('- Atendidos:', totalAtendidoCont)

        print('\nAlunos de Formulario:')
        print('- Total:', totalAlunosForm)
        print('- Atendidos:', totalAtendidoForm)
        print('- Fracao de alunos atendidos:', fracForm)

        print('\n~~~~~  TURMAS  ~~~~~')
        print('Quantidade de turmas:')
        print('- Total de turmas abertas:', qtdTurmasAbertas)
        print('- Turmas completas:', qtdCompletas)
        print('- Turmas incompletas:', qtdIncompletas)

        print('\nDistribuicao de alunos nas turmas:')
        print('- Media de alunos por turma:', mediaAlunosPorTurma)
        print('- Desvio padrao da distribuicao de alunos:', dpPorTurma)
        print('- Qtd de alunos na menor turma:', qtdMenorTurma)
        print('- Qtd de alunos na maior turma:', qtdMaiorTurma)

        print('\n~~~~~  VERBA  ~~~~~')
        print('- Verba disponibilizada:', verbaTotal)
        print('- Verba utilizada:', verbaUtilizada)
        print('- Verba restante:', verbaRestante)

    def estatisticaSolver(self):
        """
        ESTATISTICAS DO SOLVER
        ----------------------
        Apresenta algumas das principais estatisticas associadas ao metodo utilizado:
        - Tipo de solucao (otima, factivel ou infactivel) do ultimo modelo executado.
        - Valor da funcao objetivo da ultima solucao encontrada.
        - Numero de variaveis de decisao e de restricoes do ultimo modelo executado.
        - Tempos de execucao do metodo(total, pre-solver, solver ortools)
        Obs 1: os tempos de execucao sao medidos em segundos.

        Obs 2: o tempo de execucao do solver ortools representa o tempo total de uso, isto e, se
        mais de um modelo linear foi solucionado, o tempo de execucao representa a soma dos tempos
        para cada modelo.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        obj = self.modelo.Objective()
        res.printbox('DADOS DE EXECUCAO')

        print('Dados do ultimo modelo solucionado:')
        if self.status == pywraplp.Solver.OPTIMAL:
            print('- Solucao: otima.')
        elif self.status == pywraplp.Solver.FEASIBLE:
            print('- Solucao: factivel.')
        elif self.status == pywraplp.Solver.INFEASIBLE:
            print('- Solucao: infactivel.')

        print('- Valor objetivo:', obj.Value())

        print('- Numero de variaveis:', self.modelo.NumVariables())
        print('- Numero de restricoes:', self.modelo.NumConstraints())

        ##Tempo de execucao
        print('\nTempos de execucao (s):')
        print('- Total: {:.4f}'.format(self.tempoExecTotal))
        print('- Pre-solver: {:.4f}'.format(self.tempoExecPreSolver))
        print('- Solver ortools: {:.4f}'.format(self.modelo.WallTime()*(10**(-3))))

    def analiseGrafica(self):
        """
        ANALISE GRAFICA
        ---------------
        Gera alguns graficos de barras que representam a solucao obtido.

        Distribuicao de alunos por escola: gera um grafico de barras, onde as barras estao associadas a escola. Cada escola
        possui tres barras, uma para alunos de formulario, outra para alunos de continuidade e finalmente, uma que representa
        o total de alunos na escola.

        Distribuicao de alunos por turma: gera um grafico para cada escola, e cada grafico contem barras associadas a cada
        turma da escola. Uma barra que representa o total de alunos na turma, uma que representa o total de alunos de formulario
        na turma e outra para o total de alunos de continuidade.

        Distribuicao de turmas por escola: gera uma grafico para cada escola e cada barra representa o total de turmas de
        uma determinada serie abertas na escola.

        Obs: para uso da ferramenta de analise, tenha uma pasta com nome 'fig' no diretorio em que o codigo esta sendo
        executado. As figuras geradas serao gravadas no formato '.jpg' dentro da pasta fig.
        """
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        res.grafDistAlunosPorEscola(self)
        res.grafDistAlunosPorTurma(self)
        res.grafDistTurmasPorEscola(self)

    def exportaSolucaoSQLite(self):
        if not self.aplicouSolver:
            raise erros.ErroFalhaAoExibirResultados()

        database = sqlite3.connect(self.databasePath)
        c = database.cursor()

        identTurma = res.geraIdentTurma(self, self.tabelaSerie, self.tabelaEscola,
                                        self.tabelaRegiao)

        res.attTabelaSolucao_sol_aluno(self, c, identTurma)
        res.attTabelaSolucao_sol_priorizacao_formulario(self, c, identTurma)
        res.attTabelaSolucao_sol_turma(self, c, identTurma)

        database.commit()
        database.close()
