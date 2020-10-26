from math import ceil

from numpy.random import uniform

############################
#####  PRIMEIRA ETAPA  #####
############################
#####  Variaveis de Decisao Etapa 1  #####
def addVariaveisDecisaoEtapa1(modelo, x, p):
    """Adiciona as variaveis de alunos de continuidade e de turmas ao modelo."""
    ## Variaveis de alunos de continuidade
    for i, turmas in modelo.alunoCont.items():
        x[i] = {}
        for t in turmas:
            x[i][t] = modelo.solver.IntVar(0, 1, 'x[{}][{}]'.format(i, t))

    ## Variaveis de turmas
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                p[t] = modelo.solver.IntVar(0, 1, 'p[{}]'.format(t))


#####  Restricoes Etapa 1  #####
def limiteQtdTurmasPorAlunoCont(modelo, x):
    """Alunos de continuidade sao matriculados em exatamente uma turma."""
    for i, turmas in modelo.alunoCont.items():
        turmas = [x[i][t] for t in turmas]

        modelo.solver.Add(sum(turmas) == 1)

def limiteQtdAlunosPorTurmaCont(modelo, x, p):
    """
    Atender o limite de alunos por turma se a turma estiver aberta, considerando
    somente alunos de continuidade.
    """
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                alunosCont = []
                for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                    alunosCont.append(x[i][t])

                modelo.solver.Add(sum(alunosCont) <= modelo.maxAlunos*p[t])

def abreTurmaEmOrdemCrescenteEtapa1(modelo, p):
    """Abrir turmas de continuidade em ordem crescente."""
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            turmas = modelo.listaTurmas[escola][serie]['turmas']
            for t in range(len(turmas)-1):
                modelo.solver.Add(p[turmas[t+1]] <= p[turmas[t]])

def fechaTurmaSeNaoTemAlunoCont(modelo, x, p):
    """Se nao tem alunos de continuidade na turma, a turma deve ser fechada."""
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                alunosCont = []
                for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                    alunosCont.append(x[i][t])

                modelo.solver.Add(p[t] <= sum(alunosCont))

def alunoContMesmaTurmaQueColegas(modelo, x):
    """O aluno de continuidade que nao reprovou deve continuar com os colegas."""
    for i in modelo.alunoCont:
        for j in modelo.alunoCont:
            if (modelo.mesmaTurma[i][j]) and (not modelo.reprovou[i]) and (not modelo.reprovou[j]):
                turmas = modelo.alunoCont[i]
                for t in turmas:
                    modelo.solver.Add(x[i][t] == x[j][t])

def addRestricoesEtapa1(modelo, x, p):
    """
    Adiciona as restricoes do problema envolvendo somente alunos de continuidade
    (Etapa 1) ao modelo.

    Obs: a verba foi desconsiderada, de forma que uma solucao para alunos
    de continuidade sempre sara obtida, mesmo faltando verba para alunos de
    continuidade.
    """
    # (I.a): alunos de continuidade sao matriculados em exatamente uma turma
    limiteQtdTurmasPorAlunoCont(modelo, x)

    # (II*): atender o limite de alunos por turma se a turma estiver aberta
    limiteQtdAlunosPorTurmaCont(modelo, x, p)

    # (III*): abrir turmas em ordem crescente
    abreTurmaEmOrdemCrescenteEtapa1(modelo, p)

    # (IV*): se nao tem aluno na turma, a turma deve ser fechada
    fechaTurmaSeNaoTemAlunoCont(modelo, x, p)

    # (V): o aluno de continuidade que nao reprovou deve continuar com os colegas
    alunoContMesmaTurmaQueColegas(modelo, x)


#####  Funcao Objetivo Etapa 1  #####
def addObjetivoMinTurmas(modelo, p):
    """
    Objetivo Etapa 1: minimizar a soma das turmas para forcar a uniao de turmas
    quando possivel.
    """
    P = []
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                P.append(p[t])

    modelo.solver.Minimize(sum(P))


