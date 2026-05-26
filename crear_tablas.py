import requests

# Configuración
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
headers = {
    'apikey': SERVICE_ROLE_KEY,
    'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# SQL para crear la tabla users
sql = """
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY,
    username TEXT,
    email TEXT UNIQUE,
    rol TEXT,
    telefono TEXT,
    saldo NUMERIC DEFAULT 0,
    estado_abogado TEXT,
    matricula TEXT,
    experiencia TEXT,
    descripcion TEXT,
    especialidad TEXT,
    dni TEXT,
    direccion TEXT,
    cuenta_bancaria TEXT,
    foto_url TEXT,
    fcm_token TEXT,
    email_verified BOOLEAN DEFAULT false,
    creado TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Tabla consultas
CREATE TABLE IF NOT EXISTS public.consultas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_uid UUID,
    abogado_uid UUID,
    tipo_servicio TEXT,
    descripcion TEXT,
    estado TEXT DEFAULT 'pendiente',
    precio NUMERIC DEFAULT 0,
    monto NUMERIC DEFAULT 0,
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    fecha_finalizacion TIMESTAMP WITH TIME ZONE,
    ultimo_mensaje TEXT,
    ultimo_mensaje_timestamp TIMESTAMP WITH TIME ZONE
);

-- Tabla mensajes
CREATE TABLE IF NOT EXISTS public.mensajes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consulta_id UUID,
    emisor_uid UUID,
    texto TEXT,
    tipo TEXT DEFAULT 'texto',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    leido BOOLEAN DEFAULT false
);

-- Tabla resenas
CREATE TABLE IF NOT EXISTS public.resenas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consulta_id UUID,
    abogado_email TEXT,
    cliente_email TEXT,
    puntaje INTEGER,
    comentario TEXT,
    fecha TEXT
);

-- Tabla retiros
CREATE TABLE IF NOT EXISTS public.retiros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abogado_uid UUID,
    abogado_email TEXT,
    monto_bruto NUMERIC,
    comision_plataforma NUMERIC DEFAULT 0,
    monto_neto NUMERIC,
    cuenta_destino TEXT,
    estado TEXT DEFAULT 'pendiente',
    fecha TEXT,
    pagado_at TIMESTAMP WITH TIME ZONE,
    admin_uid UUID
);

-- Tabla verificaciones
CREATE TABLE IF NOT EXISTS public.verificaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    codigo TEXT,
    creado TIMESTAMP WITH TIME ZONE DEFAULT now(),
    expira TIMESTAMP WITH TIME ZONE,
    intentos INTEGER DEFAULT 0,
    verificado BOOLEAN DEFAULT false
);
"""

# Ejecutar SQL
response = requests.post(
    f'{SUPABASE_URL}/rest/v1/rpc/exec_sql',
    headers=headers,
    json={'query': sql}
)

if response.status_code == 200:
    print("Tablas creadas exitosamente!")
else:
    print(f"Error: {response.status_code}")
    print(response.text)