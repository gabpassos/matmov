from ortools.linear_solver import pywraplp

#Dados
m = 0 ##Numero de alunos de continuidade
n = 0 ##Numero de alunos de formulario

##listaAlunos = ['458.010.638-54']

Xturma = [] #turma['458.010.638-54'] = ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D'] //// Aluno i é da escola 01 da regiao ZO e cursa o 2º medio
Yturma = []

#x['458.010.638-54']['ZO01_2A']
#for i in listaAlunos:
#    for t in Xturma[i]:
#        x[i][j] = MatMovModel.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

###Add um array com alunos nas linhas e os indices de cada turma que o aluno pode ir na coluna
XT = []
YT = []

#Inicializacao do modelo
MatMovModel = pywraplp.Solver.CreateSolver("Matematica_em_Movimento", "CBC_MIXED_INTEGER_PROGRAMMING")

#####  VARIAVEIS   #####
#Alunos de continuidade

#Alunos de formulario

#Turmas

#####  FUNCAO OBJETIVO  #####
objetivo = MatMovModel.Objective()

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
