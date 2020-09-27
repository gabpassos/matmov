from math import ceil

from numpy.random import uniform

##################################
#####  VARIAVEIS DE DECISAO  #####
##################################
def defineVariavelAlunoCont_x(self):
    """ Adiciona as variaveis de decisao para alunos de continuidade. """
    for i, turmas in self.alunoCont.items():
        self.x[i] = {}
        for t in turmas:
            self.x[i][t] = self.modelo.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

def defineVariavelAlunoForm_y(self):
    """ Adiciona as variaveis de decisao para alunos de formulario. """
    for k, turmas in self.alunoForm.items():
        self.y[k] = {}
        for t in turmas:
            self.y[k][t] = self.modelo.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

def defineVariavelTurma_p(self):
    """ Adiciona as variaveis de decisao para as turmas liberadas. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                self.p[t] = self.modelo.IntVar(0, 1, 'p[{}]'.format(t))

########################
#####  RESTRICOES  #####
########################
#####  Restricoes modelo base  #####
def limiteQtdTurmasAlunoCont(self):
    """ (I.a): alunos de continuidade sao matriculados em exatamente uma turma. """
    for i, turmas in self.alunoCont.items():
        turmas = [self.x[i][t] for t in turmas]
        self.modelo.Add(sum(turmas) == 1)

def limiteQtdTurmasAlunoForm(self):
    """ (I.b): alunos de formulario sao matriculados em no maximo uma turma. """
    for k, turmas in self.alunoForm.items():
        turmas = [self.y[k][t] for t in turmas]
        self.modelo.Add(sum(turmas) <= 1)

def limiteQtdAlunosPorTurma(self):
    """ (II): atender o limite de alunos por turma se a turma estiver aberta. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                alunosForm = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                self.modelo.Add(sum(alunosCont) + sum(alunosForm) <= self.maxAlunos*self.p[t])

def abreTurmaEmOrdemCrescente(self):
    """ (III): abrir turmas em ordem crescente. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            turmas = self.listaTurmas[escola][serie]['turmas']
            for t in range(len(turmas)-1):
                self.modelo.Add(self.p[turmas[t+1]] <= self.p[turmas[t]])

def fechaTurmaSeNaoTemAluno(self):
    """ (IV): se nao tem alunos na turma, a turma deve ser fechada. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]
                alunosForm = [self.y[k][t] for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']]

                self.modelo.Add(self.p[t] <= sum(alunosCont) + sum(alunosForm))

def alunoContMesmaTurmaQueColegas(self):
    """ (V): o aluno de continuidade que nao reprovou deve continuar na mesma turma que os colegas. """
    for i in self.alunoCont.keys():
        for j in self.alunoCont.keys():
            if (self.mesmaTurma[i][j]) and (not self.reprovou[i]) and (not self.reprovou[j]):
                turmas = self.alunoCont[i]
                for t in turmas:
                    self.modelo.Add(self.x[i][t] == self.x[j][t])

def priorizaOrdemFormulario(self):
    """ (VI): priorizar alunos de formulario que se inscreveram antes. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            alunosForm = self.listaTurmas[escola][serie]['alunosPossiveis']['form']
            for k in alunosForm:
                for l in alunosForm:
                    if self.ordemForm[k][l]:
                        yk = [self.y[k][t] for t in self.listaTurmas[escola][serie]['turmas']]
                        yl = [self.y[l][t] for t in self.listaTurmas[escola][serie]['turmas']]

                        self.modelo.Add(sum(yl) <= sum(yk))

def limiteVerba(self):
    """ (VII): atender limitacao de verba. """
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Add(self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P) <= self.verba)

def addRestricoesModeloBase(self):
    """ Adiciona as restricoes do modelo linear base ao modelo em 'self'. """
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

#####  Restricoes para alunos de continuidade - Etapa 1 #####
def limiteQtdAlunosPorTurmaSomenteCont(self):
    """ (II*): atender o limite de alunos por turma se a turma estiver aberta, considerando somente alunos de continuidade. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]

                self.modelo.Add(sum(alunosCont) <= self.maxAlunos*self.p[t])

def fechaTurmaSeNaoTemAlunoSomenteCont(self):
    """ (IV*): se nao tem alunos de continuidade na turma, a turma deve ser fechada. """
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                alunosCont = [self.x[i][t] for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']]

                self.modelo.Add(self.p[t] <= sum(alunosCont))

def limiteVerbaSomenteCont(self):
    """ (VII*): atender limitacao de verba. """
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Add(self.custoAluno*sum(X) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P) <= self.verba)

