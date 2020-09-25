import time
from datetime import datetime
from math import ceil

from numpy.random import uniform

import erros

def dicionarioFinalListaTurmas():
    """
    Funcao auxiliar para criacao da estrutura utilizada.
    """
    dicionario = {'turmas': [],
                  'alunosPossiveis': {'cont': [], 'form': []},
                  'aprova': {},
                  'demanda': 0}

    return dicionario

###############################
#####  DEMANDA DE TURMAS  #####
###############################
def existeDemandaDeContinuidade(t, otimizaNoAno, tabelaAlunoCont):
    """
    Verifica se existe demanda de alunos de continuidade para a turma 't' caso a otimizacao seja feita no ano,
    ou para a continuacao da turma 't' no ano seguinte se a otimizacao for feita entre anos consecutivos.
    Retorna "True" se houver demanda.

    Para haver demanda:
    -------------------
    - Otimizacao no ano: a turma deve ter ao menos um aluno que ira continuar matriculado.
    - Otimizacao entre anos: a turma deve ter ao menos um aluno aprovado e que ira continuar matriculado.
    """
    if otimizaNoAno == 0:
        demandaCont = tabelaAlunoCont[(tabelaAlunoCont['turma_id'] == t) & (tabelaAlunoCont['continua'] == 1) & (tabelaAlunoCont['reprova'] == 0)]
    else:
        demandaCont = tabelaAlunoCont[(tabelaAlunoCont['turma_id'] == t) & (tabelaAlunoCont['continua'] == 1)]

    if len(demandaCont.index) > 0:
        return True

    return False

def verificaDemandaTurmas(modelo, tabelaTurma, tabelaAlunoCont, tabelaAlunoForm, tabelaSerie):
    """
    Verifica quantas e quais turmas sao necessarias para alocar todos os alunos (de continuidade e de formulario).
    O processo feito por essa funcao se divide em tres etapas:

    - Etapa 1: distribui as turmas que ja existem, liberando as turmas para todos os alunos de continuidade que
    nao reprovaram e que irao continuar matriculados.

    - Etapa 2: verifica a demanda de alunos repetentes se a otimizacao for entre anos (Etapa 2a) e verifica a
    demanda de alunos de formulario (Etapa 2b).

    - Etapa 3: adiciona as turmas necessarias para para atender alunos repetentes e alunos de formulario.

    Tratamento de erro: se uma serie que precisa estar aberta para atender um aluno de continuidade esta fechada,
    um erro sera exibido.
    """
    #####  Etapa 1: trabalha com as turmas existentes, alocando espaco para alunos de continuidade #####
    for t in tabelaTurma.index:
        if existeDemandaDeContinuidade(t, modelo.otimizaNoAno, tabelaAlunoCont):
            escola = tabelaTurma['escola_id'][t]
            serie = tabelaTurma['serie_id'][t]
            ordem = tabelaSerie['ordem'][serie]

            if modelo.otimizaNoAno == 0:
                ordem += 1

            if ordem <= modelo.ordemUltimaSerie:
                serie = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]

                if tabelaSerie['ativa'][serie] == 0:
                    raise erros.ErroSerieContinuidadeFechada(tabelaSerie['nome'][serie])

                if not escola in modelo.listaTurmas.keys():
                    modelo.listaTurmas[escola] = {}
                    modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()
                    chave = (escola, serie, 1)
                elif not serie in modelo.listaTurmas[escola].keys():
                    modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()
                    chave = (escola, serie, 1)
                else:
                    totalTurmas = len(modelo.listaTurmas[escola][serie]['turmas'])
                    chave = (escola, serie, totalTurmas + 1)
                modelo.listaTurmas[escola][serie]['turmas'].append(chave)
                modelo.listaTurmas[escola][serie]['aprova'][chave] = 0

    #####  Etapa 2a: contabiliza a demanda dos alunos repetentes (caso otimizar entre os anos)  #####
    if modelo.otimizaNoAno == 0:
        demandaRepetentes = {}
        for i in tabelaAlunoCont.index:
            if tabelaAlunoCont['reprova'][i] == 1:
                t = tabelaAlunoCont['turma_id'][i]
                escola = tabelaTurma['escola_id'][t]
                serie = tabelaTurma['serie_id'][t]

                if tabelaSerie['ativa'][serie] == 0:
                    raise erros.ErroSerieContinuidadeFechada(tabelaSerie['nome'][serie])

                if (escola, serie) in demandaRepetentes.keys():
                    demandaRepetentes[(escola, serie)] += 1
                else:
                    demandaRepetentes[(escola, serie)] = 1

                if not escola in modelo.listaTurmas.keys():
                    modelo.listaTurmas[escola] = {}
                    modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()
                elif not serie in modelo.listaTurmas[escola].keys():
                        modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()

    #####  Etapa 2b: contabiliza a demanda de alunos de formulario  #####
    for k in tabelaAlunoForm.index:
        escola = tabelaAlunoForm['escola_id'][k]
        serie = tabelaAlunoForm['serie_id'][k]
        anoReferencia = tabelaAlunoForm['ano_referencia'][k]

        ordem = tabelaSerie['ordem'][serie]
        ordem += modelo.anoPlanejamento - anoReferencia

        if ordem <= modelo.ordemUltimaSerie:
            serie = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
            if tabelaSerie['ativa'][serie] == 1:
                if not escola in modelo.listaTurmas.keys():
                    modelo.listaTurmas[escola] = {}
                    modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()
                elif not serie in modelo.listaTurmas[escola].keys():
                    modelo.listaTurmas[escola][serie] = dicionarioFinalListaTurmas()

                modelo.listaTurmas[escola][serie]['demanda'] += 1

    #####  Etapa 3: abertura de turmas suficientes para atender formulario e repetentes #####
    for escola in modelo.listaTurmas.keys():
        for serie in modelo.listaTurmas[escola].keys():
            demandaTotal = modelo.listaTurmas[escola][serie]['demanda']

            if modelo.otimizaNoAno == 0 and (escola, serie) in demandaRepetentes.keys():
                demandaTotal += demandaRepetentes[(escola, serie)]

            qtdTurmasNovas = ceil(demandaTotal/modelo.maxAlunos)

            qtdTurmasCont = len(modelo.listaTurmas[escola][serie]['turmas'])
            for c in range(1, qtdTurmasNovas + 1):
                chave = (escola, serie, qtdTurmasCont + c)
                modelo.listaTurmas[escola][serie]['turmas'].append(chave)
                modelo.listaTurmas[escola][serie]['aprova'][chave] = 0

