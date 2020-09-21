from datetime import datetime
from math import ceil

def verificaDemandaTurmas(modelo, anoPlanejamento, otimizaNoAno, tabelaTurma, tabelaAlunoCont, tabelaAlunoForm, tabelaSerie):
    #Contabiliza as turmas ja existentes
    for t in tabelaTurma.index:
        escola_id = tabelaTurma['escola_id'][t]
        serie_id = tabelaTurma['serie_id'][t]

        if otimizaNoAno == 0:
            serie_id = serie_id + 1

        if serie_id <= tabelaSerie.tail(1).index[0]: #Exclui anos alem do ultimo ano oferecido
            if not escola_id in modelo.listaTurmas.keys():
                modelo.listaTurmas[escola_id] = {}
                modelo.listaTurmas[escola_id][serie_id] = {'turmas': [(escola_id, serie_id, 1)],
                                                        'alunosPossiveis': {'cont': [], 'form': []},
                                                        'demanda': 0}
            elif not serie_id in modelo.listaTurmas[escola_id].keys():
                modelo.listaTurmas[escola_id][serie_id] = {'turmas': [(escola_id, serie_id, 1)],
                                                        'alunosPossiveis': {'cont': [], 'form': []},
                                                        'demanda': 0}
            else:
                totalTurmas = modelo.listaTurmas[escola_id][serie_id]['turmas']
                modelo.listaTurmas[escola_id][serie_id]['turmas'].append((escola_id, serie_id, len(totalTurmas) + 1))

    #Adiciona turmas suficientes para atender todo o formulario
    for i in tabelaAlunoForm.index:
        escola_id = tabelaAlunoForm['escola_id'][i]
        serie_id = tabelaAlunoForm['serie_id'][i]
        anoReferencia = tabelaAlunoForm['ano_referencia'][i]

        serie_id = serie_id + anoPlanejamento - anoReferencia

        if otimizaNoAno == 0:
            serie_id = serie_id + 1

        if serie_id <= tabelaSerie.tail(1).index[0]: #Exclui anos alem do ultimo ano oferecido
            if not escola_id in modelo.listaTurmas.keys():
                modelo.listaTurmas[escola_id] = {}
                modelo.listaTurmas[escola_id][serie_id] = {'turmas': [],
                                                        'alunosPossiveis': {'cont': [], 'form': []},
                                                        'demanda': 1}
            elif not serie_id in modelo.listaTurmas[escola_id].keys():
                modelo.listaTurmas[escola_id][serie_id] = {'turmas': [],
                                                        'alunosPossiveis': {'cont': [], 'form': []},
                                                        'demanda': 1}
            else:
                modelo.listaTurmas[escola_id][serie_id]['demanda'] = modelo.listaTurmas[escola_id][serie_id]['demanda'] + 1

    for escola_id in modelo.listaTurmas.keys():
        for serie_id in modelo.listaTurmas[escola_id].keys():
            totalReprovados = 0
            for turma_id in tabelaTurma[(tabelaTurma['escola_id'] == escola_id) & (tabelaTurma['serie_id'] == serie_id)].index:
                totalReprovados = totalReprovados + len(tabelaAlunoCont[(tabelaAlunoCont['turma_id'] == turma_id) & (tabelaAlunoCont['reprova'] == 1)].index)

            demandaTotal = modelo.listaTurmas[escola_id][serie_id]['demanda'] + totalReprovados
            qtdTurmasNovas = ceil(demandaTotal/(modelo.maxAlunos))

            totalTurmasObrigatorias = len(modelo.listaTurmas[escola_id][serie_id]['turmas'])
            for t in range(1, qtdTurmasNovas + 1):
                modelo.listaTurmas[escola_id][serie_id]['turmas'].append((escola_id, serie_id, totalTurmasObrigatorias + t))

#####  ALUNOS DE CONTINUIDADE  #####
def calculaNovaSerieIdCont(serie_id, reprova, otimizaNoAno, ordemUltimaSerie, tabelaSerie):
    if reprova == 1 or otimizaNoAno == 1: #O aluno nao muda de serie
        novaSerie_id = serie_id
    else:
        ordem = tabelaSerie['ordem'][serie_id] + 1 ##Passou de ano

        if ordem <= ordemUltimaSerie:
            novaSerie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
        else:
            novaSerie_id = None

    if (novaSerie_id != None) and (tabelaSerie['ativa'][novaSerie_id] == 0):
        novaSerie_id = None

    return novaSerie_id

