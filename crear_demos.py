# crear_abogados_completo.py
# Corre UNA SOLA VEZ: python crear_abogados_completo.py

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase_config import supabase
from firebase_auth import crear_usuario_auth

ABOGADOS = [
    # ── BUENOS AIRES ──
    {"email": "civil.bsas@legalapp.com", "nombre": "Dr. Marcos Villanueva", "especialidad": "Derecho Civil", "provincia": "Buenos Aires", "ciudad": "La Plata", "experiencia": "12 anos", "descripcion": "Contratos, alquileres, danos y perjuicios. Atencion rapida y personalizada.", "estado_abogado": "disponible"},
    {"email": "penal.bsas@legalapp.com", "nombre": "Dra. Sofia Ramos", "especialidad": "Derecho Penal", "provincia": "Buenos Aires", "ciudad": "La Plata", "experiencia": "8 anos", "descripcion": "Defensa penal, excarcelaciones y recursos. Disponible para urgencias.", "estado_abogado": "disponible"},
    {"email": "laboral.bsas@legalapp.com", "nombre": "Dr. Eduardo Herrera", "especialidad": "Derecho Laboral", "provincia": "Buenos Aires", "ciudad": "Mar del Plata", "experiencia": "15 anos", "descripcion": "Despidos, ART, trabajo en negro e indemnizaciones.", "estado_abogado": "disponible"},
    {"email": "familia.bsas@legalapp.com", "nombre": "Dra. Carmen Suarez", "especialidad": "Derecho de Familia", "provincia": "Buenos Aires", "ciudad": "Mar del Plata", "experiencia": "10 anos", "descripcion": "Divorcios, custodia, alimentos y adopciones.", "estado_abogado": "disponible"},
    {"email": "comercial.bsas@legalapp.com", "nombre": "Dr. Pablo Morales", "especialidad": "Derecho Comercial", "provincia": "Buenos Aires", "ciudad": "Quilmes", "experiencia": "9 anos", "descripcion": "Contratos comerciales, marcas y sociedades.", "estado_abogado": "disponible"},
    {"email": "tributario.bsas@legalapp.com", "nombre": "Dra. Laura Benitez", "especialidad": "Derecho Tributario", "provincia": "Buenos Aires", "ciudad": "La Plata", "experiencia": "11 anos", "descripcion": "AFIP, impuestos, monotributo y problemas fiscales.", "estado_abogado": "disponible"},
    {"email": "inmobiliario.bsas@legalapp.com", "nombre": "Dr. Ricardo Paz", "especialidad": "Derecho Inmobiliario", "provincia": "Buenos Aires", "ciudad": "Tigre", "experiencia": "7 anos", "descripcion": "Compra, venta, alquileres y propiedades.", "estado_abogado": "disponible"},
    {"email": "sucesorio.bsas@legalapp.com", "nombre": "Dra. Patricia Ruiz", "especialidad": "Derecho Sucesorio", "provincia": "Buenos Aires", "ciudad": "San Isidro", "experiencia": "14 anos", "descripcion": "Herencias, sucesiones y testamentos.", "estado_abogado": "disponible"},

    # ── CABA ──
    {"email": "civil.caba@legalapp.com", "nombre": "Dr. Alejandro Rios", "especialidad": "Derecho Civil", "provincia": "CABA", "ciudad": "CABA", "experiencia": "18 anos", "descripcion": "Especialista en contratos y responsabilidad civil.", "estado_abogado": "disponible"},
    {"email": "penal.caba@legalapp.com", "nombre": "Dra. Valentina Cruz", "especialidad": "Derecho Penal", "provincia": "CABA", "ciudad": "CABA", "experiencia": "12 anos", "descripcion": "Defensa criminal, estafas y delitos informaticos.", "estado_abogado": "guardia"},
    {"email": "laboral.caba@legalapp.com", "nombre": "Dr. Martin Vega", "especialidad": "Derecho Laboral", "provincia": "CABA", "ciudad": "CABA", "experiencia": "16 anos", "descripcion": "Despidos injustificados, ART y accidentes laborales.", "estado_abogado": "disponible"},
    {"email": "familia.caba@legalapp.com", "nombre": "Dra. Andrea Lopez", "especialidad": "Derecho de Familia", "provincia": "CABA", "ciudad": "CABA", "experiencia": "9 anos", "descripcion": "Divorcios express, tenencia y regimen de visitas.", "estado_abogado": "disponible"},
    {"email": "empresarial.caba@legalapp.com", "nombre": "Dr. Nicolas Blanco", "especialidad": "Derecho Empresarial", "provincia": "CABA", "ciudad": "CABA", "experiencia": "13 anos", "descripcion": "Startups, inversiones y estructura societaria.", "estado_abogado": "disponible"},
    {"email": "administrativo.caba@legalapp.com", "nombre": "Dra. Monica Ferreira", "especialidad": "Derecho Administrativo", "provincia": "CABA", "ciudad": "CABA", "experiencia": "11 anos", "descripcion": "Organismos publicos, licitaciones y multas.", "estado_abogado": "disponible"},
    {"email": "consumidor.caba@legalapp.com", "nombre": "Dr. Diego Salinas", "especialidad": "Derecho del Consumidor", "provincia": "CABA", "ciudad": "CABA", "experiencia": "6 anos", "descripcion": "Defensa al consumidor, garantias y reclamos.", "estado_abogado": "disponible"},
    {"email": "informatico.caba@legalapp.com", "nombre": "Dra. Camila Torres", "especialidad": "Derecho Informatico", "provincia": "CABA", "ciudad": "CABA", "experiencia": "5 anos", "descripcion": "Delitos digitales, hackeos y privacidad en redes.", "estado_abogado": "disponible"},
    {"email": "migratorio.caba@legalapp.com", "nombre": "Dr. Fernando Castillo", "especialidad": "Derecho Migratorio", "provincia": "CABA", "ciudad": "CABA", "experiencia": "8 anos", "descripcion": "Residencias, visas y ciudadania argentina.", "estado_abogado": "disponible"},
    {"email": "seguros.caba@legalapp.com", "nombre": "Dra. Lucia Mendez", "especialidad": "Derecho de Seguros", "provincia": "CABA", "ciudad": "CABA", "experiencia": "10 anos", "descripcion": "Reclamos a aseguradoras y coberturas.", "estado_abogado": "disponible"},

    # ── CORDOBA ──
    {"email": "civil.cba@legalapp.com", "nombre": "Dr. Gustavo Navarro", "especialidad": "Derecho Civil", "provincia": "Cordoba", "ciudad": "Cordoba Capital", "experiencia": "14 anos", "descripcion": "Contratos, inmuebles y responsabilidad civil.", "estado_abogado": "disponible"},
    {"email": "penal.cba@legalapp.com", "nombre": "Dra. Florencia Aguirre", "especialidad": "Derecho Penal", "provincia": "Cordoba", "ciudad": "Cordoba Capital", "experiencia": "9 anos", "descripcion": "Defensa penal y derecho procesal penal.", "estado_abogado": "guardia"},
    {"email": "laboral.cba@legalapp.com", "nombre": "Dr. Hector Vargas", "especialidad": "Derecho Laboral", "provincia": "Cordoba", "ciudad": "Cordoba Capital", "experiencia": "12 anos", "descripcion": "Conflictos laborales, despidos y ART.", "estado_abogado": "disponible"},
    {"email": "familia.cba@legalapp.com", "nombre": "Dra. Natalia Romero", "especialidad": "Derecho de Familia", "provincia": "Cordoba", "ciudad": "Villa Carlos Paz", "experiencia": "8 anos", "descripcion": "Divorcios, alimentos y violencia familiar.", "estado_abogado": "disponible"},
    {"email": "tributario.cba@legalapp.com", "nombre": "Dr. Oscar Medina", "especialidad": "Derecho Tributario", "provincia": "Cordoba", "ciudad": "Cordoba Capital", "experiencia": "16 anos", "descripcion": "Impuestos provinciales, AFIP y rentas.", "estado_abogado": "disponible"},
    {"email": "previsional.cba@legalapp.com", "nombre": "Dra. Rosa Gimenez", "especialidad": "Derecho Previsional", "provincia": "Cordoba", "ciudad": "Rio Cuarto", "experiencia": "20 anos", "descripcion": "Jubilaciones, ANSES y pensiones.", "estado_abogado": "disponible"},

    # ── SANTA FE ──
    {"email": "civil.sf@legalapp.com", "nombre": "Dr. Jorge Maldonado", "especialidad": "Derecho Civil", "provincia": "Santa Fe", "ciudad": "Rosario", "experiencia": "11 anos", "descripcion": "Contratos, danos y propiedad.", "estado_abogado": "disponible"},
    {"email": "laboral.sf@legalapp.com", "nombre": "Dra. Silvia Campos", "especialidad": "Derecho Laboral", "provincia": "Santa Fe", "ciudad": "Rosario", "experiencia": "13 anos", "descripcion": "Despidos, accidentes laborales y sindicatos.", "estado_abogado": "disponible"},
    {"email": "penal.sf@legalapp.com", "nombre": "Dr. Ramon Espinoza", "especialidad": "Derecho Penal", "provincia": "Santa Fe", "ciudad": "Santa Fe Capital", "experiencia": "10 anos", "descripcion": "Defensa penal y excarcelaciones.", "estado_abogado": "disponible"},
    {"email": "familia.sf@legalapp.com", "nombre": "Dra. Isabel Ponce", "especialidad": "Derecho de Familia", "provincia": "Santa Fe", "ciudad": "Rosario", "experiencia": "7 anos", "descripcion": "Divorcios, tenencia y adopciones.", "estado_abogado": "disponible"},

    # ── MENDOZA ──
    {"email": "civil.mdz@legalapp.com", "nombre": "Dr. Carlos Quiroga", "especialidad": "Derecho Civil", "provincia": "Mendoza", "ciudad": "Mendoza Capital", "experiencia": "9 anos", "descripcion": "Contratos y responsabilidad civil.", "estado_abogado": "disponible"},
    {"email": "laboral.mdz@legalapp.com", "nombre": "Dra. Ana Lucero", "especialidad": "Derecho Laboral", "provincia": "Mendoza", "ciudad": "Godoy Cruz", "experiencia": "8 anos", "descripcion": "Empleo vitivinicola, despidos y ART.", "estado_abogado": "disponible"},
    {"email": "familia.mdz@legalapp.com", "nombre": "Dr. Luis Arce", "especialidad": "Derecho de Familia", "provincia": "Mendoza", "ciudad": "Mendoza Capital", "experiencia": "12 anos", "descripcion": "Divorcios, alimentos y herencias.", "estado_abogado": "disponible"},
    {"email": "comercial.mdz@legalapp.com", "nombre": "Dra. Elena Bustos", "especialidad": "Derecho Comercial", "provincia": "Mendoza", "ciudad": "San Rafael", "experiencia": "7 anos", "descripcion": "Contratos comerciales y sociedades.", "estado_abogado": "disponible"},

    # ── SALTA ──
    {"email": "civil.salta@legalapp.com", "nombre": "Dr. Roberto Alvarado", "especialidad": "Derecho Civil", "provincia": "Salta", "ciudad": "Salta Capital", "experiencia": "10 anos", "descripcion": "Contratos y propiedad inmueble.", "estado_abogado": "disponible"},
    {"email": "penal.salta@legalapp.com", "nombre": "Dra. Claudia Mamani", "especialidad": "Derecho Penal", "provincia": "Salta", "ciudad": "Salta Capital", "experiencia": "8 anos", "descripcion": "Defensa penal y violencia de genero.", "estado_abogado": "guardia"},
    {"email": "laboral.salta@legalapp.com", "nombre": "Dr. Hugo Diaz", "especialidad": "Derecho Laboral", "provincia": "Salta", "ciudad": "Salta Capital", "experiencia": "11 anos", "descripcion": "Despidos y conflictos laborales.", "estado_abogado": "disponible"},
    {"email": "familia.salta@legalapp.com", "nombre": "Dra. Miriam Flores", "especialidad": "Derecho de Familia", "provincia": "Salta", "ciudad": "Salta Capital", "experiencia": "6 anos", "descripcion": "Divorcios y custodia de menores.", "estado_abogado": "disponible"},

    # ── TUCUMAN ──
    {"email": "civil.tuc@legalapp.com", "nombre": "Dr. Andres Soria", "especialidad": "Derecho Civil", "provincia": "Tucuman", "ciudad": "San Miguel de Tucuman", "experiencia": "9 anos", "descripcion": "Contratos, danos y alquileres.", "estado_abogado": "disponible"},
    {"email": "laboral.tuc@legalapp.com", "nombre": "Dra. Graciela Juarez", "especialidad": "Derecho Laboral", "provincia": "Tucuman", "ciudad": "San Miguel de Tucuman", "experiencia": "13 anos", "descripcion": "Industria azucarera, despidos y ART.", "estado_abogado": "disponible"},
    {"email": "penal.tuc@legalapp.com", "nombre": "Dr. Victor Luna", "especialidad": "Derecho Penal", "provincia": "Tucuman", "ciudad": "San Miguel de Tucuman", "experiencia": "7 anos", "descripcion": "Defensa penal y recursos.", "estado_abogado": "disponible"},

    # ── ENTRE RIOS ──
    {"email": "civil.er@legalapp.com", "nombre": "Dra. Susana Peralta", "especialidad": "Derecho Civil", "provincia": "Entre Rios", "ciudad": "Parana", "experiencia": "8 anos", "descripcion": "Contratos y propiedades.", "estado_abogado": "disponible"},
    {"email": "familia.er@legalapp.com", "nombre": "Dr. Miguel Acosta", "especialidad": "Derecho de Familia", "provincia": "Entre Rios", "ciudad": "Concordia", "experiencia": "10 anos", "descripcion": "Divorcios y alimentos.", "estado_abogado": "disponible"},

    # ── NEUQUEN ──
    {"email": "civil.nqn@legalapp.com", "nombre": "Dr. Sergio Mansilla", "especialidad": "Derecho Civil", "provincia": "Neuquen", "ciudad": "Neuquen Capital", "experiencia": "9 anos", "descripcion": "Contratos y responsabilidad civil.", "estado_abogado": "disponible"},
    {"email": "laboral.nqn@legalapp.com", "nombre": "Dra. Karina Palacios", "especialidad": "Derecho Laboral", "provincia": "Neuquen", "ciudad": "Neuquen Capital", "experiencia": "7 anos", "descripcion": "Industria petrolera, despidos y ART.", "estado_abogado": "disponible"},

    # ── RIO NEGRO ──
    {"email": "civil.rn@legalapp.com", "nombre": "Dr. Pablo Carrasco", "especialidad": "Derecho Civil", "provincia": "Rio Negro", "ciudad": "Bariloche", "experiencia": "8 anos", "descripcion": "Contratos y propiedad horizontal.", "estado_abogado": "disponible"},
    {"email": "familia.rn@legalapp.com", "nombre": "Dra. Mariana Godoy", "especialidad": "Derecho de Familia", "provincia": "Rio Negro", "ciudad": "Viedma", "experiencia": "6 anos", "descripcion": "Divorcios y tenencia.", "estado_abogado": "disponible"},

    # ── MISIONES ──
    {"email": "civil.mis@legalapp.com", "nombre": "Dr. Daniel Cabrera", "especialidad": "Derecho Civil", "provincia": "Misiones", "ciudad": "Posadas", "experiencia": "7 anos", "descripcion": "Contratos y danos.", "estado_abogado": "disponible"},
    {"email": "laboral.mis@legalapp.com", "nombre": "Dra. Sandra Vera", "especialidad": "Derecho Laboral", "provincia": "Misiones", "ciudad": "Posadas", "experiencia": "9 anos", "descripcion": "Despidos y conflictos laborales.", "estado_abogado": "disponible"},

    # ── CHACO ──
    {"email": "civil.chaco@legalapp.com", "nombre": "Dr. Raul Ibarra", "especialidad": "Derecho Civil", "provincia": "Chaco", "ciudad": "Resistencia", "experiencia": "10 anos", "descripcion": "Contratos y propiedades.", "estado_abogado": "disponible"},
    {"email": "penal.chaco@legalapp.com", "nombre": "Dra. Norma Quispe", "especialidad": "Derecho Penal", "provincia": "Chaco", "ciudad": "Resistencia", "experiencia": "8 anos", "descripcion": "Defensa penal.", "estado_abogado": "disponible"},

    # ── CORRIENTES ──
    {"email": "civil.ctes@legalapp.com", "nombre": "Dr. Alberto Leiva", "especialidad": "Derecho Civil", "provincia": "Corrientes", "ciudad": "Corrientes Capital", "experiencia": "11 anos", "descripcion": "Contratos y alquileres.", "estado_abogado": "disponible"},
    {"email": "familia.ctes@legalapp.com", "nombre": "Dra. Elsa Maidana", "especialidad": "Derecho de Familia", "provincia": "Corrientes", "ciudad": "Corrientes Capital", "experiencia": "9 anos", "descripcion": "Divorcios y alimentos.", "estado_abogado": "disponible"},

    # ── JUJUY ──
    {"email": "civil.jujuy@legalapp.com", "nombre": "Dr. Ernesto Condori", "especialidad": "Derecho Civil", "provincia": "Jujuy", "ciudad": "San Salvador de Jujuy", "experiencia": "8 anos", "descripcion": "Contratos y propiedad.", "estado_abogado": "disponible"},
    {"email": "laboral.jujuy@legalapp.com", "nombre": "Dra. Beatriz Choquehuanca", "especialidad": "Derecho Laboral", "provincia": "Jujuy", "ciudad": "San Salvador de Jujuy", "experiencia": "7 anos", "descripcion": "Despidos y ART.", "estado_abogado": "disponible"},
]