def addRestricoesEtapaContinuidade(self):
    """ Adiciona as restricoes do problema envolvendo somente alunos de continuidade (Etapa 1) ao modelo em 'self'."""
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

#####  Restricoes adicionais para etapas 2 e 3  #####
def addRestricoesAdicionaisEtapa2(self, turmaAlunoCont, turmasFechadas):
    """
    Completa o modelo com as restricoes adicionais da etapa 2:
    - (E2.a): fixa os alunos de continuidade nas turmas determinadas pela Etapa 1.
    - (E2.b): mantem as turmas que nao possuem alunos de continuidade fechada. Isso forca o modelo a completar as turmas existentes.
    """
    # (E2.a): Fixa os alunos de continuidade nas turmas determinadas pela Etapa 1
    for i, t in turmaAlunoCont:
        self.modelo.Add(self.x[i][t] == 1)

    # (E2.b): Mantem as turmas que nao possuem alunos de continuidade fechada.
    for t in turmasFechadas:
        self.modelo.Add(self.p[t] == 0)

def addRestricoesAdicionaisEtapa3(self, alunoTurmaCont, alunoTurmaForm, turmasFechadas):
    """
    Completa o modelo com as restricoes adicionais da etapa 3:
    - (E3.a): fixa os alunos de continuidade nas turmas determinadas pela Etapa 2.
    - (E3.b): fixa os alunos de formulario atendidos nas turmas determinadas pela Etapa 1.
    - (E3.c): fecha as turmas que devem ser fechadas, mantendo aberta somente as turmas com prioridade.
    """
    for i, t in alunoTurmaCont:
        self.modelo.Add(self.x[i][t] == 1)

    for k, t in alunoTurmaForm:
        self.modelo.Add(self.y[k][t] == 1)

    for t in turmasFechadas:
        self.modelo.Add(self.p[t] == 0)

##############################
#####  FUNCOES OBJETIVO  #####
##############################
def objMinSomaTurmas(self):
    """ Objetivo Etapa 1: minimizar a soma das turmas para forcar a uniao de turmas quando possivel. """
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t])

    self.modelo.Minimize(sum(P))

def objMaxSomaTodosAlunos(self):
    """ Define como objetivo a maximizacao do total de alunos matriculados (entre alunos de continuidade e formulario)."""
    X = [self.x[i][t] for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]

    self.modelo.Maximize(sum(X) + sum(Y))

def objMaxSomaAlunosForm(self):
    """
    Define como objetivo a maximizacao de alunos de formulario matriculados. Como a turma de destino de cada alunos de
    continuidade esta determinada a partir da primeira etapa, podemos considerar somente a maximizacao de alunos de formulario
    atendidos nas etapas 2 e 3.
    """
    Y = [self.y[k][t] for k in self.alunoForm.keys() for t in self.alunoForm[k]]

    self.modelo.Maximize(sum(Y))

################################
#####  FUNCOES AUXILIARES  #####
################################
def verbaDisponivel(self):
    """
    Dada a solucao de um modelo, retorna a verba que sobra apos utilizacao para atender todos os
    alunos e turmas da solucao. Utilizada para verificar se a verba disponivel e suficiente
    para atender novas turmas.
    """
    X = [self.x[i][t].solution_value() for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    Y = [self.y[k][t].solution_value() for k in self.alunoForm.keys() for t in self.alunoForm[k]]
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t].solution_value())

    return self.verba - (self.custoAluno*(sum(X) + sum(Y)) + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*sum(P))

def pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self):
    """
    Verifica a prioridade entre os tipos de turmas p e q. Retorna 'True' se p prioriza q, e 'False' caso contrario.

    Como a prioridade e calculada:
    ------------------------------
    Obs: Primeiramente, observamos que (nas circunstancia dos metodos implementados aqui) a demanda por p sempre sera maior
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

def ordenaDemanda(demanda):
    """
    Dado um dicionario que armazena as demandas por cada tipo de turma, remove as turmas que possuem demanda zero
    e ordena os elementos do dicionario de acordo com a demanda.
    """
    demanda = {k: v for k, v in demanda.items() if v != 0}
    demandaOrdenada = {k: v for k, v in sorted(demanda.items(), key=lambda item: item[1], reverse= True)}

    return demandaOrdenada

def armazenaSolContInicTurmasAbertasFechadas(self):
    """
    Funcao utilizada apos finalizacao da Etapa 1 (etapa de alunos de continuidade). Responsavel por construir/iniciar
    as estruturas:
    - 'alunoTurmaCont': armazena as tuplas (i, t), em que t e a turma em que o aluno de continuidade i foi alocado.
    - 'turmasAbertas': turmas que devem ser mantidas abertas (nesse ponto sao somente as turmas que possuem alunos de cont.).
    - 'turmasFechadas': turmas que devem ser mantidas fechadas (nesse ponto, e o conj. complementar das turmas abertas).
    - 'desempateEscola': contabiliza o desempate de escolas, contando tumas abertas e alunos matriculados por escola.
    """
    alunoTurmaCont = []
    turmasAbertas = []
    turmasFechadas = []
    desempateEscola = {}
    for escola in self.listaTurmas.keys():
        desempateEscola[escola] = {'alunosMatriculados': 0, 'totalTurmas': 0}
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    desempateEscola[escola]['totalTurmas'] += 1
                    turmasAbertas.append(t)
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        if self.x[i][t].solution_value() == 1:
                            alunoTurmaCont.append((i,t))
                            desempateEscola[escola]['alunosMatriculados'] += 1
                else:
                    turmasFechadas.append(t)

    return alunoTurmaCont, turmasAbertas, turmasFechadas, desempateEscola

def iniciaDemandaOrdenadaAlunoTurmaForm(self, desempateEscola):
    """
    Funcao utilizada apos finalizacao da Etapa 2. Como a Etapa 2 tem o objetivo de somente completar com alunos
    de formulario as turmas de continuidade, nao sao geradas novas turmas. Entao, coletamos a demanda geral
    de cada turma (calculada no pre-solver) e para cada aluno de formulario adequado, removemos ele da demanda
    e adicionamos ele no total de alunos matriculados em sua respectiva escola.

    Esta funcao tem tambem o papel de iniciar a construcao da estrutura 'alunoTurmaForm', que armazena as
    tuplas (k, t), em que t e a turma em que o aluno de formulario k foi alocado.
    """
    demanda = {}
    alunoTurmaForm = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            demanda[(escola,serie)] = self.listaTurmas[escola][serie]['demanda']
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        if self.y[k][t].solution_value() == 1:
                            alunoTurmaForm.append((k, t))
                            demanda[(escola,serie)] -= 1
                            desempateEscola[escola]['alunosMatriculados'] += 1

    demandaOrdenada = ordenaDemanda(demanda)
    return demandaOrdenada, alunoTurmaForm

def atualizaDadosTurmas(self, alunoTurmaForm, turmasAbertas, turmasPermitidas, turmasFechadas, demanda, desempateEscola):
    """
    Nessa funcao, pela construcao do metodo, a variavel 'turmasPermitidas' possui ao menos um elemento e ainda
    estao todas na mesma escola e na mesma serie. A estrutura utilizada permite atualizar a demanda e quais turmas
    serao abertas ou fechadas sem verificar toda a solucao encontrada, mas verificando somente a solucao envolvendo as
    turmas permitidas.

    Apos a resolucao de um modelo da etapa 3, as 'turmasPermitidas' podem ou nao virar turmas abertas. Verifica-se
    a solucao de cada turma permitida, e se o seu p[t] associado valer 1, ela passa a ser turma aberta, caso contrario,
    volta a ser turma fechada. Alem disso, verifica-se cada aluno de formulario matriculado nas turmas permitidas que
    foram abertas para atualizar as variaveis 'demanda', 'desempateEscola' e 'alunoTurmaForm'.
    """
    escola = turmasPermitidas[0][0]
    serie = turmasPermitidas[0][1]
    for t in turmasPermitidas:
        if self.p[t].solution_value() == 1:
            turmasAbertas.append(t)
            desempateEscola[escola]['totalTurmas'] += 1
            for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                if self.y[k][t].solution_value() == 1:
                    demanda[(escola, serie)] -= 1
                    desempateEscola[escola]['alunosMatriculados'] += 1
                    alunoTurmaForm.append((k, t))
        else:
            turmasFechadas.append(t)

    return ordenaDemanda(demanda)

def avaliaTurmasPermitidas(self, turmasFechadas, demandaOrdenada, desempateEscola):
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
    if verbaDisponivel(self) < self.custoBase:
        return None
    elif len(demandaOrdenada) == 0:
        return None

    turmasPermitidas = []
    key = list(demandaOrdenada.keys())
    if len(key) == 1:
        p = key[0]
        escola = p[0]
        serie = p[1]
        for t in self.listaTurmas[escola][serie]['turmas']:
            if self.p[t].solution_value() == 0:
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
            if contTurmas < qtdNovasTurmas and self.p[t].solution_value() == 0:
                if contTurmas < qtdNovasTurmas:
                    turmasPermitidas.append(t)
                    contTurmas += 1
                else:
                    break

    for t in turmasPermitidas:
        turmasFechadas.remove(t)

    return turmasPermitidas

#####################################################################################
def armazenaSolContInicTurmasFechadas(self):
    """
    Mesma funcionalidade da funcao 'armazenaSolContInicTurmasAbertasFechadas', entretanto, como o metodo
    de 'prioridade parcial' nao usa da estrutura de turmas abertas, ela nao e considerada nesta funcao.
    """
    alunoTurmaCont = []
    turmasFechadas = []
    desempateEscola = {}
    for escola in self.listaTurmas.keys():
        desempateEscola[escola] = {'alunosMatriculados': 0, 'totalTurmas': 0}
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    desempateEscola[escola]['totalTurmas'] += 1
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        if self.x[i][t].solution_value() == 1:
                            alunoTurmaCont.append((i,t))
                            desempateEscola[escola]['alunosMatriculados'] += 1
                else:
                    turmasFechadas.append(t)

    return alunoTurmaCont, turmasFechadas, desempateEscola


def ordenaTurmasDeFormularioPrioridadeParcial(self, demandaOrdenada, desempateEscola):
    """
    Basicamente, dada a demanda ordenada de cada turma, aplica a relacao de demanda
    estipulada pela ONG em toda a estrutura 'demandaOrdenada'.
    Exemplo:
    --------
    Suponha que existam tres turmas, sendo p, q e r. A demanda de p e maior que a de q,
    que por sua vez e maior que a de r. Comparamos primeiramente p com q e temos que q
    tem prioridade sobre p. Como q prioriza p, reordenamos 'demandaOrdenada' e obtemos a
    seguinte ordem: q, p, r. Os proximos a serem comparados sao o segundo com o terceiro,
    isto e, p com r. Isso segue ate comparar todos os pares consecutivos.
    """
    key_order = list(demandaOrdenada.keys())
    for c in range(len(demandaOrdenada) - 1):
        d = c + 1
        p = key_order[c]
        q = key_order[d]
        if not pPrioriza_q(p, q, demandaOrdenada, desempateEscola, self):
            aux = key_order[c]
            key_order[c] = key_order[d]
            key_order[d] = aux
            demandaOrdenada = {k: demandaOrdenada[k] for k in key_order}

    return demandaOrdenada

def addRestricoesAdicionaisPrioridadeParcialEtapa3(self, turmaAlunoCont, turmaAlunoForm, demandaOrdenada):
    """
    Completa o modelo com as restricoes adicionais da etapa 3:
    - (E3'.a): fixa os alunos de continuidade nas turmas determinadas pela Etapa 2.
    - (E3'.b): fixa os alunos de formulario atendidos nas turmas determinadas pela Etapa 1.
    - (E3'.c): seguindo a ordem de 'demandaOrdenada', para tipos consecutivos de turma, se um tipo possui maior prioridade, o total de turmas abertas desse tipo deve ser maior ou igual ao seu proximo tipo com menor prioridade.
       """
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
        P1 = []
        P2 = []

        escola = turma1[0]
        serie = turma1[1]
        for t in self.listaTurmas[escola][serie]['turmas']:
            if self.listaTurmas[escola][serie]['aprova'][t] == 0:
                P1.append(self.p[t])

        escola = turma2[0]
        serie = turma2[1]
        for t in self.listaTurmas[escola][serie]['turmas']:
            if self.listaTurmas[escola][serie]['aprova'][t] == 0:
                P2.append(self.p[t])

        self.modelo.Add(sum(P2) <= sum(P1))
