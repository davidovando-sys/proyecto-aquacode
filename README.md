# Proyecto Aquacivis

Repositorio oficial del backend desarrollado con Django y conectado a una base de datos PostgreSQL en Supabase.

**AquaCivis** es una plataforma web de monitoreo ciudadano diseñada para vigilar, analizar y transparentar en tiempo real la calidad del agua potable en Chile bajo los estándares de la norma NCh409/1.

## Estado actual
Desplegado

## Guía paso a paso para el equipo (Windows / PowerShell)

1. Clonar el repositorio y abrir la carpeta:
git clone <URL_DEL_REPOSITORIO>
cd proyecto-aquacode

2. Crear y activar el entorno virtual:
python -m venv venv
.\venv\Scripts\Activate.ps1

3. Instalar dependencias:
pip install requirements.txt

4. Configurar credenciales en tu archivo .env (seguir plantilla de .env.example y rellenar)

5. Aplicar migraciones:
python manage.py migrate

6. Iniciar el servidor local:
python manage.py runserver
(Entrar a http://127.0.0.1:8000/).

**actualizar este archivo con información util al terminar**