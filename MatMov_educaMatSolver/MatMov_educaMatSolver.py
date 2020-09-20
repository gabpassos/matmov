import sqlite3
import pandas as pd
from ortools.linear_solver import pywraplp

import preSolver as ps

class Modelo:
    """Classe modelo para o problema da ONG Matematica em Movimento."""

    def __init__(self, databasePath= 'data/database.db', tipoSolver= 'CBC', tempoLimiteSolver= 3600):
        #Arquivo de entrada
        self.databasePath = databasePath

        #Dados do problema
        self.tabelaRegiao = None
        self.tabelaEscola = None
        self.tabelaTurma = None
        self.tabelaSerie = None
        self.tabelaAlunoCont = None
        self.tabelaAlunoForm = None

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
        self.tempoLimiteSolver = tempoLimiteSolver

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

        self.dadosAdicionados = True

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

    def Solve(self):
        ps.preSolve(self)
        print('\n\nSAIU DO PRE SOLVER\n\n')

        self.modelo = pywraplp.Solver.CreateSolver('Matematica_em_Movimento', self.tipoSolver)

        #####  VARIAVEIS  #####
        #Alunos de continuidade
        for i, turmas in self.alunoCont.items():
            self.x[i] = {}
            for t in turmas:
                self.x[i][t] = self.modelo.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

        #Alunos de formulario
        for k, turmas in self.alunoForm.items():
            self.y[k] = {}
            for t in turmas:
                self.y[k][t] = self.modelo.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

        #Turmas
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                turmas = self.listaTurmas[escola][serie]['turmas']
                for t in turmas:
                    self.p[t] = self.modelo.IntVar(0, 1, 'p[{}]'.format(t))

        #####  RESTRICOES  #####
        # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
        for i in self.alunoCont.keys():
            turmas = [self.x[i][t] for t in self.alunoCont[i]]
            self.modelo.Add(sum(turmas) == 1)

        # (I.b): alunos de formulario sao matriculados em no máximo uma turma
        for k in self.alunoForm.keys():
            turmas = [self.y[k][t] for t in self.alunoForm[k]]
            self.modelo.Add(sum(turmas) <= 1)

        # (II): atender o limite de alunos por turma se a turma estiver aberta
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                    alunosForm_t = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                    self.modelo.Add(sum(alunosCont_t) + sum(alunosForm_t) <= self.maxAlunos*self.p[t])

        # (III): abrir turmas em ordem crescente
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                turmas = self.listaTurmas[escola][serie]['turmas']
                for t in range(len(turmas)-1):
                    self.modelo.Add(self.p[turmas[t+1]] <= self.p[turmas[t]])

        # (IV): se nao tem aluno na turma, a turma deve ser fechada
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                    alunosForm_t = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                    self.modelo.Add(self.p[t] <= sum(alunosCont_t) + sum(alunosForm_t))

        # (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
        for i in self.alunoCont.keys():
            for j in self.alunoCont.keys():
                if self.mesmaTurma[i][j] and not self.reprovou[i] and not self.reprovou[j]:
                    turmas = self.alunoCont[i] ## Como i e j estudaram na mesma turma e nenhum reprovou, entao alunoCont[i] == alunoCont[j]
                    for t in turmas:
                        self.modelo.Add(self.x[i][t] == self.x[j][t])

        # (VI): priorizar alunos de formulario que se inscreveram antes
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                alunosForm_t = self.listaTurmas[escola][serie]['alunosPossiveis']['form']
                for k in alunosForm_t:
                    for l in alunosForm_t:
                        if self.ordemForm[k][l]: ##ordemForm[k][l] = True se k vem antes de l no formulario, False caso contrario
                            yk = [self.y[k][t] for t in self.listaTurmas[escola][serie]['turmas']]
                            yl = [self.y[l][t] for t in self.listaTurmas[escola][serie]['turmas']]

                            self.modelo.Add(sum(yl) <= sum(yk))

        # (VII): atender limitacao de verba
        X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
        Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]
        P = []
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    P.append(self.p[t])

        self.modelo.Add(self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P) <= self.verba)

        ####################################################################
        # (VIII): prioridade da abertura de turmas
        ##Como fazer isso??
        ####################################################################

        #####  FUNCAO OBJETIVO  #####
        X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
        Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]
        P = []
        for escola in self.listaTurmas.keys():
            for serie in self.listaTurmas[escola].keys():
                for t in self.listaTurmas[escola][serie]['turmas']:
                    P.append(-1*self.p[t])

        self.modelo.Maximize(sum(X) + sum(Y) + sum(P))
        print("\nAdd todas as restricoes!!!\n")
        self.status = self.modelo.Solve()

        if(self.status == pywraplp.Solver.OPTIMAL):
            print('CHUPA WILSON')



MatMov = Modelo()

MatMov.leituraDados()

MatMov.configuraParametros()

MatMov.Solve()
