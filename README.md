# Agri Trace

## Agri Trace - Local development

**Step 1: Create a Virtual Environment**  
To isolate your project dependencies, create a Python virtual environment:

```bash
python -m venv env
```

**Step 2: Activate the Virtual Environment**  
Before installing dependencies, activate the virtual environment.

- **For Windows:**
  ```bash
  .\env\Scripts\activate
  ```

**Step 3: Install Dependencies**  
Install all required packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

**Step 4: Create a `.env` File**
Inside your project's root directory, create a `.env` file and add the following configurations:


```env
DJANGO_SECRET_KEY=your_secret_key
PODS_DB_NAME=agri_trace_db
PODS_DB_USERNAME=your_username
PODS_DB_PASSWORD=your_password
PODS_DB_HOST=localhost
PODS_DB_PORT=5432
PODS_ALLOWED_HOSTS=kelompok-71-agri-trace.pkpl.cs.ui.ac.id,.cluster.local,.svc,localhost,127.0.0.1
```
- Make sure to replace the values with your own credentials.

**Step 5: Create the Database**  
Ensure that you have **PostgreSQL** installed. Then, create the database as specified in the `.env` file.

```bash
psql -U your_username -c "CREATE DATABASE agri_trace_db;"
```

**Step 6: Run Database Migrations**  
To apply the initial migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

**Step 7: Run the Server**
Finally, start the development server:

```bash
python manage.py runserver
```

---