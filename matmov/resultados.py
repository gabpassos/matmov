from string import ascii_uppercase
import statistics as st

import numpy as np
import matplotlib.pyplot as plt

from matmov import funcoesmod as fm

def verificaObrig(modelo, t, nome):
    """
    Verifica se a turma ```t``` com nome ```nome``` é uma turma que deve ser ativada
    obrigatoriamente ou se e uma turma opcional.
    """
    escola = t[0]
    serie = t[1]
    if len(modelo.tabelaTurma[(modelo.tabelaTurma['nome'] == nome)].index) > 0:
        modelo.listaTurmas[escola][serie]['aprova'][t] = 1
        return True
    else:
        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
            if modelo.x[i][t] == 1:
                modelo.listaTurmas[escola][serie]['aprova'][t] = 1
                return True

    return False

def aprova(modelo, t):
    """
    Retorna ```True``` se a a turma ```t``` é a provada e ```False``` caso contrario.
    """
    escola = t[0]
    serie = t[1]
    aprova = True
    if modelo.listaTurmas[escola][serie]['aprova'][t] == 0:
        if modelo.somenteTurmasObrig:
            aprova = False

    return aprova

def geraIdentTurma(modelo, tabelaSerie, tabelaEscola, tabelaRegiao):
    """
    Gera o nome das turmas da maneira com que a ONG faz atualmente, sem modificacoes.
    Para solucionar o problema de mais de uma escola na mesma regiao, adicionamos um
    contador de turmas, que vai contabilizar a 'ordem alfabetica' de maneira sequencial.
    Isto e, se duas ou mais escolas estao na mesma regiao, pode ser que uma turma comece
    a ser contabilizada numa escola a partir da letra C.

    Obs: essa funcao e responsavel por analisar quais turmas devem ser ativas ou
    opcionais e essas informacoes sao armazenadas no dicionario ```identTurma```, que
    contem o nome e o ID de cada turma. Se ```Modelo().somenteTurmasObrig = True```,
    entao ```identTurma``` contem as informacoes somente das turmas ativas.
    """
    contadorTurmas = {}
    for regiao_id in modelo.tabelaRegiao.index:
        contadorTurmas[regiao_id] = {}
        for serie_id in modelo.tabelaSerie[(modelo.tabelaSerie['ativa'] == 1)].index:
            contadorTurmas[regiao_id][serie_id] = 0

    identTurma = {}
    turma_id = 1
    for escola in modelo.listaTurmas:
        regiao_id = tabelaEscola['regiao_id'][escola]
        regiao = tabelaRegiao['nome'][regiao_id]
        for serie_id in modelo.listaTurmas[escola]:
            serie = tabelaSerie['nome'][serie_id][0]
            for t in modelo.listaTurmas[escola][serie_id]['turmas']:
                if modelo.p[t] == 1:
                    turma = ascii_uppercase[contadorTurmas[regiao_id][serie_id]]
                    nome = regiao + '_' + serie + turma

                    addTurma = True
                    ehObrig = verificaObrig(modelo, t, nome)
                    if modelo.somenteTurmasObrig:
                        if ehObrig:
                            addTurma = True
                        else:
                            addTurma = False

                    if addTurma:
                        identTurma[t] = {}
                        identTurma[t]['nome'] = nome
                        identTurma[t]['id'] = turma_id

                        turma_id += 1
                        contadorTurmas[regiao_id][serie_id] += 1

    return identTurma

def criaColunasTurmas(modelo):
    """
    Verifica as series ativas e gera as strings para criar as colunas associadas ao
    total de turmas de cada serie nas tabelas SQlite.
    """
    colunaTurmas = []
    for ordem in range(1, len(modelo.tabelaSerie.index) + 1):
        serie = modelo.tabelaSerie[(modelo.tabelaSerie['ordem'] == ordem)].index[0]
        if modelo.tabelaSerie['ativa'][serie] == 1:
            nome = modelo.tabelaSerie['nome'][serie]
            ano = nome[0]
            colunaTurmas.append('total_turmas_{} INTEGER NOT NULL, '.format(ano))

    return colunaTurmas

