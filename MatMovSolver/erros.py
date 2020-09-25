##################################
#####  VERIFICACAO DE ERROS  #####
##################################
#####  Erros de dados de entrada da ONG  #####
class ErroSerieContinuidadeFechada(Exception):
    """ Erro exibido se um aluno de continuidade deve ser alocado em uma turma cuja serie nao esta ativa. """
    def __init__(self, serie):
        self.serie = serie

    def __str__(self):
        return 'ERRO! A serie "{}" esta fechada. Para atender a demanda dos alunos de continuidade ela deve ser aberta.'.format(self.serie)

class ErroVerbaInsufParaContinuidade(Exception):
    """ Erro exibido se a verba disponibilizada nao e suficiente para alocar os alunos de continuidade. """
    def __str__(self):
        return 'A verba disponibilizada nao e suficiente para atender os alunos de continuidade.'

class ErroTurmaDeContinuidadeComMuitosAlunos(Exception):
    """ Erro exibido se uma turma de alunos de continuidade possui mais matriculados do que o permitido nos parametros. """
    def __init__(self, turma):
        self.turma = turma

    def __str__(self):
        return 'A turma "{}" possui mais alunos que o limite estipulado. Nao e possivel executar a otimizacao ate que os dados sejam ajustados.'.format(self.turma)

class ErroCPFRepetido(Exception):
    """ Erro exibido se existe algum CPF repetido na lista de alunos de continuidade ou na lista de alunos de formulario. """
    def __init__(self, cpf, cont, qtdMatr):
        self.cpf = cpf
        self.cont = cont
        self.qtdMatr = qtdMatr

    def __str__(self):
        if self.cont:
            return 'O aluno de continuidade com CPF {} possui {} matriculas (deve possuir somente uma).'.format(self.cpf, self.qtdMatr)
        else:
            return 'O aluno de formulario com CPF {} possui {} inscricoes (deve possuir somente uma).'.format(self.cpf, self.qtdMatr)

#####  Erros do modulo #####
class ErroLeituraDadosParametros(Exception):
    """ Erro exibido se a leitura de dados e configuracao de parametros nao foi realizada. """
    def __str__(self):
        return 'A leitura de dados nao foi realizada. Execute Modelo().leituraDadosParametros() previamente.'

class ErroFalhaAoExibirResultados(Exception):
    """ Erro exibido se o usuario tentar utilizar alguma ferramenta de visualizacao de solucao antes que o solver seja executado. """
    def __str__(self):
        return 'Erro ao exibir resultados. Execute Modelo().Solver() previamente.'

def verificaCpfRepetido(tabelaAlunoCont, tabelaAlunoForm):
    """
    Verifica as tabelas de alunos de continuidade e de formulario buscando multiplas inscricoes de um mesmo CPF. Retorna "ErroCPFRepetido"
    ao encontrar duas ou mais entradas com mesmo CPF.
    """
    for i in tabelaAlunoCont.index:
        cpf = tabelaAlunoCont['cpf'][i]
        inscr = tabelaAlunoCont[(tabelaAlunoCont['cpf'] == cpf)]
        qtdMatr = len(inscr.index)

        if qtdMatr > 1:
            raise ErroCPFRepetido(cpf, True, qtdMatr)

    for k in tabelaAlunoForm.index:
        cpf = tabelaAlunoForm['cpf'][k]
        inscr = tabelaAlunoForm[(tabelaAlunoForm['cpf'] == cpf)]
        qtdMatr = len(inscr.index)

        if qtdMatr > 1:
            raise ErroCPFRepetido(cpf, False, qtdMatr)
