-- Table: rci_capteurs.rci_lost

-- DROP TABLE IF EXISTS rci_capteurs.rci_lost;

CREATE TABLE IF NOT EXISTS rci_capteurs.rci_lost
(
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone,
    "uuid" UUID NOT NULL,
    device character varying COLLATE pg_catalog."default",
    data jsonb,
    UNIQUE (uuid)
);

-- Create index on device column for rci_lost table
CREATE INDEX idx_rci_lost_device ON rci_capteurs.rci_lost(device);
CREATE INDEX idx_rci_lost_uuid ON rci_capteurs.rci_lost(uuid);

-- yoko_scci
-- DROP TABLE IF EXISTS rci_capteurs.rci_yoko_scci;

CREATE TABLE IF NOT EXISTS rci_capteurs.rci_yoko_scci
(
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone,
    "uuid" UUID NOT NULL,
    device character varying COLLATE pg_catalog."default",
    data jsonb,
    UNIQUE (uuid)
);

-- Create index on device column for rci_yoko_scci table
CREATE INDEX idx_rci_yoko_scci_device ON rci_capteurs.rci_yoko_scci(device);
CREATE INDEX idx_rci_yoko_scci_uuid ON rci_capteurs.rci_yoko_scci(uuid);

-- yoko_meeb1
-- DROP TABLE IF EXISTS rci_capteurs.rci_yoko_meeb1;

CREATE TABLE IF NOT EXISTS rci_capteurs.rci_yoko_meeb1
(
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone,
    "uuid" UUID NOT NULL,
    device character varying COLLATE pg_catalog."default",
    data jsonb,
   UNIQUE (uuid)
);

-- Create index on device column for rci_yoko_meeb1 table
CREATE INDEX idx_rci_yoko_meeb1_device ON rci_capteurs.rci_yoko_meeb1(device);
CREATE INDEX idx_rci_yoko_meeb1_uuid ON rci_capteurs.rci_yoko_meeb1(uuid);

-- jace_scci
-- DROP TABLE IF EXISTS rci_capteurs.rci_jace_scci;

CREATE TABLE IF NOT EXISTS rci_capteurs.rci_jace_scci
(
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone,
    "uuid" UUID NOT NULL,
    device character varying COLLATE pg_catalog."default",
    data jsonb,
    UNIQUE (uuid)
);

-- Create index on device column for rci_jace_scci table
CREATE INDEX idx_rci_jace_scci_device ON rci_capteurs.rci_jace_scci(device);
CREATE INDEX idx_rci_jace_scci_uuid ON rci_capteurs.rci_jace_scci(uuid);

-- SyncIoT Configuration table
CREATE TABLE IF NOT EXISTS rci_capteurs.rci_config
(
    key character varying COLLATE pg_catalog."default" NOT NULL,
    data jsonb,
    UNIQUE (key)
);

-- Utils SQL Scripts
select count(*) as jace_scci,
	(select count(*) as yoko_meeb1 from rci_capteurs.rci_yoko_meeb1),
	(select count(*) as rci_yoko_scci from rci_capteurs.rci_yoko_scci)
	from rci_capteurs.rci_jace_scci;
