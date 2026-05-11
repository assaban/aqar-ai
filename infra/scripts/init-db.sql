-- ============================================
-- Aqar.ai - Database Initialization
-- ============================================
-- Runs automatically on first container start
-- ============================================

-- Enable PostGIS for geospatial queries
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram similarity for fuzzy text matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable unaccent for Arabic text normalization
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Verify extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'uuid-ossp', 'pg_trgm', 'unaccent');