#####  Pos-processamento Etapa 1  #####
def armazenaSolucaoEtapa1(modelo, x, p):
    """
    Armazena a solucao obtida na Etapa 1.
    """
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if p[t].solution_value() == 1:
                    ## Armazena turma aberta
                    modelo.p[t] = 1
                    modelo.pSoma += 1

                    ## Armazena a turma do respectivo aluno
                    for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        if x[i][t].solution_value() == 1:
                            modelo.x[i] = t
                            modelo.xSoma += 1


###########################
#####  SEGUNDA ETAPA  #####
###########################
#####  Pre-Processamento Etapa 2  #####
def preparaEtapa2(modelo):
    """
    Analisa a solucao encontrada na Etapa 1 e determina as turmas de continuidade
    e quantas vagas existem em cada turma de continuidade. Retorna tambem a quantidade
    de verba que esta disponivel para ser usada (considerando a alocacao de turmas e
    alunos de continuidade).
    """
    Tc = []
    vagasTc = {}
    for t in modelo.p:
        if modelo.p[t] == 1:
            Tc.append(t)
            vagasTc[t] = modelo.maxAlunos

    for i in modelo.x:
        t = modelo.x[i]
        if not t is None:
            vagasTc[t] -= 1

    usoVerba = verbaUtilizada(modelo)
    verbaDisp = modelo.verba - usoVerba

    return Tc, vagasTc, verbaDisp

#####  Variaveis de Decisao Etapa 2  #####
def addVariaveisDecisaoEtapa2(modelo, y, Tc):
    """
    Adiciona as variaveis de alunos de continuidade que podem ser matriculados
    nas turmas abertas na etapa 1.
    """
    for t in Tc:
        escola = t[0]
        serie = t[1]
        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
            if not k in y:
                y[k] = {}
            y[k][t] = modelo.solver.IntVar(0, 1, 'y[{}][{}]'.format(k, t))

#####  Restricoes Etapa 2  #####
def limiteQtdTurmasPorAlunoFormEtapa2(modelo, y):
    """ Alunos de formulario sao matriculados em no maximo uma turma. """
    for k in y:
        turmas = []
        for t in y[k]:
            turmas.append(y[k][t])
        modelo.solver.Add(sum(turmas) <= 1)

def limiteQtdAlunosPorTurmaEtapa2(modelo, y, Tc, vagasTc):
    """Atender o limite de alunos por turma."""
    alunosForm = {t:[] for t in Tc}
    for k in y:
        for t in y[k]:
            alunosForm[t].append(y[k][t])

    for t in Tc:
        modelo.solver.Add(sum(alunosForm[t]) <= vagasTc[t])

def ordemFormularioEtapa2(modelo, y):
    """Alunos que preencheram o formulário com antecedencia tem prioridade."""
    for k in y:
        for l in y:
            if y[k].keys() == y[l].keys(): ## Devem concorrer para mesma escola e serie
                if modelo.ordemForm[k][l]:
                    yk = [y[k][t] for t in y[k]]
                    yl = [y[l][t] for t in y[l]]

                    modelo.solver.Add(sum(yl) <= sum(yk))

def limiteVerbaEtapa2(modelo, y, verbaDisp):
    """Adiciona restricao de limite de verba."""
    Y = []
    for k in y:
        for t in y[k]:
            Y.append(y[k][t])

    modelo.solver.Add(modelo.custoAluno*sum(Y) <= verbaDisp)

def addRestricoesEtapa2(modelo, y, Tc, vagasTc, verbaDisp):
    limiteQtdTurmasPorAlunoFormEtapa2(modelo, y)

    limiteQtdAlunosPorTurmaEtapa2(modelo, y, Tc, vagasTc)

    ordemFormularioEtapa2(modelo, y)

    limiteVerbaEtapa2(modelo, y, verbaDisp)


#####  Funcao Objetivo Etapa 2  #####
def addObjetivoMaxAlunosForm(modelo, y):
    Y = []
    for k in y:
        for t in y[k]:
            Y.append(y[k][t])

    modelo.solver.Maximize(sum(Y))


