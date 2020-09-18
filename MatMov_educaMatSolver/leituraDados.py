import sqlite3
import pandas as pd
from datetime import datetime

databaseFilePath = 'data/database.db'

def aberturaTabelas(databaseFilePath):
    database = sqlite3.connect(databaseFilePath)

    tabelaRegiao = pd.read_sql_query('SELECT * FROM regiao', database, index_col= 'id')
    tabelaEscola = pd.read_sql_query('SELECT * FROM escola', database, index_col= 'id')
    tabelaTurma = pd.read_sql_query('SELECT * FROM turma', database, index_col= 'id')
    tabelaSerie = pd.read_sql_query('SELECT * FROM serie', database, index_col= 'id')

    tabelaAlunoCont = pd.read_sql_query('SELECT * FROM aluno', database, index_col= 'id')
    tabelaAlunoForm = pd.read_sql_query('SELECT * FROM formulario_inscricao', database, index_col= 'id')

    return tabelaRegiao, tabelaEscola, tabelaTurma, tabelaSerie, tabelaAlunoCont, tabelaAlunoForm

def verificaDemandaTurmas():
    listaTurmas = {}

    return listaTurmas

def calculaNovaSerieIdCont(serie_id, reprova, tabelaSeries):
    if reprova == 1:
        novaSerie_id = serie_id
    else:
        if serie_id == tabelaSeries.tail(1).index[0]: #Se ele foi aprovado, e esta no ultimo ano de curso fornecido, ele deve ser desconsiderado do problema
            novaSerie_id = None
        else:
            novaSerie_id = serie_id + 1
    return novaSerie_id

def calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, tabelaSeries):
    #Ano planejamento >= anoReferencia SEMPRE
    totalPassAno = anoPlanejamento - anoReferencia + 1 # + 1 para o planejamento entre anos
    novaSerie_id = serie_id + totalPassAno
    if novaSerie_id > tabelaSeries.tail(1).index[0]:
        novaSerie_id = None

    return novaSerie_id

def verificaTurmasPossiveisParaAlunoCont(cpf, escola_id, serie_id, reprova, continua, tabelaSeries, listaTurmas):
    if continua == 1:
        novaSerie_id = calculaNovaSerieIdCont(serie_id, reprova, tabelaSeries)
        if novaSerie_id != None:
            turmasPossiveis = listaTurmas[escola_id][novaSerie_id][0]
            listaTurmas[escola_id][novaSerie_id][1][0].append(cpf)
        else:
            turmasPossiveis = None
    else:
        turmasPossiveis = None

    return turmasPossiveis


def verificaTurmasPossiveisParaAlunoForm(cpf, escola_id, serie_id, anoReferencia, anoPlanejamento, tabelaSeries, listaTurmas):
    novaSerie_id = calculaNovaSerieIdForm(serie_id, anoReferencia, anoPlanejamento, tabelaSeries)
    if novaSerie_id != None:
        turmasPossiveis = listaTurmas[escola_id][novaSerie_id][0]
        listaTurmas[escola_id][novaSerie_id][1][1].append(cpf)
    else:
        turmasPossiveis = None

    return turmasPossiveis

def aluno_i_antesDo_j(dataAluno_i, dataAluno_j):
    dataInscr_i = datetime.strptime(dataAluno_i, '%d/%m/%Y %H:%M:%S')
    dataInscr_j = datetime.strptime(dataAluno_j, '%d/%m/%Y %H:%M:%S')

    if dataInscr_i < dataInscr_j:
        return True

    return False

def leituraDadosAlunosContinuidade(data, listaTurmas):
    tabelaAlunos = pd.read_sql_query('SELECT * FROM aluno', data)
    tabelaAlunos.index = pd.RangeIndex(start= 1, stop= len(tabelaAlunos.index) + 1)

    tabelaTurmas = pd.read_sql_query('SELECT * FROM turma', data)
    tabelaTurmas.index = pd.RangeIndex(start= 1, stop= len(tabelaTurmas.index) + 1)

    tabelaEscolas = pd.read_sql_query('SELECT * FROM escola', data)
    tabelaEscolas.index = pd.RangeIndex(start= 1, stop= len(tabelaEscolas.index) + 1)

    tabelaSeries = pd.read_sql_query('SELECT * FROM serie', data)
    tabelaSeries.index = pd.RangeIndex(start= 1, stop= len(tabelaSeries.index) + 1)

    alunosCont = {}
    reprovou = {}
    mesmaTurma = {}
    for i in tabelaAlunos.index:
        cpf = tabelaAlunos['cpf'][i]
        turma_id = tabelaAlunos['turma_id'][i]
        reprova = tabelaAlunos['reprova'][i]
        continua = tabelaAlunos['continua'][i]

        escola_id = tabelaTurmas['escola_id'][turma_id]
        serie_id = tabelaTurmas['serie_id'][turma_id]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoCont(cpf, escola_id, serie_id, reprova, continua, tabelaSeries, listaTurmas)
        if turmasPossiveis != None:
            alunosCont[cpf] = turmasPossiveis

            if reprova == 1:
                reprovou[cpf] = True
            else:
                reprovou[cpf] = False

            for cpf_j in alunosCont.keys():
                j = tabelaAlunos.query("cpf == '{}'".format(cpf_j)).index[0] ##Assumimos que tera somente um elemento (esperamos que o front-end cuide disso)

                if tabelaAlunos['turma_id'][j] == turma_id: ##Turma do i == turma do j -> estudaram na mesma turma
                    mesmaTurma[cpf][cpf_j] = True
                    mesmaTurma[cpf_j][cpf] = True
                else:
                    mesmaTurma[cpf][cpf_j] = False
                    mesmaTurma[cpf_j][cpf] = False

    return alunosCont, reprovou, mesmaTurma

def leituraDadosAlunosFormulario(anoPlanejamento, data, listaTurmas):
    tabelaAlunos = pd.read_sql_query('SELECT * FROM formulario_inscricao', data)
    tabelaAlunos.index = pd.RangeIndex(start= 1, stop= len(tabelaAlunos.index) + 1)

    tabelaSeries = pd.read_sql_query('SELECT * FROM serie', data)
    tabelaSeries.index = pd.RangeIndex(start= 1, stop= len(tabelaSeries.index) + 1)

    alunosForm = {}
    ordemForm = {}
    for i in tabelaAlunos.index:
        cpf = tabelaAlunos['cpf'][i]
        escola_id = tabelaAlunos['escola_id'][i]
        serie_id = tabelaAlunos['serie_id'][i]
        dataAluno_i = tabelaAlunos['data_inscricao'][i]
        anoReferencia = tabelaAlunos['ano_referencia'][i]

        turmasPossiveis = verificaTurmasPossiveisParaAlunoForm(cpf, escola_id, serie_id, anoReferencia, anoPlanejamento, tabelaSeries, listaTurmas)
        if turmasPossiveis != None:
            for cpf_j in alunosForm.keys():
                j = tabelaAlunos.query("cpf == '{}'".format(cpf_j)).index[0] ##Assumimos que tera somente um elemento (esperamos que o front-end cuide disso)
                dataAluno_j = tabelaAlunos['data_inscricao'][j]

                if aluno_i_antesDo_j(dataAluno_i, dataAluno_j):
                    ordemForm[cpf][cpf_j] = True
                    ordemForm[cpf_j][cpf] = False
                else:
                    ordemForm[cpf_j][cpf] = True
                    ordemForm[cpf][cpf_j] = False

            alunosForm[cpf] = turmasPossiveis
            ordemForm[cpf][cpf] = False

    return alunosForm, ordemForm
