from ortools.linear_solver import pywraplp

#Parametros
alfa = 1

#Dados
m = 0 ##Numero de alunos de continuidade
n = 0 ##Numero de alunos de formulario

listaAlunosContCPF = ['458.010.638-54']
listaAlunosFormCPF = ['458.010.638-54']

listaTurmas = ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D', 'ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D']

turmaAlunoCont = {'458.010.638-54': ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D']}
turmaAlunoForm = {'458.010.638-54': ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D']}

#Inicializacao do modelo
MatMovModel = pywraplp.Solver.CreateSolver("Matematica_em_Movimento", "CBC_MIXED_INTEGER_PROGRAMMING")

#####  VARIAVEIS   #####
#Alunos de continuidade
x = {}
for i in listaAlunosContCPF:
    x[i] = {}
    for t in turmaAlunoCont[i]:
        x[i][t] = MatMovModel.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

#Alunos de formulario
y = {}
for k in listaAlunosFormCPF:
    y[k] = {}
    for t in turmaAlunoForm[k]:
        y[k][t] = MatMovModel.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

#Turmas
p = {}
for t in listaTurmas:
    p[t] = MatMovModel.IntVar(0, 1, 'p[{}]'.format(t))

#####  FUNCAO OBJETIVO  #####
objetivo = MatMovModel.Objective()

#Coef. dos alunos de continuidade: 1
for i in listaAlunosContCPF:
    for t in turmaAlunoCont[i]:
        objetivo.SetCoefficient(x[i][t], 1)

#Coef. dos alunos de formulario: 1
for k in listaAlunosFormCPF:
    for t in turmaAlunoForm[k]:
        objetivo.SetCoefficient(y[k][t], 1)

#Coef. das turmas: -1 (OBS: aqui é um bom lugar para priorizar as turmas mais novas(usar os pesos da tabela SERIE/ORDEM).
#Tentar implementar um vetor de pesos que possa levar em consideração a demanda do tipo de turma
for t in listaTurmas:
    objetivo.SetCoefficient(p[t], -1)

#####  RESTRICOES  #####

#####  APRESENTACAO DOS DADOS  #####
#Tipo de solução: ótima, factível, infactível
#Tempo de execução do solver
#Função objetivo

#Número turmas abertas
#Quais turmas estao abertas ou fechadas
#Marcar turmas de sugestão
#Custo (uso da verba)

#Representar a distribuição dos alunos nas turmas