def verificaTurmasPossiveisParaAlunoCont(aluno_id, escola_id, serie_id, reprova, continua, otimizaNoAno, ordemUltimaSerie, tabelaSerie, listaTurmas):
    if continua == 1:
        novaSerie_id = calculaNovaSerieIdCont(serie_id, reprova, otimizaNoAno, ordemUltimaSerie, tabelaSerie)
        if novaSerie_id is None:
            turmasPossiveis = None
        else:
            turmasPossiveis = listaTurmas[escola_id][novaSerie_id]['turmas']
            listaTurmas[escola_id][novaSerie_id]['alunosPossiveis']['cont'].append(aluno_id)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def preparaDadosAlunosContinuidade(modelo, tabelaTurma, tabelaSerie, tabelaAlunoCont, listaTurmas):
    for i in tabelaAlunoCont.index:
        turma_id = tabelaAlunoCont['turma_id'][i]
        reprova = tabelaAlunoCont['reprova'][i]
        continua = tabelaAlunoCont['continua'][i]

        escola_id = tabelaTurma['escola_id'][turma_id]
        serie_id = tabelaTurma['serie_id'][turma_id]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoCont(i, escola_id, serie_id, reprova, continua, modelo.otimizaNoAno, modelo.ordemUltimaSerie, tabelaSerie, listaTurmas)
        if not turmasPossiveis is None:
            if reprova == 1:
                modelo.reprovou[i] = True
            else:
                modelo.reprovou[i] = False

            modelo.mesmaTurma[i] = {}

            for j in modelo.alunoCont.keys():
                if tabelaAlunoCont['turma_id'][j] == turma_id: ##Turma do i == turma do j -> estudaram na mesma turma
                    modelo.mesmaTurma[i][j] = True
                    modelo.mesmaTurma[j][i] = True
                else:
                    modelo.mesmaTurma[i][j] = False
                    modelo.mesmaTurma[j][i] = False

            modelo.mesmaTurma[i][i] = False
            modelo.alunoCont[i] = turmasPossiveis

#####  ALUNOS DE FORMULARIO  #####
def calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, ordemUltimaSerie, tabelaSerie):
    #Ano planejamento >= anoReferencia SEMPRE
    if otimizaNoAno == 1:
        totalPassAno = anoPlanejamento - anoReferencia
    else:
        totalPassAno = anoPlanejamento - anoReferencia + 1 # + 1 para o planejamento entre anos

    ordem = tabelaSerie['ordem'][serie_id] + totalPassAno

    if ordem <= ordemUltimaSerie:
        novaSerie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]

        if tabelaSerie['ativa'][novaSerie_id] == 0:
            novaSerie_id = None
    else:
        novaSerie_id = None

    return novaSerie_id

def verificaTurmasPossiveisParaAlunoForm(aluno_id, escola_id, serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, ordemUltimaSerie, tabelaSerie, listaTurmas):
    novaSerie_id = calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, ordemUltimaSerie, tabelaSerie)
    if not novaSerie_id is None:
        turmasPossiveis = listaTurmas[escola_id][novaSerie_id]['turmas']
        listaTurmas[escola_id][novaSerie_id]['alunosPossiveis']['form'].append(aluno_id)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def aluno_i_antesDo_j(dataAluno_i, dataAluno_j):
    dataInscr_i = datetime.strptime(dataAluno_i, '%d/%m/%Y %H:%M:%S')
    dataInscr_j = datetime.strptime(dataAluno_j, '%d/%m/%Y %H:%M:%S')

    if dataInscr_i < dataInscr_j:
        return True

    return False

def preparaDadosAlunosFormulario(modelo, tabelaSerie, tabelaAlunoForm, listaTurmas):
    for i in tabelaAlunoForm.index:
        escola_id = tabelaAlunoForm['escola_id'][i]
        serie_id = tabelaAlunoForm['serie_id'][i]
        dataAluno_i = tabelaAlunoForm['data_inscricao'][i]
        anoReferencia = tabelaAlunoForm['ano_referencia'][i]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoForm(i, escola_id, serie_id, anoReferencia, modelo.anoPlanejamento, modelo.otimizaNoAno, modelo.ordemUltimaSerie, tabelaSerie, listaTurmas)
        if not turmasPossiveis is None:
            modelo.ordemForm[i] = {}

            for j in modelo.alunoForm.keys():
                dataAluno_j = tabelaAlunoForm['data_inscricao'][j]

                if aluno_i_antesDo_j(dataAluno_i, dataAluno_j):
                    modelo.ordemForm[i][j] = True
                    modelo.ordemForm[j][i] = False
                else:
                    modelo.ordemForm[j][i] = True
                    modelo.ordemForm[i][j] = False

            modelo.ordemForm[i][i] = False
            modelo.alunoForm[i] = turmasPossiveis

def preSolve(modelo):
    verificaDemandaTurmas(modelo, modelo.anoPlanejamento, modelo.otimizaNoAno, modelo.tabelaTurma, modelo.tabelaAlunoCont,
                        modelo.tabelaAlunoForm, modelo.tabelaSerie)
    print("\nVerificou Demanda\n")

    preparaDadosAlunosContinuidade(modelo, modelo.tabelaTurma, modelo.tabelaSerie, modelo.tabelaAlunoCont, modelo.listaTurmas)
    print("Preparou Continuidade\n")

    preparaDadosAlunosFormulario(modelo, modelo.tabelaSerie, modelo.tabelaAlunoForm, modelo.listaTurmas)
    print("Preparou Form\n")
