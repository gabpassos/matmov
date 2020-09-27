import matmov as mm

#Para selecionar o arquivo, basta comentar as linhas de forma adequada:
arquivo = 'original.db'
#arquivo = 'original2020.db'
#arquivo = 'otimizaNoAno.db'
#arquivo = 'reduzirVerba.db'
#arquivo = 'juntaTurmaCont.db'
#arquivo = 'addQuartoAnoEM.db'

############################################
database = 'data/' + arquivo
MatMov = mm.modelo(databasePath= database)

MatMov.leituraDadosParametros()

MatMov.Solve()

MatMov.exportaSolucaoSQLite()

############################################
##  Opcional  ##
MatMov.estatisticaSolver()

MatMov.estatisticaProblema()

MatMov.analiseGrafica()
