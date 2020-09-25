from numpy.random import uniform
from math import ceil

#####  VARIAVEIS  #####
#Alunos de continuidade
def defineVariavelAlunoCont_x(self):
    for i, turmas in self.alunoCont.items():
        self.x[i] = {}
        for t in turmas:
            self.x[i][t] = self.modelo.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

#Alunos de formulario
def defineVariavelAlunoForm_y(self):
    for k, turmas in self.alunoForm.items():
        self.y[k] = {}
        for t in turmas:
            self.y[k][t] = self.modelo.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

#Turmas
def defineVariavelTurma_p(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            turmas = self.listaTurmas[escola][serie]['turmas']
            for t in turmas:
                self.p[t] = self.modelo.IntVar(0, 1, 'p[{}]'.format(t))

#####  RESTRICOES MODELO PADRAO  #####
# (I.a): alunos de continuidade sao matriculados em exatamente uma turma
def limiteQtdTurmasAlunoCont(self):
    for i in self.alunoCont.keys():
        turmas = [self.x[i][t] for t in self.alunoCont[i]]
        self.modelo.Add(sum(turmas) == 1)

# (I.b): alunos de formulario sao matriculados em no máximo uma turma
def limiteQtdTurmasAlunoForm(self):
    for k in self.alunoForm.keys():
        turmas = [self.y[k][t] for t in self.alunoForm[k]]
        self.modelo.Add(sum(turmas) <= 1)

# (II): atender o limite de alunos por turma se a turma estiver aberta
def limiteQtdAlunosPorTurma(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                alunosForm_t = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                self.modelo.Add(sum(alunosCont_t) + sum(alunosForm_t) <= self.maxAlunos*self.p[t])

# (III): abrir turmas em ordem crescente
def abreTurmaEmOrdemCrescente(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            turmas = self.listaTurmas[escola][serie]['turmas']
            for t in range(len(turmas)-1):
                self.modelo.Add(self.p[turmas[t+1]] <= self.p[turmas[t]])

# (IV): se nao tem aluno na turma, a turma deve ser fechada
def fechaTurmaSeNaoTemAluno(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                alunosForm_t = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                self.modelo.Add(self.p[t] <= sum(alunosCont_t) + sum(alunosForm_t))

# (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
def alunoContMesmaTurmaQueColegas(self):
    for i in self.alunoCont.keys():
        for j in self.alunoCont.keys():
            if self.mesmaTurma[i][j] and not self.reprovou[i] and not self.reprovou[j]:
                turmas = self.alunoCont[i] ## Como i e j estudaram na mesma turma e nenhum reprovou, entao alunoCont[i] == alunoCont[j]
                for t in turmas:
                    self.modelo.Add(self.x[i][t] == self.x[j][t])

# (VI): priorizar alunos de formulario que se inscreveram antes
def priorizaOrdemFormulario(self):
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
def limiteVerba(self):
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Add(self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P) <= self.verba)

def restricoesModeloPadrao(self):
    # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
    limiteQtdTurmasAlunoCont(self)

    # (I.b): alunos de formulario sao matriculados em no máximo uma turma
    limiteQtdTurmasAlunoForm(self)

    # (II): atender o limite de alunos por turma se a turma estiver aberta
    limiteQtdAlunosPorTurma(self)

    # (III): abrir turmas em ordem crescente
    abreTurmaEmOrdemCrescente(self)

    # (IV): se nao tem aluno na turma, a turma deve ser fechada
    fechaTurmaSeNaoTemAluno(self)

    # (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
    alunoContMesmaTurmaQueColegas(self)

    # (VI): priorizar alunos de formulario que se inscreveram antes
    priorizaOrdemFormulario(self)

    # (VII): atender limitacao de verba
    limiteVerba(self)

#####  RESTRICOES MODIFICADAS PARA ETAPA DE CONTINUIDADE  #####
# (II*): atender o limite de alunos por turma se a turma estiver aberta
def limiteQtdAlunosPorTurmaSomenteCont(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]

                self.modelo.Add(sum(alunosCont_t) <= self.maxAlunos*self.p[t])

# (IV*): se nao tem aluno na turma, a turma deve ser fechada
def fechaTurmaSeNaoTemAlunoSomenteCont(self):
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont_t = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]

                self.modelo.Add(self.p[t] <= sum(alunosCont_t))

# (VII*): atender limitacao de verba
def limiteVerbaSomenteCont(self):
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Add(self.custoAluno*sum(X) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P) <= self.verba)

def restricoesEtapaContinuidade(self):
    # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
    limiteQtdTurmasAlunoCont(self)

    # (II*): atender o limite de alunos por turma se a turma estiver aberta
    limiteQtdAlunosPorTurmaSomenteCont(self)

    # (III): abrir turmas em ordem crescente
    abreTurmaEmOrdemCrescente(self)

    # (IV*): se nao tem aluno na turma, a turma deve ser fechada
    fechaTurmaSeNaoTemAlunoSomenteCont(self)

    # (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas
    alunoContMesmaTurmaQueColegas(self)

    # (VII*): atender limitacao de verba
    limiteVerbaSomenteCont(self)

def confirmaSolucaoParaAlunosContinuidade(self):
    alunoTurmaCont = []
    turmasCont = []
    desempateEscola = {}
    for escola in self.listaTurmas.keys():
        desempateEscola[escola] = {'alunosMatriculados': 0, 'totalTurmas': 0}
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    desempateEscola[escola]['totalTurmas'] += 1
                    self.listaTurmas[escola][serie]['aprova'][t] = 1 # Aprova a turma pois possui alunos de continuidade
                    turmasCont.append(t)
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        if self.x[i][t].solution_value() == 1:
                            alunoTurmaCont.append((i,t))
                            desempateEscola[escola]['alunosMatriculados'] += 1

    return alunoTurmaCont, turmasCont, desempateEscola

def recalculaDemandaBaseadoNasTurmasContEOrdena(self, desempateEscola):
    demanda = {}
    turmaAlunoForm = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            demanda[(escola,serie)] = self.listaTurmas[escola][serie]['demanda']
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        if self.y[k][t].solution_value() == 1:
                            turmaAlunoForm.append((k,t))
                            demanda[(escola,serie)] -= 1
                            desempateEscola[escola]['alunosMatriculados'] += 1

    demanda = {k: v for k, v in demanda.items() if v != 0} ##Remove as demandas nulas para nao afetar criterio de desempate

    demandaOrdenada = {k: v for k, v in sorted(demanda.items(), key=lambda item: item[1], reverse= True)}

    return turmaAlunoForm, demandaOrdenada

def pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self):
    #Demanda de p sera sempre maior ou igual a demanda de q (nas condicoes dos metodos implementados aqui)
    if demandaOrdenada[p] - demandaOrdenada[q] <= 0.25*self.maxAlunos: #empate
        escola_p = p[0]
        serie_p = p[1]

        escola_q = q[0]
        serie_q = q[1]

        if self.tabelaSerie['ordem'][serie_p] < self.tabelaSerie['ordem'][serie_q]:
            return True
        elif self.tabelaSerie['ordem'][serie_p] > self.tabelaSerie['ordem'][serie_q]:
            return False
        elif desempateEscola[escola_p]['alunosMatriculados'] < desempateEscola[escola_q]['alunosMatriculados']:
            return True
        elif desempateEscola[escola_p]['alunosMatriculados'] > desempateEscola[escola_q]['alunosMatriculados']:
            return False
        elif desempateEscola[escola_p]['totalTurmas'] < desempateEscola[escola_q]['totalTurmas']:
            return True
        elif desempateEscola[escola_p]['totalTurmas'] > desempateEscola[escola_q]['totalTurmas']:
            return False
        else: # Escolhe aleatorio
            if uniform(0, 1) < 0.5:
                return True
            else:
                return False

    return True