def iniciaDistTurmas(modelo):
    """
    Inicia variavel para contabilizar o numero de turmas em cada serie.
    """
    distTurmas = {}
    for ordem in range(1, len(modelo.tabelaSerie.index) + 1):
        serie = modelo.tabelaSerie[(modelo.tabelaSerie['ordem'] == ordem)].index[0]
        if modelo.tabelaSerie['ativa'][serie] == 1:
            distTurmas[serie] = 0

    return distTurmas

def attTabelaSolucao_sol_aluno(modelo, c, identTurma):
    """
    Atualiza os dados de solucao de alunos de continuidade na tabela SQLite. A variavel
    ```identTurma``` armazena o nome e o ID das turmas.
    """
    c.execute('DELETE FROM sol_aluno')
    alunoCont_id = 0
    for i in modelo.alunoCont:
        for t in modelo.alunoCont[i]:
            if modelo.x[i][t] == 1:
                alunoCont_id += 1

                cpf = modelo.tabelaAlunoCont['cpf'][i]
                nome = modelo.tabelaAlunoCont['nome'][i]
                email = modelo.tabelaAlunoCont['email'][i]
                telefone = modelo.tabelaAlunoCont['telefone'][i]
                responsavel = modelo.tabelaAlunoCont['nome_responsavel'][i]
                telResp = modelo.tabelaAlunoCont['telefone_responsavel'][i]
                origem = modelo.tabelaAlunoCont['nome_escola_origem'][i]

                linha = (alunoCont_id, cpf, nome, email, telefone, responsavel,
                         telResp, origem, identTurma[t]['id'])

                c.execute('INSERT INTO sol_aluno VALUES (?,?,?,?,?,?,?,?,?)', linha)
                break  ## Para de procurar nas turmas e segue para o proximo aluno

def attTabelaSolucao_sol_priorizacao_formulario(modelo, c, identTurma):
    """
    Atualiza os dados de solucao dos alunos de formulario na tabela SQLite. A variavel
    ```identTurma``` armazena o nome e o ID das turmas.

    Obs: se ```Modelo().somenteTurmasObrig = True```, serao exibidos somente os alunos
    de formulario que estao matriculados em turmas ativas.
    """
    c.execute('DELETE FROM sol_priorizacao_formulario')
    aluno_id = 0
    for k in modelo.alunoForm:
        for t in modelo.alunoForm[k]:
            escola = t[0]
            serie = t[1]
            if aprova(modelo, t):
                if modelo.y[k][t] == 1:
                    aluno_id += 1

                    cpf = modelo.tabelaAlunoForm['cpf'][k]
                    nome = modelo.tabelaAlunoForm['nome'][k]
                    email = modelo.tabelaAlunoForm['email_aluno'][k]
                    telefone = modelo.tabelaAlunoForm['telefone_aluno'][k]
                    responsavel = modelo.tabelaAlunoForm['nome_responsavel'][k]
                    telResp = modelo.tabelaAlunoForm['telefone_responsavel'][k]
                    origem = modelo.tabelaAlunoForm['nome_escola_origem'][k]

                    linha = (aluno_id, nome, cpf, email, telefone, responsavel, telResp,
                            int(escola), int(serie), origem, identTurma[t]['id'], None)

                    comando = (
                            'INSERT INTO sol_priorizacao_formulario VALUES '
                            '(?,?,?,?,?,?,?,?,?,?,?,?)'
                            )
                    c.execute(comando, linha)
                    break  ## Para de procurar nas turmas e segue para o proximo aluno

def attTabelaSolucao_sol_turma(modelo, c, identTurma):
    """
    Atualiza a tabela SQLite com as turmas liberadas pelo modelo. A variavel
    ```identTurma``` armazena o nome e o ID das turmas.

    Obs: se ```Modelo().somenteTurmasObrig = True```, serao exibidos somente as
    turmas ativas.
    """
    c.execute('DELETE FROM sol_turma')
    for t in identTurma:
        escola = t[0]
        serie = t[1]

        nome = identTurma[t]['nome']

        aprova = modelo.listaTurmas[escola][serie]['aprova'][t]
        turma_id = identTurma[t]['id']

        linha = (turma_id, nome, modelo.maxAlunos, modelo.qtdProfAcd,
                 modelo.qtdProfPedag, int(escola), int(serie), aprova)

        c.execute('INSERT INTO sol_turma VALUES (?,?,?,?,?,?,?,?)', linha)