####################################
#####  ALUNOS DE CONTINUIDADE  #####
####################################
def calculaNovaSerieCont(serie, reprova, otimizaNoAno, ordemUltimaSerie, tabelaSerie):
    """
    Dada a situacao de um aluno de continuidade, retorna a nova serie que o aluno deve cursar.
    Caso nao exista uma serie adequada, retorna 'None' (isso ocorre somente quando o aluno finaliza
    as series disponibilizadas pela ONG).

    Obs: nao e necessario tratar o problema de serie fechada para aluno de continuidade pois isso foi tratado na
    funcao 'verificaDemandaTurmas'.
    """
    if otimizaNoAno == 1 or reprova == 1:
        novaSerie = serie
    else:
        ordem = tabelaSerie['ordem'][serie] + 1

        if ordem <= ordemUltimaSerie:
            novaSerie = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
        else:
            novaSerie = None

    return novaSerie

def verificaTurmasPossiveisAlunoCont(aluno, escola, serie, reprova, continua, otimizaNoAno, ordemUltimaSerie, tabelaSerie, listaTurmas):
    """
    Dada a situacao de um aluno de continuidade, retorna todas as turmas em que o aluno pode se matricular.
    Caso nao exista ao menos uma turma adequada, retorna 'None' (isso ocorre somente quando o aluno finaliza
    as series disponibilizadas pela ONG).
    """
    if continua == 1:
        novaSerie = calculaNovaSerieCont(serie, reprova, otimizaNoAno, ordemUltimaSerie, tabelaSerie)
        if novaSerie is None:
            turmasPossiveis = None
        else:
            turmasPossiveis = listaTurmas[escola][novaSerie]['turmas']
            listaTurmas[escola][novaSerie]['alunosPossiveis']['cont'].append(aluno)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def preparaDadosAlunosContinuidade(modelo, tabelaTurma, tabelaSerie, tabelaAlunoCont):
    """
    Analisa a situacao de cada aluno de continuidade, configurando as turmas para as quais ele pode ser matriculado
    e completando a estrutura 'Modelo.listaTurmas'.
    """
    for i in tabelaAlunoCont.index:
        turma = tabelaAlunoCont['turma_id'][i]
        reprova = tabelaAlunoCont['reprova'][i]
        continua = tabelaAlunoCont['continua'][i]
        escola = tabelaTurma['escola_id'][turma]
        serie = tabelaTurma['serie_id'][turma]

        turmasPossiveis = verificaTurmasPossiveisAlunoCont(i, escola, serie, reprova, continua, modelo.otimizaNoAno,
                                                           modelo.ordemUltimaSerie, tabelaSerie, modelo.listaTurmas)

        if not turmasPossiveis is None:
            if modelo.otimizaNoAno == 0 and reprova == 1:
                modelo.reprovou[i] = True
            else:
                modelo.reprovou[i] = False

            modelo.mesmaTurma[i] = {}
            for j in modelo.alunoCont.keys():
                if tabelaAlunoCont['turma_id'][j] == turma:
                    modelo.mesmaTurma[i][j] = True
                    modelo.mesmaTurma[j][i] = True
                else:
                    modelo.mesmaTurma[i][j] = False
                    modelo.mesmaTurma[j][i] = False

            modelo.mesmaTurma[i][i] = False ##  Para excluir restricoes redundantes
            modelo.alunoCont[i] = turmasPossiveis