#####  Pos-processamento Etapa 2  #####
def armazenaSolucaoEtapa2(modelo, y):
    """
    Armazena a solucao de alunos de formulario opbtida na etapa 2.
    """
    for k in y:
        for t in y[k]:
            if y[k][t].solution_value() == 1:
                modelo.y[k] = t
                modelo.ySoma += 1


############################
#####  TERCEIRA ETAPA  #####
############################
#####  Pre-Processamento Etapa 3  #####
def iniciaDesempateEscola(modelo):
    """
    Inicia a estrutura de desempate de escola com os resultados que ja existem.
    Para cada escola usada como chave do dicionario, armazena o total de alunos
    matriculados e o total de turmas abertas naquela escola.
    """
    desempateEscola = {}
    for escola in modelo.listaTurmas.keys():
        desempateEscola[escola] = {'alunosMatriculados': 0, 'totalTurmas': 0}

    for i in modelo.x:
        escola =  modelo.x[i][0]
        desempateEscola[escola]['alunosMatriculados'] += 1

    for k in modelo.y:
        if not modelo.y[k] is None:
            escola =  modelo.y[k][0]
            desempateEscola[escola]['alunosMatriculados'] += 1

    for t in modelo.p:
        if modelo.p[t] == 1:
            escola = t[0]
            desempateEscola[escola]['totalTurmas'] += 1

    return desempateEscola

def iniciaDemanda(modelo):
    """
    Inicia a variavel que guarda a demanda de alunos de formulario corrente de cada
    tipo de turma (escola, serie).
    """
    demanda = {}
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            demanda[(escola,serie)] = modelo.listaTurmas[escola][serie]['demanda']

    for k in modelo.y:
        if not modelo.y[k] is None:
            escola =  modelo.y[k][0]
            serie = modelo.y[k][1]
            demanda[(escola,serie)] -= 1

    return demanda

def pPrioriza_q(p, q, demandaOrdenada, desempateEscola, modelo):
    """
    Verifica a prioridade entre os tipos de turmas p e q. Retorna ```True``` se
    p prioriza q, e ```False``` caso contrario.

    Como a prioridade e calculada:
    ------------------------------
    Primeiramente, observamos que (nas circunstancias dos metodos implementados aqui) a
    demanda por p sempre sera maior ou igual que a demanda por q e que ambas sempre
    serao diferentes de zero.

    A prioridade e decidida pelo seguinte processo:
    1 - Se a diferenca e maior que 25% da capacidade da turma, p tem prioridade.
    2 - Se a diferenca das demandas e menor ou igual a 25%, retornamos a que possuir a
        menor serie.
    3 - Se as series sao iguais, olhamos para as escolas e retornamos a que possui menos
        alunos matriculados.
    4 - Se o numero de matriculados ainda e igual, selecionamos a que possui menos
        turmas.
    5 - Se o o numero de turmas em cada escola tambem se iguala, escolhemos
        aleatoriamente (distribuicao uniforme).
    """
    if demandaOrdenada[p] - demandaOrdenada[q] <= 0.25*modelo.maxAlunos: #empate
        escola_p = p[0]
        serie_p = p[1]

        escola_q = q[0]
        serie_q = q[1]

        if modelo.tabelaSerie['ordem'][serie_p] < modelo.tabelaSerie['ordem'][serie_q]:
            return True
        elif modelo.tabelaSerie['ordem'][serie_p] > modelo.tabelaSerie['ordem'][serie_q]:
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

