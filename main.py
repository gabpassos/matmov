import matmov as mm

arquivo = 'original.db'
#arquivo = 'original2020.db'
#arquivo = 'otimizaNoAno.db'
#arquivo = 'reduzirVerba.db'
#arquivo = 'juntaTurmaCont.db'
#arquivo = 'addQuartoAnoEM.db'

database = 'data/' + arquivo
MatMov = mm.modelo(databasePath= database)

MatMov.leituraDadosParametros()

MatMov.Solve()

MatMov.estatisticaSolver()

MatMov.estatisticaProblema()

MatMov.exportaSolucaoSQLite()

MatMov.analiseGrafica()