def tabelaDistribuicaoAlunos(modelo, c, identTurma):
    """
    TABELA SOLICITADA PARA FASE FINAL!!!
    Armazena a distribuicao de alunos em cada turma.

    - Nome da tabela: distribuicao_alunos.
    - Colunas:
        - turma_id: ID da turma.
        - alunos_cont: total de alunos de continuidade na turma.
        - alunos_form: total de alunos de formulario na turma.
        - total_alunos: total de alunos na turma.
        - meta: meta a ser atingida (maximo de alunos)
        - meta_atingida_percent: percentual da meta atingido

    Obs: se ```Modelo().somenteTurmasObrig = True```, serao exibidos somente as
    turmas ativas.
    """
    schema = ('id INTEGER PRIMARY KEY NOT NULL, '
              'turma_id INTEGER NOT NULL, '
              'alunos_cont INTEGER NOT NULL, '
              'alunos_form INTEGER NOT NULL, '
              'total_alunos INTEGER NOT NULL, '
              'meta INTEGER NOT NULL, '
              'meta_atingida_percent REAL NOT NULL, '
              'FOREIGN KEY (turma_id) REFERENCES sol_turma (id)'
             )

    create = 'CREATE TABLE IF NOT EXISTS distribuicao_alunos ({})'.format(schema)

    c.execute(create)
    c.execute('DELETE FROM distribuicao_alunos')

    ID = 1
    for t in identTurma:
        escola = t[0]
        serie = t[1]

        alunosCont = 0
        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
            if modelo.x[i][t] == 1:
                alunosCont += 1

        alunosForm = 0
        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
            if modelo.y[k][t] == 1:
                alunosForm += 1

        totalAlunos = alunosCont + alunosForm
        metaPercentual = totalAlunos/modelo.maxAlunos

        linha = (ID, identTurma[t]['id'], alunosCont, alunosForm, totalAlunos,
                 modelo.maxAlunos, metaPercentual)

        c.execute('INSERT INTO distribuicao_alunos VALUES (?,?,?,?,?,?,?)', linha)

        ID += 1


def tabelaDistribuicaoTurmas(modelo, c, colunaTurmas):
    """
    Armazena a distribuicao de turmas por escola na tabela SQLite:

    - Nome da tabela: distribuicao_turmas.
    - Colunas:
        - escola_id: ID da escola.
        - regiao_id: ID da regiao da escola.
        - total_turmas_S: uma coluna para cada serie S ativa.
        - alunos_cont: alunos de continuidade na escola.
        - alunos_form: alunos de formulario na escola.
        - total_alunos: total de alunos matriculados na escola.

    Obs: se ```Modelo().somenteTurmasObrig = True```, serao consideradas somente as
    informacoes (turmas e alunos) associadas a turmas ativas.
    """
    schema1 = ('id INTEGER PRIMARY KEY NOT NULL, '
               'escola_id INTEGER NOT NULL, '
               'regiao_id INTEGER NOT NULL, '
              )

    schema2 = ('total_turmas INTEGER NOT NULL, '
               'alunos_cont INTEGER NOT NULL, '
               'alunos_form INTEGER NOT NULL, '
               'total_alunos INTEGER NOT NULL, '
               'FOREIGN KEY (escola_id) REFERENCES escola (id), '
               'FOREIGN KEY (regiao_id) REFERENCES regiao (id)'
              )

    somaColunaTurma = ''
    for turma in colunaTurmas:
        somaColunaTurma = somaColunaTurma + turma
    schema = schema1 + somaColunaTurma + schema2

    create = 'CREATE TABLE IF NOT EXISTS distribuicao_turmas ({})'.format(schema)

    c.execute(create)
    c.execute('DELETE FROM distribuicao_turmas')

    qtdSeries = len(colunaTurmas)
    sqlArgs = '(?,?,?,' + '?,'*qtdSeries + '?,?,?,?)'

    ID = 1
    for escola in modelo.listaTurmas:
        alunosCont = 0
        alunosForm = 0
        distTurmas = iniciaDistTurmas(modelo)
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if aprova(modelo, t):
                    if modelo.p[t] == 1:
                        distTurmas[serie] += 1
                        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                            if modelo.x[i][t] == 1:
                                alunosCont += 1

                        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                            if modelo.y[k][t] == 1:
                                alunosForm += 1

        linha = [ID, int(escola), int(modelo.tabelaEscola['regiao_id'][escola])]
        totalTurmas = 0
        for t in distTurmas:
            linha.append(distTurmas[t])
            totalTurmas += distTurmas[t]

        totalAlunos = alunosCont + alunosForm
        linhaAux = [totalTurmas, alunosCont, alunosForm, totalAlunos]

        linha = tuple(linha + linhaAux)

        c.execute('INSERT INTO distribuicao_turmas VALUES ' + sqlArgs, linha)

        ID += 1

