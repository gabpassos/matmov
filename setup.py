from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name= 'matmov',
      version= '1.0.0',
      description= 'Solver para o problema de alocação de alunos na ONG Matemática em Movimento',
      long_description= long_description,
      long_description_content_type= 'text/markdown',
      author= 'Gabriel Passos, Flávia C. Gachet',
      author_email= 'gabrielpassos97@hotmail.com',
      url= 'https://github.com/gabpassos/matmov',
      packages= ['matmov'],
      license= 'MIT',

      classifiers= [
            'Development Status :: 4 - Beta',
            'License :: OSI Approved :: MIT License',
            'Environment :: Console',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.8',
            'Operating System :: OS Independent'
      ],

      install_requires= [
            'ortools >= 7.8.7959',
            'pandas >= 1.1.2',
            'numpy >= 1.19.2'
      ],
      python_requires= '>=3.7',
)
