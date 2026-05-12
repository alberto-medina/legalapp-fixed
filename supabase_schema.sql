-- supabase_schema.sql — Juris Lex
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- Este schema replica el SQLite local pero en PostgreSQL con seguridad Row Level Security.

-- ─────────────────────────────────────────────────────────────────────────
-- TABLA: users
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL DEFAULT '',
    rol             TEXT NOT NULL DEFAULT 'cliente' CHECK (rol IN ('cliente', 'abogado', 'admin')),
    telefono        TEXT DEFAULT '',
    foto            TEXT DEFAULT '',
    matricula       TEXT DEFAULT '',
    experiencia     TEXT DEFAULT '',
    descripcion     TEXT DEFAULT '',
    estado_abogado  TEXT DEFAULT 'disponible' CHECK (estado_abogado IN ('disponible', 'ocupado', 'inactivo')),
    cuenta_bancaria TEXT DEFAULT '',
    saldo           NUMERIC(12, 2) DEFAULT 0.00,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────
-- TABLA: consultas
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consultas (
    id              BIGSERIAL PRIMARY KEY,
    user_email      TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    abogado         TEXT NOT NULL REFERENCES users(email),
    estado          TEXT DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'activa', 'finalizada', 'cancelada')),
    tipo_servicio   TEXT NOT NULL CHECK (tipo_servicio IN ('chat', 'video', 'urgente')),
    fecha           TIMESTAMPTZ DEFAULT NOW(),
    monto           NUMERIC(10, 2) DEFAULT 0.00
);

-- ─────────────────────────────────────────────────────────────────────────
-- TABLA: mensajes
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mensajes (
    id          BIGSERIAL PRIMARY KEY,
    consulta_id BIGINT NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    emisor      TEXT NOT NULL,
    mensaje     TEXT DEFAULT '',
    archivo     TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────
-- TABLA: resenas
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resenas (
    id             BIGSERIAL PRIMARY KEY,
    consulta_id    BIGINT UNIQUE NOT NULL REFERENCES consultas(id),
    abogado_email  TEXT NOT NULL REFERENCES users(email),
    cliente_email  TEXT NOT NULL REFERENCES users(email),
    puntaje        INTEGER NOT NULL CHECK (puntaje BETWEEN 1 AND 5),
    comentario     TEXT DEFAULT '',
    fecha          TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────
-- TABLA: retiros
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS retiros (
    id                  BIGSERIAL PRIMARY KEY,
    abogado_email       TEXT NOT NULL REFERENCES users(email),
    monto_bruto         NUMERIC(10, 2) NOT NULL,
    comision_plataforma NUMERIC(10, 2) DEFAULT 0.00,
    monto_neto          NUMERIC(10, 2) NOT NULL,
    cuenta_destino      TEXT NOT NULL,
    estado              TEXT DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'procesado', 'rechazado')),
    fecha               TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────
-- ÍNDICES
-- ─────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_consultas_user    ON consultas(user_email);
CREATE INDEX IF NOT EXISTS idx_consultas_abogado ON consultas(abogado);
CREATE INDEX IF NOT EXISTS idx_mensajes_consulta ON mensajes(consulta_id);
CREATE INDEX IF NOT EXISTS idx_users_rol         ON users(rol);

-- ─────────────────────────────────────────────────────────────────────────
-- FUNCIÓN: incrementar saldo de forma atómica
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION increment_saldo(user_email TEXT, delta NUMERIC)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET saldo = saldo + delta, updated_at = NOW()
    WHERE email = user_email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─────────────────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- Cada usuario solo puede ver sus propios datos.
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE consultas ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensajes  ENABLE ROW LEVEL SECURITY;
ALTER TABLE resenas   ENABLE ROW LEVEL SECURITY;
ALTER TABLE retiros   ENABLE ROW LEVEL SECURITY;

-- Los usuarios solo ven su propio perfil
CREATE POLICY "users_own_row" ON users
    FOR ALL USING (email = current_setting('app.current_user_email', TRUE));

-- Clientes ven sus consultas; abogados ven las asignadas a ellos
CREATE POLICY "consultas_access" ON consultas
    FOR ALL USING (
        user_email = current_setting('app.current_user_email', TRUE)
        OR abogado = current_setting('app.current_user_email', TRUE)
    );

-- ─────────────────────────────────────────────────────────────────────────
-- TRIGGER: actualizar updated_at automáticamente
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