def tabelaDistribuicaoGeral(modelo, c, colunaTurmas):
    """
    Armazena a distribuicao geral de turmas e alunos na tabela SQLite:

    - Nome da tabela: distribuicao_geral.
    - Colunas:
        - total_turmas_S: uma coluna para cada serie S ativa.
        - alunos_cont: alunos de continuidade na escola.
        - alunos_form: alunos de formulario na escola.
        - total_alunos: total de alunos matriculados na escola.
        - verba_disponibilizada: verba disponibilizada pela ONG.
        - verba_utilizada: total utilizado na solucao obtida.
        - verba_utilizada_percent: percentual utilizado da verba.

    Obs: se ```Modelo().somenteTurmasObrig = True```, serao consideradas somente as
    informacoes (verba, turmas e alunos) associadas a turmas ativas.

    Obs: se a faltou verba para alocar alunos de continuidade, sera exibido na coluna
    verba_utilizada um valor acima da verba disponibilizada, indicando a verba necessaria
    para alocar todos os alunos de continuidade respeitando o criterio de verba.
    """
    schema1 = 'id INTEGER PRIMARY KEY NOT NULL, '

    schema2 = ('total_turmas INTEGER NOT NULL, '
               'alunos_cont INTEGER NOT NULL, '
               'alunos_form INTEGER NOT NULL, '
               'total_alunos INTEGER NOT NULL, '
               'verba_disponibilizada INTEGER NOT NULL, '
               'verba_utilizada INTEGER NOT NULL, '
               'verba_utilizada_percent REAL NOT NULL'
              )

    somaColunaTurma = ''
    for turma in colunaTurmas:
        somaColunaTurma = somaColunaTurma + turma
    schema = schema1 + somaColunaTurma + schema2

    create = 'CREATE TABLE IF NOT EXISTS distribuicao_geral ({})'.format(schema)

    c.execute(create)
    c.execute('DELETE FROM distribuicao_geral')

    qtdSeries = len(colunaTurmas)
    sqlArgs = '(?,' + '?,'*qtdSeries + '?,?,?,?,?,?,?)'

    alunosCont = 0
    alunosForm = 0
    distTurmas = iniciaDistTurmas(modelo)
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if aprova(modelo, t):
                    if modelo.p[t] == 1:
                        distTurmas[serie] += 1
                        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                            if modelo.x[i][t] == 1:
                                alunosCont += 1

                        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                            if modelo.y[k][t] == 1:
                                alunosForm += 1

    linha = [1]
    totalTurmas = 0
    for t in distTurmas:
        linha.append(distTurmas[t])
        totalTurmas += distTurmas[t]

    totalAlunos = alunosCont + alunosForm
    usoVerba = (modelo.custoAluno*totalAlunos
                + modelo.custoProf*(modelo.qtdProfPedag + modelo.qtdProfAcd)*totalTurmas)

    linhaAux = [totalTurmas, alunosCont, alunosForm, totalAlunos, modelo.verba,
                usoVerba, usoVerba/modelo.verba]

    linha = tuple(linha + linhaAux)

    c.execute('INSERT INTO distribuicao_geral VALUES ' + sqlArgs, linha)

