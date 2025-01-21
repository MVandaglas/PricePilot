import sqlite3

# Database-instellingen
DATABASE_FILE = "bullsai.db"

def create_connection():
    """Maak verbinding met de SQLite-database."""
    conn = sqlite3.connect("bullsai.db")  # Databasebestand
    return conn

def setup_database():
    """Maak de tabellen `Offertes` en `Synoniemen` aan."""
    conn = create_connection()
    cursor = conn.cursor()

    # Tabel Offertes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Offertes (
        Offertenummer INTEGER,
        Rijnummer INTEGER,
        Artikelnaam TEXT NOT NULL,
        Artikelnummer TEXT NOT NULL,
        Spacer TEXT,
        Breedte INTEGER,
        Hoogte INTEGER,
        Aantal INTEGER,
        M2_per_stuk REAL,
        M2_totaal REAL,
        RSP REAL,
        SAP_Prijs REAL,
        Handmatige_Prijs REAL,
        Min_prijs REAL,
        Max_prijs REAL,
        Prijs_backend REAL,
        Verkoopprijs REAL,
        Source TEXT,
        Datum TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (Offertenummer, Rijnummer) -- Gekoppelde PRIMARY KEY
    );
    """)

    # Tabel Synoniemen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Synoniemen (
        Synoniem TEXT PRIMARY KEY,
        Artikelnummer TEXT NOT NULL,
        Artikelnaam TEXT,
        Input TEXT,
        Bron TEXT,
        Datum TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

# Roep deze functie aan bij het opstarten
if __name__ == "__main__":
    setup_database()
