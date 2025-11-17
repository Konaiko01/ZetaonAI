# 1. Use uma imagem base leve do Python
FROM python:3.11-slim

# 2. Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# 3. ATUALIZE o Linux e INSTALE O FFMPEG
RUN apt-get update && apt-get install -y ffmpeg

# 4. Copie o arquivo de dependências
COPY requirements.txt .

# 5. Instale as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copie TODO o seu código
COPY . .

# --- INÍCIO DA CORREÇÃO ---
# 7. Adicione o diretório /app ao PYTHONPATH
ENV PYTHONPATH /app
# --- FIM DA CORREÇÃO ---

# 8. Exponha a porta
EXPOSE 8000

# 9. O comando para rodar sua aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]