def avaliaTurmasPermitidas(modelo, demandaOrdenada, desempateEscola):
    """
    Essa funcao e responsavel por liberar novas turmas seguindo o criterio de demanda
    estipulado pela ONG. Ela retorna 'None' se nao for possivel abrir novas turmas.
    Se possivel abrir novas turmas, ela retorna uma lista nao vazia com as turmas
    permitidas, isto e, quais turmas podem ser abertas na resolucao do proximo modelo.
    Alem disso, atualiza a variavel 'turmasFechadas', removendo as turmas permitidas.

    Obs 1: como os dados de demanda chegam ordenados de forma decrescente sem demanda
    nula, se a de maior demanda dominar a de segunda maior demanda, serao liberadas
    turmas o suficiente para 'empatar' as duas turmas, evitando liberar uma turma por
    vez do que pode ser liberado diretamente, reduzindo o total de modelos resolvidos.
    Se a segunda maior demanda domina a primeira, entao sabe-se que as diferenca entre
    as demandas e menor que 25% da capacidade. Nesse caso, somente uma turma e liberada,
    o que e suficiente para desempatar as demandas.
    """
    usoVerba = verbaUtilizada(modelo)
    verbaDisp = modelo.verba - usoVerba

    if verbaDisp < modelo.custoBase:
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
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if modelo.p[t] == 0:
                    turmasPermitidas.append(t)
                    break
        else:
            p = key[0]
            q = key[1]
            if pPrioriza_q(p, q, demandaOrdenada, desempateEscola, modelo):
                #Toma o maximo caso as demandas seja iguais(ceil(0) = 0)
                qtd = (demandaOrdenada[p] - demandaOrdenada[q])/modelo.maxAlunos
                qtdNovasTurmas = max([qtd,1])
                escola = p[0]
                serie = p[1]
            else:
                qtdNovasTurmas = 1
                escola = q[0]
                serie = q[1]

            contTurmas = 0
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if contTurmas < qtdNovasTurmas and modelo.p[t] == 0:
                    if contTurmas < qtdNovasTurmas:
                        turmasPermitidas.append(t)
                        contTurmas += 1
                    else:
                        break

    return turmasPermitidas, verbaDisp

def preparaEtapa3(modelo):
    demanda = iniciaDemanda(modelo)
    demandaOrdenada = ordenaDemanda(demanda)

    desempateEscola = iniciaDesempateEscola(modelo)

    return demandaOrdenada, desempateEscola

#####  Variaveis de Decisao Etapa 3  #####
def addVariaveisDecisaoEtapa3(modelo, y, p, turmasPermitidas):
    escola = turmasPermitidas[0][0]
    serie = turmasPermitidas[0][1]
    for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
        if modelo.y[k] == None:
            y[k] = {}

    for t in turmasPermitidas:
        p[t] = modelo.solver.IntVar(0, 1, 'p[{}]'.format(t))

        for k in y:
            y[k][t] = modelo.solver.IntVar(0, 1, 'y[{}][{}]'.format(k, t))


#####  Restricoes Etapa 3  #####
def limiteQtdTurmasPorAlunoFormEtapa3(modelo, y):
    """ Alunos de formulario sao matriculados em no maximo uma turma. """
    for k in y:
        turmas = [y[k][t] for t in y[k]]
        modelo.solver.Add(sum(turmas) <= 1)

def limiteQtdAlunosPorTurmaEtapa3(modelo, y, p, turmasPermitidas):
    """Atender o limite de alunos por turma."""
    for t in turmasPermitidas:
        alunosForm = [y[k][t] for k in y]
        modelo.solver.Add(sum(alunosForm) <= modelo.maxAlunos*p[t])

def fechaTurmaSeNaoTemAlunoForm(modelo, y, p, turmasPermitidas):
    """Fecha as turmas que nao possuem alunos de formulario."""
    for t in turmasPermitidas:
        alunosForm = [y[k][t] for k in y]
        modelo.solver.Add(p[t] <= sum(alunosForm))

def abreTurmaEmOrdemCrescenteEtapa3(modelo, p, turmasPermitidas):
    """Garante que as turmas sejam abertas em ordem crescente."""
    for t in range(len(turmasPermitidas)-1):
        a = turmasPermitidas[t]
        b = turmasPermitidas[t+1]

        modelo.solver.Add(p[b] <= p[a])

def ordemFormularioEtapa3(modelo, y, turmasPermitidas):
    """Alunos que preencheram o formulário com antecedencia tem prioridade."""
    for k in y:
        for l in y:
            if modelo.ordemForm[k][l]:
                yk = [y[k][t] for t in turmasPermitidas]
                yl = [y[l][t] for t in turmasPermitidas]

                modelo.solver.Add(sum(yl) <= sum(yk))