PASSWORD = "Legal123!"


def crear_abogado(datos):
    email = datos["email"]
    nombre = datos["nombre"]

    print(f"\nCreando: {nombre} ({email})")

    # Verificar si ya existe en Supabase
    res = supabase.table("usuarios").select("uid").eq("email", email).execute()
    if res.data:
        print(f"  Ya existe, saltando.")
        return

    # Crear en Firebase
    ok, uid, error = crear_usuario_auth(email, PASSWORD, nombre)
    if not ok:
        if "EMAIL_EXISTS" in str(error) or "email-already-exists" in str(error):
            print(f"  Ya existe en Firebase pero no en Supabase, saltando.")
        else:
            print(f"  Error Firebase: {error}")
        return

    # Insertar en Supabase
    row = {
        "uid": uid,
        "nombre": nombre,
        "username": nombre,
        "email": email,
        "rol": "abogado",
        "telefono": "",
        "email_verified": True,
        "especialidad": datos["especialidad"],
        "especialidades": f'["{datos["especialidad"]}"]',
        "provincia": datos["provincia"],
        "ciudad": datos["ciudad"],
        "experiencia": datos["experiencia"],
        "descripcion": datos["descripcion"],
        "estado_abogado": datos["estado_abogado"],
        "suscripcion_activa": True,
        "suscripcion_monto": 55000,
    }

    try:
        res = supabase.table("usuarios").insert(row).execute()
        if res.data:
            print(f"  OK - {datos['provincia']}, {datos['ciudad']} - {datos['especialidad']}")
        else:
            print(f"  Error insertando en Supabase")
    except Exception as e:
        print(f"  Error Supabase: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("CREANDO ABOGADOS DE PRUEBA - Legal App")
    print(f"Total: {len(ABOGADOS)} abogados")
    print("=" * 60)

    for abogado in ABOGADOS:
        crear_abogado(abogado)

    print("\n" + "=" * 60)
    print("LISTO!")
    print("=" * 60)
    print(f"\nSe crearon abogados en:")
    provincias = list(set(a['provincia'] for a in ABOGADOS))
    for p in sorted(provincias):
        count = sum(1 for a in ABOGADOS if a['provincia'] == p)
        print(f"  {p}: {count} abogados")
    print(f"\nPassword para todos: {PASSWORD}")