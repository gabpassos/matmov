from math import ceil

from numpy.random import uniform

############################
#####  PRIMEIRA ETAPA  #####
############################
#####  Variaveis de Decisao Etapa 1  #####
def addVariaveisDecisaoEtapa1(self):
    """Adiciona as variaveis de alunos de continuidade e de turmas ao modelo."""
    ## Variaveis de alunos de continuidade
    for i, turmas in self.alunoCont.items():
        self.x[i] = {}
        for t in turmas:
            self.x[i][t] = self.modelo.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

    ## Variaveis de turmas
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                self.p[t] = self.modelo.IntVar(0, 1, 'p[{}]'.format(t))


#####  Restricoes Etapa 1  #####
def limiteQtdTurmasPorAlunoCont(self):
    """ (I.a): alunos de continuidade sao matriculados em exatamente uma turma. """
    for i, turmas in self.alunoCont.items():
        turmas = [self.x[i][t] for t in turmas]

        self.modelo.Add(sum(turmas) == 1)

def limiteQtdAlunosPorTurmaCont(self):
    """
    (II*): atender o limite de alunos por turma se a turma estiver aberta, considerando
    somente alunos de continuidade.
    """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = []
                for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                    alunosCont.append(self.x[i][t])

                self.modelo.Add(sum(alunosCont) <= self.maxAlunos*self.p[t])

def abreTurmaEmOrdemCrescenteEtapa1(self):
    """ (III*): abrir turmas de continuidade em ordem crescente. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            turmas = self.listaTurmas[escola][serie]['turmas']
            for t in range(len(turmas)-1):
                self.modelo.Add(self.p[turmas[t+1]] <= self.p[turmas[t]])

def fechaTurmaSeNaoTemAlunoCont(self):
    """ (IV*): se nao tem alunos de continuidade na turma, a turma deve ser fechada. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = []
                for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                    alunosCont.append(self.x[i][t])

                self.modelo.Add(self.p[t] <= sum(alunosCont))

def alunoContMesmaTurmaQueColegas(self):
    """ (V): o aluno de continuidade que nao reprovou deve continuar com os colegas. """
    for i in self.alunoCont.keys():
        for j in self.alunoCont.keys():
            if (self.mesmaTurma[i][j]) and (not self.reprovou[i]) and (not self.reprovou[j]):
                turmas = self.alunoCont[i]
                for t in turmas:
                    self.modelo.Add(self.x[i][t] == self.x[j][t])

def addRestricoesEtapa1(self):
    """
    Adiciona as restricoes do problema envolvendo somente alunos de continuidade
    (Etapa 1) ao modelo.
    """
    # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
    limiteQtdTurmasPorAlunoCont(self)

    # (II*): atender o limite de alunos por turma se a turma estiver aberta
    limiteQtdAlunosPorTurmaCont(self)

    # (III*): abrir turmas em ordem crescente
    abreTurmaEmOrdemCrescenteEtapa1(self)

    # (IV*): se nao tem aluno na turma, a turma deve ser fechada
    fechaTurmaSeNaoTemAlunoCont(self)

    # (V): o aluno de continuidade que nao reprovou deve continuar com os colegas
    alunoContMesmaTurmaQueColegas(self)


#####  Funcao Objetivo Etapa 1  #####
def addObjetivoMinTurmas(self):
    """
    Objetivo Etapa 1: minimizar a soma das turmas para forcar a uniao de turmas
    quando possivel.
    """
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Minimize(sum(P))


#####  Pos-processamento Etapa 1  #####
def armazenaSolucaoEtapa1(self):
    """
    Armazena a solucao obtida na Etapa 1.
    """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    ## Armazena turma aberta
                    self.pSol[t] = 1
                    self.pSolTotalAbertas += 1

                    ## Armazena a turma do respectivo aluno
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        if self.x[i][t].solution_value() == 1:
                            self.xSol[i] = t
                            self.xSolTotalMatric += 1


###########################
#####  SEGUNDA ETAPA  #####
###########################
#####  Pre-Processamento Etapa 2  #####
def preparaEtapa2(self):
    """
    Analisa a solucao encontrada na Etapa 1 e determina as turmas de continuidade
    e quantas vagas existem em cada turma de continuidade. Retorna tambem a quantidade
    de verba que esta disponivel para ser usada (considerando a alocacao de turmas e
    alunos de continuidade).
    """
    Tc = []
    vagasTc = {}
    for t in self.pSol.keys():
        if self.pSol[t] == 1:
            Tc.append(t)
            vagasTc[t] = self.maxAlunos

    for i in self.xSol.keys():
        t = self.xSol[i]
        if not t is None:
            vagasTc[t] -= 1

    usoVerba = verbaUtilizada(self, self.xSolTotalMatric, self.ySolTotalMatric,
                              self.pSolTotalAbertas)

    verbaDisp = self.verba - usoVerba

    return Tc, vagasTc, verbaDisp