def limiteVerbaEtapa3(modelo, y, p, turmasPermitidas, verbaDisp):
    """Adiciona restricao de limite de verba."""
    Y = [y[k][t] for k in y for t in turmasPermitidas]
    P = [p[t] for t in turmasPermitidas]

    modelo.solver.Add(modelo.custoAluno*sum(Y)
                    + modelo.custoProf*(modelo.qtdProfPedag + modelo.qtdProfAcd)*sum(P)
                    <= verbaDisp)

def addRestricoesEtapa3(modelo, y, p, turmasPermitidas, verbaDisp):
    limiteQtdTurmasPorAlunoFormEtapa3(modelo, y)

    limiteQtdAlunosPorTurmaEtapa3(modelo, y, p, turmasPermitidas)

    fechaTurmaSeNaoTemAlunoForm(modelo, y, p, turmasPermitidas)

    abreTurmaEmOrdemCrescenteEtapa3(modelo, p, turmasPermitidas)

    ordemFormularioEtapa3(modelo, y, turmasPermitidas)

    limiteVerbaEtapa3(modelo, y, p, turmasPermitidas, verbaDisp)

#####  Funcao Objetivo Etapa 3  #####
def addObjetivoMaxAlunosFormEtapa3(modelo, y, turmasPermitidas):
    Y = [y[k][t] for k in y for t in turmasPermitidas]

    modelo.solver.Maximize(sum(Y))

#####  Pos-processamento Etapa 3  #####
def armazenaSolucaoEtapa3(modelo, y, p, turmasPermitidas):
    """
    Armazena as soluções encontradas na etapa 3.
    """
    for t in turmasPermitidas:
        if p[t].solution_value() == 1:
            modelo.p[t] = 1
            modelo.pSoma += 1

    for k in y:
        for t in turmasPermitidas:
            if y[k][t].solution_value() == 1:
                modelo.y[k] = t
                modelo.ySoma += 1

def atualizaDemandaOrdenadaDesempate(modelo, y, p, turmasPermitidas,
                                     demandaOrdenada, desempateEscola):
    """
    Atualiza a demanda por cada turma e as variaveis usadas para criterio de desempate.
    """
    escola = turmasPermitidas[0][0]
    serie = turmasPermitidas[0][1]

    for t in turmasPermitidas:
        if p[t].solution_value() == 1:
            desempateEscola[escola]['totalTurmas'] += 1

    for k in y:
        for t in turmasPermitidas:
            if y[k][t].solution_value() == 1:
                demandaOrdenada[(escola,serie)] -= 1
                desempateEscola[escola]['alunosMatriculados'] += 1

    demandaOrdenada = ordenaDemanda(demandaOrdenada)
    return demandaOrdenada, desempateEscola

########################################################################################
################################
#####  FUNCOES AUXILIARES  #####
################################
def verbaUtilizada(modelo):
    """
    Dados os parametros do problema (armazenados em 'modelo'), calcula a verba utilizada
    para distribuir 'totalCont + totalForm' alunos em 'totalTurmAbertas' turmas.

    Retorna o valor da verba utilizada.
    """
    usoVerba = (modelo.custoAluno*(modelo.xSoma + modelo.ySoma)
          + modelo.custoProf*(modelo.qtdProfPedag + modelo.qtdProfAcd)*modelo.pSoma)

    return usoVerba

def ordenaDemanda(demanda):
    """
    Dado um dicionario que armazena as demandas por cada tipo de turma, remove as turmas
    que possuem demanda zero e ordena os elementos do dicionario de acordo com a demanda.
    """
    demanda = {k: v for k, v in demanda.items() if v != 0}

    itensOrdenados = sorted(demanda.items(), key=lambda item: item[1], reverse= True)

    demandaOrdenada = {k: v for k, v in itensOrdenados}

    return demandaOrdenada

def limpaModelo(modelo):
    """
    Limpa o solver do ortools e reinicia os dicionarios que armazenam as variaveis
    de decisao.
    """
    x = {}
    y = {}
    p = {}

    modelo.solver.Clear()
    return x, y, p
