import pandas as pd

# Structure des données avec les colonnes attendues par ton importateur
data = {
    "NUMERO_POLICE": ["CTR-2026-601", "CTR-2026-602", "CTR-2026-603"],
    "NOM": ["KOFFI", "AGBO", "EKLOU"],
    "PRENOM": ["Jean", "Amen", "Kofi"],
    "EMAIL": ["jean.koffi@gmail.com", "amen.agbo@gmail.com", "kofi.eklou@gmail.com"],
    "TELEPHONE": ["90010203", "91020304", "92030405"],
    "MARQUE": ["Toyota", "Hyundai", "Nissan"],
    "MODELE": ["Corolla", "Tucson", "Sunny"],
    "IMMATRICULATION": ["TG-1111-AA", "TG-2222-BB", "TG-3333-CC"],
    "NUMERO_QUITTANCE": ["QUIT-2026-601-A", "QUIT-2026-602-A", "QUIT-2026-603-A"],
    "DATE_DEBUT": ["2026-01-01", "2026-02-01", "2026-03-01"],
    "DATE_FIN": ["2026-12-31", "2027-01-31", "2027-02-28"],
    "PRIME_NETTE": [120000, 150000, 135000]
}

# Création du DataFrame et exportation au format XLSX
df = pd.DataFrame(data)
nom_fichier = "contrats_fidelia_template.xlsx"
df.to_excel(nom_fichier, index=False)

print(f" Le fichier Excel a été généré avec succès : {nom_fichier}")