def reorganizaVariaveisDecisao(modelo):
    """
    Modifica a forma de armazenanar as turmas onde os alunos sao armazendos. Ao inves
    guardar deretamente a turma, armazena numeros binarios da mesma forma que e feita
    pelo solver ortools.
    """
    x = {}
    for i in modelo.alunoCont:
        x[i] = {}
        for t in modelo.alunoCont[i]:
            if modelo.x[i] == t:
                x[i][t] = 1
            else:
                x[i][t] = 0

    y = {}
    for k in modelo.alunoForm:
        y[k] = {}
        for t in modelo.alunoForm[k]:
            if modelo.y[k] == t:
                y[k][t] = 1
            else:
                y[k][t] = 0

    modelo.x = x
    modelo.y = y

def estatisticasBasicasTurma(modelo):
    """
    Retorna algumas estatistcas basicas da distribuicao de turmas:
    - 'mediaAlunosPorTurma': media de alunos por turma
    - 'qtdAlunosMenorTurma': total de alunos na turma com menos alunos
    - 'qtdAlunosMaiorTurma': total de alunos na turma com mais alunos
    - 'turmasCompletas': total de turmas completas
    - 'turmasIncompletas': total de turmas incompletas

    Obs: considera todos os alunos e turmas, independente do valor de
    ```Modelo().somenteTurmasObrig```.
    """
    qtdAlunos = []
    for escola in modelo.listaTurmas:
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if modelo.p[t] == 1:
                    soma = 0
                    for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        soma += modelo.x[i][t]

                    for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        soma += modelo.y[k][t]
                    qtdAlunos.append(soma)

    if len(qtdAlunos) > 0:
        mediaAlunosPorTurma = st.mean(qtdAlunos)
        qtdAlunosMenorTurma = min(qtdAlunos)
        qtdAlunosMaiorTurma = max(qtdAlunos)
        qtdCompletas = sum([1 for qtd in qtdAlunos if qtd == modelo.maxAlunos])
        qtdIncompletas = sum([1 for qtd in qtdAlunos if qtd < modelo.maxAlunos])
        return (mediaAlunosPorTurma, qtdAlunosMenorTurma, qtdAlunosMaiorTurma,
                qtdCompletas, qtdIncompletas)

    return 0, 0, 0, 0, 0

def grafDistAlunosPorEscola(modelo):
    """
    Gera um grafico de barras organizado por escola. Cada escola possui tres barras
    associadas:
    - Uma que representa o total de alunos na turma.
    - Uma que representa o total de alunos de continuidade.
    - Uma que representa o total de alunos de formulario.

    No eixo x, sao representados os ID's de cada escola. No eixo y, o total de alunos
    atendidos para cada barra.

    Obs1: os graficos gerados por essa funcao representam a visualizacao dos dados de
    alunos disponiveis na tabela 'distribuicao_turmas'.

    Obs2: se ```Modelo().somenteTurmasObrig = True```, serao consideradas somente as
    informacoes (turmas e alunos) associadas a turmas ativas.
    """
    width = 0.4
    center = np.arange(len(modelo.listaTurmas))
    labels = []
    listaCont = []
    listaForm = []
    listaTotal = []
    for escola in modelo.listaTurmas:
        labels.append(str(escola))
        somaCont = 0
        somaForm = 0
        somaTotal = 0
        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if aprova(modelo, t):
                    if modelo.p[t] == 1:
                        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                            somaCont += modelo.x[i][t]

                        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                            somaForm += modelo.y[k][t]

        somaTotal += somaCont + somaForm

        listaCont.append(somaCont)
        listaForm.append(somaForm)
        listaTotal.append(somaTotal)

    fig, ax = plt.subplots()

    total = ax.bar(center, listaTotal, width)
    cont = ax.bar(center + width/4, listaCont, width/2)
    form = ax.bar(center - width/4, listaForm, width/2)

    autolabel(cont, ax)
    autolabel(form, ax)

    ax.legend([total, cont, form], ['Total', 'Cont.', 'Form.'])
    ax.set_xticks(center)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Alunos Atendidos')
    ax.set_xlabel('ID da Escola')
    ax.set_title('Distribuição de alunos por escola')
    fig.tight_layout()

    fig.savefig('fig/distAlunosPorEscola.jpg')

