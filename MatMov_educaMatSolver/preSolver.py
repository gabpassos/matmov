import sqlite3
import pandas as pd
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
def calculaNovaSerieIdCont(serie_id, reprova, otimizaNoAno, tabelaSerie):
    if reprova == 1 or otimizaNoAno == 1:
        novaSerie_id = serie_id
    else:
        #Se ele foi aprovado, planejamos de um ano para o outro e esta no ultimo ano de curso fornecido, aluno desconsiderado do problema
        if serie_id == tabelaSerie.tail(1).index[0]:
            novaSerie_id = None
        else:
            novaSerie_id = serie_id + 1
    return novaSerie_id

def verificaTurmasPossiveisParaAlunoCont(cpf, escola_id, serie_id, reprova, continua, otimizaNoAno, tabelaSerie, listaTurmas):
    if continua == 1:
        novaSerie_id = calculaNovaSerieIdCont(serie_id, reprova, otimizaNoAno, tabelaSerie)
        if novaSerie_id is None:
            turmasPossiveis = None
        else:
            turmasPossiveis = listaTurmas[escola_id][novaSerie_id]['turmas']
            listaTurmas[escola_id][novaSerie_id]['alunosPossiveis']['cont'].append(cpf)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def preparaDadosAlunosContinuidade(modelo, tabelaTurma, tabelaSerie, tabelaAlunoCont, listaTurmas):
    for i in tabelaAlunoCont.index:
        cpf = tabelaAlunoCont['cpf'][i]
        turma_id = tabelaAlunoCont['turma_id'][i]
        reprova = tabelaAlunoCont['reprova'][i]
        continua = tabelaAlunoCont['continua'][i]

        escola_id = tabelaTurma['escola_id'][turma_id]
        serie_id = tabelaTurma['serie_id'][turma_id]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoCont(cpf, escola_id, serie_id, reprova, continua, modelo.otimizaNoAno, tabelaSerie, listaTurmas)
        if not turmasPossiveis is None:
            if reprova == 1:
                modelo.reprovou[cpf] = True
            else:
                modelo.reprovou[cpf] = False

            modelo.mesmaTurma[cpf] = {}

            for cpf_j in modelo.alunoCont.keys():
                j = tabelaAlunoCont.query("cpf == '{}'".format(cpf_j)).index[0] ##Assumimos que tera somente um elemento (esperamos que o front-end cuide disso)

                if tabelaAlunoCont['turma_id'][j] == turma_id: ##Turma do i == turma do j -> estudaram na mesma turma
                    modelo.mesmaTurma[cpf][cpf_j] = True
                    modelo.mesmaTurma[cpf_j][cpf] = True
                else:
                    modelo.mesmaTurma[cpf][cpf_j] = False
                    modelo.mesmaTurma[cpf_j][cpf] = False

            modelo.mesmaTurma[cpf][cpf] = False
            modelo.alunoCont[cpf] = turmasPossiveis

#####  ALUNOS DE FORMULARIO  #####
def calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, tabelaSerie):
    #Ano planejamento >= anoReferencia SEMPRE
    if otimizaNoAno == 1:
        totalPassAno = anoPlanejamento - anoReferencia
    else:
        totalPassAno = anoPlanejamento - anoReferencia + 1 # + 1 para o planejamento entre anos

    novaSerie_id = serie_id + totalPassAno

    #Verifica se ultrapassou o limite de atendimento das series
    if novaSerie_id > tabelaSerie.tail(1).index[0]:
        novaSerie_id = None

    return novaSerie_id

def verificaTurmasPossiveisParaAlunoForm(cpf, escola_id, serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, tabelaSerie, listaTurmas):
    novaSerie_id = calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, otimizaNoAno, tabelaSerie)
    if not novaSerie_id is None:
        turmasPossiveis = listaTurmas[escola_id][novaSerie_id]['turmas']
        listaTurmas[escola_id][novaSerie_id]['alunosPossiveis']['form'].append(cpf)
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
    cpfRepetido = {}
    for i in tabelaAlunoForm.index:
        cpf = tabelaAlunoForm['cpf'][i]
        escola_id = tabelaAlunoForm['escola_id'][i]
        serie_id = tabelaAlunoForm['serie_id'][i]
        dataAluno_i = tabelaAlunoForm['data_inscricao'][i]
        anoReferencia = tabelaAlunoForm['ano_referencia'][i]

        if not cpf in cpfRepetido.keys():
            cpfRepetido[cpf] = False
        else:
            cpfRepetido[cpf] = True

        if not cpfRepetido[cpf]:
            turmasPossiveis = verificaTurmasPossiveisParaAlunoForm(cpf, escola_id, serie_id, anoReferencia, modelo.anoPlanejamento, modelo.otimizaNoAno, tabelaSerie, listaTurmas)
            if not turmasPossiveis is None:
                modelo.ordemForm[cpf] = {}

                for cpf_j in modelo.alunoForm.keys():
                    j = tabelaAlunoForm.query("cpf == '{}'".format(cpf_j)).index[0] ##Assumimos que tera somente um elemento (esperamos que o front-end cuide disso)
                    dataAluno_j = tabelaAlunoForm['data_inscricao'][j]

                    if aluno_i_antesDo_j(dataAluno_i, dataAluno_j):
                        modelo.ordemForm[cpf][cpf_j] = True
                        modelo.ordemForm[cpf_j][cpf] = False
                    else:
                        modelo.ordemForm[cpf_j][cpf] = True
                        modelo.ordemForm[cpf][cpf_j] = False

                modelo.ordemForm[cpf][cpf] = False
                modelo.alunoForm[cpf] = turmasPossiveis

def preSolve(modelo):
    verificaDemandaTurmas(modelo, modelo.anoPlanejamento, modelo.otimizaNoAno, modelo.tabelaTurma, modelo.tabelaAlunoCont,
                        modelo.tabelaAlunoForm, modelo.tabelaSerie)

    preparaDadosAlunosContinuidade(modelo, modelo.tabelaTurma, modelo.tabelaSerie, modelo.tabelaAlunoCont, modelo.listaTurmas)

    preparaDadosAlunosFormulario(modelo, modelo.tabelaSerie, modelo.tabelaAlunoForm, modelo.listaTurmas)