#####  Variaveis de Decisao Etapa 2  #####
def addVariaveisDecisaoEtapa2(self, Tc):
    for t in Tc:
        escola = t[0]
        serie = t[1]

        for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
            if not k in self.y.keys():
                self.y[k] = {}
            self.y[k][t] = self.modelo.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

#####  Restricoes Etapa 2  #####
def limiteQtdTurmasPorAlunoFormEtapa2(self):
    """ Alunos de formulario sao matriculados em no maximo uma turma. """
    for k in self.y.keys():
        turmas = []
        for t in self.y[k].keys():
            turmas.append(self.y[k][t])
        self.modelo.Add(sum(turmas) <= 1)

def limiteQtdAlunosPorTurmaEtapa2(self, Tc, vagasTc):
    """Atender o limite de alunos por turma."""
    alunosForm = {t:[] for t in Tc}

    for k in self.y.keys():
        for t in self.y[k].keys():
            alunosForm[t].append(self.y[k][t])

    for t in Tc:
        self.modelo.Add(sum(alunosForm[t]) <= vagasTc[t])

def ordemFormularioEtapa2(self):
    """Alunos que preencheram o formulário com antecedencia tem prioridade."""
    alunosForm = self.y.keys()
    for k in alunosForm:
        for l in alunosForm:
            if self.y[k].keys() == self.y[l].keys():
                if self.ordemForm[k][l]:
                    yk = [self.y[k][t] for t in self.y[k].keys()]
                    yl = [self.y[l][t] for t in self.y[l].keys()]

                    self.modelo.Add(sum(yl) <= sum(yk))

def limiteVerbaEtapa2(self, verbaDisp):
    """Adiciona restricao de limite de verba."""
    Y = []
    for k in self.y.keys():
        for t in self.y[k].keys():
            Y.append(self.y[k][t])

    self.modelo.Add(self.custoAluno*sum(Y) <= verbaDisp)

def addRestricoesEtapa2(self, Tc, vagasTc, verbaDisp):
    limiteQtdTurmasPorAlunoFormEtapa2(self)

    limiteQtdAlunosPorTurmaEtapa2(self, Tc, vagasTc)

    ordemFormularioEtapa2(self)

    limiteVerbaEtapa2(self, verbaDisp)

#####  Funcao Objetivo Etapa 2  #####
def addObjetivoMaxAlunosForm(self):
    Y = []
    for k in self.y.keys():
        for t in self.y[k].keys():
            Y.append(self.y[k][t])

    self.modelo.Maximize(sum(Y))

#####  Pos-processamento Etapa 2  #####
def armazenaSolucaoEtapa2(self):
    for k in self.y.keys():
        for t in self.y[k].keys():
            if self.y[k][t].solution_value() == 1:
                self.ySol[k] = t
                self.ySolTotalMatric += 1


############################
#####  TERCEIRA ETAPA  #####
############################
#####  Pre-Processamento Etapa 3  #####
def iniciaDesempateEscola(self):
    desempateEscola = {}
    for escola in self.listaTurmas.keys():
        desempateEscola[escola] = {'alunosMatriculados': 0, 'totalTurmas': 0}

    for i in self.xSol.keys():
        escola =  self.xSol[i][0]
        desempateEscola[escola]['alunosMatriculados'] += 1

    for k in self.ySol.keys():
        if not self.ySol[k] is None:
            escola =  self.ySol[k][0]
            desempateEscola[escola]['alunosMatriculados'] += 1

    for t in self.pSol.keys():
        if self.pSol[t] == 1:
            escola = t[0]
            desempateEscola[escola]['totalTurmas'] += 1

    return desempateEscola

def iniciaDemanda(self):
    demanda = {}
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            demanda[(escola,serie)] = self.listaTurmas[escola][serie]['demanda']

    for k in self.ySol.keys():
        if not self.ySol[k] is None:
            escola =  self.ySol[k][0]
            serie = self.ySol[k][1]
            demanda[(escola,serie)] -= 1

    return demanda

def pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self):
    """
    Verifica a prioridade entre os tipos de turmas p e q. Retorna 'True' se p prioriza q, e 'False' caso contrario.

    Como a prioridade e calculada:
    ------------------------------
    Primeiramente, observamos que (nas circunstancias dos metodos implementados aqui) a demanda por p sempre sera maior
    ou igual que a demanda por q e que ambas sempre serao diferentes de zero.

    A prioridade e decidida pelo seguinte processo:
    1 - Se a diferenca e maior que 25% da capacidade da turma, p tem prioridade.
    2 - Se a diferenca das demandas e menor ou igual a 25%, retornamos a que possuir a menor serie.
    3 - Se as series sao iguais, olhamos para as escolas e retornamos a que possui menos alunos matriculados.
    4 - Se o numero de matriculados ainda e igual, selecionamos a que possui menos turmas.
    5 - Se o o numero de turmas em cada escola tambem se iguala, escolhemos aleatoriamente (distribuicao uniforme).
    """
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

