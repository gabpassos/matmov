import sqlite3

import pandas as pd
from ortools.linear_solver import pywraplp

from matmov import erros
from matmov import presolver as ps
from matmov import funcoesmod as fm
from matmov import resultados as res

class modelo:
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
        self.tempoExecPreSolver = 0

    def leituraDadosParametros(self):
        '''
        LEITURA DE DADOS E PARAMETROS

        - Realiza a leitura de dados a partir das tabelas SQLite e os armazena no formato de pandas.DataFrame.
        - Configura os parametros do modelo.
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

        erros.verificaCpfRepetido(self.tabelaAlunoCont, self.tabelaAlunoForm)

        self.dadosParametrosConfigurados = True

    def resolveSemPrioridade(self):
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

        self.tempoExecPreSolver = ps.preSolver(self)

        self.modelo = pywraplp.Solver.CreateSolver('MatMovSolver_SemPrioridade', self.tipoSolver)
        self.modelo.SetTimeLimit(self.tempoLimiteSolver*(10**3))

        ##  Variaveis  ##
        fm.defineVariavelAlunoCont_x(self)
        fm.defineVariavelAlunoForm_y(self)
        fm.defineVariavelTurma_p(self)

        ##  Restricoes  ##
        fm.addRestricoesModeloBase(self)

        ##  Funcao Objetivo  ##
        fm.objMaxSomaTodosAlunos(self)

        ##  Resolucao do modelo  ##
        self.status = self.modelo.Solve()

        if self.status == pywraplp.Solver.INFEASIBLE:
            raise erros.ErroVerbaInsufParaContinuidade()

    def resolveComPrioridadeParcial(self):
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

        self.tempoExecPreSolver = ps.preSolver(self)

        self.modelo = pywraplp.Solver.CreateSolver('MatMovSolver_PrioridadeParcial', self.tipoSolver)
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
        turmaAlunoCont, turmasCont, desempateEscola = fm.armazenaSolucaoEtapaContinuidade(self)
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
        fm.addRestricoesAdicionaisEtapa2(self, turmaAlunoCont, turmasCont)

        ##  Funcao Objetivo  ##
        fm.objMaxSomaTodosAlunos(self)

        ##  Resolve completando as turmas de alunos de continuidade  ##
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
        fm.addRestricoesModeloBase(self)
        fm.addRestricoesAdicionaisPrioridadeParcialEtapaFinal(self, turmaAlunoCont, turmaAlunoForm, demandaOrdenada)

        #####  Funcao Objetivo  #####
        fm.objMaxSomaTodosAlunos(self)

        #####  Resolve liberando novas turmas e priorizando demanda #####
        self.status = self.modelo.Solve()

    def Solve(self):
        if not self.dadosParametrosConfigurados:
            raise erros.ErroLeituraDadosParametros()

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
        turmaAlunoCont, turmasCont, desempateEscola = fm.armazenaSolucaoEtapaContinuidade(self)
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
        fm.addRestricoesAdicionaisEtapa2(self, turmaAlunoCont, turmasCont)

        ##  Funcao Objetivo  ##
        fm.objMaxSomaTodosAlunos(self)

        ##  Resolve completando as turmas de alunos de continuidade  ##
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
            fm.addRestricoesModeloBase(self) #Restricoes modelo padrao

            # Aplica as solucoes da primeira e da segunda etapa via restricoes
            for i, t in turmaAlunoCont:
                self.modelo.Add(self.x[i][t] == 1)

            for k, t in turmaAlunoForm:
                self.modelo.Add(self.y[k][t] == 1)

            for t in turmasFechadas:
                self.modelo.Add(self.p[t] == 0)

            fm.objMaxSomaTodosAlunos(self)

            ## Resolve ##
            self.status = self.modelo.Solve()

            turmaAlunoCont, turmasCont, desempateEscola = fm.armazenaSolucaoEtapaContinuidade(self)
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
                        nome = res.geraNomeTurma(regiao, serie, contadorTurmas, self.tabelaSerie, self.tabelaEscola, self.tabelaRegiao)

                        if len(self.tabelaTurma[(self.tabelaTurma['nome'] == nome)].index) > 0:
                            self.listaTurmas[escola][serie]['aprova'][t] = 1 #Aprova a turma se ela existia

                        aprova = self.listaTurmas[escola][serie]['aprova'][t]
                        linha = (turma_id, nome, self.maxAlunos, self.qtdProfAcd, self.qtdProfPedag, int(escola), int(serie), aprova)
                        c.execute('INSERT INTO sol_turma VALUES (?,?,?,?,?,?,?,?)', linha)

                        contadorTurmas[regiao][serie] = contadorTurmas[regiao][serie] + 1

        database.commit()
        database.close()
