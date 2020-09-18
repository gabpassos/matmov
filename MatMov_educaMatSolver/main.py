from ortools.linear_solver import pywraplp

#Parametros
alfa = 1

#Dados
m = 0 ##Numero de alunos de continuidade
n = 0 ##Numero de alunos de formulario

listaAlunosContCPF = ['458.010.638-54']
listaAlunosFormCPF = ['458.010.638-54']

#listaTurmas['ZO']['01']['9'][0] = ['ZO01_9A', 'ZO01_9B', ...]
#listaTurmas['ZO']['01']['9'][1] = ['98197391' = CPF dos alunos na turma tipo ZO01_9(ABCD)]
listaTurmas = {}

alunoCont = {'458.010.638-54': ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D']}
alunoForm = {'458.010.638-54': ['ZO01_2A', 'ZO01_2B', 'ZO01_2C', 'ZO01_2D']}

mesmaTurma ={}
reprovou = {}
W = {}

#Inicializacao do modelo
MatMovModel = pywraplp.Solver.CreateSolver("Matematica_em_Movimento", "CBC_MIXED_INTEGER_PROGRAMMING")

#####  VARIAVEIS   #####
#Alunos de continuidade
x = {}
for i, turmas in alunoCont.items():
    x[i] = {}
    for t in turmas:
        x[i][t] = MatMovModel.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

#Alunos de formulario
y = {}
for k, turmas in alunoForm.items():
    y[k] = {}
    for t in turmas:
        y[k][t] = MatMovModel.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

#Turmas (Acho que da pra melhorar esses 4 for's usando items() ao inves de keys)
p = {}
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            for t in turmas:
                p[t] = MatMovModel.IntVar(0, 1, 'p[{}]'.format(t))

#####  FUNCAO OBJETIVO  #####
objetivo = MatMovModel.Objective()

#Coef. dos alunos de continuidade: 1
for i in listaAlunosContCPF:
    for t in alunoCont[i]:
        objetivo.SetCoefficient(x[i][t], 1)

#Coef. dos alunos de formulario: 1
for k in listaAlunosFormCPF:
    for t in alunoForm[k]:
        objetivo.SetCoefficient(y[k][t], 1)

#Coef. das turmas: -1 (OBS: aqui é um bom lugar para priorizar as turmas mais novas(usar os pesos da tabela SERIE/ORDEM).
#Tentar implementar um vetor de pesos que possa levar em consideração a demanda do tipo de turma
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            for t in turmas:
                objetivo.SetCoefficient(p[t], -1)

#####  RESTRICOES  #####
# (I.a): alunos de continuidade sao matriculados em exatamente uma turma
for i in listaAlunosContCPF:
    turmas = [x[i][t] for t in alunoCont[i]]
    MatMovModel.Add(sum(turmas) == 1)

# (I.b): alunos de formulario sao matriculados em no máximo uma turma
for k in listaAlunosFormCPF:
    turmas = [y[k][t] for t in alunoForm[k]]
    MatMovModel.Add(sum(turmas) <= 1)

# (II): atender o limite de alunos por turma se a turma estiver aberta
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            alunosContNaTurma_t = listaTurmas[zona][escola][serie][1][0]
            alunosFormNaTurma_t = listaTurmas[zona][escola][serie][1][1]
            for t in turmas:
                alunosCont = [x[i][t] for i in alunosContNaTurma_t]
                alunosForm = [y[k][t] for k in alunosFormNaTurma_t]

                MatMovModel.Add(sum(alunosCont) + sum(alunosForm) <= 20*p[t])

# (III): abrir urmas em ordem crescente
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            for t in range(len(turmas)-1):
                MatMovModel.Add(p[turmas[t+1]] <= p[turmas[t]])

# (IV): se nao tem aluno na turma, a turma deve ser fechada
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            alunosContNaTurma_t = listaTurmas[zona][escola][serie][1][0]
            alunosFormNaTurma_t = listaTurmas[zona][escola][serie][1][1]
            for t in turmas:
                alunosCont = [x[i][t] for i in alunosContNaTurma_t]
                alunosForm = [y[k][t] for k in alunosFormNaTurma_t]

                MatMovModel.Add(p[t] <= sum(alunosCont) + sum(alunosForm))

# (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
for i in alunosCont.keys():
    for j in alunosCont.keys():
        if mesmaTurma[i][j] and not reprovou[i] and not reprovou[j]:
            turmas = alunoCont[i] ## Como i e j estudaram na mesma turma e nenhum reprovou, entao alunoCont[i] == alunoCont[j]
            for t in turmas:
                MatMovModel.Add(x[i][t] - x[j][t] == 0)

# (VI): priorizar alunos de formulario que se inscreveram antes
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            alunosFormNaTurma_t = listaTurmas[zona][escola][serie][1][1]
            for k in alunosFormNaTurma_t:
                for l in alunosFormNaTurma_t:
                    if W[k][l]: ##W[k][l] = True se k vem antes de l no formulario, False caso contrario
                        yk = [y[k][t] for t in turmas]
                        yl = [y[l][t] for t in turmas]

                        MatMovModel.Add(sum(yl) <= sum(yk))

# (VII): atender limitacao de verba
X = [x[i][t] for i in alunosCont.keys() for t in alunoCont[i]]
Y = [y[k][t] for k in alunosForm.keys() for t in alunoForm[k]]
P = []
for zona in listaTurmas.keys():
    for escola in listaTurmas[zona].keys():
        for serie in listaTurmas[zona][escola].keys():
            turmas = listaTurmas[zona][escola][serie][0]
            for t in turmas:
                P.append(p[t])

MatMovModel.Add(100*(sum(X) + sum(Y)) + 400*sum(P) <= 30000)

status = MatMovModel.Solve()
tempo_solver = MatMovModel.wall_time()

#####  APRESENTACAO DOS DADOS  #####
#Tipo de solução: ótima, factível, infactível
#Tempo de execução do solver
#Função objetivo


if status == pywraplp.Solver.OPTIMAL:
    print('\nSOLUÇÃO ÓTIMA:')
    print('Número ótimo de alunos que a ONG contemplará : ',MatMovModel.Objective().Value())
    print('Tempo total de uso do solver: ', tempo_solver*(10**(-3)),'s')
elif status == pywraplp.Solver.FEASIBLE:
    print('\nSOLUÇÃO FACTÍVEL:')
    print('Número ótimo de alunos que a ONG contemplará : ',MatMovModel.Objective().Value())
    print('Tempo total de uso do solver: ', tempo_solver*(10**(-3)),'s')
elif status == pywraplp.Solver.UNBOUNDED:
    print('\nPROBLEMA ILIMITADO')
elif status == pywraplp.Solver.INFEASIBLE:
    print('\nPROBLEMA INFACTÍVEL')
else:
    print('status?????')

#Número turmas abertas
somaTurmas = 0
for escola in listaTurmas.keys():
    for serie in listaTurmas[escola].keys():
        turmas = listaTurmas[escola][serie][0]
        somaTurmas = somaTurmas + sum([p[t].solution_value() for t in turmas])

print('Número de turmas abertas: ', somaTurmas)

#Quais turmas estao abertas ou fechadas
for escola in listaTurmas.keys():
    for serie in listaTurmas[escola].keys():
        turmas = listaTurmas[escola][serie][0]
        for t in turmas:
            if p[t].solution_value()==1:
                print ('Turma ', t, ' Aberta')
            else:
                print ('Turma ', t, ' Fechada')

#Marcar turmas de sugestão

#Custo (uso da verba)
X = [x[i][t].solution_value() for i in alunosCont.keys() for t in alunoCont[i]]
Y = [y[k][t].solution_value() for k in alunosForm.keys() for t in alunoForm[k]]
P = []
for escola in listaTurmas.keys():
    for serie in listaTurmas[escola].keys():
        turmas = listaTurmas[escola][serie][0]
        for t in turmas:
            P.append(p[t].solution_value())

custo = 100*(sum(X) + sum(Y)) + 400*sum(P)
print('O custo é: ', custo)

#Representar a distribuição dos alunos nas turmas