def avaliaTurmasPermitidas(self, demandaOrdenada, desempateEscola):
    """
    Essa funcao e responsavel por liberar novas turmas seguindo o criterio de demanda estipulado pela ONG.
    Ela retorna 'None' se nao for possivel abrir novas turmas. Se possivel abrir novas turmas, ela retorna
    uma lista nao vazia com as turmas permitidas, isto e, quais turmas podem ser abertas na resolucao do
    proximo modelo. Alem disso, atualiza a variavel 'turmasFechadas', removendo as turmas permitidas.

    Obs 1: como os dados de demanda chegam ordenados de forma decrescente sem demanda nula, se a de maior
    demanda dominar a de segunda maior demanda, serao liberadas turmas o suficiente para 'empatar' as duas turmas,
    evitando liberar uma turma por vez do que pode ser liberado diretamente, reduzindo o total de modelos resolvidos.
    Se a segunda maior demanda domina a primeira, entao sabe-se que as diferenca entre as demandas e menor que 25% da
    capacidade. Nesse caso, somente uma turma e liberada, o que e suficiente para desempatar as demandas.
    """
    usoVerba = verbaUtilizada(self, self.xSolTotalMatric,
                              self.ySolTotalMatric, self.pSolTotalAbertas)
    verbaDisp = self.verba - usoVerba

    if verbaDisp < self.custoBase:
        turmasPermitidas = None
    elif len(demandaOrdenada) == 0:
        turmasPermitidas = None
    else:
        turmasPermitidas = []
        key = list(demandaOrdenada.keys())
        if len(key) == 1:
            p = key[0]
            escola = p[0]
            serie = p[1]
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.pSol[t] == 0:
                    turmasPermitidas.append(t)
                    break
        else:
            p = key[0]
            q = key[1]
            if pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self):
                qtdNovasTurmas = max([ceil((demandaOrdenada[p] - demandaOrdenada[q])/self.maxAlunos),1])
                escola = p[0]
                serie = p[1]
            else:
                qtdNovasTurmas = 1
                escola = q[0]
                serie = q[1]

            contTurmas = 0
            for t in self.listaTurmas[escola][serie]['turmas']:
                if contTurmas < qtdNovasTurmas and self.pSol[t] == 0:
                    if contTurmas < qtdNovasTurmas:
                        turmasPermitidas.append(t)
                        contTurmas += 1
                    else:
                        break

    return turmasPermitidas, verbaDisp

def preparaEtapa3(self):
    demanda = iniciaDemanda(self)
    demandaOrdenada = ordenaDemanda(demanda)

    desempateEscola = iniciaDesempateEscola(self)

    return demandaOrdenada, desempateEscola

#####  Variaveis de Decisao Etapa 3  #####
def addVariaveisDecisaoEtapa3(self, turmasPermitidas):
    escola = turmasPermitidas[0][0]
    serie = turmasPermitidas[0][1]
    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
        if self.ySol[k] == None:
            self.y[k] = {}

    for t in turmasPermitidas:
        self.p[t] = self.modelo.IntVar(0, 1, 'p[{}]'.format(t))

        for k in self.y.keys():
            self.y[k][t] = self.modelo.IntVar(0, 1, 'y[{}][{}]'.format(k, t))


#####  Restricoes Etapa 3  #####
def limiteQtdTurmasPorAlunoFormEtapa3(self):
    """ Alunos de formulario sao matriculados em no maximo uma turma. """
    for k in self.y.keys():
        turmas = []
        for t in self.y[k].keys():
            turmas.append(self.y[k][t])
        self.modelo.Add(sum(turmas) <= 1)

def limiteQtdAlunosPorTurmaEtapa3(self,turmasPermitidas):
    """Atender o limite de alunos por turma."""
    for t in turmasPermitidas:
        alunosForm = [self.y[k][t] for k in self.y.keys()]

        self.modelo.Add(sum(alunosForm) <= self.maxAlunos*self.p[t])

def fechaTurmaSeNaoTemAlunoForm(self,turmasPermitidas):
    for t in turmasPermitidas:
        alunosForm = [self.y[k][t] for k in self.y.keys()]

        self.modelo.Add(self.p[t] <= sum(alunosForm))

def abreTurmaEmOrdemCrescenteEtapa3(self, turmasPermitidas):
    if len(turmasPermitidas) > 1:
        for t in range(len(turmasPermitidas)-1):
            a = turmasPermitidas[t]
            b = turmasPermitidas[t+1]

            self.modelo.Add(self.p[b] <= self.p[a])

