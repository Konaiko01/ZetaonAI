# 1. Use uma imagem base leve do Python
FROM python:3.11-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. ATUALIZE o Linux e INSTALE O FFMPEG (A correção crucial)
RUN apt-get update && apt-get install -y ffmpeg

# 4. Copie o arquivo de dependências
COPY requirements.txt .

# 5. Instale as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copie TODO o seu código (main.py, agents/, clients/, etc.)
COPY . .

# 7. Exponha a porta que o Uvicorn/Gunicorn usará
EXPOSE 8000

# 8. O comando para rodar sua aplicação em produção
# (O mesmo comando gunicorn que falhou no Windows funcionará aqui, pois Docker é Linux)
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "main:app"]