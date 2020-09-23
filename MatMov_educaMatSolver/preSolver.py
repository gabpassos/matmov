from datetime import datetime
from math import ceil

class ErroSerieContinuidadeFechada(Exception):
    def __init__(self, serie):
        self.serie = serie

    def __str__(self):
        return 'ERRO! A serie "{}" esta fechada. Para atender a demanda dos alunos de continuidade ela deve ser aberta.'.format(self.serie)

###Tem que verificar todos os repetentes para evitar infactibilidade
def verificaDemandaTurmas(modelo, tabelaTurma, tabelaAlunoCont, tabelaAlunoForm, tabelaSerie):
    #Contabiliza as turmas ja existentes e leva elas para o proximo ano (da conta de atender todos os alunos de continuidade nao repetentes)
    for t in tabelaTurma.index:
        escola_id = tabelaTurma['escola_id'][t]
        serie_id = tabelaTurma['serie_id'][t]
        ordem = tabelaSerie['ordem'][serie_id]

        if modelo.otimizaNoAno == 0:
            ordem += 1

        if ordem <= modelo.ordemUltimaSerie:
            serie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
            if tabelaSerie['ativa'][serie_id] == 1:
                if not escola_id in modelo.listaTurmas.keys():
                    modelo.listaTurmas[escola_id] = {}
                    modelo.listaTurmas[escola_id][serie_id] = {'turmas': [(escola_id, serie_id, 1)],
                                                            'alunosPossiveis': {'cont': [], 'form': []},
                                                            'aprova': {(escola_id, serie_id, 1): 0},
                                                            'demanda': 0}
                elif not serie_id in modelo.listaTurmas[escola_id].keys():
                    modelo.listaTurmas[escola_id][serie_id] = {'turmas': [(escola_id, serie_id, 1)],
                                                            'alunosPossiveis': {'cont': [], 'form': []},
                                                            'aprova': {(escola_id, serie_id, 1): 0},
                                                            'demanda': 0}
                else:
                    totalTurmas = len(modelo.listaTurmas[escola_id][serie_id]['turmas'])
                    modelo.listaTurmas[escola_id][serie_id]['turmas'].append((escola_id, serie_id, totalTurmas + 1))
                    modelo.listaTurmas[escola_id][serie_id]['aprova'][(escola_id, serie_id, totalTurmas + 1)] = 0
            else:
                raise ErroSerieContinuidadeFechada(tabelaSerie['nome'][serie_id])

    #Nao cria turma, so contabiliza a demanda para posteriormente criar turmas suficientes para atender todo o formulario
    for i in tabelaAlunoForm.index:
        escola_id = tabelaAlunoForm['escola_id'][i]
        serie_id = tabelaAlunoForm['serie_id'][i]
        anoReferencia = tabelaAlunoForm['ano_referencia'][i]
        ordem = tabelaSerie['ordem'][serie_id]

        ordem += modelo.anoPlanejamento - anoReferencia
        if ordem <= modelo.ordemUltimaSerie:
            serie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
            if tabelaSerie['ativa'][serie_id] == 1:
                if not escola_id in modelo.listaTurmas.keys():
                    modelo.listaTurmas[escola_id] = {}
                    modelo.listaTurmas[escola_id][serie_id] = {'turmas': [],
                                                            'alunosPossiveis': {'cont': [], 'form': []},
                                                            'aprova': {},
                                                            'demanda': 1}
                elif not serie_id in modelo.listaTurmas[escola_id].keys():
                    modelo.listaTurmas[escola_id][serie_id] = {'turmas': [],
                                                            'alunosPossiveis': {'cont': [], 'form': []},
                                                            'aprova': {},
                                                            'demanda': 1}
                else:
                    modelo.listaTurmas[escola_id][serie_id]['demanda'] += 1

    for escola_id in modelo.listaTurmas.keys():
        for serie_id in modelo.listaTurmas[escola_id].keys():
            totalReprovados = 0
            if modelo.otimizaNoAno == 0: #Se otimiza de um ano para o outro, contabiliza os repetentes
                for turma_id in tabelaTurma[(tabelaTurma['escola_id'] == escola_id) & (tabelaTurma['serie_id'] == serie_id)].index:
                    totalReprovados += len(tabelaAlunoCont[(tabelaAlunoCont['turma_id'] == turma_id) & (tabelaAlunoCont['reprova'] == 1) & (tabelaAlunoCont['continua'] == 1)].index)

            demandaTotal = modelo.listaTurmas[escola_id][serie_id]['demanda'] + totalReprovados
            qtdTurmasNovas = ceil(demandaTotal/(modelo.maxAlunos)) #Turmas novas necessarias para atender todo o formulario (e repetentes quando necessario)

            totalTurmasObrigatorias = len(modelo.listaTurmas[escola_id][serie_id]['turmas'])
            for t in range(1, qtdTurmasNovas + 1):
                modelo.listaTurmas[escola_id][serie_id]['turmas'].append((escola_id, serie_id, totalTurmasObrigatorias + t))
                modelo.listaTurmas[escola_id][serie_id]['aprova'][(escola_id, serie_id, totalTurmasObrigatorias + t)] = 0

