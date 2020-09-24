import sqlite3
from string import ascii_uppercase
import pandas as pd
from ortools.linear_solver import pywraplp


import preSolver as ps
import funcoesModelagem as fm

class ErroLeituraDados(Exception):
    def __str__(self):
        return 'A leitura de dados não foi realizada. Execute Modelo.leituraDados() antes de executar o solver.'

class ErroConfiguracaoParametros(Exception):
    def __str__(self):
        return 'A configuração de parâmetros não foi realizada. Execute Modelo.configuraParametros() antes de executar o solver.'

def geraNomeTurma(regiao_id, serie_id, contadorTurmas, tabelaSerie, tabelaEscola, tabelaRegiao):
    regiao = tabelaRegiao['nome'][regiao_id]
    serie = tabelaSerie['nome'][serie_id][0]
    turma = ascii_uppercase[contadorTurmas[regiao_id][serie_id]]

    return regiao + '_' + serie + turma

class Modelo():
    """Classe modelo para o problema da ONG Matematica em Movimento."""

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

        self.dadosAdicionados = False

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

        self.parametrosConfigurados = False

        #Config. Solver
        self.tipoSolver = tipoSolver
        self.tempoLimiteSolver = tempoLimSolverSegundos

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

    def leituraDados(self):
        database = sqlite3.connect(self.databasePath)

        self.tabelaRegiao = pd.read_sql_query('SELECT * FROM regiao', database, index_col= 'id')
        self.tabelaEscola = pd.read_sql_query('SELECT * FROM escola', database, index_col= 'id')
        self.tabelaTurma = pd.read_sql_query('SELECT * FROM turma', database, index_col= 'id')
        self.tabelaSerie = pd.read_sql_query('SELECT * FROM serie', database, index_col= 'id')
        self.tabelaAlunoCont = pd.read_sql_query('SELECT * FROM aluno', database, index_col= 'id')
        self.tabelaAlunoForm = pd.read_sql_query('SELECT * FROM formulario_inscricao', database, index_col= 'id')

        ultimaSerie_id = self.tabelaSerie[(self.tabelaSerie['ativa'] == 1)]['ordem'].idxmax()
        self.ordemUltimaSerie = self.tabelaSerie['ordem'][ultimaSerie_id]

        self.dadosAdicionados = True

        database.close()

    def configuraParametros(self):
        database = sqlite3.connect(self.databasePath)
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

        self.parametrosConfigurados = True

        database.close()

    def Solver1(self):
        if not self.dadosAdicionados:
            raise ErroLeituraDados()

        if not self.parametrosConfigurados:
            raise ErroConfiguracaoParametros()

        ps.preSolve(self)

        self.modelo = pywraplp.Solver.CreateSolver('Matematica_em_Movimento_modelo1', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        #####  VARIAVEIS  #####
        #Alunos de continuidade
        fm.defineVariavelAlunoCont_x(self)

        #Alunos de formulario
        fm.defineVariavelAlunoForm_y(self)

        #Turmas
        fm.defineVariavelTurma_p(self)

        #####  RESTRICOES  #####
        # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
        fm.limiteQtdTurmasAlunoCont(self)

        # (I.b): alunos de formulario sao matriculados em no máximo uma turma
        fm.limiteQtdTurmasAlunoForm(self)

        # (II): atender o limite de alunos por turma se a turma estiver aberta
        fm.limiteQtdAlunosPorTurma(self)

        # (III): abrir turmas em ordem crescente
        fm.abreTurmaEmOrdemCrescente(self)

        # (IV): se nao tem aluno na turma, a turma deve ser fechada
        fm.fechaTurmaSeNaoTemAluno(self)

        # (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
        fm.alunoContMesmaTurmaQueColegas(self)

        # (VI): priorizar alunos de formulario que se inscreveram antes
        fm.priorizaOrdemFormulario(self)

        # (VII): atender limitacao de verba
        fm.limiteVerba(self)

        #####  FUNCAO OBJETIVO  #####
        fm.objSomaTodosAlunos(self)

        self.status = self.modelo.Solve()

    def Solver2(self):
        if not self.dadosAdicionados:
            raise ErroLeituraDados()

        if not self.parametrosConfigurados:
            raise ErroConfiguracaoParametros()

        ps.preSolve(self)

        self.modelo = pywraplp.Solver.CreateSolver('Matematica_em_Movimento', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        ##########################################################
        #####  PRIMEIRA ETAPA (aloca alunos de continuidade) #####
        ##########################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.restricoesEtapaContinuidade(self)

        ##  Funcao Obj  ##
        fm.objMinimizaTurmasParaContinuidade(self) #Minimizamos o total de turmas para juntar sala quando possivel

        ##### Resolve para alunos de continuidade  #####
        self.status = self.modelo.Solve()

        if self.status == pywraplp.Solver.INFEASIBLE: ##Verba insuficiente
            raise ps.ErroVerbaInsufParaContinuidade()

        #####  PREPARA PARA SEGUNDA ETAPA  #####
        turmaAlunoCont, turmasCont, desempateEscola = fm.confirmaSolucaoParaAlunosContinuidade(self)
        self.modelo.Clear()

        ###############################################################
        #####  SEGUNDA ETAPA (preenche com alunos de formulario)  #####
        ###############################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelAlunoForm_y(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.restricoesModeloPadrao(self) #Restricoes modelo padrao

        ##  Restricoes adicionais:
        # Aplica a solucao da primeira etapa via restricoes
        for i, t in turmaAlunoCont:
            self.modelo.Add(self.x[i][t] == 1)

        # Mantem as turmas que nao possuem alunos de continuidade fechadas
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    if not t in turmasCont:
                        self.modelo.Add(self.p[t] == 0)

        ##  Funcao Objetivo  ##
        fm.objSomaTodosAlunos(self)

        #####  Resolve completando as turmas de alunos de continuidade  #####
        self.status = self.modelo.Solve()

        ### PREPARA PARA TERCEIRA ETAPA  ###
        turmaAlunoForm, demandaOrdenada = fm.recalculaDemandaBaseadoNasTurmasContEOrdena(self, desempateEscola)
        demandaOrdenada = fm.ordenaTurmasDeFormulario(self, demandaOrdenada, desempateEscola)
        self.modelo.Clear()

        ################################################################################################
        #####  TERCEIRA ETAPA (abre turmas novas priorizando a demanda com criterio de desempate)  #####
        ################################################################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelAlunoForm_y(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.restricoesModeloPadrao(self)

        # Aplica as solucoes da primeira e da segunda etapa via restricoes
        for i, t in turmaAlunoCont:
            self.modelo.Add(self.x[i][t] == 1)

        for k, t in turmaAlunoForm:
            self.modelo.Add(self.y[k][t] == 1)

        # Adiciona restricoes para priorizar turmas com maior demanda
        keys = list(demandaOrdenada.keys())
        for t1 in range(len(demandaOrdenada)-1):
            t2 = t1 + 1
            turma1 = keys[t1]
            turma2 = keys[t2]
            Y1 = []
            Y2 = []

            escola = turma1[0]
            serie = turma1[1]
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.listaTurmas[escola][serie]['aprova'][t] == 0:
                        Y1.append(self.p[t])

            escola = turma2[0]
            serie = turma2[1]
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.listaTurmas[escola][serie]['aprova'][t] == 0:
                        Y2.append(self.p[t])

            self.modelo.Add(sum(Y2) <= sum(Y1))

        #####  Funcao Objetivo  #####
        fm.objSomaTodosAlunos(self)

        #####  Resolve liberando novas turmas e priorizando demanda #####
        self.status = self.modelo.Solve()

    def SolverConstrutivo(self):
        if not self.dadosAdicionados:
            raise ErroLeituraDados()

        if not self.parametrosConfigurados:
            raise ErroConfiguracaoParametros()

        ps.preSolve(self)

        self.modelo = pywraplp.Solver.CreateSolver('Matematica_em_Movimento', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        ##########################################################
        #####  PRIMEIRA ETAPA (aloca alunos de continuidade) #####
        ##########################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.restricoesEtapaContinuidade(self)

        ##  Funcao Obj  ##
        fm.objMinimizaTurmasParaContinuidade(self) #Minimizamos o total de turmas para juntar sala quando possivel

        ##### Resolve para alunos de continuidade  #####
        self.status = self.modelo.Solve()

        if self.status == pywraplp.Solver.INFEASIBLE: ##Verba insuficiente
            raise ps.ErroVerbaInsufParaContinuidade()

        #####  PREPARA PARA SEGUNDA ETAPA  #####
        turmaAlunoCont, turmasCont, desempateEscola = fm.confirmaSolucaoParaAlunosContinuidade(self)
        self.modelo.Clear()

        ###############################################################
        #####  SEGUNDA ETAPA (preenche com alunos de formulario)  #####
        ###############################################################
        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelAlunoForm_y(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.restricoesModeloPadrao(self) #Restricoes modelo padrao

        ##  Restricoes adicionais:
        # Aplica a solucao da primeira etapa via restricoes
        for i, t in turmaAlunoCont:
            self.modelo.Add(self.x[i][t] == 1)

        # Mantem as turmas que nao possuem alunos de continuidade fechadas
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    if not t in turmasCont:
                        self.modelo.Add(self.p[t] == 0)

        ##  Funcao Objetivo  ##
        fm.objSomaTodosAlunos(self)

        #####  Resolve completando as turmas de alunos de continuidade  #####
        self.status = self.modelo.Solve()

        ### PREPARA PARA TERCEIRA ETAPA  ###
        turmaAlunoForm, demandaOrdenada = fm.recalculaDemandaBaseadoNasTurmasContEOrdena(self, desempateEscola)
        turmasFechadas = fm.verificaTurmasFechadas(self, demandaOrdenada, desempateEscola)

        ################################################################################################
        #####  TERCEIRA ETAPA (abre turmas novas priorizando a demanda com criterio de desempate)  #####
        ################################################################################################
        while not turmasFechadas is None:
            self.modelo.Clear()

            ##  Variaveis  ##
            fm.defineVariavelAlunoCont_x(self)
            fm.defineVariavelAlunoForm_y(self)
            fm.defineVariavelTurma_p(self)

            ##  Restricoes  ##
            fm.restricoesModeloPadrao(self) #Restricoes modelo padrao

            # Aplica as solucoes da primeira e da segunda etapa via restricoes
            for i, t in turmaAlunoCont:
                self.modelo.Add(self.x[i][t] == 1)

            for k, t in turmaAlunoForm:
                self.modelo.Add(self.y[k][t] == 1)

            for t in turmasFechadas:
                self.modelo.Add(self.p[t] == 0)

            fm.objSomaTodosAlunos(self)

            ## Resolve ##
            self.status = self.modelo.Solve()

            turmaAlunoCont, turmasCont, desempateEscola = fm.confirmaSolucaoParaAlunosContinuidade(self)
            turmaAlunoForm, demandaOrdenada = fm.recalculaDemandaBaseadoNasTurmasContEOrdena(self, desempateEscola)

            turmasFechadas = fm.verificaTurmasFechadas(self, demandaOrdenada, desempateEscola)

    def estatisticaProblema(self):
        print('\nESTATISTICAS PROBLEMA')
        #Total de alunos atendidos
        X = [self.x[i][t].solution_value() for i in self.alunoCont.keys() for t in self.alunoCont[i]]
        Y = [self.y[k][t].solution_value() for k in self.alunoForm.keys() for t in self.alunoForm[k]]
        print('ALUNOS')
        print('Alunos de continuidade atendidos: ', sum(X))
        print('Alunos de fomulario atendidos: ', sum(Y))
        print('Total de alunos atendidos: ', sum(X)+sum(Y))

        #Turmas
        P = []
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    P.append(self.p[t].solution_value())
        print('\nTURMAS')
        print('Total ', sum(P))

        print('\nVerba utilizada: ', self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P))
        print('\nVerba restante: ', self.verba - (self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P)))

    def estatisticaSolver(self):
        obj = self.modelo.Objective()
        print('\nDADOS DE EXECUCAO')

        ##Status solucao
        if self.status == pywraplp.Solver.OPTIMAL:
            print('Solucao: otima')
        elif self.status == pywraplp.Solver.FEASIBLE:
            print('Solucao: factivel')
        elif self.status == pywraplp.Solver.INFEASIBLE:
            print('PROBLEMA INFACTIVEL')

        ##Valor otimo
        print('Valor objetivo: ', obj.Value())

        ##Total de variaveis e restricoes
        print('Numero de variaveis: ', self.modelo.NumVariables())
        print('Numero de restricoes: ', self.modelo.NumConstraints())

        ##Tempo de execucao
        print('Tempo de execucao total do solver (ms): ', self.modelo.WallTime())
        print('Tempo de execucao total do solver (s): ', self.modelo.WallTime()*(10**(-3)))

    def exportaSolucaoSQLite(self):
        database = sqlite3.connect(self.databasePath)
        c = database.cursor()

        contadorTurmas = {}
        for regiao in self.tabelaRegiao.index:
            contadorTurmas[regiao] = {}
            for serie in self.tabelaSerie[(self.tabelaSerie['ativa'] == 1)].index:
                contadorTurmas[regiao][serie] = 0

        ###Adiciona turmas
        c.execute('DELETE FROM sol_turma')
        c.execute('DELETE FROM sol_aluno')
        c.execute('DELETE FROM sol_priorizacao_formulario')
        turma_id = 0
        alunoCont_id = 0
        alunoForm_id = 0
        for escola in self.listaTurmas.keys():
            regiao = self.tabelaEscola['regiao_id'][escola]
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    if self.p[t].solution_value() == 1:
                        turma_id = turma_id + 1

                        ###Adiciona alunos de continuidade
                        for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                            if self.x[i][t].solution_value() == 1:
                                alunoCont_id = alunoCont_id + 1
                                cpf = self.tabelaAlunoCont['cpf'][i]
                                nome = self.tabelaAlunoCont['nome'][i]
                                email = self.tabelaAlunoCont['email'][i]
                                telefone = self.tabelaAlunoCont['telefone'][i]
                                responsavel = self.tabelaAlunoCont['nome_responsavel'][i]
                                telResp = self.tabelaAlunoCont['telefone_responsavel'][i]
                                origem = self.tabelaAlunoCont['nome_escola_origem'][i]

                                linha = (alunoCont_id, cpf, nome, email, telefone, responsavel, telResp, origem, turma_id)

                                self.listaTurmas[escola][serie]['aprova'][t] = 1 #Aprova a turma se tiver algum aluno de continuidade

                                c.execute('INSERT INTO sol_aluno VALUES (?,?,?,?,?,?,?,?,?)', linha)

                        for i in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                            if self.y[i][t].solution_value() == 1:
                                alunoForm_id = alunoForm_id + 1
                                cpf = self.tabelaAlunoForm['cpf'][i]
                                nome = self.tabelaAlunoForm['nome'][i]
                                email = self.tabelaAlunoForm['email_aluno'][i]
                                telefone = self.tabelaAlunoForm['telefone_aluno'][i]
                                responsavel = self.tabelaAlunoForm['nome_responsavel'][i]
                                telResp = self.tabelaAlunoForm['telefone_responsavel'][i]
                                origem = self.tabelaAlunoForm['nome_escola_origem'][i]

                                linha = (alunoForm_id, nome, cpf, email, telefone, responsavel, telResp, int(escola), int(serie), origem, turma_id, None)

                                c.execute('INSERT INTO sol_priorizacao_formulario VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', linha)

                        ###Adiciona turma
                        nome = geraNomeTurma(regiao, serie, contadorTurmas, self.tabelaSerie, self.tabelaEscola, self.tabelaRegiao)

                        if len(self.tabelaTurma[(self.tabelaTurma['nome'] == nome)].index) > 0:
                            self.listaTurmas[escola][serie]['aprova'][t] = 1 #Aprova a turma se ela existia

                        aprova = self.listaTurmas[escola][serie]['aprova'][t]
                        linha = (turma_id, nome, self.maxAlunos, self.qtdProfAcd, self.qtdProfPedag, int(escola), int(serie), aprova)
                        c.execute('INSERT INTO sol_turma VALUES (?,?,?,?,?,?,?,?)', linha)

                        contadorTurmas[regiao][serie] = contadorTurmas[regiao][serie] + 1

        database.commit()
        database.close()
