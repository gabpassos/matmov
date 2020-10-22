import matmov as mm

#Para selecionar o arquivo, basta comentar as linhas de forma adequada:
#arquivo = 'cenario_2.db'
#arquivo = 'cenario_5.db'
#arquivo = 'original.db'
arquivo = 'original2020.db'
#arquivo = 'otimizaNoAno.db'
#arquivo = 'reduzirVerba.db'
#arquivo = 'juntaTurmaCont.db'
#arquivo = 'addQuartoAnoEM.db'

############################################
database = 'data/' + arquivo
MatMov = mm.modelo(databasePath= database, tipoSolver= 'CP_SAT')

MatMov.leituraDadosParametros()

MatMov.SolveOpt()

#MatMov.exportaSolucaoSQLite()

############################################
##  Opcional  ##
MatMov.estatisticaSolver()

#MatMov.estatisticaProblema()

#MatMov.analiseGrafica()
