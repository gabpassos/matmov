from string import ascii_uppercase

def geraNomeTurma(regiao_id, serie_id, contadorTurmas, tabelaSerie, tabelaEscola, tabelaRegiao):
    regiao = tabelaRegiao['nome'][regiao_id]
    serie = tabelaSerie['nome'][serie_id][0]
    turma = ascii_uppercase[contadorTurmas[regiao_id][serie_id]]

    return regiao + '_' + serie + turma