#####  ALUNOS DE CONTINUIDADE  #####
def calculaNovaSerieIdCont(serie_id, reprova, otimizaNoAno, ordemUltimaSerie, tabelaSerie):
    if reprova == 1 or otimizaNoAno == 1: #O aluno nao muda de serie
        novaSerie_id = serie_id
    else:
        ordem = tabelaSerie['ordem'][serie_id] + 1 ##Passou de ano

        if ordem <= ordemUltimaSerie:
            novaSerie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]
        else:
            novaSerie_id = None #A ONG nao atende series maiores("Terminou o ensino medio")

    if (not novaSerie_id is None) and (tabelaSerie['ativa'][novaSerie_id] == 0):
        raise ErroSerieContinuidadeFechada(tabelaSerie['nome'][serie_id])

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
            if modelo.otimizaNoAno == 0 and reprova == 1: #O caso de reprova deve ser considerado somente no planejamento entre anos
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

            modelo.mesmaTurma[i][i] = False #Para nao adicionar restricoes desnecessarias
            modelo.alunoCont[i] = turmasPossiveis

#####  ALUNOS DE FORMULARIO  #####
def calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie):
    #Ano planejamento >= anoReferencia SEMPRE
    ordem = tabelaSerie['ordem'][serie_id] + anoPlanejamento - anoReferencia

    if ordem <= ordemUltimaSerie:
        novaSerie_id = tabelaSerie[(tabelaSerie['ordem'] == ordem)].index[0]

        if tabelaSerie['ativa'][novaSerie_id] == 0: #Aqui, se a serie de destino nao esta ativa, basta desconsiderar o aluno de formulario
            novaSerie_id = None
    else:
        novaSerie_id = None

    return novaSerie_id

def verificaTurmasPossiveisParaAlunoForm(aluno_id, escola_id, serie_id, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie, listaTurmas):
    novaSerie_id = calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, ordemUltimaSerie, tabelaSerie)
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

        turmasPossiveis = verificaTurmasPossiveisParaAlunoForm(i, escola_id, serie_id, anoReferencia, modelo.anoPlanejamento, modelo.ordemUltimaSerie, tabelaSerie, listaTurmas)
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
    verificaDemandaTurmas(modelo, modelo.tabelaTurma, modelo.tabelaAlunoCont, modelo.tabelaAlunoForm, modelo.tabelaSerie)

    preparaDadosAlunosContinuidade(modelo, modelo.tabelaTurma, modelo.tabelaSerie, modelo.tabelaAlunoCont, modelo.listaTurmas)

    preparaDadosAlunosFormulario(modelo, modelo.tabelaSerie, modelo.tabelaAlunoForm, modelo.listaTurmas)