##################################
#####  ALUNOS DE FORMULARIO  #####
##################################
def calculaNovaSerieForm(serie, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie):
    """
    Dada a situacao de um aluno de formulario, calcula a serie adequada em que esse aluno pode ser matriculado.
    Se a serie que ele deve ser destinado nao esta ativa ou se o aluno ja passou pela ultima serie atendida pela ONG,
    entao, nao existe uma serie apropriada. Nesse caso, retorna 'None'.
    """
    ordem = tabelaSerie['ordem'][serie] + anoPlanejamento - anoReferencia

    if ordem <= ordemUltimaSerie:
        novaSerie = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]

        if tabelaSerie['ativa'][novaSerie] == 0:
            novaSerie = None
    else:
        novaSerie = None

    return novaSerie

def verificaTurmasPossiveisParaAlunoForm(aluno, escola, serie, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie, listaTurmas):
    """
    Dada a situacao de um aluno de formulario, retorna todas as turmas em que esse aluno pode ser matriculado.
    Caso nao exista ao menos uma turma adequada (se 'calculaNovaSerieForm' retornou 'None'), retorna 'None'.
    """
    novaSerie = calculaNovaSerieForm(serie, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie)
    if not novaSerie is None:
        turmasPossiveis = listaTurmas[escola][novaSerie]['turmas']
        listaTurmas[escola][novaSerie]['alunosPossiveis']['form'].append(aluno)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def aluno_k_antesDo_l(dataAluno_k, dataAluno_l):
    """
    Retorna 'True' se o aluno k se inscreveu antes do l e 'False' caso contrario. Em caso de empate,
    a escolha e feita aleatoriamente.
    """
    dataInscr_k = datetime.strptime(dataAluno_k, '%d/%m/%Y %H:%M:%S')
    dataInscr_l = datetime.strptime(dataAluno_l, '%d/%m/%Y %H:%M:%S')

    if dataInscr_k < dataInscr_l:
        return True
    elif dataInscr_l < dataInscr_k:
        return False
    else:
        if uniform(0, 1) < 0.5:
            return True

    return False

def preparaDadosAlunosFormulario(modelo, tabelaSerie, tabelaAlunoForm, listaTurmas):
    """
    Analisa a situacao de cada aluno de formulario, configurando as turmas para as quais eles podem ser matriculados
    e completando a estrutura 'Modelo.listaTurmas'.
    """
    for k in tabelaAlunoForm.index:
        escola = tabelaAlunoForm['escola_id'][k]
        serie = tabelaAlunoForm['serie_id'][k]
        dataAluno_k = tabelaAlunoForm['data_inscricao'][k]
        anoReferencia = tabelaAlunoForm['ano_referencia'][k]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoForm(k, escola, serie, anoReferencia, modelo.anoPlanejamento,
                                                               modelo.ordemUltimaSerie, tabelaSerie, listaTurmas)
        if not turmasPossiveis is None:
            modelo.ordemForm[k] = {}

            for l in modelo.alunoForm.keys():
                dataAluno_l = tabelaAlunoForm['data_inscricao'][l]

                if aluno_k_antesDo_l(dataAluno_k, dataAluno_l):
                    modelo.ordemForm[k][l] = True
                    modelo.ordemForm[l][k] = False
                else:
                    modelo.ordemForm[l][k] = True
                    modelo.ordemForm[k][l] = False

            modelo.ordemForm[k][k] = False
            modelo.alunoForm[k] = turmasPossiveis

########################
#####  PRE-SOLVER  #####
########################
def preSolver(modelo):
    """
    PRE-SOLVER
    ----------
    Etapa fundamental na resolucao do problema. Resposavel por construir corretamente as estruturas
    - Modelo().listaTurmas
    - Modelo().alunoCont
    - Modelo().alunoForm
    - Modelo().mesmaTurma
    - Modelo().reprovou
    - Modelo().ordemForm
    Uma parte do problema e resolvida na construcao dessas estruturas, como por exemplo, em qual escola ou
    serie os alunos de continuidade devem ser matriculados. Isso permite uma simplificacao do modelo, reduzindo a
    quantidade de variaveis de decisao e de restricoes.

    Retorna o tempo de execucao total do pre-solver.
    """
    start = time.time()
    verificaDemandaTurmas(modelo, modelo.tabelaTurma, modelo.tabelaAlunoCont, modelo.tabelaAlunoForm, modelo.tabelaSerie)

    preparaDadosAlunosContinuidade(modelo, modelo.tabelaTurma, modelo.tabelaSerie, modelo.tabelaAlunoCont)

    preparaDadosAlunosFormulario(modelo, modelo.tabelaSerie, modelo.tabelaAlunoForm, modelo.listaTurmas)
    stop = time.time()

    return start - stop
