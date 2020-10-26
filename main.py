import matmov as mm

#Para selecionar o arquivo, basta comentar as linhas de forma adequada:
arquivo = 'cenario_2.db'
#arquivo = 'cenario_5.db'
#arquivo = 'original.db'
#arquivo = 'original2020.db'
#arquivo = 'otimizaNoAno.db'
#arquivo = 'reduzirVerba.db'
#arquivo = 'juntaTurmaCont.db'
#arquivo = 'addQuartoAnoEM.db'

############################################
# - Solver padrao: CP-SAT (CBC tambem pode ser utilizado)
# - somenteTurmasObrig: variavel binaria que exibe ou nao os dados de turmas nao
#   ativas
database = 'data/' + arquivo
MatMov = mm.modelo(databasePath= database, somenteTurmasObrig= True)

MatMov.leituraDadosParametros()

MatMov.Solve()

MatMov.exportaSolucaoSQLite()

############################################
##  Opcional  ##
MatMov.estatisticaSolver()

MatMov.estatisticaProblema()

MatMov.analiseGrafica()
