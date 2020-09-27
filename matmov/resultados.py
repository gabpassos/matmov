from string import ascii_uppercase
import statistics as st

import numpy as np
import matplotlib.pyplot as plt

def matriculasCont(self):
    """ Calcula o total de alunos de continuidade matriculados. """
    X = [self.x[i][t].solution_value() for i in self.alunoCont.keys() for t in self.alunoCont[i]]
    totalAtendidoCont = sum(X)

    return totalAtendidoCont

def matriculasForm(self):
    """
    Calcula o total de alunos de formulario atendidos, o total de alunos de formulario
    (entre atendidos e nao atendidos),  e a fracao de alunos de formulario atendidos.
    """
    Y = [self.y[k][t].solution_value() for k in self.alunoForm.keys() for t in self.alunoForm[k]]

    totalAtendidoForm = sum(Y)
    totalAlunosForm = len(self.tabelaAlunoForm.index)
    fracForm = totalAtendidoForm/totalAlunosForm
    return totalAlunosForm, totalAtendidoForm, fracForm

def qtdTurmasAbertas(self):
    """
    Retorna o total de turmas abertas.
    """
    P = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                P.append(self.p[t].solution_value())

    return sum(P)

def estatisticasBasicasTurma(self):
    """
    Retorna algumas estatistcas basicas da distribuicao de turmas:
    - 'mediaAlunosPorTurma': media de alunos por turma
    - 'dpAlunosPorTurma': desvio padrao da distribuicao de alunos por turma
    - 'qtdAlunosMenorTurma': total de alunos na turma com menos alunos
    - 'qtdAlunosMaiorTurma': total de alunos na turma com mais alunos
    - 'turmasCompletas': total de turmas completas
    - 'turmasIncompletas': total de turmas incompletas
    """
    qtdAlunos = []
    for escola in self.listaTurmas.keys():
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    soma = 0
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        soma += self.x[i][t].solution_value()

                    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        soma += self.y[k][t].solution_value()
                    qtdAlunos.append(soma)

    mediaAlunosPorTurma = st.mean(qtdAlunos)
    dpAlunosPorTurma = st.stdev(qtdAlunos, mediaAlunosPorTurma)
    qtdAlunosMenorTurma = min(qtdAlunos)
    qtdAlunosMaiorTurma = max(qtdAlunos)
    turmasCompletas = sum([1 for qtd in qtdAlunos if qtd == self.maxAlunos])
    turmasIncompletas = sum([1 for qtd in qtdAlunos if qtd < self.maxAlunos])
    return mediaAlunosPorTurma, dpAlunosPorTurma, qtdAlunosMenorTurma, qtdAlunosMaiorTurma, turmasCompletas, turmasIncompletas

def estatisticasVerba(self, totalAlunos, totalTurmas):
    """
    Retorna a verba total disponibilizada, a verba total utilizada e o que sobrou da verba.
    """
    verbaTotal = self.verba
    verbaUtilizada = self.custoAluno*totalAlunos + self.custoProf*(self.qtdProfPedag + self.qtdProfAcd)*totalTurmas
    verbaRestante = verbaTotal - verbaUtilizada

    return verbaTotal, verbaUtilizada, verbaRestante

def grafDistAlunosPorEscola(self):
    """
    Gera um grafico de barras organizado por escola. Cada escola possui tres barras associadas:
    - Uma que representa o total de alunos na turma.
    - Uma que representa o total de alunos de continuidade.
    - Uma que representa o total de alunos de formulario.

    No eixo x, sao representados os ID's de cada escola. No eixo y, o total de alunos atendidos para cada barra.
    """
    width = 0.4
    center = np.arange(len(self.listaTurmas.keys()))
    labels = []
    listaCont = []
    listaForm = []
    listaTotal = []
    for escola in self.listaTurmas.keys():
        labels.append(str(escola))
        somaCont = 0
        somaForm = 0
        somaTotal = 0
        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        somaCont += self.x[i][t].solution_value()

                    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        somaForm += self.y[k][t].solution_value()

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