def ordenaTurmasDeFormulario(self, demandaOrdenada, desempateEscola):
    key_order = list(demandaOrdenada.keys())
    for c in range(len(demandaOrdenada) - 1):
        d = c + 1
        p = key_order[c]
        q = key_order[d]
        if not pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self): #Se a turma q tem prioridade sobre a turma q + 1
            aux = key_order[c]
            key_order[c] = key_order[d]
            key_order[d] = aux
            demandaOrdenada = {k: demandaOrdenada[k] for k in key_order}

    return demandaOrdenada

def verbaDisponivel(self):
    X = [self.x[i][t].solution_value() for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t].solution_value() for k in self.alunoForm.keys() for t in self.alunoForm[k]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t].solution_value())

    return self.verba - (self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P))

def verificaTurmasFechadas(self, demandaOrdenada, desempateEscola):
    if verbaDisponivel(self) < self.custoAluno + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd): #Nao consegue abrir nenhuma turma
        return None
    elif len(demandaOrdenada) == 0: ##Todo o formulario foi atendido
        return None

    turmasAbertas = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    turmasAbertas.append(t)

    key = list(demandaOrdenada.keys())
    if len(key) == 1:
        p = key[0]
        escola = p[0]
        serie = p[1]
        for t in self.listaTurmas[escola][serie]['turmas']:
            if self.p[t].solution_value() == 0:
                turmasAbertas.append(t)
                break
    else:
        p = key[0]
        q = key[1]
        if pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self): #Se a turma q tem prioridade sobre a turma q + 1
            ##Permite abertura de turmas suficientes para alterar a ordem de prioridade
            qtdNovasTurmas = ceil((demandaOrdenada[p] - demandaOrdenada[q])/self.maxAlunos)
            escola = p[0]
            serie = p[1]

            contTurmas = 0
            for t in self.listaTurmas[escola][serie]['turmas']:
                if contTurmas < qtdNovasTurmas and self.p[t].solution_value() == 0:
                    turmasAbertas.append(t)
                    contTurmas += 1
        else:
            escola = q[0]
            serie = q[1]
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 0:
                    turmasAbertas.append(t)
                    break

    turmasFechadas = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if not t in turmasAbertas:
                    turmasFechadas.append(t)

    return turmasFechadas

#####  FUNCOES OBJETIVO  #####
def objMinimizaTurmasParaContinuidade(self):
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Minimize(sum(P))


def objSomaTodosAlunos(self):
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]

    self.modelo.Maximize(sum(X) + sum(Y))