def grafDistTurmasPorEscola(modelo):
    """
    Gera uma grafico para cada escola e cada barra representa o total de turmas de uma
    determinada serie abertas na escola.

    Obs1: os graficos gerados por essa funcao representam a visualizacao dos dados de
    turmas disponiveis na tabela 'distribuicao_turmas'.

    Obs2: se ```Modelo().somenteTurmasObrig = True```, serao consideradas somente as
    informacoes (turmas e alunos) associadas a turmas ativas.
    """
    width = 0.4
    for escola in modelo.listaTurmas:
        turmas = []
        labels = []
        for serie in modelo.listaTurmas[escola]:
            soma = 0
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if aprova(modelo, t):
                    soma += modelo.p[t]

            turmas.append(soma)
            labels.append(str(serie))

        center = np.arange(len(turmas))
        fig, ax = plt.subplots()

        total = ax.bar(center, turmas, width)

        autolabel(total, ax)

        ax.set_xticks(center)
        ax.set_xticklabels(labels)
        ax.set_ylabel('Total de Turmas')
        ax.set_xlabel('ID da Serie')
        ax.set_title('Distribuição de turmas: ' + modelo.tabelaEscola['nome'][escola])
        fig.tight_layout()

        fig.savefig('fig/distTurmasEscola'+str(escola)+'.jpg')

def grafDistAlunosPorTurma(modelo, identTurma):
    """
    Gera um grafico para cada escola, e cada grafico organiza as barras por turmas.
    Cada turma possui tres barras:
    - Total de alunos na turma
    - Total de alunos de continuidade
    - Total de alunos de formulario

    Obs1: os graficos gerados por essa funcao representam a visualizacao dos dados de
    alunos disponiveis na tabela 'distribuicao_alunos'.

    Obs2: se ```Modelo().somenteTurmasObrig = True```, serao consideradas somente as
    informacoes (turmas e alunos) associadas a turmas ativas.
    """
    width = 0.4

    for escola in modelo.listaTurmas:
        listaCont = []
        listaForm = []
        listaTotal = []
        labels = []

        for serie in modelo.listaTurmas[escola]:
            for t in modelo.listaTurmas[escola][serie]['turmas']:
                if aprova(modelo, t):
                    if modelo.p[t] == 1:
                        somaCont = 0
                        somaForm = 0
                        somaTotal = 0
                        for i in modelo.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                            somaCont += modelo.x[i][t]

                        for k in modelo.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                            somaForm += modelo.y[k][t]

                        somaTotal += somaCont + somaForm

                        listaCont.append(somaCont)
                        listaForm.append(somaForm)
                        listaTotal.append(somaTotal)

                        labels.append(identTurma[t]['nome'])


        fig, ax = plt.subplots()
        center = np.arange(len(listaTotal))
        total = ax.bar(center, listaTotal, width)
        cont = ax.bar(center + width/4, listaCont, width/2)
        form = ax.bar(center - width/4, listaForm, width/2)

        autolabel(cont, ax)
        autolabel(form, ax)

        ax.legend([total, cont, form], ['Total', 'Cont.', 'Form.'])
        ax.set_xticks(center)
        ax.set_xticklabels(labels)
        ax.set_ylabel('Alunos Atendidos')
        ax.set_xlabel('Nome Turma')
        ax.set_title('Distribuição de alunos: ' + modelo.tabelaEscola['nome'][escola])
        fig.tight_layout()

        fig.savefig('fig/alunosPorTurmaEscola'+str(escola)+'.jpg')

def printbox(palavra):
    """ Imprime uma caixa de *** em volta de 'palavra'."""
    palavra = '**  ' + palavra + '  **'
    estrela = '*'*len(palavra)

    print('\n' + estrela)
    print(palavra)
    print(estrela)

def autolabel(rects, ax):
    """ Funcao para uso no plot dos graficos de barra. Coloca a altura da barra no topo de cada barra. """
    for rect in rects:
        height = int(rect.get_height())
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