def grafDistTurmasPorEscola(self):
    """
    Gera uma grafico para cada escola e cada barra representa o total de turmas de uma determinada serie abertas na escola.
    """
    width = 0.4
    for escola in self.listaTurmas.keys():
        turmas = []
        labels = []
        for serie in self.listaTurmas[escola].keys():
            soma = 0
            for t in self.listaTurmas[escola][serie]['turmas']:
                    soma += self.p[t].solution_value()

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
        ax.set_title('Distribuição de turmas: ' + self.tabelaEscola['nome'][escola])
        fig.tight_layout()

        fig.savefig('fig/distTurmasEscola'+str(escola)+'.jpg')

def grafDistAlunosPorTurma(self):
    """
    Gera um grafico para cada escola, e cada grafico organiza as barras por turmas. Cada turma possui tres barras:
    - Total de alunos na turma
    - Total de alunos de continuidade
    - Total de alunos de formulario
    """
    width = 0.4

    contadorTurmas = {}
    for regiao in self.tabelaRegiao.index:
        contadorTurmas[regiao] = {}
        for serie in self.tabelaSerie[(self.tabelaSerie['ativa'] == 1)].index:
            contadorTurmas[regiao][serie] = 0

    for escola in self.listaTurmas.keys():
        regiao = self.tabelaEscola['regiao_id'][escola]
        listaCont = []
        listaForm = []
        listaTotal = []
        labels = []

        for serie in self.listaTurmas[escola].keys():
            for t in self.listaTurmas[escola][serie]['turmas']:
                if self.p[t].solution_value() == 1:
                    somaCont = 0
                    somaForm = 0
                    somaTotal = 0
                    for i in self.listaTurmas[escola][serie]['alunosPossiveis']['cont']:
                        somaCont += self.x[i][t].solution_value()

                    for k in self.listaTurmas[escola][serie]['alunosPossiveis']['form']:
                        somaForm += self.y[k][t].solution_value()

                    somaTotal += somaCont + somaForm

                    listaCont.append(somaCont)
                    listaForm.append(somaForm)
                    listaTotal.append(somaTotal)

                    labels.append(geraNomeTurma(regiao, serie, contadorTurmas, self.tabelaSerie, self.tabelaEscola, self.tabelaRegiao))
                    contadorTurmas[regiao][serie] = contadorTurmas[regiao][serie] + 1

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
        ax.set_title('Distribuição de alunos: ' + self.tabelaEscola['nome'][escola])
        fig.tight_layout()

        fig.savefig('fig/alunosPorTurmaEscola'+str(escola)+'.jpg')

def printbox(palavra):
    """ Imprime uma caixa de *** em volta de 'palavra'."""
    palavra = '**  ' + palavra + '  **'
    estrela = '*'*len(palavra)

    print('\n' + estrela)
    print(palavra)
    print(estrela)

def geraNomeTurma(regiao_id, serie_id, contadorTurmas, tabelaSerie, tabelaEscola, tabelaRegiao):
    """
    Gera o nome da turma EXATAMENTE da maneira com que a ONG faz atualmente.
    Para solucionar o problema de mais de uma escola na mesma regiao, adicionamos um contador de turmas,
    que vai adicionar a 'ordem alfabetica' de maneira sequencial. Isto e, se duas ou mais escolas estao na
    mesma regiao, pode ser que uma turma comece a ser contabilizada numa escola a partir da letra C.
    """
    regiao = tabelaRegiao['nome'][regiao_id]
    serie = tabelaSerie['nome'][serie_id][0]
    turma = ascii_uppercase[contadorTurmas[regiao_id][serie_id]]

    return regiao + '_' + serie + turma

def autolabel(rects, ax):
    """ Funcao para uso no plot dos graficos de barra. Coloca a altura da barra no topo de cada barra. """
    for rect in rects:
        height = int(rect.get_height())
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