def ordemFormularioEtapa3(self, turmasPermitidas):
    """Alunos que preencheram o formulário com antecedencia tem prioridade."""
    alunosForm = self.y.keys()
    for k in alunosForm:
        for l in alunosForm:
            if self.ordemForm[k][l]:
                yk = [self.y[k][t] for t in turmasPermitidas]
                yl = [self.y[l][t] for t in turmasPermitidas]

                self.modelo.Add(sum(yl) <= sum(yk))

def limiteVerbaEtapa3(self, turmasPermitidas, verbaDisp):
    """Adiciona restricao de limite de verba."""
    Y = []
    for k in self.y.keys():
        for t in turmasPermitidas:
            Y.append(self.y[k][t])

    P = [self.p[t] for t in turmasPermitidas]

    self.modelo.Add(self.custoAluno*sum(Y)
                    + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P)
                    <= verbaDisp)

def addRestricoesEtapa3(self, turmasPermitidas, verbaDisp):
    limiteQtdTurmasPorAlunoFormEtapa3(self)

    limiteQtdAlunosPorTurmaEtapa3(self,turmasPermitidas)

    fechaTurmaSeNaoTemAlunoForm(self,turmasPermitidas)

    abreTurmaEmOrdemCrescenteEtapa3(self, turmasPermitidas)

    ordemFormularioEtapa3(self, turmasPermitidas)

    limiteVerbaEtapa3(self, turmasPermitidas, verbaDisp)

#####  Funcao Objetivo Etapa 3  #####
def addObjetivoMaxAlunosFormEtapa3(self, turmasPermitidas):
    Y = []
    for k in self.y.keys():
        for t in turmasPermitidas:
            Y.append(self.y[k][t])

    self.modelo.Maximize(sum(Y))

#####  Pos-processamento Etapa 3  #####
def armazenaSolucaoEtapa3(self, turmasPermitidas):
    for t in turmasPermitidas:
        if self.p[t].solution_value() == 1:
            self.pSol[t] = 1
            self.pSolTotalAbertas += 1

    for k in self.y.keys():
        for t in turmasPermitidas:
            if self.y[k][t].solution_value() == 1:
                self.ySol[k] = t


def atualizaDemandaOrdenadaDesempate(self, turmasPermitidas,
                                     demandaOrdenada, desempateEscola):
    escola = turmasPermitidas[0][0]
    serie = turmasPermitidas[0][1]

    for t in turmasPermitidas:
        if self.p[t].solution_value() == 1:
            desempateEscola[escola]['totalTurmas'] += 1

    for k in self.y.keys():
        for t in turmasPermitidas:
            if self.y[k][t].solution_value() == 1:
                demandaOrdenada[(escola,serie)] -= 1
                desempateEscola[escola]['alunosMatriculados'] += 1

    demandaOrdenada = ordenaDemanda(demandaOrdenada)

    return demandaOrdenada, desempateEscola

########################################################################################
################################
#####  FUNCOES AUXILIARES  #####
################################
def verbaUtilizada(self, totalCont, totalForm, totalTurmAbertas):
    """
    Dados os parametros do problema (armazenados em 'self'), calcula a verba utilizada
    para distribuir 'totalCont + totalForm' alunos em 'totalTurmAbertas' turmas.

    Retorna o valor da verba utilizada.
    """
    usoVerba = (self.custoAluno*(totalCont + totalForm)
                + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*totalTurmAbertas)

    return usoVerba

def ordenaDemanda(demanda):
    """
    Dado um dicionario que armazena as demandas por cada tipo de turma, remove as turmas que possuem demanda zero
    e ordena os elementos do dicionario de acordo com a demanda.
    """
    demanda = {k: v for k, v in demanda.items() if v != 0}
    demandaOrdenada = {k: v for k, v in sorted(demanda.items(), key=lambda item: item[1], reverse= True)}

    return demandaOrdenada

def limpaModelo(self):
    self.x = {}
    self.y = {}
    self.p = {}

class dv():
    def __init__(self, b):
        self.b = b

    def solution_value(self):
        return self.b

def reorganizaSol(self):
    limpaModelo(self)

    for i in self.alunoCont.keys():
        self.x[i] = {}
        for t in self.alunoCont[i]:
            if self.xSol[i] == t:
                self.x[i][t] = dv(1)
            else:
                self.x[i][t] = dv(0)

    for k in self.alunoForm.keys():
        self.y[k] = {}
        for t in self.alunoForm[k]:
            if self.ySol[k] == t:
                self.y[k][t] = dv(1)
            else:
                self.y[k][t] = dv(0)

    for t in self.pSol.keys():
        if self.pSol[t] == 1:
            self.p[t] = dv(1)
        else:
            self.p[t] = dv(0)
